"""
Generate Config V3 - Standardized (Dictionary-Based)
=====================================================
Generates a clean config_master.json using STRICT dictionary matching.
Only pre-defined activity titles are accepted - no garbage data.

Usage:
    python scripts/generate_config_v3_standardized.py
"""

import pandas as pd
import json
import os
from datetime import datetime
from collections import defaultdict

# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = "تملک دارایی سرمایه ای.xlsx"
OUTPUT_FILE = "app/config/config_master.json"

# ============================================================
# THE GOLDEN DICTIONARY - Strict Activity Mapping
# ============================================================

STANDARD_MAP = {
    "URBAN_SERVICES": {
        "نگهداری و توسعه فضای سبز": ["فضای سبز", "پارک", "درخت", "گیاه", "آبیاری", "چمن", "نهال", "باغ"],
        "نظافت شهری و مدیریت پسماند": ["نظافت", "رفت و روب", "زباله", "پسماند", "جارو", "حمل زباله", "نخاله"],
        "لایروبی و مسیل‌ها": ["لایروبی", "مادی", "نهر", "کانال", "جوی", "زاینده رود"],
        "تاسیسات و مبلمان شهری": ["مبلمان", "نیمکت", "سطل", "تاسیسات شهری", "رنگ آمیزی", "آذین"],
        "آبرسانی و چاه": ["آبرسانی", "تانکر", "چاه", "قنات", "منبع آب", "جذبی"]
    },
    "CIVIL_TRAFFIC": {
        "روکش و ترمیم آسفالت": ["آسفالت", "روکش", "لکه گیری", "قیر", "تراش", "معابر"],
        "پیاده‌روسازی و معابر": ["پیاده رو", "سنگ فرش", "بلوک", "کف فرش", "زیرسازی", "پیاده‌رو"],
        "جدول‌گذاری و آبهای سطحی": ["جدول", "کانیو", "آبراهه", "دفع آب", "جدول گذاری"],
        "تجهیزات و علائم ترافیکی": ["ترافیک", "خط کشی", "تابلو", "سرعت گیر", "گاردریل", "چراغ راهنما"],
        "پل و زیرگذر": ["پل", "زیرگذر", "روگذر", "تقاطع"]
    },
    "BUILDINGS": {
        "روشنایی و نورپردازی": ["روشنایی", "نورپردازی", "برق", "لوستر", "پروژکتور", "نور"],
        "تعمیر و نگهداری ساختمان": ["ساختمان", "ابنیه", "اداری", "تاسیسات ساختمان", "موتورخانه", "مستحدثات"],
        "ایمن‌سازی و بهسازی": ["ایمن سازی", "بهسازی", "مقاوم سازی", "ایمنی"]
    },
    "ADMIN_WELFARE": {
        "خدمات رفاهی و انگیزشی": ["رفاهی", "پاداش", "بن", "ورزشی", "هدیه", "کمک هزینه", "تشویق"],
        "ملزومات و تجهیزات اداری": ["چاپ", "تجهیزات اداری", "کامپیوتر", "کاغذ", "نرم افزار", "اثاثیه", "مبلمان اداری"],
        "تعمیرات و نگهداری اموال": ["تعمیرات اساسی", "نگهداری اموال", "ماشین آلات", "وسایط نقلیه"]
    }
}

# Subsystem Definitions
SUBSYSTEM_DEFINITIONS = {
    "URBAN_SERVICES": {
        "code": "URBAN_SERVICES",
        "title": "سامانه خدمات شهری",
        "icon": "Trees",
        "fallback_title": "سایر خدمات شهری"
    },
    "CIVIL_TRAFFIC": {
        "code": "CIVIL_TRAFFIC",
        "title": "سامانه عمران و ترافیک",
        "icon": "Road",
        "fallback_title": "سایر امور عمرانی"
    },
    "BUILDINGS": {
        "code": "BUILDINGS",
        "title": "سامانه ساختمان و تاسیسات",
        "icon": "Building",
        "fallback_title": "سایر امور تاسیساتی"
    },
    "ADMIN_WELFARE": {
        "code": "ADMIN_WELFARE",
        "title": "سامانه اداری و رفاهی",
        "icon": "Users",
        "fallback_title": "سایر امور اداری"
    }
}

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def normalize_text(text) -> str:
    """Normalize Persian text (standardize characters)."""
    if pd.isna(text) or text is None:
        return ""
    s = str(text).strip()
    # Normalize Persian characters
    s = s.replace("ي", "ی").replace("ك", "ک")
    return s


def get_subsystem_from_trustee(trustee: str) -> str:
    """Map Trustee to Subsystem code based on keywords."""
    trustee_clean = normalize_text(trustee)
    
    if "خدمات" in trustee_clean:
        return "URBAN_SERVICES"
    elif "عمران" in trustee_clean or "حمل" in trustee_clean:
        return "CIVIL_TRAFFIC"
    elif "معماری" in trustee_clean or "شهر ساز" in trustee_clean:
        return "BUILDINGS"
    elif "برنامه" in trustee_clean or "مالی" in trustee_clean or "فرهنگ" in trustee_clean:
        return "ADMIN_WELFARE"
    else:
        return "ADMIN_WELFARE"  # Fallback


def match_activity(description: str, subsystem_code: str) -> str:
    """
    Match description to a standard activity title using the Golden Dictionary.
    First match wins. If no match, return fallback title.
    """
    desc_clean = normalize_text(description)
    
    if subsystem_code not in STANDARD_MAP:
        return SUBSYSTEM_DEFINITIONS.get(subsystem_code, {}).get("fallback_title", "سایر موارد")
    
    # Search through keywords
    for standard_title, keywords in STANDARD_MAP[subsystem_code].items():
        for keyword in keywords:
            if keyword in desc_clean:
                return standard_title
    
    # No match found - return fallback
    return SUBSYSTEM_DEFINITIONS[subsystem_code]["fallback_title"]


# ============================================================
# MAIN GENERATOR
# ============================================================

def generate_config():
    """Main function to generate standardized config."""
    print("=" * 60)
    print("📊 GENERATE CONFIG V3 - STANDARDIZED (Dictionary-Based)")
    print("=" * 60)
    
    # Load Excel file
    print(f"\n📁 Loading: {INPUT_FILE}")
    if not os.path.exists(INPUT_FILE):
        print(f"❌ File not found: {INPUT_FILE}")
        return
    
    try:
        df = pd.read_excel(INPUT_FILE, engine='openpyxl')
        print(f"   ✅ Loaded: {len(df):,} rows")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Find columns
    row_type_col = None
    trustee_col = None
    desc_col = None
    
    for col in df.columns:
        col_str = str(col).strip()
        if "نوع ردیف" in col_str:
            row_type_col = col
        elif "متولی" in col_str or "متولي" in col_str:
            trustee_col = col
        elif "شرح ردیف" in col_str or "شرح" == col_str:
            desc_col = col
    
    print(f"   📋 Columns found:")
    print(f"      - Row Type: {row_type_col}")
    print(f"      - Trustee: {trustee_col}")
    print(f"      - Description: {desc_col}")
    
    if not all([row_type_col, trustee_col, desc_col]):
        print("❌ Missing required columns!")
        return
    
    # Filter to continuous rows only
    df_filtered = df[df[row_type_col].astype(str).str.contains('مستمر', na=False)]
    print(f"\n🔄 Filtered to مستمر (Continuous) rows: {len(df_filtered):,}")
    
    # Process rows and collect activities
    subsystem_activities = defaultdict(set)
    stats = defaultdict(lambda: {"matched": 0, "fallback": 0})
    
    for _, row in df_filtered.iterrows():
        trustee = normalize_text(row.get(trustee_col, ''))
        description = normalize_text(row.get(desc_col, ''))
        
        if not description:
            continue
        
        # Get subsystem
        subsystem_code = get_subsystem_from_trustee(trustee)
        
        # Match activity
        activity_title = match_activity(description, subsystem_code)
        
        # Track stats
        fallback_title = SUBSYSTEM_DEFINITIONS[subsystem_code]["fallback_title"]
        if activity_title == fallback_title:
            stats[subsystem_code]["fallback"] += 1
        else:
            stats[subsystem_code]["matched"] += 1
        
        # Add to set (deduplicates automatically)
        subsystem_activities[subsystem_code].add(activity_title)
    
    # Print statistics
    print("\n📋 Matching Statistics:")
    print("-" * 50)
    for code, stat in stats.items():
        title = SUBSYSTEM_DEFINITIONS[code]["title"]
        total = stat["matched"] + stat["fallback"]
        match_rate = (stat["matched"] / total * 100) if total > 0 else 0
        print(f"   {title}: {stat['matched']}/{total} matched ({match_rate:.1f}%)")
    
    # Build JSON structure
    print("\n🔨 Building JSON structure...")
    subsystems_json = []
    
    for code in ["URBAN_SERVICES", "CIVIL_TRAFFIC", "BUILDINGS", "ADMIN_WELFARE"]:
        if code not in subsystem_activities:
            continue
        
        definition = SUBSYSTEM_DEFINITIONS[code]
        activities = sorted(subsystem_activities[code])
        
        activities_json = []
        for idx, title in enumerate(activities, 1):
            activity_code = f"{code}_{idx:02d}"
            activities_json.append({
                "code": activity_code,
                "title": title,
                "form_type": None,
                "frequency": "MONTHLY",
                "requires_file_upload": False,
                "external_service_url": None,
                "order": idx,
                "is_active": True,
                "constraints": [
                    {
                        "budget_code_pattern": None,
                        "allowed_budget_types": ["capital"],
                        "cost_center_pattern": None,
                        "allowed_cost_centers": None,
                        "constraint_type": "INCLUDE",
                        "priority": 1,
                        "description": "فقط ردیف‌های بودجه سرمایه‌ای"
                    }
                ]
            })
        
        subsystems_json.append({
            "code": code,
            "title": definition["title"],
            "icon": definition["icon"],
            "attachment_type": "both",
            "order": len(subsystems_json) + 1,
            "is_active": True,
            "activities": activities_json
        })
    
    # Final config
    config = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "version": "3.0.0",
        "generated_at": datetime.now().isoformat(),
        "description": "Standardized config - Dictionary-based mapping (no garbage titles)",
        "subsystems": subsystems_json
    }
    
    # Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    # Summary
    print(f"\n✅ Saved to: {OUTPUT_FILE}")
    print(f"   Total subsystems: {len(subsystems_json)}")
    total_activities = sum(len(s['activities']) for s in subsystems_json)
    print(f"   Total activities: {total_activities}")
    
    print("\n📋 Activities per Subsystem:")
    for s in subsystems_json:
        print(f"   - {s['title']}: {len(s['activities'])} activities")
    
    print("\n" + "=" * 60)
    print("🎉 Done! Clean config generated with NO garbage data.")
    print("=" * 60)


if __name__ == "__main__":
    generate_config()
