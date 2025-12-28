import pandas as pd
import json
import re

# --- 1. تعریف ۱۳ سامانه ---
SUBSYSTEMS_DEF = {
    "URBAN_PLANNING": "سامانه شهرسازی",
    "CONTRACTS": "سامانه امور قراردادها",
    "PAYROLL": "سامانه حقوق و دستمزد",
    "TADAROKAT": "سامانه تدارکات",
    "BUDGET": "سامانه بودجه",
    "TREASURY": "سامانه خزانه‌داری",
    "CONTRACTORS": "سامانه امور پیمانکاران",
    "WELFARE": "سامانه رفاه کارکنان",
    "REAL_ESTATE": "سامانه املاک",
    "WAREHOUSE": "سامانه انبار و اموال",
    "REVENUE": "سامانه درآمد",
    "ISFAHAN_CARD": "سامانه اصفهان کارت",
    "INVESTMENT": "سامانه مشارکت‌ها و سرمایه‌گذاری",
    "OTHER": "سایر / عمومی"
}

# --- 2. دیکشنری غنی‌شده (Expanded Dictionary) ---
# کلمات کلیدی جدید برای سامانه‌های خالی اضافه شد
CLEANING_MAP = {
    # خدمات شهری
    "نگهداری و توسعه فضای سبز": ["فضای سبز", "پارک", "درخت", "گیاه", "آبیاری", "چمن"],
    "نظافت شهری و مدیریت پسماند": ["نظافت", "رفت و روب", "زباله", "پسماند", "جارو"],
    "لایروبی انهار و مسیل‌ها": ["لایروبی", "مادی", "نهر", "کانال"],
    "تاسیسات و مبلمان شهری": ["مبلمان", "نیمکت", "سطل", "تاسیسات شهری", "رنگ آمیزی", "آذین"],
    
    # عمران
    "روکش و ترمیم آسفالت": ["آسفالت", "روکش", "لکه گیری", "قیر"],
    "پیاده‌روسازی و اصلاح معابر": ["پیاده رو", "سنگ فرش", "بلوک", "کف فرش", "زیرسازی"],
    "جدول‌گذاری و کانیو": ["جدول", "کانیو", "آبراهه"],
    "تجهیزات ترافیکی": ["ترافیک", "خط کشی", "تابلو", "سرعت گیر", "گاردریل"],
    
    # شهرسازی (جدید)
    "طرح‌های توسعه شهری و بازآفرینی": ["طرح تفصیلی", "بازآفرینی", "بافت فرسوده", "گلوگاه", "حریم", "جامع"],
    "ممیزی و بازدید املاک": ["ممیزی", "بازدید", "کارشناسی", "بر و کف"],
    
    # بودجه و مالی (جدید)
    "مدیریت بودجه و اعتبارات": ["بودجه", "تخصیص", "موافقتنامه", "تفریغ"],
    "حسابرسی و امور مالی": ["حسابرسی", "ذیحساب", "صورت وضعیت"],
    
    # درآمد (جدید)
    "وصول درآمد و عوارض": ["عوارض", "نوسازی", "کسب و پیشه", "درآمد"],
    
    # عمومی
    "حقوق و دستمزد": ["حقوق", "دستمزد", "مزایا"],
    "خدمات رفاهی": ["رفاهی", "پاداش", "بن", "ورزشی"],
    "ملزومات اداری": ["خرید", "تجهیزات", "ملزومات", "چاپ"],
    "تملک اراضی": ["تملک", "آزادسازی", "مسیر"],
    "دیون و تعهدات": ["دیون", "انتقال وجوه"]
}

def clean_text_smart(text):
    """
    متن را می‌گیرد و اگر در دیکشنری نبود، آن را تمیز می‌کند تا قابل استفاده شود.
    """
    if pd.isna(text): return ""
    text = str(text).replace("ي", "ی").replace("ك", "ک").strip()
    
    # 1. جستجو در دیکشنری (اولویت بالا)
    for clean_title, keywords in CLEANING_MAP.items():
        for kw in keywords:
            if kw in text:
                return clean_title
                
    # 2. اگر پیدا نشد: پاکسازی هوشمند (Soft Fallback)
    # حذف کلمات زائد
    text = text.replace("پروژه", "").replace("عملیات", "").replace("اجرای", "").replace("طرح", "")
    # حذف اعداد (مثلاً کوچه 12)
    text = re.sub(r'\d+', '', text) 
    # حذف پرانتزها
    text = re.sub(r'\(.*?\)', '', text)
    # حذف کاراکترهای عجیب
    text = text.replace("-", "").replace("_", "").strip()
    
    # اگر متن خیلی کوتاه شد (زیر 4 کاراکتر)، برگردان به "سایر"
    if len(text) < 4:
        return None 
        
    return text # متن تمیز شده (مثلاً "زیرسازی خیابان کاوه" -> "زیرسازی خیابان کاوه")

def determine_subsystem(row, source_type):
    trustee = str(row.get('متولی', '')).replace("ي", "ی").replace("ك", "ک")
    subject = str(row.get('موضوع', '')).replace("ي", "ی").replace("ك", "ک")
    
    # منطق نگاشت متولی به سامانه
    if "شهرسازی" in trustee or "معماری" in trustee: return "URBAN_PLANNING"
    if "برنامه" in trustee: return "BUDGET" # برنامه‌ریزی معمولاً بودجه است
    if "مالی" in trustee or "خزانه" in trustee: return "TREASURY" # مالی می‌تواند خزانه یا درآمد باشد
    if "درآمد" in trustee: return "REVENUE"
    
    if "حقوق" in subject: return "PAYROLL"
    if "تدارکات" in trustee or "پشتیبانی" in trustee: return "TADAROKAT"
    
    # نگاشت‌های پیش‌فرض
    if "خدمات" in trustee: return "CONTRACTORS" # یا خدمات شهری
    if "عمران" in trustee or "حمل" in trustee: return "CONTRACTORS"
    if "فرهنگی" in trustee: return "WELFARE" # یا فرهنگی مجزا
    
    if source_type == 'capital': return "CONTRACTORS"
    
    return "OTHER"

def generate_full_coverage_config():
    print("🚀 Starting V5 Config Generation (Full Coverage)...")
    
    # لود کردن داده‌ها
    try:
        df_cap = pd.read_excel('تملک دارایی سرمایه ای.xlsx', engine='openpyxl')
        df_exp = pd.read_excel('اعتبارات هزینه ای.xlsx', engine='openpyxl')
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    subsystem_activities = {code: set() for code in SUBSYSTEMS_DEF.keys()}
    
    # تابع پردازش
    def process_rows(df, source_type):
        for _, row in df.iterrows():
            # فقط مستمرها (برای سرمایه ای)
            if source_type == 'capital' and str(row.get('نوع ردیف')).strip() != 'مستمر':
                continue
                
            sys_code = determine_subsystem(row, source_type)
            raw_desc = row.get('شرح ردیف') if 'شرح ردیف' in row else row.get('شرح')
            
            clean_title = clean_text_smart(raw_desc)
            
            if clean_title:
                subsystem_activities[sys_code].add(clean_title)

    process_rows(df_cap, 'capital')
    process_rows(df_exp, 'expense')

    # ساخت JSON
    final_subsystems = []
    total_acts = 0
    
    for code, title in SUBSYSTEMS_DEF.items():
        acts = sorted(list(subsystem_activities[code]))
        
        # اگر هنوز خالی است، یک فعالیت پیش‌فرض بگذار تا سامانه نمایش داده شود
        if not acts:
            acts = ["سایر موارد"]
            
        act_objects = []
        for idx, act_title in enumerate(acts):
            # محدود کردن تعداد فعالیت‌ها برای جلوگیری از انفجار (مثلاً ماکسیمم 30 تا پر تکرار)
            # اینجا همه را می‌آوریم چون شما خواهان پوشش هستید
            act_objects.append({
                "code": f"{code}_{idx+1}",
                "title": act_title,
                "frequency": "MONTHLY",
                "requires_file_upload": False,
                "constraints": [{"description": "خودکار"}]
            })
            
        total_acts += len(act_objects)
        final_subsystems.append({
            "code": code,
            "title": title,
            "activities": act_objects
        })

    output = {"version": "5.0", "subsystems": final_subsystems}
    
    with open('app/config/config_master_v5.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Config V5 Generated! Total Activities: {total_acts}")
    print("   All 13 Subsystems are now populated.")

if __name__ == "__main__":
    generate_full_coverage_config()