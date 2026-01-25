"""
Organizations Router - Org structure and budget-related endpoints
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from app import models
from app.routers.auth import get_db

router = APIRouter(prefix="/portal", tags=["Organizations"])

@router.get("/org/roots")
def get_root_orgs(db: Session = Depends(get_db)):
    """Get top-level zones (Level 1)"""
    return db.query(models.OrgUnit).filter(models.OrgUnit.parent_id == None).all()

@router.get("/org/children/{parent_id}")
def get_org_children(parent_id: int, db: Session = Depends(get_db)):
    """Get children of a specific unit"""
    return db.query(models.OrgUnit).filter(models.OrgUnit.parent_id == parent_id).all()

@router.get("/budgets/for-org")
def get_budgets_for_org(zone_id: int, department_id: Optional[int] = None, section_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get budgets for the selected org context"""
    zone = db.query(models.OrgUnit).filter(models.OrgUnit.id == zone_id).first()
    if not zone:
        return []
    
    budget_codes_query = db.query(models.OrgBudgetMap.budget_code).filter(models.OrgBudgetMap.zone_code == zone.code, models.OrgBudgetMap.budget_code != None, models.OrgBudgetMap.budget_code != "").distinct()
    budget_codes = [bc[0] for bc in budget_codes_query.all()]
    
    if not budget_codes:
        return []
    
    items = db.query(models.BudgetItem).filter(models.BudgetItem.budget_code.in_(budget_codes)).order_by(models.BudgetItem.budget_code).limit(500).all()
    return [{"id": item.id, "budget_code": item.budget_code, "title": item.description, "description": item.description, "allocated_1403": item.allocated_1403 or 0, "remaining_budget": item.remaining_budget or 0, "budget_type": item.budget_type, "row_type": item.row_type, "zone_code": item.zone_code, "trustee": item.trustee} for item in items]

@router.get("/cost-centers/for-org")
def get_cost_centers_for_org(zone_id: int, department_id: Optional[int] = None, section_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get cost centers for the selected org context"""
    zone = db.query(models.OrgUnit).filter(models.OrgUnit.id == zone_id).first()
    if not zone:
        return []
    
    cost_centers_query = db.query(models.OrgBudgetMap.cost_center_desc).filter(models.OrgBudgetMap.zone_code == zone.code, models.OrgBudgetMap.cost_center_desc != None, models.OrgBudgetMap.cost_center_desc != "").distinct()
    cost_center_descs = [cc[0] for cc in cost_centers_query.all()]
    return [{"id": idx + 1, "code": f"CC-{str(idx + 1).zfill(4)}", "title": desc, "name": desc} for idx, desc in enumerate(cost_center_descs)]

@router.get("/continuous-actions/for-org")
def get_continuous_actions_for_org(zone_id: int, department_id: Optional[int] = None, section_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get continuous actions for the selected org context"""
    zone = db.query(models.OrgUnit).filter(models.OrgUnit.id == zone_id).first()
    if not zone:
        return []
    
    actions_query = db.query(models.OrgBudgetMap.continuous_action_desc).filter(models.OrgBudgetMap.zone_code == zone.code, models.OrgBudgetMap.continuous_action_desc != None, models.OrgBudgetMap.continuous_action_desc != "").distinct().limit(200)
    action_descs = [a[0] for a in actions_query.all()]
    return [{"id": idx + 1, "code": f"CA-{str(idx + 1).zfill(3)}", "title": desc, "name": desc} for idx, desc in enumerate(action_descs)]

@router.get("/budgets/trustees/{zone_code}")
def get_trustees_for_zone(zone_code: str, db: Session = Depends(get_db)):
    """Get distinct trustees for budget items in a zone"""
    selected_zone = db.query(models.OrgUnit).filter(models.OrgUnit.code == zone_code, models.OrgUnit.parent_id == None).first()
    if not selected_zone:
        return {"trustees": []}
    
    zone_ids = [selected_zone.id]
    children = db.query(models.OrgUnit.id).filter(models.OrgUnit.parent_id == selected_zone.id).all()
    zone_ids.extend([c[0] for c in children])
    for child_id in [c[0] for c in children]:
        grandchildren = db.query(models.OrgUnit.id).filter(models.OrgUnit.parent_id == child_id).all()
        zone_ids.extend([g[0] for g in grandchildren])
    
    trustees = db.query(models.BudgetItem.trustee).filter(models.BudgetItem.trustee_section_id.in_(zone_ids), models.BudgetItem.trustee != None, models.BudgetItem.trustee != "").distinct().all()
    return {"zone_code": zone_code, "zone_title": selected_zone.title, "trustees": [t[0] for t in trustees if t[0]]}

@router.get("/budgets/by-zone/{zone_code}")
def get_budgets_by_zone_code(zone_code: str, trustee: str = "", request: Request = None, db: Session = Depends(get_db)):
    """Get budgets filtered by zone and optionally by trustee"""
    query = db.query(models.BudgetItem)
    selected_zone = db.query(models.OrgUnit).filter(models.OrgUnit.code == zone_code, models.OrgUnit.parent_id == None).first()
    
    if selected_zone:
        zone_ids = [selected_zone.id]
        children = db.query(models.OrgUnit.id).filter(models.OrgUnit.parent_id == selected_zone.id).all()
        zone_ids.extend([c[0] for c in children])
        for child_id in [c[0] for c in children]:
            grandchildren = db.query(models.OrgUnit.id).filter(models.OrgUnit.parent_id == child_id).all()
            zone_ids.extend([g[0] for g in grandchildren])
        query = query.filter(models.BudgetItem.trustee_section_id.in_(zone_ids))
    
    if trustee:
        query = query.filter(models.BudgetItem.trustee == trustee)
    
    items = query.order_by(models.BudgetItem.budget_code).limit(500).all()
    return [{"id": item.id, "budget_code": item.budget_code, "title": item.description, "description": item.description, "allocated_1403": item.allocated_1403 or 0, "remaining_budget": item.remaining_budget or 0, "budget_type": item.budget_type, "row_type": item.row_type, "zone_code": item.zone_code, "trustee": item.trustee, "trustee_section_id": item.trustee_section_id} for item in items]

@router.get("/budgets/all")
def get_all_budgets(limit: int = 100, search: str = "", db: Session = Depends(get_db)):
    """Get all budget items with optional search"""
    query = db.query(models.BudgetItem)
    if search:
        query = query.filter(or_(models.BudgetItem.budget_code.contains(search), models.BudgetItem.description.contains(search)))
    items = query.order_by(models.BudgetItem.budget_code).limit(limit).all()
    return [{"id": item.id, "budget_code": item.budget_code, "title": item.description, "allocated_1403": item.allocated_1403 or 0, "remaining_budget": item.remaining_budget or 0, "budget_type": item.budget_type} for item in items]

@router.get("/continuous-actions")
def get_continuous_actions(search: str = "", db: Session = Depends(get_db)):
    query = db.query(models.ContinuousAction)
    if search:
        query = query.filter(models.ContinuousAction.title.contains(search))
    return query.limit(100).all()

@router.get("/financial-events")
def get_financial_events(db: Session = Depends(get_db)):
    return db.query(models.FinancialEventRef).order_by(models.FinancialEventRef.code).all()

@router.get("/cost-centers")
def get_cost_centers(db: Session = Depends(get_db)):
    return db.query(models.CostCenterRef).all()

@router.get("/reports/financial-docs/{zone_code}")
def get_financial_docs(zone_code: str, db: Session = Depends(get_db)):
    """Get financial documents for a specific zone"""
    return db.query(models.FinancialDocument).filter(models.FinancialDocument.zone_code == zone_code).limit(100).all()
