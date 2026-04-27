"""Finance allocation models for split HR transactions."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import backref, relationship

from app.database import Base


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


__all__ = ["TransactionAllocation"]
