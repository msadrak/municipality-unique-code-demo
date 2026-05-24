# Contractor Assignment Fix - Implementation Guide

## Problem Summary
The Volume Contracts workflow was deadlocked at Step 105 (ثبت کارکرد) because:
1. Contracts were created without assigning a specific `contractor_id`
2. Step 105 requires the `CONTRACTOR` role, but no contractor was linked to the project
3. The existing contractor account was coupled to the Security module

## Solution Implemented

### 1. Dynamic Contractor Assignment (✓ Completed)
**Files Modified:**
- `app/routers/civil.py`: Added `contractor_id` field to `CivilProjectCreateRequest`
- `app/routers/civil.py`: Updated `_create_volume_contract_project()` to save `contractor_id` to the project

**Impact:** HR_ADMIN can now select a specific CONTRACTOR user when creating a new volume contract at Step 101.

### 2. Generic Contractor Seed (✓ Completed)
**Files Modified:**
- `scripts/seed_users.py`: Added `cleaning_contractor@test.com` user

**New User:**
- Username: `cleaning_contractor@test.com`
- Password: `password123`
- Role: `CONTRACTOR`
- Purpose: Universal contractor for all 11 Volume Contract categories

### 3. Data Isolation (✓ Already Correct)
**File:** `app/routers/volume_contracts.py`

The GET projects endpoint already filters correctly:
```python
if user.role == "CONTRACTOR":
    query = query.filter(CivilProject.contractor_id == user.id)
```

### 4. Rescue Scripts (✓ Created)
**Files Created:**
- `scripts/rescue_stuck_contract.py`: Python script to fix stuck contracts
- `scripts/sql_add_cleaning_contractor.sql`: SQL script to create contractor user
- `scripts/sql_rescue_stuck_contract.sql`: SQL script to assign contractor to stuck project

## How to Apply the Fix

### Option A: Using Python Scripts (Recommended)

**Prerequisites:**
- PostgreSQL database must be running
- Python environment with dependencies installed

**Steps:**
```bash
# 1. Start the database (if using Docker)
docker compose up -d

# 2. Create the cleaning contractor user
python scripts/seed_users.py

# 3. Fix the stuck contract
python scripts/rescue_stuck_contract.py
```

### Option B: Using SQL Scripts (If Python environment unavailable)

**Prerequisites:**
- PostgreSQL database must be running
- Access to `psql` or any PostgreSQL client

**Steps:**
```bash
# 1. Start the database (if using Docker)
docker compose up -d

# 2. Create the cleaning contractor user
psql -U postgres -d municipality_demo -f scripts/sql_add_cleaning_contractor.sql

# 3. Fix the stuck contract
psql -U postgres -d municipality_demo -f scripts/sql_rescue_stuck_contract.sql
```

### Option C: Manual SQL (Direct database access)

```sql
-- 1. Create contractor user
INSERT INTO users (username, password_hash, full_name, role, is_active, failed_attempts, created_at)
VALUES (
    'cleaning_contractor@test.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYfZvJ6U7Su',
    'Cleaning Services Contractor',
    'CONTRACTOR',
    TRUE,
    0,
    NOW()
);

-- 2. Get the contractor user ID
SELECT id FROM users WHERE username = 'cleaning_contractor@test.com';
-- Note the ID (e.g., 123)

-- 3. Find and fix stuck contract
UPDATE civil_projects 
SET contractor_id = 123  -- Replace with actual ID from step 2
WHERE id IN (
    SELECT cp.id 
    FROM civil_projects cp
    JOIN workflow_steps ws ON cp.current_step_id = ws.id
    WHERE cp.contract_category = 'نظافت و پذیرایی'
      AND ws.order_index = 105
);
```

## Verification

After applying the fix:

1. **Login as contractor:**
   - Username: `cleaning_contractor@test.com`
   - Password: `password123`

2. **Check the contract list:**
   - Navigate to Volume Contracts → Cleaning category
   - You should see the stuck contract

3. **Complete Step 105:**
   - Open the contract
   - Fill in the required work performance data (ثبت کارکرد)
   - Submit to advance to Step 106

## Future Contract Creation

When creating new Volume Contracts at Step 101:

1. HR_ADMIN fills in the contract details
2. **NEW:** Select a contractor from the dropdown (contractor_id field)
3. Submit the contract
4. The selected contractor will automatically have access to complete their steps

## Database Schema Reference

**Table:** `civil_projects`
- `contractor_id` (INTEGER, nullable): Foreign key to `users.id`
- Links a project to a specific CONTRACTOR user

**Table:** `users`
- `role` (VARCHAR): User role, e.g., 'CONTRACTOR'
- Contractors with role='CONTRACTOR' can access projects where `contractor_id = user.id`

## Troubleshooting

### Database not running
```bash
# Check if Docker containers are running
docker ps

# Start database
docker compose up -d

# Check logs
docker compose logs db
```

### User already exists
The scripts are idempotent - they will update the existing user if it already exists.

### No stuck contract found
Check all cleaning contracts:
```sql
SELECT cp.id, cp.project_code, cp.contractor_id, ws.order_index, ws.name
FROM civil_projects cp
LEFT JOIN workflow_steps ws ON cp.current_step_id = ws.id
WHERE cp.contract_category = 'نظافت و پذیرایی';
```

### Contractor can't see the contract
Verify the contractor_id is set:
```sql
SELECT id, project_code, contractor_id 
FROM civil_projects 
WHERE contract_category = 'نظافت و پذیرایی';
```

If `contractor_id` is NULL, run the rescue script again.

## Files Modified/Created

### Modified Files:
1. `app/routers/civil.py` - Added contractor_id to schema and project creation
2. `scripts/seed_users.py` - Added cleaning_contractor@test.com

### New Files:
1. `scripts/rescue_stuck_contract.py` - Python rescue script
2. `scripts/sql_add_cleaning_contractor.sql` - SQL to create contractor
3. `scripts/sql_rescue_stuck_contract.sql` - SQL to fix stuck contract
4. `scripts/CONTRACTOR_ASSIGNMENT_FIX.md` - This documentation

## Contact

If you encounter issues, check:
1. Database connection in `.env` file
2. PostgreSQL service is running
3. User has correct role ('CONTRACTOR')
4. Project has contractor_id set
