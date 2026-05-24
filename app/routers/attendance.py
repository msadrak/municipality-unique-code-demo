from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.workflow import transition
from app.database import get_db
from app.models import User, UserRole
from app.models.attendance import RegionalAttendanceSheet
from app.models.enums import AttendanceSheetStatus
from app.schemas.attendance import (
    AttachmentOut,
    AttendanceAggregationOut,
    AttendanceReconciliationOut,
    AttendanceRecordOut,
    AttendanceRecordUpdate,
    AttendanceAuditLogOut,
    AttendanceSheetRejectRequest,
    AttendanceSheetOut,
    PenaltyRecordCreate,
    PenaltyRecordOut,
    WorkPeriodApprovalOut,
    WorkPeriodStatusOut,
    WorkflowTransitionRequest,
)
from app.services.attendance_service import (
    approve_work_period_aggregation,
    create_penalty_record_for_work_period,
    finalize_work_period,
    get_attendance_aggregation,
    get_work_period_upload_status,
    get_work_period_reconciliation,
    parse_attendance_excel_to_db,
    parse_contractor_statement_excel,
    reject_attendance_sheet,
)
from app.utils.constants import AUTHORIZED_REGION_SET

router = APIRouter(prefix="/api/attendance", tags=["attendance"])

ADMIN_ROLE_VALUES = {"admin", "ADMIN"}
ATTENDANCE_VIEW_ROLES = {
    UserRole.REGION_USER.value,
    UserRole.SECURITY_AGGREGATOR.value,
    UserRole.CONTRACTOR.value,
    UserRole.SECURITY_DIRECTOR.value,
}


def _role_value(user: User) -> str:
    return (user.role or "").strip()


def _normalized_role(user: User) -> str:
    return _role_value(user).upper()


def _is_admin(user: User) -> bool:
    raw_role = _role_value(user)
    return raw_role in ADMIN_ROLE_VALUES or raw_role.startswith("ADMIN_L")


def _ensure_attendance_view_access(current_user: User) -> None:
    if _is_admin(current_user):
        return
    if _normalized_role(current_user) not in ATTENDANCE_VIEW_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to the attendance module is not allowed for this account.",
        )


def _validate_region_name(region_name: str) -> str:
    normalized_region_name = region_name.strip()
    if normalized_region_name not in AUTHORIZED_REGION_SET:
        raise HTTPException(
            status_code=400,
            detail="Invalid region_name. Select one of the authorized organizational units.",
        )
    return normalized_region_name


def _ensure_region_scope(current_user: User, region_name: str) -> None:
    if _is_admin(current_user):
        return

    if _normalized_role(current_user) == UserRole.REGION_USER.value:
        if not current_user.region_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Region user is not linked to an authorized region.",
            )
        if current_user.region_name != region_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Region users can only work with their own organizational unit.",
            )


def _ensure_can_upload_attendance(current_user: User, region_name: str) -> None:
    if _is_admin(current_user):
        return
    if _normalized_role(current_user) != UserRole.REGION_USER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only regional users can upload attendance sheets.",
        )
    _ensure_region_scope(current_user, region_name)


def _ensure_can_upload_statement(current_user: User) -> None:
    if _is_admin(current_user):
        return
    if _normalized_role(current_user) != UserRole.CONTRACTOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the contractor account can upload contractor statements.",
        )


def _ensure_can_access_sheet(current_user: User, sheet: RegionalAttendanceSheet) -> None:
    _ensure_attendance_view_access(current_user)
    _ensure_region_scope(current_user, sheet.region or "")


def _ensure_can_transition_sheet(
    current_user: User,
    sheet: RegionalAttendanceSheet,
    action: str,
) -> None:
    if _is_admin(current_user):
        return

    normalized_role = _normalized_role(current_user)
    status_to_role = {
        AttendanceSheetStatus.DRAFT: UserRole.REGION_USER.value,
        AttendanceSheetStatus.NEEDS_CORRECTION: UserRole.REGION_USER.value,
        AttendanceSheetStatus.CREATOR_APPROVED: UserRole.CONTRACTOR.value,
        AttendanceSheetStatus.COMPANY_REP_APPROVED: UserRole.SECURITY_AGGREGATOR.value,
        AttendanceSheetStatus.SECURITY_APPROVED: UserRole.SECURITY_DIRECTOR.value,
    }

    required_role = status_to_role.get(sheet.status)
    if required_role is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition a sheet in status '{sheet.status.value}'.",
        )

    if normalized_role != required_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to transition this sheet at the current workflow step.",
        )

    if normalized_role == UserRole.REGION_USER.value:
        _ensure_region_scope(current_user, sheet.region or "")
        if action != "approve":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Regional users can only submit their own sheet for review.",
            )


def _can_access_aggregation_dashboard(current_user: User) -> bool:
    if _is_admin(current_user):
        return True
    return _normalized_role(current_user) in {
        UserRole.SECURITY_AGGREGATOR.value,
        UserRole.SECURITY_DIRECTOR.value,
    }


def _ensure_security_aggregator(current_user: User) -> None:
    if _is_admin(current_user):
        return
    if _normalized_role(current_user) != UserRole.SECURITY_AGGREGATOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the security aggregator can approve regional aggregation.",
        )


def _ensure_security_director(current_user: User) -> None:
    if _is_admin(current_user):
        return
    if _normalized_role(current_user) != UserRole.SECURITY_DIRECTOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the security director can manage final reconciliation.",
        )


@router.get("", response_model=List[AttendanceSheetOut])
def get_attendance_sheets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get attendance sheets for inbox (only sheets with parsed attendance rows)."""
    _ensure_attendance_view_access(current_user)

    query = (
        db.query(RegionalAttendanceSheet)
        .filter(RegionalAttendanceSheet.row_count > 0)
        .order_by(RegionalAttendanceSheet.created_at.desc())
    )

    if not _is_admin(current_user) and _normalized_role(current_user) == UserRole.REGION_USER.value:
        query = query.filter(RegionalAttendanceSheet.region == current_user.region_name)

    return query.all()


@router.post("/upload", response_model=AttendanceSheetOut, status_code=201)
def upload_attendance_sheet(
    file: UploadFile = File(...),
    title: str = Form(...),
    year: int = Form(...),
    month: int = Form(...),
    region_name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validated_region_name = _validate_region_name(region_name)
    _ensure_can_upload_attendance(current_user, validated_region_name)
    return parse_attendance_excel_to_db(
        file=file,
        title=title,
        year=year,
        month=month,
        region_name=validated_region_name,
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
    current_user: User = Depends(get_current_user),
):
    validated_region_name = _validate_region_name(region_name)
    _ensure_can_upload_statement(current_user)
    return parse_contractor_statement_excel(
        file=file,
        title=title,
        year=year,
        month=month,
        region_name=validated_region_name,
        declared_total_amount=declared_total_amount,
        creator_id=current_user.id,
        db=db,
    )


@router.post("/{sheet_id}/transition", response_model=AttendanceSheetOut)
def workflow_transition(
    sheet_id: int,
    body: WorkflowTransitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sheet = (
        db.query(RegionalAttendanceSheet)
        .filter(RegionalAttendanceSheet.id == sheet_id)
        .first()
    )
    if not sheet:
        raise HTTPException(status_code=404, detail="Sheet not found.")

    _ensure_can_access_sheet(current_user, sheet)
    _ensure_can_transition_sheet(current_user, sheet, body.action)

    return transition(
        sheet=sheet,
        action=body.action,
        actor_id=current_user.id,
        db=db,
        rejection_reason=body.rejection_reason,
    )


@router.post("/sheets/{sheet_id}/reject", response_model=AttendanceSheetOut)
def reject_sheet_with_feedback(
    sheet_id: int,
    body: AttendanceSheetRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_security_aggregator(current_user)
    return reject_attendance_sheet(
        db,
        sheet_id=sheet_id,
        reason=body.reason,
        actor_id=current_user.id,
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
    current_user: User = Depends(get_current_user),
):
    if not _can_access_aggregation_dashboard(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only security workflow users can access attendance aggregation reports.",
        )

    return get_attendance_aggregation(
        db,
        region=region,
        status=status_filter,
    )


@router.get(
    "/work-periods/{year}/{month}/reconciliation",
    response_model=AttendanceReconciliationOut,
)
def get_work_period_reconciliation_report(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_security_director(current_user)
    return get_work_period_reconciliation(
        db,
        year=year,
        month=month,
    )


@router.get(
    "/work-periods/{year}/{month}/status",
    response_model=WorkPeriodStatusOut,
)
def get_work_period_status(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_access_aggregation_dashboard(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only security workflow users can access work-period status.",
        )

    return get_work_period_upload_status(
        db,
        year=year,
        month=month,
    )


@router.post(
    "/work-periods/{year}/{month}/approve-aggregation",
    response_model=WorkPeriodApprovalOut,
)
def approve_aggregation_for_work_period(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_security_aggregator(current_user)
    return approve_work_period_aggregation(
        db,
        year=year,
        month=month,
    )


@router.post(
    "/work-periods/{year}/{month}/penalties",
    response_model=PenaltyRecordOut,
    status_code=201,
)
def create_work_period_penalty(
    year: int,
    month: int,
    body: PenaltyRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_security_director(current_user)
    return create_penalty_record_for_work_period(
        db,
        year=year,
        month=month,
        payload=body,
    )


@router.post(
    "/work-periods/{year}/{month}/finalize",
    response_model=WorkPeriodApprovalOut,
)
def finalize_work_period_report(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_security_director(current_user)
    return finalize_work_period(
        db,
        year=year,
        month=month,
        initiated_by=current_user,
    )



# ---------------------------------------------------------------------------
# Attachment endpoints
# ---------------------------------------------------------------------------

ALLOWED_ATTACHMENT_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}

ATTACHMENT_MIME_TO_TYPE = {
    "application/pdf": "pdf",
    "image/jpeg": "image",
    "image/png": "image",
}


@router.post(
    "/sheets/{sheet_id}/attachments",
    response_model=List[AttachmentOut],
    status_code=201,
)
def upload_sheet_attachments(
    sheet_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload one or more PDF / image attachment files for a sheet (invoice docs)."""
    import os
    import uuid
    from app.models.attendance import Attachment

    _ensure_attendance_view_access(current_user)

    sheet = (
        db.query(RegionalAttendanceSheet)
        .filter(RegionalAttendanceSheet.id == sheet_id)
        .first()
    )
    if not sheet:
        raise HTTPException(status_code=404, detail="Sheet not found.")

    _ensure_can_access_sheet(current_user, sheet)

    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")

    base_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "uploads",
        "attachments",
    )
    os.makedirs(base_dir, exist_ok=True)

    created: List[Attachment] = []
    for upload in files:
        content_type = upload.content_type or ""
        if content_type not in ALLOWED_ATTACHMENT_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"File '{upload.filename}' has unsupported type '{content_type}'. "
                    "Only PDF, JPEG, and PNG are allowed."
                ),
            )

        file_type = ATTACHMENT_MIME_TO_TYPE[content_type]
        ext = ".pdf" if file_type == "pdf" else (
            ".jpg" if content_type == "image/jpeg" else ".png"
        )
        unique_name = f"{uuid.uuid4().hex}{ext}"
        dest_path = os.path.join(base_dir, unique_name)
        relative_path = f"uploads/attachments/{unique_name}"

        with open(dest_path, "wb") as dest:
            dest.write(upload.file.read())

        attachment = Attachment(
            sheet_id=sheet_id,
            file_path=relative_path,
            file_name=upload.filename or unique_name,
            file_type=file_type,
        )
        db.add(attachment)
        created.append(attachment)

    db.commit()
    for att in created:
        db.refresh(att)

    return created


@router.get(
    "/sheets/{sheet_id}/attachments",
    response_model=List[AttachmentOut],
)
def get_sheet_attachments(
    sheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all attachments for a given sheet."""
    from app.models.attendance import Attachment

    _ensure_attendance_view_access(current_user)

    sheet = (
        db.query(RegionalAttendanceSheet)
        .filter(RegionalAttendanceSheet.id == sheet_id)
        .first()
    )
    if not sheet:
        raise HTTPException(status_code=404, detail="Sheet not found.")

    _ensure_can_access_sheet(current_user, sheet)

    return (
        db.query(Attachment)
        .filter(Attachment.sheet_id == sheet_id)
        .order_by(Attachment.created_at.asc())
        .all()
    )


@router.get("/{sheet_id}", response_model=AttendanceSheetOut)
def get_attendance_sheet_details(
    sheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific sheet with all its parsed Excel records."""
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

    _ensure_can_access_sheet(current_user, sheet)
    return sheet


@router.patch("/records/{record_id}", response_model=AttendanceRecordOut)
def update_attendance_record_api(
    record_id: int,
    body: AttendanceRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.attendance_service import update_attendance_record
    _ensure_security_aggregator(current_user)
    return update_attendance_record(db, record_id=record_id, payload=body, user_id=current_user.id)


@router.get("/records/{record_id}/audit-logs", response_model=List[AttendanceAuditLogOut])
def get_audit_logs_api(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.attendance_service import get_attendance_audit_logs
    if not _can_access_aggregation_dashboard(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )
    return get_attendance_audit_logs(db, record_id=record_id)


@router.get(
    "/work-periods/{year}/{month}/regions/{region_name}/records",
    response_model=List[AttendanceRecordOut],
)
def get_region_records_api(
    year: int,
    month: int,
    region_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.attendance_service import get_work_period_region_records
    if not _can_access_aggregation_dashboard(current_user):
        raise HTTPException(status_code=403, detail="Access denied.")
    validated_region = _validate_region_name(region_name)
    return get_work_period_region_records(db, year=year, month=month, region_name=validated_region)
