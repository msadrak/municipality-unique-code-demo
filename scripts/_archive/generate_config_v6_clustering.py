"""
Master Config Generator V6 - Common Prefix Clustering
=======================================================
Generates app/config/config_master.json using a THREE-LAYER cleaning pipeline:

Layer 1: Golden Dictionary (CLEANING_MAP) - Highest Priority
Layer 2: Common Prefix Clustering - Groups similar descriptions
Layer 3: Strict Fallback - "سایر خدمات [Subsystem]"

This eliminates garbage data (specific names like streets) while preserving
meaningful activity categories.

Usage:
    python scripts/generate_config_v6_clustering.py
"""

import pandas as pd
import json
import re
from collections import defaultdict, Counter
from typing import Optional, List, Dict, Set, Tuple
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_CAPITAL = "تملک دارایی سرمایه ای.xlsx"
INPUT_EXPENSE = "اعتبارات هزینه ای.xlsx"
OUTPUT_FILE = "app/config/config_master.json"

# Minimum occurrences for a prefix to become a cluster
MIN_CLUSTER_SIZE = 3

# Minimum prefix length (words) for clustering
MIN_PREFIX_WORDS = 2


# ============================================================
# THE 13 SUBSYSTEMS DEFINITION
# ============================================================

SUBSYSTEMS = {
    "URBAN_PLANNING": {
        "code": "URBAN_PLANNING",
        "title": "سامانه شهرسازی",
        "persian_name": "شهرسازی",
        "icon": "Building2",
        "attachment_type": "both",
        "order": 1
    },
    "CONTRACTS": {
        "code": "CONTRACTS",
        "title": "سامانه امور قراردادها",
        "persian_name": "قراردادها",
        "icon": "FileText",
        "attachment_type": "both",
        "order": 2
    },
    "PAYROLL": {
        "code": "PAYROLL",
        "title": "سامانه حقوق و دستمزد",
        "persian_name": "حقوق و دستمزد",
        "icon": "Users",
        "attachment_type": "api",
        "order": 3
    },
    "TADAROKAT": {
        "code": "TADAROKAT",
        "title": "سامانه تدارکات",
        "persian_name": "تدارکات",
        "icon": "ShoppingCart",
        "attachment_type": "upload",
        "order": 4
    },
    "BUDGET": {
        "code": "BUDGET",
        "title": "سامانه بودجه",
        "persian_name": "بودجه",
        "icon": "BarChart3",
        "attachment_type": "none",
        "order": 5
    },
    "TREASURY": {
        "code": "TREASURY",
        "title": "سامانه خزانه‌داری",
        "persian_name": "خزانه‌داری",
        "icon": "Vault",
        "attachment_type": "upload",
        "order": 6
    },
    "CONTRACTORS": {
        "code": "CONTRACTORS",
        "title": "سامانه امور پیمانکاران",
        "persian_name": "پیمانکاران",
        "icon": "HardHat",
        "attachment_type": "both",
        "order": 7
    },
    "WELFARE": {
        "code": "WELFARE",
        "title": "سامانه رفاه کارکنان",
        "persian_name": "رفاه",
        "icon": "Heart",
        "attachment_type": "upload",
        "order": 8
    },
    "REAL_ESTATE": {
        "code": "REAL_ESTATE",
        "title": "سامانه املاک",
        "persian_name": "املاک",
        "icon": "Home",
        "attachment_type": "both",
        "order": 9
    },
    "WAREHOUSE": {
        "code": "WAREHOUSE",
        "title": "سامانه انبار و اموال",
        "persian_name": "انبار و اموال",
        "icon": "Package",
        "attachment_type": "upload",
        "order": 10
    },
    "REVENUE": {
        "code": "REVENUE",
        "title": "سامانه درآمد",
        "persian_name": "درآمد",
        "icon": "TrendingUp",
        "attachment_type": "api",
        "order": 11
    },
    "ISFAHAN_CARD": {
        "code": "ISFAHAN_CARD",
        "title": "سامانه اصفهان کارت",
        "persian_name": "اصفهان کارت",
        "icon": "CreditCard",
        "attachment_type": "api",
        "order": 12
    },
    "INVESTMENT": {
        "code": "INVESTMENT",
        "title": "سامانه مشارکت‌ها و سرمایه‌گذاری",
        "persian_name": "مشارکت‌ها",
        "icon": "Handshake",
        "attachment_type": "both",
        "order": 13
    },
    "OTHER": {
        "code": "OTHER",
        "title": "سایر / عمومی",
        "persian_name": "سایر",
        "icon": "MoreHorizontal",
        "attachment_type": "upload",
        "order": 14
    }
}


# ============================================================
# LAYER 1: GOLDEN DICTIONARY (CLEANING_MAP)
# ============================================================

CLEANING_MAP = {
    # Urban & Services
    "نگهداری و توسعه فضای سبز": ["فضای سبز", "پارک", "درخت", "گیاه", "آبیاری", "چمن", "باغبانی"],
    "نظافت شهری و مدیریت پسماند": ["نظافت", "رفت و روب", "زباله", "پسماند", "جارو", "بازیافت"],
    "لایروبی انهار و مسیل‌ها": ["لایروبی", "مادی", "نهر", "کانال", "مسیل"],
    "آبرسانی و تاسیسات آبی": ["آبرسانی", "تانکر", "چاه", "قنات", "منبع آب"],
    "تاسیسات و مبلمان شهری": ["مبلمان", "نیمکت", "سطل", "تاسیسات شهری", "آذین بندی"],
    
    # Civil & Traffic
    "روکش و ترمیم آسفالت": ["آسفالت", "روکش", "لکه گیری", "قیر"],
    "پیاده‌روسازی و اصلاح معابر": ["پیاده رو", "سنگ فرش", "بلوک", "کف فرش", "زیرسازی معابر"],
    "جدول‌گذاری و کانیو": ["جدول", "کانیو", "آبراهه", "جدولگذاری"],
    "تجهیزات و علائم ترافیکی": ["ترافیک", "خط کشی", "تابلو", "سرعت گیر", "گاردریل", "چراغ راهنما"],
    "پل و تقاطع غیرهمسطح": ["پل", "زیرگذر", "روگذر", "تقاطع"],
    
    # Buildings & Facilities
    "روشنایی و نورپردازی": ["روشنایی", "نورپردازی", "برق", "لوستر", "چراغ"],
    "تعمیر و نگهداری ساختمان‌ها": ["ساختمان", "ابنیه", "تاسیسات ساختمان", "موتورخانه", "تعمیرات"],
    "احداث و بازسازی ابنیه": ["احداث", "بازسازی", "ساخت", "تکمیل"],
    
    # Admin & HR
    "پرداخت حقوق و مزایا": ["حقوق", "دستمزد", "مزایا", "کارانه", "فوق العاده"],
    "خدمات رفاهی و انگیزشی": ["رفاهی", "پاداش", "بن", "ورزشی", "هدیه", "بیمه تکمیلی"],
    "خرید ملزومات و تجهیزات": ["خرید", "تجهیزات", "ملزومات", "اثاثیه", "لوازم"],
    "خدمات چاپ و انتشارات": ["چاپ", "نشریات", "بنر", "انتشارات"],
    
    # Financial & Legal
    "پرداخت دیون و تعهدات": ["دیون", "انتقال وجوه", "بازپرداخت", "بدهی"],
    "تملک و آزادسازی اراضی": ["تملک", "آزادسازی", "مسیر", "عرصه", "زمین"],
    "پروژه‌های مشارکتی": ["مشارکت", "سرمایه گذاری", "سرمایه‌گذاری"],
    
    # Budget & Revenue (New)
    "مدیریت بودجه و اعتبارات": ["بودجه", "تخصیص", "موافقتنامه", "تفریغ", "اعتبار"],
    "وصول درآمد و عوارض": ["عوارض", "نوسازی", "کسب و پیشه", "درآمد", "وصول"],
    "اصفهان کارت": ["اصفهان کارت", "اصفهان‌کارت", "کارت شهروندی"],
}


# ============================================================
# TRUSTEE -> SUBSYSTEM MAPPING
# ============================================================

TRUSTEE_TO_SUBSYSTEM = {
    "معاونت خدمات": "CONTRACTORS",
    "خدمات شهری": "CONTRACTORS",
    "معاونت خدمات شهری": "CONTRACTORS",
    "معاونت فنی": "CONTRACTORS",
    "فنی عمرانی": "CONTRACTORS",
    "معاونت فنی و عمرانی": "CONTRACTORS",
    "شهرسازی": "URBAN_PLANNING",
    "معاونت شهرسازی": "URBAN_PLANNING",
    "معماری": "URBAN_PLANNING",
    "معاونت مالی": "TREASURY",
    "مالی": "TREASURY",
    "خزانه": "TREASURY",
    "برنامه ریزی": "BUDGET",
    "برنامه‌ریزی": "BUDGET",
    "امور اداری": "WAREHOUSE",
    "اداری": "WAREHOUSE",
    "درآمد": "REVENUE",
    "مشارکت": "INVESTMENT",
    "سرمایه گذاری": "INVESTMENT",
}


# ============================================================
# KEYWORD -> SUBSYSTEM MAPPING
# ============================================================

KEYWORD_TO_SUBSYSTEM = {
    "ISFAHAN_CARD": ["اصفهان کارت", "اصفهان‌کارت"],
    "WELFARE": ["رفاهی", "پاداش", "ورزشی", "بن کارت", "بیمه تکمیلی", "هدیه"],
    "PAYROLL": ["حقوق", "دستمزد", "مزایا", "کارانه", "فوق العاده"],
    "REAL_ESTATE": ["تملک", "آزادسازی", "مسیر گشایی", "اراضی", "ملک"],
    "TREASURY": ["دیون", "انتقال وجوه", "بانکی", "خزانه", "چک", "حواله"],
    "TADAROKAT": ["خرید", "ملزومات", "تجهیزات", "چاپ", "لوازم"],
    "INVESTMENT": ["مشارکت", "سرمایه گذاری"],
    "BUDGET": ["بودجه", "تخصیص", "موافقتنامه", "اعتبار"],
    "REVENUE": ["عوارض", "درآمد", "وصول", "نوسازی"],
    "CONTRACTORS": ["احداث", "تکمیل", "زیرسازی", "آسفالت", "جدول", "ساخت", "عمرانی",
                    "پیاده رو", "پل", "زیرگذر", "فضای سبز", "نظافت", "لایروبی"],
    "WAREHOUSE": ["انبار", "اموال", "کالا"],
}


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def clean_text(text) -> str:
    """Clean and normalize Persian text."""
    if pd.isna(text) or text is None:
        return ""
    text = str(text).strip()
    # Normalize Arabic characters to Persian
    text = text.replace("ي", "ی").replace("ك", "ک")
    return text


def find_column(df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
    """Find a column containing any of the keywords."""
    for col in df.columns:
        col_str = str(col).strip()
        for kw in keywords:
            if kw in col_str:
                return col
    return None


def contains_any(text: str, keywords: List[str]) -> bool:
    """Check if text contains any of the keywords."""
    if not text:
        return False
    return any(kw in text for kw in keywords)


def extract_prefix(text: str, num_words: int = 2) -> str:
    """Extract the first N words from text as a prefix."""
    # Remove noise patterns
    text = re.sub(r'\d+', '', text)  # Remove numbers
    text = re.sub(r'\(.*?\)', '', text)  # Remove parentheses content
    text = re.sub(r'[،,\-_:]', ' ', text)  # Replace punctuation with space
    
    words = text.split()
    if len(words) >= num_words:
        return ' '.join(words[:num_words])
    elif len(words) > 0:
        return ' '.join(words)
    return ""


def get_fallback_title(subsystem_code: str) -> str:
    """Generate fallback title for a subsystem."""
    persian_name = SUBSYSTEMS.get(subsystem_code, {}).get("persian_name", "سایر")
    return f"سایر خدمات {persian_name}"


# ============================================================
# LAYER 1: DICTIONARY MATCHING
# ============================================================

def match_dictionary(description: str) -> Optional[str]:
    """Layer 1: Check if description matches any keyword in CLEANING_MAP."""
    for clean_title, keywords in CLEANING_MAP.items():
        if contains_any(description, keywords):
            return clean_title
    return None


# ============================================================
# LAYER 2: COMMON PREFIX CLUSTERING
# ============================================================

def build_prefix_clusters(descriptions: List[str], min_size: int = 3) -> Dict[str, str]:
    """
    Build clusters from common prefixes.
    Returns a mapping: raw_description -> cluster_title
    """
    # Count prefix occurrences
    prefix_counter = Counter()
    desc_to_prefix = {}
    
    for desc in descriptions:
        prefix = extract_prefix(desc, num_words=MIN_PREFIX_WORDS)
        if prefix and len(prefix) >= 5:  # Minimum prefix length
            prefix_counter[prefix] += 1
            desc_to_prefix[desc] = prefix
    
    # Find valid clusters (prefixes appearing >= min_size times)
    valid_clusters = {prefix for prefix, count in prefix_counter.items() if count >= min_size}
    
    # Map descriptions to their cluster title
    cluster_mapping = {}
    for desc, prefix in desc_to_prefix.items():
        if prefix in valid_clusters:
            cluster_mapping[desc] = prefix
    
    return cluster_mapping


# ============================================================
# SUBSYSTEM CLASSIFICATION
# ============================================================

def classify_to_subsystem(row_data: dict, is_capital: bool) -> str:
    """Classify a row to a subsystem using waterfall logic."""
    trustee = row_data.get('trustee', '')
    subject = row_data.get('subject', '')
    description = row_data.get('description', '')
    
    # Level 1: Trustee Check
    for trustee_pattern, subsystem in TRUSTEE_TO_SUBSYSTEM.items():
        if trustee_pattern in trustee:
            return subsystem
    
    # Level 2: Subject Check (for Payroll)
    if contains_any(subject, KEYWORD_TO_SUBSYSTEM.get("PAYROLL", [])):
        return "PAYROLL"
    
    # Level 3: Description Keywords
    for subsystem, patterns in KEYWORD_TO_SUBSYSTEM.items():
        if subsystem == "CONTRACTORS" and not is_capital:
            continue
        if contains_any(description, patterns):
            return subsystem
    
    # Level 4: Fallback
    return "CONTRACTORS" if is_capital else "OTHER"


# ============================================================
# DATA LOADING
# ============================================================

def load_excel_with_budget_type(filepath: str, budget_type: str, 
                                 filter_continuous: bool = False) -> List[dict]:
    """Load Excel file and tag all rows with budget type."""
    try:
        df = pd.read_excel(filepath, engine='openpyxl')
        print(f"   ✅ Loaded: {filepath} ({len(df):,} rows)")
    except Exception as e:
        print(f"   ❌ Error loading {filepath}: {e}")
        return []
    
    # Find columns
    desc_col = find_column(df, ['شرح ردیف', 'شرح'])
    trustee_col = find_column(df, ['متولی', 'متولي'])
    subject_col = find_column(df, ['موضوع', 'زیر موضوع'])
    row_type_col = find_column(df, ['نوع ردیف'])
    
    if not desc_col:
        print(f"   ⚠️  No description column found!")
        return []
    
    # Filter for continuous rows if needed
    if filter_continuous and row_type_col:
        df = df[df[row_type_col].astype(str).str.contains('مستمر', na=False)]
        print(f"   🔄 Filtered to 'مستمر': {len(df):,} rows")
    
    # Process rows
    rows = []
    for _, row in df.iterrows():
        desc = clean_text(row.get(desc_col, ''))
        if not desc:
            continue
        
        rows.append({
            'description': desc,
            'trustee': clean_text(row.get(trustee_col, '')) if trustee_col else '',
            'subject': clean_text(row.get(subject_col, '')) if subject_col else '',
            'budget_type': budget_type
        })
    
    return rows


# ============================================================
# THREE-LAYER PROCESSING PIPELINE
# ============================================================

def process_with_three_layers(all_rows: List[dict]) -> Dict[str, Dict[str, Set[str]]]:
    """
    Process all rows through the three-layer pipeline.
    Returns: {subsystem: {budget_type: set(activity_titles)}}
    """
    # Group rows by subsystem first
    subsystem_rows = defaultdict(list)
    
    for row in all_rows:
        is_capital = row['budget_type'] == 'capital'
        subsystem = classify_to_subsystem(row, is_capital)
        subsystem_rows[subsystem].append(row)
    
    # Results: {subsystem: {budget_type: set(titles)}}
    results = defaultdict(lambda: defaultdict(set))
    
    # Stats
    stats = {'layer1': 0, 'layer2': 0, 'layer3': 0}
    
    for subsystem, rows in subsystem_rows.items():
        # Separate by budget type
        capital_rows = [r for r in rows if r['budget_type'] == 'capital']
        expense_rows = [r for r in rows if r['budget_type'] == 'expense']
        
        for budget_type, budget_rows in [('capital', capital_rows), ('expense', expense_rows)]:
            if not budget_rows:
                continue
            
            # Rows not matched by Layer 1
            unmatched_descriptions = []
            
            for row in budget_rows:
                desc = row['description']
                
                # LAYER 1: Dictionary Match
                dict_title = match_dictionary(desc)
                if dict_title:
                    results[subsystem][budget_type].add(dict_title)
                    stats['layer1'] += 1
                else:
                    unmatched_descriptions.append(desc)
            
            # LAYER 2: Common Prefix Clustering (on unmatched)
            if unmatched_descriptions:
                cluster_mapping = build_prefix_clusters(unmatched_descriptions, MIN_CLUSTER_SIZE)
                
                for desc in unmatched_descriptions:
                    if desc in cluster_mapping:
                        # Use cluster title (prefix)
                        results[subsystem][budget_type].add(cluster_mapping[desc])
                        stats['layer2'] += 1
                    else:
                        # LAYER 3: Strict Fallback
                        fallback = get_fallback_title(subsystem)
                        results[subsystem][budget_type].add(fallback)
                        stats['layer3'] += 1
    
    print(f"\n📊 Layer Statistics:")
    print(f"   Layer 1 (Dictionary): {stats['layer1']:,} matches")
    print(f"   Layer 2 (Clustering): {stats['layer2']:,} matches")
    print(f"   Layer 3 (Fallback):   {stats['layer3']:,} fallbacks")
    
    return results


# ============================================================
# JSON GENERATION
# ============================================================

def build_activity(subsystem_code: str, title: str, index: int, budget_type: str) -> dict:
    """Build activity JSON with proper budget type constraint."""
    return {
        "code": f"{subsystem_code}_{index:02d}",
        "title": title,
        "form_type": None,
        "frequency": "MONTHLY",
        "requires_file_upload": False,
        "external_service_url": None,
        "order": index,
        "is_active": True,
        "constraints": [
            {
                "budget_code_pattern": None,
                "allowed_budget_types": [budget_type],
                "cost_center_pattern": None,
                "allowed_cost_centers": None,
                "constraint_type": "INCLUDE",
                "priority": 1,
                "description": f"فقط ردیف‌های بودجه {'سرمایه‌ای' if budget_type == 'capital' else 'هزینه‌ای'}"
            }
        ]
    }


def build_subsystem(code: str, activities_by_budget: Dict[str, Set[str]]) -> dict:
    """Build subsystem JSON with activities."""
    subsystem_def = SUBSYSTEMS.get(code, SUBSYSTEMS["OTHER"])
    
    activities = []
    idx = 1
    seen = set()
    
    # Add expense activities first
    for title in sorted(activities_by_budget.get('expense', set())):
        if title not in seen:
            activities.append(build_activity(code, title, idx, 'expense'))
            seen.add(title)
            idx += 1
    
    # Add capital activities
    for title in sorted(activities_by_budget.get('capital', set())):
        if title not in seen:
            activities.append(build_activity(code, title, idx, 'capital'))
            seen.add(title)
            idx += 1
    
    return {
        "code": subsystem_def["code"],
        "title": subsystem_def["title"],
        "icon": subsystem_def["icon"],
        "attachment_type": subsystem_def["attachment_type"],
        "order": subsystem_def["order"],
        "is_active": len(activities) > 0,
        "activities": activities
    }


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("📊 CONFIG GENERATOR V6 - COMMON PREFIX CLUSTERING")
    print("=" * 70)
    print()
    print("Three-Layer Pipeline:")
    print("  Layer 1: Golden Dictionary (CLEANING_MAP)")
    print("  Layer 2: Common Prefix Clustering (min 3 occurrences)")
    print("  Layer 3: Strict Fallback (سایر خدمات [Subsystem])")
    print()
    
    # Load data with budget type tagging
    print("📁 Loading Excel files...")
    capital_rows = load_excel_with_budget_type(INPUT_CAPITAL, 'capital', filter_continuous=True)
    expense_rows = load_excel_with_budget_type(INPUT_EXPENSE, 'expense', filter_continuous=False)
    
    all_rows = capital_rows + expense_rows
    print(f"\n   Total rows to process: {len(all_rows):,}")
    
    # Process through three layers
    print("\n🔄 Processing through Three-Layer Pipeline...")
    results = process_with_three_layers(all_rows)
    
    # Build JSON structure
    print("\n🔨 Building JSON structure...")
    subsystems_json = []
    
    for code in sorted(SUBSYSTEMS.keys(), key=lambda x: SUBSYSTEMS[x]["order"]):
        activities_by_budget = results.get(code, {})
        if activities_by_budget:
            subsystems_json.append(build_subsystem(code, activities_by_budget))
    
    # Create final config
    config = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "version": "6.0.0",
        "generated_at": datetime.now().isoformat(),
        "description": "Config V6 - Three-layer cleaning with Common Prefix Clustering",
        "subsystems": subsystems_json
    }
    
    # Save to file
    import os
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    # Summary
    total_activities = sum(len(s['activities']) for s in config['subsystems'])
    
    print("\n" + "=" * 70)
    print("📋 SUMMARY")
    print("=" * 70)
    print(f"   Output File: {OUTPUT_FILE}")
    print(f"   Total Subsystems: {len(config['subsystems'])}")
    print(f"   Total Activities: {total_activities}")
    print()
    print("   Per Subsystem:")
    for s in config['subsystems']:
        print(f"   • {s['title']}: {len(s['activities'])} activities")
    
    print("\n✅ Config V6 generated successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
