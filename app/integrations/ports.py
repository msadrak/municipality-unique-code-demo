"""
Integration Ports - Abstract Interfaces
========================================

Defines the contracts that all adapters must implement.
Uses Python Protocol (structural subtyping) for zero-inheritance flexibility.
"""
from typing import Protocol, Optional, List
from dataclasses import dataclass


# ============================================================
# Data Transfer Objects (DTOs)
# ============================================================

@dataclass
class ContractorInfo:
    """Data returned from Setad contractor lookup."""
    national_id: str
    company_name: str
    registration_number: Optional[str] = None
    ceo_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    setad_ref_id: Optional[str] = None
    is_verified: bool = False


@dataclass
class CreditApprovalResponse:
    """Response from Credit System for a credit provision request."""
    ref_id: str
    status: str  # APPROVED, REJECTED, PENDING
    approved_amount: Optional[float] = None
    message: Optional[str] = None


@dataclass
class CreditStatusResponse:
    """Status check response from Credit System."""
    ref_id: str
    status: str  # APPROVED, REJECTED, PENDING
    message: Optional[str] = None


@dataclass
class CreditSubmitRequest:
    """Request payload for submitting to Credit System."""
    budget_code: str
    amount: float
    description: str
    zone_id: int
    fiscal_year: str = "1403"


# ============================================================
# Port Interfaces (Protocols)
# ============================================================

class SetadPort(Protocol):
    """
    Abstract interface for Setad Iran e-procurement system.
    
    Setad (سامانه تدارکات الکترونیکی دولت) provides:
    - Contractor/vendor verification
    - Auction winner lookup
    - Contractor search
    """
    
    def fetch_auction_winner(self, auction_id: str) -> Optional[ContractorInfo]:
        """Fetch the winning contractor for a specific auction."""
        ...
    
    def verify_contractor(self, national_id: str) -> bool:
        """Verify if a contractor exists and is valid in Setad."""
        ...
    
    def search_contractors(self, query: str) -> List[ContractorInfo]:
        """Search contractors by name or partial national ID."""
        ...


class CreditSystemPort(Protocol):
    """
    Abstract interface for the Credit Provision System.
    
    Handles submission and status tracking of credit provision requests
    (درخواست تامین اعتبار) to the central financial system.
    """
    
    def submit_credit_request(self, request: CreditSubmitRequest) -> CreditApprovalResponse:
        """Submit a credit provision request."""
        ...
    
    def check_status(self, ref_id: str) -> CreditStatusResponse:
        """Check the status of a previously submitted request."""
        ...
