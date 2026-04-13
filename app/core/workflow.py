from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.attendance import RegionalAttendanceSheet
from app.models.enums import AttendanceSheetStatus

_FORWARD = {
    AttendanceSheetStatus.DRAFT: AttendanceSheetStatus.CREATOR_APPROVED,
    AttendanceSheetStatus.NEEDS_CORRECTION: AttendanceSheetStatus.CREATOR_APPROVED,
    AttendanceSheetStatus.CREATOR_APPROVED: AttendanceSheetStatus.COMPANY_REP_APPROVED,
    AttendanceSheetStatus.COMPANY_REP_APPROVED: AttendanceSheetStatus.SECURITY_APPROVED,
    AttendanceSheetStatus.SECURITY_APPROVED: AttendanceSheetStatus.GM_APPROVED,
}

_TIMESTAMP_FIELD = {
    AttendanceSheetStatus.CREATOR_APPROVED: "creator_approved_at",
    AttendanceSheetStatus.COMPANY_REP_APPROVED: "company_rep_approved_at",
    AttendanceSheetStatus.SECURITY_APPROVED: "security_approved_at",
    AttendanceSheetStatus.GM_APPROVED: "gm_approved_at",
}


def transition(
    sheet: RegionalAttendanceSheet,
    action: str,
    actor_id: int,
    db: Session,
    rejection_reason: Optional[str] = None,
) -> RegionalAttendanceSheet:
    _ = actor_id
    now = datetime.now(timezone.utc)

    if action == "approve":
        next_status = _FORWARD.get(sheet.status)
        if next_status is None:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot approve from status '{sheet.status.value}'.",
            )
        sheet.status = next_status
        ts_field = _TIMESTAMP_FIELD.get(next_status)
        if ts_field:
            setattr(sheet, ts_field, now)
        sheet.rejection_reason = None

    elif action == "reject":
        if sheet.status in (
            AttendanceSheetStatus.DRAFT,
            AttendanceSheetStatus.NEEDS_CORRECTION,
            AttendanceSheetStatus.REJECTED,
        ):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot reject from status '{sheet.status.value}'.",
            )
        sheet.status = AttendanceSheetStatus.NEEDS_CORRECTION
        sheet.rejection_reason = rejection_reason or "No reason provided."

    elif action == "final_reject":
        sheet.status = AttendanceSheetStatus.REJECTED
        sheet.rejection_reason = rejection_reason or "Permanently rejected."

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    try:
        db.commit()
        db.refresh(sheet)
    except Exception:
        db.rollback()
        raise

    return sheet
