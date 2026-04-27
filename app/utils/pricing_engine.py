from decimal import Decimal

from app.models.attendance import AttendanceRecord

# Appendix 7 Cost Constants (All values in IRR)
BASE_SALARY_MONTHLY = Decimal("156096558")
FIXED_ALLOWANCES_MONTHLY = Decimal("260000000")
OVERTIME_HOURLY_RATE = Decimal("1282775")
HOLIDAY_DAILY_RATE = Decimal("8209764")
FRIDAY_DAILY_RATE = Decimal("10555412")
SHIFT_22_5_DAILY_RATE = Decimal("1319426")

# Marital & Child Allowances (Added for realistic demo)
FAMILY_ALLOWANCE = Decimal("20000000")
CHILD_ALLOWANCE = Decimal("10000000")


def calculate_record_legal_value(record: AttendanceRecord) -> Decimal:
    """
    Calculate the exact legal monetary value of an AttendanceRecord
    based on the constants from Appendix 7, including marital and child allowances.
    """
    base = BASE_SALARY_MONTHLY + FIXED_ALLOWANCES_MONTHLY

    # Add Marital Allowance
    if getattr(record, "marital_status", None) == "متأهل":
        base += FAMILY_ALLOWANCE

    # Add Child Allowance (if children_count exists on record)
    children_count = int(getattr(record, "children_count", 0) or 0)
    if children_count > 0:
        base += Decimal(str(children_count)) * CHILD_ALLOWANCE

    overtime_hours = record.total_overtime_given if record.total_overtime_given else Decimal("0")
    overtime_pay = overtime_hours * OVERTIME_HOURLY_RATE

    holiday_work_days = Decimal(str(getattr(record, "holiday_work_days", 0) or 0))
    holiday_pay = holiday_work_days * HOLIDAY_DAILY_RATE

    friday_work_days = Decimal(str(getattr(record, "friday_work_days", 0) or 0))
    friday_pay = friday_work_days * FRIDAY_DAILY_RATE

    shift_22_5_days = Decimal(str(getattr(record, "shift_22_5_days", 0) or 0))
    shift_pay = shift_22_5_days * SHIFT_22_5_DAILY_RATE

    return base + overtime_pay + holiday_pay + friday_pay + shift_pay
