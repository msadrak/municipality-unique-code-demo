-- SQL script to assign contractor_id to stuck Cleaning contract
-- Run this AFTER creating the cleaning_contractor user

DO $$
DECLARE
    contractor_user_id INTEGER;
    stuck_project_id INTEGER;
    stuck_project_code VARCHAR;
BEGIN
    -- Find the cleaning contractor user
    SELECT id INTO contractor_user_id 
    FROM users 
    WHERE username = 'cleaning_contractor@test.com';
    
    IF contractor_user_id IS NULL THEN
        RAISE EXCEPTION 'cleaning_contractor@test.com not found! Run sql_add_cleaning_contractor.sql first';
    END IF;
    
    RAISE NOTICE 'Found contractor user ID: %', contractor_user_id;
    
    -- Find stuck Cleaning contract at Step 105
    SELECT cp.id, cp.project_code INTO stuck_project_id, stuck_project_code
    FROM civil_projects cp
    JOIN workflow_steps ws ON cp.current_step_id = ws.id
    WHERE cp.contract_category = 'نظافت و پذیرایی'
      AND ws.order_index = 105
    LIMIT 1;
    
    IF stuck_project_id IS NULL THEN
        RAISE NOTICE 'No stuck Cleaning contract found at Step 105';
        RAISE NOTICE 'Checking all Cleaning contracts...';
        
        -- Show all cleaning contracts
        RAISE NOTICE '--- All Cleaning Contracts ---';
        FOR stuck_project_id, stuck_project_code IN 
            SELECT cp.id, cp.project_code
            FROM civil_projects cp
            WHERE cp.contract_category = 'نظافت و پذیرایی'
        LOOP
            RAISE NOTICE 'Project ID: %, Code: %', stuck_project_id, stuck_project_code;
        END LOOP;
    ELSE
        RAISE NOTICE 'Found stuck contract: ID=%, Code=%', stuck_project_id, stuck_project_code;
        
        -- Assign contractor
        UPDATE civil_projects 
        SET contractor_id = contractor_user_id
        WHERE id = stuck_project_id;
        
        RAISE NOTICE '✓ SUCCESS: Assigned contractor_id=% to project %', contractor_user_id, stuck_project_code;
        RAISE NOTICE 'User can now log in as: cleaning_contractor@test.com / password123';
        RAISE NOTICE 'And complete Step 105 (ثبت کارکرد)';
    END IF;
END $$;

-- Show the updated project
SELECT 
    cp.id,
    cp.project_code,
    cp.title,
    cp.contract_category,
    cp.contractor_id,
    u.username as contractor_username,
    ws.order_index as current_step,
    ws.name as current_step_name
FROM civil_projects cp
LEFT JOIN users u ON cp.contractor_id = u.id
LEFT JOIN workflow_steps ws ON cp.current_step_id = ws.id
WHERE cp.contract_category = 'نظافت و پذیرایی'
ORDER BY cp.id;
