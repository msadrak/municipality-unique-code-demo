# app/routers/__init__.py
"""
API Routers for Municipality ERP
================================

Router Modules:
- auth: Authentication, session management, user registration
- admin: Transaction management with 4-level approval workflow
- portal: User-facing transaction creation and dashboard
- subsystems: Subsystem and activity management
- orgs: Organizational structure and budget endpoints
- test_mode: Excel-based test/verification endpoints
- accounts: Account codes API
- budget: Budget control and reservation
- rbac: Role-based access control
- accounting: Accounting posting module
"""

from .budget import router as budget_router
from .rbac import router as rbac_router
from .auth import router as auth_router
from .admin import router as admin_router
from .portal import router as portal_router
from .subsystems import router as subsystems_router
from .orgs import router as orgs_router
from .test_mode import router as test_mode_router
from .accounts import router as accounts_router
from .accounting import router as accounting_router

__all__ = [
    "budget_router", "rbac_router", "auth_router", "admin_router",
    "portal_router", "subsystems_router", "orgs_router", 
    "test_mode_router", "accounts_router", "accounting_router"
]
