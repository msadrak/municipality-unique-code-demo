"""
Subsystems Router - Subsystem and activity management
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models
from app.routers.auth import get_db

router = APIRouter(prefix="/portal", tags=["Subsystems"])

@router.get("/subsystems")
def get_subsystems(db: Session = Depends(get_db)):
    """Get all active subsystems (14 سامانه)"""
    subsystems = db.query(models.Subsystem).filter(models.Subsystem.is_active == True).order_by(models.Subsystem.order).all()
    return {"count": len(subsystems), "subsystems": [{"id": s.id, "code": s.code, "title": s.title, "icon": s.icon, "attachment_type": s.attachment_type, "order": s.order} for s in subsystems]}

@router.get("/subsystems/{subsystem_id}/activities")
def get_subsystem_activities(subsystem_id: int, db: Session = Depends(get_db)):
    """Get activities for a specific subsystem"""
    subsystem = db.query(models.Subsystem).filter(models.Subsystem.id == subsystem_id).first()
    if not subsystem:
        raise HTTPException(status_code=404, detail="سامانه یافت نشد")
    
    activities = db.query(models.SubsystemActivity).filter(models.SubsystemActivity.subsystem_id == subsystem_id, models.SubsystemActivity.is_active == True).order_by(models.SubsystemActivity.order).all()
    return {"subsystem": {"id": subsystem.id, "code": subsystem.code, "title": subsystem.title}, "count": len(activities), "activities": [{"id": a.id, "code": a.code, "title": a.title, "form_type": a.form_type} for a in activities]}

@router.get("/subsystems/for-section/{section_id}")
def get_subsystems_for_section(section_id: int, db: Session = Depends(get_db)):
    """Get subsystems accessible by a specific section"""
    mappings = db.query(models.SectionSubsystemAccess).filter(models.SectionSubsystemAccess.section_id == section_id).all()
    
    if mappings:
        subsystem_ids = [m.subsystem_id for m in mappings]
        subsystems = db.query(models.Subsystem).filter(models.Subsystem.id.in_(subsystem_ids), models.Subsystem.is_active == True).order_by(models.Subsystem.order).all()
    else:
        subsystems = db.query(models.Subsystem).filter(models.Subsystem.is_active == True).order_by(models.Subsystem.order).all()
    
    return {"section_id": section_id, "count": len(subsystems), "subsystems": [{"id": s.id, "code": s.code, "title": s.title, "icon": s.icon, "attachment_type": s.attachment_type} for s in subsystems]}
