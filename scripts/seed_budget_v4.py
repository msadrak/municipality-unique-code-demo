"""
Budget Row Seeder V4 - ZONE-AWARE Edition
==========================================

This script seeds the BudgetRow table with:
1. ZONE EXTRACTION: Finds the zone/region column and maps to org_unit_id
2. SMART FILTER: Dynamically finds the column containing "مستمر" values
3. FLEXIBLE MATCHING: Strips ALL spaces before comparison
4. REVERSE LOOKUP: Activity title inside Excel description

Input Files:
- تملک دارایی سرمایه ای.xlsx (Capital) -> SMART FILTER on "مستمر"
- اعتبارات هزینه ای.xlsx (Expense) -> Import ALL rows

Usage:
    python scripts/seed_budget_v4.py              # Full seed
    python scripts/seed_budget_v4.py --dry-run    # Preview only
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
OUTPUT_MISSED = "scripts/missed_budget_rows_v4.csv"

# Persian text normalization map
ARABIC_TO_PERSIAN = {
    'ي': 'ی',
    'ك': 'ک',
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
}

# Zone name variations mapping (will be enhanced from database)
ZONE_NAME_VARIATIONS = {
    # Add common variations here
    'منطقه ۱': 'منطقه یک',
    'منطقه 1': 'منطقه یک',
    'منطقه۱': 'منطقه یک',
    'منطقه ۲': 'منطقه دو',
    'منطقه 2': 'منطقه دو',
    'منطقه۲': 'منطقه دو',
    # ... etc
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
    text = text.replace('\u200c', '')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def normalize_for_matching(text) -> str:
    """Aggressive normalization for fuzzy matching."""
    normalized = normalize_persian(text).lower()
    return re.sub(r'\s+', '', normalized)


def extract_zone_number(text: str) -> Optional[int]:
    """Extract zone number from text like 'منطقه ۱' or 'منطقه 15'."""
    if not text:
        return None
    
    normalized = normalize_persian(text)
    
    # Try to find "منطقه" followed by a number
    match = re.search(r'منطقه\s*(\d+)', normalized)
    if match:
        return int(match.group(1))
    
    # Try Persian number words
    persian_nums = {
        'یک': 1, 'دو': 2, 'سه': 3, 'چهار': 4, 'پنج': 5,
        'شش': 6, 'هفت': 7, 'هشت': 8, 'نه': 9, 'ده': 10,
        'یازده': 11, 'دوازده': 12, 'سیزده': 13, 'چهارده': 14, 'پانزده': 15
    }
    
    for word, num in persian_nums.items():
        if word in normalized:
            return num
    
    return None


# ============================================================
# DATABASE UTILITIES
# ============================================================

def load_org_unit_mapping() -> Dict[str, int]:
    """
    Load OrgUnit mapping from database.
    Returns dict: {normalized_title: id}
    """
    from app.database import SessionLocal
    from app.models import OrgUnit
    
    db = SessionLocal()
    mapping = {}
    
    try:
        zones = db.query(OrgUnit).filter(OrgUnit.org_type == 'zone').all()
        if not zones:
            zones = db.query(OrgUnit).filter(OrgUnit.parent_id.is_(None)).all()
        
        for zone in zones:
            # Add multiple variations for matching
            title_clean = normalize_for_matching(zone.title)
            mapping[title_clean] = zone.id
            
            # Also add "منطقهN" pattern
            zone_num = extract_zone_number(zone.title)
            if zone_num:
                mapping[f'منطقه{zone_num}'] = zone.id
                mapping[normalize_for_matching(f'منطقه {zone_num}')] = zone.id
                
        print(f"   [i] Loaded {len(zones)} zones from database")
    finally:
        db.close()
    
    return mapping


def load_activities_from_db() -> List[Dict]:
    """Load SubsystemActivity records from database."""
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
                'title_clean': normalize_for_matching(act.title),
                'subsystem_id': act.subsystem_id
            })
    finally:
        db.close()
    
    return activities


def resolve_zone_id(zone_text: str, mapping: Dict[str, int]) -> Optional[int]:
    """Resolve zone text to org_unit_id."""
    if not zone_text:
        return None
    
    # Try exact match first
    clean = normalize_for_matching(zone_text)
    if clean in mapping:
        return mapping[clean]
    
    # Try zone number extraction
    zone_num = extract_zone_number(zone_text)
    if zone_num:
        key = f'منطقه{zone_num}'
        if key in mapping:
            return mapping[key]
    
    # Try partial matching
    for key, zone_id in mapping.items():
        if key in clean or clean in key:
            return zone_id
    
    return None


# ============================================================
# COLUMN DETECTION
# ============================================================

def find_column_by_keywords(df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
    """Find column name that contains any of the keywords."""
    for col in df.columns:
        col_normalized = normalize_persian(str(col))
        for kw in keywords:
            if kw in col_normalized:
                return col
    return None


def find_continuous_column(df: pd.DataFrame) -> Optional[str]:
    """Find the column containing 'مستمر' values."""
    target = normalize_for_matching('مستمر')
    
    for col in df.columns:
        series = df[col].astype(str).apply(normalize_persian)
        if series.str.contains(target, na=False).any():
            count = series.str.contains(target, na=False).sum()
            print(f"   [i] Found 'مستمر' in column '{col}' ({count} rows)")
            return col
    
    return None


def find_zone_column(df: pd.DataFrame) -> Optional[str]:
    """Find column containing zone/region data."""
    zone_keywords = ['منطقه', 'واحد', 'مرکز هزینه', 'حوزه', 'zone', 'region']
    
    # First try column names
    col = find_column_by_keywords(df, zone_keywords)
    if col:
        print(f"   [i] Found zone column by name: '{col}'")
        return col
    
    # Then try column values
    for col in df.columns:
        sample = df[col].astype(str).head(50)
        sample_normalized = sample.apply(normalize_persian)
        zone_count = sample_normalized.str.contains('منطقه', na=False).sum()
        if zone_count > 5:
            print(f"   [i] Found zone column by values: '{col}' ({zone_count} zone mentions)")
            return col
    
    return None


# ============================================================
# ACTIVITY MATCHING
# ============================================================

def find_best_activity_match(
    description: str, 
    activities: List[Dict]
) -> Tuple[Optional[Dict], int]:
    """
    Find the best matching activity for a budget row description.
    Returns (activity_dict, match_score)
    """
    desc_clean = normalize_for_matching(description)
    
    if not desc_clean or len(desc_clean) < 3:
        return None, 0
    
    best_match = None
    best_score = 0
    
    for activity in activities:
        act_clean = activity['title_clean']
        
        if not act_clean:
            continue
        
        # Check if activity title is substring of description
        if act_clean in desc_clean:
            score = len(act_clean)
            if score > best_score:
                best_score = score
                best_match = activity
        
        # Also check reverse (description in activity title)
        elif desc_clean in act_clean:
            score = len(desc_clean)
            if score > best_score:
                best_score = score
                best_match = activity
    
    return best_match, best_score


# ============================================================
# DATA EXTRACTION
# ============================================================

def extract_budget_rows(
    df: pd.DataFrame, 
    budget_type: str, 
    zone_mapping: Dict[str, int],
    activities: List[Dict]
) -> Tuple[List[Dict], List[Dict]]:
    """
    Extract budget rows with zone and activity matching.
    Returns (matched_rows, missed_rows)
    """
    if df.empty:
        return [], []
    
    # Find columns
    code_col = find_column_by_keywords(df, ['کد ردیف', 'کد بودجه', 'کدردیف', 'کد'])
    desc_col = find_column_by_keywords(df, ['شرح ردیف', 'شرح'])
    amount_col = find_column_by_keywords(df, ['مصوب', 'مبلغ مصوب', 'مصوب 1403', 'مصوب 1404'])
    zone_col = find_zone_column(df)
    
    if code_col is None:
        code_col = df.columns[0]
        print(f"   [!] Using first column as code: '{code_col}'")
    
    if desc_col is None:
        print(f"   [!] Description column not found!")
        return [], []
    
    print(f"   [i] Columns: code='{code_col}', desc='{desc_col}', amount='{amount_col}', zone='{zone_col}'")
    
    matched_rows = []
    missed_rows = []
    
    for idx, row in df.iterrows():
        # Extract basic data
        code = str(row.get(code_col, '')).strip() if pd.notna(row.get(code_col)) else ''
        description = str(row.get(desc_col, '')).strip() if pd.notna(row.get(desc_col)) else ''
        
        if not code or not description:
            continue
        
        # Extract amount
        amount = 0
        if amount_col and pd.notna(row.get(amount_col)):
            try:
                amount = int(float(row.get(amount_col, 0)))
            except:
                amount = 0
        
        # Extract zone
        zone_text = ''
        zone_id = None
        if zone_col and pd.notna(row.get(zone_col)):
            zone_text = str(row.get(zone_col, '')).strip()
            zone_id = resolve_zone_id(zone_text, zone_mapping)
        
        # Match to activity
        activity, score = find_best_activity_match(description, activities)
        
        if activity:
            matched_rows.append({
                'budget_code': code,
                'description': description,
                'approved_amount': amount,
                'activity_id': activity['id'],
                'activity_code': activity['code'],
                'org_unit_id': zone_id,
                'zone_text': zone_text,
                'budget_type': budget_type,
                'match_score': score
            })
        else:
            missed_rows.append({
                'budget_code': code,
                'description': description[:100],
                'approved_amount': amount,
                'zone_text': zone_text,
                'budget_type': budget_type
            })
    
    return matched_rows, missed_rows


# ============================================================
# MAIN SEEDING LOGIC
# ============================================================

def load_capital_budget(filepath: str) -> pd.DataFrame:
    """Load Capital Budget with smart filtering on 'مستمر'."""
    print(f"\n[*] Loading Capital Budget: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"   [!] File not found!")
        return pd.DataFrame()
    
    try:
        df = pd.read_excel(filepath, engine='openpyxl')
    except Exception as e:
        print(f"   [X] Error: {e}")
        return pd.DataFrame()
    
    print(f"   [i] Total rows: {len(df)}")
    
    # V4: RELAXED FILTER - Don't require 'مستمر' strictly
    continuous_col = find_continuous_column(df)
    
    if continuous_col:
        # Filter to rows containing "مستمر"
        target = normalize_for_matching('مستمر')
        mask = df[continuous_col].astype(str).apply(
            lambda x: target in normalize_for_matching(x)
        )
        df_filtered = df[mask].copy()
        print(f"   [+] Filtered to {len(df_filtered)} 'مستمر' rows")
    else:
        # If no continuous column found, take all rows
        print(f"   [!] No 'مستمر' column found, using ALL rows")
        df_filtered = df.copy()
    
    df_filtered['budget_type'] = 'capital'
    return df_filtered


def load_expense_budget(filepath: str) -> pd.DataFrame:
    """Load Expense Budget (all rows)."""
    print(f"\n[*] Loading Expense Budget: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"   [!] File not found!")
        return pd.DataFrame()
    
    try:
        df = pd.read_excel(filepath, engine='openpyxl')
    except Exception as e:
        print(f"   [X] Error: {e}")
        return pd.DataFrame()
    
    print(f"   [+] Total rows: {len(df)} (all included)")
    
    df = df.copy()
    df['budget_type'] = 'expense'
    return df


def seed_budget_rows(dry_run: bool = False):
    """Main seeding function - Zone-Aware Edition."""
    print("\n" + "=" * 60)
    print("BUDGET ROW SEEDER V4 - ZONE-AWARE")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    stats = {
        'inserted': 0,
        'updated': 0,
        'missed': 0,
        'with_zone': 0,
        'without_zone': 0,
        'errors': []
    }
    
    # ---- PHASE 1: Load Reference Data ----
    print("\n" + "-" * 50)
    print("PHASE 1: Loading Reference Data")
    print("-" * 50)
    
    zone_mapping = load_org_unit_mapping()
    activities = load_activities_from_db()
    print(f"   [+] Loaded {len(activities)} activities")
    
    # ---- PHASE 2: Load Excel Files ----
    print("\n" + "-" * 50)
    print("PHASE 2: Loading Excel Files")
    print("-" * 50)
    
    df_capital = load_capital_budget(INPUT_CAPITAL)
    df_expense = load_expense_budget(INPUT_EXPENSE)
    
    # ---- PHASE 3: Extract and Match ----
    print("\n" + "-" * 50)
    print("PHASE 3: Extracting Budget Rows")
    print("-" * 50)
    
    all_matched = []
    all_missed = []
    
    if not df_capital.empty:
        print("\n   Processing Capital Budget...")
        matched, missed = extract_budget_rows(df_capital, 'capital', zone_mapping, activities)
        all_matched.extend(matched)
        all_missed.extend(missed)
        print(f"   [+] Matched: {len(matched)}, Missed: {len(missed)}")
    
    if not df_expense.empty:
        print("\n   Processing Expense Budget...")
        matched, missed = extract_budget_rows(df_expense, 'expense', zone_mapping, activities)
        all_matched.extend(matched)
        all_missed.extend(missed)
        print(f"   [+] Matched: {len(matched)}, Missed: {len(missed)}")
    
    # ---- PHASE 4: Deduplicate ----
    print("\n" + "-" * 50)
    print("PHASE 4: Deduplication")
    print("-" * 50)
    
    deduplicated = {}
    for row in all_matched:
        key = row['budget_code']
        if key not in deduplicated:
            deduplicated[key] = row
        elif row['approved_amount'] > deduplicated[key]['approved_amount']:
            deduplicated[key] = row
    
    unique_rows = list(deduplicated.values())
    print(f"   [+] Unique budget codes: {len(unique_rows)} (from {len(all_matched)} total)")
    
    # Count zones
    for row in unique_rows:
        if row['org_unit_id']:
            stats['with_zone'] += 1
        else:
            stats['without_zone'] += 1
    
    print(f"   [i] With zone: {stats['with_zone']}, Without zone (Global): {stats['without_zone']}")
    
    # ---- PHASE 5: Save Missed ----
    if all_missed:
        print(f"\n   [!] Writing {len(all_missed)} missed rows to {OUTPUT_MISSED}")
        with open(OUTPUT_MISSED, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['budget_code', 'description', 'approved_amount', 'zone_text', 'budget_type'])
            writer.writeheader()
            writer.writerows(all_missed)
        stats['missed'] = len(all_missed)
    
    # ---- PHASE 6: Database Insert ----
    if dry_run:
        print("\n[DRY RUN] No database changes made")
        print("\n   Sample rows that WOULD be inserted:")
        for row in unique_rows[:5]:
            print(f"      {row['budget_code']} -> Activity {row['activity_code']}, Zone: {row.get('zone_text', 'N/A')}")
        return stats
    
    print("\n" + "-" * 50)
    print("PHASE 6: Inserting/Updating Database")
    print("-" * 50)
    
    from app.database import SessionLocal
    from app.models import BudgetRow
    
    db = SessionLocal()
    try:
        for row in unique_rows:
            existing = db.query(BudgetRow).filter(
                BudgetRow.budget_coding == row['budget_code']
            ).first()
            
            if existing:
                existing.description = row['description']
                existing.approved_amount = row['approved_amount']
                existing.activity_id = row['activity_id']
                existing.org_unit_id = row['org_unit_id']  # V4: Zone support
                stats['updated'] += 1
            else:
                new_row = BudgetRow(
                    activity_id=row['activity_id'],
                    org_unit_id=row['org_unit_id'],  # V4: Zone support
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
    
    # ---- Summary ----
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"   Inserted: {stats['inserted']}")
    print(f"   Updated: {stats['updated']}")
    print(f"   With Zone: {stats['with_zone']}")
    print(f"   Global: {stats['without_zone']}")
    print(f"   Missed: {stats['missed']}")
    print(f"   Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return stats


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Budget Row Seeder V4 - Zone-Aware")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Preview without changes")
    args = parser.parse_args()
    
    seed_budget_rows(dry_run=args.dry_run)
