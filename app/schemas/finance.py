from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FinancialMatrixBase(BaseModel):
    budget_line_level_5: str = Field(..., min_length=1, max_length=64)
    cost_center: str = Field(..., min_length=1, max_length=128)
    financial_event: str = Field(..., min_length=1, max_length=128)
    activity_name: str = Field(..., min_length=1, max_length=255)
    is_active: bool = True


class FinancialMatrixCreate(FinancialMatrixBase):
    pass


class FinancialMatrixUpdate(BaseModel):
    budget_line_level_5: str | None = Field(None, min_length=1, max_length=64)
    cost_center: str | None = Field(None, min_length=1, max_length=128)
    financial_event: str | None = Field(None, min_length=1, max_length=128)
    activity_name: str | None = Field(None, min_length=1, max_length=255)
    is_active: bool | None = None


class FinancialMatrixOut(FinancialMatrixBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FinancialMatrixYektaCodeRequest(BaseModel):
    budget_line_level_5: str = Field(..., min_length=1, max_length=64)
    cost_center: str = Field(..., min_length=1, max_length=128)
    financial_event: str = Field(..., min_length=1, max_length=128)
    activity_name: str = Field(..., min_length=1, max_length=255)
    sequence: int = Field(default=1, ge=1)


class FinancialMatrixYektaCodeOut(BaseModel):
    yekta_code: str


__all__ = [
    "FinancialMatrixCreate",
    "FinancialMatrixOut",
    "FinancialMatrixUpdate",
    "FinancialMatrixYektaCodeOut",
    "FinancialMatrixYektaCodeRequest",
]
