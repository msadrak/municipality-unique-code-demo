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