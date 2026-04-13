from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import jdatetime
from pydantic import BaseModel, ConfigDict, Field

from app.models import FundingStatus


def _today_persian() -> str:
    return jdatetime.date.today().strftime("%Y/%m/%d")


class FundingRequestCreate(BaseModel):
    letter_date: str = Field(default_factory=_today_persian, examples=["1405/01/22"])
    receiver_title: str = Field(..., min_length=2, max_length=256, examples=["معاون محترم برنامه‌ریزی و توسعه سرمایه انسانی"])
    sender_title: str = Field(..., min_length=2, max_length=256, examples=["مدیرکل سرمایه انسانی"])
    subject: str = Field(..., min_length=2, max_length=512, examples=["درخواست شارژ کارت رفاهی پرسنل - اردیبهشت 1405"])
    body_text: str = Field(..., min_length=10)
    cc_list: Optional[str] = Field(None, examples=["مدیرکل مالی\nمعاون توسعه مدیریت"])
    attachment_count: int = Field(0, ge=0)
    amount: Optional[int] = Field(None, ge=0, description="مبلغ به ریال")
    request_type: Optional[str] = Field(None, examples=["voucher_charge"])


class FundingRequestUpdate(BaseModel):
    letter_number: Optional[str] = None
    letter_date: Optional[str] = None
    receiver_title: Optional[str] = None
    sender_title: Optional[str] = None
    subject: Optional[str] = None
    body_text: Optional[str] = None
    cc_list: Optional[str] = None
    attachment_count: Optional[int] = Field(None, ge=0)
    amount: Optional[int] = Field(None, ge=0)
    request_type: Optional[str] = None
    status: Optional[FundingStatus] = None
    budget_year: Optional[int] = None
    budget_code: Optional[str] = None
    charge_letter_number: Optional[str] = None
    charge_letter_date: Optional[datetime] = None


class AdvanceRequest(BaseModel):
    action: str
    comment: Optional[str] = None
    extra_fields: Optional[dict[str, Any]] = None


class FundingWorkflowLogResponse(BaseModel):
    id: int
    request_id: int
    user_id: int
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None
    from_status: FundingStatus
    to_status: FundingStatus
    action: str
    comment: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class FundingRequestResponse(BaseModel):
    id: int
    tracking_number: str
    letter_number: Optional[str] = None
    letter_date: str
    receiver_title: str
    sender_title: str
    subject: str
    body_text: str
    cc_list: Optional[str] = None
    attachment_count: int
    amount: Optional[int] = None
    request_type: Optional[str] = None
    status: FundingStatus
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    budget_year: Optional[int] = None
    budget_code: Optional[str] = None
    charge_letter_number: Optional[str] = None
    charge_letter_date: Optional[datetime] = None

    # Legacy compatibility for older clients that still read these fields.
    title: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
