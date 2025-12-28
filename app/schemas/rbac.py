# app/schemas/rbac.py
"""
RBAC (Role-Based Access Control) Schemas
=========================================

Pydantic schemas for User-Subsystem access control.
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# --------------------------------------------------------
# Request Schemas
# --------------------------------------------------------

class SubsystemAccessAssignRequest(BaseModel):
    """Request body for assigning subsystems to a user (Full Sync)"""
    subsystem_ids: List[int]


class SubsystemAccessAssignByCodeRequest(BaseModel):
    """Alternative: assign by subsystem codes instead of IDs"""
    subsystem_codes: List[str]  # e.g., ["URBAN_PLANNING", "FINANCE"]


# --------------------------------------------------------
# Response Schemas
# --------------------------------------------------------

class SubsystemInfoResponse(BaseModel):
    """Subsystem information"""
    id: int
    code: str
    title: str
    icon: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserSubsystemAccessResponse(BaseModel):
    """Single access record"""
    id: int
    user_id: int
    subsystem_id: int
    created_at: datetime
    subsystem: SubsystemInfoResponse
    
    class Config:
        from_attributes = True


class AllowedSubsystemsResponse(BaseModel):
    """Response for /users/me/allowed-subsystems"""
    user_id: int
    allowed_subsystems: List[SubsystemInfoResponse]
    total_count: int


class AccessUpdateResponse(BaseModel):
    """Response after updating user access"""
    user_id: int
    message: str
    assigned_count: int
    assigned_subsystems: List[SubsystemInfoResponse]
