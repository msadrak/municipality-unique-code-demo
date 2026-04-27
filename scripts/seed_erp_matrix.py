"""Seed the ERP organization hierarchy and financial mapping matrix."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app.database import SessionLocal
from app.models import Activity, FinancialRule, OrgUnit, OrgUnitType


MOCK_EXCEL_DATA = {
    "deputy": {
        "name": "معاونت توسعه منابع",
        "type": OrgUnitType.DEPUTY.value,
        "departments": [
            {
                "name": "اداره کل منابع انسانی",
                "type": OrgUnitType.DEPARTMENT.value,
                "units": [
                    {
                        "name": "رفاه",
                        "type": OrgUnitType.UNIT.value,
                        "activities": [
                            {
                                "name": "شارژ بن کارت",
                                "description": "شارژ مزایای رفاهی کارکنان در سامانه بن کارت.",
                                "is_active": True,
                                "financial_rule": {
                                    "cost_center_code": "CC-101",
                                    "budget_line_code": "BL-2020-5",
                                    "financial_event_type": "REWARD_BONUS",
                                    "is_active": True,
                                },
                            }
                        ],
                    },
                    {
                        "name": "حفاظت فیزیکی",
                        "type": OrgUnitType.UNIT.value,
                        "activities": [
                            {
                                "name": "تسویه کارکرد پیمانکاران",
                                "description": "ثبت و تسویه کارکرد ماهانه پیمانکاران حفاظت فیزیکی.",
                                "is_active": True,
                                "financial_rule": {
                                    "cost_center_code": "CC-102",
                                    "budget_line_code": "BL-2020-8",
                                    "financial_event_type": "CONTRACTOR_PAYROLL",
                                    "is_active": True,
                                },
                            }
                        ],
                    },
                ],
            }
        ],
    }
}


def get_or_create_org_unit(db, *, name: str, unit_type: str, parent_id: int | None) -> OrgUnit:
    org_unit = db.query(OrgUnit).filter_by(name=name, parent_id=parent_id).first()

    if org_unit is None:
        org_unit = OrgUnit(name=name, type=unit_type, parent_id=parent_id)
        db.add(org_unit)
        db.flush()
        print(
            f"[ORG_UNIT] created id={org_unit.id} type={unit_type} "
            f"parent_id={parent_id} name={name}"
        )
        return org_unit

    changed = False
    if org_unit.type != unit_type:
        org_unit.type = unit_type
        changed = True

    if changed:
        db.flush()

    print(
        f"[ORG_UNIT] existing id={org_unit.id} type={org_unit.type} "
        f"parent_id={org_unit.parent_id} name={org_unit.name}"
    )
    return org_unit


def get_or_create_activity(db, *, unit: OrgUnit, payload: dict) -> Activity:
    activity = db.query(Activity).filter_by(name=payload["name"], org_unit_id=unit.id).first()

    if activity is None:
        activity = Activity(
            name=payload["name"],
            org_unit_id=unit.id,
            description=payload.get("description"),
            is_active=payload.get("is_active", True),
        )
        db.add(activity)
        db.flush()
        print(
            f"[ACTIVITY] created id={activity.id} org_unit_id={activity.org_unit_id} "
            f"name={activity.name}"
        )
        return activity

    activity.description = payload.get("description")
    activity.is_active = payload.get("is_active", True)
    db.flush()
    print(
        f"[ACTIVITY] existing id={activity.id} org_unit_id={activity.org_unit_id} "
        f"name={activity.name}"
    )
    return activity


def get_or_create_financial_rule(db, *, activity: Activity, payload: dict) -> FinancialRule:
    rule = db.query(FinancialRule).filter_by(activity_id=activity.id).first()

    if rule is None:
        rule = FinancialRule(
            activity_id=activity.id,
            cost_center_code=payload["cost_center_code"],
            budget_line_code=payload["budget_line_code"],
            financial_event_type=payload["financial_event_type"],
            is_active=payload.get("is_active", True),
        )
        db.add(rule)
        db.flush()
        print(
            f"[RULE] created id={rule.id} activity_id={rule.activity_id} "
            f"event={rule.financial_event_type}"
        )
        return rule

    rule.cost_center_code = payload["cost_center_code"]
    rule.budget_line_code = payload["budget_line_code"]
    rule.financial_event_type = payload["financial_event_type"]
    rule.is_active = payload.get("is_active", True)
    db.flush()
    print(
        f"[RULE] existing id={rule.id} activity_id={rule.activity_id} "
        f"event={rule.financial_event_type}"
    )
    return rule


def seed_matrix() -> None:
    db = SessionLocal()
    created_activities: list[Activity] = []
    created_rules: list[FinancialRule] = []

    try:
        deputy_payload = MOCK_EXCEL_DATA["deputy"]
        deputy = get_or_create_org_unit(
            db,
            name=deputy_payload["name"],
            unit_type=deputy_payload["type"],
            parent_id=None,
        )

        for department_payload in deputy_payload["departments"]:
            department = get_or_create_org_unit(
                db,
                name=department_payload["name"],
                unit_type=department_payload["type"],
                parent_id=deputy.id,
            )

            for unit_payload in department_payload["units"]:
                unit = get_or_create_org_unit(
                    db,
                    name=unit_payload["name"],
                    unit_type=unit_payload["type"],
                    parent_id=department.id,
                )

                for activity_payload in unit_payload["activities"]:
                    activity = get_or_create_activity(db, unit=unit, payload=activity_payload)
                    rule = get_or_create_financial_rule(
                        db,
                        activity=activity,
                        payload=activity_payload["financial_rule"],
                    )
                    created_activities.append(activity)
                    created_rules.append(rule)

        db.commit()

        print("\n=== ERP Matrix Summary ===")
        for activity in created_activities:
            print(
                f"Activity alive -> id={activity.id} name={activity.name} "
                f"org_unit_id={activity.org_unit_id}"
            )
        for rule in created_rules:
            print(
                f"FinancialRule alive -> id={rule.id} activity_id={rule.activity_id} "
                f"cost_center={rule.cost_center_code} budget_line={rule.budget_line_code} "
                f"event_type={rule.financial_event_type}"
            )
        print("Seed completed successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_matrix()
