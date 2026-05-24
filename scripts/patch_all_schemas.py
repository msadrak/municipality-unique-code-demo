#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import engine  # noqa: E402


GENERIC_SCHEMA = {
    "type": "object",
    "properties": {
        "action_remarks": {
            "type": "string",
            "title": "توضیحات / نظریه کارشناسی",
            "widget": "textarea",
        }
    },
}


def main() -> int:
    schema_json = json.dumps(GENERIC_SCHEMA, ensure_ascii=False)

    with engine.begin() as connection:
        missing_steps = connection.execute(
            text(
                """
                SELECT expected.step_number
                FROM generate_series(1, 39) AS expected(step_number)
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM workflow_step_definitions definitions
                    WHERE definitions.step_number = expected.step_number
                )
                ORDER BY expected.step_number
                """
            )
        ).scalars().all()
        if missing_steps:
            print(
                "Missing workflow_step_definitions for steps: "
                + ", ".join(str(step) for step in missing_steps),
                file=sys.stderr,
            )
            return 1

        patched_rows = connection.execute(
            text(
                """
                UPDATE workflow_step_definitions
                SET
                    required_form_type = COALESCE(
                        NULLIF(required_form_type, ''),
                        'GENERIC_STEP_' || lpad(step_number::text, 2, '0')
                    ),
                    form_schema = CASE
                        WHEN form_schema IS NULL
                            OR form_schema = '{}'::jsonb
                            OR form_schema = 'null'::jsonb
                        THEN CAST(:schema_json AS jsonb)
                        ELSE form_schema
                    END
                WHERE step_number BETWEEN 1 AND 39
                  AND (
                    required_form_type IS NULL
                    OR required_form_type = ''
                    OR form_schema IS NULL
                    OR form_schema = '{}'::jsonb
                    OR form_schema = 'null'::jsonb
                  )
                RETURNING step_number, required_form_type
                """
            ),
            {"schema_json": schema_json},
        ).mappings().all()

        total_rows = connection.execute(
            text(
                """
                SELECT count(*)
                FROM workflow_step_definitions
                WHERE step_number BETWEEN 1 AND 39
                  AND required_form_type IS NOT NULL
                  AND required_form_type <> ''
                  AND form_schema IS NOT NULL
                  AND form_schema <> '{}'::jsonb
                  AND form_schema <> 'null'::jsonb
                """
            )
        ).scalar_one()

    print(f"Patched workflow schema fallbacks for {len(patched_rows)} step(s).")
    print(f"Workflow steps with usable form types and schemas: {total_rows}/39.")
    if patched_rows:
        patched = ", ".join(
            f"{row['step_number']}:{row['required_form_type']}" for row in patched_rows
        )
        print(f"Updated steps: {patched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
