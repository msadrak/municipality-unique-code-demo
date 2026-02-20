# Region 14 Quick Start Guide

**Goal:** Deploy Region 14 Civil Works with Zero Trust architecture in 5 minutes.

---

## Prerequisites Check

```bash
# 1. Ensure Excel file exists
ls data/reports/Sarmayei_Region14.xlsx

# 2. Ensure database is initialized
# (Tables should already exist from main system setup)

# 3. Verify Python environment
python --version  # Should be 3.10+
```

---

## Step 1: Preview Import (Dry Run)

**Purpose:** See what will be created WITHOUT making changes.

```bash
cd scripts
python import_region14_budget.py --dry-run
```

**Expected Output:**
```
IMPORT SUMMARY REPORT
Status: DRY RUN COMPLETED (No changes saved)

Zero Trust Components Created:
  • SubsystemActivities (1-to-1): 126
  • BudgetRows (Zero Trust): 126
  • ActivityConstraints (Locks): 126

Human Layer Components Created:
  • OrgUnits (Departments): 8
  • Admin Users (L1): 8
```

**What to check:**
- ✓ Numbers look reasonable (roughly matches Excel row count)
- ✓ No errors in output
- ✓ Unique trustees count looks correct

---

## Step 2: Execute Import

**Purpose:** Apply changes to database.

```bash
python import_region14_budget.py
```

**What happens:**
1. Creates Civil Works subsystem
2. Creates Region 14 organizational structure
3. Creates 1-to-1 activities for each budget line
4. Creates BudgetRow records (Zero Trust)
5. Creates ActivityConstraints (locks)
6. Creates OrgUnits for each trustee
7. Creates Admin users for each trustee
8. Creates legacy BudgetItem records (backward compatibility)

**Expected Duration:** 30-60 seconds (depending on Excel size)

---

## Step 3: Verify Deployment

**Purpose:** Confirm everything was created correctly.

```bash
python audit_region14.py
```

**Expected Output:**
```
REGION 14 ORGANIZATIONAL STRUCTURE
✓ Region: منطقه چهارده (ID: X, Code: 14)
✓ Departments: 8

CIVIL WORKS SUBSYSTEM
✓ Subsystem: عمران و طرح‌ها
  - Total Activities: 126

ADMIN USERS
✓ Total Admin Users: 8

BUDGET ROWS (ZERO TRUST MODEL)
✓ Total BudgetRows: 126
  Budget Summary...

INTEGRITY CHECKS
✓ Check 1: All BudgetRows have linked Activities
✓ Check 2: All Activities have Constraints
✓ Check 3: All Admin Users have Subsystem Access
✓ Check 4: All BudgetRows respect spending limits
✓ Check 5: All BudgetRow codes are unique

INTEGRITY SCORE: 5/5 checks passed
✓ ALL CHECKS PASSED - System integrity verified
```

---

## Step 4: Review Created Users

```bash
python audit_region14.py --users
```

**Output shows:**
- Username (e.g., `admin_r14_a3f8`)
- Full name
- Default password: `Tehran@1403`
- Linked department
- Subsystem access

**⚠️ SECURITY NOTE:**
All users created with default password `Tehran@1403`.
Users MUST change password on first login.

---

## Step 5: Check Specific Trustee

```bash
python audit_region14.py --trustees
```

**Shows:**
- Each department (trustee)
- Its admin user
- Number of budget lines assigned

---

## Common Commands

### View Budget Summary Only
```bash
python audit_region14.py --budget-summary
```

### Re-import (if needed)
```bash
# Currently: Manual cleanup required
# Future: Will add --force flag
```

### Check for Errors
```bash
# Look for lines starting with:
#   [ERROR] - Critical errors
#   ⚠️ - Warnings
```

---

## What Got Created?

### Database Tables Populated

| Table | Records | Purpose |
|-------|---------|---------|
| `org_units` | 9 | Region + 8 departments |
| `subsystems` | 1 | Civil Works subsystem |
| `subsystem_activities` | 126 | 1 per budget line |
| `budget_rows` | 126 | Zero Trust budget |
| `activity_constraints` | 126 | Budget locks |
| `users` | 8 | Admin L1 per dept |
| `user_subsystem_access` | 8 | RBAC grants |
| `budget_items` | 126 | Legacy (optional) |

### Total Records: ~536

---

## Verify Specific Budget Code

```python
# In Python shell or script
from app.database import SessionLocal
from app import models

db = SessionLocal()

# Find budget row
budget_code = "20501001"
br = db.query(models.BudgetRow).filter(
    models.BudgetRow.budget_coding == budget_code
).first()

print(f"Budget: {br.budget_coding}")
print(f"Approved: {br.approved_amount:,}")
print(f"Activity: {br.activity.title}")
print(f"Constraint: {br.activity.constraints[0].budget_code_pattern}")
```

---

## Architecture Verification

### Check 1-to-1 Mapping

```sql
-- Every activity should have exactly 1 constraint
SELECT 
    sa.code,
    sa.title,
    COUNT(ac.id) as constraint_count
FROM subsystem_activities sa
LEFT JOIN activity_constraints ac ON sa.id = ac.subsystem_activity_id
WHERE sa.subsystem_id = (SELECT id FROM subsystems WHERE code = 'CIVIL_WORKS')
GROUP BY sa.id
HAVING COUNT(ac.id) != 1;

-- Should return 0 rows (all activities have exactly 1 constraint)
```

### Check Budget Integrity

```sql
-- No budget should exceed limits
SELECT 
    budget_coding,
    approved_amount,
    spent_amount,
    blocked_amount,
    (spent_amount + blocked_amount) as total_committed
FROM budget_rows
WHERE spent_amount + blocked_amount > approved_amount;

-- Should return 0 rows (CheckConstraint prevents this)
```

---

## Troubleshooting

### Problem: "Excel file not found"

**Solution:**
```bash
# Check file location
ls data/reports/Sarmayei_Region14.xlsx

# If missing, ensure you have the correct file path
# Update EXCEL_FILE constant in import_region14_budget.py
```

### Problem: "Duplicate key error"

**Cause:** Re-running import without cleanup

**Solution:**
```bash
# Option 1: Don't re-import (data already exists)
# Option 2: Manual cleanup (advanced)
# Option 3: Reset database (nuclear option - loses all data)
```

### Problem: "No activities created"

**Check:**
1. Excel file has valid 'کد بودجه' column
2. Run with `--dry-run` first to see errors
3. Check for encoding issues (file should be UTF-8)

### Problem: "Constraint violations"

**Cause:** Database already has conflicting data

**Solution:**
1. Check audit report: `python audit_region14.py`
2. Look for integrity check failures
3. Manual investigation required

---

## Next Steps (After Import)

1. **Test Login**
   - Use any created admin username
   - Password: `Tehran@1403`
   - Force password change

2. **Create Test Transaction**
   - Use Region 14 budget code
   - Select Civil Works activity
   - Verify constraint validation

3. **Budget Monitoring**
   - Check remaining balances
   - Track spending
   - Export reports

4. **User Management**
   - Grant additional permissions
   - Create regular users under each admin
   - Set up approval workflows

---

## Support

**Issues?**
1. Check `audit_region14.py` output
2. Review `DEPLOYMENT_REGION14.md` for architecture details
3. Inspect database directly if needed

**Files:**
- Import: `scripts/import_region14_budget.py`
- Audit: `scripts/audit_region14.py`
- Docs: `scripts/DEPLOYMENT_REGION14.md`
- Models: `app/models.py`

---

**Last Updated:** 2026-01-26  
**Version:** 1.0 (Phase 1 Complete)
