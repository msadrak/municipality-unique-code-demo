import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found in .env")
    exit(1)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE regional_attendance_sheets ADD COLUMN declared_total_amount NUMERIC(18, 2)"))
        conn.commit()
        print("Column declared_total_amount added successfully to regional_attendance_sheets table.")
    except Exception as e:
        if "already exists" in str(e):
            print("Column already exists.")
        else:
            print(f"Error: {e}")
