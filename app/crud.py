from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas
import uuid

# --------------------------------------------------------
# Resolver Logic (هوش مصنوعی سیستم)
# --------------------------------------------------------

def resolve_org_unit(db: Session, hint: schemas.OrgHint) -> models.OrgUnit:
    if not hint.zone_title and not hint.zone_code:
        return None

    query = db.query(models.OrgUnit).filter(models.OrgUnit.parent_id == None)
    
    if hint.zone_code:
        query = query.filter(models.OrgUnit.code == hint.zone_code)
    elif hint.zone_title:
        query = query.filter(models.OrgUnit.title.ilike(f"%{hint.zone_title}%"))
    
    root_unit = query.first()
    
    if not root_unit:
        return None

    current_unit = root_unit

    if hint.department_title:
        dept = db.query(models.OrgUnit).filter(
            models.OrgUnit.parent_id == current_unit.id,
            models.OrgUnit.title.ilike(f"%{hint.department_title}%")
        ).first()
        
        if dept:
            current_unit = dept

    if hint.section_title:
        section = db.query(models.OrgUnit).filter(
            models.OrgUnit.parent_id == current_unit.id,
            models.OrgUnit.title.ilike(f"%{hint.section_title}%")
        ).first()
        
        if section:
            current_unit = section

    return current_unit

def get_or_create_financial_type(db: Session, title: str):
    if not title: title = "نامشخص"
    obj = db.query(models.FinancialEventType).filter_by(title=title).first()
    if not obj:
        obj = models.FinancialEventType(title=title)
        db.add(obj)
        db.commit()
        db.refresh(obj)
    return obj

# --------------------------------------------------------
# Main CRUD Operation
# --------------------------------------------------------

def create_special_action(db: Session, payload: schemas.ExternalSpecialActionPayload):
    # 1. پیدا کردن واحد سازمانی
    org_unit = None
    
    if payload.org_unit_full_code:
        org_unit = db.query(models.OrgUnit).filter_by(full_code=payload.org_unit_full_code).first()
    elif payload.org_hint:
        org_unit = resolve_org_unit(db, payload.org_hint)
    
    # اگر پیدا نشد، یک واحد پیش‌فرض (اولین واحد موجود) را بگذاریم
    if not org_unit:
        org_unit = db.query(models.OrgUnit).first()
        
    if not org_unit:
        # اگر دیتابیس خالی است و هیچ واحدی نیست
        raise ValueError("واحد سازمانی یافت نشد و دیتابیس خالی است. ابتدا seed.py را اجرا کنید.")

    # 2. مدیریت Continuous Action
    cont_action_id = None
    if payload.continuous_action_code:
        ca = db.query(models.ContinuousAction).filter_by(code=payload.continuous_action_code).first()
        if ca: cont_action_id = ca.id

    # 3. مدیریت Action Type
    act_type_id = None
    if payload.action_type_code:
        at = db.query(models.ActionType).filter_by(code=payload.action_type_code).first()
        if at: act_type_id = at.id

    # 4. مدیریت Financial Type
    fin_type = get_or_create_financial_type(db, payload.financial_event_title)

    # 5. تولید کد یکتا
    # اگر کد یونیک از سمت آداپتر آمده بود (local_record_id) همان را استفاده می‌کنیم
    # اگر نه، یک چیزی می‌سازیم. اینجا فرض می‌کنیم local_record_id همان کد نهایی است.
    base_code = org_unit.code if org_unit.code else str(org_unit.id)
    # اگر local_record_id خودش فرمت کامل دارد، همان را استفاده کن، وگرنه ترکیب کن
    generated_unique_code = payload.local_record_id 

    # 6. ذخیره در دیتابیس
    db_obj = models.SpecialAction(
        org_unit_id=org_unit.id,
        continuous_action_id=cont_action_id,
        action_type_id=act_type_id,
        financial_event_type_id=fin_type.id,
        
        unique_code=generated_unique_code,
        amount=payload.amount,
        local_record_id=payload.local_record_id,
        description=payload.description,
        action_date=payload.action_date,  # <--- اینجا ویرگول گذاشتم
        
        details=payload.details 
    )
    
    # Upsert (اگر تکراری بود، خطا نده)
    try:
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
    except Exception:
        db.rollback()
        # اگر تکراری بود، رکورد قبلی را برگردان (یا می‌توانیم آپدیت کنیم)
        existing = db.query(models.SpecialAction).filter_by(unique_code=generated_unique_code).first()
        if existing:
            return existing
        else:
            raise

    return db_obj