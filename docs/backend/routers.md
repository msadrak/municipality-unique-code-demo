# API Routers Documentation

## Router Modules

### auth.py - Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | POST | User login, creates session |
| `/auth/logout` | POST | Destroys session |
| `/auth/me` | GET | Get current user info |
| `/auth/register` | POST | Register new user (admin only) |
| `/auth/users` | GET | List all users (admin only) |

### admin.py - Admin Transactions
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/transactions` | GET | List transactions with filters |
| `/admin/transactions/{id}` | GET | Get transaction detail |
| `/admin/transactions/{id}/approve` | POST | Approve (moves to next level) |
| `/admin/transactions/{id}/reject` | POST | Reject with reason |

### portal.py - User Portal
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/portal/transactions/create` | POST | Create new transaction |
| `/portal/my-transactions` | GET | User's transactions |
| `/portal/user/allowed-activities` | GET | Allowed activities for user |
| `/portal/dashboard/init` | GET | Dashboard initialization data |

### subsystems.py - Subsystems
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/portal/subsystems` | GET | List all subsystems |
| `/portal/subsystems/{id}/activities` | GET | Activities for subsystem |
| `/portal/subsystems/for-section/{id}` | GET | Subsystems for section |

### orgs.py - Organizations & Budgets
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/portal/org/roots` | GET | Top-level zones |
| `/portal/org/children/{id}` | GET | Children of org unit |
| `/portal/budgets/for-org` | GET | Budgets by org context |
| `/portal/budgets/all` | GET | All budgets |
| `/portal/cost-centers` | GET | Cost centers |
| `/portal/financial-events` | GET | Financial events |

### budget.py - Budget Control
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/budget/check/{activity_id}` | GET | Pre-flight budget check |
| `/budget/block` | POST | Reserve funds |
| `/budget/release` | POST | Release reserved funds |
| `/budget/confirm` | POST | Confirm (deduct) funds |

### accounts.py - Account Codes
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/account-codes` | GET | List account codes |
| `/api/account-codes/stats` | GET | Statistics |
| `/api/account-codes/{id}` | GET | Detail |
