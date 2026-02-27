"""
Pydantic Schemas for Contractor CRUD (Phase 2)
===============================================

Covers: creation, response, list views, and Setad lookup results.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


# ============================================================
# Request Schemas
# ============================================================

class ContractorCreate(BaseModel):
    """POST /contractors - create a new contractor record."""
    national_id: str = Field(..., min_length=1, description="National ID")
    company_name: str = Field(..., min_length=1, description="Company name")
    registration_number: Optional[str] = Field(None, description="Registration number")
    ceo_name: Optional[str] = Field(None, description="CEO name")
    phone: Optional[str] = Field(None, description="Phone number")
    address: Optional[str] = Field(None, description="Address")

    # Contractor onboarding fields
    corporate_id: Optional[str] = Field(None, description="Corporate national ID")
    economic_code: Optional[str] = Field(None, description="Economic code")
    postal_code: Optional[str] = Field(None, description="Postal code")
    province: Optional[str] = Field(None, description="Province")
    city: Optional[str] = Field(None, description="City")
    bank_name: Optional[str] = Field(None, description="Bank name")
    account_number: Optional[str] = Field(None, description="Bank account number")
    iban: Optional[str] = Field(None, description="IBAN")

    setad_ref_id: Optional[str] = Field(None, description="Setad reference ID")
    source_system: str = Field("MANUAL", description="MANUAL | SETAD")


class ContractorSetadFetch(BaseModel):
    """POST /contractors/fetch-from-setad - lookup contractor by national ID."""
    national_id: str = Field(..., min_length=1, description="National ID")


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

    # Contractor onboarding fields
    corporate_id: Optional[str] = None
    economic_code: Optional[str] = None
    postal_code: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    iban: Optional[str] = None

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
    """GET /contractors - paginated list."""
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
