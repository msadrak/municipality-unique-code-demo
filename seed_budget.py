import pandas as pd
import sys
import os

# افزودن مسیر جاری برای شناسایی پکیج app
sys.path.append(os.getcwd())

from app.database import SessionLocal, engine
from app import models

# نام فایل اکسل بودجه (همان فایلی که نامش را budget.xlsx گذاشتیم)
EXCEL_FILE = "budget.xlsx"

def clean_str(val):
    if pd.isna(val) or str(val).strip() == "": return None
    s = str(val).strip()
    if s.endswith('.0'): s = s[:-2]
    return s

def seed_budgets():
    print(f"--- START SEEDING BUDGETS FROM {EXCEL_FILE} ---")
    
    if not os.path.exists(EXCEL_FILE):
        print(f"❌ Error: File '{EXCEL_FILE}' not found.")
        print("Please rename your budget excel file to 'budget.xlsx' and place it here.")
        return
    
    # اطمینان از وجود جداول
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. پاکسازی داده‌های قبلی
        print("Cleaning old budget data...")
        db.query(models.BudgetRef).delete()
        db.commit()

        # 2. خواندن اکسل
        print("Reading Excel file...")
        df = pd.read_excel(EXCEL_FILE)
        print(f"Loaded {len(df)} rows.")

        count = 0
        for _, row in df.iterrows():
            # نگاشت ستون‌ها بر اساس خروجی که قبلاً گرفتیم
            # ستون [1]: منطقه
            # ستون [2]: کد بودجه
            # ستون [3]: شرح ردیف
            # ستون [11]: نوع ردیف (مستمر/غیرمستمر)
            
            budget = models.BudgetRef(
                zone_raw = clean_str(row.iloc[1]),    # ستون منطقه
                budget_code = clean_str(row.iloc[2]), # کد بودجه
                title = clean_str(row.iloc[3]),       # شرح
                row_type = clean_str(row.iloc[11]),   # نوع (مستمر/...)
                deputy = clean_str(row.iloc[14])      # متولی (اختیاری)
            )
            db.add(budget)
            count += 1
            
            # نمایش پیشرفت هر 1000 رکورد
            if count % 1000 == 0:
                print(f"Processed {count} rows...")

        db.commit()
        print(f"✅ SUCCESS! Imported {count} budget lines.")

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_budgets()