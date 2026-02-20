"""
Contract Template Router - Phase 2
====================================

Provides CRUD endpoints for dynamic contract template management.
Templates define JSON Schema structures that render dynamic forms on the frontend.

Endpoints:
  GET  /contract-templates         — List templates (filter by category, active)
  GET  /contract-templates/{id}    — Template detail with full schema
  POST /contract-templates         — Create new template (admin only)
  PUT  /contract-templates/{id}    — Update template (increments version)
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.models import ContractTemplate
from app.schemas.contract_template import (
    ContractTemplateCreate,
    ContractTemplateUpdate,
    ContractTemplateResponse,
    ContractTemplateListItem,
    ContractTemplateListResponse,
)
from app.routers.auth import get_current_user, get_db

router = APIRouter(prefix="/contract-templates", tags=["Contract Templates"])


# ============================================================
# Helpers
# ============================================================

def _require_auth(request: Request, db: Session):
    """Get authenticated user or raise 401."""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    return user


def _require_admin(request: Request, db: Session):
    """Require admin-level access for template management."""
    user = _require_auth(request, db)
    admin_level = user.admin_level or 0
    is_admin = user.role == "admin" or (user.role.startswith("ADMIN_L") and admin_level >= 1)
    if not is_admin:
        raise HTTPException(status_code=403, detail="دسترسی ادمین برای مدیریت قالب‌ها الزامی است")
    return user


def _template_to_response(t: ContractTemplate) -> ContractTemplateResponse:
    """Convert ContractTemplate ORM model to Pydantic response."""
    return ContractTemplateResponse(
        id=t.id,
        code=t.code,
        title=t.title,
        category=t.category,
        schema_definition=t.schema_definition or {},
        default_values=t.default_values,
        required_fields=t.required_fields,
        approval_workflow_config=t.approval_workflow_config,
        is_active=t.is_active if t.is_active is not None else True,
        version=t.version or 1,
        created_at=t.created_at.strftime("%Y/%m/%d %H:%M") if t.created_at else None,
        updated_at=t.updated_at.strftime("%Y/%m/%d %H:%M") if t.updated_at else None,
    )


def _template_to_list_item(t: ContractTemplate) -> ContractTemplateListItem:
    """Convert ContractTemplate ORM model to list item."""
    return ContractTemplateListItem(
        id=t.id,
        code=t.code,
        title=t.title,
        category=t.category,
        is_active=t.is_active if t.is_active is not None else True,
        version=t.version or 1,
        created_at=t.created_at.strftime("%Y/%m/%d %H:%M") if t.created_at else None,
    )


# ============================================================
# GET /contract-templates — list
# ============================================================

@router.get("", response_model=ContractTemplateListResponse)
def list_templates(
    request: Request,
    category: Optional[str] = Query(None, description="Filter by category (CIVIL, GREEN_SPACE, ...)"),
    active_only: bool = Query(True, description="Show only active templates"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List contract templates with optional filters."""
    _require_auth(request, db)
    
    query = db.query(ContractTemplate)
    
    if category:
        query = query.filter(ContractTemplate.category == category)
    if active_only:
        query = query.filter(ContractTemplate.is_active == True)
    
    total = query.count()
    offset = (page - 1) * limit
    templates = query.order_by(ContractTemplate.created_at.desc()).offset(offset).limit(limit).all()
    
    items = [_template_to_list_item(t) for t in templates]
    return ContractTemplateListResponse(items=items, total=total, page=page, limit=limit)


# ============================================================
# GET /contract-templates/{id} — detail
# ============================================================

@router.get("/{template_id}", response_model=ContractTemplateResponse)
def get_template(
    template_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get contract template detail with full JSON Schema definition."""
    _require_auth(request, db)
    
    template = db.query(ContractTemplate).filter(ContractTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="قالب قرارداد یافت نشد")
    
    return _template_to_response(template)


# ============================================================
# POST /contract-templates — create
# ============================================================

@router.post("", response_model=ContractTemplateResponse)
def create_template(
    data: ContractTemplateCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Create a new contract template.
    
    The schema_definition must be a valid JSON Schema object with at minimum
    a 'type' and 'properties' key. Example:
    
    {
        "type": "object",
        "properties": {
            "project_location": {"type": "string", "title": "محل پروژه"},
            "duration_days": {"type": "integer", "title": "مدت (روز)"}
        },
        "required": ["project_location"]
    }
    """
    _require_admin(request, db)
    
    # Check for duplicate code
    existing = db.query(ContractTemplate).filter(
        ContractTemplate.code == data.code
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"قالب با کد {data.code} قبلاً تعریف شده است"
        )
    
    # Basic JSON Schema validation
    schema = data.schema_definition
    if not isinstance(schema, dict):
        raise HTTPException(status_code=422, detail="schema_definition باید یک آبجکت JSON باشد")
    if "type" not in schema:
        raise HTTPException(status_code=422, detail="schema_definition باید دارای فیلد 'type' باشد")
    if "properties" not in schema:
        raise HTTPException(status_code=422, detail="schema_definition باید دارای فیلد 'properties' باشد")
    
    template = ContractTemplate(
        code=data.code,
        title=data.title,
        category=data.category,
        schema_definition=data.schema_definition,
        default_values=data.default_values,
        required_fields=data.required_fields,
        approval_workflow_config=data.approval_workflow_config,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return _template_to_response(template)


# ============================================================
# PUT /contract-templates/{id} — update (version increment)
# ============================================================

@router.put("/{template_id}", response_model=ContractTemplateResponse)
def update_template(
    template_id: int,
    data: ContractTemplateUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Update a contract template. Increments version automatically.
    
    Existing contracts keep their template_id reference.
    Only the latest version is used for new contracts.
    """
    _require_admin(request, db)
    
    template = db.query(ContractTemplate).filter(ContractTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="قالب قرارداد یافت نشد")
    
    # Apply partial updates
    if data.title is not None:
        template.title = data.title
    if data.category is not None:
        template.category = data.category
    if data.schema_definition is not None:
        # Validate schema
        schema = data.schema_definition
        if not isinstance(schema, dict) or "type" not in schema or "properties" not in schema:
            raise HTTPException(status_code=422, detail="schema_definition نامعتبر است")
        template.schema_definition = schema
    if data.default_values is not None:
        template.default_values = data.default_values
    if data.required_fields is not None:
        template.required_fields = data.required_fields
    if data.approval_workflow_config is not None:
        template.approval_workflow_config = data.approval_workflow_config
    if data.is_active is not None:
        template.is_active = data.is_active
    
    # Increment version
    template.version = (template.version or 1) + 1
    template.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(template)
    
    return _template_to_response(template)
