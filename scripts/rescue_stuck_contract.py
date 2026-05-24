"""Rescue script to assign contractor_id to stuck Cleaning contract at Step 105.

This script finds the Cleaning contract currently stuck at Step 105 (ثبت کارکرد)
and assigns it to the newly created cleaning_contractor@test.com user.
"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import SessionLocal
from app.models import CivilProject, User, WorkflowStep
from sqlalchemy.orm import joinedload


def rescue_stuck_contract() -> None:
    """Find stuck Cleaning contract and assign to cleaning_contractor."""
    db = SessionLocal()
    try:
        # Find the cleaning contractor user
        contractor = db.query(User).filter(
            User.username == "cleaning_contractor@test.com"
        ).first()
        
        if not contractor:
            print("ERROR: cleaning_contractor@test.com not found!")
            print("Please run: python scripts/seed_users.py first")
            return
        
        print(f"Found contractor: {contractor.username} (ID: {contractor.id})")
        
        # Find stuck Cleaning contract at Step 105
        project = db.query(CivilProject).options(
            joinedload(CivilProject.current_step)
        ).filter(
            CivilProject.contract_category == "نظافت و پذیرایی",
            CivilProject.current_step.has(WorkflowStep.order_index == 105)
        ).first()
        
        if not project:
            print("No stuck Cleaning contract found at Step 105")
            print("Checking all Cleaning contracts...")
            
            all_cleaning = db.query(CivilProject).options(
                joinedload(CivilProject.current_step)
            ).filter(
                CivilProject.contract_category == "نظافت و پذیرایی"
            ).all()
            
            if all_cleaning:
                print(f"\nFound {len(all_cleaning)} Cleaning contract(s):")
                for p in all_cleaning:
                    step_info = f"{p.current_step.order_index} - {p.current_step.name}" if p.current_step else "No step"
                    print(f"  - ID {p.id}: {p.project_code} | Step: {step_info} | Contractor ID: {p.contractor_id}")
            else:
                print("No Cleaning contracts found in database")
            return
        
        print(f"\nFound stuck contract:")
        print(f"  Project ID: {project.id}")
        print(f"  Project Code: {project.project_code}")
        print(f"  Title: {project.title}")
        print(f"  Current Step: {project.current_step.order_index} - {project.current_step.name}")
        print(f"  Current Contractor ID: {project.contractor_id}")
        
        if project.contractor_id == contractor.id:
            print(f"\n✓ Contract already assigned to {contractor.username}")
            return
        
        # Assign contractor
        project.contractor_id = contractor.id
        db.commit()
        
        print(f"\n✓ SUCCESS: Assigned contractor_id={contractor.id} to project {project.project_code}")
        print(f"  User can now log in as: cleaning_contractor@test.com / password123")
        print(f"  And complete Step 105 (ثبت کارکرد)")
        
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    rescue_stuck_contract()
