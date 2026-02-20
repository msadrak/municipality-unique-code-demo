"""
Pydantic Schemas for Contractor CRUD (Phase 2)
===============================================

Covers: creation, response, list views, and Setad lookup results.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============================================================
# Request Schemas
# ============================================================

class ContractorCreate(BaseModel):
    """POST /contractors — create a new contractor record."""
    national_id: str = Field(..., min_length=1, description="کد ملی / شناسه ملی")
    company_name: str = Field(..., min_length=1, description="نام شرکت")
    registration_number: Optional[str] = Field(None, description="شماره ثبت")
    ceo_name: Optional[str] = Field(None, description="نام مدیرعامل")
    phone: Optional[str] = Field(None, description="تلفن")
    address: Optional[str] = Field(None, description="آدرس")
    setad_ref_id: Optional[str] = Field(None, description="شناسه سامانه ستاد")
    source_system: str = Field("MANUAL", description="MANUAL | SETAD")


class ContractorSetadFetch(BaseModel):
    """POST /contractors/fetch-from-setad — lookup contractor by national ID."""
    national_id: str = Field(..., min_length=1, description="کد ملی برای جستجو در ستاد")


# ============================================================
# Response Schemas
# ============================================================

class ContractorResponse(BaseModel):
    """Full contractor detail."""
    id: int
    national_id: str
    company_name: str
    registration_number: Optional[str] = None
    ceo_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    setad_ref_id: Optional[str] = None
    source_system: str
    is_verified: bool
    portal_enabled: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class ContractorListItem(BaseModel):
    """Abbreviated contractor for list views."""
    id: int
    national_id: str
    company_name: str
    ceo_name: Optional[str] = None
    source_system: str
    is_verified: bool
    created_at: Optional[str] = None


class ContractorListResponse(BaseModel):
    """GET /contractors — paginated list."""
    items: List[ContractorListItem]
    total: int
    page: int
    limit: int


class SetadContractorInfo(BaseModel):
    """Data returned from Setad lookup (mock or real)."""
    national_id: str
    company_name: str
    registration_number: Optional[str] = None
    ceo_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    setad_ref_id: Optional[str] = None
    is_verified: bool = False


class SetadSearchResponse(BaseModel):
    """Response for Setad contractor search."""
    results: List[SetadContractorInfo]
    source: str = "SETAD_MOCK"
