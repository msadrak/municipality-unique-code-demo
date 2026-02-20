# -*- coding: utf-8 -*-
"""
Compare region14_civil_items.csv vs Sarmayei_Region14.xlsx
- Civil CSV = the 20 items chosen as civil (عمران و طرح‌ها).
- Excel = full Region 14 budget.
Output: budget rows in Excel that are NOT in the civil list (not chosen as civil), and why.
"""
import sys
import pandas as pd
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CIVIL_CSV = SCRIPT_DIR / "region14_civil_items.csv"
# Try multiple possible locations for Excel
EXCEL_CANDIDATES = [
    PROJECT_ROOT / "data" / "reports" / "Sarmayei_Region14.xlsx",
    PROJECT_ROOT / "Sarmayei_Region14.xlsx",
    SCRIPT_DIR / "Sarmayei_Region14.xlsx",
]


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Compare civil items CSV vs Region14 Excel budget")
    parser.add_argument("excel", nargs="?", help="Path to Sarmayei_Region14.xlsx (optional)")
    args = parser.parse_args()

    if args.excel:
        excel_path = Path(args.excel)
        if not excel_path.exists():
            print(f"ERROR: File not found: {excel_path}")
            return 1
        EXCEL_CANDIDATES.insert(0, excel_path)
    # 1) Load civil items (first file)
    if not CIVIL_CSV.exists():
        print(f"ERROR: Civil CSV not found: {CIVIL_CSV}")
        return 1
    civil_df = pd.read_csv(CIVIL_CSV, encoding="utf-8")
    # Normalize budget code column (might be "کد بودجه")
    code_col = [c for c in civil_df.columns if "کد" in c or "code" in c.lower()]
    if not code_col:
        code_col = [civil_df.columns[0]]
    civil_codes = set(civil_df[code_col[0]].astype(str).str.strip())
    civil_codes.discard("nan")
    print(f"Civil items (first file): {len(civil_codes)} rows")
    print(f"  Codes: {sorted(civil_codes)}\n")

    # 2) Load Excel (second file)
    excel_path = None
    for p in EXCEL_CANDIDATES:
        if p.exists():
            excel_path = p
            break
    if not excel_path:
        print("ERROR: Sarmayei_Region14.xlsx not found in:")
        for p in EXCEL_CANDIDATES:
            print(f"  - {p}")
        print("\nPlace the Excel file in data/reports/ or project root and run again.")
        return 1

    df = pd.read_excel(excel_path)
    # Find budget code column
    budget_col = None
    for c in df.columns:
        if "کد بودجه" in str(c) or (isinstance(c, str) and "بودجه" in c and "کد" in c):
            budget_col = c
            break
    if budget_col is None:
        budget_col = df.columns[0]
    excel_codes = df[budget_col].astype(str).str.strip()
    excel_codes_set = set(excel_codes.dropna())
    excel_codes_set.discard("nan")

    # 3) Which Excel rows are NOT in civil list?
    not_civil = excel_codes_set - civil_codes
    in_civil = excel_codes_set & civil_codes

    print(f"Excel (second file): {len(excel_codes_set)} budget rows from {excel_path.name}\n")
    print("=" * 70)
    print("Budget rows in Excel that are NOT in civil items (not chosen as civil):")
    print("=" * 70)

    # Build full rows for "not civil" for description
    desc_col = None
    for c in df.columns:
        if "شرح" in str(c):
            desc_col = c
            break
    if desc_col is None:
        desc_col = df.columns[1] if len(df.columns) > 1 else None

    not_civil_list = sorted(not_civil)
    for i, code in enumerate(not_civil_list, 1):
        row = df[df[budget_col].astype(str).str.strip() == code].iloc[0]
        desc = row.get(desc_col, "") if desc_col is not None else ""
        print(f"  {i:2}. {code}  |  {desc}")

    print()
    print("=" * 70)
    print("Summary:")
    print("=" * 70)
    print(f"  Total in Excel:           {len(excel_codes_set)}")
    print(f"  Chosen as civil (in CSV): {len(in_civil)}")
    print(f"  NOT chosen as civil:      {len(not_civil_list)}")
    print()
    print("Why these are not in the civil list:")
    print("  They are budget lines that were not classified as civil/construction")
    print("  (عمران و طرح‌ها). Only the 20 lines in region14_civil_items.csv are")
    print("  treated as civil items; the rest may be administrative, cultural,")
    print("  social, or other non-civil activities.")
    print()
    if len(civil_codes) == 20:
        print("  Civil items count check: exactly 20 civil items (OK).")
    else:
        print(f"  Civil items count: {len(civil_codes)} (expected 20).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
