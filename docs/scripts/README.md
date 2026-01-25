# Scripts Documentation

## Overview

Scripts are organized in the `scripts/` directory with old versions archived in `scripts/_archive/`.

## Active Scripts

### Seeders

| Script | Purpose |
|--------|---------|
| `seed_admins.py` | Create 5-level admin users |
| `seed_budget_v4.py` | Seed budget data from Excel |
| `seed_budget_real.py` | Seed real budget data |
| `seed_full_system.py` | Full system seeding orchestrator |

### Config Generators

| Script | Purpose |
|--------|---------|
| `generate_v8_strict_review.py` | Generate config_master.json |
| `export_config_to_excel.py` | Export config to Excel |
| `export_final_clean_report.py` | Final report generation |

### User Management

| Script | Purpose |
|--------|---------|
| `create_users.py` | Create regular users |
| `create_finance_user.py` | Create finance users |
| `add_user_access.py` | Add subsystem access |

### Analysis & Diagnostics

| Script | Purpose |
|--------|---------|
| `audit_db_status.py` | Database status audit |
| `audit_admins.py` | Admin users audit |
| `diagnostic_budget.py` | Budget diagnostics |
| `diagnose_treasury.py` | Treasury diagnostics |

### Database

| Script | Purpose |
|--------|---------|
| `reset_db.py` | Reset database |
| `test_api.py` | API testing |
| `test_login_cli.py` | Login testing |

## Running Scripts

```bash
cd municipality_demo
.venv\Scripts\activate
python scripts/{script_name}.py
```

## Archived Scripts

Old versions are in `scripts/_archive/`:
- generate_config_v3-v7
- seed_budget_v2-v3
- export_v5_report
