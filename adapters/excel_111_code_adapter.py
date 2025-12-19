import pandas as pd
import requests
from pathlib import Path
import json

# ---------------- تنظیمات عمومی ----------------

API_BASE_URL = "http://127.0.0.1:8000"
SOURCE_CODE = "FIN_111_EXCEL"  # برای شناسایی این منبع در سیستم خودت

# این مسیر رو با مسیر واقعی فایل روی سیستم خودت عوض کن
EXCEL_PATH = r"F:\Freelancing_Project\KalaniProject\municipality_demo\111_Code.xlsx"
EXCEL_SHEET_NAME = 0  # اگر شیت خاصی اسم داشت، اسمش رو اینجا بذار

# این سه مقدار باید با داده‌های واقعی DB هماهنگ باشه
ORG_UNIT_FULL_CODE = "01-01-01-01"      # مثال؛ در ادامه میگم از کجا بیاری

CONTINUOUS_ACTION_CODE = "CA001"        # فقط خودِ کد، نه کل آبجکت

ACTION_TYPE_CODE = "ACT017"             # فقط خودِ کد، نه لیست

LIMIT_ROWS = 50  # برای تست فقط ۲۰ ردیف اول


def load_records(path: str, sheet_name=0):
    """
    اکسل 111_Code.xlsx را می‌خواند و آن را به رکوردهای قابل ارسال به API تبدیل می‌کند.
    """
    print(f"[load_records] reading excel: {path}")

    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")

    df = pd.read_excel(path_obj, sheet_name=sheet_name)
    print(f"[load_records] columns: {list(df.columns)}")
    print(f"[load_records] total rows in file: {len(df)}")

    expected_cols = [
        "سال مالی",
        "منطقه",
        "سند",
        "تاریخ",
        "کد کل",
        "کد معین",
        "کد تفضیلی",
        "کد جزء",
        "کل",
        "معین",
        "تفضیلی",
        "جزء",
        "بدهکار",
        "بستانکار",
        "RadKNo",
        "RadMNo",
        "RadTNo",
        "RadJNo",
        "RadJNam",
        "DocDesc",
        "RankDesc",
    ]

    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        print(f"[load_records] MISSING COLUMNS: {missing}")
        raise ValueError(f"Missing columns in Excel: {missing}.\nFound: {list(df.columns)}")

    records = []

    for idx, row in df.iterrows():
        debit = row["بدهکار"] if not pd.isna(row["بدهکار"]) else 0
        credit = row["بستانکار"] if not pd.isna(row["بستانکار"]) else 0
        amount = float(debit) - float(credit)

        if amount == 0:
            continue

        fiscal_year = str(row["سال مالی"]).strip()
        area = str(row["منطقه"]).strip()
        doc_no = str(row["سند"]).strip()
        rad_jno = "" if pd.isna(row["RadJNo"]) else str(int(row["RadJNo"]))

        local_record_id = f"{fiscal_year}-{area}-{doc_no}"
        if rad_jno:
            local_record_id += f"-{rad_jno}"

        financial_event_title = None
        if not pd.isna(row["RadJNam"]):
            financial_event_title = str(row["RadJNam"]).strip()

        desc_parts = []
        if not pd.isna(row["DocDesc"]):
            desc_parts.append(str(row["DocDesc"]).strip())
        if not pd.isna(row["RankDesc"]):
            desc_parts.append(str(row["RankDesc"]).strip())

        description = " | ".join(desc_parts) if desc_parts else None

        action_date = None  # فعلاً تاریخ رو نمی‌فرستیم (شمسیه)

        record = {
            "org_unit_full_code": ORG_UNIT_FULL_CODE,
            "continuous_action_code": CONTINUOUS_ACTION_CODE,
            "action_type_code": ACTION_TYPE_CODE,
            "financial_event_title": financial_event_title,
            "amount": amount,
            "local_record_id": local_record_id,
            "action_date": action_date,
            "description": description,
        }

        records.append(record)

    print(f"[load_records] prepared {len(records)} records with non-zero amount")
    return records


def send_record(record: dict, idx: int):
    """
    یک رکورد را به API external می‌فرستد.
    """
    url = f"{API_BASE_URL}/external/{SOURCE_CODE}/special-actions"
    print(f"[send_record] [{idx}] POST {url} local_record_id={record.get('local_record_id')}")
    print(f"[send_record] [{idx}] payload: {json.dumps(record, ensure_ascii=False, indent=2)}")
    resp = requests.post(url, json=record)
    print(f"[send_record] [{idx}] status={resp.status_code}")
    if resp.status_code != 200:
        print(f"[send_record] [{idx}] error body: {resp.text}")
        try:
            error_detail = resp.json()
            print(f"[send_record] [{idx}] error detail: {json.dumps(error_detail, ensure_ascii=False, indent=2)}")
        except:
            pass
        raise RuntimeError(f"API error {resp.status_code}: {resp.text}")
    return resp.json()


def main():
    print("=== 111_Code adapter started ===")
    print(f"Using EXCEL_PATH = {EXCEL_PATH}")
    print(f"Using ORG_UNIT_FULL_CODE = {ORG_UNIT_FULL_CODE}")
    print(f"Using CONTINUOUS_ACTION_CODE = {CONTINUOUS_ACTION_CODE}")
    print(f"Using ACTION_TYPE_CODE = {ACTION_TYPE_CODE}")

    records = load_records(EXCEL_PATH, sheet_name=EXCEL_SHEET_NAME)
    total = len(records)
    print(f"[main] total prepared records: {total}")

    if LIMIT_ROWS is not None:
        records = records[:LIMIT_ROWS]
        print(f"[main] limiting to first {len(records)} records for test.")

    ok = 0
    fail = 0

    for idx, rec in enumerate(records, start=1):
        try:
            result = send_record(rec, idx)
            ok += 1
            print(f"[main] [{idx}] OK → unique_code = {result['unique_code']}")
        except Exception as e:
            fail += 1
            print(f"[main] [{idx}] FAILED: {e}")

    print(f"=== DONE. Success: {ok}, Failed: {fail} ===")


if __name__ == "__main__":
    print(">>> __main__ block started (excel_111_code_adapter)")
    main()
