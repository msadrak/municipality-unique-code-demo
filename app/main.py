"""
Municipality Action Portal - Main Application
==============================================

This is the main FastAPI application that mounts all routers.
The business logic has been split into separate router modules for maintainability.

Routers:
- auth: Authentication and session management
- admin: Admin transaction management
- portal: User portal endpoints
- subsystems: Subsystem/activity management
- orgs: Organization structure and budgets
- test_mode: Excel-based test endpoints
- accounts: Account codes API
- budget: Budget control (existing)
- rbac: Role-based access control (existing)
- accounting: Accounting posting module (NEW)
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.exceptions import ResponseValidationError
import os
import hashlib
import logging

from app import models
from app.database import SessionLocal, engine

# Configure logging for response validation errors
logger = logging.getLogger(__name__)
from app.routers import (
    auth_router, admin_router, budget_router, rbac_router,
    portal_router, subsystems_router, orgs_router, 
    test_mode_router, accounts_router, accounting_router,
    treasury_integration_router, credit_requests_router,
    contractors_router, templates_router, contracts_router,
    statements_router, reports_router,
)
from pydantic import BaseModel

# --- FastAPI App ---
app = FastAPI(title="Municipality Action Portal")

# --- Database Initialization (lazy - on startup) ---
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on server startup"""
    try:
        models.Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed (PostgreSQL may not be running): {e}")
        logger.warning("Server will continue, but database operations may fail until PostgreSQL is available")

# --- Register API Routers ---
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(portal_router)
app.include_router(subsystems_router)
app.include_router(orgs_router)
app.include_router(test_mode_router)
app.include_router(accounts_router)
app.include_router(budget_router, tags=["Budget Control"])
app.include_router(rbac_router, tags=["RBAC - Access Control"])
app.include_router(accounting_router)
app.include_router(treasury_integration_router)
app.include_router(credit_requests_router)
app.include_router(contractors_router)
app.include_router(templates_router)
app.include_router(contracts_router)
app.include_router(statements_router)
app.include_router(reports_router, tags=["Reports"])

# --- CORS Configuration ---
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# --- Response Validation Error Handler ---
# Catches ORM/Schema mismatches and prevents leaking internal details
@app.exception_handler(ResponseValidationError)
async def response_validation_exception_handler(request: Request, exc: ResponseValidationError):
    """
    Handle response validation errors (ORM/Schema mismatches).
    
    This prevents 500 errors from leaking internal exception details.
    Logs full error for debugging while returning sanitized response.
    """
    logger.error(f"Response validation failed for {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# --- Mount React Build Static Files ---
REACT_BUILD_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "build")
ARCHIVE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "archive")
if os.path.exists(REACT_BUILD_PATH):
    app.mount("/react-assets", StaticFiles(directory=os.path.join(REACT_BUILD_PATH, "assets")), name="react-assets")


# Helper function to serve React app with proper asset paths
def serve_react_app():
    """Serve React build index.html with corrected asset paths"""
    react_index = os.path.join(REACT_BUILD_PATH, "index.html")
    if os.path.exists(react_index):
        with open(react_index, "r", encoding="utf-8") as f:
            html = f.read()
            html = html.replace('="/assets/', '="/react-assets/')
            html = html.replace("='/assets/", "='/react-assets/")
            return html
    return None


# --- Portal Submit (for legacy 11-part code generation) ---
class PortalSubmit(BaseModel):
    zone: str
    dept_code: str = "00"
    section_code: str = "000"
    budget_code: str
    budget_title: str = ""
    cost_center: str = "000"
    continuous_activity: str = "00"
    special_activity: str = ""
    contractor_name: str
    contract_number: str = "0000"
    financial_event: str = "000"
    date: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/portal/submit")
def submit_action(data: PortalSubmit):
    """Generate 11-Part Unique Code (legacy endpoint)"""
    zone_code = data.zone.zfill(2) if data.zone.isdigit() else "00"
    dept_code = data.dept_code.zfill(2) if data.dept_code else "00"
    section_code = data.section_code.zfill(3) if data.section_code else "000"
    budget_code = data.budget_code.zfill(4) if data.budget_code else "0000"
    cost_center = data.cost_center.zfill(3) if data.cost_center else "000"
    cont_act = data.continuous_activity.zfill(2) if data.continuous_activity else "00"
    spec_act_hash = hashlib.md5(data.special_activity.encode()).hexdigest()[:3].upper() if data.special_activity else "000"
    name_clean = data.contractor_name.strip() or "Unknown"
    ben_hash = hashlib.md5(name_clean.encode()).hexdigest()[:6].upper()
    fin_event = data.financial_event.zfill(3) if data.financial_event else "000"
    date_code = data.date.split("/")[0] if "/" in data.date else data.date[:4]
    occurrence = "001"  # Would need DB query for proper incrementing
    
    unique_code = f"{zone_code}-{dept_code}-{section_code}-{budget_code}-{cost_center}-{cont_act}-{spec_act_hash}-{ben_hash}-{fin_event}-{date_code}-{occurrence}"
    
    return {
        "status": "success",
        "generated_code": unique_code,
        "message": "کد یکتا 11 قسمتی با موفقیت تولید شد"
    }


# --- HTML Page Serving (React-First with Archive Fallback) ---
@app.get("/login", response_class=HTMLResponse)
def read_login():
    """Serve React app for login (legacy HTML archived)"""
    react_html = serve_react_app()
    if react_html:
        return react_html
    # Fallback to archived HTML
    try:
        with open(os.path.join(ARCHIVE_PATH, "login.html"), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>React build not found. Run 'npm run build' in frontend/</h1>"


@app.get("/portal", response_class=HTMLResponse)
def read_portal():
    """Serve React app for portal (legacy HTML archived)"""
    react_html = serve_react_app()
    if react_html:
        return react_html
    # Fallback to archived HTML
    try:
        with open(os.path.join(ARCHIVE_PATH, "portal.html"), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>React build not found. Run 'npm run build' in frontend/</h1>"


@app.get("/admin", response_class=HTMLResponse)
def read_admin():
    """Serve React app for admin dashboard (legacy HTML archived)"""
    react_html = serve_react_app()
    if react_html:
        return react_html
    # Fallback to archived HTML
    try:
        with open(os.path.join(ARCHIVE_PATH, "admin.html"), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>React build not found. Run 'npm run build' in frontend/</h1>"


@app.get("/portal/test2", response_class=HTMLResponse)
def read_test_mode2():
    """Serve Test Mode 2 page (standalone debug tool - kept as-is)"""
    try:
        with open("test_mode2.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error: test_mode2.html not found!</h1>"


@app.get("/", response_class=HTMLResponse)
def root():
    """Serve React app for root (public dashboard)"""
    react_html = serve_react_app()
    if react_html:
        return react_html
    # Fallback to archived HTML
    try:
        with open(os.path.join(ARCHIVE_PATH, "index.html"), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return RedirectResponse(url="/login")

