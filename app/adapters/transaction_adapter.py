"""
Transaction Adapter
===================

آداپتر برای import و پردازش تراکنش‌های مالی از فایل‌های اکسل.
"""

import pandas as pd
import re
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal


class TransactionAdapter:
    """
    آداپتر برای پردازش تراکنش‌های مالی
    
    این آداپتر می‌تواند:
    - تراکنش‌های موجود را از اکسل بخواند
    - اطلاعات را پاکسازی و استانداردسازی کند
    - کد یکتا برای تراکنش‌ها تولید کند
    """
    
    def __init__(self, file_path: str, sheet_name: Optional[str] = None):
        self.file_path = file_path
        self.sheet_name = sheet_name
        self.df: Optional[pd.DataFrame] = None
        self.errors: List[str] = []
    
    def read_file(self) -> bool:
        """خواندن فایل اکسل"""
        try:
            self.df = pd.read_excel(
                self.file_path,
                sheet_name=self.sheet_name or 0,
                dtype=str
            )
            self.df.dropna(how='all', inplace=True)
            return True
        except Exception as e:
            self.errors.append(f"خطا در خواندن فایل: {e}")
            return False
    
    def clean_amount(self, raw_amount: Any) -> float:
        """تمیزکاری مبالغ"""
        if pd.isna(raw_amount) or raw_amount is None:
            return 0.0
        
        amount_str = str(raw_amount)
        amount_str = amount_str.replace(',', '').replace(' ', '')
        
        # تبدیل اعداد فارسی
        persian_nums = '۰۱۲۳۴۵۶۷۸۹'
        english_nums = '0123456789'
        for p, e in zip(persian_nums, english_nums):
            amount_str = amount_str.replace(p, e)
        
        amount_str = re.sub(r'[^\d.]', '', amount_str)
        
        try:
            return float(amount_str) if amount_str else 0.0
        except ValueError:
            return 0.0
    
    def find_budget_code(self, row: pd.Series, columns: List[str]) -> Optional[str]:
        """
        جستجوی کد بودجه در ستون‌های مختلف
        
        Args:
            row: سطر DataFrame
            columns: لیست نام ستون‌های احتمالی
            
        Returns:
            کد بودجه یا None
        """
        for col in columns:
            if col in row.index:
                value = row[col]
                if pd.notna(value):
                    # استخراج الگوی کد بودجه (۴-۶ رقم)
                    match = re.search(r'\b(\d{4,6})\b', str(value))
                    if match:
                        return match.group(1).zfill(6)[:6]
        return None
    
    def find_beneficiary(self, row: pd.Series, columns: List[str]) -> str:
        """جستجوی نام ذینفع"""
        for col in columns:
            if col in row.index:
                value = row[col]
                if pd.notna(value) and str(value).strip():
                    return str(value).strip()
        return "نامشخص"
    
    def analyze_file(self) -> Dict[str, Any]:
        """
        آنالیز فایل برای تشخیص ساختار
        
        Returns:
            اطلاعات تحلیلی فایل
        """
        if not self.read_file():
            return {"error": self.errors}
        
        analysis = {
            "total_rows": len(self.df),
            "columns": list(self.df.columns),
            "column_types": {},
            "sample_values": {},
            "potential_mappings": {}
        }
        
        # نمونه مقادیر هر ستون
        for col in self.df.columns:
            non_null = self.df[col].dropna()
            analysis["sample_values"][col] = list(non_null.head(3))
            
            # تشخیص نوع ستون
            sample = str(non_null.iloc[0]) if len(non_null) > 0 else ""
            
            if re.match(r'^\d{4,6}$', sample.strip()):
                analysis["potential_mappings"][col] = "budget_code"
            elif re.match(r'^[\d,]+$', sample.replace('.', '')):
                analysis["potential_mappings"][col] = "amount"
            elif "نام" in col or "ذی" in col:
                analysis["potential_mappings"][col] = "beneficiary"
            elif "تاریخ" in col:
                analysis["potential_mappings"][col] = "date"
            elif "شرح" in col or "توضیح" in col:
                analysis["potential_mappings"][col] = "description"
        
        return analysis
    
    def process_transactions(
        self,
        column_mapping: Dict[str, str],
        zone_id: int,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        پردازش و ایجاد تراکنش‌ها
        
        Args:
            column_mapping: نگاشت ستون‌ها (budget_code, amount, beneficiary, etc.)
            zone_id: ID منطقه پیش‌فرض
            dry_run: فقط پیش‌نمایش
            
        Returns:
            نتایج پردازش
        """
        results = {
            "processed": 0,
            "skipped": 0,
            "errors": [],
            "transactions": []
        }
        
        if self.df is None:
            if not self.read_file():
                results["errors"] = self.errors
                return results
        
        db = SessionLocal()
        try:
            for idx, row in self.df.iterrows():
                try:
                    budget_code = None
                    if "budget_code" in column_mapping:
                        raw_code = row.get(column_mapping["budget_code"])
                        if pd.notna(raw_code):
                            match = re.search(r'\b(\d{4,6})\b', str(raw_code))
                            if match:
                                budget_code = match.group(1).zfill(6)[:6]
                    
                    if not budget_code:
                        results["skipped"] += 1
                        continue
                    
                    amount = 0.0
                    if "amount" in column_mapping:
                        amount = self.clean_amount(row.get(column_mapping["amount"]))
                    
                    beneficiary = "نامشخص"
                    if "beneficiary" in column_mapping:
                        val = row.get(column_mapping["beneficiary"])
                        if pd.notna(val):
                            beneficiary = str(val).strip()
                    
                    transaction_data = {
                        "budget_code": budget_code,
                        "amount": amount,
                        "beneficiary_name": beneficiary,
                        "zone_id": zone_id,
                        "status": "pending"
                    }
                    
                    results["transactions"].append(transaction_data)
                    results["processed"] += 1
                    
                except Exception as e:
                    results["errors"].append(f"سطر {idx}: {e}")
            
            if not dry_run and results["transactions"]:
                # ذخیره در دیتابیس
                for t_data in results["transactions"]:
                    # پیدا کردن budget_item
                    budget_item = db.query(models.BudgetItem).filter(
                        models.BudgetItem.budget_code == t_data["budget_code"]
                    ).first()
                    
                    t = models.Transaction(
                        status=t_data["status"],
                        zone_id=t_data["zone_id"],
                        budget_item_id=budget_item.id if budget_item else None,
                        amount=t_data["amount"],
                        beneficiary_name=t_data["beneficiary_name"]
                    )
                    db.add(t)
                
                db.commit()
        
        finally:
            db.close()
        
        return results
