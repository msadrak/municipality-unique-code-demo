import sys
import os
sys.path.append(os.getcwd())
from app.database import SessionLocal, engine
from app import models

def seed_events():
    print("--- Seeding Financial Events ---")
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # لیست استاندارد شده بر اساس تصویر ارسالی شما
    events = [
        ("01", "تامین اعتبار"),
        ("02", "پیش‌پرداخت"),
        ("03", "علی‌الحساب"),
        ("04", "صورت‌وضعیت موقت"),
        ("05", "صورت‌وضعیت تعدیل"),
        ("06", "صورت‌وضعیت قطعی"),
        ("07", "سپرده بیمه"),
        ("08", "سپرده حسن انجام کار"),
        ("09", "استرداد سپرده"),
        ("10", "هزینه قطعی"),
        ("11", "تنخواه گردان"),
        ("12", "بازپرداخت تنخواه"),
        ("13", "حقوق و دستمزد"),
        ("14", "مزایا و رفاهی"),
        ("15", "اضافه کار"),
        ("16", "ماموریت"),
        ("17", "پاداش و عیدی"),
        ("18", "سنوات و بازخرید خدمت"),
        ("19", "بازخرید مرخصی"),
        ("20", "کسورات قانونی"),
        ("21", "کمک هزینه"),
        ("22", "خرید خدمات"),
        ("23", "تعمیر و نگهداری"),
        ("99", "سایر موارد")
    ]

    try:
        # پاکسازی قبلی‌ها
        db.query(models.FinancialEventRef).delete()
        
        count = 0
        for code, title in events:
            db.add(models.FinancialEventRef(code=code, title=title))
            count += 1
        
        db.commit()
        print(f"✅ Success! {count} financial events imported.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_events()