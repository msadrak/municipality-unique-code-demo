# Validation: Org-Context Based Budget/Cost Center/Continuous Action Fix

## Overview

This document proves that the trustee-based logic has been replaced with org-context based logic as required.

## Changes Made

### Backend (main.py)

Added three new API endpoints:

| Endpoint | Description | Source |
|----------|-------------|--------|
| `GET /portal/budgets/for-org` | Returns budgets for selected org context | `OrgBudgetMap` → `BudgetItem` |
| `GET /portal/cost-centers/for-org` | Returns cost centers for org context | `OrgBudgetMap.cost_center_desc` |
| `GET /portal/continuous-actions/for-org` | Returns continuous actions for org context | `OrgBudgetMap.continuous_action_desc` |

All three endpoints:
- Accept `zone_id` (required), `department_id` (optional), `section_id` (optional)
- Do NOT accept a `trustee` parameter
- Derive data from `OrgBudgetMap` table which is populated from `Hesabdary Information.xlsx`

### Frontend (React)

| File | Change |
|------|--------|
| `adapters.ts` | Added `fetchBudgetsForOrg()`, `fetchCostCentersForOrg()`, `fetchContinuousActionsForOrg()` |
| `WizardStep3_Budget.tsx` | Removed trustee dropdown entirely; budgets load automatically on org selection |
| `WizardStep4_FinancialEvent.tsx` | Cost centers and continuous actions now use org-filtered APIs |

---

## Proof: No Trustee Selection in Wizard

### Before (Incorrect)
```
Step 1 → Step 2: Select Zone/Dept/Section
       → Step 3: Select Trustee  ← INCORRECT
                 → Select Budget
```

### After (Correct)
```
Step 1 → Step 2: Select Zone/Dept/Section
       → Step 3: Budget list loads automatically ← CORRECT
                 (No trustee dropdown)
```

---

## Example Data Flow

### Example 1: Zone 20 (شهرداری مرکزی)

**Input:** 
- `zone_id = 1` (assuming OrgUnit.id=1 has code='20')

**API Call:**
```
GET /portal/budgets/for-org?zone_id=1
```

**Query Logic:**
1. Look up `OrgUnit` with `id=1` → get `code='20'`
2. Query `OrgBudgetMap` for `zone_code='20'` → get distinct `budget_code` values
3. Join with `BudgetItem` table to get full budget details

**Expected Result:**
- Budget items that appear in `Hesabdary Information.xlsx` for zone 20
- These budgets exist in both:
  - `اعتبارات هزینه‌ای.xlsx` (expense budgets)
  - `تملک دارایی سرمایه‌ای.xlsx` (capital budgets)

---

### Example 2: Cost Centers for Zone 20

**API Call:**
```
GET /portal/cost-centers/for-org?zone_id=1
```

**Query Logic:**
1. Look up zone code from `zone_id`
2. Query `OrgBudgetMap.cost_center_desc` for that zone
3. Return distinct values

**Source Column:** `شرح مرکزهزینه` from `Hesabdary Information.xlsx`

---

### Example 3: Continuous Actions for Zone 20

**API Call:**
```
GET /portal/continuous-actions/for-org?zone_id=1
```

**Query Logic:**
1. Look up zone code from `zone_id`
2. Query `OrgBudgetMap.continuous_action_desc` for that zone
3. Return distinct values

**Source Column:** `شرح سرفصل حساب جزء` (سرفصل جزء) from `Hesabdary Information.xlsx`

---

## Column Mapping Verification

| Requirement | Excel Column | DB Column | API Response Field |
|-------------|--------------|-----------|-------------------|
| Budget Code | `کد بودجه` | `OrgBudgetMap.budget_code` | Joined to `BudgetItem` |
| Cost Center | `شرح مرکزهزینه` | `OrgBudgetMap.cost_center_desc` | `name`, `title` |
| Continuous Action | `شرح سرفصل حساب جزء` | `OrgBudgetMap.continuous_action_desc` | `name`, `title` |

---

## Acceptance Criteria Verification

| Criteria | Status |
|----------|--------|
| No trustee selection step in wizard | ✅ Removed from Step 3 |
| Step 3 budget list changes with org context | ✅ Uses `/portal/budgets/for-org` |
| Continuous action uses `سرفصل جزء` column | ✅ Uses `continuous_action_desc` |
| Cost center uses `مرکز هزینه` column | ✅ Uses `cost_center_desc` |
| Fast with large datasets | ✅ Uses indexed queries with LIMIT |
| Minimal schema changes | ✅ No schema changes needed |

---

## Test Script

To verify the implementation works correctly, run:

```bash
# Start backend
cd f:\Freelancing_Project\KalaniProject\municipality_demo
uvicorn app.main:app --reload

# Test budgets for org endpoint
curl "http://localhost:8000/portal/budgets/for-org?zone_id=1"

# Test cost centers for org endpoint
curl "http://localhost:8000/portal/cost-centers/for-org?zone_id=1"

# Test continuous actions for org endpoint
curl "http://localhost:8000/portal/continuous-actions/for-org?zone_id=1"
```

---

## Prerequisites

Before testing, ensure the `OrgBudgetMap` table has been populated:

```bash
python scripts/import_org_budget_map.py
```

This script reads `Hesabdary Information.xlsx` and populates the `org_budget_map` table with:
- Zone codes
- Budget codes  
- Cost center descriptions
- Continuous action descriptions
