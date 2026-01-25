"""
Master Config Generator V2
===========================
Generates app/config/config_master.json from Excel budget files.
Maps budget rows to 13 Subsystems using waterfall logic.

Usage:
    python scripts/generate_master_config_v2.py
"""

import pandas as pd
import json
import os
import re
from collections import Counter, defaultdict
from typing import Optional, List, Dict, Tuple
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

# Input files
EXPENSE_BUDGET_FILE = "اعتبارات هزینه ای.xlsx"
CAPITAL_BUDGET_FILE = "تملک دارایی سرمایه ای.xlsx"

# Output file
OUTPUT_FILE = "app/config/config_master.json"

# Maximum activities per subsystem (to avoid UI clutter)
MAX_ACTIVITIES_PER_SUBSYSTEM = 10

# ============================================================
# THE 13 SUBSYSTEMS DEFINITION
# ============================================================

SUBSYSTEMS = {
    "URBAN_PLANNING": {
        "code": "URBAN_PLANNING",
        "title": "سامانه شهرسازی",
        "icon": "Building2",
        "attachment_type": "both",
        "order": 1
    },
    "CONTRACTS": {
        "code": "CONTRACTS",
        "title": "سامانه امور قراردادها",
        "icon": "FileText",
        "attachment_type": "both",
        "order": 2
    },
    "PAYROLL": {
        "code": "PAYROLL",
        "title": "سامانه حقوق و دستمزد",
        "icon": "Users",
        "attachment_type": "api",
        "order": 3
    },
    "TADAROKAT": {
        "code": "TADAROKAT",
        "title": "سامانه تدارکات",
        "icon": "ShoppingCart",
        "attachment_type": "upload",
        "order": 4
    },
    "BUDGET": {
        "code": "BUDGET",
        "title": "سامانه بودجه",
        "icon": "BarChart3",
        "attachment_type": "none",
        "order": 5
    },
    "TREASURY": {
        "code": "TREASURY",
        "title": "سامانه خزانه‌داری",
        "icon": "Vault",
        "attachment_type": "upload",
        "order": 6
    },
    "CONTRACTORS": {
        "code": "CONTRACTORS",
        "title": "سامانه امور پیمانکاران",
        "icon": "HardHat",
        "attachment_type": "both",
        "order": 7
    },
    "WELFARE": {
        "code": "WELFARE",
        "title": "سامانه رفاه کارکنان",
        "icon": "Heart",
        "attachment_type": "upload",
        "order": 8
    },
    "REAL_ESTATE": {
        "code": "REAL_ESTATE",
        "title": "سامانه املاک",
        "icon": "Home",
        "attachment_type": "both",
        "order": 9
    },
    "WAREHOUSE": {
        "code": "WAREHOUSE",
        "title": "سامانه انبار و اموال",
        "icon": "Package",
        "attachment_type": "upload",
        "order": 10
    },
    "REVENUE": {
        "code": "REVENUE",
        "title": "سامانه درآمد",
        "icon": "TrendingUp",
        "attachment_type": "api",
        "order": 11
    },
    "ISFAHAN_CARD": {
        "code": "ISFAHAN_CARD",
        "title": "سامانه اصفهان کارت",
        "icon": "CreditCard",
        "attachment_type": "api",
        "order": 12
    },
    "INVESTMENT": {
        "code": "INVESTMENT",
        "title": "سامانه مشارکت‌ها و سرمایه‌گذاری",
        "icon": "Handshake",
        "attachment_type": "both",
        "order": 13
    },
    "OTHER": {
        "code": "OTHER",
        "title": "سایر / عمومی",
        "icon": "MoreHorizontal",
        "attachment_type": "upload",
        "order": 14
    }
}

# ============================================================
# KEYWORD MAPPING FOR WATERFALL LOGIC
# ============================================================

# Level 1: Trustee patterns (strongest signal)
TRUSTEE_PATTERNS = {
    "URBAN_PLANNING": ["شهرسازی", "معماری", "شهر سازي", "معماري"],
    "BUDGET": ["برنامه ريزي", "برنامه‌ریزی"],
    "INVESTMENT": ["مشارکت", "سرمایه گذار"]
}

# Level 2: Subject (موضوع) patterns
SUBJECT_PATTERNS = {
    "PAYROLL": ["حقوق", "دستمزد", "جبران خدمات"]
}

# Level 3: Description keyword patterns
DESCRIPTION_PATTERNS = {
    "ISFAHAN_CARD": ["اصفهان کارت", "اصفهان‌کارت"],
    "WELFARE": ["رفاهی", "پاداش", "ورزشی", "بن کارت", "بن غیر نقدی", "بیمه تکمیلی", 
                "کمک هزینه", "مساعدت", "سفر", "تفریح", "جشن", "مناسبت"],
    "REAL_ESTATE": ["تملک", "آزادسازی", "مسیر", "اراضی", "ملک", "آزاد سازی"],
    "WAREHOUSE": ["تعمیرات اساسی", "نگهداری اموال", "اثاثیه", "تجهیزات اداری", "اموال"],
    "TREASURY": ["دیون", "انتقال وجوه", "بانکی", "خزانه", "چک", "حواله"],
    "TADAROKAT": ["خرید", "ملزومات", "تجهیزات", "چاپ", "لوازم", "مواد مصرفی"],
    "INVESTMENT": ["مشارکت", "سرمایه گذاری", "سرمایه‌گذاری"],
    "PAYROLL": ["حقوق", "دستمزد", "مزایا", "فوق العاده", "اضافه کاری", "مامورین"],
    # Capital-specific (for CONTRACTORS)
    "CONTRACTORS": ["احداث", "تکمیل", "زیرسازی", "آسفالت", "جدول", "ساخت", "عمرانی"]
}

# Prefixes to remove from activity titles
TITLE_PREFIXES_TO_REMOVE = [
    "پروژه", "عملیات", "اجرای", "اجرا", "انجام", "برنامه", "طرح",
    "هزینه", "پرداخت", "واگذاری", "خدمات"
]

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


def clean_activity_title(title: str) -> str:
    """Remove prefixes and clean up activity title."""
    result = title
    for prefix in TITLE_PREFIXES_TO_REMOVE:
        result = re.sub(rf'^{prefix}\s+', '', result)
        result = re.sub(rf'\s+{prefix}\s+', ' ', result)
    
    # Clean up extra spaces and trim
    result = re.sub(r'\s+', ' ', result).strip()
    
    # Limit length
    if len(result) > 50:
        result = result[:47] + "..."
    
    return result if result else title


def generate_activity_code(title: str, index: int) -> str:
    """Generate a unique activity code from title."""
    # Create a simple code from title keywords
    words = title.split()[:3]  # First 3 words
    code_parts = []
    for word in words:
        # Keep first 3 characters of each word
        if len(word) > 0:
            code_parts.append(word[:3].upper())
    
    base_code = "_".join(code_parts) if code_parts else "ACT"
    return f"{base_code}_{index:02d}"


def contains_any(text: str, keywords: List[str]) -> bool:
    """Check if text contains any of the keywords."""
    text_lower = text.lower()
    return any(kw in text_lower or kw in text for kw in keywords)


# ============================================================
# SUBSYSTEM CLASSIFICATION (Waterfall Logic)
# ============================================================

def classify_row(row: dict, is_capital: bool) -> str:
    """
    Classify a row to a subsystem using waterfall logic.
    Returns the subsystem code.
    """
    trustee = clean_text(row.get('trustee', ''))
    subject = clean_text(row.get('subject', ''))
    description = clean_text(row.get('description', ''))
    
    # Level 1: Trustee Check (Strongest Signal)
    for subsystem, patterns in TRUSTEE_PATTERNS.items():
        if contains_any(trustee, patterns):
            return subsystem
    
    # Level 2: Subject Check
    for subsystem, patterns in SUBJECT_PATTERNS.items():
        if contains_any(subject, patterns):
            return subsystem
    
    # Level 3: Description Keyword Mining
    for subsystem, patterns in DESCRIPTION_PATTERNS.items():
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
    """Load expense budget Excel file."""
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
    """Load capital budget Excel file and filter to continuous rows."""
    if not os.path.exists(CAPITAL_BUDGET_FILE):
        print(f"   ⚠️  File not found: {CAPITAL_BUDGET_FILE}")
        return None
    
    try:
        df = pd.read_excel(CAPITAL_BUDGET_FILE, engine='openpyxl')
        print(f"   ✅ Loaded: {CAPITAL_BUDGET_FILE} ({len(df):,} rows)")
        
        # Filter to continuous rows only (نوع ردیف = مستمر)
        row_type_col = find_column(df, ['نوع ردیف'])
        if row_type_col:
            df_filtered = df[df[row_type_col].astype(str).str.contains('مستمر', na=False)]
            print(f"   🔄 Filtered to continuous rows: {len(df_filtered):,} rows")
            return df_filtered
        else:
            print(f"   ⚠️  No 'نوع ردیف' column found, using all rows")
            return df
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def process_dataframe(df: pd.DataFrame, is_capital: bool) -> Dict[str, List[dict]]:
    """Process DataFrame and group activities by subsystem."""
    
    # Find relevant columns
    desc_col = find_column(df, ['شرح ردیف', 'شرح'])
    trustee_col = find_column(df, ['متولی', 'متولي'])
    subject_col = find_column(df, ['موضوع'])
    
    if not desc_col:
        print(f"   ⚠️  No description column found!")
        return {}
    
    # Group activities by subsystem
    subsystem_activities = defaultdict(Counter)
    
    for _, row in df.iterrows():
        row_data = {
            'description': clean_text(row.get(desc_col, '')),
            'trustee': clean_text(row.get(trustee_col, '')) if trustee_col else '',
            'subject': clean_text(row.get(subject_col, '')) if subject_col else ''
        }
        
        if not row_data['description']:
            continue
        
        # Classify row
        subsystem = classify_row(row_data, is_capital)
        
        # Clean the activity title
        activity_title = clean_activity_title(row_data['description'])
        
        if activity_title:
            subsystem_activities[subsystem][activity_title] += 1
    
    # Convert to list of dicts with top activities
    result = {}
    for subsystem, counter in subsystem_activities.items():
        result[subsystem] = [
            {"title": title, "count": count}
            for title, count in counter.most_common(MAX_ACTIVITIES_PER_SUBSYSTEM)
        ]
    
    return result


# ============================================================
# JSON GENERATION
# ============================================================

def build_activity_json(title: str, index: int, budget_type: str) -> dict:
    """Build a single activity JSON object."""
    code = generate_activity_code(title, index)
    
    return {
        "code": code,
        "title": title,
        "form_type": None,  # Will need manual configuration
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


def build_subsystem_json(subsystem_code: str, expense_activities: List[dict], 
                         capital_activities: List[dict]) -> dict:
    """Build a single subsystem JSON object with merged activities."""
    
    subsystem_def = SUBSYSTEMS.get(subsystem_code, SUBSYSTEMS["OTHER"])
    
    activities = []
    seen_titles = set()
    activity_index = 1
    
    # Add expense activities
    for act in expense_activities:
        title = act["title"]
        if title not in seen_titles:
            activities.append(build_activity_json(title, activity_index, "expense"))
            seen_titles.add(title)
            activity_index += 1
    
    # Add capital activities
    for act in capital_activities:
        title = act["title"]
        if title not in seen_titles:
            activities.append(build_activity_json(title, activity_index, "capital"))
            seen_titles.add(title)
            activity_index += 1
    
    # Limit total activities
    activities = activities[:MAX_ACTIVITIES_PER_SUBSYSTEM]
    
    return {
        "code": subsystem_def["code"],
        "title": subsystem_def["title"],
        "icon": subsystem_def["icon"],
        "attachment_type": subsystem_def["attachment_type"],
        "order": subsystem_def["order"],
        "is_active": len(activities) > 0,  # Active only if has activities
        "activities": activities
    }


def generate_master_config() -> dict:
    """Generate the complete master config JSON."""
    
    print("=" * 70)
    print("📊 MASTER CONFIG GENERATOR V2")
    print("=" * 70)
    
    # Load data
    print("\n📁 Loading Excel files...")
    expense_df = load_expense_budget()
    capital_df = load_capital_budget()
    
    # Process data
    print("\n🔄 Processing activities...")
    expense_activities = process_dataframe(expense_df, is_capital=False) if expense_df is not None else {}
    capital_activities = process_dataframe(capital_df, is_capital=True) if capital_df is not None else {}
    
    # Print summary
    print("\n📋 Activities per Subsystem:")
    print("-" * 50)
    for subsystem_code in SUBSYSTEMS.keys():
        expense_count = len(expense_activities.get(subsystem_code, []))
        capital_count = len(capital_activities.get(subsystem_code, []))
        if expense_count > 0 or capital_count > 0:
            print(f"   {SUBSYSTEMS[subsystem_code]['title']:<35} | E:{expense_count:3d} | C:{capital_count:3d}")
    
    # Build final JSON
    print("\n🔨 Building JSON structure...")
    subsystems_json = []
    
    for subsystem_code in sorted(SUBSYSTEMS.keys(), key=lambda x: SUBSYSTEMS[x]["order"]):
        expense_acts = expense_activities.get(subsystem_code, [])
        capital_acts = capital_activities.get(subsystem_code, [])
        
        # Only include subsystems with activities
        if expense_acts or capital_acts:
            subsystems_json.append(
                build_subsystem_json(subsystem_code, expense_acts, capital_acts)
            )
    
    # Final config structure
    config = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "version": "2.0.0",
        "generated_at": datetime.now().isoformat(),
        "description": "Master configuration for Municipality Subsystems - Auto-generated from Excel budget files",
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
