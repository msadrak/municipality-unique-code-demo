#!/usr/bin/env python3
from __future__ import annotations

import io
import sys
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from app.database import SessionLocal
from app.models.civil import WorkflowStep, WorkflowStepDefinition


def phase_for_step(step_number: int | None) -> int | None:
    if step_number is None:
        return None
    if step_number <= 11:
        return 1
    if step_number <= 18:
        return 2
    if step_number <= 34:
        return 3
    return 4


def fetch_missing_schema_steps(db: Session) -> list[tuple[WorkflowStepDefinition, int | None]]:
    return (
        db.query(WorkflowStepDefinition, WorkflowStep.phase_number)
        .outerjoin(WorkflowStep, WorkflowStep.step_definition_id == WorkflowStepDefinition.id)
        .filter(
            or_(
                WorkflowStepDefinition.form_schema.is_(None),
                WorkflowStepDefinition.form_schema == {},
            )
        )
        .order_by(
            WorkflowStep.phase_number.asc().nullslast(),
            WorkflowStepDefinition.step_number.asc(),
        )
        .all()
    )


def print_results(rows: list[tuple[WorkflowStepDefinition, int | None]]) -> None:
    print("\nWorkflow steps missing JSON schemas")
    print("=" * 43)

    if not rows:
        print("No workflow step definitions are missing form_schema.")
        return

    headers = ("Phase", "Step", "Name", "Required Form Type")
    rendered_rows = [
        (
            str(phase_number or phase_for_step(definition.step_number) or "-"),
            str(definition.step_number),
            definition.name,
            definition.required_form_type or "-",
        )
        for definition, phase_number in rows
    ]

    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rendered_rows))
        for index in range(len(headers))
    ]

    header_line = " | ".join(
        headers[index].ljust(widths[index]) for index in range(len(headers))
    )
    separator = "-+-".join("-" * width for width in widths)

    print(header_line)
    print(separator)
    for row in rendered_rows:
        print(" | ".join(row[index].ljust(widths[index]) for index in range(len(row))))

    print(f"\nTotal missing schemas: {len(rows)}")


def main() -> None:
    db = SessionLocal()
    try:
        print_results(fetch_missing_schema_steps(db))
    finally:
        db.close()


if __name__ == "__main__":
    main()
