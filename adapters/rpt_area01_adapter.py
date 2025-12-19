import pandas as pd
import requests
import hashlib
import os

# ---------------- CONFIGURATION ----------------
EXCEL_PATH = r"F:\Freelancing_Project\KalaniProject\municipality_demo\Rpt_area01.xlsx"
BUDGET_FILE = r"F:\Freelancing_Project\KalaniProject\municipality_demo\سرفصل های مالی-همراه بودجه.xlsx"
BUDGET_SHEET = "اعبارات جزء" 

API_URL = "http://127.0.0.1:8000/external/RPT_AREA01/special-actions"
SEND_TO_API = True

# Constants
ORG_CODE = "01-01-01-01"
CONT_ACTION = "CA001"
ACT_TYPE = "ACT017"

# ---------------- HELPERS ----------------
def clean_str(val):
    if pd.isna(val) or str(val).strip() == "" or str(val).lower() == 'nan': return ""
    s = str(val).strip()
    if s.endswith(".0"): s = s[:-2]
    return s

def clean_and_pad(val, length):
    s = clean_str(val)
    if not s: return "0" * length
    return s.zfill(length)

def normalize_date(val):
    s = clean_str(val)
    if not s or len(s) < 6: return "00000000"
    s = s.split(" ")[0].replace("/", "").replace("-", "")
    return s

def generate_stable_hash(text):
    if not text: return "000000"
    hash_obj = hashlib.md5(text.encode('utf-8'))
    num_val = int(hash_obj.hexdigest(), 16)
    return str(num_val % 1000000).zfill(6)

# ---------------- MAIN LOGIC ----------------
def main():
    print("=== STARTING ADAPTER: FINAL FIX ===")
    
    # 1. Load Budget
    budget_map = {}
    if os.path.exists(BUDGET_FILE):
        try:
            df_b = pd.read_excel(BUDGET_FILE, sheet_name=BUDGET_SHEET)
            for _, row in df_b.iterrows():
                code = str(row.iloc[0]).replace('-', '').replace('.0', '').strip()
                name = str(row.iloc[3]).strip()
                budget_map[code] = name
            print(f"✅ Budget Loaded: {len(budget_map)} items.")
        except Exception as e:
            print(f"❌ Budget Error: {e}")

    # 2. Load Performance Excel & FIX EMPTY CELLS
    try:
        print(f"Loading Performance: {EXCEL_PATH}...")
        df = pd.read_excel(EXCEL_PATH, sheet_name=0)
        
        # 👇👇👇 FIX: پر کردن سلول‌های خالی با مقدار بالا 👇👇👇
        df = df.ffill()
        
        print(f"✅ Excel Loaded & Filled. Rows: {len(df)}")
    except Exception as e:
        print(f"❌ Excel Error: {e}")
        return

    # 3. Process Row-by-Row (Using Indexes based on your check_columns output)
    processed_rows = []
    
    for idx, row in df.iterrows():
        # A=0, B=1, C=2 ... K=10 ... P=15, Q=16
        if pd.isna(row.iloc[0]) and pd.isna(row.iloc[3]): continue

        r_area = clean_str(row.iloc[0])
        r_doc_no = clean_str(row.iloc[1])
        r_date = normalize_date(row.iloc[2]) # Column C
        
        # Account Codes (D, F, H, J -> 3, 5, 7, 9)
        r_kol = clean_and_pad(row.iloc[3], 3)
        r_moin = clean_and_pad(row.iloc[5], 3)
        r_taf = clean_and_pad(row.iloc[7], 5)
        r_joz = clean_and_pad(row.iloc[9], 5)
        
        # Name: Column K (Index 10)
        r_name = clean_str(row.iloc[10]) 
        
        # Rad: Column P (Index 15 - RadJNam)
        r_rad = clean_str(row.iloc[15])
        
        # Desc: Column Q (Index 16 - DocDesc) 
        # Note: In some versions it might be P(16), check index carefully.
        # Based on your list: 15 is RadJNam, 16 is DocDesc
        r_desc = clean_str(row.iloc[16]) 
        
        # Amounts: Last two columns
        try:
            r_debit = float(row.iloc[-2]) if pd.notna(row.iloc[-2]) else 0
            r_credit = float(row.iloc[-1]) if pd.notna(row.iloc[-1]) else 0
        except:
            r_debit, r_credit = 0, 0

        budget_code = f"{r_kol}{r_moin}{r_taf}{r_joz}"
        
        # Fallback if name is still empty (should not happen with ffill)
        final_name = r_name if r_name else "نامشخص"

        processed_rows.append({
            'area': r_area,
            'budget_code': budget_code,
            'date': r_date,
            'name': final_name,
            'doc_no': r_doc_no,
            'desc': r_desc,
            'rad': r_rad,
            'debit': r_debit,
            'credit': r_credit,
            'account_display': f"{r_kol}-{r_moin}-{r_taf}-{r_joz}"
        })

    # Grouping
    clean_df = pd.DataFrame(processed_rows)
    clean_df['hash_id'] = clean_df['name'].apply(generate_stable_hash)
    
    clean_df['group_key'] = clean_df.apply(
        lambda r: f"{r['area']}-{r['budget_code']}-{r['date']}-{r['hash_id']}", 
        axis=1
    )

    grouped = clean_df.groupby('group_key')
    print(f"Unique Actions: {len(grouped)}")

    actions_to_send = []

    for key, group_df in grouped:
        first = group_df.iloc[0]
        net_amount = group_df['debit'].sum() - group_df['credit'].sum()
        
        # Unique values for summary
        doc_summary = " | ".join(group_df['doc_no'].unique())
        budget_title = budget_map.get(first['budget_code'], "---")
        
        raw_rows_list = []
        for _, r in group_df.iterrows():
            raw_rows_list.append({
                "doc_no": r['doc_no'],
                "date": r['date'],
                "desc": r['desc'],
                "rad": r['rad'],
                "debit": f"{r['debit']:,.0f}",
                "credit": f"{r['credit']:,.0f}",
                "account_parts": r['account_display']
            })

        payload = {
            "org_unit_full_code": ORG_CODE,
            "continuous_action_code": CONT_ACTION,
            "action_type_code": ACT_TYPE,
            "financial_event_title": first['name'],
            "amount": float(net_amount),
            "local_record_id": key,
            "description": f"شرح سیستمی: {len(raw_rows_list)} ردیف",
            "action_date": None,
            "details": {
                "doc_no": doc_summary,
                "rad_name": first['rad'],
                "budget_row": budget_title,
                "budget_code": first['budget_code'],
                "raw_date": str(first['date']),
                "raw_rows": raw_rows_list
            }
        }
        actions_to_send.append(payload)

    # Sending
    if SEND_TO_API:
        print(f"\nSending {len(actions_to_send)} records...")
        session = requests.Session()
        success = 0
        for idx, action in enumerate(actions_to_send):
            try:
                resp = session.post(API_URL, json=action)
                if resp.status_code == 200:
                    success += 1
                    if (idx+1) % 500 == 0: print(f"Sent {idx+1}...")
            except: pass
        print(f"Done. Success: {success}")

if __name__ == "__main__":
    main()