"""
Pydantic Schemas for Contract Lifecycle (Sprint 2)
====================================================

Covers: draft creation, status transitions, template rendering, list/detail views.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date


# ============================================================
# Request Schemas
# ============================================================

class ContractDraftCreate(BaseModel):
    """POST /contracts/draft — start the contract wizard."""
    budget_row_id: int = Field(..., description="ردیف بودجه مرتبط")
    contractor_id: int = Field(..., description="شناسه پیمانکار")
    template_id: int = Field(..., description="شناسه قالب قرارداد")
    title: str = Field(..., min_length=1, description="عنوان قرارداد")
    total_amount: int = Field(..., gt=0, description="مبلغ کل قرارداد (ریال)")
    template_data: Optional[Dict[str, Any]] = Field(
        None, description="داده‌های اولیه فرم قالب (اختیاری)"
    )
    start_date: Optional[date] = Field(None, description="تاریخ شروع")
    end_date: Optional[date] = Field(None, description="تاریخ پایان")


class ContractStatusTransition(BaseModel):
    """PUT /contracts/{id}/transition — explicit status change."""
    new_status: str = Field(..., description="وضعیت جدید قرارداد")


# ============================================================
# Response Schemas
# ============================================================

class ContractResponse(BaseModel):
    """Full contract detail."""
    id: int
    contract_number: str
    title: str
    status: str

    # References
    contractor_id: int
    contractor_name: Optional[str] = None
    template_id: Optional[int] = None
    template_title: Optional[str] = None
    budget_row_id: Optional[int] = None
    credit_request_id: Optional[int] = None
    org_unit_id: Optional[int] = None

    # Financial
    total_amount: int
    paid_amount: int = 0

    # Dates
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    # Template data
    template_data: Optional[Dict[str, Any]] = None
    metadata_extra: Optional[Dict[str, Any]] = None

    # Audit
    created_by_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    version: int = 1

    class Config:
        from_attributes = True


class ContractListItem(BaseModel):
    """Abbreviated contract for list views."""
    id: int
    contract_number: str
    title: str
    status: str
    contractor_name: Optional[str] = None
    total_amount: int
    paid_amount: int = 0
    created_at: Optional[str] = None


class ContractListResponse(BaseModel):
    """GET /contracts — paginated list."""
    items: List[ContractListItem]
    total: int
    page: int
    limit: int


class ContractRenderResponse(BaseModel):
    """GET /contracts/{id}/render — merged schema + data for frontend form."""
    contract_id: int
    contract_number: str
    status: str
    template_id: int
    template_code: str
    template_title: str
    schema_definition: Dict[str, Any]
    default_values: Optional[Dict[str, Any]] = None
    current_data: Optional[Dict[str, Any]] = None
