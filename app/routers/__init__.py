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
- treasury_integration: Treasury System (Khazaneh-dari) integration API
- contractors: Contractor CRUD + Setad integration (Phase 2)
- templates: Contract Template CRUD (Phase 2)
- contracts: Contract Lifecycle Wizard (Sprint 2)
- statements: Progress Statement Lifecycle (Sprint 3)
- reports: Executive Dashboard aggregation (Sprint 4)
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
from .treasury_integration import router as treasury_integration_router
from .credit_requests import router as credit_requests_router
from .contractors import router as contractors_router
from .templates import router as templates_router
from .contracts import router as contracts_router
from .statements import router as statements_router
from .reports import router as reports_router

__all__ = [
    "budget_router", "rbac_router", "auth_router", "admin_router",
    "portal_router", "subsystems_router", "orgs_router", 
    "test_mode_router", "accounts_router", "accounting_router",
    "treasury_integration_router", "credit_requests_router",
    "contractors_router", "templates_router", "contracts_router",
    "statements_router", "reports_router",
]

