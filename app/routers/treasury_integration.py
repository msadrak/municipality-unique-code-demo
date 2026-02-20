"""
Treasury Integration Router
============================

Provides API endpoint for external Treasury System (Samaneh Khazaneh-dari).
Exports transaction data in the exact format required by the Treasury.

Endpoint: GET /api/v1/treasury/export

Output Format:
[
  {
    "code_yekta": "20-02-015-11020401-001-01-000-A1B2C3-001-1403-001",
    "amount": 10000000,
    "submission_date": "2025-01-29",
    "financial_event": {
      "id": 1,
      "name": "تامین اعتبار"
    },
    "activity": {
      "id": 1,
      "name": "پرداخت حقوق"
    }
  }
]

Data Mapping:
- code_yekta: Transaction.unique_code
- amount: Transaction.amount
- submission_date: Transaction.reviewed_at (approval date) or created_at
- financial_event: Transaction.financial_event (FinancialEventRef)
- activity: Transaction.subsystem_activity (SubsystemActivity) via budget_row relationship
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import SessionLocal
from app.models import Transaction, FinancialEventRef, SubsystemActivity, BudgetRow
from app.routers.auth import get_current_user


router = APIRouter(prefix="/api/v1/treasury", tags=["Treasury Integration"])


# ============ Response Schemas ============

class FinancialEventSchema(BaseModel):
    """Financial Event object for Treasury"""
    id: int
    name: str
    
    class Config:
        from_attributes = True


class ActivitySchema(BaseModel):
    """Activity object for Treasury"""
    id: int
    name: str
    
    class Config:
        from_attributes = True


class TreasuryTransactionSchema(BaseModel):
    """Single transaction record for Treasury System"""
    code_yekta: str
    amount: float
    submission_date: str  # ISO format YYYY-MM-DD
    financial_event: FinancialEventSchema
    activity: ActivitySchema
    
    class Config:
        from_attributes = True


# ============ Database Dependency ============

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============ API Endpoint ============

@router.get("/export", response_model=List[TreasuryTransactionSchema])
def export_transactions_for_treasury(
    request: Request,
    status: str = Query("APPROVED", description="Transaction status filter (APPROVED, POSTED, ALL)"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    zone_id: Optional[int] = Query(None, description="Filter by zone/region ID"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of records"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    """
    Export approved transactions for Treasury System (Samaneh Khazaneh-dari)
    
    **Authentication:** Requires admin or accountant role
    
    **Query Parameters:**
    - status: APPROVED (default), POSTED, or ALL
    - date_from: Filter by approval date (YYYY-MM-DD)
    - date_to: Filter by approval date (YYYY-MM-DD)
    - zone_id: Filter by organizational zone
    - limit: Max records (default 1000, max 10000)
    - offset: Pagination offset
    
    **Returns:**
    Array of transaction objects with:
    - code_yekta: Unique transaction code
    - amount: Transaction amount (Rials)
    - submission_date: Approval/process date
    - financial_event: Object with id and name
    - activity: Object with id and name
    """
    
    # Authentication check
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است - Authentication required")
    
    # Authorization check (only admin, accountant, or inspector roles)
    allowed_roles = ["admin", "ACCOUNTANT", "ADMIN_L4", "ADMIN_L3", "ADMIN_L2", "ADMIN_L1", "inspector"]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=403, 
            detail=f"دسترسی مجاز نیست - Access denied. Required roles: {allowed_roles}"
        )
    
    # Build query with eager loading
    query = db.query(Transaction).options(
        joinedload(Transaction.financial_event),
        joinedload(Transaction.subsystem_activity)
    )
    
    # Status filter
    if status == "APPROVED":
        query = query.filter(Transaction.status == "APPROVED")
    elif status == "POSTED":
        # Include both APPROVED and transactions with accounting_status = POSTED
        query = query.filter(
            (Transaction.status == "APPROVED") | (Transaction.status == "BOOKED")
        )
    elif status != "ALL":
        query = query.filter(Transaction.status == status)
    
    # Date range filter (use reviewed_at for approval date)
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Transaction.reviewed_at >= date_from_obj)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date format for date_from: {date_from}. Use YYYY-MM-DD")
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(Transaction.reviewed_at <= date_to_obj)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date format for date_to: {date_to}. Use YYYY-MM-DD")
    
    # Zone filter
    if zone_id:
        query = query.filter(Transaction.zone_id == zone_id)
    
    # Order by approval date (most recent first)
    query = query.order_by(Transaction.reviewed_at.desc())
    
    # Pagination
    query = query.offset(offset).limit(limit)
    
    # Execute query
    transactions = query.all()
    
    # Transform to Treasury format
    result = []
    for tx in transactions:
        # Skip transactions without required fields
        if not tx.unique_code:
            continue
        
        # Get submission_date (prefer reviewed_at, fallback to created_at)
        submission_date = tx.reviewed_at or tx.created_at
        if not submission_date:
            submission_date = datetime.utcnow()
        
        # Format date as YYYY-MM-DD
        submission_date_str = submission_date.strftime("%Y-%m-%d")
        
        # Get financial_event (required)
        if not tx.financial_event:
            # If missing, use default placeholder
            financial_event = FinancialEventSchema(
                id=0,
                name="رویداد مالی نامشخص"
            )
        else:
            financial_event = FinancialEventSchema(
                id=tx.financial_event.id,
                name=tx.financial_event.title
            )
        
        # Get activity (required)
        # First try direct subsystem_activity relationship
        if tx.subsystem_activity:
            activity = ActivitySchema(
                id=tx.subsystem_activity.id,
                name=tx.subsystem_activity.title
            )
        else:
            # Fallback: Use placeholder
            activity = ActivitySchema(
                id=0,
                name="فعالیت نامشخص"
            )
        
        # Create treasury record
        treasury_record = TreasuryTransactionSchema(
            code_yekta=tx.unique_code,
            amount=tx.amount or 0.0,
            submission_date=submission_date_str,
            financial_event=financial_event,
            activity=activity
        )
        
        result.append(treasury_record)
    
    return result


@router.get("/export/summary")
def get_export_summary(
    request: Request,
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for Treasury export
    
    **Returns:**
    - total_transactions: Total count of exportable transactions
    - total_amount: Sum of all transaction amounts
    - date_range: Actual date range of data
    - zones_count: Number of unique zones/regions
    """
    
    # Authentication
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    
    # Build base query
    query = db.query(Transaction).filter(Transaction.status == "APPROVED")
    
    # Apply date filters
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Transaction.reviewed_at >= date_from_obj)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date_from: {date_from}")
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(Transaction.reviewed_at <= date_to_obj)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date_to: {date_to}")
    
    # Get transactions
    transactions = query.all()
    
    # Calculate statistics
    total_transactions = len(transactions)
    total_amount = sum(tx.amount or 0 for tx in transactions)
    
    # Get unique zones
    unique_zones = set(tx.zone_id for tx in transactions if tx.zone_id)
    zones_count = len(unique_zones)
    
    # Get date range
    dates = [tx.reviewed_at or tx.created_at for tx in transactions if tx.reviewed_at or tx.created_at]
    min_date = min(dates).strftime("%Y-%m-%d") if dates else None
    max_date = max(dates).strftime("%Y-%m-%d") if dates else None
    
    return {
        "total_transactions": total_transactions,
        "total_amount": total_amount,
        "date_range": {
            "from": min_date,
            "to": max_date
        },
        "zones_count": zones_count,
        "status": "success"
    }


@router.get("/health")
def treasury_api_health():
    """
    Health check endpoint for Treasury Integration API
    
    **Returns:**
    - status: API status
    - timestamp: Current server time
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Treasury Integration API",
        "version": "1.0.0"
    }
