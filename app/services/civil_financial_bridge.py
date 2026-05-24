"""Event-driven bridge from civil BPMS gates to finance ledger transactions."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models import (
    Activity,
    BudgetItem,
    CivilProject,
    EntityDocument,
    FinancialRule,
    Transaction,
    WorkflowStep,
)

logger = logging.getLogger(__name__)


TRANSACTION_CREATED = "TRANSACTION_CREATED"
PROGRESS_STATEMENT = "PROGRESS_STATEMENT"
PROGRESS_STATEMENT_STEP_NUMBER = 33
NET_PAYABLE_RATE = Decimal("0.85")

PERSIAN_ARABIC_DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)


class CivilFinancialBridgeService:
    """Translates civil workflow financial gates into ERP ledger mutations."""

    def trigger_financial_gate(
        self,
        project_id: int,
        gate_name: str,
        db_session: Session,
    ) -> Transaction | None:
        normalized_gate = (gate_name or "").strip().upper()
        if normalized_gate != TRANSACTION_CREATED:
            logger.info(
                "Civil financial gate %s for project_id=%s has no bridge handler yet",
                gate_name,
                project_id,
            )
            return None

        return self._create_transaction_from_progress_statement(project_id, db_session)

    def _create_transaction_from_progress_statement(
        self,
        project_id: int,
        db: Session,
    ) -> Transaction:
        project = (
            db.query(CivilProject)
            .filter(CivilProject.id == project_id)
            .with_for_update()
            .first()
        )
        if project is None:
            raise ValueError(f"Civil project {project_id} was not found")

        document = self._latest_progress_statement_document(project.id, db)
        if document is None:
            raise ValueError(
                f"Civil project {project.project_code} has no {PROGRESS_STATEMENT} "
                f"document from workflow step {PROGRESS_STATEMENT_STEP_NUMBER}"
            )

        tracking_number = self._tracking_number(project, document)
        existing = (
            db.query(Transaction)
            .filter(Transaction.tracking_number == tracking_number)
            .first()
        )
        if existing is not None:
            logger.info(
                "Civil bridge transaction already exists for project_id=%s, document_id=%s",
                project.id,
                document.id,
            )
            return existing

        gross_amount = self._extract_gross_amount(document.payload or {})
        net_amount = self._calculate_net_amount(gross_amount)
        active_rule = self._active_financial_rule(project)
        budget_item = self._resolve_budget_item(active_rule, db)

        transaction = Transaction(
            tracking_number=tracking_number,
            unique_code=None,
            status="PENDING_TREASURY",
            current_approval_level=0,
            created_by_id=document.created_by_id,
            zone_id=project.owning_org_unit_id,
            activity_id=project.activity_id,
            budget_item_id=budget_item.id if budget_item else None,
            amount=net_amount,
            beneficiary_name=self._resolve_beneficiary_name(project, document.payload or {}),
            contract_number=self._resolve_contract_number(project, document.payload or {}),
            special_activity=project.activity.name if project.activity else None,
            description=(
                f"Civil BPMS gate {TRANSACTION_CREATED}: net payable from "
                f"{PROGRESS_STATEMENT} document #{document.id} for project "
                f"{project.project_code}"
            ),
            form_data={
                "source": "CIVIL_BPMS",
                "financial_gate": TRANSACTION_CREATED,
                "civil_project_id": project.id,
                "civil_project_code": project.project_code,
                "entity_document_id": document.id,
                "document_type": document.document_type,
                "gross_amount": int(gross_amount),
                "deduction_rate": "0.15",
                "net_payable_rate": str(NET_PAYABLE_RATE),
                "net_amount": net_amount,
                "activity_id": project.activity_id,
                "org_unit_id": project.owning_org_unit_id,
                "budget_line_code": active_rule.budget_line_code if active_rule else None,
                "cost_center_code": active_rule.cost_center_code if active_rule else None,
            },
            fiscal_year=self._current_persian_year(),
        )

        try:
            db.add(transaction)
            db.commit()
            db.refresh(transaction)
        except Exception:
            db.rollback()
            raise

        logger.info(
            "Created civil bridge transaction id=%s tracking_number=%s project_id=%s "
            "document_id=%s gross=%s net=%s",
            transaction.id,
            transaction.tracking_number,
            project.id,
            document.id,
            gross_amount,
            net_amount,
        )
        return transaction

    def _latest_progress_statement_document(
        self,
        project_id: int,
        db: Session,
    ) -> EntityDocument | None:
        return (
            db.query(EntityDocument)
            .join(WorkflowStep, EntityDocument.step_id == WorkflowStep.id)
            .filter(
                EntityDocument.project_id == project_id,
                EntityDocument.document_type == PROGRESS_STATEMENT,
                WorkflowStep.order_index == PROGRESS_STATEMENT_STEP_NUMBER,
            )
            .order_by(EntityDocument.created_at.desc(), EntityDocument.id.desc())
            .first()
        )

    def _extract_gross_amount(self, payload: dict[str, Any]) -> Decimal:
        raw_amount = self._first_payload_value(
            payload,
            "gross_amount",
            "grossAmount",
            "gross",
            "amount_gross",
            "مبلغ ناخالص",
            "مبلغ_ناخالص",
        )
        if raw_amount is None:
            raise ValueError("PROGRESS_STATEMENT payload is missing gross_amount")

        amount = self._parse_amount(raw_amount)
        if amount <= 0:
            raise ValueError("PROGRESS_STATEMENT gross_amount must be positive")
        return amount

    def _calculate_net_amount(self, gross_amount: Decimal) -> int:
        net_amount = (gross_amount * NET_PAYABLE_RATE).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
        return int(net_amount)

    def _active_financial_rule(self, project: CivilProject) -> FinancialRule | None:
        rules = list(project.activity.financial_rules) if project.activity else []
        return next((rule for rule in rules if rule.is_active), rules[0] if rules else None)

    def _resolve_budget_item(
        self,
        active_rule: FinancialRule | None,
        db: Session,
    ) -> BudgetItem | None:
        if active_rule is None or not active_rule.budget_line_code:
            return None
        return (
            db.query(BudgetItem)
            .filter(BudgetItem.budget_code == active_rule.budget_line_code)
            .first()
        )

    def _resolve_beneficiary_name(
        self,
        project: CivilProject,
        payload: dict[str, Any],
    ) -> str:
        beneficiary = self._first_payload_value(
            payload,
            "beneficiary_name",
            "beneficiary",
            "contractor_name",
            "contractor",
            "نام پیمانکار",
            "ذینفع",
        )
        if beneficiary is not None and str(beneficiary).strip():
            return str(beneficiary).strip()
        return project.title

    def _resolve_contract_number(
        self,
        project: CivilProject,
        payload: dict[str, Any],
    ) -> str:
        contract_number = self._first_payload_value(
            payload,
            "contract_number",
            "contract_no",
            "contractRefNumber",
            "شماره قرارداد",
        )
        if contract_number is not None and str(contract_number).strip():
            return str(contract_number).strip()
        return project.project_code

    def _tracking_number(self, project: CivilProject, document: EntityDocument) -> str:
        normalized_project_code = re.sub(r"[^A-Za-z0-9]+", "-", project.project_code).strip("-")
        if not normalized_project_code:
            normalized_project_code = f"PROJECT-{project.id}"
        return f"CIVIL-{normalized_project_code}-DOC-{document.id}"

    def _parse_amount(self, raw_amount: Any) -> Decimal:
        if isinstance(raw_amount, Decimal):
            return raw_amount
        if isinstance(raw_amount, int):
            return Decimal(raw_amount)
        if isinstance(raw_amount, float):
            return Decimal(str(raw_amount))

        normalized = str(raw_amount).translate(PERSIAN_ARABIC_DIGITS).strip()
        normalized = normalized.replace(",", "").replace("٬", "").replace(" ", "")
        normalized = re.sub(r"[^\d.]", "", normalized)
        if not normalized:
            raise ValueError(f"Invalid gross_amount value: {raw_amount!r}")
        try:
            return Decimal(normalized)
        except InvalidOperation as exc:
            raise ValueError(f"Invalid gross_amount value: {raw_amount!r}") from exc

    def _first_payload_value(self, payload: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in payload:
                return payload[key]
        return None

    def _current_persian_year(self) -> str:
        now = datetime.utcnow()
        if (now.month, now.day) < (3, 21):
            return str(now.year - 622)
        return str(now.year - 621)


def trigger_financial_gate(
    project_id: int,
    gate_name: str,
    db_session: Session,
) -> Transaction | None:
    return CivilFinancialBridgeService().trigger_financial_gate(
        project_id,
        gate_name,
        db_session,
    )


__all__ = ["CivilFinancialBridgeService", "trigger_financial_gate"]
