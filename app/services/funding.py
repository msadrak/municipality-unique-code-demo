from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import List, Optional
from datetime import datetime

from app.models import FundingRequest, FundingRequestStatus
from app.schemas.funding import FundingRequestCreate, FundingRequestUpdate

def create_funding_request(db: Session, request_in: FundingRequestCreate, user_id: int) -> FundingRequest:
    # Generate tracking number (e.g., HR-1403-XYZ)
    # Simple logic: HR-{year}-{id}
    # We will get the next ID roughly by counting or max ID
    from sqlalchemy import func
    max_id = db.query(func.max(FundingRequest.id)).scalar() or 0
    next_id = max_id + 1
    
    # We use Jalali calendar year normally, but for demo we can hardcode 1403 or use a quick heuristic
    current_year = 1403
    tracking_number = f"HR-{current_year}-{next_id:04d}"
    
    db_obj = FundingRequest(
        title=request_in.title,
        amount=request_in.amount,
        description=request_in.description,
        tracking_number=tracking_number,
        status=FundingRequestStatus.DRAFT,
        created_by_id=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_funding_request(db: Session, request_id: int) -> Optional[FundingRequest]:
    return db.query(FundingRequest).filter(FundingRequest.id == request_id).first()

def list_funding_requests(db: Session, skip: int = 0, limit: int = 100) -> List[FundingRequest]:
    return db.query(FundingRequest).order_by(FundingRequest.id.desc()).offset(skip).limit(limit).all()

def list_my_funding_requests(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[FundingRequest]:
    return db.query(FundingRequest).filter(FundingRequest.created_by_id == user_id).order_by(FundingRequest.id.desc()).offset(skip).limit(limit).all()

def update_funding_request(db: Session, request_id: int, update_data: FundingRequestUpdate, user_id: int) -> FundingRequest:
    db_obj = get_funding_request(db, request_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="درخواست یافت نشد")
        
    # Optional logic: only creator or admin can update
    # and only if in DRAFT state (for editing content)
    
    if update_data.title is not None:
        db_obj.title = update_data.title
    if update_data.amount is not None:
        db_obj.amount = update_data.amount
    if update_data.description is not None:
        db_obj.description = update_data.description
        
    db_obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_obj)
    return db_obj

def transition_status(db: Session, request_id: int, new_status: FundingRequestStatus, user_id: int) -> FundingRequest:
    db_obj = get_funding_request(db, request_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="درخواست یافت نشد")
        
    db_obj.status = new_status
    db_obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_obj)
    return db_obj
