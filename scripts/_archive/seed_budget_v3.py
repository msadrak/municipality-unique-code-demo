"""
Budget Row Seeder V3 - Smart Column Detection & Fuzzy Matching
==============================================================

This script seeds the BudgetRow table with:
1. SMART FILTER: Dynamically finds the column containing "مستمر" values
2. FLEXIBLE MATCHING: Strips ALL spaces before comparison
3. REVERSE LOOKUP: Activity title inside Excel description
4. TIE-BREAKER: Longest matching title wins

Input Files:
- تملک دارایی سرمایه ای.xlsx (Capital) -> SMART FILTER on "مستمر"
- اعتبارات هزینه ای.xlsx (Expense) -> Import ALL rows

Usage:
    python scripts/seed_budget_v3.py              # Full seed
    python scripts/seed_budget_v3.py --dry-run    # Preview only
"""

import sys
import os
import csv
import re
from datetime import datetime
from typing import Optional, List, Dict, Tuple

# Ensure we can import from 'app'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_CAPITAL = "تملک دارایی سرمایه ای.xlsx"
INPUT_EXPENSE = "اعتبارات هزینه ای.xlsx"
OUTPUT_MISSED = "scripts/missed_budget_rows_v3.csv"

# Persian text normalization map
ARABIC_TO_PERSIAN = {
    'ي': 'ی',
    'ك': 'ک',
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
}


# ============================================================
# TEXT UTILITIES
# ============================================================

def normalize_persian(text) -> str:
    """Normalize Persian/Arabic text for comparison."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    text = str(text).strip()
    for ar, fa in ARABIC_TO_PERSIAN.items():
        text = text.replace(ar, fa)
    # Replace zero-width non-joiner with nothing (not space)
    text = text.replace('\u200c', '')
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def normalize_for_matching(text) -> str:
    """
    Aggressive normalization for fuzzy matching.
    Strips ALL spaces and normalizes Persian characters.
    """
    normalized = normalize_persian(text).lower()
    # Remove ALL whitespace for matching
    return re.sub(r'\s+', '', normalized)


def find_best_activity_match(
    description: str, 
    activities: List[Dict]
) -> Optional[Dict]:
    """
    REVERSE LOOKUP with space-stripped matching.
    
    Logic:
    - Normalize both sides by removing ALL spaces
    - Check if activity.title exists inside description
    - Pick LONGEST matching title (most specific)
    
    Args:
        description: The dirty Excel description
        activities: List of activity dicts with 'id', 'code', 'title', 'title_clean'
    
    Returns:
        The best matching activity dict, or None
    """
    desc_clean = normalize_for_matching(description)
    
    best_match = None
    best_length = 0
    
    for activity in activities:
        title_clean = activity['title_clean']  # Pre-computed
        
        # Check if activity title exists inside description
        if title_clean in desc_clean:
            # Tie-breaker: prefer longer (more specific) titles
            if len(title_clean) > best_length:
                best_length = len(title_clean)
                best_match = activity
    
    return best_match


# ============================================================
# SMART COLUMN DETECTION
# ============================================================

def find_continuous_column(df: pd.DataFrame) -> Optional[str]:
    """
    Smart Column Detection: Find which column contains "مستمر" values.
    
    Iterates through ALL columns and checks if any contain the string "مستمر".
    
    Returns:
        Column name if found, None otherwise
    """
    target = 'مستمر'
    
    for col in df.columns:
        # Check if any value in this column contains "مستمر"
        series = df[col].astype(str).apply(normalize_persian)
        if series.str.contains(target, na=False).any():
            count = series.str.contains(target, na=False).sum()
            print(f"   [i] Found '{target}' in column '{col}' ({count} rows)")
            return col
    
    return None


def find_column_by_keywords(df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
    """Find column name that contains any of the keywords."""
    for col in df.columns:
        col_normalized = normalize_persian(str(col))
        for kw in keywords:
            if kw in col_normalized:
                return col
    return None


# ============================================================
# DATA LOADING
# ============================================================

def load_activities_from_db() -> List[Dict]:
    """Load SubsystemActivity records from database with pre-computed clean titles."""
    from app.database import SessionLocal
    from app.models import SubsystemActivity
    
    db = SessionLocal()
    activities = []
    try:
        for act in db.query(SubsystemActivity).filter(SubsystemActivity.is_active == True).all():
            activities.append({
                'id': act.id,
                'code': act.code,
                'title': act.title,
                'title_clean': normalize_for_matching(act.title),  # Pre-compute
                'subsystem_id': act.subsystem_id
            })
    finally:
        db.close()
    
    return activities


def load_capital_budget(filepath: str) -> pd.DataFrame:
    """
    Load Capital Budget file with SMART filtering.
    
    Dynamically finds the column containing "مستمر" and filters on it.
    """
    print(f"\n[*] Loading Capital Budget: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"   [!] File not found!")
        return pd.DataFrame()
    
    try:
        df = pd.read_excel(filepath, engine='openpyxl')
    except Exception as e:
        print(f"   [X] Error loading file: {e}")
        return pd.DataFrame()
    
    print(f"   [i] Total rows in file: {len(df)}")
    print(f"   [i] Columns: {list(df.columns)}")
    
    # Smart Column Detection
    print(f"\n   [*] Searching for column containing 'mostamar'...")
    continuous_col = find_continuous_column(df)
    
    if continuous_col is None:
        print(f"   [!] CRITICAL: No column contains 'mostamar' values!")
        print(f"   [!] Safety mode: Importing ZERO rows from capital budget.")
        print(f"   [!] Please verify the Excel file format.")
        return pd.DataFrame()
    
    # Apply filter
    initial_count = len(df)
    df[continuous_col] = df[continuous_col].apply(lambda x: normalize_persian(x) if pd.notna(x) else '')
    df_filtered = df[df[continuous_col].str.contains('مستمر', na=False, case=False)]
    
    filtered_count = len(df_filtered)
    discarded = initial_count - filtered_count
    
    print(f"   [+] Rows with 'mostamar': {filtered_count}")
    print(f"   [-] Rows DISCARDED (projects): {discarded}")
    
    if filtered_count == 0:
        print(f"   [!] WARNING: Zero continuous rows found!")
    
    # Add budget type marker
    df_filtered = df_filtered.copy()
    df_filtered['budget_type'] = 'capital'
    
    return df_filtered


def load_expense_budget(filepath: str) -> pd.DataFrame:
    """
    Load Expense Budget file (ALL rows are valid).
    """
    print(f"\n[*] Loading Expense Budget: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"   [!] File not found!")
        return pd.DataFrame()
    
    try:
        df = pd.read_excel(filepath, engine='openpyxl')
    except Exception as e:
        print(f"   [X] Error loading file: {e}")
        return pd.DataFrame()
    
    print(f"   [+] Total rows: {len(df)} (all included)")
    print(f"   [i] Columns: {list(df.columns)}")
    
    # Add budget type marker
    df = df.copy()
    df['budget_type'] = 'expense'
    
    return df


def extract_budget_rows(df: pd.DataFrame, budget_type: str) -> List[Dict]:
    """
    Extract budget rows from DataFrame.
    
    Smart detection of code and description columns.
    """
    if df.empty:
        return []
    
    # Find required columns with flexible detection
    code_col = find_column_by_keywords(df, ['کد ردیف', 'کد بودجه', 'کدردیف', 'کد'])
    desc_col = find_column_by_keywords(df, ['شرح ردیف', 'شرح'])
    amount_col = find_column_by_keywords(df, ['مصوب', 'مبلغ مصوب', 'مصوب 1403', 'مصوب 1404'])
    
    # Fallback: Use first column as code if not found
    if code_col is None:
        code_col = df.columns[0]
        print(f"   [!] Using first column as code: '{code_col}'")
    
    if desc_col is None:
        print(f"   [!] Required 'description' column not found!")
        print(f"   Available: {list(df.columns)}")
        return []
    
    print(f"   [i] Using columns: code='{code_col}', desc='{desc_col}', amount='{amount_col}'")
    
    rows = []
    for _, row in df.iterrows():
        code_value = normalize_persian(row.get(code_col, ''))
        desc_value = normalize_persian(row.get(desc_col, ''))
        
        if not code_value or not desc_value:
            continue
        
        # Parse amount
        amount = 0
        if amount_col and pd.notna(row.get(amount_col)):
            try:
                amount_str = str(row[amount_col]).replace(',', '').replace('،', '')
                amount = int(float(amount_str))
            except (ValueError, TypeError):
                amount = 0
        
        rows.append({
            'budget_code': code_value,
            'description': desc_value,
            'approved_amount': amount,
            'budget_type': budget_type
        })
    
    return rows


# ============================================================
# DATABASE OPERATIONS
# ============================================================

def seed_budget_rows(dry_run: bool = False) -> Dict:
    """
    Main seeding function with smart detection and fuzzy matching.
    """
    from app.database import SessionLocal, engine
    from app.models import Base, BudgetRow
    
    stats = {
        'capital_total': 0,
        'capital_filtered': 0,
        'expense_total': 0,
        'matched': 0,
        'missed': 0,
        'inserted': 0,
        'updated': 0,
        'errors': []
    }
    
    print("\n" + "=" * 70)
    print("BUDGET ROW SEEDER V3 - Smart Detection & Fuzzy Matching")
    print("=" * 70)
    
    # Ensure tables exist
    if not dry_run:
        Base.metadata.create_all(bind=engine)
    
    # ---- PHASE 1: Load Activities from DB ----
    print("\n" + "-" * 50)
    print("PHASE 1: Loading Activities from Database")
    print("-" * 50)
    
    activities = load_activities_from_db()
    print(f"   [+] Loaded {len(activities)} active activities")
    
    if len(activities) == 0:
        print("   [X] No activities in database! Run seed_full_system.py first.")
        stats['errors'].append("No activities in database")
        return stats
    
    # Show sample titles (original and cleaned)
    print("   [i] Sample activity titles (original -> cleaned):")
    for act in activities[:3]:
        print(f"      - {act['title']} -> '{act['title_clean']}'")
    
    # ---- PHASE 2: Load Excel Files ----
    print("\n" + "-" * 50)
    print("PHASE 2: Loading Excel Budget Files (Smart Detection)")
    print("-" * 50)
    
    # Load Capital (with smart filtering)
    capital_df = load_capital_budget(INPUT_CAPITAL)
    capital_rows = extract_budget_rows(capital_df, 'capital')
    stats['capital_total'] = len(capital_df) if not capital_df.empty else 0
    stats['capital_filtered'] = len(capital_rows)
    
    # Load Expense (all rows)
    expense_df = load_expense_budget(INPUT_EXPENSE)
    expense_rows = extract_budget_rows(expense_df, 'expense')
    stats['expense_total'] = len(expense_rows)
    
    all_rows = capital_rows + expense_rows
    print(f"\n   [i] Total budget rows to process: {len(all_rows)}")
    print(f"      - Capital (filtered): {len(capital_rows)}")
    print(f"      - Expense: {len(expense_rows)}")
    
    if len(all_rows) == 0:
        print("   [!] No budget rows to process!")
        return stats
    
    # ---- PHASE 3: Matching with Fuzzy Lookup ----
    print("\n" + "-" * 50)
    print("PHASE 3: Fuzzy Matching (Space-Stripped Comparison)")
    print("-" * 50)
    
    matched_rows = []
    missed_rows = []
    
    for row in all_rows:
        match = find_best_activity_match(row['description'], activities)
        
        if match:
            matched_rows.append({
                **row,
                'activity_id': match['id'],
                'activity_code': match['code'],
                'activity_title': match['title']
            })
            stats['matched'] += 1
        else:
            missed_rows.append(row)
            stats['missed'] += 1
    
    print(f"\n   [+] Matched: {stats['matched']}")
    print(f"   [!] Missed (no activity match): {stats['missed']}")
    
    # Show sample matches
    if matched_rows:
        print("\n   [i] Sample matches:")
        for row in matched_rows[:5]:
            desc_short = row['description'][:40] if len(row['description']) > 40 else row['description']
            print(f"      '{desc_short}...'")
            print(f"         -> {row['activity_code']}: {row['activity_title']}")
    
    # ---- PHASE 4: Write Missed Rows Report ----
    if missed_rows:
        print(f"\n[*] Writing missed rows to: {OUTPUT_MISSED}")
        with open(OUTPUT_MISSED, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'budget_code', 'description', 'approved_amount', 'budget_type'
            ])
            writer.writeheader()
            writer.writerows(missed_rows)
        print(f"   [+] Wrote {len(missed_rows)} rows for human review")
    
    # ---- PHASE 5: Insert into Database ----
    if dry_run:
        print("\n[DRY RUN] No database changes made")
        print("\n   Sample rows that WOULD be inserted:")
        for row in matched_rows[:5]:
            print(f"      {row['budget_code']} -> Activity {row['activity_code']}")
            print(f"         Amount: {row['approved_amount']:,} Rials")
    else:
        print("\n" + "-" * 50)
        print("PHASE 5: Inserting/Updating Database")
        print("-" * 50)
        
        # CRITICAL: Deduplicate matched_rows by budget_code (keep latest/highest amount)
        print("   [*] Deduplicating by budget_code...")
        deduplicated = {}
        for row in matched_rows:
            budget_code = row['budget_code']
            if budget_code not in deduplicated:
                deduplicated[budget_code] = row
            else:
                # Keep the one with higher approved_amount
                if row['approved_amount'] > deduplicated[budget_code]['approved_amount']:
                    deduplicated[budget_code] = row
        
        unique_rows = list(deduplicated.values())
        print(f"   [+] Unique budget codes: {len(unique_rows)} (from {len(matched_rows)} total)")
        
        db = SessionLocal()
        try:
            for row in unique_rows:
                # UPSERT logic
                existing = db.query(BudgetRow).filter(
                    BudgetRow.budget_coding == row['budget_code']
                ).first()
                
                if existing:
                    # Update existing
                    existing.description = row['description']
                    existing.approved_amount = row['approved_amount']
                    existing.activity_id = row['activity_id']
                    stats['updated'] += 1
                else:
                    # Insert new
                    new_row = BudgetRow(
                        activity_id=row['activity_id'],
                        budget_coding=row['budget_code'],
                        description=row['description'],
                        approved_amount=row['approved_amount'],
                        blocked_amount=0,
                        spent_amount=0,
                        fiscal_year='1403'
                    )
                    db.add(new_row)
                    stats['inserted'] += 1
            
            db.commit()
            print(f"   [+] Inserted: {stats['inserted']}")
            print(f"   [+] Updated: {stats['updated']}")
            
        except Exception as e:
            db.rollback()
            stats['errors'].append(str(e))
            print(f"   [X] Error: {e}")
            raise
        finally:
            db.close()
    
    # ---- SUMMARY ----
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"   Capital Budget:")
    print(f"      - Total rows in file: {stats['capital_total']}")
    print(f"      - After 'mostamar' filter: {stats['capital_filtered']}")
    print(f"   Expense Budget:")
    print(f"      - Total rows: {stats['expense_total']}")
    print(f"   Matching:")
    print(f"      - Matched to Activity: {stats['matched']}")
    print(f"      - Missed (for review): {stats['missed']}")
    if not dry_run:
        print(f"   Database:")
        print(f"      - Inserted: {stats['inserted']}")
        print(f"      - Updated: {stats['updated']}")
    if missed_rows:
        print(f"\n   [!] Review {OUTPUT_MISSED} for unmatched budget rows")
    print("=" * 70)
    
    return stats


# ============================================================
# MAIN
# ============================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Seed BudgetRow table with smart detection and fuzzy matching"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Preview changes without modifying database"
    )
    
    args = parser.parse_args()
    seed_budget_rows(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
