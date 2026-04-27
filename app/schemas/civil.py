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
    current_step_code: str | None = None
    current_step_name: str | None = None
    activity_name: str | None = None
    budget_line: str | None = None
    owning_org_unit_name: str | None = None

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
    date: str | None = None
    amount: int | None = None
    description: str | None = None
    status: str | None = None

class StepInfoResponse(BaseModel):
    step_name: str
    step_number: int
    total_steps: int
    required_form_type: str | None = None
    form_schema: Dict[str, Any] | None = None

class CivilProjectDetailResponse(BaseModel):
    id: int
    project_code: str
    title: str
    budget_line: str | None = None
    current_step_info: StepInfoResponse
    documents: List[DocumentResponse]
    approval_tasks: List[ApprovalTaskResponse]
    can_advance: bool
    financial_summary: CivilFinancialSummary | None = None
    transactions: List[CivilTransactionResponse] = []


__all__ = ["CivilProjectListItem", "CivilProjectDetailResponse"]
