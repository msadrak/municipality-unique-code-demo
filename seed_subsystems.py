"""
اسکریپت seed برای ۱۴ سامانه زیرمجموعه حسابداری
"""
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal, engine
from app.models import Base, Subsystem, SubsystemActivity

# ایجاد جداول جدید
Base.metadata.create_all(bind=engine)

# تعریف ۱۴ سامانه
SUBSYSTEMS = [
    {"code": "PROCUREMENT", "title": "تدارکات", "icon": "ShoppingCart", "order": 1, "attachment_type": "both"},
    {"code": "BUDGET", "title": "بودجه", "icon": "Calculator", "order": 2, "attachment_type": "upload"},
    {"code": "TREASURY", "title": "خزانه", "icon": "Vault", "order": 3, "attachment_type": "upload"},
    {"code": "URBAN_PLANNING", "title": "شهرسازی", "icon": "Building", "order": 4, "attachment_type": "both"},
    {"code": "PAYROLL", "title": "حقوق و دستمزد", "icon": "Users", "order": 5, "attachment_type": "api"},
    {"code": "REVENUE", "title": "درآمد", "icon": "TrendingUp", "order": 6, "attachment_type": "upload"},
    {"code": "CONTRACTS", "title": "قراردادها", "icon": "FileText", "order": 7, "attachment_type": "both"},
    {"code": "WELFARE", "title": "رفاه", "icon": "Heart", "order": 8, "attachment_type": "upload"},
    {"code": "REAL_ESTATE", "title": "املاک", "icon": "Home", "order": 9, "attachment_type": "both"},
    {"code": "CONTRACTORS", "title": "امور پیمانکاران", "icon": "HardHat", "order": 10, "attachment_type": "both"},
    {"code": "WAREHOUSE", "title": "انبار و اموال", "icon": "Package", "order": 11, "attachment_type": "upload"},
    {"code": "PARTNERSHIPS", "title": "مشارکتها و سرمایه‌گذاری", "icon": "Handshake", "order": 12, "attachment_type": "both"},
    {"code": "ISFAHAN_CARD", "title": "اصفهان کارت", "icon": "CreditCard", "order": 13, "attachment_type": "api"},
    {"code": "OTHER", "title": "سایر", "icon": "MoreHorizontal", "order": 14, "attachment_type": "upload"},
]

# فعالیت‌های ویژه نمونه (بعداً تکمیل می‌شود)
SAMPLE_ACTIVITIES = {
    "PAYROLL": [
        {"code": "SALARY_PAYMENT", "title": "پرداخت حقوق و دستمزد", "form_type": "payroll"},
        {"code": "OVERTIME_PAYMENT", "title": "پرداخت اضافه کاری", "form_type": "payroll"},
        {"code": "BONUS_PAYMENT", "title": "پرداخت پاداش", "form_type": "payroll"},
    ],
    "CONTRACTS": [
        {"code": "CONTRACT_REGISTER", "title": "ثبت قرارداد جدید", "form_type": "contract"},
        {"code": "CONTRACT_AMENDMENT", "title": "اصلاحیه قرارداد", "form_type": "contract"},
        {"code": "CONTRACT_PROGRESS", "title": "صورت وضعیت پیمانکار", "form_type": "contractor_progress"},
    ],
    "CONTRACTORS": [
        {"code": "PROGRESS_PAYMENT", "title": "پرداخت صورت وضعیت", "form_type": "contractor_progress"},
        {"code": "ADVANCE_PAYMENT", "title": "پرداخت پیش‌پرداخت", "form_type": "advance"},
        {"code": "PERFORMANCE_BOND", "title": "ضمانت‌نامه حسن انجام کار", "form_type": "performance_bond"},
    ],
    "TREASURY": [
        {"code": "CHECK_ISSUE", "title": "صدور چک", "form_type": "check"},
        {"code": "BANK_TRANSFER", "title": "انتقال بانکی", "form_type": "transfer"},
    ],
    "PROCUREMENT": [
        {"code": "PURCHASE_REQUEST", "title": "درخواست خرید", "form_type": "purchase"},
        {"code": "INVOICE_PAYMENT", "title": "پرداخت فاکتور", "form_type": "invoice"},
    ],
    "WELFARE": [
        {"code": "LOAN_PAYMENT", "title": "پرداخت وام", "form_type": None},
        {"code": "AID_PAYMENT", "title": "پرداخت کمک", "form_type": None},
    ],
}

def seed_subsystems():
    db = SessionLocal()
    try:
        # بررسی اگر قبلاً اضافه شده
        existing = db.query(Subsystem).first()
        if existing:
            print("سامانه‌ها قبلاً اضافه شده‌اند. برای بازنشانی اول پاک کنید.")
            return
        
        print("در حال اضافه کردن ۱۴ سامانه...")
        subsystem_map = {}
        
        for sub_data in SUBSYSTEMS:
            subsystem = Subsystem(**sub_data)
            db.add(subsystem)
            db.flush()  # برای گرفتن ID
            subsystem_map[sub_data["code"]] = subsystem.id
            print(f"  ✓ {sub_data['title']}")
        
        print("\nدر حال اضافه کردن فعالیت‌های ویژه نمونه...")
        for subsystem_code, activities in SAMPLE_ACTIVITIES.items():
            subsystem_id = subsystem_map.get(subsystem_code)
            if subsystem_id:
                for idx, act_data in enumerate(activities):
                    activity = SubsystemActivity(
                        subsystem_id=subsystem_id,
                        code=act_data["code"],
                        title=act_data["title"],
                        form_type=act_data.get("form_type"),
                        order=idx + 1
                    )
                    db.add(activity)
                    print(f"  ✓ [{subsystem_code}] {act_data['title']}")
        
        db.commit()
        print("\n✅ همه سامانه‌ها و فعالیت‌ها با موفقیت اضافه شدند!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ خطا: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_subsystems()
