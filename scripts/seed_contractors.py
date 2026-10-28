import os
import sys

# Add the current directory to sys.path so we can import 'app'
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models import Contractor
from datetime import datetime

def seed():
    db = SessionLocal()
    try:
        count = db.query(Contractor).count()
        if count == 0:
            contractors = [
                Contractor(
                    national_id="10103456789",
                    company_name="شرکت مهندسی سازه گستر اصفهان",
                    ceo_name="مهندس علوی",
                    registration_number="12345",
                    source_system="MANUAL",
                    is_verified=True
                ),
                Contractor(
                    national_id="14005678901",
                    company_name="پیمانکاری راه و ساختمان کویر",
                    ceo_name="دکتر رضایی",
                    registration_number="67890",
                    source_system="MANUAL",
                    is_verified=True
                ),
                Contractor(
                    national_id="10260451234",
                    company_name="فنی مهندسی ابنیه ماندگار",
                    ceo_name="خانم مهندس پارسا",
                    registration_number="11223",
                    source_system="MANUAL",
                    is_verified=True
                )
            ]
            db.add_all(contractors)
            db.commit()
            print("Successfully seeded 3 test contractors.")
        else:
            print(f"Database already contains {count} contractors.")
    except Exception as e:
        print(f"Error seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
