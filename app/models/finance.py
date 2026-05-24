"""Finance allocation and classification matrix models."""

from __future__ import annotations

import hashlib

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import backref, relationship

from app.database import Base


def generate_financial_matrix_yekta_code(
    *,
    budget_line_level_5: str,
    cost_center: str,
    financial_event: str,
    activity_name: str,
    sequence: int = 1,
) -> str:
    """Build a stable Yekta-code seed from the core financial matrix fields."""
    normalized_parts = [
        (budget_line_level_5 or "").strip().upper(),
        (cost_center or "").strip().upper(),
        (financial_event or "").strip().upper(),
        (activity_name or "").strip().upper(),
    ]
    digest = hashlib.sha256("|".join(normalized_parts).encode("utf-8")).hexdigest()[:10].upper()
    budget_fragment = "".join(ch for ch in normalized_parts[0] if ch.isascii() and ch.isalnum())[:12] or "BUDGET"
    cost_center_fragment = "".join(ch for ch in normalized_parts[1] if ch.isascii() and ch.isalnum())[:8] or "CENTER"
    event_fragment = "".join(ch for ch in normalized_parts[2] if ch.isascii() and ch.isalnum())[:8] or "EVENT"
    return f"YK-{budget_fragment}-{cost_center_fragment}-{event_fragment}-{digest}-{sequence:04d}"


class FinancialMatrix(Base):
    __tablename__ = "financial_matrix"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "statement_document_id",
            "financial_event",
            name="uq_financial_matrix_statement_event",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("civil_projects.id", ondelete="CASCADE"), nullable=True, index=True)
    statement_document_id = Column(
        Integer,
        ForeignKey("entity_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    budget_line_level_5 = Column(String(64), nullable=False, index=True)
    cost_center = Column(String(128), nullable=False, index=True)
    financial_event = Column(String(128), nullable=False, index=True)
    financial_event_label = Column(String(255), nullable=True)
    event_group = Column(String(64), nullable=True, index=True)
    event_sequence = Column(Integer, nullable=False, default=1)
    event_direction = Column(String(16), nullable=False, default="DEBIT")
    activity_name = Column(String(255), nullable=False, index=True)
    period_key = Column(String(64), nullable=True, index=True)
    amount = Column(Numeric(18, 2), nullable=True)
    yekta_code = Column(String(128), nullable=True, unique=True, index=True)
    payment_queue_status = Column(String(64), nullable=False, default="MATRIX_ONLY", index=True)
    source_payload = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project = relationship("CivilProject", backref=backref("financial_matrix_rows", cascade="all, delete-orphan"))
    statement_document = relationship("EntityDocument", foreign_keys=[statement_document_id])
    transaction = relationship("Transaction", foreign_keys=[transaction_id])

    def generate_yekta_code(self, sequence: int = 1) -> str:
        return generate_financial_matrix_yekta_code(
            budget_line_level_5=self.budget_line_level_5,
            cost_center=self.cost_center,
            financial_event=self.financial_event,
            activity_name=self.activity_name,
            sequence=sequence,
        )


class TransactionAllocation(Base):
    __tablename__ = "transaction_allocations"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(
        Integer,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_unit_name = Column(String(255), nullable=False)
    cost_center_code = Column(String(64), nullable=False, index=True)
    budget_line_code = Column(String(64), nullable=False, index=True)
    allocated_amount = Column(Numeric(18, 2), nullable=False)
    legal_deductions = Column(Numeric(18, 2), nullable=False, default=0)
    penalties = Column(Numeric(18, 2), nullable=False, default=0)
    net_amount = Column(Numeric(18, 2), nullable=False)
    unique_code = Column(String(64), nullable=False, unique=True, index=True)

    transaction = relationship(
        "Transaction",
        backref=backref(
            "allocations",
            cascade="all, delete-orphan",
            order_by="TransactionAllocation.id",
        ),
    )


__all__ = ["FinancialMatrix", "TransactionAllocation", "generate_financial_matrix_yekta_code"]
