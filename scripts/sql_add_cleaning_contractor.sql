-- SQL script to add cleaning_contractor@test.com user
-- Run this when database is available

-- First, check if user already exists
DO $$
DECLARE
    user_exists INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_exists FROM users WHERE username = 'cleaning_contractor@test.com';
    
    IF user_exists = 0 THEN
        -- Insert new contractor user
        INSERT INTO users (
            username,
            password_hash,
            full_name,
            role,
            region_name,
            is_active,
            failed_attempts,
            created_at
        ) VALUES (
            'cleaning_contractor@test.com',
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYfZvJ6U7Su', -- password123
            'Cleaning Services Contractor',
            'CONTRACTOR',
            NULL,
            TRUE,
            0,
            NOW()
        );
        RAISE NOTICE 'Created cleaning_contractor@test.com';
    ELSE
        -- Update existing user
        UPDATE users SET
            password_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYfZvJ6U7Su',
            full_name = 'Cleaning Services Contractor',
            role = 'CONTRACTOR',
            is_active = TRUE,
            failed_attempts = 0,
            locked_until = NULL
        WHERE username = 'cleaning_contractor@test.com';
        RAISE NOTICE 'Updated cleaning_contractor@test.com';
    END IF;
END $$;

-- Show the created/updated user
SELECT id, username, full_name, role FROM users WHERE username = 'cleaning_contractor@test.com';
