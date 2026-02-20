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

from .contract_service import (
    create_draft,
    transition_status,
    render_contract,
    ContractNotFoundError,
    InvalidTransitionError,
    ContractValidationError,
)

from .statement_service import (
    create_statement,
    submit_statement,
    approve_statement,
    pay_statement,
    get_contract_statements,
    get_statement_financial_summary,
    StatementNotFoundError,
    StatementValidationError,
    InvalidStatementTransitionError,
    OverPaymentError,
)

__all__ = [
    "block_funds",
    "release_funds", 
    "confirm_spend",
    "InsufficientFundsError",
    "InvalidOperationError",
    "create_draft",
    "transition_status",
    "render_contract",
    "ContractNotFoundError",
    "InvalidTransitionError",
    "ContractValidationError",
    "create_statement",
    "submit_statement",
    "approve_statement",
    "pay_statement",
    "get_contract_statements",
    "get_statement_financial_summary",
    "StatementNotFoundError",
    "StatementValidationError",
    "InvalidStatementTransitionError",
    "OverPaymentError",
]
