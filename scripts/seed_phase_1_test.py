from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.security import get_password_hash
from app.database import SessionLocal
from app.models import (
    Activity,
    ApprovalTask,
    ApprovalTaskStatus,
    CivilProject,
    CivilProjectAssignment,
    CivilProjectRole,
    OrgUnit,
    StepAction,
    User,
    WorkflowStep,
)
from app.models.enums import UserRole


PROJECT_CODE = "CIVIL-PHASE1-TEST-1405"
PROJECT_TITLE = "تست فاز ۱ - برنامه‌ریزی و طراحی"
PHASE_1_USERNAME = "civil@test.com"
PHASE_1_PASSWORD = "password123"
PHASE_1_STEP_1_SCHEMA = {
    "title": "تعریف پروژه برای سال آینده",
    "description": "فقط اطلاعات پایه را وارد کنید و مدارک فنی، فرم‌های طراحی و مستندات تفصیلی را در بخش پیوست‌ها بارگذاری کنید.",
    "type": "object",
    "properties": {
        "project_title": {
            "type": "string",
            "title": "عنوان پروژه",
            "placeholder": PROJECT_TITLE,
        },
        "reference_number": {
            "type": "string",
            "title": "شماره نامه / ارجاع",
            "placeholder": "REF-1405-001",
        },
    },
    "required": ["project_title", "reference_number"],
}


def upsert_org_unit(db: Session) -> OrgUnit:
    zone = db.query(OrgUnit).filter(OrgUnit.code == "PHASE1-TEST").first()
    if zone is None:
        zone = OrgUnit(code="PHASE1-TEST")
        db.add(zone)
        db.flush()
    zone.title = "منطقه تست فاز ۱"
    zone.org_type = "ZONE"
    return zone


def upsert_activity(db: Session, zone: OrgUnit) -> Activity:
    activity = (
        db.query(Activity)
        .filter(
            Activity.org_unit_id == zone.id,
            Activity.name == "برنامه‌ریزی و طراحی پروژه‌های عمرانی",
        )
        .first()
    )
    if activity is None:
        activity = Activity(
            org_unit_id=zone.id,
            name="برنامه‌ریزی و طراحی پروژه‌های عمرانی",
        )
        db.add(activity)
        db.flush()
    activity.description = "فعالیت تست برای بررسی مراحل ۱ تا ۱۱ گردش کار عمرانی"
    activity.is_active = True
    return activity


def upsert_civil_user(db: Session, zone: OrgUnit) -> User:
    user = db.query(User).filter(User.username == PHASE_1_USERNAME).first()
    if user is None:
        user = User(username=PHASE_1_USERNAME)
        db.add(user)
        db.flush()

    user.full_name = "کارشناس عمران تست فاز ۱"
    user.role = UserRole.CIVIL_MANAGER.value
    user.region_name = zone.title
    user.default_zone_id = zone.id
    user.hashed_password = get_password_hash(PHASE_1_PASSWORD)
    user.is_active = True
    user.failed_attempts = 0
    user.locked_until = None
    return user


def get_phase_1_step(db: Session) -> WorkflowStep:
    step = db.query(WorkflowStep).filter(WorkflowStep.order_index == 1).first()
    if step is None:
        raise RuntimeError(
            "Workflow step 1 was not found. Run Alembic migration b7c4d9e2f103 first."
        )
    expected_name = "تعریف پروژه برای سال آینده..."
    if step.name != expected_name:
        raise RuntimeError(
            f"Workflow step 1 is '{step.name}', expected '{expected_name}'. "
            "Re-run migration b7c4d9e2f103."
        )
    if step.definition is None:
        raise RuntimeError("Workflow step 1 is not linked to a WorkflowStepDefinition.")
    step.definition.form_schema = PHASE_1_STEP_1_SCHEMA
    step.definition.required_form_type = "NEXT_YEAR_PROJECT_DEFINITION"
    return step


def ensure_project_assignment(db: Session, project: CivilProject, user: User) -> None:
    assignment = (
        db.query(CivilProjectAssignment)
        .filter(
            CivilProjectAssignment.project_id == project.id,
            CivilProjectAssignment.user_id == user.id,
            CivilProjectAssignment.role == CivilProjectRole.CIVIL_MANAGER,
        )
        .first()
    )
    if assignment is None:
        assignment = CivilProjectAssignment(
            project_id=project.id,
            user_id=user.id,
            role=CivilProjectRole.CIVIL_MANAGER,
        )
        db.add(assignment)
    assignment.is_active = True


def ensure_step_action(db: Session, step: WorkflowStep) -> StepAction:
    if step.definition is None:
        raise RuntimeError("Workflow step 1 is not linked to a WorkflowStepDefinition.")

    action = (
        db.query(StepAction)
        .filter(
            StepAction.step_definition_id == step.definition.id,
            StepAction.assigned_role == UserRole.CIVIL_MANAGER.value,
        )
        .first()
    )
    if action is None:
        action = StepAction(
            step_definition_id=step.definition.id,
            assigned_role=UserRole.CIVIL_MANAGER.value,
        )
        db.add(action)
        db.flush()
    action.is_required = True
    action.order_index = 1
    return action


def upsert_project(
    db: Session,
    *,
    zone: OrgUnit,
    activity: Activity,
    user: User,
    step: WorkflowStep,
) -> CivilProject:
    project = db.query(CivilProject).filter(CivilProject.project_code == PROJECT_CODE).first()
    if project is None:
        project = CivilProject(project_code=PROJECT_CODE)
        db.add(project)

    project.title = PROJECT_TITLE
    project.owning_org_unit_id = zone.id
    project.activity_id = activity.id
    project.created_by_id = user.id
    project.current_step_id = step.id
    project.planned_start_date = date(2026, 3, 21)
    project.planned_end_date = date(2026, 9, 22)
    project.is_active = True
    project.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.flush()
    return project


def seed() -> None:
    db = SessionLocal()
    try:
        step = get_phase_1_step(db)
        zone = upsert_org_unit(db)
        activity = upsert_activity(db, zone)
        civil_user = upsert_civil_user(db, zone)
        project = upsert_project(
            db,
            zone=zone,
            activity=activity,
            user=civil_user,
            step=step,
        )
        ensure_project_assignment(db, project, civil_user)
        action = ensure_step_action(db, step)

        db.query(ApprovalTask).filter(ApprovalTask.project_id == project.id).delete(
            synchronize_session=False
        )
        task = ApprovalTask(
            project_id=project.id,
            step_id=step.id,
            step_action_id=action.id,
            assigned_role=UserRole.CIVIL_MANAGER.value,
            assigned_user_id=civil_user.id,
            status=ApprovalTaskStatus.PENDING,
            is_required=True,
            comments="تکلیف شروع تست فاز ۱ برای تعریف پروژه سال آینده",
        )
        db.add(task)

        db.commit()
        db.refresh(project)
        db.refresh(task)

        print("Phase 1 civil workflow test seed complete.")
        print(f"Project: {project.project_code} - {project.title}")
        print(f"Current step: {step.order_index} - {step.name}")
        print(f"Assigned task: #{task.id} -> {civil_user.username} ({civil_user.role})")
        print(f"Login: {civil_user.username} / {PHASE_1_PASSWORD}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
