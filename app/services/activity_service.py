# app/services/activity_service.py
"""
Activity Service - RBAC-Filtered Activity Access
=================================================

Provides filtered activity queries based on user's subsystem access.
Implements DENY ALL policy: users with no access see no activities.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import SubsystemActivity, Subsystem, UserSubsystemAccess


def get_user_allowed_subsystem_ids(db: Session, user_id: int) -> List[int]:
    """
    Get list of subsystem IDs the user can access.
    Returns empty list if user has no access (DENY ALL policy).
    """
    access_records = (
        db.query(UserSubsystemAccess.subsystem_id)
        .filter(UserSubsystemAccess.user_id == user_id)
        .all()
    )
    return [record[0] for record in access_records]


def get_allowed_activities_for_user(
    db: Session,
    user_id: int,
    subsystem_id: Optional[int] = None,
) -> List[SubsystemActivity]:
    """
    Get activities the user is allowed to see, based on their subsystem access.
    
    Args:
        db: Database session
        user_id: ID of the current user
        subsystem_id: Optional filter to specific subsystem
    
    Returns:
        List of SubsystemActivity objects the user can access.
        Returns empty list if user has no subsystem access (DENY ALL).
    """
    # Step 1: Get user's allowed subsystem IDs
    allowed_subsystem_ids = get_user_allowed_subsystem_ids(db, user_id)
    
    # DENY ALL: If no access records, return empty list
    if not allowed_subsystem_ids:
        return []
    
    # Step 2: Build query with RBAC filter
    query = db.query(SubsystemActivity).filter(
        SubsystemActivity.subsystem_id.in_(allowed_subsystem_ids),
        SubsystemActivity.is_active == True,
    )
    
    # Optional: Filter to specific subsystem
    if subsystem_id:
        if subsystem_id not in allowed_subsystem_ids:
            # User trying to access subsystem they don't have access to
            return []
        query = query.filter(SubsystemActivity.subsystem_id == subsystem_id)
    
    # Order by subsystem and then by order
    query = query.order_by(
        SubsystemActivity.subsystem_id,
        SubsystemActivity.order,
    )
    
    return query.all()


def get_allowed_subsystems_for_user(
    db: Session,
    user_id: int,
) -> List[Subsystem]:
    """
    Get subsystems the user is allowed to access.
    
    Returns:
        List of Subsystem objects the user can access.
        Returns empty list if user has no access (DENY ALL).
    """
    allowed_subsystem_ids = get_user_allowed_subsystem_ids(db, user_id)
    
    if not allowed_subsystem_ids:
        return []
    
    subsystems = (
        db.query(Subsystem)
        .filter(
            Subsystem.id.in_(allowed_subsystem_ids),
            Subsystem.is_active == True,
        )
        .order_by(Subsystem.order)
        .all()
    )
    
    return subsystems


def check_user_has_access_to_activity(
    db: Session,
    user_id: int,
    activity_id: int,
) -> bool:
    """
    Check if a user has access to a specific activity.
    
    Returns:
        True if user can access the activity, False otherwise.
    """
    # Get the activity's subsystem_id
    activity = db.query(SubsystemActivity).filter(
        SubsystemActivity.id == activity_id
    ).first()
    
    if not activity:
        return False
    
    # Check if user has access to that subsystem
    allowed_subsystem_ids = get_user_allowed_subsystem_ids(db, user_id)
    return activity.subsystem_id in allowed_subsystem_ids


def check_user_has_access_to_subsystem(
    db: Session,
    user_id: int,
    subsystem_id: int,
) -> bool:
    """
    Check if a user has access to a specific subsystem.
    
    Returns:
        True if user can access the subsystem, False otherwise.
    """
    access = (
        db.query(UserSubsystemAccess)
        .filter(
            UserSubsystemAccess.user_id == user_id,
            UserSubsystemAccess.subsystem_id == subsystem_id,
        )
        .first()
    )
    return access is not None
