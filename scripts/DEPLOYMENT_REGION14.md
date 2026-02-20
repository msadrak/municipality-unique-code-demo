# Region 14 Deployment Guide — Zero Trust Architecture

**Status:** Phase 1 Complete ✓  
**Last Updated:** 2026-01-26  
**Architecture:** Anti-Corruption 1-to-1 Mapping

---

## Executive Summary

This document describes the **Zero Trust deployment** for Region 14 (Civil Works). The system implements a strict 1-to-1 mapping between budget lines and activities to prevent fund shifting corruption.

### Key Achievements (Phase 1)

✅ **Atomic Data Ingestion**: Every budget line → Unique Activity → BudgetRow → Constraint  
✅ **Human Layer Automation**: Auto-generate OrgUnits and Admin Users from Excel  
✅ **Database-Level Security**: CheckConstraints enforce spending limits  
✅ **RBAC Integration**: Admin users get subsystem access automatically

---

## Architecture Philosophy: "Anti-Corruption 1-to-1 Mapping"

### The Problem We're Solving

**Traditional Approach (Insecure):**
```
Budget Line 1 ─┐
Budget Line 2 ─┼──> "Road Maintenance" Activity
Budget Line 3 ─┘
```
*Risk: Funds from Line 1 can be spent on Line 3's projects*

**Our Approach (Zero Trust):**
```
Budget Line 1 ──> Activity_1 ──> BudgetRow_1 ──> Constraint: ONLY budget_code_1
Budget Line 2 ──> Activity_2 ──> BudgetRow_2 ──> Constraint: ONLY budget_code_2
Budget Line 3 ──> Activity_3 ──> BudgetRow_3 ──> Constraint: ONLY budget_code_3
```
*Guarantee: Each budget line has its own isolated activity and cannot cross-contaminate*

### Database-Level Enforcement

```sql
-- CheckConstraint in BudgetRow table
CHECK (spent_amount + blocked_amount <= approved_amount)

-- ActivityConstraint table enforces:
activity_id=123 can ONLY use budget_code="20501001" (exact match)
```

---

## Phase 1: Data Ingestion + Human Layer

### What Was Implemented

The `import_region14_budget.py` script performs these **atomic operations**:

#### 1. Zero Trust Model Population

For each Excel row:
1. **Create SubsystemActivity** (unique per budget line)
   - Code: `CW_{budget_code}_{row_index}`
   - Title: Budget line description
   - Linked to `CIVIL_WORKS` subsystem

2. **Create BudgetRow** (replaces legacy BudgetItem)
   - Links to the activity created above
   - Stores: `approved_amount`, `blocked_amount=0`, `spent_amount=0`
   - Database constraint: `spent + blocked <= approved`

3. **Create ActivityConstraint** (lock mechanism)
   - Locks the activity to ONLY use this budget code
   - Pattern: Exact match (not a wildcard)
   - Priority: 100 (high)

#### 2. Human Layer Automation (The Innovation)

The script automatically extracts unique "Trustee" (متولی) values and creates:

1. **OrgUnit** (Department)
   - Title: Trustee name (e.g., "اداره عمران")
   - Type: DEPARTMENT
   - Parent: Region 14 OrgUnit
   - Code: Auto-generated

2. **Admin User** (Level 1)
   - Username: `admin_r14_{hash}` (consistent hash from trustee name)
   - Password: `Tehran@1403` (must change on first login)
   - Role: ADMIN_L1
   - Linked to: OrgUnit created above
   - Subsystem Access: CIVIL_WORKS (RBAC)

---

## How to Use

### Prerequisites

1. Excel file must exist at: `data/reports/Sarmayei_Region14.xlsx`
2. Database must be initialized (tables created)
3. Python environment with dependencies installed

### Step 1: Preview (Dry Run)

```bash
cd scripts
python import_region14_budget.py --dry-run
```

**What it does:**
- Reads the Excel file
- Simulates all operations
- Shows what WOULD be created
- Rolls back all changes (no DB modification)

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

### Step 2: Execute Import

```bash
python import_region14_budget.py
```

**What it does:**
- Performs all operations from dry run
- Commits changes to database
- Displays verification statistics

### Step 3: Verify Import

The script automatically verifies:
- Total activities in system
- Total BudgetRows for fiscal year 1403
- Total constraints created
- Region 14 departments
- Admin users created

---

## Data Mapping

### Excel Columns → Database Fields

| Excel Column | Database Table | Field | Notes |
|-------------|----------------|-------|-------|
| کد بودجه | BudgetRow | budget_coding | Unique identifier |
| شرح ردیف | BudgetRow | description | Activity title |
| مصوب 1403 | BudgetRow | approved_amount | Converted to integer |
| تخصیص 1403 | BudgetItem | allocated_1403 | Legacy only |
| هزینه 1403 | BudgetItem | spent_1403 | Legacy only |
| متولی | OrgUnit | title | Auto-creates dept |
| منطقه | BudgetItem | zone | For reference |
| موضوع | BudgetItem | subject | For reference |
| زیر موضوع | BudgetItem | sub_subject | For reference |

### Activity Naming Convention

```
Code: CW_20501001_42
      │   │      │
      │   │      └── Row index in Excel
      │   └── Budget code
      └── Civil Works prefix
```

### Username Generation

```python
# From trustee "اداره عمران منطقه"
# Generates: admin_r14_a3f8
#            │      │   │
#            │      │   └── MD5 hash (4 chars)
#            │      └── Region code
#            └── Role prefix
```

---

## Security Features

### 1. Database-Level Constraints

```python
# Enforced by PostgreSQL/SQLite
CHECK (spent_amount + blocked_amount <= approved_amount)
```
*Cannot be bypassed by application code*

### 2. Activity-Budget Locking

```python
ActivityConstraint(
    activity_id=123,
    budget_code_pattern="20501001",  # Exact match
    constraint_type="INCLUDE"
)
```
*Transactions using activity 123 can ONLY charge budget 20501001*

### 3. RBAC (Role-Based Access Control)

```python
UserSubsystemAccess(
    user_id=admin_id,
    subsystem_id=civil_works_id
)
```
*Deny-all by default; explicit grants only*

---

## Phase 2: Transaction Logic Migration

### Current State (Insecure)

```python
# Transaction model (line 400 in models.py)
budget_item_id = Column(Integer, ForeignKey("budget_items.id"))
```
*No CheckConstraint enforcement during spending*

### Target State (Secure)

```python
# Future: Transaction must link to BudgetRow
budget_row_id = Column(Integer, ForeignKey("budget_rows.id"))

# Budget service validates:
1. activity_id is allowed for this budget_code (ActivityConstraint)
2. remaining_balance >= requested_amount (BudgetRow)
3. Database CheckConstraint as final safety net
```

### Migration Strategy

1. **Parallel Running**: Keep both `budget_item_id` and new `budget_row_id`
2. **Gradual Cutover**: New transactions use BudgetRow
3. **Read-Only Legacy**: Old transactions still readable via BudgetItem
4. **Final Migration**: Eventually remove budget_item_id

---

## Operational Notes

### Default Credentials

**All admin users created with:**
- Password: `Tehran@1403`
- Role: ADMIN_L1
- Subsystem: CIVIL_WORKS

⚠️ **CRITICAL**: Users MUST change password on first login

### Trustees → Users Mapping

| Trustee (متولی) | Username | Full Name | OrgUnit |
|-----------------|----------|-----------|---------|
| اداره عمران | admin_r14_xxxx | Admin - اداره عمران | منطقه چهارده > اداره عمران |
| دایره خدمات شهری | admin_r14_yyyy | Admin - دایره خدمات شهری | منطقه چهارده > دایره خدمات شهری |

*(Run import to see actual list)*

---

## Troubleshooting

### Issue: "Excel file not found"

**Solution:**
```bash
# Ensure file exists at:
data/reports/Sarmayei_Region14.xlsx

# Or update EXCEL_FILE constant in script
```

### Issue: "Duplicate key error"

**Cause:** Re-running import without cleanup

**Solution:**
```bash
# Use --force flag (future enhancement)
# OR manually clean database
```

### Issue: "No activities created"

**Possible causes:**
1. Excel file has no valid rows (check 'کد بودجه' column)
2. All rows already imported (check with dry-run)
3. Database constraints violated

---

## Next Steps (Phase 2)

1. ✅ **Phase 1 Complete**: Data ingestion + Human layer
2. 🔄 **Phase 2 In Progress**: Refactor transaction logic
   - [ ] Update Transaction model to use BudgetRow
   - [ ] Implement budget validation service
   - [ ] Create ActivityConstraint validator
   - [ ] Add budget blocking/release logic
   - [ ] Update UI to show BudgetRow data
3. 📋 **Phase 3 Planned**: End-to-end testing
   - [ ] Create test scenarios
   - [ ] Verify constraint enforcement
   - [ ] Load testing with concurrent transactions

---

## Architecture Diagrams

### Zero Trust Flow

```
Excel Import
     ↓
For Each Row:
     ├─→ Create SubsystemActivity (unique)
     ├─→ Create BudgetRow (Zero Trust)
     └─→ Create ActivityConstraint (lock)

For Each Trustee:
     ├─→ Create OrgUnit (if new)
     └─→ Create Admin User (if new)
```

### Transaction Flow (Future - Phase 2)

```
User Creates Transaction
     ↓
1. Validate Activity is allowed (ActivityConstraint)
     ↓
2. Check Budget Availability (BudgetRow.remaining_balance)
     ↓
3. BLOCK amount (spent_amount + blocked_amount <= approved_amount)
     ↓
4. Workflow Approval (L1 → L2 → L3 → L4)
     ↓
5. On Final Approval: BLOCK → SPEND
     ↓
6. Database CheckConstraint validates (final safety net)
```

---

## References

- **Models**: `app/models.py` (lines 559-642: BudgetRow + Constraints)
- **Import Script**: `scripts/import_region14_budget.py`
- **Auth Utils**: `app/auth_utils.py` (password hashing)
- **Excel Source**: `data/reports/Sarmayei_Region14.xlsx`

---

**Document Version:** 2.0 (Zero Trust Implementation)  
**Author:** System Architect  
**Reviewed By:** Security Auditor
