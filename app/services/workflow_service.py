from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import FundingRequest, FundingStatus as S, FundingWorkflowLog, UserRole
from app.services.funding_budget_service import BudgetService


TRANSITION_MAP: dict[S, dict[str, tuple[UserRole, S]]] = {
    S.PENDING_VP_PLANNING: {
        "approve": (UserRole.VP_PLANNING, S.PENDING_VP_FINANCE_REVIEW),
        "reject": (UserRole.VP_PLANNING, S.REJECTED),
    },
    S.PENDING_VP_FINANCE_REVIEW: {
        "approve": (UserRole.VP_FINANCE, S.BUDGET_WELFARE_DEPT),
        "reject": (UserRole.VP_FINANCE, S.REJECTED),
    },
    S.BUDGET_WELFARE_DEPT: {
        "approve": (UserRole.WELFARE_DEPT, S.BUDGET_GM_HC),
        "reject": (UserRole.WELFARE_DEPT, S.REJECTED),
    },
    S.BUDGET_GM_HC: {
        "approve": (UserRole.GM_HC, S.BUDGET_FINANCE_UNIT),
        "reject": (UserRole.GM_HC, S.REJECTED),
    },
    S.BUDGET_FINANCE_UNIT: {
        "approve": (UserRole.FINANCE_UNIT, S.BUDGET_VP_FINANCE),
        "reject": (UserRole.FINANCE_UNIT, S.REJECTED),
    },
    S.BUDGET_VP_FINANCE: {
        "approve": (UserRole.VP_FINANCE, S.CHARGE_LETTER_REGISTERED),
        "reject": (UserRole.VP_FINANCE, S.REJECTED),
    },
    S.CHARGE_LETTER_REGISTERED: {
        "register": (UserRole.GM_HC, S.PENDING_FINAL_CHARGE),
    },
    S.PENDING_FINAL_CHARGE: {
        "approve": (UserRole.VP_FINANCE, S.FINAL_APPROVED),
        "reject": (UserRole.VP_FINANCE, S.REJECTED),
    },
    S.FINAL_APPROVED: {
        "execute": (UserRole.ISFAHAN_CARD, S.CHARGING_IN_PROGRESS),
    },
    S.CHARGING_IN_PROGRESS: {
        "complete": (UserRole.ISFAHAN_CARD, S.COMPLETED),
    },
}

ROLE_VISIBLE_STATUSES: dict[UserRole, list[S]] = {}
for _workflow_status, _actions in TRANSITION_MAP.items():
    for _required_role, _ in _actions.values():
        visible = ROLE_VISIBLE_STATUSES.setdefault(_required_role, [])
        if _workflow_status not in visible:
            visible.append(_workflow_status)
ROLE_VISIBLE_STATUSES[UserRole.ADMIN] = list(S)

SYSTEM_ADMIN_ROLE_PREFIXES = ("ADMIN_L",)
SYSTEM_ADMIN_ROLES = {"admin", "ADMIN"}
UPDATABLE_EXTRA_FIELDS = {
    "budget_code",
    "budget_year",
    "charge_letter_number",
    "charge_letter_date",
    "letter_number",
    "letter_date",
    "receiver_title",
    "sender_title",
    "subject",
    "body_text",
    "cc_list",
    "attachment_count",
    "amount",
    "request_type",
    "title",
    "description",
}


def is_admin_role(raw_role: Optional[str]) -> bool:
    if not raw_role:
        return False
    if raw_role in SYSTEM_ADMIN_ROLES:
        return True
    return any(raw_role.startswith(prefix) for prefix in SYSTEM_ADMIN_ROLE_PREFIXES)


def normalize_user_role(raw_role: Optional[str]) -> Optional[UserRole]:
    if not raw_role:
        return None
    if is_admin_role(raw_role):
        return UserRole.ADMIN

    candidates = [raw_role, raw_role.upper()]
    for candidate in candidates:
        try:
            return UserRole(candidate)
        except ValueError:
            continue
    return None


class WorkflowService:
    def __init__(self, db: Session):
        self.db = db

    def advance_status(
        self,
        request_id: int,
        user_id: int,
        raw_user_role: Optional[str],
        action: str,
        comment: Optional[str] = None,
        extra_fields: Optional[dict] = None,
    ) -> FundingRequest:
        req = (
            self.db.query(FundingRequest)
            .filter(FundingRequest.id == request_id)
            .with_for_update()
            .first()
        )
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="درخواست یافت نشد",
            )

        current = req.status
        actions = TRANSITION_MAP.get(current)
        if not actions or action not in actions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"عملیات «{action}» در وضعیت «{current.value}» مجاز نیست",
            )

        normalized_role = normalize_user_role(raw_user_role)
        required_role, next_status = actions[action]
        if normalized_role != UserRole.ADMIN and normalized_role != required_role:
            role_label = raw_user_role or "UNKNOWN"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"نقش «{role_label}» اجازه این عملیات را ندارد",
            )

        if action == "reject" and req.budget_code:
            BudgetService.release_budget(req.budget_code)

        old_status = req.status
        req.status = next_status
        req.updated_at = datetime.utcnow()

        for field_name, value in (extra_fields or {}).items():
            if field_name in UPDATABLE_EXTRA_FIELDS:
                setattr(req, field_name, value)

        log = FundingWorkflowLog(
            request_id=request_id,
            user_id=user_id,
            from_status=old_status,
            to_status=next_status,
            action=action,
            comment=comment,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(req)
        return req

    def get_inbox(self, raw_user_role: Optional[str]) -> list[FundingRequest]:
        normalized_role = normalize_user_role(raw_user_role)
        if not normalized_role:
            return []

        visible_statuses = ROLE_VISIBLE_STATUSES.get(normalized_role, [])
        if not visible_statuses:
            return []

        return (
            self.db.query(FundingRequest)
            .filter(FundingRequest.status.in_(visible_statuses))
            .order_by(FundingRequest.updated_at.desc())
            .all()
        )

    def get_history(self, request_id: int) -> list[FundingWorkflowLog]:
        return (
            self.db.query(FundingWorkflowLog)
            .filter(FundingWorkflowLog.request_id == request_id)
            .order_by(FundingWorkflowLog.timestamp.asc())
            .all()
        )
