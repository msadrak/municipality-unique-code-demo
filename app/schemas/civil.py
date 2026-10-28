from __future__ import annotations

from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from app.models.civil import ApprovalTaskStatus

class CivilProjectListItem(BaseModel):
    id: int
    project_code: str
    title: str
    current_phase: int
    current_step: int
    contract_category: str | None = None
    yekta_code: str | None = None
    current_step_code: str | None = None
    current_step_name: str | None = None
    activity_name: str | None = None
    budget_line: str | None = None
    owning_org_unit_name: str | None = None
    created_at: str | None = None
    paid_amount: int | None = None

class DocumentResponse(BaseModel):
    id: int
    document_type: str
    payload: Dict[str, Any]
    submitted_by: str | None = None
    submitted_at: str | None = None

class ApprovalTaskResponse(BaseModel):
    id: int
    role: str
    status: ApprovalTaskStatus
    comments: str | None = None
    approver_name: str | None = None

class CivilFinancialSummary(BaseModel):
    total_budget: int | None = None
    committed_amount: int | None = None
    total_paid_net: int = 0

class CivilTransactionResponse(BaseModel):
    id: int
    document_number: str
    unique_code: str | None = None
    date: str | None = None
    amount: int | None = None
    description: str | None = None
    status: str | None = None
    financial_event: str | None = None
    financial_event_label: str | None = None
    financial_matrix_id: int | None = None

class CivilFinancialMatrixRowResponse(BaseModel):
    id: int
    transaction_id: int | None = None
    event_sequence: int | None = None
    event_code: str
    event_label: str | None = None
    event_group: str | None = None
    event_direction: str | None = None
    amount: float | None = None
    yekta_code: str | None = None
    payment_queue_status: str | None = None
    period_key: str | None = None
    source_payload: Dict[str, Any] | None = None

class StepInfoResponse(BaseModel):
    step_name: str
    step_number: int
    total_steps: int
    assigned_role: str | None = None
    required_form_type: str | None = None
    form_schema: Dict[str, Any] | None = None

class CivilProjectDetailResponse(BaseModel):
    id: int
    project_code: str
    title: str
    contract_category: str | None = None
    yekta_code: str | None = None
    budget_line: str | None = None
    current_step_info: StepInfoResponse
    documents: List[DocumentResponse]
    approval_tasks: List[ApprovalTaskResponse]
    can_advance: bool
    financial_summary: CivilFinancialSummary | None = None
    transactions: List[CivilTransactionResponse] = []
    financial_matrix: List[CivilFinancialMatrixRowResponse] = []


__all__ = ["CivilProjectListItem", "CivilProjectDetailResponse", "CivilFinancialMatrixRowResponse"]
