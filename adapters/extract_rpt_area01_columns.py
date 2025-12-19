# adapters/extract_rpt_area01_columns.py
# -*- coding: utf-8 -*-
import pandas as pd
from pathlib import Path


# ریشه‌ی پروژه (یک پوشه بالاتر از adapters)
ROOT_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT_DIR / "Rpt_area01.xlsx"
OUTPUT_FILE = ROOT_DIR / "Rpt_area01_extracted.xlsx"


def detect_date_column(df: pd.DataFrame) -> str:
    """
    پیدا کردن ستون تاریخ:
    - اگر ستونی Unnamed / No column name بود، همون
    - وگرنه ستون سوم (index=2) را فرض می‌کنیم
    """
    for c in df.columns:
        s = str(c)
        if "Unnamed" in s or "No column name" in s:
            return c
    return df.columns[2]


def safe_int_series(series: pd.Series) -> pd.Series:
    """تبدیل یک سری به عدد صحیح (ناعددی‌ها → 0)"""
    return pd.to_numeric(series, errors="coerce").fillna(0).astype("int64")


def make_unique_code(row: pd.Series, idx: int) -> str:
    """
    ساخت کد یکتا بر اساس:
    AreaNo - تاریخ۸رقمی - DocNo - شمارنده ۵رقمی
    مثال: 1-14030119-1-00001
    """
    area = int(row.get("AreaNo", 0) or 0)

    raw_date = str(row.get("ActionDateRaw", "") or "")
    digits = "".join(ch for ch in raw_date if ch.isdigit())
    date_part = (digits[:8] if len(digits) >= 8 else "00000000")

    doc_no = int(row.get("DocNo", 0) or 0)

    return f"{area}-{date_part}-{doc_no}-{idx:05d}"


def main():
    print(f"📥 در حال خواندن اکسل اصلی از: {INPUT_FILE}")
    df = pd.read_excel(INPUT_FILE)
    print(f"تعداد ردیف‌ها در فایل اصلی: {len(df)}")

    # --- ۱) تشخیص و نگه‌داشتن ستون تاریخ ---
    date_col = detect_date_column(df)
    df["ActionDateRaw"] = df[date_col]

    # --- ۲) ستون‌های کد کل / معین / تفصیلی / جزء ---

    # اگر این اسامی در فایل اصلی هستند، همان‌ها را به Kol/Moein/... نگه می‌داریم
    # در غیر این صورت صفرشان می‌کنیم
    if "TitKNo" in df.columns:
        df["Kol"] = safe_int_series(df["TitKNo"])
    elif "کل" in df.columns:
        df["Kol"] = safe_int_series(df["کل"])
    else:
        df["Kol"] = 0

    if "TitMNo" in df.columns:
        df["Moein"] = safe_int_series(df["TitMNo"])
    elif "معین" in df.columns:
        df["Moein"] = safe_int_series(df["معین"])
    else:
        df["Moein"] = 0

    if "TitTNo" in df.columns:
        df["Tafsili"] = safe_int_series(df["TitTNo"])
    elif "تفصیلی" in df.columns:
        df["Tafsili"] = safe_int_series(df["تفصیلی"])
    else:
        df["Tafsili"] = 0

    if "TitJNo" in df.columns:
        df["Joz"] = safe_int_series(df["TitJNo"])
    elif "جزء" in df.columns:
        df["Joz"] = safe_int_series(df["جزء"])
    else:
        df["Joz"] = 0

    # کد کامل حساب
    df["FullAccountCode"] = (
        df["Kol"].astype(str)
        + "-" + df["Moein"].astype(str)
        + "-" + df["Tafsili"].astype(str)
        + "-" + df["Joz"].astype(str)
    )

    # --- ۳) مبلغ‌ها و خالص مبلغ ---
    if "DebitAmnt" not in df.columns:
        df["DebitAmnt"] = 0
    if "CreditAmnt" not in df.columns:
        df["CreditAmnt"] = 0

    debit = pd.to_numeric(df["DebitAmnt"], errors="coerce").fillna(0)
    credit = pd.to_numeric(df["CreditAmnt"], errors="coerce").fillna(0)
    df["NetAmount"] = debit - credit

    # --- ۴) ساخت UniqueCode برای هر ردیف ---
    df = df.reset_index(drop=True)
    df["UniqueCode"] = [
        make_unique_code(row, idx + 1) for idx, row in df.iterrows()
    ]

    # --- ۵) انتخاب ستون‌ها برای خروجی ---
    desired_cols = [
        "AreaNo",
        "DocNo",
        "ActionDateRaw",

        "Kol",
        "Moein",
        "Tafsili",
        "Joz",
        "FullAccountCode",

        "TitJNam",

        "RadKNo",
        "RadMNo",
        "RadTNo",
        "RadJNo",
        "RadJNam",

        "DocDesc",
        "RankDesc",

        "DebitAmnt",
        "CreditAmnt",
        "NetAmount",

        "UniqueCode",
    ]

    existing_cols = [c for c in desired_cols if c in df.columns]
    out_df = df[existing_cols]

    # --- ۶) ذخیره اکسل خروجی ---
    out_df.to_excel(OUTPUT_FILE, index=False)
    print(f"✅ استخراج انجام شد. {len(out_df)} ردیف نوشتیم به:\n   {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
