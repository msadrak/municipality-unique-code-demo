"""
Pydantic Schemas for Credit Request (Stage 1 Gateway)
=====================================================

Covers: creation, submission, approval, rejection, cancellation,
listing (with filters), and detail responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ============================================================
# Request Schemas
# ============================================================

class CreditRequestCreate(BaseModel):
    """POST /credit-requests — create a DRAFT credit request."""
    zone_id: int
    department_id: Optional[int] = None
    section_id: Optional[int] = None
    budget_code: str = Field(..., min_length=1)
    amount_requested: float = Field(..., gt=0)
    description: str = Field(..., min_length=1)
    fiscal_year: str = "1403"
    attachments: Optional[Any] = None
    form_data: Optional[dict] = None
    client_request_id: Optional[str] = None


class CreditRequestApprove(BaseModel):
    """POST /credit-requests/{id}/approve"""
    amount_approved: Optional[float] = None  # None => use amount_requested
    comment: Optional[str] = None


class CreditRequestReject(BaseModel):
    """POST /credit-requests/{id}/reject"""
    reason: str = Field(..., min_length=1)


class CreditRequestCancel(BaseModel):
    """POST /credit-requests/{id}/cancel"""
    reason: Optional[str] = None


# ============================================================
# Response Schemas
# ============================================================

class CreditRequestResponse(BaseModel):
    """Full credit request detail."""
    id: int
    credit_request_code: str
    status: str
    zone_id: int
    zone_title: Optional[str] = None
    department_id: Optional[int] = None
    department_title: Optional[str] = None
    section_id: Optional[int] = None
    section_title: Optional[str] = None
    budget_code: str
    amount_requested: float
    amount_approved: Optional[float] = None
    description: str
    fiscal_year: str
    attachments: Optional[Any] = None
    form_data: Optional[dict] = None
    created_by_id: int
    created_by_name: Optional[str] = None
    reviewed_by_id: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    used_transaction_id: Optional[int] = None
    version: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class CreditRequestListItem(BaseModel):
    """Abbreviated item for list views."""
    id: int
    credit_request_code: str
    status: str
    zone_title: Optional[str] = None
    budget_code: str
    amount_requested: float
    amount_approved: Optional[float] = None
    description: str
    created_by_name: Optional[str] = None
    used_transaction_id: Optional[int] = None
    created_at: Optional[str] = None


class CreditRequestListResponse(BaseModel):
    """GET /credit-requests — paginated list."""
    items: List[CreditRequestListItem]
    total: int
    page: int
    limit: int


class CreditRequestActionResponse(BaseModel):
    """Response for state-transition actions (submit/approve/reject/cancel)."""
    status: str  # "success"
    message: str
    new_status: str
    credit_request_code: str


class CreditRequestLogEntry(BaseModel):
    """Single audit log entry."""
    id: int
    action: str
    previous_status: str
    new_status: str
    actor_name: Optional[str] = None
    comment: Optional[str] = None
    created_at: Optional[str] = None
