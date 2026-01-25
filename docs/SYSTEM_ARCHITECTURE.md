# Municipality System Architecture

## Overview

This document explains the complete backend structure, frontend integration, and the transaction flow.

---

## Backend Structure

```
app/
├── main.py                 # App entry point, router mounting, HTML serving
├── database.py             # SQLAlchemy engine & session
├── models.py               # Database ORM models (28 tables)
├── auth_utils.py           # Password hashing (Argon2 + SHA-256 migration)
├── routers/                # API endpoint modules
│   ├── auth.py             # Authentication (login, logout, register)
│   ├── admin.py            # Admin workflow (approve/reject)
│   ├── portal.py           # User portal (create transaction, dashboard)
│   ├── subsystems.py       # Subsystem management
│   ├── orgs.py             # Org structure, budgets
│   ├── budget.py           # Budget control (block/release/confirm)
│   ├── rbac.py             # Role-based access control
│   ├── test_mode.py        # Excel verification
│   └── accounts.py         # Account codes
├── schemas/                # Pydantic models
└── services/               # Business logic
```

---

## Key Database Models (models.py)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│      User       │────>│   Transaction   │<────│   BudgetItem    │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id              │     │ id              │     │ id              │
│ username        │     │ unique_code     │     │ budget_code     │
│ password_hash   │     │ status          │     │ allocated_1403  │
│ role            │     │ amount          │     │ remaining_budget│
│ admin_level     │     │ created_by_id   │     │ reserved_amount │
│ default_zone_id │     │ zone_id         │     │ spent_1403      │
│ default_section │     │ budget_item_id  │     └─────────────────┘
└─────────────────┘     │ rejection_reason│
                        └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │  WorkflowLog    │
                        ├─────────────────┤
                        │ transaction_id  │
                        │ admin_id        │
                        │ admin_level     │
                        │ action          │
                        │ previous_status │
                        │ new_status      │
                        └─────────────────┘
```

---

## Frontend Structure

```
frontend/src/
├── App.tsx                 # React Router, main routes
├── components/
│   ├── Login.tsx           # Login page
│   ├── UserPortal.tsx      # Main user dashboard
│   ├── AdminDashboard.tsx  # Admin approval interface
│   ├── TransactionWizard.tsx # Multi-step transaction creation
│   ├── MyTransactionsList.tsx # User's transaction history
│   └── wizard-steps/       # Wizard step components
├── services/
│   ├── api.ts              # Base API client
│   ├── auth.ts             # Auth service (login/logout)
│   └── adapters.ts         # Data transformation
└── types/                  # TypeScript interfaces
```

---

## Frontend ↔ Backend Communication

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                         │
│                      http://localhost:3000                       │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                    API Calls (fetch/axios)
                    Cookie: session_token
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Vite Dev Server Proxy                        │
│              /auth/*, /portal/*, /admin/* → :8000                │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                         │
│                      http://localhost:8000                       │
├─────────────────────────────────────────────────────────────────┤
│  auth_router    │  admin_router   │  portal_router  │  ...      │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        SQLite Database                           │
│                        municipality.db                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Complete Transaction Flow

### Phase 1: User Login

```
┌──────────────┐    POST /auth/login     ┌──────────────┐
│   Frontend   │ ───────────────────────>│   Backend    │
│  Login.tsx   │   {username, password}  │  auth.py     │
└──────────────┘                         └──────┬───────┘
                                                │
                                                ▼
                                    ┌───────────────────┐
                                    │ 1. Query User     │
                                    │ 2. Verify Password│
                                    │ 3. Create Session │
                                    │ 4. Set Cookie     │
                                    └───────────────────┘
                                                │
       Set-Cookie: session_token=xxx            │
┌──────────────┐<───────────────────────────────┘
│   Frontend   │    {status: "success", user: {...}}
│  → Portal    │
└──────────────┘
```

### Phase 2: Dashboard Initialization

```
┌──────────────┐   GET /portal/dashboard/init   ┌──────────────┐
│  UserPortal  │ ──────────────────────────────>│  portal.py   │
│              │   Cookie: session_token        │              │
└──────────────┘                                └──────┬───────┘
                                                       │
                                                       ▼
                                        ┌──────────────────────────┐
                                        │ 1. Get user from session │
                                        │ 2. Get user's zone/section│
                                        │ 3. Get allowed subsystems │
                                        │ 4. Get allowed activities │
                                        │ 5. Get budget constraints │
                                        └──────────────────────────┘
                                                       │
┌──────────────┐<──────────────────────────────────────┘
│  UserPortal  │   DashboardInitResponse:
│  Shows Grid  │   - user_context
│  of Activities   - subsystem
└──────────────┘   - allowed_activities[]
```

### Phase 3: Transaction Creation (Wizard)

```
User clicks activity card → Opens TransactionWizard

Step 1: Activity Already Selected (from card click)

Step 2: Budget Selection
┌──────────────┐   GET /portal/budgets/for-org?zone_id=X   ┌──────────────┐
│   Wizard     │ ─────────────────────────────────────────>│   orgs.py    │
│   Step 2     │                                           └──────┬───────┘
└──────────────┘                                                  │
       │                                                          ▼
       │                                           ┌───────────────────────────┐
       │                                           │ Query BudgetItem table    │
       │                                           │ Filter by zone/trustee    │
       │                                           │ Show remaining_budget     │
       │                                           └───────────────────────────┘
       │
       ▼
Step 3: Financial Event Selection
┌──────────────┐   GET /portal/financial-events            ┌──────────────┐
│   Wizard     │ ─────────────────────────────────────────>│   orgs.py    │
│   Step 3     │                                           └──────────────┘
└──────────────┘

Step 4: Contract Details (Beneficiary, Amount, etc.)
       │
       ▼
Step 5: Review & Submit
┌──────────────┐   POST /portal/transactions/create        ┌──────────────┐
│   Wizard     │ ─────────────────────────────────────────>│  portal.py   │
│   Submit     │   CreateTransactionRequest:               └──────┬───────┘
└──────────────┘   {zone_id, budget_code, amount, ...}            │
                                                                  │
                                                                  ▼
```

### Phase 4: Transaction Creation (Backend Detail)

```python
# portal.py - create_transaction()

def create_transaction(data: CreateTransactionRequest, request: Request, db):
    
    # 1. AUTHENTICATION CHECK
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(401, "احراز هویت الزامی است")
    
    # 2. GET ORG UNIT CODES
    zone = db.query(OrgUnit).filter(OrgUnit.id == data.zone_id).first()
    zone_code = zone.code.zfill(2)  # e.g., "20"
    
    # 3. GENERATE 11-PART UNIQUE CODE
    # Format: ZZ-DD-SSS-BBBB-CCC-AA-HHH-BBBBBB-FFF-YYYY-NNN
    unique_code = f"{zone_code}-{dept_code}-{section_code}-{budget_code}-..."
    
    # 4. BUDGET CHECK & RESERVATION
    budget_item = db.query(BudgetItem).filter(
        BudgetItem.budget_code == data.budget_code
    ).first()
    
    remaining = budget_item.remaining_budget - budget_item.reserved_amount
    if remaining < data.amount:
        raise HTTPException(400, f"بودجه کافی نیست. مانده: {remaining}")
    
    # RESERVE the funds (blocked until approved/rejected)
    budget_item.reserved_amount += data.amount
    
    # 5. CREATE TRANSACTION RECORD
    transaction = Transaction(
        unique_code=unique_code,
        status="PENDING_L1",          # ← Starts at Level 1
        current_approval_level=0,
        created_by_id=current_user.id,
        amount=data.amount,
        ...
    )
    db.add(transaction)
    db.commit()
    
    return {"status": "success", "unique_code": unique_code}
```

### Phase 5: 4-Level Approval Workflow

```
                    ┌─────────────────────────────────────────────┐
                    │              TRANSACTION LIFECYCLE           │
                    └─────────────────────────────────────────────┘

User Creates → [PENDING_L1] → [PENDING_L2] → [PENDING_L3] → [PENDING_L4] → [APPROVED]
                    │              │              │              │
                    │              │              │              │
               ┌────▼────┐   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
               │ Level 1 │   │ Level 2 │   │ Level 3 │   │ Level 4 │
               │ Section │   │  Dept   │   │  Zone   │   │   Top   │
               │  Admin  │   │  Admin  │   │  Admin  │   │  Admin  │
               └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘
                    │              │              │              │
                    ▼              ▼              ▼              ▼
               Approve?       Approve?       Approve?       Approve?
                Yes│No         Yes│No         Yes│No         Yes│No
                   │ │            │ │            │ │            │ │
                   │ ▼            │ ▼            │ ▼            │ ▼
                   │[REJECTED]   │[REJECTED]   │[REJECTED]   │[REJECTED]
                   │    or       │    or       │    or       │
                   │[DRAFT]      │[DRAFT]      │[DRAFT]      │
                   │(return)     │(return)     │(return)     │
                   ▼                                          ▼
              PENDING_L2 ────────────────────────────────> APPROVED
```

### Phase 6: Admin Approval (Backend)

```python
# admin.py - admin_approve_transaction()

def admin_approve_transaction(transaction_id: int, request: Request, db):
    
    # 1. CHECK ADMIN ACCESS
    current_user = get_current_user(request, db)
    admin_level = current_user.admin_level  # 1, 2, 3, or 4
    
    # 2. GET TRANSACTION
    t = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    
    # 3. WORKFLOW MAP - Who can approve what
    workflow_map = {
        "PENDING_L1": ("PENDING_L2", "ADMIN_L1", 1),  # L1 admin → moves to L2
        "PENDING_L2": ("PENDING_L3", "ADMIN_L2", 2),  # L2 admin → moves to L3
        "PENDING_L3": ("PENDING_L4", "ADMIN_L3", 3),  # L3 admin → moves to L4
        "PENDING_L4": ("APPROVED",   "ADMIN_L4", 4),  # L4 admin → FINAL APPROVAL
    }
    
    new_status, required_role, level = workflow_map[t.status]
    
    # 4. PERMISSION CHECK
    if current_user.role != required_role:
        raise HTTPException(403, "شما مجوز تایید این تراکنش را ندارید")
    
    # 5. IF FINAL APPROVAL → DEDUCT BUDGET
    if new_status == "APPROVED":
        budget = db.query(BudgetItem).filter(BudgetItem.id == t.budget_item_id).first()
        budget.remaining_budget -= t.amount       # Deduct from available
        budget.reserved_amount -= t.amount        # Release reservation
        budget.spent_1403 += t.amount             # Add to spent
    
    # 6. UPDATE TRANSACTION STATUS
    t.status = new_status
    t.reviewed_by_id = current_user.id
    t.reviewed_at = datetime.utcnow()
    
    # 7. LOG WORKFLOW ACTION
    log = WorkflowLog(
        transaction_id=t.id,
        admin_id=current_user.id,
        admin_level=level,
        action="APPROVE",
        previous_status=previous,
        new_status=new_status
    )
    db.add(log)
    db.commit()
```

### Phase 7: Rejection Flow

```
Admin hits "Reject" button

┌──────────────┐   POST /admin/transactions/{id}/reject   ┌──────────────┐
│    Admin     │ ─────────────────────────────────────────>│   admin.py   │
│  Dashboard   │   {reason: "...", return_to_user: bool}   └──────┬───────┘
└──────────────┘                                                  │
                                                                  ▼
                                              ┌─────────────────────────────┐
                                              │ 1. Validate admin permission │
                                              │ 2. RELEASE reserved budget   │
                                              │    budget.reserved -= amount │
                                              │ 3. Set status:               │
                                              │    return_to_user=True → DRAFT│
                                              │    return_to_user=False→ REJECTED│
                                              │ 4. Store rejection_reason    │
                                              │ 5. Log to WorkflowLog        │
                                              └─────────────────────────────┘

User sees rejected transaction with reason in MyTransactionsList
```

---

## Budget Control Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        BUDGET LIFECYCLE                          │
└─────────────────────────────────────────────────────────────────┘

Initial State:
┌──────────────────────────────────────────────────────────┐
│ allocated_1403: 100,000,000                              │
│ remaining_budget: 100,000,000                            │
│ reserved_amount: 0                                        │
│ spent_1403: 0                                             │
└──────────────────────────────────────────────────────────┘

After Transaction Created (amount: 10,000,000):
┌──────────────────────────────────────────────────────────┐
│ remaining_budget: 100,000,000  (unchanged)               │
│ reserved_amount: 10,000,000    (BLOCKED)                 │
│ available = remaining - reserved = 90,000,000            │
└──────────────────────────────────────────────────────────┘

After Final Approval:
┌──────────────────────────────────────────────────────────┐
│ remaining_budget: 90,000,000   (DEDUCTED)                │
│ reserved_amount: 0             (RELEASED)                │
│ spent_1403: 10,000,000         (RECORDED)                │
└──────────────────────────────────────────────────────────┘

After Rejection:
┌──────────────────────────────────────────────────────────┐
│ remaining_budget: 100,000,000  (unchanged)               │
│ reserved_amount: 0             (RELEASED)                │
│ spent_1403: 0                  (NOT recorded)            │
└──────────────────────────────────────────────────────────┘
```

---

## Session / Authentication Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                        SESSION MANAGEMENT                           │
└────────────────────────────────────────────────────────────────────┘

1. User logs in → Backend creates session token
2. Token stored in: active_sessions = {token: {user_id, expires_at}}
3. Token sent to client as HttpOnly cookie
4. Every API request includes cookie automatically
5. Backend validates token on each request via get_current_user()

┌─────────────┐                    ┌─────────────┐
│   Browser   │   session_token    │   Backend   │
│   (React)   │◄──────────────────►│  (FastAPI)  │
└─────────────┘   HttpOnly Cookie  └─────────────┘
                                          │
                                          ▼
                               active_sessions = {
                                 "abc123...": {
                                   user_id: 5,
                                   expires_at: datetime
                                 }
                               }
```

---

## API Endpoint Summary

| Endpoint | Method | Router | Description |
|----------|--------|--------|-------------|
| `/auth/login` | POST | auth.py | User login |
| `/auth/me` | GET | auth.py | Get current user |
| `/portal/dashboard/init` | GET | portal.py | Dashboard data |
| `/portal/transactions/create` | POST | portal.py | Create transaction |
| `/portal/my-transactions` | GET | portal.py | User's transactions |
| `/admin/transactions` | GET | admin.py | Admin transaction list |
| `/admin/transactions/{id}/approve` | POST | admin.py | Approve |
| `/admin/transactions/{id}/reject` | POST | admin.py | Reject |
| `/portal/budgets/for-org` | GET | orgs.py | Get budgets |
| `/portal/financial-events` | GET | orgs.py | Get events |

---

## 11-Part Unique Code Structure

```
XX-YY-ZZZ-BBBB-CCC-AA-HHH-NNNNNN-FFF-YYYY-SSS
│  │  │   │    │   │  │   │      │   │    │
│  │  │   │    │   │  │   │      │   │    └── Sequence (001, 002...)
│  │  │   │    │   │  │   │      │   └─────── Fiscal Year (1403)
│  │  │   │    │   │  │   │      └─────────── Financial Event (000-999)
│  │  │   │    │   │  │   └────────────────── Beneficiary Hash (6 chars)
│  │  │   │    │   │  └────────────────────── Special Activity Hash (3 chars)
│  │  │   │    │   └───────────────────────── Continuous Activity (00-99)
│  │  │   │    └───────────────────────────── Cost Center (000-999)
│  │  │   └────────────────────────────────── Budget Code (0000-9999)
│  │  └────────────────────────────────────── Section Code (000-999)
│  └───────────────────────────────────────── Department Code (00-99)
└──────────────────────────────────────────── Zone Code (20, 21...)

Example: 20-04-001-1501-001-05-ABC-D1E2F3-002-1403-001
```
