"""
Fix PostgreSQL enum: recreate with lowercase values to match existing data.
The data has 'monthly' but the enum was created with 'DAILY', 'MONTHLY', 'YEARLY'.
Solution: Drop and recreate enum with lowercase values, then alter column.
"""
from sqlalchemy import text
from app.database import engine

def fix_enum():
    with engine.connect() as conn:
        # Check current data
        result = conn.execute(text("SELECT frequency FROM subsystem_activities LIMIT 1"))
        row = result.fetchone()
        print(f"Current frequency value in data: {row[0] if row else 'No data'}")
        
        # PostgreSQL approach: use ALTER TYPE to add lowercase values, then remove uppercase
        # Or simpler: drop column, drop enum, recreate
        print("\nFixing enum type...")
        
        # Step 1: Set all frequencies to NULL temporarily
        conn.execute(text("ALTER TABLE subsystem_activities ALTER COLUMN frequency DROP DEFAULT"))
        conn.execute(text("ALTER TABLE subsystem_activities ALTER COLUMN frequency TYPE VARCHAR(20)"))
        
        # Step 2: Drop the old enum type
        conn.execute(text("DROP TYPE IF EXISTS activityfrequency"))
        
        # Step 3: Recreate enum with correct lowercase values
        conn.execute(text("CREATE TYPE activityfrequency AS ENUM ('DAILY', 'MONTHLY', 'YEARLY')"))
        
        # Step 4: Update existing lowercase values to uppercase
        conn.execute(text("UPDATE subsystem_activities SET frequency = UPPER(frequency) WHERE frequency IS NOT NULL"))
        
        # Step 5: Change column back to enum type
        conn.execute(text("ALTER TABLE subsystem_activities ALTER COLUMN frequency TYPE activityfrequency USING frequency::activityfrequency"))
        conn.execute(text("ALTER TABLE subsystem_activities ALTER COLUMN frequency SET DEFAULT 'MONTHLY'"))
        
        conn.commit()
        print("✅ Enum fixed successfully!")
        
        # Verify
        result = conn.execute(text("SELECT frequency FROM subsystem_activities LIMIT 3"))
        print("\nVerification - first 3 rows:")
        for row in result:
            print(f"  {row[0]}")

if __name__ == "__main__":
    fix_enum()
