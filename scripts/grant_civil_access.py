"""
Grant User Access for Civil Department (Region 14)
===============================================
Grants the civil admin user access to relevant subsystems and budget items.
"""
import sys
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models

# Create tables if needed
models.Base.metadata.create_all(bind=engine)

def main():
    print("Granting user access for Civil Department (Region 14)...")

    db = SessionLocal()
    try:
        # Find the civil department user
        civil_user = db.query(models.User).filter(models.User.username == "admin_معاونت_عمران_شهري_reg14").first()
        if not civil_user:
            print("ERROR: Civil user not found")
            return

        print(f"Found civil user: {civil_user.username} (ID: {civil_user.id})")

        # Find the INFRA subsystem (created during mapping)
        infra_subsystem = db.query(models.Subsystem).filter(models.Subsystem.code == "INFRA").first()
        if not infra_subsystem:
            print("ERROR: INFRA subsystem not found")
            return

        print(f"Found INFRA subsystem: {infra_subsystem.title} (ID: {infra_subsystem.id})")

        # Grant subsystem access
        existing_access = db.query(models.UserSubsystemAccess).filter(
            models.UserSubsystemAccess.user_id == civil_user.id,
            models.UserSubsystemAccess.subsystem_id == infra_subsystem.id
        ).first()

        if not existing_access:
            access = models.UserSubsystemAccess(
                user_id=civil_user.id,
                subsystem_id=infra_subsystem.id
            )
            db.add(access)
            db.flush()
            print(f"Granted subsystem access: {civil_user.username} -> {infra_subsystem.title}")

        # Grant budget access to civil-related budget items
        # Find budget items linked to civil activities (those with trustee = civil department)
        civil_org_unit = db.query(models.OrgUnit).filter(models.OrgUnit.title == "معاونت عمران شهري").first()
        if civil_org_unit:
            civil_budget_items = db.query(models.BudgetItem).filter(
                models.BudgetItem.trustee_section_id == civil_org_unit.id
            ).all()

            for budget in civil_budget_items:
                existing_budget_access = db.query(models.UserBudgetAccess).filter(
                    models.UserBudgetAccess.user_id == civil_user.id,
                    models.UserBudgetAccess.budget_item_id == budget.id
                ).first()

                if not existing_budget_access:
                    budget_access = models.UserBudgetAccess(
                        user_id=civil_user.id,
                        budget_item_id=budget.id
                    )
                    db.add(budget_access)
                    print(f"Granted budget access: {civil_user.username} -> {budget.budget_code}")

        db.commit()
        print("Access granted successfully!")

    finally:
        db.close()

if __name__ == "__main__":
    main()