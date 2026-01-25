"""
Import بودجه از دو فایل اصلی
=============================

این اسکریپت داده‌های بودجه را از دو فایل زیر import می‌کند:
1. اعتبارات هزینه ای.xlsx
2. تملک دارایی سرمایه ای.xlsx

نحوه استفاده:
    python import_municipality_budget.py
"""

import pandas as pd
import re
from app.database import SessionLocal
from app import models


def clean_amount(value):
    """تبدیل مبلغ به عدد"""
    if pd.isna(value) or value is None:
        return 0.0
    
    s = str(value).replace(',', '').replace(' ', '').strip()
    
    # تبدیل اعداد فارسی
    persian = '۰۱۲۳۴۵۶۷۸۹'
    for i, p in enumerate(persian):
        s = s.replace(p, str(i))
    
    s = re.sub(r'[^\d.]', '', s)
    
    try:
        return float(s) if s else 0.0
    except:
        return 0.0


def clean_budget_code(code):
    """استانداردسازی کد بودجه"""
    if pd.isna(code) or code is None:
        return None
    
    s = str(code).strip()
    s = re.sub(r'[^\d]', '', s)
    
    if len(s) < 4:
        return None
    
    return s[:8]  # حداکثر ۸ رقم


def parse_zone_from_text(text):
    """استخراج کد منطقه از متن"""
    if pd.isna(text) or text is None:
        return None
    
    s = str(text).strip()
    
    # الگوهای شناخته شده
    # "شهرداری منطقه ۵" -> 5
    # "منطقه 20" -> 20
    # "شهرداري اصفهان 300" -> 20 (مرکزی)
    
    if "مرکز" in s or "300" in s or "اصفهان" in s.lower():
        return "20"  # امور مالی/مرکزی
    
    match = re.search(r'منطقه\s*(\d+)', s)
    if match:
        return match.group(1)
    
    match = re.search(r'(\d+)\s*$', s)
    if match:
        return match.group(1)
    
    return None


def find_trustee_section(trustee_text, db):
    """پیدا کردن قسمت متولی"""
    if pd.isna(trustee_text) or not trustee_text:
        return None
    
    s = str(trustee_text).strip()
    
    # جستجو در OrgUnit
    section = db.query(models.OrgUnit).filter(
        models.OrgUnit.title.contains(s)
    ).first()
    
    if section:
        return section.id
    
    # جستجوی جزئی
    keywords = s.split()
    for kw in keywords:
        if len(kw) > 3:
            section = db.query(models.OrgUnit).filter(
                models.OrgUnit.title.contains(kw)
            ).first()
            if section:
                return section.id
    
    return None


def import_hazineei():
    """Import فایل اعتبارات هزینه‌ای"""
    print("\n" + "="*60)
    print("📂 Import: اعتبارات هزینه ای.xlsx")
    print("="*60)
    
    df = pd.read_excel("اعتبارات هزینه ای.xlsx", dtype=str)
    print(f"📊 تعداد سطرها: {len(df)}")
    
    db = SessionLocal()
    success = 0
    updated = 0
    skipped = 0
    
    try:
        for idx, row in df.iterrows():
            budget_code = clean_budget_code(row.get("کد بودجه"))
            if not budget_code:
                skipped += 1
                continue
            
            description = str(row.get("شرح ردیف", "")).strip()
            allocated = clean_amount(row.get("مصوب 1403"))
            spent = clean_amount(row.get("هزینه 1403"))
            trustee_text = row.get("متولی")
            subject = str(row.get("موضوع", "")).strip()
            
            # پیدا کردن قسمت متولی
            trustee_id = find_trustee_section(trustee_text, db)
            
            # بررسی وجود قبلی
            existing = db.query(models.BudgetItem).filter(
                models.BudgetItem.budget_code == budget_code
            ).first()
            
            if existing:
                # بروزرسانی
                existing.description = description or existing.description
                existing.allocated_1403 = allocated if allocated > 0 else existing.allocated_1403
                existing.spent_1403 = spent if spent > 0 else existing.spent_1403
                if trustee_id:
                    existing.trustee_section_id = trustee_id
                existing.remaining_budget = (existing.allocated_1403 or 0) - (existing.spent_1403 or 0)
                updated += 1
            else:
                # ایجاد جدید
                remaining = allocated - spent
                item = models.BudgetItem(
                    budget_code=budget_code,
                    description=description,
                    budget_type="expense",  # هزینه‌ای
                    allocated_1403=allocated,
                    spent_1403=spent,
                    remaining_budget=remaining,
                    reserved_amount=0,
                    trustee_section_id=trustee_id
                )
                db.add(item)
                success += 1
        
        db.commit()
        print(f"✅ جدید: {success}")
        print(f"🔄 بروزرسانی: {updated}")
        print(f"⏭️ رد شده: {skipped}")
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        db.rollback()
    finally:
        db.close()
    
    return {"success": success, "updated": updated, "skipped": skipped}


def import_tamalok():
    """Import فایل تملک دارایی سرمایه‌ای"""
    print("\n" + "="*60)
    print("📂 Import: تملک دارایی سرمایه ای.xlsx")
    print("="*60)
    
    df = pd.read_excel("تملک دارایی سرمایه ای.xlsx", dtype=str)
    print(f"📊 تعداد سطرها: {len(df)}")
    
    db = SessionLocal()
    success = 0
    updated = 0
    skipped = 0
    
    try:
        for idx, row in df.iterrows():
            budget_code = clean_budget_code(row.get("کد بودجه"))
            if not budget_code:
                skipped += 1
                continue
            
            description = str(row.get("شرح ردیف", "")).strip()
            project_desc = str(row.get("شرح پروژه", "")).strip()
            full_desc = f"{description}" + (f" - {project_desc}" if project_desc and project_desc != 'nan' else "")
            
            allocated = clean_amount(row.get("مصوب 1403"))
            spent = clean_amount(row.get("هزینه 1403"))
            trustee_text = row.get("متولی")
            zone_text = row.get("منطقه")
            
            # پیدا کردن قسمت متولی
            trustee_id = find_trustee_section(trustee_text, db) if pd.notna(trustee_text) else None
            
            # استخراج کد منطقه
            zone_code = parse_zone_from_text(zone_text)
            
            # بررسی وجود قبلی - اگر هست، مبالغ رو جمع کن
            existing = db.query(models.BudgetItem).filter(
                models.BudgetItem.budget_code == budget_code
            ).first()
            
            if existing:
                # Aggregate amounts for duplicates
                existing.allocated_1403 = (existing.allocated_1403 or 0) + allocated
                existing.spent_1403 = (existing.spent_1403 or 0) + spent
                existing.remaining_budget = (existing.allocated_1403 or 0) - (existing.spent_1403 or 0)
                
                # Update trustee/zone if not set
                if trustee_id and not existing.trustee_section_id:
                    existing.trustee_section_id = trustee_id
                if zone_code and not existing.zone_code:
                    existing.zone_code = zone_code
                    
                updated += 1
            else:
                # ایجاد جدید
                remaining = allocated - spent
                item = models.BudgetItem(
                    budget_code=budget_code,
                    description=full_desc,
                    budget_type="capital",  # سرمایه‌ای
                    zone_code=zone_code,
                    allocated_1403=allocated,
                    spent_1403=spent,
                    remaining_budget=remaining,
                    reserved_amount=0,
                    trustee_section_id=trustee_id
                )
                db.add(item)
                success += 1
            
            # Commit after each row to handle duplicates
            db.commit()
            
            # Progress
            if (idx + 1) % 500 == 0:
                print(f"   پردازش: {idx + 1} / {len(df)}")
        
        print(f"✅ جدید: {success}")
        print(f"🔄 بروزرسانی/تجمیع: {updated}")
        print(f"⏭️ رد شده: {skipped}")
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        db.rollback()
    finally:
        db.close()
    
    return {"success": success, "updated": updated, "skipped": skipped}


def main():
    print("\n🚀 Import بودجه شهرداری")
    print("="*60)
    
    # Import هر دو فایل
    r1 = import_hazineei()
    r2 = import_tamalok()
    
    # آمار کلی
    print("\n" + "="*60)
    print("📊 آمار کلی:")
    print(f"   جدید: {r1['success'] + r2['success']}")
    print(f"   بروزرسانی: {r1['updated'] + r2['updated']}")
    print(f"   رد شده: {r1['skipped'] + r2['skipped']}")
    print("="*60)


if __name__ == "__main__":
    main()
