"""
Pydantic Schemas for Progress Statement (Sprint 3)
==================================================

Covers: statement creation, approval, payment, list/detail views, financial summary.
"""

from datetime import date
from typing import Optional, List

from pydantic import BaseModel, Field


# ============================================================
# Request Schemas
# ============================================================

class StatementCreate(BaseModel):
    """POST /contracts/{id}/statements - create a draft statement."""

    amount: Optional[int] = Field(
        None,
        gt=0,
        description="Requested net amount in Rials (preferred for Sprint 3).",
    )
    gross_amount: Optional[int] = Field(
        None,
        gt=0,
        description="Gross amount in Rials (backward compatible).",
    )
    deductions: int = Field(0, ge=0, description="Deductions in Rials.")
    description: str = Field(..., min_length=1, description="Statement description.")
    period_start: Optional[date] = Field(None, description="Statement period start date.")
    period_end: Optional[date] = Field(None, description="Statement period end date.")
    statement_type: str = Field("INTERIM", description="INTERIM, FINAL, ADJUSTMENT.")


class StatementApprove(BaseModel):
    """PUT /statements/{id}/approve - supervisor approval."""

    review_comment: Optional[str] = Field(None, description="Supervisor comment.")


# ============================================================
# Response Schemas
# ============================================================

class StatementResponse(BaseModel):
    """Full statement detail."""

    id: int
    statement_number: str
    contract_id: int
    sequence_number: int
    statement_type: str
    status: str

    # Content
    description: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None

    # Financial
    gross_amount: int
    deductions: int = 0
    net_amount: int
    cumulative_amount: int = 0

    # Workflow
    submitted_by_id: Optional[int] = None
    reviewed_by_id: Optional[int] = None
    review_comment: Optional[str] = None
    submitted_at: Optional[str] = None
    reviewed_at: Optional[str] = None

    # Audit
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    version: int = 1

    class Config:
        from_attributes = True


class StatementListItem(BaseModel):
    """Abbreviated statement for list views."""

    id: int
    statement_number: str
    sequence_number: int
    status: str
    net_amount: int
    cumulative_amount: int = 0
    created_at: Optional[str] = None


class StatementListResponse(BaseModel):
    """GET /contracts/{id}/statements - list response."""

    items: List[StatementListItem]
    total: int
    contract_id: int


class StatementFinancialSummary(BaseModel):
    """Financial summary for a contract's statements."""

    contract_id: int
    contract_total: int
    statement_count: int
    total_gross: int
    total_deductions: int
    total_net_committed: int
    total_paid: int
    remaining: int
