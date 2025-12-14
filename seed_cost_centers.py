import pandas as pd
import sys
import os

# Add root path
sys.path.append(os.getcwd())

from app.database import SessionLocal, engine
from app import models

# Config: مطمئن شوید نام فایل اکسل همین است
EXCEL_FILE = "cost_centers.xlsx"

def clean_str(val):
    if pd.isna(val) or str(val).strip() == "" or str(val).lower() == 'nan': return None
    s = str(val).strip()
    if s.endswith('.0'): s = s[:-2]
    return s

def is_valid_code(val):
    """Check if value looks like a cost center code (numeric, >2 digits)"""
    s = str(val).strip()
    if s.endswith('.0'): s = s[:-2]
    return s.isdigit() and len(s) > 2

def seed_cost_centers():
    print(f"--- START SMART SEEDING: COST CENTERS (ALL SHEETS) ---")
    
    if not os.path.exists(EXCEL_FILE):
        print(f"❌ Error: File '{EXCEL_FILE}' not found.")
        return

    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Clear old data
        db.query(models.CostCenterRef).delete()
        db.commit()
        print("Cleaning old data... Done.")

        # Read ALL sheets without header
        print("Reading Excel file...")
        xls = pd.read_excel(EXCEL_FILE, sheet_name=None, header=None)
        
        total_imported = 0
        
        for sheet_name, df in xls.items():
            # print(f"Scanning {sheet_name}...") # Uncomment for debug
            sheet_count = 0
            
            for idx, row in df.iterrows():
                code_found = None
                title_found = None
                
                # Scan first 5 columns for a Code
                for i in range(min(6, len(row))):
                    val = row.iloc[i]
                    if is_valid_code(val):
                        code_found = clean_str(val)
                        
                        # Look for title in next 2 columns
                        for j in range(i + 1, min(i + 3, len(row))):
                            possible_title = clean_str(row.iloc[j])
                            if possible_title and not possible_title.isdigit():
                                title_found = possible_title
                                break
                        break 
                
                if code_found and title_found:
                    # Avoid duplicates
                    exists = db.query(models.CostCenterRef).filter_by(code=code_found).first()
                    if not exists:
                        db.add(models.CostCenterRef(code=code_found, title=title_found))
                        sheet_count += 1
                        total_imported += 1
            
            if sheet_count > 0:
                print(f"   -> Sheet '{sheet_name}': Extracted {sheet_count} records.")

        db.commit()
        print("-" * 30)
        print(f"✅ FINAL SUCCESS! Total Imported: {total_imported} cost centers.")
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_cost_centers()