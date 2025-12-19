"""
Migration script for Architecture 2.0
Adds new columns to users and transactions tables
Creates workflow_logs table
"""
from sqlalchemy import text
from app.database import engine

def run_migration():
    with engine.connect() as conn:
        # Add columns to users table
        print("Adding columns to users table...")
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS admin_level INTEGER"))
            conn.commit()
            print("  - admin_level added")
        except Exception as e:
            print(f"  - admin_level: {e}")
        
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS managed_subsystem_ids JSON"))
            conn.commit()
            print("  - managed_subsystem_ids added")
        except Exception as e:
            print(f"  - managed_subsystem_ids: {e}")
        
        # Create workflow_logs table
        print("Creating workflow_logs table...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS workflow_logs (
                    id SERIAL PRIMARY KEY,
                    transaction_id INTEGER NOT NULL REFERENCES transactions(id),
                    admin_id INTEGER NOT NULL REFERENCES users(id),
                    admin_level INTEGER NOT NULL,
                    action VARCHAR NOT NULL,
                    comment VARCHAR,
                    previous_status VARCHAR NOT NULL,
                    new_status VARCHAR NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            print("  - workflow_logs table created")
        except Exception as e:
            print(f"  - workflow_logs: {e}")
        
        print("Migration complete!")

if __name__ == "__main__":
    run_migration()
