"""
Contractor Router - Phase 2
============================

Provides CRUD endpoints for contractor management.
Integrates with Setad (mock/live) via the ACL layer.

Endpoints:
  GET  /contractors         — List contractors from local DB
  GET  /contractors/{id}    — Contractor detail
  POST /contractors         — Create local contractor record
  POST /contractors/fetch-from-setad  — Fetch from Setad by national ID
  GET  /contractors/search-setad      — Search Setad by query string
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.models import Contractor
from app.schemas.contractor import (
    ContractorCreate,
    ContractorSetadFetch,
    ContractorResponse,
    ContractorListItem,
    ContractorListResponse,
    SetadContractorInfo,
    SetadSearchResponse,
)
from app.routers.auth import get_current_user, get_db
from app.integrations import get_setad_port

router = APIRouter(prefix="/contractors", tags=["Contractors"])


# ============================================================
# Helpers
# ============================================================

def _require_auth(request: Request, db: Session):
    """Get authenticated user or raise 401."""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    return user


def _contractor_to_response(c: Contractor) -> ContractorResponse:
    """Convert Contractor ORM model to Pydantic response."""
    return ContractorResponse(
        id=c.id,
        national_id=c.national_id,
        company_name=c.company_name,
        registration_number=c.registration_number,
        ceo_name=c.ceo_name,
        phone=c.phone,
        address=c.address,
        setad_ref_id=c.setad_ref_id,
        source_system=c.source_system or "MANUAL",
        is_verified=c.is_verified or False,
        portal_enabled=c.portal_enabled or False,
        created_at=c.created_at.strftime("%Y/%m/%d %H:%M") if c.created_at else None,
        updated_at=c.updated_at.strftime("%Y/%m/%d %H:%M") if c.updated_at else None,
    )


def _contractor_to_list_item(c: Contractor) -> ContractorListItem:
    """Convert Contractor ORM model to list item."""
    return ContractorListItem(
        id=c.id,
        national_id=c.national_id,
        company_name=c.company_name,
        ceo_name=c.ceo_name,
        source_system=c.source_system or "MANUAL",
        is_verified=c.is_verified or False,
        created_at=c.created_at.strftime("%Y/%m/%d %H:%M") if c.created_at else None,
    )


# ============================================================
# GET /contractors — list from local DB
# ============================================================

@router.get("", response_model=ContractorListResponse)
def list_contractors(
    request: Request,
    search: Optional[str] = Query(None, description="Search by name or national ID"),
    verified_only: bool = Query(False, description="Show only verified contractors"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List contractors from local database."""
    _require_auth(request, db)
    
    query = db.query(Contractor)
    
    if search:
        query = query.filter(
            (Contractor.company_name.ilike(f"%{search}%")) |
            (Contractor.national_id.ilike(f"%{search}%"))
        )
    if verified_only:
        query = query.filter(Contractor.is_verified == True)
    
    total = query.count()
    offset = (page - 1) * limit
    contractors = query.order_by(Contractor.created_at.desc()).offset(offset).limit(limit).all()
    
    items = [_contractor_to_list_item(c) for c in contractors]
    return ContractorListResponse(items=items, total=total, page=page, limit=limit)


# ============================================================
# GET /contractors/{id} — detail
# ============================================================

@router.get("/{contractor_id}", response_model=ContractorResponse)
def get_contractor(
    contractor_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get contractor detail by ID."""
    _require_auth(request, db)
    
    contractor = db.query(Contractor).filter(Contractor.id == contractor_id).first()
    if not contractor:
        raise HTTPException(status_code=404, detail="پیمانکار یافت نشد")
    
    return _contractor_to_response(contractor)


# ============================================================
# POST /contractors — create local record
# ============================================================

@router.post("", response_model=ContractorResponse)
def create_contractor(
    data: ContractorCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new contractor record in local database."""
    _require_auth(request, db)
    
    # Check for duplicate national_id
    existing = db.query(Contractor).filter(
        Contractor.national_id == data.national_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"پیمانکار با کد ملی {data.national_id} قبلاً ثبت شده است"
        )
    
    contractor = Contractor(
        national_id=data.national_id,
        company_name=data.company_name,
        registration_number=data.registration_number,
        ceo_name=data.ceo_name,
        phone=data.phone,
        address=data.address,
        setad_ref_id=data.setad_ref_id,
        source_system=data.source_system,
    )
    db.add(contractor)
    db.commit()
    db.refresh(contractor)
    
    return _contractor_to_response(contractor)


# ============================================================
# POST /contractors/fetch-from-setad — fetch from mock Setad
# ============================================================

@router.post("/fetch-from-setad", response_model=ContractorResponse)
def fetch_from_setad(
    data: ContractorSetadFetch,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Fetch contractor from Setad by national ID and create local record.
    
    If the contractor already exists locally, returns the existing record.
    If found in Setad (mock), creates a new local record with source_system=SETAD.
    """
    _require_auth(request, db)
    
    # Check if already exists locally
    existing = db.query(Contractor).filter(
        Contractor.national_id == data.national_id
    ).first()
    if existing:
        return _contractor_to_response(existing)
    
    # Fetch from Setad (mock or real via ACL)
    setad = get_setad_port()
    info = setad.get_by_national_id(data.national_id)
    
    if not info:
        raise HTTPException(
            status_code=404,
            detail=f"پیمانکار با کد ملی {data.national_id} در سامانه ستاد یافت نشد"
        )
    
    # Create local record from Setad data
    contractor = Contractor(
        national_id=info.national_id,
        company_name=info.company_name,
        registration_number=info.registration_number,
        ceo_name=info.ceo_name,
        phone=info.phone,
        address=info.address,
        setad_ref_id=info.setad_ref_id,
        source_system="SETAD",
        is_verified=info.is_verified,
    )
    db.add(contractor)
    db.commit()
    db.refresh(contractor)
    
    return _contractor_to_response(contractor)


# ============================================================
# GET /contractors/search-setad — search Setad
# ============================================================

@router.get("/search-setad", response_model=SetadSearchResponse)
def search_setad(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query (name or national ID)"),
    db: Session = Depends(get_db),
):
    """Search contractors in Setad system (mock or real via ACL)."""
    _require_auth(request, db)
    
    setad = get_setad_port()
    results = setad.search_contractors(q)
    
    items = [
        SetadContractorInfo(
            national_id=r.national_id,
            company_name=r.company_name,
            registration_number=r.registration_number,
            ceo_name=r.ceo_name,
            phone=r.phone,
            address=r.address,
            setad_ref_id=r.setad_ref_id,
            is_verified=r.is_verified,
        )
        for r in results
    ]
    
    return SetadSearchResponse(results=items)
