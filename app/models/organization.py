"""Organizational chart and activity catalog models."""

from __future__ import annotations

import enum

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import backref, relationship, synonym

from app._legacy_models import OrgUnit
from app.database import Base


class OrgUnitType(str, enum.Enum):
    """Canonical ERP-facing org unit levels."""

    DEPUTY = "DEPUTY"
    DEPARTMENT = "DEPARTMENT"
    UNIT = "UNIT"


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    org_unit_id = Column(
        Integer,
        ForeignKey("org_units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    org_unit = relationship(
        "OrgUnit",
        backref=backref("activities"),
    )
    financial_rules = relationship(
        "FinancialRule",
        back_populates="activity",
        cascade="all, delete-orphan",
    )
    transactions = relationship(
        "Transaction",
        back_populates="activity",
    )


# Backward-compatible ERP aliases on the legacy org_units table.
if "name" not in OrgUnit.__dict__:
    OrgUnit.name = synonym("title")

if "type" not in OrgUnit.__dict__:
    OrgUnit.type = synonym("org_type")

if "parent" not in OrgUnit.__dict__:
    OrgUnit.parent = relationship(
        "OrgUnit",
        remote_side=[OrgUnit.id],
        foreign_keys=[OrgUnit.parent_id],
        backref=backref("children"),
    )


__all__ = ["Activity", "OrgUnit", "OrgUnitType"]
