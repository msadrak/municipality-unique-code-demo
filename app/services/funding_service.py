from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import jdatetime
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import FundingRequest, FundingStatus, FundingWorkflowLog
from app.schemas.funding_workflow import FundingRequestCreate, FundingRequestUpdate
from app.services.workflow_service import is_admin_role


EDITABLE_STATUSES = {FundingStatus.PENDING_VP_PLANNING, FundingStatus.DRAFT}
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def _get_current_fiscal_year() -> int:
    try:
        return int(jdatetime.datetime.now().year)
    except Exception:
        return datetime.utcnow().year


def _generate_tracking_number(db: Session) -> str:
    max_id = db.query(func.max(FundingRequest.id)).scalar() or 0
    next_id = max_id + 1
    fiscal_year = _get_current_fiscal_year()
    return f"HR-{fiscal_year}-{next_id:04d}"


def _extract_budget_year(letter_date: Optional[str]) -> Optional[int]:
    if not letter_date:
        return None

    normalized = letter_date.translate(PERSIAN_DIGITS).strip()
    year_part = normalized.split("/", 1)[0]
    if year_part.isdigit():
        return int(year_part)
    return None


def create_funding_request(db: Session, request_in: FundingRequestCreate, user_id: int) -> FundingRequest:
    status_value = FundingStatus.PENDING_VP_PLANNING
    budget_year = _extract_budget_year(request_in.letter_date)
    current_year = _get_current_fiscal_year()
    db_obj = FundingRequest(
        tracking_number=_generate_tracking_number(db),
        letter_number=None,
        letter_date=request_in.letter_date,
        receiver_title=request_in.receiver_title,
        sender_title=request_in.sender_title,
        subject=request_in.subject,
        body_text=request_in.body_text,
        cc_list=request_in.cc_list,
        attachment_count=request_in.attachment_count,
        amount=request_in.amount,
        request_type=request_in.request_type,
        title=request_in.subject,
        description=request_in.body_text,
        budget_year=budget_year,
        status=status_value,
        created_by_id=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(db_obj)
    db.flush()
    db_obj.letter_number = f"{current_year}/{db_obj.id:05d}"
    db.add(
        FundingWorkflowLog(
            request_id=db_obj.id,
            user_id=user_id,
            from_status=status_value,
            to_status=status_value,
            action="create",
            comment="ثبت اولیه نامه درخواست تامین اعتبار",
        )
    )
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_funding_request(db: Session, request_id: int) -> Optional[FundingRequest]:
    return db.query(FundingRequest).filter(FundingRequest.id == request_id).first()


def list_funding_requests(db: Session, skip: int = 0, limit: int = 100) -> List[FundingRequest]:
    return (
        db.query(FundingRequest)
        .order_by(FundingRequest.created_at.desc(), FundingRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def list_my_funding_requests(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[FundingRequest]:
    return (
        db.query(FundingRequest)
        .filter(FundingRequest.created_by_id == user_id)
        .order_by(FundingRequest.updated_at.desc(), FundingRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_funding_request(
    db: Session,
    request_id: int,
    update_data: FundingRequestUpdate,
    user_id: int,
    raw_user_role: Optional[str] = None,
) -> FundingRequest:
    db_obj = get_funding_request(db, request_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="درخواست یافت نشد")

    is_admin = is_admin_role(raw_user_role)
    if db_obj.created_by_id != user_id and not is_admin:
        raise HTTPException(status_code=403, detail="اجازه ویرایش این درخواست را ندارید")

    if db_obj.status not in EDITABLE_STATUSES and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ویرایش فقط قبل از شروع گردش اصلی مجاز است",
        )

    payload = update_data.model_dump(exclude_unset=True)
    for field_name, value in payload.items():
        if field_name == "status":
            db_obj.status = value
        else:
            setattr(db_obj, field_name, value)

    if "subject" in payload:
        db_obj.title = db_obj.subject
    if "body_text" in payload:
        db_obj.description = db_obj.body_text
    if "letter_date" in payload and "budget_year" not in payload:
        db_obj.budget_year = _extract_budget_year(db_obj.letter_date)

    db_obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_obj)
    return db_obj


def transition_status(
    db: Session,
    request_id: int,
    new_status: FundingStatus,
    user_id: int,
    raw_user_role: Optional[str] = None,
) -> FundingRequest:
    if not is_admin_role(raw_user_role):
        raise HTTPException(status_code=403, detail="تغییر مستقیم وضعیت فقط برای ادمین مجاز است")

    db_obj = get_funding_request(db, request_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="درخواست یافت نشد")

    old_status = db_obj.status
    db_obj.status = new_status
    db_obj.updated_at = datetime.utcnow()
    db.add(
        FundingWorkflowLog(
            request_id=db_obj.id,
            user_id=user_id,
            from_status=old_status,
            to_status=new_status,
            action="manual_status_update",
            comment="تغییر مستقیم وضعیت توسط ادمین",
        )
    )
    db.commit()
    db.refresh(db_obj)
    return db_obj
