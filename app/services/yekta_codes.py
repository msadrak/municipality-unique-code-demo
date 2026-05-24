"""Shared helpers for municipality Yekta code construction."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable


YEKTA_SEQUENCE_LENGTH = 3


def zero_fill_segment(value: object, length: int, default: str) -> str:
    """Return the legacy zero-filled segment without truncating longer codes."""
    raw = str(value if value not in {None, ""} else default).strip()
    if not raw:
        raw = default
    return raw.zfill(length)


def hash_segment(value: object, length: int, default: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return default
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:length].upper()


@dataclass(frozen=True)
class YektaCodeSegments:
    zone: str
    department: str
    section: str
    budget: str
    cost_center: str
    continuous_action: str
    special_activity_hash: str
    beneficiary_hash: str
    financial_event: str
    fiscal_year: str
    sequence: str

    def prefix_parts(self) -> list[str]:
        return [
            self.zone,
            self.department,
            self.section,
            self.budget,
            self.cost_center,
            self.continuous_action,
            self.special_activity_hash,
            self.beneficiary_hash,
            self.financial_event,
            self.fiscal_year,
        ]

    def parts(self) -> list[str]:
        return [*self.prefix_parts(), self.sequence]

    def prefix(self) -> str:
        return "-".join(self.prefix_parts())

    def code(self) -> str:
        return "-".join(self.parts())

    def as_dict(self) -> dict[str, str]:
        return {
            "zone": self.zone,
            "department": self.department,
            "section": self.section,
            "budget": self.budget,
            "cost_center": self.cost_center,
            "continuous_action": self.continuous_action,
            "special_activity_hash": self.special_activity_hash,
            "beneficiary_hash": self.beneficiary_hash,
            "financial_event": self.financial_event,
            "fiscal_year": self.fiscal_year,
            "sequence": self.sequence,
        }


def build_yekta_segments(
    *,
    zone_code: object,
    department_code: object,
    section_code: object,
    budget_code: object,
    cost_center_code: object,
    continuous_action_code: object,
    special_activity: object,
    beneficiary_name: object,
    financial_event_code: object,
    fiscal_year: object,
    sequence: int | str,
) -> YektaCodeSegments:
    return YektaCodeSegments(
        zone=zero_fill_segment(zone_code, 2, "00"),
        department=zero_fill_segment(department_code, 2, "00"),
        section=zero_fill_segment(section_code, 3, "000"),
        budget=zero_fill_segment(budget_code, 8, "00000000"),
        cost_center=zero_fill_segment(cost_center_code, 3, "000"),
        continuous_action=zero_fill_segment(continuous_action_code, 2, "00"),
        special_activity_hash=hash_segment(special_activity, 3, "000"),
        beneficiary_hash=hash_segment(beneficiary_name or "Unknown", 6, "000000"),
        financial_event=zero_fill_segment(financial_event_code, 3, "000"),
        fiscal_year=zero_fill_segment(fiscal_year, 4, "1403")[:4],
        sequence=zero_fill_segment(sequence, YEKTA_SEQUENCE_LENGTH, "001"),
    )


def build_yekta_code(**kwargs: object) -> str:
    return build_yekta_segments(**kwargs).code()


def build_yekta_prefix(**kwargs: object) -> str:
    return build_yekta_segments(sequence=1, **kwargs).prefix()


def split_yekta_code(code: str | None) -> list[str]:
    if not code:
        return []
    return [segment.strip() for segment in str(code).split("-")]


def sequence_from_code(code: str | None) -> str | None:
    parts = split_yekta_code(code)
    return parts[-1] if len(parts) == 11 else None


def prefix_from_code(code: str | None) -> str | None:
    parts = split_yekta_code(code)
    if len(parts) != 11:
        return None
    return "-".join(parts[:-1])


def prefix_matches(code: str | None, prefix: str) -> bool:
    return prefix_from_code(code) == prefix


def first_nonempty(values: Iterable[object]) -> object | None:
    for value in values:
        if value not in {None, ""}:
            return value
    return None


__all__ = [
    "YektaCodeSegments",
    "build_yekta_code",
    "build_yekta_prefix",
    "build_yekta_segments",
    "first_nonempty",
    "hash_segment",
    "prefix_from_code",
    "prefix_matches",
    "sequence_from_code",
    "split_yekta_code",
    "zero_fill_segment",
]
