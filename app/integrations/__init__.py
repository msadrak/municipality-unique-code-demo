"""
Anti-Corruption Layer (ACL) - External Integration Package
==========================================================

Hexagonal Architecture: Port-Adapter pattern for external systems.
Swap adapters via INTEGRATION_MODE env var ("mock" | "live").

Ports (abstract interfaces):
  - SetadPort: Contractor lookup from Setad Iran e-procurement system
  - CreditSystemPort: Credit provision system integration

Adapters (implementations):
  - setad_mock: Returns test data (Phase 2 default)
  - credit_mock: Auto-approves credit requests (Phase 2 default)
"""

from .registry import get_setad_port, get_credit_port

__all__ = ["get_setad_port", "get_credit_port"]
