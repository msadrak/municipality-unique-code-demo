"""
Migration script: Add Service Catalog & Constraint Engine tables/columns

This script adds:
1. New columns to subsystem_activities table:
   - frequency (ENUM: daily, monthly, yearly)
   - requires_file_upload (BOOLEAN)
   - external_service_url (VARCHAR)
   
2. New table: activity_constraints
   - Links activities to allowed budget/cost center patterns

Safe for re-runs (IF NOT EXISTS pattern for table, safe column additions)

Usage:
    python migrate_activity_constraints.py
"""

import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from app.database import engine
from app.models import Base

def run_migration():
    print("=" * 60)
    print("MIGRATION: Service Catalog & Constraint Engine")
    print("=" * 60)
    
    with engine.connect() as conn:
        # 1. Create ENUM type for frequency (PostgreSQL)
        print("\n1. Creating activityfrequency ENUM type...")
        try:
            conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE activityfrequency AS ENUM ('daily', 'monthly', 'yearly');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            conn.commit()
            print("   ✓ activityfrequency ENUM created (or exists)")
        except Exception as e:
            print(f"   ⚠ ENUM: {e}")
        
        # 2. Add columns to subsystem_activities
        print("\n2. Adding columns to subsystem_activities...")
        
        columns = [
            ("frequency", "activityfrequency DEFAULT 'monthly'"),
            ("requires_file_upload", "BOOLEAN DEFAULT FALSE"),
            ("external_service_url", "VARCHAR"),
        ]
        
        for col_name, col_type in columns:
            try:
                conn.execute(text(f"""
                    ALTER TABLE subsystem_activities 
                    ADD COLUMN IF NOT EXISTS {col_name} {col_type}
                """))
                conn.commit()
                print(f"   ✓ {col_name} added")
            except Exception as e:
                print(f"   ⚠ {col_name}: {e}")
        
        # 3. Create activity_constraints table
        print("\n3. Creating activity_constraints table...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS activity_constraints (
                    id SERIAL PRIMARY KEY,
                    subsystem_activity_id INTEGER NOT NULL REFERENCES subsystem_activities(id),
                    budget_code_pattern VARCHAR,
                    allowed_budget_types JSON,
                    cost_center_pattern VARCHAR,
                    allowed_cost_centers JSON,
                    constraint_type VARCHAR DEFAULT 'INCLUDE',
                    priority INTEGER DEFAULT 0,
                    description VARCHAR,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """))
            conn.commit()
            print("   ✓ activity_constraints table created (or exists)")
        except Exception as e:
            print(f"   ⚠ Table: {e}")
        
        # 4. Create index on subsystem_activity_id
        print("\n4. Creating indexes...")
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_activity_constraints_activity_id 
                ON activity_constraints (subsystem_activity_id)
            """))
            conn.commit()
            print("   ✓ Index on subsystem_activity_id created")
        except Exception as e:
            print(f"   ⚠ Index: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Migration complete!")
    print("=" * 60)

if __name__ == "__main__":
    run_migration()
