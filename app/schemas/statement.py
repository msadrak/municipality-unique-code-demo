"""
Pydantic Schemas for Progress Statement — 4-Stage Workflow
==========================================================

Covers: statement creation, approval, rejection, list/detail views, financial summary.
"""

from datetime import date
from typing import Optional, List, Any

from pydantic import BaseModel, Field


# ============================================================
# Request Schemas
# ============================================================

class StatementCreate(BaseModel):
    """POST /contracts/{id}/statements - create a draft statement."""

    amount: Optional[int] = Field(
        None,
        gt=0,
        description="Requested net amount in Rials (preferred).",
    )
    gross_amount: Optional[int] = Field(
        None,
        gt=0,
        description="Gross amount in Rials (backward compatible).",
    )
    deductions: int = Field(0, ge=0, description="Total deductions in Rials.")
    description: str = Field(..., min_length=1, description="Statement description.")
    period_start: Optional[date] = Field(None, description="Statement period start date.")
    period_end: Optional[date] = Field(None, description="Statement period end date.")
    statement_type: str = Field("INTERIM", description="INTERIM, FINAL, ADJUSTMENT, FINAL_ADJUSTMENT.")

    # New generalized fields
    originating_organ: Optional[str] = Field(None, description="Municipal organ submitting the statement.")
    template_data: Optional[dict] = Field(None, description="Department-specific data (JSON).")

    # Deduction breakdown
    insurance_deduction: int = Field(0, ge=0, description="Insurance deduction in Rials.")
    tax_deduction: int = Field(0, ge=0, description="Tax deduction in Rials.")
    advance_payment_amount: int = Field(0, ge=0, description="Advance payment deduction in Rials.")
    other_deductions: int = Field(0, ge=0, description="Other deductions in Rials.")


class StatementApprove(BaseModel):
    """PUT /statements/{id}/approve - approval at any level."""

    review_comment: Optional[str] = Field(None, description="Reviewer comment.")


class StatementReject(BaseModel):
    """PUT /statements/{id}/reject - rejection at any pending stage."""

    rejection_reason: Optional[str] = Field(None, description="Reason for rejection.")


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
    originating_organ: Optional[str] = None

    # Financial
    gross_amount: int
    deductions: int = 0
    net_amount: int
    cumulative_amount: int = 0
    previous_statement_amount: int = 0

    # Deduction breakdown
    insurance_deduction: int = 0
    tax_deduction: int = 0
    advance_payment_amount: int = 0
    other_deductions: int = 0

    # Approval level
    current_approval_level: int = 0

    # Department-specific data
    template_data: Optional[Any] = None

    # Workflow
    submitted_by_id: Optional[int] = None
    reviewed_by_id: Optional[int] = None
    rejected_by_id: Optional[int] = None
    review_comment: Optional[str] = None
    rejection_reason: Optional[str] = None
    submitted_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    rejected_at: Optional[str] = None

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
    current_approval_level: int = 0
    originating_organ: Optional[str] = None
    created_at: Optional[str] = None

    # Optional contract context (populated by pending-statements endpoint)
    contract_number: Optional[str] = None
    contract_title: Optional[str] = None


class StatementListResponse(BaseModel):
    """GET /contracts/{id}/statements - list response."""

    items: List[StatementListItem]
    total: int
    contract_id: int


class PendingStatementListResponse(BaseModel):
    """GET /statements/pending - all pending statements across contracts."""

    items: List[StatementListItem]
    total: int


class StatementFinancialSummary(BaseModel):
    """Financial summary for a contract's statements."""

    contract_id: int
    contract_total: int
    statement_count: int
    total_gross: int
    total_deductions: int
    total_net_committed: int
    total_approved: int
    remaining: int
