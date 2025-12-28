"""
Budget API Schemas - Pydantic v2 Models
========================================

Request/Response schemas for the Budget Control API endpoints.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================
# Enums
# ============================================================

class BudgetStatus(str, Enum):
    """Status indicators for budget availability."""
    AVAILABLE = "AVAILABLE"       # Has remaining balance
    LOW = "LOW"                   # Less than 20% remaining
    EXHAUSTED = "EXHAUSTED"       # Zero remaining


class TransactionStatus(str, Enum):
    """Status of a transaction in the approval workflow."""
    # Approval workflow statuses
    PENDING_SECTION = "PENDING_SECTION"    # Level 1 - Section approver
    PENDING_OFFICE = "PENDING_OFFICE"      # Level 2 - Office approver
    PENDING_ZONE = "PENDING_ZONE"          # Level 3 - Zone approver
    PENDING_FINANCE = "PENDING_FINANCE"    # Level 4 - Comptroller
    APPROVED = "APPROVED"                  # Final approval
    REJECTED = "REJECTED"                  # Returned to user
    
    # Budget operation statuses (kept for backwards compatibility)
    BLOCKED = "BLOCKED"
    RELEASED = "RELEASED"
    SPENT = "SPENT"


# ============================================================
# Request Schemas
# ============================================================

class BlockFundsRequest(BaseModel):
    """Request to block/reserve funds for a pending request."""
    budget_row_id: int = Field(
        ..., 
        description="ID of the BudgetRow to reserve funds from"
    )
    amount: int = Field(
        ..., 
        gt=0, 
        description="Amount to block in Rials (must be positive)"
    )
    request_reference_id: str = Field(
        ..., 
        description="Reference ID of the related request (e.g., 'REQ-2024-001')"
    )
    notes: Optional[str] = Field(
        None, 
        description="Optional notes for audit trail"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "budget_row_id": 42,
                "amount": 10000000,
                "request_reference_id": "REQ-2024-001",
                "notes": "Monthly expense claim"
            }
        }
    }


class ReleaseFundsRequest(BaseModel):
    """Request to release blocked funds (when request is rejected)."""
    transaction_id: int = Field(
        ..., 
        description="ID of the BLOCK transaction to reverse"
    )
    notes: Optional[str] = Field(
        None, 
        description="Reason for release (e.g., 'Request rejected by manager')"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id": 123,
                "notes": "Request rejected - incorrect documentation"
            }
        }
    }


class ConfirmSpendRequest(BaseModel):
    """Request to confirm spending (move from blocked to spent)."""
    transaction_id: int = Field(
        ..., 
        description="ID of the BLOCK transaction to confirm"
    )
    notes: Optional[str] = Field(
        None, 
        description="Payment confirmation notes"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id": 123,
                "notes": "Payment processed - Check #456789"
            }
        }
    }


# ============================================================
# Response Schemas
# ============================================================

class BudgetCheckResponse(BaseModel):
    """Response for pre-flight budget availability check."""
    budget_row_id: int
    budget_code: str
    description: str
    activity_id: int
    activity_code: Optional[str] = None
    fiscal_year: str
    
    # Financial amounts (in Rials)
    total_approved: int = Field(..., description="Total approved budget")
    total_blocked: int = Field(..., description="Funds reserved for pending requests")
    total_spent: int = Field(..., description="Funds already spent")
    remaining_available: int = Field(..., description="Available for new requests")
    
    # Status indicator
    status: BudgetStatus
    utilization_percent: float = Field(..., description="Percentage of budget utilized")

    model_config = {
        "json_schema_extra": {
            "example": {
                "budget_row_id": 42,
                "budget_code": "20501001",
                "description": "Operating expenses",
                "activity_id": 15,
                "activity_code": "PAYROLL_01",
                "fiscal_year": "1403",
                "total_approved": 100000000,
                "total_blocked": 10000000,
                "total_spent": 30000000,
                "remaining_available": 60000000,
                "status": "AVAILABLE",
                "utilization_percent": 40.0
            }
        }
    }


class BudgetTransactionResponse(BaseModel):
    """Response for block/release/confirm operations."""
    transaction_id: int
    budget_row_id: int
    budget_code: str
    status: TransactionStatus
    amount: int
    reference_doc: Optional[str]
    performed_by: str
    created_at: datetime
    
    # Updated balance after operation
    new_remaining_balance: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id": 123,
                "budget_row_id": 42,
                "budget_code": "20501001",
                "status": "BLOCKED",
                "amount": 10000000,
                "reference_doc": "REQ-2024-001",
                "performed_by": "user_123",
                "created_at": "2024-01-15T10:30:00",
                "new_remaining_balance": 50000000
            }
        }
    }


class BudgetListResponse(BaseModel):
    """Response for listing budget rows by activity."""
    budget_rows: List[BudgetCheckResponse]
    total_count: int


# ============================================================
# Error Response Schemas
# ============================================================

class InsufficientFundsResponse(BaseModel):
    """Error response when budget is insufficient."""
    error: str = "INSUFFICIENT_FUNDS"
    message: str
    budget_row_id: int
    requested_amount: int
    available_balance: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "INSUFFICIENT_FUNDS",
                "message": "Not enough funds available",
                "budget_row_id": 42,
                "requested_amount": 50000000,
                "available_balance": 30000000
            }
        }
    }


class BudgetNotFoundResponse(BaseModel):
    """Error response when budget row is not found."""
    error: str = "BUDGET_NOT_FOUND"
    message: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "BUDGET_NOT_FOUND",
                "message": "No budget allocated for this activity"
            }
        }
    }
