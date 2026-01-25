# Backend Documentation

## Overview

The Municipality Action Portal backend is built with FastAPI and provides APIs for:
- User authentication and session management
- Transaction creation and 4-level approval workflow
- Budget control with reservation system
- Subsystem and activity management
- Organizational unit hierarchies

## Directory Structure

```
app/
├── main.py                 # App initialization, router mounting
├── models.py               # SQLAlchemy ORM models
├── database.py             # Database connection
├── auth_utils.py           # Password hashing (Argon2)
├── routers/                # API endpoint modules
│   ├── auth.py             # Login, logout, registration
│   ├── admin.py            # Transaction management
│   ├── portal.py           # User portal endpoints
│   ├── subsystems.py       # Subsystem/activity APIs
│   ├── orgs.py             # Organization & budget APIs
│   ├── test_mode.py        # Excel verification endpoints
│   ├── accounts.py         # Account codes API
│   ├── budget.py           # Budget control API
│   └── rbac.py             # Access control
├── schemas/                # Pydantic request/response models
├── services/               # Business logic
└── config/                 # Configuration files
```

## Running the Server

```bash
cd municipality_demo
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

API docs available at: `http://localhost:8000/docs`

## Key Features

### 4-Level Approval Workflow
Transactions flow through 4 approval levels:
1. **PENDING_L1** → Section admin review
2. **PENDING_L2** → Department admin review
3. **PENDING_L3** → Zone admin review
4. **PENDING_L4** → Top admin final approval → **APPROVED**

### Budget Reservation System
- Pre-flight checks for budget availability
- Funds blocked when transaction created
- Released on rejection, confirmed on final approval

### Session Management
In-memory sessions for development. Use Redis for production.
