import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import SessionLocal, engine
from app.models.civil import WorkflowStepDefinition, StepAction, WorkflowTransition
from app.models import User, Base
from app.core.security import get_password_hash

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    roles = set()
    
    for (role,) in db.query(WorkflowStepDefinition.role_required).distinct():
        if role:
            roles.add(role)
            
    for (role,) in db.query(StepAction.assigned_role).distinct():
        if role:
            roles.add(role)
            
    for (role,) in db.query(WorkflowTransition.required_role).distinct():
        if role:
            roles.add(role)
            
    # Add explicitly requested test roles if not already discovered
    roles.update(['COUNCIL', 'DESIGN_ORG', 'REGION_MANAGER', 'FINANCE'])
    
    if 'CONTRACTOR' in roles:
        roles.remove('CONTRACTOR')
    if 'ADMIN' in roles:
        roles.remove('ADMIN')
        
    print(f"Discovered roles: {roles}")
    
    for role in roles:
        email = f"{role.lower()}@test.com"
        user = db.query(User).filter(User.username == email).first()
        if not user:
            user = User(
                username=email,
                full_name=f"Test {role}",
                role=role,
                hashed_password=get_password_hash('password123'),
                is_active=True
            )
            db.add(user)
            print(f"Created {email} / password123")
        else:
            user.role = role
            user.hashed_password = get_password_hash('password123')
            user.is_active = True
            print(f"Updated {email} / password123")
            
    db.commit()
    db.close()
    print("Seeding complete.")

if __name__ == "__main__":
    seed()
