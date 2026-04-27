"""Financial classification matrix models."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class FinancialRule(Base):
    __tablename__ = "financial_rules"

    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(
        Integer,
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cost_center_code = Column(String(64), nullable=False, index=True)
    budget_line_code = Column(String(64), nullable=False, index=True)
    financial_event_type = Column(String(128), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)

    activity = relationship("Activity", back_populates="financial_rules")


__all__ = ["FinancialRule"]
