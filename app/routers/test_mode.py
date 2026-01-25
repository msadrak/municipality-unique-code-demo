"""
Test Mode Router - Excel-based test endpoints for verification
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_
import pandas as pd
import os
from app import models
from app.routers.auth import get_db

router = APIRouter(prefix="/portal", tags=["Test Mode"])

EXCEL_FILE = "combined_output_version_2.xlsx"
ZONE_FILTER = 20
TRANSACTION_FILE = "_شهرداری مرکزی گزارش دفتر مرکزی1403.xlsx"
_sheet_names_cache = None
_transaction_df_cache = None

def get_sheet_names():
    global _sheet_names_cache
    if _sheet_names_cache is None:
        xl = pd.ExcelFile(EXCEL_FILE)
        _sheet_names_cache = xl.sheet_names
    return _sheet_names_cache

def safe_str(val, default=""):
    if pd.isna(val):
        return default
    return str(val)

def clean_request_id(req):
    if pd.isna(req):
        return None
    req_str = str(req).strip()
    req_str = ' '.join(req_str.split())
    return req_str if req_str else None

def get_transaction_df():
    global _transaction_df_cache
    if _transaction_df_cache is None:
        df = pd.read_excel(TRANSACTION_FILE)
        df['BodgetNo_str'] = df['BodgetNo'].apply(lambda x: str(int(x)) if pd.notna(x) and isinstance(x, (int, float)) else str(x).strip() if pd.notna(x) else "")
        _transaction_df_cache = df
    return _transaction_df_cache

@router.get("/test/sheets")
def get_excel_sheets():
    """Get list of sheets from Excel"""
    try:
        sheet_names = get_sheet_names()
        return {"sheets": [{"name": name, "display_name": name.strip()} for name in sheet_names]}
    except Exception as e:
        return {"error": str(e), "sheets": []}

@router.get("/test/requests/{sheet_name:path}")
def get_sheet_requests(sheet_name: str):
    """Get request numbers for a specific sheet (Zone 20 only)"""
    try:
        actual_sheet_name = None
        for name in get_sheet_names():
            if name == sheet_name or name.strip() == sheet_name.strip():
                actual_sheet_name = name
                break
        if actual_sheet_name is None:
            return {"error": f"Sheet not found: {sheet_name}", "requests": []}
        
        df = pd.read_excel(EXCEL_FILE, sheet_name=actual_sheet_name)
        df20 = df[df['AreaNo'] == ZONE_FILTER]
        if len(df20) == 0:
            return {"sheet_name": actual_sheet_name, "zone": ZONE_FILTER, "message": "این شیت داده‌ای برای منطقه ۲۰ ندارد", "requests": []}
        
        request_stats = {}
        for idx, row in df20.iterrows():
            clean_req = clean_request_id(row.get('Requests'))
            if clean_req is None:
                continue
            if clean_req not in request_stats:
                request_stats[clean_req] = {"raw_value": row.get('Requests'), "count": 0, "total_debit": 0.0, "total_credit": 0.0}
            request_stats[clean_req]["count"] += 1
            request_stats[clean_req]["total_debit"] += float(row.get('DebitAmnt', 0)) if pd.notna(row.get('DebitAmnt')) else 0.0
            request_stats[clean_req]["total_credit"] += float(row.get('CreditAmnt', 0)) if pd.notna(row.get('CreditAmnt')) else 0.0
        
        requests = [{"request_id": clean_req, "transaction_count": stats["count"], "total_debit": stats["total_debit"], "total_credit": stats["total_credit"], "is_balanced": abs(stats["total_debit"] - stats["total_credit"]) < 1} for clean_req, stats in request_stats.items()]
        requests.sort(key=lambda x: x['transaction_count'], reverse=True)
        return {"sheet_name": actual_sheet_name, "zone": ZONE_FILTER, "requests": requests}
    except Exception as e:
        return {"error": str(e), "requests": []}

@router.get("/test2/budget-items")
def get_budget_items(search: str = "", trustee: str = "", subject: str = "", row_type: str = "", budget_type: str = "", limit: int = 100, db: Session = Depends(get_db)):
    """Get budget items with filters"""
    query = db.query(models.BudgetItem)
    if search:
        query = query.filter(or_(models.BudgetItem.budget_code.contains(search), models.BudgetItem.description.contains(search)))
    if trustee:
        query = query.filter(models.BudgetItem.trustee.contains(trustee))
    if subject:
        query = query.filter(models.BudgetItem.subject.contains(subject))
    if row_type:
        query = query.filter(models.BudgetItem.row_type == row_type)
    if budget_type:
        query = query.filter(models.BudgetItem.budget_type == budget_type)
    
    items = query.limit(limit).all()
    return {"count": len(items), "items": [{"id": item.id, "budget_code": item.budget_code, "description": item.description, "budget_type": item.budget_type, "zone": item.zone, "trustee": item.trustee, "subject": item.subject, "row_type": item.row_type, "allocated_1403": item.allocated_1403} for item in items]}

@router.get("/test2/budget-items/{budget_code}")
def get_budget_item_detail(budget_code: str, db: Session = Depends(get_db)):
    """Get single budget item with transaction summary"""
    item = db.query(models.BudgetItem).filter(models.BudgetItem.budget_code == budget_code).first()
    if not item:
        return {"error": f"Budget code not found: {budget_code}"}
    
    df = get_transaction_df()
    df_filtered = df[df['BodgetNo_str'] == budget_code]
    total_debit = df_filtered['DebitAmnt'].sum() if len(df_filtered) > 0 else 0
    total_credit = df_filtered['CreditAmnt'].sum() if len(df_filtered) > 0 else 0
    
    return {"budget_item": {"budget_code": item.budget_code, "description": item.description, "budget_type": item.budget_type, "trustee": item.trustee, "allocated_1403": item.allocated_1403}, "transaction_summary": {"count": len(df_filtered), "total_debit": float(total_debit) if pd.notna(total_debit) else 0, "total_credit": float(total_credit) if pd.notna(total_credit) else 0}}

@router.get("/test2/filters")
def get_filter_options(db: Session = Depends(get_db)):
    """Get unique filter options for dropdowns"""
    trustees = db.query(models.BudgetItem.trustee).distinct().filter(models.BudgetItem.trustee != None).all()
    subjects = db.query(models.BudgetItem.subject).distinct().filter(models.BudgetItem.subject != None).all()
    return {"trustees": [t[0] for t in trustees if t[0]], "subjects": [s[0] for s in subjects if s[0]], "row_types": ["مستمر", "غیر مستمر"], "budget_types": ["hazine", "sarmaye"]}
