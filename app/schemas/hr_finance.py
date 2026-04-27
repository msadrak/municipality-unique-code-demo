from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class HRFinanceAllocationLineIn(BaseModel):
    org_unit_name: str = Field(..., min_length=1, max_length=255)
    cost_center_code: str = Field(..., min_length=1, max_length=64)
    budget_line_code: str = Field(..., min_length=1, max_length=64)
    financial_event_type: str = Field(..., min_length=1, max_length=128)
    allocated_amount: Decimal = Field(..., gt=0)
    legal_deductions: Decimal = Field(default=Decimal("0"), ge=0)
    penalties: Decimal = Field(default=Decimal("0"), ge=0)
    net_amount: Decimal | None = Field(default=None, ge=0)


class HRFinanceFinalizeRequest(BaseModel):
    allocations: list[HRFinanceAllocationLineIn] = Field(..., min_length=1)


class HRFinanceTransactionInfoOut(BaseModel):
    id: int
    status: str
    gross_amount: int | None = None
    activity_id: int | None = None
    activity_name: str | None = None
    contract_number: str | None = None


class HRFinanceDateRangeOut(BaseModel):
    start: str
    end: str


class HRFinanceOperationalContextOut(BaseModel):
    work_period_id: int
    name: str
    year: int
    month: int
    date_range: HRFinanceDateRangeOut
    contractor_name: str | None = None
    contract_number: str | None = None


class HRFinanceFinancialRulesOut(BaseModel):
    cost_center_code: str
    budget_line_code: str
    financial_event_type: str


class HRFinanceAllocationLineOut(BaseModel):
    id: int
    org_unit_name: str
    cost_center_code: str
    budget_line_code: str
    financial_event_type: str
    allocated_amount: float
    legal_deductions: float
    penalties: float
    net_amount: float
    unique_code: str | None = None


class GeneratedHRTransactionCodeOut(BaseModel):
    region: str
    code: str


class HRFinanceWorkflowContextOut(BaseModel):
    transaction: HRFinanceTransactionInfoOut
    operational_context: HRFinanceOperationalContextOut
    financial_rules: HRFinanceFinancialRulesOut
    allocation_lines: list[HRFinanceAllocationLineOut] | None = None
