"""
Import Account Codes to Database
=================================

این اسکریپت کدهای یکتا را از آداپتور تولید کرده و در دیتابیس ذخیره می‌کند.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app import models
from app.adapters.account_code_adapter import AccountCodeAdapter

# ایجاد جداول
models.Base.metadata.create_all(bind=engine)


def import_account_codes(file_path: str, clear_existing: bool = True):
    """
    پردازش فایل و ذخیره کدها در دیتابیس
    """
    print("=" * 60)
    print("🚀 شروع Import کدهای یکتا به دیتابیس")
    print("=" * 60)
    
    # پردازش با Adapter
    adapter = AccountCodeAdapter(file_path)
    result = adapter.process()
    
    if not result["success"]:
        print(f"❌ خطا: {result.get('error')}")
        return False
    
    db = SessionLocal()
    
    try:
        if clear_existing:
            print("\n🗑️ پاک کردن داده‌های قبلی...")
            db.query(models.TemporaryAccountRecord).delete()
            db.query(models.PermanentAccountRecord).delete()
            db.query(models.AccountCode).delete()
            db.commit()
        
        print(f"\n💾 ذخیره {len(result['unique_codes']):,} کد یکتا...")
        
        for i, code_data in enumerate(result["unique_codes"]):
            # Parse unique code
            parts = code_data["unique_code"].split("-")
            
            account_code = models.AccountCode(
                unique_code=code_data["unique_code"],
                zone_code=parts[0] if len(parts) > 0 else "",
                category=parts[1] if len(parts) > 1 else "",
                budget_code=parts[2] if len(parts) > 2 else "",
                permanent_code=parts[3] if len(parts) > 3 else "",
                sequence=int(parts[4]) if len(parts) > 4 else i + 1,
                request_id=code_data["request_id"],
                transaction_type=code_data["transaction_type"],
                total_amount=code_data["total_amount"],
                temp_account_count=code_data["temp_count"],
                perm_account_count=code_data["perm_count"],
                bank_account_count=code_data["bank_count"],
                is_balanced=code_data["is_balanced"]
            )
            db.add(account_code)
            
            if (i + 1) % 500 == 0:
                print(f"   ذخیره شد: {i + 1:,}")
                db.commit()
        
        db.commit()
        
        # آمار نهایی
        total_codes = db.query(models.AccountCode).count()
        print(f"\n✅ ذخیره کامل شد: {total_codes:,} کد یکتا")
        
        # نمایش آمار دسته‌بندی
        print("\n📊 آمار دسته‌بندی:")
        from sqlalchemy import func
        category_stats = db.query(
            models.AccountCode.category,
            func.count(models.AccountCode.id)
        ).group_by(models.AccountCode.category).all()
        
        for cat, count in category_stats:
            print(f"   {cat}: {count:,}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    file_path = "_شهرداری مرکزی گزارش دفتر مرکزی1403.xlsx"
    import_account_codes(file_path)
