import pandas as pd
import sys
import os

# Add root path
sys.path.append(os.getcwd())

from app.database import SessionLocal, engine
from app import models

# Excel File Config
EXCEL_FILE = "cost_centers.xlsx"

def seed_continuous():
    print(f"--- START SEEDING: CONTINUOUS ACTIONS ---")
    
    if not os.path.exists(EXCEL_FILE):
        print(f"❌ Error: File '{EXCEL_FILE}' not found.")
        return

    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 👇👇👇 FIX: First clear the dependent table (SpecialAction) 👇👇👇
        print("1. Clearing dependent Special Actions (Required to update references)...")
        db.query(models.SpecialAction).delete()
        
        # Then clear the target table
        print("2. Cleaning old Continuous Actions...")
        db.query(models.ContinuousAction).delete()
        
        db.commit()
        print("   -> Old data cleared successfully.")

        # --- Reading Excel Logic ---
        df = pd.read_excel(EXCEL_FILE, header=None)
        
        # Find target column
        target_col_idx = -1
        for r_idx in range(min(5, len(df))):
            row = df.iloc[r_idx]
            for c_idx, val in enumerate(row):
                if "اقدامات مستمر" in str(val):
                    target_col_idx = c_idx
                    print(f"✅ Column 'اقدامات مستمر' found at index {c_idx} (Row {r_idx})")
                    break
            if target_col_idx != -1: break
            
        if target_col_idx == -1:
            print("❌ Column 'اقدامات مستمر' not found!")
            return

        # Extract Data
        count = 0
        added = set()
        
        for i in range(r_idx + 1, len(df)):
            val = str(df.iloc[i, target_col_idx]).strip()
            
            if val and val.lower() != 'nan' and val not in added:
                code = f"CA-{count+1:03d}"
                db.add(models.ContinuousAction(code=code, title=val))
                added.add(val)
                count += 1

        db.commit()
        print(f"✅ SUCCESS! Imported {count} continuous actions.")

    except Exception as e:
        db.rollback()
        print(f"❌ CRITICAL ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_continuous()