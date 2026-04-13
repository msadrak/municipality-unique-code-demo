from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.database import get_db
from app.models import FundingRequest, FundingStatus, User, UserRole
from app.routers.auth import require_auth
from app.schemas.funding_workflow import (
    AdvanceRequest,
    FundingRequestCreate,
    FundingRequestResponse,
    FundingRequestUpdate,
    FundingWorkflowLogResponse,
)
from app.services.funding_budget_service import BudgetService
from app.services.funding_service import (
    create_funding_request,
    get_funding_request,
    list_funding_requests,
    list_my_funding_requests,
    transition_status,
    update_funding_request,
)
from app.services.workflow_service import (
    ROLE_VISIBLE_STATUSES,
    WorkflowService,
    is_admin_role,
    normalize_user_role,
)

router = APIRouter(prefix="/funding", tags=["HR Funding Requests"])

ARCHIVE_ROLES = {
    UserRole.ADMIN,
    UserRole.GM_HC,
    UserRole.VP_PLANNING,
    UserRole.VP_FINANCE,
    UserRole.WELFARE_DEPT,
    UserRole.FINANCE_UNIT,
    UserRole.GM_FINANCE,
    UserRole.ISFAHAN_CARD,
}


def _hydrate_request_defaults(req: FundingRequest) -> FundingRequest:
    req.letter_date = req.letter_date or "1405/01/01"
    req.receiver_title = req.receiver_title or "گیرنده تعیین نشده"
    req.sender_title = req.sender_title or "فرستنده تعیین نشده"
    req.subject = req.subject or req.title or req.tracking_number or "موضوع تعیین نشده"
    req.body_text = req.body_text or req.description or req.subject
    req.attachment_count = req.attachment_count if req.attachment_count is not None else 0
    req.request_type = req.request_type or "voucher_charge"
    req.title = req.title or req.subject
    req.description = req.description or req.body_text
    return req


def _build_funding_pdf(req: FundingRequest) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle(f"funding-request-{req.id}")
    pdf.setFont("Helvetica", 12)
    y = 800
    lines = [
        "Official Funding Letter",
        f"Tracking Number: {req.tracking_number}",
        f"Letter Number: {req.letter_number or '-'}",
        f"Letter Date: {req.letter_date}",
        f"Receiver: {req.receiver_title}",
        f"Sender: {req.sender_title}",
        f"Subject: {req.subject}",
        f"Amount: {req.amount if req.amount is not None else '-'}",
        f"Attachments: {req.attachment_count}",
        f"Status: {req.status.value}",
        f"Budget Code: {req.budget_code or '-'}",
        f"Charge Letter: {req.charge_letter_number or '-'}",
        f"Created At: {req.created_at.isoformat() if req.created_at else '-'}",
    ]
    for line in lines:
        pdf.drawString(48, y, line)
        y -= 24

    description = req.body_text or "-"
    pdf.drawString(48, y, "Body:")
    y -= 20
    for chunk_start in range(0, len(description), 90):
        pdf.drawString(60, y, description[chunk_start:chunk_start + 90])
        y -= 18
        if y < 80:
            pdf.showPage()
            pdf.setFont("Helvetica", 12)
            y = 800

    if req.cc_list:
        pdf.drawString(48, y, "CC:")
        y -= 20
        for chunk_start in range(0, len(req.cc_list), 90):
            pdf.drawString(60, y, req.cc_list[chunk_start:chunk_start + 90])
            y -= 18
            if y < 80:
                pdf.showPage()
                pdf.setFont("Helvetica", 12)
                y = 800

    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


def _normalize_extra_fields(extra_fields: dict | None) -> dict:
    normalized = dict(extra_fields or {})
    charge_letter_date = normalized.get("charge_letter_date")
    if isinstance(charge_letter_date, str):
        try:
            normalized["charge_letter_date"] = datetime.fromisoformat(charge_letter_date)
        except ValueError:
            pass
    return normalized


def _ensure_creator_role(current_user: User) -> None:
    role = normalize_user_role(current_user.role)
    if role not in {UserRole.GM_HC, UserRole.ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="فقط مدیرکل سرمایه انسانی یا ادمین مجاز به ثبت درخواست است",
        )


def _ensure_request_access(db: Session, request_id: int, current_user: User) -> FundingRequest:
    req = get_funding_request(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="درخواست یافت نشد")

    if req.created_by_id == current_user.id or is_admin_role(current_user.role):
        return req

    normalized_role = normalize_user_role(current_user.role)
    visible_statuses = ROLE_VISIBLE_STATUSES.get(normalized_role, []) if normalized_role else []
    if req.status in visible_statuses:
        return req

    raise HTTPException(status_code=403, detail="اجازه دسترسی به این درخواست را ندارید")


def _ensure_archive_access(current_user: User) -> None:
    role = normalize_user_role(current_user.role)
    if role not in ARCHIVE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="اجازه دسترسی به بایگانی نامه‌ها را ندارید",
        )


@router.post("/requests", response_model=FundingRequestResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=FundingRequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(
    body: FundingRequestCreate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    _ensure_creator_role(current_user)
    return _hydrate_request_defaults(
        create_funding_request(db=db, request_in=body, user_id=current_user.id)
    )


@router.get("/", response_model=List[FundingRequestResponse])
def get_my_requests(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return [
        _hydrate_request_defaults(item)
        for item in list_my_funding_requests(db=db, user_id=current_user.id, skip=skip, limit=limit)
    ]


@router.get("/all", response_model=List[FundingRequestResponse])
def get_all_requests(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    if is_admin_role(current_user.role):
        return [
            _hydrate_request_defaults(item)
            for item in list_funding_requests(db=db, skip=skip, limit=limit)
        ]
    return [
        _hydrate_request_defaults(item)
        for item in list_my_funding_requests(db=db, user_id=current_user.id, skip=skip, limit=limit)
    ]


@router.get("/inbox", response_model=List[FundingRequestResponse])
def inbox(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    svc = WorkflowService(db)
    return [_hydrate_request_defaults(item) for item in svc.get_inbox(current_user.role)]


@router.get("/archive", response_model=List[FundingRequestResponse])
def archive(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    _ensure_archive_access(current_user)
    return [_hydrate_request_defaults(item) for item in list_funding_requests(db=db)]


@router.post("/requests/{request_id}/transition", response_model=FundingRequestResponse)
@router.post("/{request_id}/transition", response_model=FundingRequestResponse)
@router.post("/requests/{request_id}/advance", response_model=FundingRequestResponse)
def advance_request(
    request_id: int,
    body: AdvanceRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    req = _ensure_request_access(db, request_id, current_user)
    extra_fields = _normalize_extra_fields(body.extra_fields)

    if req.status == FundingStatus.BUDGET_VP_FINANCE and body.action == "approve":
        fiscal_year = req.budget_year or 1405
        if not BudgetService.check_available_budget(req.amount, fiscal_year):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="بودجه کافی برای این درخواست در دسترس نیست",
            )
        result = BudgetService.reserve_budget(
            request_id=request_id,
            amount=req.amount,
            fiscal_year=fiscal_year,
        )
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=result.message,
            )
        extra_fields["budget_code"] = result.allocation_code

    svc = WorkflowService(db)
    return _hydrate_request_defaults(
        svc.advance_status(
            request_id=request_id,
            user_id=current_user.id,
            raw_user_role=current_user.role,
            action=body.action,
            comment=body.comment,
            extra_fields=extra_fields,
        )
    )


@router.get("/requests/{request_id}/history", response_model=List[FundingWorkflowLogResponse])
def get_request_history(
    request_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    _ensure_request_access(db, request_id, current_user)
    svc = WorkflowService(db)
    return svc.get_history(request_id)


@router.get("/requests/{request_id}", response_model=FundingRequestResponse)
@router.get("/{request_id}", response_model=FundingRequestResponse)
def get_request_detail(
    request_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return _hydrate_request_defaults(_ensure_request_access(db, request_id, current_user))


@router.get("/{request_id}/pdf")
def get_request_pdf(
    request_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    req = _ensure_request_access(db, request_id, current_user)
    pdf_bytes = _build_funding_pdf(req)
    filename = f"funding-request-{request_id}.pdf"
    headers = {"Content-Disposition": f'inline; filename="{filename}"'}
    return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)


@router.put("/{request_id}", response_model=FundingRequestResponse)
def update_request(
    request_id: int,
    body: FundingRequestUpdate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return _hydrate_request_defaults(
        update_funding_request(
            db=db,
            request_id=request_id,
            update_data=body,
            user_id=current_user.id,
            raw_user_role=current_user.role,
        )
    )


@router.patch("/{request_id}/status", response_model=FundingRequestResponse)
def manual_change_status(
    request_id: int,
    new_status: FundingStatus,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return _hydrate_request_defaults(
        transition_status(
            db=db,
            request_id=request_id,
            new_status=new_status,
            user_id=current_user.id,
            raw_user_role=current_user.role,
        )
    )
