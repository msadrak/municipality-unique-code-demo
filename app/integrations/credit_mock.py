"""
Mock Credit System Adapter
===========================

Auto-approves credit requests for Phase 2 demo.
Implements CreditSystemPort protocol without inheritance.

When the real Credit System API becomes available, create credit_adapter.py
implementing the same interface with actual HTTP calls.
"""
import uuid
from .ports import CreditSubmitRequest, CreditApprovalResponse, CreditStatusResponse


# In-memory store for mock status tracking
_MOCK_REQUESTS: dict[str, CreditStatusResponse] = {}


class CreditMockAdapter:
    """
    Mock implementation of CreditSystemPort for Phase 2 demo.
    
    Auto-approves all credit requests and tracks them in memory.
    """
    
    def submit_credit_request(self, request: CreditSubmitRequest) -> CreditApprovalResponse:
        """Auto-approve the credit request and return a mock reference ID."""
        ref_id = f"CRED-MOCK-{uuid.uuid4().hex[:8].upper()}"
        
        # Store for status lookups
        _MOCK_REQUESTS[ref_id] = CreditStatusResponse(
            ref_id=ref_id,
            status="APPROVED",
            message="تایید خودکار (محیط آزمایشی)",
        )
        
        return CreditApprovalResponse(
            ref_id=ref_id,
            status="APPROVED",
            approved_amount=request.amount,
            message="تایید خودکار (محیط آزمایشی)",
        )
    
    def check_status(self, ref_id: str) -> CreditStatusResponse:
        """Check status of a previously submitted mock request."""
        if ref_id in _MOCK_REQUESTS:
            return _MOCK_REQUESTS[ref_id]
        
        return CreditStatusResponse(
            ref_id=ref_id,
            status="NOT_FOUND",
            message="درخواست یافت نشد",
        )
