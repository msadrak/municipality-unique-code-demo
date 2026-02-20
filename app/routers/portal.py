"""
Portal Router - User-facing transaction and dashboard endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import hashlib
from app import models, schemas
from app.routers.auth import get_current_user, get_db

router = APIRouter(prefix="/portal", tags=["Portal"])

def get_section_activities(db: Session, subsystem_id: int, section_id: Optional[int]):
    """Return activities filtered by section (micro-segmentation)."""
    query = db.query(models.SubsystemActivity).filter(
        models.SubsystemActivity.subsystem_id == subsystem_id,
        models.SubsystemActivity.is_active == True
    )

    if section_id:
        query = query.join(
            models.BudgetRow,
            models.BudgetRow.activity_id == models.SubsystemActivity.id
        ).filter(models.BudgetRow.org_unit_id == section_id).distinct()

    return query.order_by(models.SubsystemActivity.order).all()

class CreateTransactionRequest(BaseModel):
    credit_request_id: Optional[int] = None  # Stage 1 Gateway: required for new creates
    zone_id: int
    department_id: Optional[int] = None
    section_id: Optional[int] = None
    budget_code: str
    cost_center_code: Optional[str] = "000"
    continuous_activity_code: Optional[str] = "00"
    special_activity: Optional[str] = ""
    financial_event_code: Optional[str] = "000"
    beneficiary_name: str
    contract_number: Optional[str] = "0000"
    amount: float
    description: Optional[str] = ""
    form_data: Optional[dict] = None

@router.post("/transactions/create")
def create_transaction(data: CreateTransactionRequest, request: Request, db: Session = Depends(get_db)):
    """Create a new transaction"""
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    
    # ========== STAGE 1 GATEWAY ENFORCEMENT ==========
    # credit_request_id is required for all new transaction creations.
    # Legacy rows (credit_request_id IS NULL) are grandfathered at DB level.
    if not data.credit_request_id:
        raise HTTPException(
            status_code=409,
            detail="درخواست تامین اعتبار تایید شده الزامی است. لطفاً ابتدا درخواست تامین اعتبار ایجاد کنید."
        )
    
    cr = db.query(models.CreditRequest).filter(
        models.CreditRequest.id == data.credit_request_id
    ).first()
    if not cr:
        raise HTTPException(status_code=404, detail="درخواست تامین اعتبار یافت نشد")
    
    cr_status = cr.status.value if hasattr(cr.status, 'value') else cr.status
    if cr_status != "APPROVED":
        raise HTTPException(
            status_code=403,
            detail=f"درخواست تامین اعتبار در وضعیت {cr_status} قابل استفاده نیست (فقط APPROVED)"
        )
    
    # Single-use enforcement: check if CR is already consumed
    if cr.used_transaction_id is not None:
        raise HTTPException(
            status_code=409,
            detail="این درخواست تامین اعتبار قبلاً مصرف شده است. لطفاً درخواست جدید ایجاد کنید."
        )
    
    # Org context compatibility
    if cr.zone_id != data.zone_id:
        raise HTTPException(
            status_code=422,
            detail="منطقه تراکنش با درخواست تامین اعتبار مطابقت ندارد"
        )
    if cr.department_id is not None and cr.department_id != data.department_id:
        raise HTTPException(
            status_code=422,
            detail="اداره تراکنش با درخواست تامین اعتبار مطابقت ندارد"
        )
    if cr.section_id is not None and cr.section_id != data.section_id:
        raise HTTPException(
            status_code=422,
            detail="قسمت تراکنش با درخواست تامین اعتبار مطابقت ندارد"
        )
    
    # Budget code match (string match for Stage 1)
    if cr.budget_code != data.budget_code:
        raise HTTPException(
            status_code=422,
            detail="کد بودجه تراکنش با درخواست تامین اعتبار مطابقت ندارد"
        )
    
    # Amount ceiling
    if data.amount > cr.amount_approved:
        raise HTTPException(
            status_code=422,
            detail=f"مبلغ تراکنش ({data.amount:,.0f}) بیشتر از سقف تامین اعتبار ({cr.amount_approved:,.0f}) است"
        )
    # ========== END STAGE 1 GATEWAY ENFORCEMENT ==========
    
    zone = db.query(models.OrgUnit).filter(models.OrgUnit.id == data.zone_id).first()
    dept = db.query(models.OrgUnit).filter(models.OrgUnit.id == data.department_id).first() if data.department_id else None
    section = db.query(models.OrgUnit).filter(models.OrgUnit.id == data.section_id).first() if data.section_id else None
    
    zone_code = (zone.code or str(data.zone_id)).zfill(2) if zone else "00"
    dept_code = (dept.code or "00").zfill(2) if dept else "00"
    section_code = (section.code or "000").zfill(3) if section else "000"
    budget_code = data.budget_code.zfill(4)
    cost_center = (data.cost_center_code or "000").zfill(3)
    cont_act = (data.continuous_activity_code or "00").zfill(2)
    spec_act_hash = hashlib.md5(data.special_activity.encode()).hexdigest()[:3].upper() if data.special_activity else "000"
    ben_hash = hashlib.md5((data.beneficiary_name.strip() or "Unknown").encode()).hexdigest()[:6].upper()
    fin_event = (data.financial_event_code or "000").zfill(3)
    date_code = "1403"
    
    existing_prefix = f"{zone_code}-{dept_code}-{section_code}-{budget_code}"
    count_query = db.query(models.Transaction).filter(models.Transaction.unique_code.like(f"{existing_prefix}%")).count()
    occurrence = str(count_query + 1).zfill(3)
    
    unique_code = f"{zone_code}-{dept_code}-{section_code}-{budget_code}-{cost_center}-{cont_act}-{spec_act_hash}-{ben_hash}-{fin_event}-{date_code}-{occurrence}"
    
    budget_item = db.query(models.BudgetItem).filter(models.BudgetItem.budget_code == data.budget_code).first()
    if budget_item:
        remaining = (budget_item.remaining_budget or budget_item.allocated_1403 or 0) - (budget_item.reserved_amount or 0)
        if remaining < data.amount:
            raise HTTPException(status_code=400, detail=f"بودجه کافی نیست. مانده: {remaining:,.0f} ریال")
        budget_item.reserved_amount = (budget_item.reserved_amount or 0) + data.amount
    
    cost_center_ref = db.query(models.CostCenterRef).filter(models.CostCenterRef.code == data.cost_center_code).first()
    cont_action = db.query(models.ContinuousAction).filter(models.ContinuousAction.code == data.continuous_activity_code).first()
    fin_event_ref = db.query(models.FinancialEventRef).filter(models.FinancialEventRef.code == data.financial_event_code).first()
    
    transaction = models.Transaction(unique_code=unique_code, status="PENDING_L1", current_approval_level=0, created_by_id=current_user.id, zone_id=data.zone_id, department_id=data.department_id, section_id=data.section_id, credit_request_id=data.credit_request_id, budget_item_id=budget_item.id if budget_item else None, cost_center_id=cost_center_ref.id if cost_center_ref else None, continuous_action_id=cont_action.id if cont_action else None, financial_event_id=fin_event_ref.id if fin_event_ref else None, amount=data.amount, beneficiary_name=data.beneficiary_name, contract_number=data.contract_number, special_activity=data.special_activity, description=data.description, form_data=data.form_data, fiscal_year="1403")
    db.add(transaction)
    db.flush()
    
    # Mark CR as used (single-use enforcement)
    if data.credit_request_id and cr:
        cr.used_transaction_id = transaction.id
    
    db.commit()
    db.refresh(transaction)
    
    return {"status": "success", "message": "تراکنش با موفقیت ایجاد شد", "transaction_id": transaction.id, "unique_code": unique_code}

@router.get("/my-transactions")
def get_my_transactions(request: Request, db: Session = Depends(get_db)):
    """Get current user's transactions"""
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    
    transactions = db.query(models.Transaction).filter(models.Transaction.created_by_id == current_user.id).order_by(models.Transaction.created_at.desc()).limit(50).all()
    return {"transactions": [{"id": t.id, "unique_code": t.unique_code, "beneficiary_name": t.beneficiary_name, "amount": t.amount, "status": t.status, "rejection_reason": t.rejection_reason, "created_at": t.created_at.strftime("%Y/%m/%d %H:%M") if t.created_at else None} for t in transactions], "count": len(transactions)}

@router.get("/user/allowed-activities")
def get_user_allowed_activities(request: Request, db: Session = Depends(get_db)):
    """Get allowed activities for user based on their section"""
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    
    section_id = current_user.default_section_id
    section = db.query(models.OrgUnit).filter(models.OrgUnit.id == section_id).first() if section_id else None
    
    if section_id:
        mappings = db.query(models.SectionSubsystemAccess).filter(models.SectionSubsystemAccess.section_id == section_id).all()
        if mappings:
            subsystem_ids = [m.subsystem_id for m in mappings]
            subsystems = db.query(models.Subsystem).filter(models.Subsystem.id.in_(subsystem_ids), models.Subsystem.is_active == True).order_by(models.Subsystem.order).all()
        else:
            subsystems = db.query(models.Subsystem).filter(models.Subsystem.is_active == True).order_by(models.Subsystem.order).all()
    else:
        subsystems = db.query(models.Subsystem).filter(models.Subsystem.is_active == True).order_by(models.Subsystem.order).all()
    
    result_subsystems = []
    for s in subsystems:
        activities = get_section_activities(db, s.id, section_id)
        result_subsystems.append({"id": s.id, "code": s.code, "title": s.title, "icon": s.icon, "attachment_type": s.attachment_type, "activities": [{"id": a.id, "code": a.code, "title": a.title, "form_type": a.form_type} for a in activities]})
    
    return {"user": {"id": current_user.id, "full_name": current_user.full_name, "role": current_user.role}, "user_section": {"id": section.id if section else None, "title": section.title if section else None}, "allowed_subsystems": result_subsystems}

@router.get("/dashboard/init", response_model=schemas.DashboardInitResponse)
def get_dashboard_init(request: Request, db: Session = Depends(get_db)):
    """Dashboard initialization - returns all data needed for dashboard and wizard"""
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    
    section = db.query(models.OrgUnit).filter(models.OrgUnit.id == current_user.default_section_id).first() if current_user.default_section_id else None
    zone = db.query(models.OrgUnit).filter(models.OrgUnit.id == current_user.default_zone_id).first() if current_user.default_zone_id else None
    
    user_context = schemas.UserContextSchema(user_id=current_user.id, user_name=current_user.full_name, zone_id=zone.id if zone else None, zone_code=zone.code if zone else None, zone_title=zone.title if zone else None, section_id=section.id if section else None, section_code=section.code if section else None, section_title=section.title if section else None)
    
    if not section:
        user_subsystem_access = db.query(models.UserSubsystemAccess).filter(models.UserSubsystemAccess.user_id == current_user.id).all()
        if user_subsystem_access:
            subsystem = db.query(models.Subsystem).filter(models.Subsystem.id == user_subsystem_access[0].subsystem_id, models.Subsystem.is_active == True).first()
            if subsystem:
                activities = db.query(models.SubsystemActivity).filter(models.SubsystemActivity.subsystem_id == subsystem.id, models.SubsystemActivity.is_active == True).order_by(models.SubsystemActivity.order).all()
                allowed_activities = []
                for activity in activities:
                    constraint = db.query(models.ActivityConstraint).filter(models.ActivityConstraint.subsystem_activity_id == activity.id, models.ActivityConstraint.is_active == True).order_by(models.ActivityConstraint.priority.desc()).first()
                    constraint_schema = schemas.ActivityConstraintSchema(budget_code_pattern=constraint.budget_code_pattern, allowed_budget_types=constraint.allowed_budget_types, cost_center_pattern=constraint.cost_center_pattern, allowed_cost_centers=constraint.allowed_cost_centers, constraint_type=constraint.constraint_type or "INCLUDE") if constraint else None
                    frequency_value = activity.frequency.value if hasattr(activity, 'frequency') and activity.frequency and hasattr(activity.frequency, 'value') else str(activity.frequency) if hasattr(activity, 'frequency') and activity.frequency else None
                    allowed_activities.append(schemas.AllowedActivitySchema(id=activity.id, code=activity.code, title=activity.title, form_type=activity.form_type, frequency=frequency_value, requires_file_upload=activity.requires_file_upload or False, external_service_url=activity.external_service_url, constraints=constraint_schema))
                return schemas.DashboardInitResponse(user_context=user_context, subsystem=schemas.SubsystemInfoSchema(id=subsystem.id, code=subsystem.code, title=subsystem.title, icon=subsystem.icon, attachment_type=subsystem.attachment_type), allowed_activities=allowed_activities, has_subsystem=True, message=None)
        return schemas.DashboardInitResponse(user_context=user_context, subsystem=None, allowed_activities=[], has_subsystem=False, message="کاربر هنوز به قسمتی تخصیص داده نشده است")
    
    subsystem_mapping = db.query(models.SectionSubsystemAccess).filter(models.SectionSubsystemAccess.section_id == section.id).first()
    subsystem = db.query(models.Subsystem).filter(models.Subsystem.id == subsystem_mapping.subsystem_id, models.Subsystem.is_active == True).first() if subsystem_mapping else db.query(models.Subsystem).filter(models.Subsystem.is_active == True).order_by(models.Subsystem.order).first()
    
    if not subsystem:
        return schemas.DashboardInitResponse(user_context=user_context, subsystem=None, allowed_activities=[], has_subsystem=False, message="سامانه‌ای برای این قسمت تعریف نشده است")
    
    subsystem_info = schemas.SubsystemInfoSchema(id=subsystem.id, code=subsystem.code, title=subsystem.title, icon=subsystem.icon, attachment_type=subsystem.attachment_type)
    activities = get_section_activities(db, subsystem.id, section.id if section else None)
    
    allowed_activities = []
    for activity in activities:
        constraint = db.query(models.ActivityConstraint).filter(models.ActivityConstraint.subsystem_activity_id == activity.id, models.ActivityConstraint.is_active == True).order_by(models.ActivityConstraint.priority.desc()).first()
        constraint_schema = schemas.ActivityConstraintSchema(budget_code_pattern=constraint.budget_code_pattern, allowed_budget_types=constraint.allowed_budget_types, cost_center_pattern=constraint.cost_center_pattern, allowed_cost_centers=constraint.allowed_cost_centers, constraint_type=constraint.constraint_type or "INCLUDE") if constraint else None
        frequency_value = activity.frequency.value if hasattr(activity, 'frequency') and activity.frequency and hasattr(activity.frequency, 'value') else str(activity.frequency) if hasattr(activity, 'frequency') and activity.frequency else None
        allowed_activities.append(schemas.AllowedActivitySchema(id=activity.id, code=activity.code, title=activity.title, form_type=activity.form_type, frequency=frequency_value, requires_file_upload=activity.requires_file_upload or False, external_service_url=activity.external_service_url, constraints=constraint_schema))
    
    return schemas.DashboardInitResponse(user_context=user_context, subsystem=subsystem_info, allowed_activities=allowed_activities, has_subsystem=True, message=None)
