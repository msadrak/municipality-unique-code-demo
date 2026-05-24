#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import engine  # noqa: E402


STEP_NUMBER = 15
FORM_TYPE = "CONTRACTOR_ASSIGNMENT"

CONTRACTOR_ASSIGNMENT_SCHEMA = {
    "title": "تعیین پیمانکار برنده",
    "description": "اطلاعات هویتی و مالی پیمانکار برنده را همراه با صورتجلسه کمیسیون ثبت کنید.",
    "type": "object",
    "properties": {
        "contractor_name": {"type": "string", "title": "نام پیمانکار"},
        "national_id": {"type": "string", "title": "کد ملی / شناسه حقوقی"},
        "phone_number": {"type": "string", "title": "شماره موبایل"},
        "winning_bid": {"type": "number", "title": "مبلغ پیشنهادی برنده - ریال"},
        "contract_coefficient": {"type": "number", "title": "ضریب پیمان"},
    },
    "required": [
        "contractor_name",
        "national_id",
        "phone_number",
        "winning_bid",
        "contract_coefficient",
    ],
}


def main() -> int:
    schema_json = json.dumps(CONTRACTOR_ASSIGNMENT_SCHEMA, ensure_ascii=False)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                ALTER TABLE civil_projects
                ADD COLUMN IF NOT EXISTS contractor_id INTEGER NULL
                """
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'fk_civil_projects_contractor_id_users'
                    ) THEN
                        ALTER TABLE civil_projects
                        ADD CONSTRAINT fk_civil_projects_contractor_id_users
                        FOREIGN KEY (contractor_id)
                        REFERENCES users(id)
                        ON DELETE SET NULL;
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_civil_projects_contractor_id
                ON civil_projects(contractor_id)
                """
            )
        )

        updated = connection.execute(
            text(
                """
                UPDATE workflow_step_definitions
                SET required_form_type = :form_type,
                    form_schema = CAST(:schema_json AS jsonb)
                WHERE step_number = :step_number
                RETURNING step_number, name, required_form_type, form_schema->>'title' AS schema_title
                """
            ),
            {
                "form_type": FORM_TYPE,
                "schema_json": schema_json,
                "step_number": STEP_NUMBER,
            },
        ).mappings().first()

    if updated is None:
        print(f"Step {STEP_NUMBER} was not found in workflow_step_definitions.", file=sys.stderr)
        return 1

    print(
        "Contractor assignment schema patched: "
        f"step={updated['step_number']}, form={updated['required_form_type']}, "
        f"schema_title={updated['schema_title'].encode('unicode_escape').decode('ascii')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
