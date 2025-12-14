from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, DateTime, Boolean, Enum, JSON
from sqlalchemy.orm import relationship, backref
from app.database import Base
from datetime import datetime

# --- جداول پایه ---
class OrgUnit(Base):
    __tablename__ = "org_units"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    code = Column(String, index=True)
    parent_id = Column(Integer, ForeignKey("org_units.id"), nullable=True)
    org_type = Column(String)
    
class BudgetRef(Base):
    __tablename__ = "budget_refs"
    id = Column(Integer, primary_key=True, index=True)
    zone_raw = Column(String, index=True)
    budget_code = Column(String, index=True)
    title = Column(String)
    row_type = Column(String)
    deputy = Column(String, nullable=True)

# --- جداول جدید برای پرتابل ---

# 1. رویدادهای مالی (تامین اعتبار، پیش‌پرداخت...)
class FinancialEventRef(Base):
    __tablename__ = "financial_event_refs"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True) 
    title = Column(String)

# 2. اقدامات مستمر (از فایل اکسل استخراج می‌شود)
class ContinuousAction(Base):
    __tablename__ = "continuous_actions"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True) # مثلاً CA-001
    title = Column(String, index=True)

# 3. مراکز هزینه (فعلاً خالی یا از گزارش استخراج می‌شود)
class CostCenterRef(Base):
    __tablename__ = "cost_center_refs"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, index=True)
    title = Column(String)

# 4. سرفصل حساب (اختیاری)
class FinancialAccountRef(Base):
    __tablename__ = "financial_account_refs"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, index=True)
    title = Column(String)

# --- جدول اصلی تراکنش‌ها ---
class SpecialAction(Base):
    __tablename__ = "special_actions"
    id = Column(Integer, primary_key=True, index=True)
    unique_code = Column(String, unique=True, index=True)
    org_unit_id = Column(Integer, nullable=True) # برای سادگی nullable کردیم
    amount = Column(Float)
    local_record_id = Column(String, index=True)
    description = Column(String, nullable=True)
    action_date = Column(Date, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class FinancialDocument(Base):
    __tablename__ = "financial_documents"
    id = Column(Integer, primary_key=True, index=True)
    zone_code = Column(String, index=True)
    doc_number = Column(Integer)
    description = Column(String)
    beneficiary = Column(String)
    amount = Column(String, nullable=True)
    debit = Column(String, nullable=True)
    credit = Column(String, nullable=True)
    budget_code = Column(String, index=True, nullable=True)
    
    # Extra columns for Test Mode / Source Verification
    rad_code = Column(String, nullable=True) # RadJNo
    tit_code = Column(String, nullable=True) # TitTNo
    tit_title = Column(String, nullable=True) # TitTNam
    opr_code = Column(String, nullable=True) # OprCod
    requests = Column(String, nullable=True) # Requests
    
    date_str = Column(String, default="1403")

# --- جدول مرجع بودجه جدید (از دو فایل اکسل) ---
class BudgetItem(Base):
    """
    Combined budget reference from:
    - اعتبارات هزینه‌ای.xlsx
    - تملک دارایی سرمایه‌ای.xlsx
    """
    __tablename__ = "budget_items"
    id = Column(Integer, primary_key=True, index=True)
    budget_code = Column(String, index=True, unique=True)  # کد بودجه
    description = Column(String)  # شرح ردیف
    budget_type = Column(String)  # "expense" (هزینه‌ای) or "capital" (سرمایه‌ای)
    zone = Column(String, nullable=True, index=True)  # منطقه (متن)
    zone_code = Column(String, nullable=True, index=True)  # کد منطقه (عددی)
    trustee = Column(String, nullable=True, index=True)  # متولی (متن)
    trustee_section_id = Column(Integer, ForeignKey("org_units.id"), nullable=True)  # ارتباط با قسمت متولی
    subject = Column(String, nullable=True, index=True)  # موضوع
    sub_subject = Column(String, nullable=True)  # زیرموضوع
    row_type = Column(String, default="مستمر", index=True)  # مستمر/غیرمستمر
    approved_1403 = Column(Float, nullable=True)  # مصوب 1403
    allocated_1403 = Column(Float, nullable=True)  # تخصیص 1403
    spent_1403 = Column(Float, nullable=True)  # هزینه 1403
    reserved_amount = Column(Float, default=0)  # مبلغ رزرو شده (pending transactions)
    remaining_budget = Column(Float, nullable=True)  # مانده قابل استفاده
    
    # Relationship
    trustee_section = relationship("OrgUnit", foreign_keys=[trustee_section_id])



# --- جداول کاربری و احراز هویت ---

class User(Base):
    """کاربران سیستم (کاربر عادی یا ادمین)"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    full_name = Column(String)
    role = Column(String, default="user")  # "user" or "admin"
    
    # اطلاعات پیش‌فرض کاربر
    default_zone_id = Column(Integer, ForeignKey("org_units.id"), nullable=True)
    default_dept_id = Column(Integer, ForeignKey("org_units.id"), nullable=True)
    default_section_id = Column(Integer, ForeignKey("org_units.id"), nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    default_zone = relationship("OrgUnit", foreign_keys=[default_zone_id])
    default_dept = relationship("OrgUnit", foreign_keys=[default_dept_id])
    default_section = relationship("OrgUnit", foreign_keys=[default_section_id])


class UserBudgetAccess(Base):
    """دسترسی کاربر به ردیف‌های بودجه"""
    __tablename__ = "user_budget_access"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    budget_item_id = Column(Integer, ForeignKey("budget_items.id"))
    
    user = relationship("User", backref="budget_accesses")
    budget_item = relationship("BudgetItem", backref="user_accesses")


# --- تراکنش‌های مالی با workflow ---

class Transaction(Base):
    """تراکنش‌های مالی با workflow تایید"""
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    unique_code = Column(String, unique=True, index=True)
    
    # وضعیت: draft -> pending -> approved/rejected -> paid
    status = Column(String, default="draft", index=True)
    
    # ایجادکننده
    created_by_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # تایید/رد
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)
    
    # اطلاعات سازمانی
    zone_id = Column(Integer, ForeignKey("org_units.id"))
    department_id = Column(Integer, ForeignKey("org_units.id"), nullable=True)
    section_id = Column(Integer, ForeignKey("org_units.id"), nullable=True)
    
    # اطلاعات بودجه و مالی
    budget_item_id = Column(Integer, ForeignKey("budget_items.id"))
    cost_center_id = Column(Integer, ForeignKey("cost_center_refs.id"), nullable=True)
    continuous_action_id = Column(Integer, ForeignKey("continuous_actions.id"), nullable=True)
    financial_event_id = Column(Integer, ForeignKey("financial_event_refs.id"), nullable=True)
    
    # مشخصات تراکنش
    amount = Column(Float)
    beneficiary_name = Column(String)
    contract_number = Column(String, nullable=True)
    special_activity = Column(String, nullable=True)
    description = Column(String, nullable=True)
    
    # جزئیات اضافی (JSON برای فرم‌های پیچیده)
    form_data = Column(JSON, nullable=True)
    
    # سال مالی
    fiscal_year = Column(String, default="1403")
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id], backref="created_transactions")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id], backref="reviewed_transactions")
    zone = relationship("OrgUnit", foreign_keys=[zone_id])
    department = relationship("OrgUnit", foreign_keys=[department_id])
    section = relationship("OrgUnit", foreign_keys=[section_id])
    budget_item = relationship("BudgetItem", backref="transactions")
    cost_center = relationship("CostCenterRef")
    continuous_action = relationship("ContinuousAction")
    financial_event = relationship("FinancialEventRef")


# --- کدهای یکتا حسابداری (کدیکتا) ---

class AccountCode(Base):
    """کدهای یکتا تولید شده توسط آداپتور کدیکتا"""
    __tablename__ = "account_codes"
    id = Column(Integer, primary_key=True, index=True)
    
    # کد یکتا اصلی
    unique_code = Column(String, unique=True, index=True)  # مثال: 20-EXP-11020401-611-0001
    
    # اجزای کد
    zone_code = Column(String, index=True)           # کد منطقه
    category = Column(String, index=True)            # دسته معامله (EXP, SAL, CON, ...)
    budget_code = Column(String, index=True)         # کد بودجه اصلی
    permanent_code = Column(String, index=True)      # کد حساب دائمی
    sequence = Column(Integer)                       # شماره ترتیب
    
    # اطلاعات تکمیلی
    request_id = Column(String, index=True)          # شماره درخواست
    transaction_type = Column(String)                # نوع معامله (TypDesc)
    total_amount = Column(Float)                     # مبلغ کل
    
    # آمار حساب‌ها
    temp_account_count = Column(Integer, default=0)  # تعداد حساب موقت
    perm_account_count = Column(Integer, default=0)  # تعداد حساب دائمی
    bank_account_count = Column(Integer, default=0)  # تعداد حساب بانکی
    is_balanced = Column(Boolean, default=True)      # آیا تراز است
    
    # زمان ایجاد
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # جزئیات اضافی (JSON)
    details = Column(JSON, nullable=True)


class TemporaryAccountRecord(Base):
    """حساب‌های موقت (با کد بودجه)"""
    __tablename__ = "temporary_account_records"
    id = Column(Integer, primary_key=True, index=True)
    
    account_code_id = Column(Integer, ForeignKey("account_codes.id"))
    budget_code = Column(String, index=True)
    request_id = Column(String, index=True)
    debit_amount = Column(Float, default=0)
    credit_amount = Column(Float, default=0)
    transaction_type = Column(String)
    zone_code = Column(String)
    titk_code = Column(Integer)
    titk_name = Column(String)
    category = Column(String)
    
    account_code = relationship("AccountCode", backref="temporary_accounts")


class PermanentAccountRecord(Base):
    """حساب‌های دائمی (بدون کد بودجه)"""
    __tablename__ = "permanent_account_records"
    id = Column(Integer, primary_key=True, index=True)
    
    account_code_id = Column(Integer, ForeignKey("account_codes.id"))
    titk_code = Column(Integer, index=True)
    titk_name = Column(String)
    titm_code = Column(Integer)
    titt_code = Column(Integer)
    titj_code = Column(Integer)
    titj_name = Column(String)
    request_id = Column(String, index=True)
    debit_amount = Column(Float, default=0)
    credit_amount = Column(Float, default=0)
    is_bank = Column(Boolean, default=False)
    
    account_code = relationship("AccountCode", backref="permanent_accounts")

