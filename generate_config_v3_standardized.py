import pandas as pd
import json
import os

# --- 1. The Golden Dictionary (Standardized Activities) ---
# این دیکشنری تعیین می‌کند چه کارت‌هایی در سیستم وجود داشته باشند.
# هر لیست شامل کلمات کلیدی است که اگر پیدا شوند، آن کارت فعال می‌شود.

STANDARD_ACTIVITIES_MAP = {
    # --- خدمات شهری ---
    "URBAN_SERVICES": {
        "نگهداری و توسعه فضای سبز": ["فضای سبز", "پارک", "درخت", "گیاه", "آبیاری", "چمن"],
        "نظافت شهری و مدیریت پسماند": ["نظافت", "رفت و روب", "زباله", "پسماند", "جارو", "حمل زباله"],
        "لایروبی و مسیل‌ها": ["لایروبی", "مادی", "نهر", "کانال", "جوی"],
        "تاسیسات و مبلمان شهری": ["مبلمان", "نیمکت", "سطل", "تاسیسات شهری", "رنگ آمیزی"],
        "آبرسانی و چاه": ["آبرسانی", "تانکر", "چاه", "قنات", "منبع آب"],
        "سایر خدمات شهری": [] # Catch-all
    },
    # --- عمران و ترافیک ---
    "CIVIL_TRAFFIC": {
        "روکش و ترمیم آسفالت": ["آسفالت", "روکش", "لکه گیری", "قیر", "تراش"],
        "پیاده‌روسازی و معابر": ["پیاده رو", "سنگ فرش", "بلوک", "کف فرش", "زیرسازی"],
        "جدول‌گذاری و آبهای سطحی": ["جدول", "کانیو", "آبراهه", "دفع آب"],
        "تجهیزات و علائم ترافیکی": ["ترافیک", "خط کشی", "تابلو", "سرعت گیر", "گاردریل"],
        "سایر امور عمرانی": [] # Catch-all
    },
    # --- تاسیسات و ساختمان ---
    "BUILDINGS": {
        "روشنایی و نورپردازی": ["روشنایی", "نورپردازی", "برق", "لوستر", "پروژکتور"],
        "تعمیر و نگهداری ساختمان": ["ساختمان", "ابنیه", "اداری", "تاسیسات ساختمان", "موتورخانه"],
        "سایر امور تاسیسات": [] # Catch-all
    },
    # --- اداری و رفاهی ---
    "ADMIN_WELFARE": {
        "حقوق و دستمزد": ["حقوق", "دستمزد", "مزایا", "کارانه"],
        "خدمات رفاهی": ["رفاهی", "پاداش", "بن", "ورزشی", "هدیه", "کمک هزینه"],
        "ملزومات اداری": ["چاپ", "تجهیزات اداری", "کامپیوتر", "کاغذ", "نرم افزار"],
        "پذیرایی و تشریفات": ["پذیرایی", "ناهار", "آبدارخانه", "تشریفات"],
        "سایر امور اداری": [] # Catch-all
    }
}

# نگاشت متولی به گروه‌های بالا
TRUSTEE_TO_GROUP = {
    "معاونت خدمات شهري": "URBAN_SERVICES",
    "معاونت عمران شهري": "CIVIL_TRAFFIC",
    "معاونت حمل و نقل و ترافيک": "CIVIL_TRAFFIC",
    "معاونت معماري و شهر سازي": "BUILDINGS", # فرض
    "معاونت برنامه ريزي": "ADMIN_WELFARE",
    "معاونت مالي و اقتصادی": "ADMIN_WELFARE",
    "معاونت فرهنگی اجتماعی": "ADMIN_WELFARE", # یا گروه جدید
}

def normalize_text(text):
    if pd.isna(text): return ""
    return str(text).replace("ي", "ی").replace("ك", "ک").strip()

def find_standard_activity(description, group_key):
    """
    متن شرح را می‌گیرد و سعی می‌کند با دیکشنری استاندارد مچ کند.
    اگر نشد، دسته 'سایر' را برمی‌گرداند.
    """
    if group_key not in STANDARD_ACTIVITIES_MAP:
        return "سایر فعالیت‌ها" # خیلی عمومی
    
    group_rules = STANDARD_ACTIVITIES_MAP[group_key]
    desc_clean = normalize_text(description)
    
    # 1. جستجو در کلیدواژه‌ها
    for standard_title, keywords in group_rules.items():
        for kw in keywords:
            if kw in desc_clean:
                return standard_title
    
    # 2. اگر پیدا نشد -> تور ایمنی
    # پیدا کردن کلید Catch-all که کلمه "سایر" دارد
    fallback = next((k for k in group_rules.keys() if "سایر" in k), "سایر موارد")
    return fallback

def generate_standardized_config():
    print("🚀 Starting Standardized Config Generation (Dictionary Based)...")
    
    try:
        # فقط فایل سرمایه ای را برای تست لود می‌کنیم (چون مستمرها آنجاست)
        # اما شما می‌توانید هر دو را لود کنید
        df = pd.read_excel('تملک دارایی سرمایه ای.xlsx', engine='openpyxl')
        print(f"✅ Loaded Data: {len(df)} rows")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # ساختار نهایی
    subsystems_config = {}

    for _, row in df.iterrows():
        # فقط مستمرها (طبق درخواست قبلی)
        if normalize_text(row.get('نوع ردیف')) != 'مستمر':
            continue

        trustee = normalize_text(row.get('متولی'))
        description = normalize_text(row.get('شرح ردیف'))
        
        # 1. تشخیص گروه (Subsystem)
        group_key = "ADMIN_WELFARE" # پیش‌فرض
        sys_code = "OTHER"
        sys_title = "سایر"

        if "خدمات" in trustee:
            group_key = "URBAN_SERVICES"
            sys_code = "URBAN_SERVICES"
            sys_title = "سامانه خدمات شهری"
        elif "عمران" in trustee or "حمل" in trustee:
            group_key = "CIVIL_TRAFFIC"
            sys_code = "CIVIL_TRAFFIC"
            sys_title = "سامانه عمران و ترافیک"
        elif "برنامه" in trustee or "مالی" in trustee:
            group_key = "ADMIN_WELFARE"
            sys_code = "ADMIN_FINANCE"
            sys_title = "سامانه اداری و مالی"
        
        # 2. استانداردسازی فعالیت
        std_activity_title = find_standard_activity(description, group_key)
        
        # 3. افزودن به لیست
        if sys_code not in subsystems_config:
            subsystems_config[sys_code] = {
                "title": sys_title,
                "activities": set()
            }
        
        subsystems_config[sys_code]["activities"].add(std_activity_title)

    # تبدیل به JSON نهایی
    final_json_list = []
    for code, data in subsystems_config.items():
        acts_list = []
        for idx, act_title in enumerate(data['activities']):
            acts_list.append({
                "code": f"{code}_{idx+1}",
                "title": act_title,
                "frequency": "MONTHLY",
                "requires_file_upload": False,
                "constraints": [{"description": "فیلتر پیش‌فرض"}]
            })
        
        final_json_list.append({
            "code": code,
            "title": data['title'],
            "activities": acts_list
        })

    output = {"version": "3.0", "subsystems": final_json_list}
    
    with open('app/config/config_master_v3.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("✅ Config V3 Generated! All garbage titles are gone.")

if __name__ == "__main__":
    generate_standardized_config()