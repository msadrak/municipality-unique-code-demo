#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
DEFAULT_CONTAINER = "municipality_postgres"


PHASE1_SCHEMAS = {
    2: {
        "title": "تصویب بودجه شورا",
        "description": "شماره مصوبه و مبلغ بودجه مصوب شورا را ثبت کنید. جزئیات تکمیلی را در پیوست‌ها بارگذاری کنید.",
        "type": "object",
        "properties": {
            "resolution_number": {
                "type": "string",
                "title": "شماره مصوبه",
                "placeholder": "1405/ش/102",
            },
            "approved_budget": {
                "type": "number",
                "title": "مبلغ مصوب",
                "placeholder": "25000000000",
            },
        },
        "required": ["resolution_number", "approved_budget"],
    },
    3: {
        "title": "تخمین ریالی هزینه انجام",
        "description": "برآورد اولیه هزینه پروژه را ثبت کنید و گزارش‌های محاسباتی را در پیوست‌ها قرار دهید.",
        "type": "object",
        "properties": {
            "estimated_cost": {
                "type": "number",
                "title": "برآورد هزینه ریالی",
                "placeholder": "18000000000",
            },
        },
        "required": ["estimated_cost"],
    },
    4: {
        "title": "ثبت در سامانه های مربوطه",
        "description": "برای فعال شدن مرحله، شماره ارجاع و توضیح کوتاه ثبت سامانه را وارد کنید.",
        "type": "object",
        "properties": {
            "reference_number": {
                "type": "string",
                "title": "شماره نامه / ارجاع",
                "placeholder": "SYS-1405-001",
            },
            "description": {
                "type": "string",
                "title": "توضیحات",
                "widget": "textarea",
                "placeholder": "خلاصه ثبت در سامانه های مرتبط",
            },
        },
        "required": ["reference_number"],
    },
    5: {
        "title": "ارسال به سازمان طراحی",
        "description": "شماره نامه ارجاع به سازمان طراحی و توضیح مختصر را ثبت کنید.",
        "type": "object",
        "properties": {
            "reference_number": {
                "type": "string",
                "title": "شماره نامه / ارجاع",
                "placeholder": "DES-1405-014",
            },
            "description": {
                "type": "string",
                "title": "توضیحات",
                "widget": "textarea",
                "placeholder": "شرح ارسال پرونده به سازمان طراحی",
            },
        },
        "required": ["reference_number"],
    },
    6: {
        "title": "جلسات کمیته فنی فاز 1",
        "description": "برای ثبت جلسه، شماره ارجاع و جمع بندی کوتاه را وارد کنید.",
        "type": "object",
        "properties": {
            "reference_number": {
                "type": "string",
                "title": "شماره نامه / ارجاع",
                "placeholder": "TC1-1405-008",
            },
            "description": {
                "type": "string",
                "title": "توضیحات",
                "widget": "textarea",
                "placeholder": "خلاصه تصمیمات کمیته فنی فاز 1",
            },
        },
        "required": ["reference_number"],
    },
    7: {
        "title": "جلسات اولویت بندی زمان طراحی",
        "description": "شماره جلسه یا نامه و نتیجه اولویت بندی را ثبت کنید.",
        "type": "object",
        "properties": {
            "reference_number": {
                "type": "string",
                "title": "شماره نامه / ارجاع",
                "placeholder": "PRIO-1405-003",
            },
            "description": {
                "type": "string",
                "title": "توضیحات",
                "widget": "textarea",
                "placeholder": "نتیجه اولویت بندی زمان طراحی",
            },
        },
        "required": ["reference_number"],
    },
    8: {
        "title": "تهیه فرم های مستندسازی",
        "description": "شماره ارجاع و وضعیت تهیه فرم‌های مستندسازی را ثبت کنید.",
        "type": "object",
        "properties": {
            "reference_number": {
                "type": "string",
                "title": "شماره نامه / ارجاع",
                "placeholder": "DOC-1405-017",
            },
            "description": {
                "type": "string",
                "title": "توضیحات",
                "widget": "textarea",
                "placeholder": "شرح فرم‌های آماده شده و مدارک پیوست",
            },
        },
        "required": ["reference_number"],
    },
    9: {
        "title": "تکمیل اطلاعات درخواستی طراحی",
        "description": "شماره ارجاع تکمیل اطلاعات و توضیح کوتاه را ثبت کنید.",
        "type": "object",
        "properties": {
            "reference_number": {
                "type": "string",
                "title": "شماره نامه / ارجاع",
                "placeholder": "REQ-1405-021",
            },
            "description": {
                "type": "string",
                "title": "توضیحات",
                "widget": "textarea",
                "placeholder": "خلاصه اطلاعات تکمیل شده برای طراحی",
            },
        },
        "required": ["reference_number"],
    },
    10: {
        "title": "جلسات کمیته فنی فاز 2",
        "description": "شماره جلسه یا نامه و جمع بندی فاز 2 را ثبت کنید.",
        "type": "object",
        "properties": {
            "reference_number": {
                "type": "string",
                "title": "شماره نامه / ارجاع",
                "placeholder": "TC2-1405-004",
            },
            "description": {
                "type": "string",
                "title": "توضیحات",
                "widget": "textarea",
                "placeholder": "جمع بندی جلسات کمیته فنی فاز 2",
            },
        },
        "required": ["reference_number"],
    },
    11: {
        "title": "بررسی طرح توسط کارشناسان معاونت عمران",
        "description": "شماره ارجاع بررسی و نتیجه کارشناسی را ثبت کنید.",
        "type": "object",
        "properties": {
            "reference_number": {
                "type": "string",
                "title": "شماره نامه / ارجاع",
                "placeholder": "DTR-1405-009",
            },
            "description": {
                "type": "string",
                "title": "توضیحات",
                "widget": "textarea",
                "placeholder": "نتیجه بررسی کارشناسان معاونت عمران",
            },
        },
        "required": ["reference_number"],
    },
}


def load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


def load_database_url() -> str:
    env_values = load_dotenv(ENV_PATH)
    return os.environ.get("DATABASE_URL") or env_values.get("DATABASE_URL", "")


def parse_database_identity() -> tuple[str, str]:
    database_url = load_database_url()
    if not database_url:
        return "postgres", "municipality_demo"

    parsed = urlparse(database_url)
    username = parsed.username or "postgres"
    database = parsed.path.lstrip("/") or "municipality_demo"
    return username, database


def build_sql() -> str:
    case_clauses = []
    for step_number, schema in PHASE1_SCHEMAS.items():
        schema_json = json.dumps(schema, ensure_ascii=False)
        case_clauses.append(
            f"WHEN {step_number} THEN $json${schema_json}$json$::jsonb"
        )

    return f"""
DO $$
DECLARE
    missing_steps text;
BEGIN
    SELECT string_agg(expected.step_number::text, ', ')
    INTO missing_steps
    FROM generate_series(2, 11) AS expected(step_number)
    WHERE NOT EXISTS (
        SELECT 1
        FROM workflow_step_definitions definitions
        WHERE definitions.step_number = expected.step_number
    );

    IF missing_steps IS NOT NULL THEN
        RAISE EXCEPTION 'Missing workflow_step_definitions for step_number(s): %', missing_steps;
    END IF;
END $$;

UPDATE workflow_step_definitions
SET form_schema = CASE step_number
    {' '.join(case_clauses)}
    ELSE form_schema
END
WHERE step_number BETWEEN 2 AND 11;

SELECT
    step_number,
    required_form_type,
    jsonb_typeof(form_schema) AS schema_type,
    form_schema->>'title' AS schema_title,
    form_schema->'required' AS required_fields
FROM workflow_step_definitions
WHERE step_number BETWEEN 2 AND 11
ORDER BY step_number;
""".strip()


def run_sql(sql: str) -> subprocess.CompletedProcess[str]:
    database_url = load_database_url()
    username, database = parse_database_identity()
    psql_path = shutil.which("psql")

    if psql_path and database_url:
        return subprocess.run(
            [psql_path, database_url, "-v", "ON_ERROR_STOP=1", "-f", "-"],
            input=sql,
            text=True,
            capture_output=True,
            cwd=PROJECT_ROOT,
            check=False,
        )

    docker_path = shutil.which("docker")
    if docker_path:
        container = os.environ.get("POSTGRES_DOCKER_CONTAINER", DEFAULT_CONTAINER)
        return subprocess.run(
            [
                docker_path,
                "exec",
                "-i",
                container,
                "psql",
                "-U",
                username,
                "-d",
                database,
                "-v",
                "ON_ERROR_STOP=1",
                "-f",
                "-",
            ],
            input=sql,
            text=True,
            capture_output=True,
            cwd=PROJECT_ROOT,
            check=False,
        )

    raise RuntimeError(
        "Neither `psql` nor `docker` is available. Install one of them or set up a supported execution path."
    )


def main() -> int:
    sql = build_sql()
    result = run_sql(sql)

    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        return result.returncode

    print("\nPhase 1 schemas for steps 2-11 were patched successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
