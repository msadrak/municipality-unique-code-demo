"""
Integration Registry - Adapter Selection
==========================================

Reads INTEGRATION_MODE env var to select the correct adapter.
Default: "mock" (Phase 2 demo mode).

Usage:
    from app.integrations import get_setad_port, get_credit_port
    
    setad = get_setad_port()
    result = setad.search_contractors("عمران")
"""
import os
from typing import Union

from .setad_mock import SetadMockAdapter
from .credit_mock import CreditMockAdapter

# Read integration mode from environment (default: mock)
INTEGRATION_MODE = os.getenv("INTEGRATION_MODE", "mock").lower()

# Singleton instances (created once, reused)
_setad_instance: Union[SetadMockAdapter, None] = None
_credit_instance: Union[CreditMockAdapter, None] = None


def get_setad_port() -> SetadMockAdapter:
    """
    Get the active Setad adapter instance.
    
    Returns SetadMockAdapter in Phase 2.
    When real API is ready, add SetadRealAdapter and switch here.
    """
    global _setad_instance
    
    if _setad_instance is None:
        if INTEGRATION_MODE == "live":
            # Future: from .setad_adapter import SetadRealAdapter
            # _setad_instance = SetadRealAdapter(api_url=os.getenv("SETAD_API_URL"))
            raise NotImplementedError(
                "Live Setad integration not yet available. "
                "Set INTEGRATION_MODE=mock or implement setad_adapter.py"
            )
        else:
            _setad_instance = SetadMockAdapter()
    
    return _setad_instance


def get_credit_port() -> CreditMockAdapter:
    """
    Get the active Credit System adapter instance.
    
    Returns CreditMockAdapter in Phase 2.
    When real API is ready, add CreditRealAdapter and switch here.
    """
    global _credit_instance
    
    if _credit_instance is None:
        if INTEGRATION_MODE == "live":
            # Future: from .credit_adapter import CreditRealAdapter
            # _credit_instance = CreditRealAdapter(api_url=os.getenv("CREDIT_API_URL"))
            raise NotImplementedError(
                "Live Credit System integration not yet available. "
                "Set INTEGRATION_MODE=mock or implement credit_adapter.py"
            )
        else:
            _credit_instance = CreditMockAdapter()
    
    return _credit_instance
