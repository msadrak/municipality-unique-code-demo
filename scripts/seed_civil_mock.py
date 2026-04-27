from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.database import SessionLocal
from app.models import (
    Activity,
    CivilProject,
    CivilProjectAssignment,
    CivilProjectRole,
    Contractor,
    FinancialRule,
    OrgUnit,
    User,
    WorkflowStep,
)
from app.models.enums import UserRole

DEFAULT_PASSWORD = "password123"
FINANCIAL_EVENT = "پرداخت صورت‌وضعیت پیمانکاری"


@dataclass(frozen=True)
class ActivitySeed:
    name: str
    description: str
    cost_center_code: str
    budget_line_code: str


@dataclass(frozen=True)
class UserSeed:
    email: str
    role: UserRole
    full_name: str


ACTIVITY_SEEDS: tuple[ActivitySeed, ...] = (
    ActivitySeed(
        name="زیرسازی و روکش آسفالت معابر",
        description="فعالیت عمرانی مرتبط با زیرسازی، مرمت و روکش آسفالت معابر منطقه ۱۴",
        cost_center_code="CC-CIVIL-14",
        budget_line_code="BL5-40201",
    ),
    ActivitySeed(
        name="احداث و توسعه فضای سبز",
        description="فعالیت عمرانی مرتبط با احداث بوستان و توسعه فضای سبز منطقه ۱۴",
        cost_center_code="CC-CIVIL-14",
        budget_line_code="BL5-40202",
    ),
)

USER_SEEDS: tuple[UserSeed, ...] = (
    UserSeed("civil@test.com", UserRole.CIVIL_MANAGER, "مدیر عمران منطقه"),
    UserSeed("tender@test.com", UserRole.TENDERING_OFFICER, "مسئول مناقصات"),
    UserSeed("contract@test.com", UserRole.CONTRACTS_OFFICER, "مسئول قراردادها"),
    UserSeed("supervisor@test.com", UserRole.SUPERVISOR, "ناظر مقیم"),
    UserSeed("commission@test.com", UserRole.DELIVERY_COMMISSION, "دبیر کمیسیون"),
    UserSeed("contractor@test.com", UserRole.CONTRACTOR, "شرکت پیمانکاری راه و باند"),
    UserSeed("finance@test.com", UserRole.FINANCE_MANAGER, "ذی‌حساب عمران"),
)

PROJECT_SEEDS = (
    {
        "project_code": "CIV-14-001",
        "title": "طراحی تقاطع غیرهمسطح",
        "current_phase": 1,
        "current_step": 4,
        "activity_name": "زیرسازی و روکش آسفالت معابر",
        "planned_start_date": date(2026, 4, 1),
        "planned_end_date": date(2026, 7, 31),
    },
    {
        "project_code": "CIV-14-002",
        "title": "مناقصه آسفالت خیابان پیروزی",
        "current_phase": 2,
        "current_step": 11,
        "activity_name": "زیرسازی و روکش آسفالت معابر",
        "planned_start_date": date(2026, 4, 10),
        "planned_end_date": date(2026, 9, 30),
    },
    {
        "project_code": "CIV-14-003",
        "title": "احداث بوستان سمیه",
        "current_phase": 3,
        "current_step": 19,
        "activity_name": "احداث و توسعه فضای سبز",
        "planned_start_date": date(2026, 3, 21),
        "planned_end_date": date(2026, 11, 20),
    },
    {
        "project_code": "CIV-14-004",
        "title": "تحویل ساختمان سرای محله",
        "current_phase": 4,
        "current_step": 28,
        "activity_name": "زیرسازی و روکش آسفالت معابر",
        "planned_start_date": date(2026, 2, 15),
        "planned_end_date": date(2026, 8, 15),
    },
)


def print_section(title: str) -> None:
    print("")
    print("=" * 80)
    print(title)
    print("=" * 80)


def print_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    if not rows:
        return

    widths = [
        max(len(header), *(len(row[index]) for row in rows))
        for index, header in enumerate(headers)
    ]
    border = "+-" + "-+-".join("-" * width for width in widths) + "-+"

    print(border)
    print("| " + " | ".join(header.ljust(widths[i]) for i, header in enumerate(headers)) + " |")
    print(border)
    for row in rows:
        print("| " + " | ".join(value.ljust(widths[i]) for i, value in enumerate(row)) + " |")
    print(border)


def find_or_create_region_14(db: Session) -> tuple[OrgUnit, str]:
    zone = (
        db.query(OrgUnit)
        .filter(
            (OrgUnit.code == "14")
            | (OrgUnit.title == "منطقه ۱۴")
            | (OrgUnit.title == "منطقه 14")
        )
        .first()
    )

    if zone:
        changed = False
        if zone.title != "منطقه ۱۴":
            zone.title = "منطقه ۱۴"
            changed = True
        if zone.code != "14":
            zone.code = "14"
            changed = True
        if (zone.org_type or "").upper() != "ZONE":
            zone.org_type = "ZONE"
            changed = True
        return zone, "updated" if changed else "existing"

    zone = OrgUnit(title="منطقه ۱۴", code="14", org_type="ZONE", parent_id=None)
    db.add(zone)
    db.flush()
    return zone, "created"


def find_or_create_activity(
    db: Session,
    *,
    org_unit: OrgUnit,
    spec: ActivitySeed,
) -> tuple[Activity, str]:
    activity = (
        db.query(Activity)
        .filter(
            Activity.org_unit_id == org_unit.id,
            Activity.name == spec.name,
        )
        .first()
    )
    if activity:
        changed = False
        if activity.description != spec.description:
            activity.description = spec.description
            changed = True
        if not activity.is_active:
            activity.is_active = True
            changed = True
        return activity, "updated" if changed else "existing"

    activity = Activity(
        org_unit_id=org_unit.id,
        name=spec.name,
        description=spec.description,
        is_active=True,
    )
    db.add(activity)
    db.flush()
    return activity, "created"


def ensure_financial_rule(
    db: Session,
    *,
    activity: Activity,
    spec: ActivitySeed,
) -> tuple[FinancialRule, str]:
    rule = (
        db.query(FinancialRule)
        .filter(
            FinancialRule.activity_id == activity.id,
            FinancialRule.cost_center_code == spec.cost_center_code,
            FinancialRule.budget_line_code == spec.budget_line_code,
            FinancialRule.financial_event_type == FINANCIAL_EVENT,
        )
        .first()
    )
    if rule:
        if not rule.is_active:
            rule.is_active = True
            return rule, "updated"
        return rule, "existing"

    rule = FinancialRule(
        activity_id=activity.id,
        cost_center_code=spec.cost_center_code,
        budget_line_code=spec.budget_line_code,
        financial_event_type=FINANCIAL_EVENT,
        is_active=True,
    )
    db.add(rule)
    db.flush()
    return rule, "created"


def find_or_create_contractor(db: Session) -> tuple[Contractor, str]:
    contractor = db.query(Contractor).filter(Contractor.national_id == "14000000014").first()
    if contractor:
        changed = False
        updates = {
            "company_name": "شرکت پیمانکاری راه و باند",
            "registration_number": "98765",
            "ceo_name": "محمد رضایی",
            "phone": "02177665544",
            "address": "تهران، منطقه ۱۴، خیابان پیروزی",
            "province": "تهران",
            "city": "تهران",
            "source_system": "MANUAL",
            "is_verified": True,
            "portal_enabled": True,
        }
        for field_name, value in updates.items():
            if getattr(contractor, field_name) != value:
                setattr(contractor, field_name, value)
                changed = True
        return contractor, "updated" if changed else "existing"

    contractor = Contractor(
        national_id="14000000014",
        company_name="شرکت پیمانکاری راه و باند",
        registration_number="98765",
        ceo_name="محمد رضایی",
        phone="02177665544",
        address="تهران، منطقه ۱۴، خیابان پیروزی",
        province="تهران",
        city="تهران",
        source_system="MANUAL",
        is_verified=True,
        portal_enabled=True,
    )
    db.add(contractor)
    db.flush()
    return contractor, "created"


def find_or_create_user(
    db: Session,
    *,
    spec: UserSeed,
    zone: OrgUnit,
    contractor: Contractor | None,
) -> tuple[User, str]:
    user = db.query(User).filter(User.username == spec.email).first()
    hashed_password = get_password_hash(DEFAULT_PASSWORD)

    if user:
        changed = False
        updates = {
            "full_name": spec.full_name,
            "role": spec.role.value,
            "is_active": True,
            "failed_attempts": 0,
            "default_zone_id": zone.id,
            "default_dept_id": None,
            "default_section_id": None,
            "contractor_id": contractor.id if contractor and spec.role == UserRole.CONTRACTOR else None,
            "hashed_password": hashed_password,
        }
        for field_name, value in updates.items():
            if getattr(user, field_name) != value:
                setattr(user, field_name, value)
                changed = True
        return user, "updated" if changed else "existing"

    user = User(
        username=spec.email,
        hashed_password=hashed_password,
        full_name=spec.full_name,
        role=spec.role.value,
        region_name=zone.title,
        contractor_id=contractor.id if contractor and spec.role == UserRole.CONTRACTOR else None,
        default_zone_id=zone.id,
        default_dept_id=None,
        default_section_id=None,
        is_active=True,
        failed_attempts=0,
    )
    db.add(user)
    db.flush()
    return user, "created"


def find_or_create_project(
    db: Session,
    *,
    zone: OrgUnit,
    activity: Activity,
    created_by: User,
    payload: dict[str, object],
) -> tuple[CivilProject, str]:
    current_step = ensure_workflow_step(
        db,
        phase_number=int(payload["current_phase"]),
        order_index=int(payload["current_step"]),
    )
    project = (
        db.query(CivilProject)
        .filter(CivilProject.project_code == payload["project_code"])
        .first()
    )

    if project:
        changed = False
        updates = {
            "title": payload["title"],
            "owning_org_unit_id": zone.id,
            "activity_id": activity.id,
            "created_by_id": created_by.id,
            "current_step_id": current_step.id,
            "planned_start_date": payload["planned_start_date"],
            "planned_end_date": payload["planned_end_date"],
            "is_active": True,
        }
        for field_name, value in updates.items():
            if getattr(project, field_name) != value:
                setattr(project, field_name, value)
                changed = True
        return project, "updated" if changed else "existing"

    project = CivilProject(
        project_code=str(payload["project_code"]),
        title=str(payload["title"]),
        owning_org_unit_id=zone.id,
        activity_id=activity.id,
        created_by_id=created_by.id,
        current_step_id=current_step.id,
        planned_start_date=payload["planned_start_date"],
        planned_end_date=payload["planned_end_date"],
        is_active=True,
    )
    db.add(project)
    db.flush()
    return project, "created"


def ensure_workflow_step(
    db: Session,
    *,
    phase_number: int,
    order_index: int,
) -> WorkflowStep:
    code = f"CIVIL_STEP_{order_index:02d}"
    step = db.query(WorkflowStep).filter(WorkflowStep.code == code).first()
    if step is None:
        step = WorkflowStep(
            code=code,
            name=f"Civil workflow step {order_index}",
            phase_number=phase_number,
            order_index=order_index,
        )
        db.add(step)
        db.flush()
        return step

    changed = False
    for field_name, value in {
        "name": f"Civil workflow step {order_index}",
        "phase_number": phase_number,
        "order_index": order_index,
    }.items():
        if getattr(step, field_name) != value:
            setattr(step, field_name, value)
            changed = True
    if changed:
        db.flush()
    return step


def ensure_assignment(
    db: Session,
    *,
    project: CivilProject,
    user: User,
    role: CivilProjectRole,
) -> tuple[CivilProjectAssignment, str]:
    assignment = (
        db.query(CivilProjectAssignment)
        .filter(
            CivilProjectAssignment.project_id == project.id,
            CivilProjectAssignment.user_id == user.id,
            CivilProjectAssignment.role == role,
        )
        .first()
    )
    if assignment:
        if not assignment.is_active:
            assignment.is_active = True
            return assignment, "updated"
        return assignment, "existing"

    assignment = CivilProjectAssignment(
        project_id=project.id,
        user_id=user.id,
        role=role,
        is_active=True,
    )
    db.add(assignment)
    db.flush()
    return assignment, "created"


def seed() -> None:
    db = SessionLocal()

    matrix_rows: list[tuple[str, str, str, str]] = []
    user_rows: list[tuple[str, str, str, str]] = []
    project_rows: list[tuple[str, str, str, str, str]] = []
    assignment_rows: list[tuple[str, str, str, str]] = []

    try:
        print_section("Step A - Financial Matrix Foundation")
        zone, zone_status = find_or_create_region_14(db)
        matrix_rows.append(("OrgUnit", zone_status, zone.code or "", zone.title or ""))

        activity_map: dict[str, Activity] = {}
        for spec in ACTIVITY_SEEDS:
            activity, activity_status = find_or_create_activity(db, org_unit=zone, spec=spec)
            rule, rule_status = ensure_financial_rule(db, activity=activity, spec=spec)
            activity_map[spec.name] = activity
            matrix_rows.append(("Activity", activity_status, str(activity.id), activity.name))
            matrix_rows.append(
                (
                    "FinancialRule",
                    rule_status,
                    spec.budget_line_code,
                    f"{activity.name} / {spec.cost_center_code}",
                )
            )

        print_table(("Kind", "Status", "Key", "Title"), matrix_rows)

        print_section("Step B - Users and Contractor Bridge")
        contractor, contractor_status = find_or_create_contractor(db)
        user_rows.append(("Contractor", contractor_status, contractor.national_id, contractor.company_name))

        user_map: dict[UserRole, User] = {}
        for spec in USER_SEEDS:
            linked_contractor = contractor if spec.role == UserRole.CONTRACTOR else None
            user, user_status = find_or_create_user(
                db,
                spec=spec,
                zone=zone,
                contractor=linked_contractor,
            )
            user_map[spec.role] = user
            user_rows.append((spec.role.value, user_status, user.username, user.full_name or ""))

        print_table(("Type", "Status", "Key", "Name"), user_rows)

        print_section("Step C - Civil Projects")
        for payload in PROJECT_SEEDS:
            activity = activity_map[str(payload["activity_name"])]
            project, project_status = find_or_create_project(
                db,
                zone=zone,
                activity=activity,
                created_by=user_map[UserRole.CIVIL_MANAGER],
                payload=payload,
            )
            project_rows.append(
                (
                    project.project_code,
                    project_status,
                    str(project.current_step.phase_number),
                    str(project.current_step.order_index),
                    activity.name,
                )
            )

        print_table(("Project Code", "Status", "Phase", "Step", "Activity"), project_rows)

        print_section("Step D - Project Assignments")
        role_assignments = (
            (CivilProjectRole.CIVIL_MANAGER, user_map[UserRole.CIVIL_MANAGER]),
            (CivilProjectRole.TENDERING_OFFICER, user_map[UserRole.TENDERING_OFFICER]),
            (CivilProjectRole.CONTRACTS_OFFICER, user_map[UserRole.CONTRACTS_OFFICER]),
            (CivilProjectRole.SUPERVISOR, user_map[UserRole.SUPERVISOR]),
            (CivilProjectRole.DELIVERY_COMMISSION, user_map[UserRole.DELIVERY_COMMISSION]),
            (CivilProjectRole.CONTRACTOR, user_map[UserRole.CONTRACTOR]),
            (CivilProjectRole.FINANCE_MANAGER, user_map[UserRole.FINANCE_MANAGER]),
        )

        projects = (
            db.query(CivilProject)
            .filter(CivilProject.project_code.in_([item["project_code"] for item in PROJECT_SEEDS]))
            .all()
        )
        for project in projects:
            for role, user in role_assignments:
                _, status = ensure_assignment(db, project=project, user=user, role=role)
                assignment_rows.append((project.project_code, role.value, user.username, status))

        print_table(("Project", "Role", "User", "Status"), assignment_rows)

        db.commit()

        print_section("Seeder Complete")
        print(f"Default password for seeded users: {DEFAULT_PASSWORD}")
        print(f"Seeded/verified projects: {len(project_rows)}")
        print(f"Seeded/verified assignments: {len(assignment_rows)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
