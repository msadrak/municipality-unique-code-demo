from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import date, datetime

# --------------------------------------------------------
# Hint Models
# --------------------------------------------------------

class OrgHint(BaseModel):
    zone_title: Optional[str] = None
    department_title: Optional[str] = None
    section_title: Optional[str] = None
    zone_code: Optional[str] = None 

class ActionHint(BaseModel):
    continuous_action_title: Optional[str] = None
    action_type_title: Optional[str] = None

# --------------------------------------------------------
# Input Payload
# --------------------------------------------------------

class ExternalSpecialActionPayload(BaseModel):
    org_unit_full_code: Optional[str] = None
    continuous_action_code: Optional[str] = None
    action_type_code: Optional[str] = None
    
    org_hint: Optional[OrgHint] = None
    action_hint: Optional[ActionHint] = None
    
    financial_event_title: str
    amount: float
    local_record_id: str
    description: Optional[str] = None
    action_date: Optional[date] = None
    
    details: Optional[Dict[str, Any]] = None 
    details: Optional[Dict[str, Any]] = None
# --------------------------------------------------------
# Output Schemas (Response)
# --------------------------------------------------------

class SpecialActionResponse(BaseModel):
    id: int
    unique_code: Optional[str] = None
    financial_event_title: Optional[str] = None
    amount: float
    status: str = "Created"
    
    created_at: Optional[datetime] = None
    org_unit_id: Optional[int] = None
    
    details: Optional[Dict[str, Any]] = None

    # 👇 THIS IS THE FIX (Works for Pydantic V2)
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------
# Dashboard Initialization Schemas
# --------------------------------------------------------

class UserContextSchema(BaseModel):
    """User's organizational context"""
    user_id: int
    user_name: str
    zone_id: Optional[int] = None
    zone_code: Optional[str] = None
    zone_title: Optional[str] = None
    section_id: Optional[int] = None
    section_code: Optional[str] = None
    section_title: Optional[str] = None

class SubsystemInfoSchema(BaseModel):
    """Subsystem basic info"""
    id: int
    code: str
    title: str
    icon: Optional[str] = None
    attachment_type: Optional[str] = None

class ActivityConstraintSchema(BaseModel):
    """Constraint rules for an activity"""
    budget_code_pattern: Optional[str] = None
    allowed_budget_types: Optional[List[str]] = None
    cost_center_pattern: Optional[str] = None
    allowed_cost_centers: Optional[List[int]] = None
    constraint_type: str = "INCLUDE"

class AllowedActivitySchema(BaseModel):
    """Activity with its constraints"""
    id: int
    code: str
    title: str
    form_type: Optional[str] = None
    frequency: Optional[str] = None
    requires_file_upload: bool = False
    external_service_url: Optional[str] = None
    constraints: Optional[ActivityConstraintSchema] = None

class DashboardInitResponse(BaseModel):
    """Complete dashboard initialization response"""
    user_context: UserContextSchema
    subsystem: Optional[SubsystemInfoSchema] = None
    allowed_activities: List[AllowedActivitySchema] = []
    has_subsystem: bool = False
    message: Optional[str] = None
