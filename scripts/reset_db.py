# scripts/reset_db.py
"""
Database Reset Script
=====================
This script drops all existing tables and recreates them with the current schema.

⚠️ WARNING: This will DELETE ALL DATA in the database!
Only use this in development environment.
"""

from app.database import engine, Base
from app.models import * # Import all models to ensure they are registered

def reset_database():
    print("=" * 60)
    print("⚠️  DATABASE RESET SCRIPT")
    print("=" * 60)
    print()
    
    print("🗑️ Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("✅ All tables dropped.")
    print()
    
    print("🏗️ Creating new tables (Schema V2 - Budget Control)...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized with new Budget & Activity tables.")
    print()
    
    # List created tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"📋 Created {len(tables)} tables:")
    for i, table in enumerate(sorted(tables), 1):
        print(f"   {i:2}. {table}")
    
    print()
    print("=" * 60)
    print("✅ Database reset complete!")
    print("=" * 60)


if __name__ == "__main__":
    reset_database()
