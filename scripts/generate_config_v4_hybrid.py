"""
Master Config Generator V4 - Hybrid Approach
==============================================
Generates app/config/config_master.json from Excel budget files.

Key Features:
- Maps rows to the EXACT 13 Subsystems (no grouping)
- Uses CLEANING_MAP dictionary to avoid garbage titles
- Falls back to "سایر خدمات [Subsystem]" if no keyword match

Inputs:
1. `تملک دارایی سرمایه ای.xlsx` - Capital Budget (filter: نوع ردیف == مستمر)
2. `اعتبارات هزینه ای.xlsx` - Expense Budget (process all)

Usage:
    python scripts/generate_config_v4_hybrid.py
"""

import pandas as pd
import json
import os
from collections import defaultdict
from typing import Optional, List, Dict, Set
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

# Input files
EXPENSE_BUDGET_FILE = "اعتبارات هزینه ای.xlsx"
CAPITAL_BUDGET_FILE = "تملک دارایی سرمایه ای.xlsx"

# Output file
OUTPUT_FILE = "app/config/config_master.json"


# ============================================================
# THE 13 SUBSYSTEMS DEFINITION (STRICT - DO NOT GROUP)
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
# CLEANING DICTIONARY - For Activity Title Standardization
# Key = Clean Title to use, Value = List of keywords to search
# ============================================================

CLEANING_MAP = {
    # Urban & Services
    "نگهداری و توسعه فضای سبز": ["فضای سبز", "پارک", "درخت", "گیاه", "آبیاری", "چمن"],
    "نظافت شهری و مدیریت پسماند": ["نظافت", "رفت و روب", "زباله", "پسماند", "جارو"],
    "لایروبی انهار و مسیل‌ها": ["لایروبی", "مادی", "نهر", "کانال"],
    "آبرسانی و تاسیسات آبی": ["آبرسانی", "تانکر", "چاه", "قنات", "منبع آب"],
    
    # Civil & Traffic
    "روکش و ترمیم آسفالت": ["آسفالت", "روکش", "لکه گیری", "قیر"],
    "پیاده‌روسازی و اصلاح معابر": ["پیاده رو", "سنگ فرش", "بلوک", "کف فرش", "زیرسازی"],
    "جدول‌گذاری و کانیو": ["جدول", "کانیو", "آبراهه"],
    "تجهیزات و علائم ترافیکی": ["ترافیک", "خط کشی", "تابلو", "سرعت گیر", "گاردریل"],
    
    # Buildings & Facilities
    "روشنایی و نورپردازی": ["روشنایی", "نورپردازی", "برق", "لوستر"],
    "تعمیر و نگهداری ساختمان‌ها": ["ساختمان", "ابنیه", "اداری", "تاسیسات ساختمان", "موتورخانه"],
    
    # Admin & HR
    "پرداخت حقوق و مزایا": ["حقوق", "دستمزد", "مزایا", "کارانه"],
    "خدمات رفاهی و انگیزشی": ["رفاهی", "پاداش", "بن", "ورزشی", "هدیه"],
    "خرید ملزومات و تجهیزات": ["خرید", "تجهیزات", "ملزومات", "اثاثیه"],
    "خدمات چاپ و انتشارات": ["چاپ", "نشریات", "بنر"],
    
    # Financial & Legal
    "پرداخت دیون و تعهدات": ["دیون", "انتقال وجوه", "بازپرداخت"],
    "تملک و آزادسازی اراضی": ["تملک", "آزادسازی", "مسیر", "عرصه"],
    "پروژه‌های مشارکتی": ["مشارکت", "سرمایه گذاری"],
    
    # Additional patterns for broader coverage
    "احداث و توسعه": ["احداث", "توسعه", "ساخت", "تکمیل"],
    "پل و تقاطع": ["پل", "زیرگذر", "روگذر", "تقاطع"],
    "خدمات شهری": ["خدمات شهری", "خدمات عمومی"],
    "امور مالی و اعتباری": ["اعتبار", "مالی", "بانکی"],
    "اصفهان کارت": ["اصفهان کارت", "اصفهان‌کارت", "کارت شهروندی"],
}


# ============================================================
# TRUSTEE -> SUBSYSTEM MAPPING
# Maps Trustee column values to subsystems
# ============================================================

TRUSTEE_TO_SUBSYSTEM = {
    # معاونت خدمات شهری -> CONTRACTORS (typically civil works contractors)
    "معاونت خدمات": "CONTRACTORS",
    "خدمات شهری": "CONTRACTORS",
    "معاونت خدمات شهری": "CONTRACTORS",
    
    # معاونت فنی عمرانی -> CONTRACTORS
    "معاونت فنی": "CONTRACTORS",
    "فنی عمرانی": "CONTRACTORS",
    "معاونت فنی و عمرانی": "CONTRACTORS",
    
    # معاونت شهرسازی -> URBAN_PLANNING
    "شهرسازی": "URBAN_PLANNING",
    "معاونت شهرسازی": "URBAN_PLANNING",
    "معماری": "URBAN_PLANNING",
    
    # معاونت مالی -> TREASURY/BUDGET
    "معاونت مالی": "TREASURY",
    "مالی": "TREASURY",
    "خزانه": "TREASURY",
    
    # برنامه ریزی -> BUDGET
    "برنامه ریزی": "BUDGET",
    "برنامه‌ریزی": "BUDGET",
    
    # امور اداری -> WAREHOUSE (for admin/assets)
    "امور اداری": "WAREHOUSE",
    "اداری": "WAREHOUSE",
    
    # درآمد -> REVENUE
    "درآمد": "REVENUE",
    
    # مشارکت -> INVESTMENT
    "مشارکت": "INVESTMENT",
    "سرمایه گذاری": "INVESTMENT",
}


# ============================================================
# KEYWORD -> SUBSYSTEM MAPPING
# For description-based classification
# ============================================================

KEYWORD_TO_SUBSYSTEM = {
    # ISFAHAN_CARD - Specific keywords
    "ISFAHAN_CARD": ["اصفهان کارت", "اصفهان‌کارت", "کارت شهروندی"],
    
    # WELFARE - Employee benefits
    "WELFARE": ["رفاهی", "پاداش", "ورزشی", "بن کارت", "بن غیر نقدی", "بیمه تکمیلی",
                "کمک هزینه", "مساعدت", "سفر", "تفریح", "جشن", "مناسبت", "هدیه"],
    
    # PAYROLL - Salary related (from Subject column primarily)
    "PAYROLL": ["حقوق", "دستمزد", "مزایا", "کارانه", "فوق العاده", "اضافه کاری"],
    
    # REAL_ESTATE - Land/property acquisition
    "REAL_ESTATE": ["تملک", "آزادسازی", "مسیر گشایی", "اراضی", "ملک", "عرصه"],
    
    # TREASURY - Financial transactions
    "TREASURY": ["دیون", "انتقال وجوه", "بانکی", "خزانه", "چک", "حواله", "بازپرداخت"],
    
    # TADAROKAT - Procurement
    "TADAROKAT": ["خرید", "ملزومات", "تجهیزات", "چاپ", "لوازم", "مواد مصرفی", "اثاثیه"],
    
    # INVESTMENT - Partnerships
    "INVESTMENT": ["مشارکت", "سرمایه گذاری", "سرمایه‌گذاری"],
    
    # CONTRACTORS - Civil works (capital budget)
    "CONTRACTORS": ["احداث", "تکمیل", "زیرسازی", "آسفالت", "جدول", "ساخت", "عمرانی",
                    "پیاده رو", "پل", "زیرگذر", "فضای سبز", "نظافت", "لایروبی"],
    
    # WAREHOUSE - Assets and inventory
    "WAREHOUSE": ["تعمیرات اساسی", "نگهداری اموال", "اموال", "انبار"],
}


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def clean_text(text) -> str:
    """Clean and normalize text."""
    if pd.isna(text) or text is None:
        return ""
    return str(text).strip()


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


def get_clean_title(description: str) -> Optional[str]:
    """
    Use CLEANING_MAP to get a clean title from description.
    Returns None if no keyword matches (will trigger fallback).
    """
    for clean_title, keywords in CLEANING_MAP.items():
        if contains_any(description, keywords):
            return clean_title
    return None


def get_fallback_title(subsystem_code: str) -> str:
    """Generate fallback title for a subsystem when no keyword matches."""
    persian_name = SUBSYSTEMS.get(subsystem_code, {}).get("persian_name", "سایر")
    return f"سایر خدمات {persian_name}"


# ============================================================
# SUBSYSTEM CLASSIFICATION (Waterfall Logic)
# ============================================================

def classify_row_to_subsystem(row_data: dict, is_capital: bool) -> str:
    """
    Classify a row to a subsystem using waterfall logic.
    
    Priority:
    1. Trustee (متولی) -> Direct mapping
    2. Subject (موضوع) -> For Payroll
    3. Description keywords -> For specific systems
    4. Default fallback based on budget type
    """
    trustee = row_data.get('trustee', '')
    subject = row_data.get('subject', '')
    description = row_data.get('description', '')
    
    # Level 1: Trustee Check (Strongest Signal)
    for trustee_pattern, subsystem in TRUSTEE_TO_SUBSYSTEM.items():
        if trustee_pattern in trustee:
            return subsystem
    
    # Level 2: Subject Check (specifically for Payroll)
    if contains_any(subject, KEYWORD_TO_SUBSYSTEM.get("PAYROLL", [])):
        return "PAYROLL"
    
    # Level 3: Description Keyword Mining
    for subsystem, patterns in KEYWORD_TO_SUBSYSTEM.items():
        # CONTRACTORS keywords only apply to capital budget
        if subsystem == "CONTRACTORS" and not is_capital:
            continue
        if contains_any(description, patterns):
            return subsystem
    
    # Level 4: Default Fallback
    if is_capital:
        return "CONTRACTS"  # Default for remaining capital projects
    else:
        return "OTHER"


# ============================================================
# DATA LOADING AND PROCESSING
# ============================================================

def load_expense_budget() -> Optional[pd.DataFrame]:
    """Load expense budget Excel file - Process ALL rows."""
    if not os.path.exists(EXPENSE_BUDGET_FILE):
        print(f"   ⚠️  File not found: {EXPENSE_BUDGET_FILE}")
        return None
    
    try:
        df = pd.read_excel(EXPENSE_BUDGET_FILE, engine='openpyxl')
        print(f"   ✅ Loaded: {EXPENSE_BUDGET_FILE} ({len(df):,} rows)")
        return df
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def load_capital_budget() -> Optional[pd.DataFrame]:
    """Load capital budget Excel file - Filter to 'مستمر' rows only."""
    if not os.path.exists(CAPITAL_BUDGET_FILE):
        print(f"   ⚠️  File not found: {CAPITAL_BUDGET_FILE}")
        return None
    
    try:
        df = pd.read_excel(CAPITAL_BUDGET_FILE, engine='openpyxl')
        print(f"   ✅ Loaded: {CAPITAL_BUDGET_FILE} ({len(df):,} total rows)")
        
        # Filter to continuous rows only (نوع ردیف = مستمر)
        row_type_col = find_column(df, ['نوع ردیف'])
        if row_type_col:
            df_filtered = df[df[row_type_col].astype(str).str.contains('مستمر', na=False)]
            print(f"   🔄 Filtered to 'مستمر' rows: {len(df_filtered):,} rows")
            return df_filtered
        else:
            print(f"   ⚠️  No 'نوع ردیف' column found, using all rows")
            return df
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def process_dataframe(df: pd.DataFrame, is_capital: bool) -> Dict[str, Set[str]]:
    """
    Process DataFrame and extract CLEAN activities per subsystem.
    Uses CLEANING_MAP to avoid garbage titles.
    Uses deduplication via Set.
    """
    
    # Find relevant columns
    desc_col = find_column(df, ['شرح ردیف', 'شرح'])
    trustee_col = find_column(df, ['متولی', 'متولي'])
    subject_col = find_column(df, ['موضوع'])
    
    if not desc_col:
        print(f"   ⚠️  No description column found!")
        return {}
    
    print(f"   📊 Found columns: desc={desc_col}, trustee={trustee_col}, subject={subject_col}")
    
    # Use sets for deduplication per subsystem
    subsystem_activities: Dict[str, Set[str]] = defaultdict(set)
    
    # Track statistics
    stats = {
        'total_rows': 0,
        'clean_matches': 0,
        'fallback_used': 0
    }
    
    for _, row in df.iterrows():
        row_data = {
            'description': clean_text(row.get(desc_col, '')),
            'trustee': clean_text(row.get(trustee_col, '')) if trustee_col else '',
            'subject': clean_text(row.get(subject_col, '')) if subject_col else ''
        }
        
        if not row_data['description']:
            continue
        
        stats['total_rows'] += 1
        
        # Step 1: Classify to subsystem
        subsystem = classify_row_to_subsystem(row_data, is_capital)
        
        # Step 2: Get clean title using CLEANING_MAP
        clean_title = get_clean_title(row_data['description'])
        
        if clean_title:
            # Matched a keyword -> Use the dictionary key as title
            stats['clean_matches'] += 1
            subsystem_activities[subsystem].add(clean_title)
        else:
            # CRITICAL FALLBACK: No keyword matched -> Use generic fallback
            # DO NOT use raw text (avoids garbage data)
            stats['fallback_used'] += 1
            fallback_title = get_fallback_title(subsystem)
            subsystem_activities[subsystem].add(fallback_title)
    
    # Print statistics
    print(f"   📈 Processed: {stats['total_rows']} rows")
    print(f"   ✅ Clean matches: {stats['clean_matches']}")
    print(f"   🔄 Fallbacks used: {stats['fallback_used']}")
    
    return subsystem_activities


# ============================================================
# JSON GENERATION
# ============================================================

def build_activity_json(subsystem_code: str, title: str, index: int, budget_type: str) -> dict:
    """Build a single activity JSON object."""
    # Generate code as SUBSYSTEM_XX format
    code = f"{subsystem_code}_{index:02d}"
    
    return {
        "code": code,
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


def build_subsystem_json(subsystem_code: str, 
                          expense_activities: Set[str], 
                          capital_activities: Set[str]) -> dict:
    """Build a single subsystem JSON object with merged activities."""
    
    subsystem_def = SUBSYSTEMS.get(subsystem_code, SUBSYSTEMS["OTHER"])
    
    activities = []
    seen_titles = set()
    activity_index = 1
    
    # Add expense activities first
    for title in sorted(expense_activities):
        if title not in seen_titles:
            activities.append(build_activity_json(subsystem_code, title, activity_index, "expense"))
            seen_titles.add(title)
            activity_index += 1
    
    # Add capital activities
    for title in sorted(capital_activities):
        if title not in seen_titles:
            activities.append(build_activity_json(subsystem_code, title, activity_index, "capital"))
            seen_titles.add(title)
            activity_index += 1
    
    return {
        "code": subsystem_def["code"],
        "title": subsystem_def["title"],
        "icon": subsystem_def["icon"],
        "attachment_type": subsystem_def["attachment_type"],
        "order": subsystem_def["order"],
        "is_active": len(activities) > 0,
        "activities": activities
    }


def generate_master_config() -> dict:
    """Generate the complete master config JSON."""
    
    print("=" * 70)
    print("📊 MASTER CONFIG GENERATOR V4 - HYBRID APPROACH")
    print("=" * 70)
    print()
    print("Key Features:")
    print("  • Strict 13 Subsystems (no grouping)")
    print("  • Dictionary-based title cleaning (CLEANING_MAP)")
    print("  • Fallback titles to avoid garbage data")
    print("  • Deduplication via Sets")
    print()
    
    # Load data
    print("📁 Loading Excel files...")
    expense_df = load_expense_budget()
    capital_df = load_capital_budget()
    print()
    
    # Process data
    print("🔄 Processing Expense Budget...")
    expense_activities = process_dataframe(expense_df, is_capital=False) if expense_df is not None else {}
    print()
    
    print("🔄 Processing Capital Budget...")
    capital_activities = process_dataframe(capital_df, is_capital=True) if capital_df is not None else {}
    print()
    
    # Print summary
    print("📋 Activities per Subsystem:")
    print("-" * 60)
    print(f"{'Subsystem':<40} | {'Expense':>8} | {'Capital':>8}")
    print("-" * 60)
    
    for subsystem_code in sorted(SUBSYSTEMS.keys(), key=lambda x: SUBSYSTEMS[x]["order"]):
        expense_count = len(expense_activities.get(subsystem_code, set()))
        capital_count = len(capital_activities.get(subsystem_code, set()))
        if expense_count > 0 or capital_count > 0:
            title = SUBSYSTEMS[subsystem_code]['title']
            print(f"{title:<40} | {expense_count:>8} | {capital_count:>8}")
    print("-" * 60)
    print()
    
    # Build final JSON
    print("🔨 Building JSON structure...")
    subsystems_json = []
    
    for subsystem_code in sorted(SUBSYSTEMS.keys(), key=lambda x: SUBSYSTEMS[x]["order"]):
        expense_acts = expense_activities.get(subsystem_code, set())
        capital_acts = capital_activities.get(subsystem_code, set())
        
        # Only include subsystems with activities
        if expense_acts or capital_acts:
            subsystems_json.append(
                build_subsystem_json(subsystem_code, expense_acts, capital_acts)
            )
    
    # Final config structure
    config = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "version": "4.0.0",
        "generated_at": datetime.now().isoformat(),
        "description": "Master config V4 - Hybrid approach with strict 13 subsystems and dictionary-based cleaning",
        "subsystems": subsystems_json
    }
    
    return config


def save_config(config: dict):
    """Save config to JSON file."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Saved to: {OUTPUT_FILE}")
    print(f"   Total subsystems: {len(config['subsystems'])}")
    total_activities = sum(len(s['activities']) for s in config['subsystems'])
    print(f"   Total activities: {total_activities}")


# ============================================================
# MAIN
# ============================================================

def main():
    """Main entry point."""
    config = generate_master_config()
    save_config(config)
    print("\n" + "=" * 70)
    print("🎉 Complete! Review the generated config file.")
    print("=" * 70)


if __name__ == "__main__":
    main()
