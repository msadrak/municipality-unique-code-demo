from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.workflow import transition
from app.database import get_db
from app.models import UserRole
from app.models.attendance import RegionalAttendanceSheet
from app.schemas.attendance import (
    AttendanceAggregationOut,
    AttendanceReconciliationOut,
    AttendanceSheetOut,
    WorkflowTransitionRequest,
)
from app.services.attendance_service import (
    get_attendance_aggregation,
    get_attendance_reconciliation,
    ingest_excel,
    ingest_statement_excel,
)

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


def _can_access_aggregation_dashboard(raw_role: Optional[str]) -> bool:
    if not raw_role:
        return False
    if raw_role in {"admin", "ADMIN"} or raw_role.startswith("ADMIN_L"):
        return True
    return raw_role.upper() == UserRole.SECURITY_DIRECTOR.value


@router.get("", response_model=List[AttendanceSheetOut])
def get_attendance_sheets(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get attendance sheets for inbox (only sheets with parsed attendance rows)."""
    return (
        db.query(RegionalAttendanceSheet)
        .filter(RegionalAttendanceSheet.row_count > 0)
        .order_by(RegionalAttendanceSheet.created_at.desc())
        .all()
    )


@router.post("/upload", response_model=AttendanceSheetOut, status_code=201)
def upload_attendance_sheet(
    file: UploadFile = File(...),
    title: str = Form(...),
    year: int = Form(...),
    month: int = Form(...),
    region_name: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ingest_excel(
        file=file,
        title=title,
        year=year,
        month=month,
        region_name=region_name,
        creator_id=current_user.id,
        db=db,
    )


@router.post("/upload/statement", response_model=AttendanceSheetOut, status_code=201)
def upload_attendance_statement(
    file: UploadFile = File(...),
    title: str = Form(default="صورت وضعیت"),
    year: int = Form(...),
    month: int = Form(...),
    region_name: str = Form(...),
    declared_total_amount: float = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ingest_statement_excel(
        file=file,
        title=title,
        year=year,
        month=month,
        region_name=region_name,
        declared_total_amount=declared_total_amount,
        creator_id=current_user.id,
        db=db,
    )


@router.post("/{sheet_id}/transition", response_model=AttendanceSheetOut)
def workflow_transition(
    sheet_id: int,
    body: WorkflowTransitionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    sheet = (
        db.query(RegionalAttendanceSheet)
        .filter(RegionalAttendanceSheet.id == sheet_id)
        .first()
    )
    if not sheet:
        raise HTTPException(status_code=404, detail="Sheet not found.")

    return transition(
        sheet=sheet,
        action=body.action,
        actor_id=current_user.id,
        db=db,
        rejection_reason=body.rejection_reason,
    )


@router.get("/reports/aggregation", response_model=AttendanceAggregationOut)
def get_attendance_aggregation_report(
    region: Optional[str] = Query(
        None,
        description="Filter by region title",
    ),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by attendance workflow status",
    ),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not _can_access_aggregation_dashboard(getattr(current_user, "role", None)):
        raise HTTPException(
            status_code=403,
            detail="دسترسی فقط برای مدیر حراست و مدیر سامانه مجاز است.",
        )

    return get_attendance_aggregation(
        db,
        region=region,
        status=status_filter,
    )


@router.get(
    "/reconciliation/{year}/{month}/{region_name}",
    response_model=AttendanceReconciliationOut,
)
def get_attendance_reconciliation_report(
    year: int,
    month: int,
    region_name: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not _can_access_aggregation_dashboard(getattr(current_user, "role", None)):
        raise HTTPException(
            status_code=403,
            detail="Ø¯Ø³ØªØ±Ø³ÛŒ ÙÙ‚Ø· Ø¨Ø±Ø§ÛŒ Ù…Ø¯ÛŒØ± Ø­Ø±Ø§Ø³Øª Ùˆ Ù…Ø¯ÛŒØ± Ø³Ø§Ù…Ø§Ù†Ù‡ Ù…Ø¬Ø§Ø² Ø§Ø³Øª.",
        )

    return get_attendance_reconciliation(
        db,
        year=year,
        month=month,
        region_name=region_name,
    )


@router.get("/{sheet_id}", response_model=AttendanceSheetOut)
def get_attendance_sheet_details(
    sheet_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a specific sheet with all its parsed Excel records"""
    sheet = (
        db.query(RegionalAttendanceSheet)
        .filter(
            RegionalAttendanceSheet.id == sheet_id,
            RegionalAttendanceSheet.row_count > 0,
        )
        .first()
    )
    if not sheet:
        raise HTTPException(status_code=404, detail="Sheet not found.")
    return sheet
