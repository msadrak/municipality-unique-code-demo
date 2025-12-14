"""
Budget Data Adapter
===================

آداپتر برای import داده‌های بودجه از فایل‌های اکسل شهرداری.

ویژگی‌ها:
- خواندن و تمیزکاری داده‌های کثیف
- تشخیص و استخراج کد بودجه ۶ رقمی
- ارتباط با متولی (trustee) و قسمت/اداره
- محاسبه مانده بودجه
"""

import pandas as pd
import re
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal


class BudgetAdapter:
    """
    آداپتر برای import بودجه از اکسل
    
    نمونه استفاده:
        adapter = BudgetAdapter("budget_file.xlsx")
        results = adapter.import_to_db()
        print(f"Imported {results['success']} items")
    """
    
    # ستون‌های مورد انتظار در فایل اکسل
    EXPECTED_COLUMNS = {
        "budget_code": ["کد بودجه", "کد", "ردیف", "budget_code", "code"],
        "description": ["شرح", "توضیحات", "عنوان", "description", "title"],
        "trustee": ["متولی", "مسئول", "trustee", "owner"],
        "allocated": ["مصوب", "تخصیص", "اعتبار", "allocated", "budget"],
        "spent": ["هزینه", "مصرف", "spent", "used"],
        "remaining": ["مانده", "باقیمانده", "remaining", "balance"],
    }
    
    def __init__(self, file_path: str, sheet_name: Optional[str] = None):
        """
        Args:
            file_path: مسیر فایل اکسل
            sheet_name: نام شیت (اختیاری - اگر None باشد اولین شیت خوانده می‌شود)
        """
        self.file_path = file_path
        self.sheet_name = sheet_name
        self.df: Optional[pd.DataFrame] = None
        self.column_mapping: Dict[str, str] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def read_file(self) -> bool:
        """خواندن فایل اکسل"""
        try:
            self.df = pd.read_excel(
                self.file_path,
                sheet_name=self.sheet_name or 0,
                dtype=str  # همه داده‌ها به صورت رشته خوانده شوند
            )
            # حذف سطرهای خالی
            self.df.dropna(how='all', inplace=True)
            return True
        except Exception as e:
            self.errors.append(f"خطا در خواندن فایل: {e}")
            return False
    
    def detect_columns(self) -> Dict[str, str]:
        """
        تشخیص خودکار ستون‌ها بر اساس نام‌های احتمالی
        
        Returns:
            دیکشنری mapping از نام استاندارد به نام واقعی ستون
        """
        if self.df is None:
            return {}
        
        mapping = {}
        columns_lower = {col.strip().lower(): col for col in self.df.columns}
        
        for field, possible_names in self.EXPECTED_COLUMNS.items():
            for name in possible_names:
                if name.lower() in columns_lower:
                    mapping[field] = columns_lower[name.lower()]
                    break
        
        self.column_mapping = mapping
        return mapping
    
    def clean_budget_code(self, raw_code: Any) -> Optional[str]:
        """
        تمیزکاری و استانداردسازی کد بودجه
        
        Args:
            raw_code: کد خام از اکسل
            
        Returns:
            کد بودجه ۶ رقمی یا None
        """
        if pd.isna(raw_code) or raw_code is None:
            return None
        
        # تبدیل به رشته و حذف کاراکترهای اضافی
        code_str = str(raw_code).strip()
        
        # حذف کاراکترهای غیرعددی به جز خط تیره
        code_str = re.sub(r'[^\d-]', '', code_str)
        
        # اگر خط تیره دارد، بخش اول را بگیر
        if '-' in code_str:
            code_str = code_str.split('-')[0]
        
        # حذف صفرهای اضافی ابتدا و سپس padding به ۶ رقم
        if code_str:
            # حداقل ۴ و حداکثر ۶ رقم
            if len(code_str) < 4:
                return None
            return code_str[:6].zfill(6)
        
        return None
    
    def clean_amount(self, raw_amount: Any) -> float:
        """
        تمیزکاری مبالغ ریالی
        
        Args:
            raw_amount: مبلغ خام
            
        Returns:
            مبلغ به صورت float
        """
        if pd.isna(raw_amount) or raw_amount is None:
            return 0.0
        
        # تبدیل به رشته
        amount_str = str(raw_amount)
        
        # حذف کاما و فاصله
        amount_str = amount_str.replace(',', '').replace(' ', '')
        
        # تبدیل اعداد فارسی به انگلیسی
        persian_nums = '۰۱۲۳۴۵۶۷۸۹'
        english_nums = '0123456789'
        for p, e in zip(persian_nums, english_nums):
            amount_str = amount_str.replace(p, e)
        
        # حذف کاراکترهای غیرعددی
        amount_str = re.sub(r'[^\d.]', '', amount_str)
        
        try:
            return float(amount_str) if amount_str else 0.0
        except ValueError:
            return 0.0
    
    def parse_trustee(self, raw_trustee: Any) -> Optional[int]:
        """
        تبدیل متولی به section_id
        
        Args:
            raw_trustee: نام یا کد متولی
            
        Returns:
            ID قسمت مربوطه یا None
        """
        if pd.isna(raw_trustee) or raw_trustee is None:
            return None
        
        trustee_str = str(raw_trustee).strip()
        
        # جستجو در دیتابیس برای پیدا کردن قسمت مربوطه
        db = SessionLocal()
        try:
            # ابتدا جستجو با کد
            section = db.query(models.OrgUnit).filter(
                models.OrgUnit.code == trustee_str
            ).first()
            
            # سپس جستجو با عنوان
            if not section:
                section = db.query(models.OrgUnit).filter(
                    models.OrgUnit.title.contains(trustee_str)
                ).first()
            
            return section.id if section else None
        finally:
            db.close()
    
    def process_row(self, row: pd.Series) -> Optional[Dict[str, Any]]:
        """
        پردازش یک سطر از اکسل
        
        Args:
            row: سطر DataFrame
            
        Returns:
            دیکشنری داده‌های پردازش شده یا None
        """
        # استخراج کد بودجه
        raw_code = row.get(self.column_mapping.get("budget_code", ""), None)
        budget_code = self.clean_budget_code(raw_code)
        
        if not budget_code:
            return None  # سطر بدون کد بودجه معتبر
        
        # استخراج سایر فیلدها
        return {
            "budget_code": budget_code,
            "description": str(row.get(self.column_mapping.get("description", ""), "")).strip(),
            "trustee_section_id": self.parse_trustee(
                row.get(self.column_mapping.get("trustee", ""), None)
            ),
            "allocated_1403": self.clean_amount(
                row.get(self.column_mapping.get("allocated", ""), 0)
            ),
            "spent_1403": self.clean_amount(
                row.get(self.column_mapping.get("spent", ""), 0)
            ),
            "remaining_budget": self.clean_amount(
                row.get(self.column_mapping.get("remaining", ""), 0)
            ),
        }
    
    def import_to_db(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Import داده‌ها به دیتابیس
        
        Args:
            dry_run: اگر True باشد، فقط پردازش انجام شده و در DB ذخیره نمی‌شود
            
        Returns:
            دیکشنری نتایج import
        """
        results = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "updated": 0,
            "errors": [],
            "processed_items": []
        }
        
        # خواندن فایل
        if not self.read_file():
            results["errors"] = self.errors
            return results
        
        # تشخیص ستون‌ها
        self.detect_columns()
        
        if not self.column_mapping.get("budget_code"):
            results["errors"].append("ستون کد بودجه پیدا نشد")
            return results
        
        db = SessionLocal()
        try:
            for idx, row in self.df.iterrows():
                processed = self.process_row(row)
                
                if not processed:
                    results["skipped"] += 1
                    continue
                
                results["processed_items"].append(processed)
                
                if dry_run:
                    results["success"] += 1
                    continue
                
                # بررسی وجود رکورد قبلی
                existing = db.query(models.BudgetItem).filter(
                    models.BudgetItem.budget_code == processed["budget_code"]
                ).first()
                
                if existing:
                    # به‌روزرسانی
                    for key, value in processed.items():
                        if value is not None:
                            setattr(existing, key, value)
                    results["updated"] += 1
                else:
                    # ایجاد جدید
                    item = models.BudgetItem(**processed)
                    db.add(item)
                    results["success"] += 1
            
            if not dry_run:
                db.commit()
                
        except Exception as e:
            results["errors"].append(f"خطا در ذخیره: {e}")
            results["failed"] += 1
            db.rollback()
        finally:
            db.close()
        
        results["errors"].extend(self.errors)
        return results
    
    def preview(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        پیش‌نمایش داده‌های پردازش شده
        
        Args:
            limit: تعداد سطرهای نمایش
            
        Returns:
            لیست داده‌های پردازش شده
        """
        return self.import_to_db(dry_run=True)["processed_items"][:limit]
