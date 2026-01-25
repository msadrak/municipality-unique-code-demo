import pandas as pd
import sys

SOURCE_FILE = r"f:\Freelancing_Project\KalaniProject\municipality_demo\data\reports\اطلاعات حسابداری1404.xlsx"
OUTPUT_FILE = r"f:\Freelancing_Project\KalaniProject\municipality_demo\data\reports\Region6_1404.xlsx"
SHEET_NAME = "سایر مناطق"
TARGET_REGION = "شهرداری منطقه شش"

def normalize_text(text):
    if pd.isna(text): return ""
    text = str(text)
    # Standardize Ye and Ke
    text = text.replace('ي', 'ی').replace('ك', 'ک')
    # Standardize numbers
    text = text.replace('1', '۱').replace('2', '۲').replace('3', '۳').replace('4', '۴').replace('5', '۵').replace('6', '۶').replace('7', '۷').replace('8', '۸').replace('9', '۹').replace('0', '۰')
    return text.strip()

def main():
    print(f"Loading {SOURCE_FILE}...")
    try:
        # Load all sheets to check for existence
        xls = pd.ExcelFile(SOURCE_FILE)
        if SHEET_NAME not in xls.sheet_names:
            print(f"Error: Sheet '{SHEET_NAME}' not found. Available sheets: {xls.sheet_names}")
            # Try to find a close match
            for s in xls.sheet_names:
                if "سایر" in s and "مناطق" in s:
                    print(f"Did you mean '{s}'?")
            return

        df = pd.read_excel(xls, sheet_name=SHEET_NAME)
        print(f"Loaded sheet '{SHEET_NAME}' with {len(df)} rows.")

        # Identify 'منطقه' column
        # User said it is column B (index 1), but let's check name 'منطقه'
        col_name = 'منطقه'
        if col_name not in df.columns:
            # Check column B
            if len(df.columns) > 1:
                col_name = df.columns[1]
                print(f"Column 'منطقه' not found by name. Using column index 1: '{col_name}'")
            else:
                print("Error: DataFrame has fewer than 2 columns.")
                return

        # Filter
        # Create a normalized temporary column for filtering
        df['norm_region'] = df[col_name].apply(normalize_text)
        target_norm = normalize_text(TARGET_REGION)

        # Try exact match first
        filtered_df = df[df['norm_region'] == target_norm]
        
        # If no matches, maybe it uses digits? 'شهرداری منطقه 6'
        if len(filtered_df) == 0:
            print(f"No rows found matches '{target_norm}'. Checking for numeric variants...")
            target_variant = normalize_text("شهرداری منطقه 6")
            filtered_df = df[df['norm_region'] == target_variant]
        
        if len(filtered_df) == 0:
            print(f"Warning: No data found for region '{TARGET_REGION}'.")
            print("Available regions in this sheet:")
            print(df[col_name].unique())
        else:
            # Drop temp column
            final_df = filtered_df.drop(columns=['norm_region'])
            
            # Export
            print(f"Found {len(final_df)} rows. Saving to {OUTPUT_FILE}...")
            final_df.to_excel(OUTPUT_FILE, index=False)
            print("Done.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
