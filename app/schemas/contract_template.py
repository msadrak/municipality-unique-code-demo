"""
Pydantic Schemas for Contract Template CRUD (Phase 2)
=====================================================

Covers: creation, update, response, and list views.
The schema_definition field accepts a JSON Schema object that defines
the dynamic form fields for contracts of this type.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================
# Request Schemas
# ============================================================

class ContractTemplateCreate(BaseModel):
    """POST /contract-templates — define a new contract type."""
    code: str = Field(..., min_length=1, description="Unique template code, e.g. CIVIL_TYPE_A")
    title: str = Field(..., min_length=1, description="عنوان فارسی قالب")
    category: Optional[str] = Field(None, description="CIVIL, GREEN_SPACE, SERVICES, ...")
    schema_definition: Dict[str, Any] = Field(
        ...,
        description="JSON Schema defining dynamic fields (type, properties, required)"
    )
    default_values: Optional[Dict[str, Any]] = Field(None, description="Default field values")
    required_fields: Optional[List[str]] = Field(None, description="Override required fields")
    approval_workflow_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Approval workflow settings (required_levels, requires_legal_review, ...)"
    )


class ContractTemplateUpdate(BaseModel):
    """PUT /contract-templates/{id} — update template (increments version)."""
    title: Optional[str] = None
    category: Optional[str] = None
    schema_definition: Optional[Dict[str, Any]] = None
    default_values: Optional[Dict[str, Any]] = None
    required_fields: Optional[List[str]] = None
    approval_workflow_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


# ============================================================
# Response Schemas
# ============================================================

class ContractTemplateResponse(BaseModel):
    """Full contract template detail with schema definition."""
    id: int
    code: str
    title: str
    category: Optional[str] = None
    schema_definition: Dict[str, Any]
    default_values: Optional[Dict[str, Any]] = None
    required_fields: Optional[List[str]] = None
    approval_workflow_config: Optional[Dict[str, Any]] = None
    is_active: bool
    version: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class ContractTemplateListItem(BaseModel):
    """Abbreviated template for list views (no full schema)."""
    id: int
    code: str
    title: str
    category: Optional[str] = None
    is_active: bool
    version: int
    created_at: Optional[str] = None


class ContractTemplateListResponse(BaseModel):
    """GET /contract-templates — paginated list."""
    items: List[ContractTemplateListItem]
    total: int
    page: int
    limit: int
