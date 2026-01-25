import pandas as pd
import sys
from pathlib import Path

SOURCE_FILE = Path(r"f:\Freelancing_Project\KalaniProject\municipality_demo\data\reports\اطلاعات حسابداری1404.xlsx")
OUTPUT_FILE = Path(r"f:\Freelancing_Project\KalaniProject\municipality_demo\data\reports\Central_1404.xlsx")
SHEET_NAME = "مرکزی"

def main():
    print(f"Loading {SOURCE_FILE}...")
    if not SOURCE_FILE.exists():
        print(f"Error: File not found at {SOURCE_FILE}")
        return

    try:
        # Check available sheets first
        xls = pd.ExcelFile(SOURCE_FILE)
        if SHEET_NAME not in xls.sheet_names:
            print(f"Error: Sheet '{SHEET_NAME}' not found.")
            print(f"Available sheets: {xls.sheet_names}")
            # Try to find close match
            possible = [s for s in xls.sheet_names if "مرکز" in s]
            if possible:
                print(f"Did you mean one of these? {possible}")
            return

        print(f"Reading sheet '{SHEET_NAME}'...")
        df = pd.read_excel(xls, sheet_name=SHEET_NAME)
        
        print(f"Loaded {len(df):,} rows.")
        
        print(f"Saving to {OUTPUT_FILE}...")
        df.to_excel(OUTPUT_FILE, index=False)
        print("Done.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
