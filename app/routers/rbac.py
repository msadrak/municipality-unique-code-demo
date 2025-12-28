# app/routers/rbac.py
"""
RBAC (Role-Based Access Control) API Router
============================================

Endpoints for managing User-Subsystem access control.
Default Policy: DENY ALL (users with no access entries see nothing).

Endpoints:
- GET  /rbac/subsystems           - List all available subsystems
- GET  /rbac/me/allowed           - Get current user's allowed subsystems
- GET  /rbac/users/{user_id}/access - Get specific user's access (Admin)
- POST /rbac/users/{user_id}/access - Assign subsystems to user (Admin)
- DELETE /rbac/users/{user_id}/access/{subsystem_id} - Revoke access (Admin)
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, Subsystem, UserSubsystemAccess
from app.schemas.rbac import (
    SubsystemAccessAssignRequest,
    SubsystemInfoResponse,
    AllowedSubsystemsResponse,
    AccessUpdateResponse,
)


router = APIRouter(prefix="/rbac", tags=["RBAC - Access Control"])


# ============================================================
# Dependencies
# ============================================================

def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_id(db: Session = Depends(get_db)) -> int:
    """
    Extract current user ID from session.
    This should integrate with your existing auth system.
    For now, returns a placeholder - integrate with your session management.
    """
    # TODO: Integrate with your existing session-based auth
    # Example: return session.get("user_id")
    # For now, we'll use a simple header-based approach for testing
    return 1  # Placeholder - replace with actual session logic


def require_admin(db: Session = Depends(get_db)):
    """Require admin role for sensitive operations."""
    # TODO: Integrate with your existing admin check
    # For now, this is a placeholder
    pass


# ============================================================
# Public Endpoints
# ============================================================

@router.get(
    "/subsystems",
    response_model=List[SubsystemInfoResponse],
    summary="List All Subsystems",
    description="Returns all 14 subsystems available in the system.",
)
def list_all_subsystems(db: Session = Depends(get_db)):
    """Get all available subsystems."""
    subsystems = db.query(Subsystem).filter(Subsystem.is_active == True).order_by(Subsystem.order).all()
    return subsystems


@router.get(
    "/me/allowed",
    response_model=AllowedSubsystemsResponse,
    summary="Get My Allowed Subsystems",
    description="Returns the list of subsystems the current user can access.",
)
def get_my_allowed_subsystems(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """Get allowed subsystems for current user (DENY ALL if empty)."""
    access_records = (
        db.query(UserSubsystemAccess)
        .filter(UserSubsystemAccess.user_id == current_user_id)
        .all()
    )
    
    allowed_subsystems = [record.subsystem for record in access_records if record.subsystem]
    
    return AllowedSubsystemsResponse(
        user_id=current_user_id,
        allowed_subsystems=allowed_subsystems,
        total_count=len(allowed_subsystems),
    )


# ============================================================
# Admin Endpoints
# ============================================================

@router.get(
    "/users/{user_id}/access",
    response_model=AllowedSubsystemsResponse,
    summary="Get User's Access (Admin)",
    description="Admin: View which subsystems a specific user can access.",
)
def get_user_access(
    user_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Admin: Get a user's subsystem access list."""
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )
    
    access_records = (
        db.query(UserSubsystemAccess)
        .filter(UserSubsystemAccess.user_id == user_id)
        .all()
    )
    
    allowed_subsystems = [record.subsystem for record in access_records if record.subsystem]
    
    return AllowedSubsystemsResponse(
        user_id=user_id,
        allowed_subsystems=allowed_subsystems,
        total_count=len(allowed_subsystems),
    )


@router.post(
    "/users/{user_id}/access",
    response_model=AccessUpdateResponse,
    summary="Assign Subsystems (Admin)",
    description="Admin: Assign subsystems to a user. Uses FULL SYNC: wipes existing access and sets new list.",
)
def assign_user_access(
    user_id: int,
    request: SubsystemAccessAssignRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    """
    Admin: Full sync of user's subsystem access.
    
    This operation:
    1. Deletes ALL existing access records for this user
    2. Creates new access records for the provided subsystem IDs
    """
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )
    
    # Verify all subsystem IDs are valid
    valid_subsystems = (
        db.query(Subsystem)
        .filter(Subsystem.id.in_(request.subsystem_ids))
        .all()
    )
    valid_ids = {s.id for s in valid_subsystems}
    invalid_ids = set(request.subsystem_ids) - valid_ids
    
    if invalid_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid subsystem IDs: {list(invalid_ids)}",
        )
    
    # Step 1: Delete existing access
    db.query(UserSubsystemAccess).filter(
        UserSubsystemAccess.user_id == user_id
    ).delete()
    
    # Step 2: Create new access records
    for subsystem_id in request.subsystem_ids:
        access = UserSubsystemAccess(
            user_id=user_id,
            subsystem_id=subsystem_id,
        )
        db.add(access)
    
    db.commit()
    
    # Fetch the updated list for response
    new_access = (
        db.query(UserSubsystemAccess)
        .filter(UserSubsystemAccess.user_id == user_id)
        .all()
    )
    assigned_subsystems = [record.subsystem for record in new_access if record.subsystem]
    
    return AccessUpdateResponse(
        user_id=user_id,
        message=f"Access updated successfully for user {user.username}",
        assigned_count=len(assigned_subsystems),
        assigned_subsystems=assigned_subsystems,
    )


@router.delete(
    "/users/{user_id}/access/{subsystem_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke Access (Admin)",
    description="Admin: Remove a specific subsystem access from a user.",
)
def revoke_user_access(
    user_id: int,
    subsystem_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Admin: Revoke a specific subsystem access from a user."""
    # Find and delete the access record
    access = (
        db.query(UserSubsystemAccess)
        .filter(
            UserSubsystemAccess.user_id == user_id,
            UserSubsystemAccess.subsystem_id == subsystem_id,
        )
        .first()
    )
    
    if not access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access record not found",
        )
    
    db.delete(access)
    db.commit()
    
    return None


# ============================================================
# Utility Functions (for use by other modules)
# ============================================================

def get_user_allowed_subsystem_ids(db: Session, user_id: int) -> List[int]:
    """
    Get list of subsystem IDs the user can access.
    Returns empty list if user has no access (DENY ALL policy).
    
    Use this in other routers to filter activities/data.
    """
    access_records = (
        db.query(UserSubsystemAccess.subsystem_id)
        .filter(UserSubsystemAccess.user_id == user_id)
        .all()
    )
    return [record[0] for record in access_records]
