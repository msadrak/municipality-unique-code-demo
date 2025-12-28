# app/services/__init__.py
"""
Domain Services for Municipality ERP
=====================================

This package contains business logic services that implement
domain rules with ACID compliance.
"""

from .budget_service import (
    block_funds,
    release_funds,
    confirm_spend,
    InsufficientFundsError,
    InvalidOperationError,
)

__all__ = [
    "block_funds",
    "release_funds", 
    "confirm_spend",
    "InsufficientFundsError",
    "InvalidOperationError",
]
