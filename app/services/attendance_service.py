import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Callable, Optional

from fastapi import HTTPException, UploadFile
from openpyxl import load_workbook
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.attendance import (
    AttendanceRecord,
    ContractorStatement,
    ContractorStatementItem,
    RegionalAttendanceSheet,
)
from app.models.enums import AttendanceSheetStatus
from app.schemas.attendance import (
    AttendanceAggregationItem,
    AttendanceAggregationOut,
    AttendanceReconciliationOut,
    SheetMetaSummary,
    WorkflowStatusLabel,
)

EXCEL_SKIPROWS = 2
EXCEL_HEADER_ROW_NUMBER = 3
EXCEL_DATA_START_ROW_NUMBER = EXCEL_HEADER_ROW_NUMBER + 1

ATTENDANCE_FIELD_ORDER = [
    "location",
    "full_name",
    "father_name",
    "national_id",
    "marital_status",
    "children_count",
    "start_date",
    "average_per_capita",
    "min_paid_hours",
    "max_paid_hours",
    "monthly_performance_days",
    "monthly_absence_days",
    "overtime_replacement",
    "overtime_hours",
    "total_average_per_capita",
    "total_overtime_given",
    "performance_balance",
]

ATTENDANCE_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "location": ("موقعیت",),
    "full_name": ("نام و نام خانوادگی", "نام ونام خانوادگی", "full_name"),
    "father_name": ("نام پدر",),
    "national_id": ("شماره ملی",),
    "marital_status": ("وضعیت تاهل", "وضعیت تأهل"),
    "children_count": ("تعداد فرزند",),
    "start_date": ("تاریخ شروع به کار",),
    "average_per_capita": ("میانگین سرانه", "amount"),
    "min_paid_hours": ("حداقل ساعت پرداختی",),
    "max_paid_hours": ("حداکثر ساعت پرداختی",),
    "monthly_performance_days": ("کارکرد ماهانه روز",),
    "monthly_absence_days": ("غیبت ماهانه روز",),
    "overtime_replacement": ("اضافه کار جایگزین مرخصی",),
    "overtime_hours": ("اضافه کار", "worked"),
    "total_average_per_capita": ("جمع کل میانگین سرانه", "total_sum", "total"),
    "total_overtime_given": ("جمع کل اضافه کار داده شده",),
    "performance_balance": ("مانده کارکرد", "description"),
}

SERIAL_COLUMN_KEYS = {
    "ردیف",
    "row",
    "index",
    "شماره",
}

SUMMARY_ROW_MARKERS = {
    "جمعکل",
    "جمع",
    "تنظیمکننده",
}

_ARABIC_CHAR_TRANSLATION = str.maketrans(
    {
        "ي": "ی",
        "ك": "ک",
        "ة": "ه",
        "ۀ": "ه",
    }
)
_PERSIAN_DIGIT_TRANSLATION = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)


def _normalize_text(value: str) -> str:
    normalized = value.translate(_ARABIC_CHAR_TRANSLATION)
    normalized = normalized.replace("\u200c", " ").replace("\xa0", " ")
    normalized = normalized.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", normalized).strip()


def _compact_text(value: str) -> str:
    normalized = _normalize_text(value).lower()
    return re.sub(r"[\s\-_()/\\:؛،,.]+", "", normalized)


def _is_missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        cleaned = _normalize_text(value).lower()
        return cleaned in {"", "nan", "none", "null", "nat"}
    try:
        return value != value
    except Exception:
        return False


def _safe_string(value) -> Optional[str]:
    if _is_missing(value):
        return None
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    cleaned = _normalize_text(str(value))
    return cleaned or None


def _safe_decimal(value) -> Optional[Decimal]:
    if _is_missing(value):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    normalized = (_safe_string(value) or "").translate(_PERSIAN_DIGIT_TRANSLATION)
    normalized = normalized.replace("−", "-").replace("–", "-").replace("—", "-")
    normalized = normalized.replace("٬", "").replace("،", "").replace(",", "")
    normalized = normalized.replace("٫", ".").replace(" ", "")
    if normalized in {"", "-", ".", "-."}:
        return None

    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None


def _safe_int(value) -> Optional[int]:
    decimal_value = _safe_decimal(value)
    if decimal_value is None:
        return None
    try:
        return int(decimal_value)
    except (ValueError, OverflowError):
        return None


FIELD_PARSERS: dict[str, Callable[[object], object]] = {
    "location": _safe_string,
    "full_name": _safe_string,
    "father_name": _safe_string,
    "national_id": _safe_string,
    "marital_status": _safe_string,
    "children_count": _safe_int,
    "start_date": _safe_string,
    "average_per_capita": _safe_decimal,
    "min_paid_hours": _safe_decimal,
    "max_paid_hours": _safe_decimal,
    "monthly_performance_days": _safe_decimal,
    "monthly_absence_days": _safe_decimal,
    "overtime_replacement": _safe_decimal,
    "overtime_hours": _safe_decimal,
    "total_average_per_capita": _safe_decimal,
    "total_overtime_given": _safe_decimal,
    "performance_balance": _safe_string,
}


def _build_column_mapping(columns) -> dict[str, object]:
    original_columns = list(columns)
    normalized_lookup: dict[str, object] = {}

    for column_name in original_columns:
        normalized = _compact_text(str(column_name))
        if normalized and normalized not in normalized_lookup:
            normalized_lookup[normalized] = column_name

    mapping: dict[str, object] = {}
    used_columns: set[object] = set()

    for field_name in ATTENDANCE_FIELD_ORDER:
        for alias in ATTENDANCE_COLUMN_ALIASES[field_name]:
            matched_column = normalized_lookup.get(_compact_text(alias))
            if matched_column is not None and matched_column not in used_columns:
                mapping[field_name] = matched_column
                used_columns.add(matched_column)
                break

    remaining_fields = [field for field in ATTENDANCE_FIELD_ORDER if field not in mapping]
    remaining_columns = [column for column in original_columns if column not in used_columns]

    if remaining_columns and _compact_text(str(remaining_columns[0])) in {
        _compact_text(value) for value in SERIAL_COLUMN_KEYS
    }:
        remaining_columns = remaining_columns[1:]

    if remaining_columns:
        # Fallback: map by column order when file provides a subset (for example 6-column templates).
        for field_name, column_name in zip(remaining_fields, remaining_columns):
            mapping[field_name] = column_name

    if "full_name" not in mapping:
        raise HTTPException(
            status_code=422,
            detail="Excel headers do not match the expected Regional Attendance template.",
        )

    return mapping


def _get_row_value(row, mapping: dict[str, object], field_name: str):
    column_name = mapping.get(field_name)
    if column_name is None:
        return None
    return row.get(column_name)


def _should_skip_row(row, mapping: dict[str, object]) -> bool:
    full_name = _safe_string(_get_row_value(row, mapping, "full_name"))
    if not full_name:
        return True

    compact_full_name = _compact_text(full_name)
    if compact_full_name in SUMMARY_ROW_MARKERS:
        return True
    if compact_full_name.startswith("جمعکل"):
        return True
    if compact_full_name == _compact_text("نام و نام خانوادگی"):
        return True

    return False


def _read_excel_rows(contents: bytes) -> tuple[list[object], list[dict[object, object]]]:
    try:
        workbook = load_workbook(io.BytesIO(contents), data_only=True, read_only=True)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Cannot parse Excel file: {exc}") from exc

    worksheet = workbook.active
    all_rows = list(worksheet.iter_rows(values_only=True))
    if len(all_rows) <= EXCEL_SKIPROWS:
        raise HTTPException(
            status_code=422,
            detail="Excel file does not contain any attendance rows.",
        )

    header_row = list(all_rows[EXCEL_SKIPROWS])
    data_rows = all_rows[EXCEL_SKIPROWS + 1 :]

    last_non_empty_index = -1
    for idx, value in enumerate(header_row):
        if not _is_missing(value):
            last_non_empty_index = idx

    if last_non_empty_index < 0:
        raise HTTPException(
            status_code=422,
            detail="Excel file does not contain any attendance headers.",
        )

    headers = header_row[: last_non_empty_index + 1]
    records: list[dict[object, object]] = []
    for row_values in data_rows:
        trimmed_values = list(row_values[: len(headers)])
        if all(_is_missing(value) for value in trimmed_values):
            continue
        records.append({header: value for header, value in zip(headers, trimmed_values)})

    if not records:
        raise HTTPException(
            status_code=422,
            detail="Excel file does not contain any attendance rows.",
        )

    return headers, records


def ingest_excel(
    file: UploadFile,
    title: str,
    year: int,
    month: int,
    region_name: str,
    creator_id: int,
    db: Session,
) -> RegionalAttendanceSheet:
    contents = file.file.read()
    columns, rows = _read_excel_rows(contents)
    template_kind = _infer_template_kind(columns)
    if template_kind == "statement_6":
        raise HTTPException(
            status_code=422,
            detail=(
                "Uploaded file appears to be the 6-column contractor statement template. "
                "Please upload it via /api/attendance/upload/statement."
            ),
        )
    if template_kind == "unknown":
        raise HTTPException(
            status_code=422,
            detail=(
                "Unsupported Excel template. Only 18-column regional attendance and "
                "6-column contractor statement templates are accepted."
            ),
        )

    column_mapping = _build_column_mapping(columns)

    sheet = db.query(RegionalAttendanceSheet).filter(
        RegionalAttendanceSheet.year == year,
        RegionalAttendanceSheet.month == month,
        RegionalAttendanceSheet.region == region_name,
    ).first()

    if not sheet:
        sheet = RegionalAttendanceSheet(
            title=title,
            year=year,
            month=month,
            region=region_name,
            original_filename=file.filename or "unknown.xlsx",
            row_count=0,
            status=AttendanceSheetStatus.DRAFT,
            created_by_id=creator_id,
        )
        db.add(sheet)
        db.flush()

    records: list[AttendanceRecord] = []
    for idx, row in enumerate(rows):
        if _should_skip_row(row, column_mapping):
            continue

        record_kwargs = {
            "sheet": sheet,
            "row_number": EXCEL_DATA_START_ROW_NUMBER + idx,
        }

        for field_name, parser in FIELD_PARSERS.items():
            record_kwargs[field_name] = parser(_get_row_value(row, column_mapping, field_name))

        if not record_kwargs["full_name"]:
            continue

        records.append(AttendanceRecord(**record_kwargs))

    sheet.row_count = sheet.row_count + len(records)

    try:
        db.add_all(records)
        db.commit()
        db.refresh(sheet)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database write failed: {str(exc)}") from exc

    return sheet


STATEMENT_FIELD_PARSERS: dict[str, Callable[[object], object]] = {
    "national_id": _safe_string,
    "full_name": _safe_string,
    "gross_amount": _safe_decimal,
    "tax_deduction": _safe_decimal,
    "insurance_deduction": _safe_decimal,
    "net_payable_amount": _safe_decimal,
}

STATEMENT_FIELD_ORDER = [
    "national_id",
    "full_name",
    "gross_amount",
    "tax_deduction",
    "insurance_deduction",
    "net_payable_amount",
]

STATEMENT_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "national_id": ("شماره ملی", "کد ملی", "national_id"),
    "full_name": ("نام و نام خانوادگی", "نام ونام خانوادگی", "full_name"),
    "gross_amount": ("مبلغ ناخالص", "ناخالص", "gross_amount"),
    "tax_deduction": ("مالیات", "کسورات مالیات", "tax"),
    "insurance_deduction": ("بیمه", "کسورات بیمه", "insurance"),
    "net_payable_amount": ("مبلغ قابل پرداخت", "خالص پرداختی", "مبلغ خالص", "net_amount"),
}

STATEMENT_TOTAL_ROW_MARKERS = {
    _compact_text("جمع کل"),
    _compact_text("جمع کل ریال"),
    _compact_text("جمع کل (ریال)"),
    _compact_text("جمع‌کل"),
}


def _count_alias_matches(columns, aliases_map: dict[str, tuple[str, ...]]) -> int:
    normalized_columns = {
        _compact_text(str(column))
        for column in columns
        if not _is_missing(column)
    }
    matches = 0
    for aliases in aliases_map.values():
        if any(_compact_text(alias) in normalized_columns for alias in aliases):
            matches += 1
    return matches


def _infer_template_kind(columns) -> str:
    """Return one of: attendance_18, statement_6, unknown."""
    effective_columns = [column for column in columns if not _is_missing(column)]
    column_count = len(effective_columns)

    attendance_hits = _count_alias_matches(effective_columns, ATTENDANCE_COLUMN_ALIASES)
    statement_hits = _count_alias_matches(effective_columns, STATEMENT_COLUMN_ALIASES)

    if statement_hits >= 4 and column_count <= 8:
        return "statement_6"
    if attendance_hits >= 6 and column_count >= 10:
        return "attendance_18"

    # Fallback by column count for header variants that still follow known templates.
    if column_count <= 8:
        return "statement_6"
    if column_count >= 12:
        return "attendance_18"
    return "unknown"


def _build_statement_column_mapping(columns) -> dict[str, object]:
    original_columns = list(columns)
    normalized_lookup: dict[str, object] = {}

    for column_name in original_columns:
        normalized = _compact_text(str(column_name))
        if normalized and normalized not in normalized_lookup:
            normalized_lookup[normalized] = column_name

    mapping: dict[str, object] = {}
    used_columns: set[object] = set()

    for field_name in STATEMENT_FIELD_ORDER:
        for alias in STATEMENT_COLUMN_ALIASES[field_name]:
            matched_column = normalized_lookup.get(_compact_text(alias))
            if matched_column is not None and matched_column not in used_columns:
                mapping[field_name] = matched_column
                used_columns.add(matched_column)
                break

    remaining_fields = [field for field in STATEMENT_FIELD_ORDER if field not in mapping]
    remaining_columns = [column for column in original_columns if column not in used_columns]

    if remaining_columns and _compact_text(str(remaining_columns[0])) in {
        _compact_text(value) for value in SERIAL_COLUMN_KEYS
    }:
        remaining_columns = remaining_columns[1:]

    if remaining_columns:
        # Fallback for 6-column contractor statement files with non-standard headers.
        for field_name, column_name in zip(remaining_fields, remaining_columns):
            mapping[field_name] = column_name

    if "full_name" not in mapping:
        raise HTTPException(
            status_code=422,
            detail="Excel headers do not match the expected Contractor Statement template.",
        )

    return mapping


def ingest_statement_excel(
    file: UploadFile,
    title: str,
    year: int,
    month: int,
    region_name: str,
    declared_total_amount: float,
    creator_id: int,
    db: Session,
) -> RegionalAttendanceSheet:
    contents = file.file.read()
    columns, rows = _read_excel_rows(contents)
    template_kind = _infer_template_kind(columns)
    if template_kind == "attendance_18":
        raise HTTPException(
            status_code=422,
            detail=(
                "Uploaded file appears to be the 18-column regional attendance template. "
                "Please upload it via /api/attendance/upload."
            ),
        )
    if template_kind == "unknown":
        raise HTTPException(
            status_code=422,
            detail=(
                "Unsupported Excel template. Only 18-column regional attendance and "
                "6-column contractor statement templates are accepted."
            ),
        )

    column_mapping = _build_statement_column_mapping(columns)
    declared_total_decimal = _as_decimal(declared_total_amount)

    if declared_total_decimal <= 0:
        raise HTTPException(
            status_code=422,
            detail="Declared total amount must be greater than zero.",
        )

    sheet = db.query(RegionalAttendanceSheet).filter(
        RegionalAttendanceSheet.year == year,
        RegionalAttendanceSheet.month == month,
        RegionalAttendanceSheet.region == region_name,
    ).first()

    if not sheet:
        sheet = RegionalAttendanceSheet(
            title=title,
            year=year,
            month=month,
            region=region_name,
            original_filename=file.filename or "statement.xlsx",
            row_count=0,
            status=AttendanceSheetStatus.DRAFT,
            declared_total_amount=declared_total_decimal,
            created_by_id=creator_id,
        )
        db.add(sheet)
        db.flush()
    else:
        # Update declared amount on existing sheet if being re-uploaded
        sheet.declared_total_amount = declared_total_decimal

    statement = ContractorStatement(
        sheet=sheet,
        year=year,
        month=month,
        region_name=region_name,
        declared_total_amount=declared_total_decimal,
    )
    db.add(statement)
    db.flush()

    items: list[ContractorStatementItem] = []
    for idx, row in enumerate(rows):
        if _should_skip_row(row, column_mapping):
            continue

        item_kwargs = {
            "statement": statement,
            "sheet": sheet,
            "row_number": EXCEL_DATA_START_ROW_NUMBER + idx,
        }

        for field_name, parser in STATEMENT_FIELD_PARSERS.items():
            item_kwargs[field_name] = parser(_get_row_value(row, column_mapping, field_name))

        if not item_kwargs["full_name"]:
            continue

        items.append(ContractorStatementItem(**item_kwargs))

    try:
        db.add_all(items)
        db.commit()
        db.refresh(sheet)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database write failed for statement: {str(exc)}") from exc

    return sheet


_STATUS_MAP: dict[str, str] = {
    AttendanceSheetStatus.DRAFT.value: WorkflowStatusLabel.DRAFT.value,
    AttendanceSheetStatus.CREATOR_APPROVED.value: WorkflowStatusLabel.CREATOR_APPROVED.value,
    AttendanceSheetStatus.COMPANY_REP_APPROVED.value: WorkflowStatusLabel.COMPANY_REP_APPROVED.value,
    AttendanceSheetStatus.SECURITY_APPROVED.value: WorkflowStatusLabel.SECURITY_APPROVED.value,
    AttendanceSheetStatus.GM_APPROVED.value: WorkflowStatusLabel.GM_APPROVED.value,
    AttendanceSheetStatus.NEEDS_CORRECTION.value: WorkflowStatusLabel.NEEDS_CORRECTION.value,
    AttendanceSheetStatus.REJECTED.value: WorkflowStatusLabel.REJECTED.value,
}


def _resolve_status_label(raw_status: str) -> str:
    return _STATUS_MAP.get(raw_status, raw_status)


def _as_float(value: Decimal | int | float | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _as_int(value: Decimal | int | float | None) -> int:
    if value is None:
        return 0
    return int(value)


def _as_decimal(value: Decimal | int | float | None) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _is_statement_total_row(item: ContractorStatementItem) -> bool:
    label = _compact_text(item.full_name or "")
    if not label:
        return False
    return label in STATEMENT_TOTAL_ROW_MARKERS or "جمعکل" in label


def _get_statement_total_candidate(item: ContractorStatementItem) -> Optional[Decimal]:
    for value in (
        item.gross_amount,
        item.net_payable_amount,
        item.tax_deduction,
        item.insurance_deduction,
    ):
        if value is not None:
            return value
    return None


def _get_attendance_sheet_for_period(
    db: Session,
    *,
    year: int,
    month: int,
    region_name: str,
) -> RegionalAttendanceSheet:
    normalized_region = _normalize_text(region_name)
    candidates = (
        db.query(RegionalAttendanceSheet)
        .filter(
            RegionalAttendanceSheet.year == year,
            RegionalAttendanceSheet.month == month,
        )
        .order_by(RegionalAttendanceSheet.created_at.desc())
        .all()
    )

    matched_sheets: list[RegionalAttendanceSheet] = []
    for sheet in candidates:
        if _normalize_text(sheet.region or "") != normalized_region:
            continue
        matched_sheets.append(sheet)
        has_rows = (
            db.query(AttendanceRecord.id)
            .filter(AttendanceRecord.sheet_id == sheet.id)
            .first()
            is not None
        )
        if has_rows:
            return sheet

    if matched_sheets:
        raise HTTPException(
            status_code=404,
            detail=(
                "No regional attendance rows found for the selected period and region. "
                "Upload the 18-column regional attendance file for this period."
            ),
        )

    raise HTTPException(
        status_code=404,
        detail=(
            f"No attendance sheet found for year={year}, month={month}, "
            f"region='{region_name}'."
        ),
    )


def get_attendance_reconciliation(
    db: Session,
    *,
    year: int,
    month: int,
    region_name: str,
) -> AttendanceReconciliationOut:
    normalized_region = _normalize_text(region_name)
    if not normalized_region:
        raise HTTPException(status_code=422, detail="Region name is required.")

    sheet = _get_attendance_sheet_for_period(
        db,
        year=year,
        month=month,
        region_name=normalized_region,
    )

    region_totals = (
        db.query(
            func.coalesce(func.sum(AttendanceRecord.total_average_per_capita), 0).label(
                "per_capita_total"
            ),
            func.coalesce(func.sum(AttendanceRecord.total_overtime_given), 0).label(
                "overtime_total"
            ),
        )
        .filter(AttendanceRecord.sheet_id == sheet.id)
        .first()
    )

    has_attendance_rows = (
        db.query(AttendanceRecord.id)
        .filter(AttendanceRecord.sheet_id == sheet.id)
        .first()
        is not None
    )
    if not has_attendance_rows:
        raise HTTPException(
            status_code=404,
            detail="No regional attendance rows found for the selected period and region.",
        )

    region_total = _as_decimal(region_totals.per_capita_total) + _as_decimal(
        region_totals.overtime_total
    )

    matching_statements = (
        db.query(ContractorStatement)
        .filter(
            ContractorStatement.year == year,
            ContractorStatement.month == month,
        )
        .order_by(ContractorStatement.created_at.desc())
        .all()
    )
    statement = next(
        (
            candidate
            for candidate in matching_statements
            if _normalize_text(candidate.region_name or "") == normalized_region
        ),
        None,
    )

    if not statement:
        raise HTTPException(
            status_code=404,
            detail="No contractor statement found for the selected period and region.",
        )

    has_statement_rows = (
        db.query(ContractorStatementItem.id)
        .filter(ContractorStatementItem.statement_id == statement.id)
        .first()
        is not None
    )
    if not has_statement_rows:
        raise HTTPException(
            status_code=404,
            detail="No contractor statement rows found for the selected period and region.",
        )

    contractor_total = _as_decimal(statement.declared_total_amount)
    difference = contractor_total - region_total

    return AttendanceReconciliationOut(
        year=year,
        month=month,
        region_name=sheet.region or normalized_region,
        region_total=region_total,
        contractor_total=contractor_total,
        difference=difference,
        is_matched=difference == 0,
    )


def get_attendance_aggregation(
    db: Session,
    *,
    region: Optional[str] = None,
    status: Optional[str] = None,
) -> AttendanceAggregationOut:
    totals_subquery = (
        db.query(
            AttendanceRecord.sheet_id.label("sheet_id"),
            func.count(AttendanceRecord.id).label("total_personnel"),
            func.coalesce(func.sum(AttendanceRecord.overtime_hours), 0).label(
                "total_worked_hours"
            ),
            func.coalesce(func.sum(AttendanceRecord.total_average_per_capita), 0).label(
                "total_amount"
            ),
        )
        .group_by(AttendanceRecord.sheet_id)
        .subquery()
    )

    query = (
        db.query(
            RegionalAttendanceSheet,
            func.coalesce(totals_subquery.c.total_personnel, 0).label("total_personnel"),
            func.coalesce(totals_subquery.c.total_worked_hours, 0).label(
                "total_worked_hours"
            ),
            func.coalesce(totals_subquery.c.total_amount, 0).label("total_amount"),
        )
        .outerjoin(totals_subquery, totals_subquery.c.sheet_id == RegionalAttendanceSheet.id)
        .filter(RegionalAttendanceSheet.row_count > 0)
        .order_by(RegionalAttendanceSheet.created_at.desc())
    )

    if region:
        query = query.filter(RegionalAttendanceSheet.region.ilike(f"%{region.strip()}%"))

    if status:
        normalized_status = status.strip().upper()
        try:
            status_enum = AttendanceSheetStatus(normalized_status)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="وضعیت حضور و غیاب نامعتبر است.") from exc
        query = query.filter(RegionalAttendanceSheet.status == status_enum)

    rows = query.all()
    items: list[AttendanceAggregationItem] = []

    for sheet_obj, total_personnel, total_worked_hours, total_amount in rows:
        raw_status = (
            sheet_obj.status.value
            if isinstance(sheet_obj.status, AttendanceSheetStatus)
            else str(sheet_obj.status)
        )
        sheet_meta = SheetMetaSummary(
            sheet_id=sheet_obj.id,
            title=sheet_obj.title,
            year=sheet_obj.year,
            month=sheet_obj.month,
            region_name=sheet_obj.region,
            original_filename=sheet_obj.original_filename,
            row_count=sheet_obj.row_count,
            created_at=sheet_obj.created_at,
            creator_approved_at=sheet_obj.creator_approved_at,
            company_rep_approved_at=sheet_obj.company_rep_approved_at,
            security_approved_at=sheet_obj.security_approved_at,
            gm_approved_at=sheet_obj.gm_approved_at,
        )
        items.append(
            AttendanceAggregationItem(
                sheet=sheet_meta,
                workflow_status=raw_status,
                workflow_status_label=_resolve_status_label(raw_status),
                total_personnel=_as_int(total_personnel),
                total_worked_hours=_as_float(total_worked_hours),
                total_amount=_as_int(total_amount),
            )
        )

    return AttendanceAggregationOut(count=len(items), items=items)
