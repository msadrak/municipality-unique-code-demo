"""
Account Code Adapter (آداپتور کدیکتا)
=====================================

این آداپتور برای پردازش داده‌های حسابداری شهرداری و تولید کد یکتا استفاده می‌شود.

وظایف:
1. خواندن فایل اکسل
2. تفکیک حساب‌های موقت (با کد بودجه) و دائمی (بدون کد بودجه)
3. دسته‌بندی معاملات
4. ایجاد رابطه بین حساب‌های موقت و دائمی
5. تولید کد یکتا
"""

import pandas as pd
import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class TransactionCategory(Enum):
    """دسته‌بندی معاملات"""
    CURRENT_EXPENSE = "EXP"      # هزینه‌های جاری
    CAPITAL_EXPENSE = "CAP"     # هزینه‌های عمرانی/سرمایه‌ای
    CONTRACTOR = "CON"          # پیمانکاران
    REVOLVING = "REV"           # تنخواه گردان
    SALARY = "SAL"              # حقوق و دستمزد
    WITHDRAWAL = "WDR"          # برداشت از بانک
    RECEIPT = "REC"             # دریافت
    ADJUSTMENT = "ADJ"          # اصلاحی
    OTHER = "OTH"               # سایر


@dataclass
class TemporaryAccount:
    """حساب موقت - دارای کد بودجه"""
    budget_code: str
    request_id: str
    debit_amount: float
    credit_amount: float
    transaction_type: str
    zone_code: str
    titk_code: int
    titk_name: str
    category: TransactionCategory = None
    
    @property
    def net_amount(self) -> float:
        return self.debit_amount - self.credit_amount


@dataclass 
class PermanentAccount:
    """حساب دائمی - بدون کد بودجه"""
    titk_code: int           # کد کل
    titk_name: str
    titm_code: int           # کد معین
    titt_code: int           # کد تفصیلی
    titj_code: int           # کد جزء
    titj_name: str
    request_id: str
    debit_amount: float
    credit_amount: float
    is_bank: bool = False
    
    @property
    def net_amount(self) -> float:
        return self.debit_amount - self.credit_amount


@dataclass
class AccountRelationship:
    """رابطه بین حساب موقت و دائمی"""
    request_id: str
    temporary_accounts: List[TemporaryAccount] = field(default_factory=list)
    permanent_accounts: List[PermanentAccount] = field(default_factory=list)
    bank_accounts: List[PermanentAccount] = field(default_factory=list)
    transaction_type: str = ""
    zone_code: str = ""
    
    @property
    def is_balanced(self) -> bool:
        all_accounts = self.temporary_accounts + self.permanent_accounts + self.bank_accounts
        total_debit = sum(a.debit_amount for a in all_accounts)
        total_credit = sum(a.credit_amount for a in all_accounts)
        return abs(total_debit - total_credit) < 1
    
    @property
    def total_amount(self) -> float:
        return sum(abs(a.net_amount) for a in self.temporary_accounts)


class AccountCodeAdapter:
    """
    آداپتور اصلی کدیکتا
    
    این آداپتور فایل اکسل را می‌خواند و:
    1. حساب‌های موقت و دائمی را جدا می‌کند
    2. رابطه بین آن‌ها را مشخص می‌کند
    3. کد یکتا تولید می‌کند
    """
    
    # الگوهای تشخیص دسته معامله
    CATEGORY_PATTERNS = {
        TransactionCategory.SALARY: ['حقوق', 'پرسنل', 'دستمزد'],
        TransactionCategory.CONTRACTOR: ['پيمانكار', 'صورت وضعيت', 'پیمانکار'],
        TransactionCategory.REVOLVING: ['تنخواه', 'علي الحساب'],
        TransactionCategory.CAPITAL_EXPENSE: ['عمراني', 'سرمایه', 'تملک'],
        TransactionCategory.CURRENT_EXPENSE: ['هزينه', 'جاري', 'هزینه'],
        TransactionCategory.WITHDRAWAL: ['برداشت', 'واريزي'],
        TransactionCategory.RECEIPT: ['دريافت', 'وصول', 'درآمد'],
        TransactionCategory.ADJUSTMENT: ['اصلاح', 'پايان دوره'],
    }
    
    def __init__(self, file_path: str, sheet_name: Optional[str] = None):
        self.file_path = file_path
        self.sheet_name = sheet_name
        self.df: Optional[pd.DataFrame] = None
        self.temporary_accounts: List[TemporaryAccount] = []
        self.permanent_accounts: List[PermanentAccount] = []
        self.relationships: Dict[str, AccountRelationship] = {}
        
    def read_file(self) -> bool:
        """خواندن فایل اکسل"""
        try:
            if self.sheet_name:
                self.df = pd.read_excel(self.file_path, sheet_name=self.sheet_name, engine='openpyxl')
            else:
                self.df = pd.read_excel(self.file_path, engine='openpyxl')
            
            print(f"✅ فایل خوانده شد: {len(self.df):,} ردیف")
            return True
        except Exception as e:
            print(f"❌ خطا در خواندن فایل: {e}")
            return False
    
    def classify_transaction(self, typ_desc: str) -> TransactionCategory:
        """دسته‌بندی معامله بر اساس توضیحات"""
        if pd.isna(typ_desc):
            return TransactionCategory.OTHER
            
        typ_desc_lower = str(typ_desc).lower()
        
        for category, patterns in self.CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if pattern in typ_desc_lower:
                    return category
        
        return TransactionCategory.OTHER
    
    def extract_accounts(self) -> Tuple[int, int]:
        """استخراج حساب‌های موقت و دائمی"""
        if self.df is None:
            raise ValueError("ابتدا فایل را بخوانید")
        
        self.temporary_accounts = []
        self.permanent_accounts = []
        
        for _, row in self.df.iterrows():
            request_id = str(row.get('Requests', ''))
            zone_code = str(row.get('AreaNo', ''))
            titk_code = int(row.get('TitkNo', 0)) if pd.notna(row.get('TitkNo')) else 0
            titk_name = str(row.get('TitkNam', ''))
            debit = float(row.get('DebitAmnt', 0)) if pd.notna(row.get('DebitAmnt')) else 0
            credit = float(row.get('CreditAmnt', 0)) if pd.notna(row.get('CreditAmnt')) else 0
            typ_desc = str(row.get('TypDesc', ''))
            budget_code = row.get('BodgetNo')
            
            if pd.notna(budget_code):
                # حساب موقت
                category = self.classify_transaction(typ_desc)
                temp_acc = TemporaryAccount(
                    budget_code=str(budget_code),
                    request_id=request_id,
                    debit_amount=debit,
                    credit_amount=credit,
                    transaction_type=typ_desc,
                    zone_code=zone_code,
                    titk_code=titk_code,
                    titk_name=titk_name,
                    category=category
                )
                self.temporary_accounts.append(temp_acc)
            else:
                # حساب دائمی
                perm_acc = PermanentAccount(
                    titk_code=titk_code,
                    titk_name=titk_name,
                    titm_code=int(row.get('TitMNo', 0)) if pd.notna(row.get('TitMNo')) else 0,
                    titt_code=int(row.get('TitTNo', 0)) if pd.notna(row.get('TitTNo')) else 0,
                    titj_code=int(row.get('TitJNo', 0)) if pd.notna(row.get('TitJNo')) else 0,
                    titj_name=str(row.get('TitJNam', '')),
                    request_id=request_id,
                    debit_amount=debit,
                    credit_amount=credit,
                    is_bank=(titk_code == 611)
                )
                self.permanent_accounts.append(perm_acc)
        
        print(f"✅ استخراج شد: {len(self.temporary_accounts):,} موقت | {len(self.permanent_accounts):,} دائمی")
        return len(self.temporary_accounts), len(self.permanent_accounts)
    
    def build_relationships(self) -> int:
        """ساخت رابطه بین حساب‌های موقت و دائمی بر اساس Request ID"""
        self.relationships = {}
        
        # گروه‌بندی حساب‌های موقت بر اساس request_id
        temp_by_request = defaultdict(list)
        for acc in self.temporary_accounts:
            temp_by_request[acc.request_id].append(acc)
        
        # گروه‌بندی حساب‌های دائمی بر اساس request_id
        perm_by_request = defaultdict(list)
        for acc in self.permanent_accounts:
            perm_by_request[acc.request_id].append(acc)
        
        # فقط درخواست‌هایی که حساب موقت دارند
        for request_id, temp_accounts in temp_by_request.items():
            perm_accounts = perm_by_request.get(request_id, [])
            bank_accounts = [a for a in perm_accounts if a.is_bank]
            other_perm = [a for a in perm_accounts if not a.is_bank]
            
            # تشخیص نوع معامله از اولین حساب موقت
            transaction_type = temp_accounts[0].transaction_type if temp_accounts else ""
            zone_code = temp_accounts[0].zone_code if temp_accounts else ""
            
            rel = AccountRelationship(
                request_id=request_id,
                temporary_accounts=temp_accounts,
                permanent_accounts=other_perm,
                bank_accounts=bank_accounts,
                transaction_type=transaction_type,
                zone_code=zone_code
            )
            self.relationships[request_id] = rel
        
        print(f"✅ ساخت رابطه: {len(self.relationships):,} درخواست")
        return len(self.relationships)
    
    def generate_unique_code(self, relationship: AccountRelationship, sequence: int = 1) -> str:
        """
        تولید کد یکتا
        
        فرمت: {Zone}-{Category}-{BudgetCode}-{PermanentCode}-{Sequence}
        مثال: 20-SAL-11020401-611-0001
        """
        # منطقه
        zone = relationship.zone_code.zfill(2)
        
        # دسته معامله
        category = TransactionCategory.OTHER
        if relationship.temporary_accounts:
            category = relationship.temporary_accounts[0].category or TransactionCategory.OTHER
        
        # کد بودجه اصلی (اولین یا بزرگترین)
        budget_code = "00000000"
        if relationship.temporary_accounts:
            # انتخاب کد بودجه با بیشترین مبلغ
            sorted_temp = sorted(
                relationship.temporary_accounts, 
                key=lambda x: abs(x.net_amount), 
                reverse=True
            )
            budget_code = sorted_temp[0].budget_code.replace('.0', '')
        
        # کد حساب دائمی اصلی (ترجیحاً بانک)
        perm_code = "000"
        if relationship.bank_accounts:
            perm_code = str(relationship.bank_accounts[0].titk_code)
        elif relationship.permanent_accounts:
            perm_code = str(relationship.permanent_accounts[0].titk_code)
        
        # شماره ترتیب
        seq = str(sequence).zfill(4)
        
        return f"{zone}-{category.value}-{budget_code}-{perm_code}-{seq}"
    
    def process(self) -> Dict[str, Any]:
        """پردازش کامل فایل"""
        print("=" * 60)
        print("🚀 شروع پردازش...")
        print("=" * 60)
        
        # 1. خواندن فایل
        if not self.read_file():
            return {"success": False, "error": "خطا در خواندن فایل"}
        
        # 2. استخراج حساب‌ها
        temp_count, perm_count = self.extract_accounts()
        
        # 3. ساخت روابط
        rel_count = self.build_relationships()
        
        # 4. تولید کدها
        unique_codes = []
        for i, (req_id, rel) in enumerate(self.relationships.items(), 1):
            code = self.generate_unique_code(rel, i)
            unique_codes.append({
                "request_id": req_id,
                "unique_code": code,
                "category": rel.temporary_accounts[0].category.value if rel.temporary_accounts else "OTH",
                "transaction_type": rel.transaction_type,
                "total_amount": rel.total_amount,
                "temp_count": len(rel.temporary_accounts),
                "perm_count": len(rel.permanent_accounts),
                "bank_count": len(rel.bank_accounts),
                "is_balanced": rel.is_balanced
            })
        
        print(f"✅ تولید کد: {len(unique_codes):,} کد یکتا")
        print("=" * 60)
        
        return {
            "success": True,
            "total_rows": len(self.df),
            "temporary_accounts": temp_count,
            "permanent_accounts": perm_count,
            "relationships": rel_count,
            "unique_codes": unique_codes
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """گزارش آماری"""
        if not self.relationships:
            return {}
        
        # آمار دسته‌بندی
        category_stats = defaultdict(int)
        for rel in self.relationships.values():
            if rel.temporary_accounts:
                cat = rel.temporary_accounts[0].category
                category_stats[cat.value if cat else "OTH"] += 1
        
        # آمار تراز
        balanced_count = sum(1 for r in self.relationships.values() if r.is_balanced)
        
        return {
            "total_relationships": len(self.relationships),
            "category_distribution": dict(category_stats),
            "balanced_requests": balanced_count,
            "unbalanced_requests": len(self.relationships) - balanced_count,
            "unique_budget_codes": len(set(a.budget_code for a in self.temporary_accounts))
        }


# تست سریع
if __name__ == "__main__":
    adapter = AccountCodeAdapter("_شهرداری مرکزی گزارش دفتر مرکزی1403.xlsx")
    result = adapter.process()
    
    if result["success"]:
        print("\n📊 نتایج:")
        print(f"  کل ردیف‌ها: {result['total_rows']:,}")
        print(f"  حساب‌های موقت: {result['temporary_accounts']:,}")
        print(f"  حساب‌های دائمی: {result['permanent_accounts']:,}")
        print(f"  روابط: {result['relationships']:,}")
        print(f"  کدهای یکتا: {len(result['unique_codes']):,}")
        
        stats = adapter.get_statistics()
        print(f"\n📈 آمار:")
        print(f"  دسته‌بندی: {stats['category_distribution']}")
        print(f"  متعادل: {stats['balanced_requests']:,}")
        print(f"  نامتعادل: {stats['unbalanced_requests']:,}")
        
        # نمونه کدها
        print("\n📝 نمونه کدهای یکتا:")
        for item in result["unique_codes"][:5]:
            print(f"  {item['unique_code']} → درخواست: {item['request_id']} | نوع: {item['category']}")
