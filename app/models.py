from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, DateTime, Boolean, Enum, JSON, CheckConstraint, BigInteger, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
from app.database import Base
from datetime import datetime
import enum


# --- Enums ---
class ActivityFrequency(enum.Enum):
    """فرکانس اجرای فعالیت"""
    DAILY = "DAILY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class OperationType(enum.Enum):
    """نوع عملیات بودجه برای ثبت در دفتر حسابداری"""
    BLOCK = "BLOCK"                 # رزرو اعتبار برای درخواست در انتظار
    RELEASE = "RELEASE"             # آزادسازی اعتبار رزرو شده (رد درخواست)
    SPEND = "SPEND"                 # تایید پرداخت (از رزرو به هزینه)
    INCREASE_BUDGET = "INCREASE_BUDGET"  # اصلاحیه بودجه


class HistoryAction(enum.Enum):
    """Action types for transaction history audit log"""
    SUBMIT = "SUBMIT"           # Initial submission by user
    APPROVE = "APPROVE"         # Approved by an admin level
    REJECT = "REJECT"           # Rejected and returned to user
    RESUBMIT = "RESUBMIT"       # Resubmitted after rejection


class AccountingStatus(enum.Enum):
    """Accounting posting state (separate from workflow)"""
    READY_TO_POST = "READY_TO_POST"
    POSTED = "POSTED"
    POST_ERROR = "POST_ERROR"


class AccountingEventType(enum.Enum):
    """Event types for accounting audit log"""
    POSTED = "POSTED"
    POST_FAILED = "POST_FAILED"
    EXPORTED = "EXPORTED"
    SNAPSHOT_CREATED = "SNAPSHOT_CREATED"

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
    org_unit_id = Column(Integer, ForeignKey("org_units.id"), nullable=True)
    amount = Column(Float)
    local_record_id = Column(String, index=True)
    description = Column(String, nullable=True)
    action_date = Column(Date, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship for eager loading
    org_unit = relationship("OrgUnit")
    
    @property
    def org_unit_title(self) -> str:
        """Computed property for schema compatibility - use with selectinload(SpecialAction.org_unit)."""
        return self.org_unit.title if self.org_unit else None

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


class OrgBudgetMap(Base):
    """
    Mapping table: links org context (zone_code) to allowed budgets, cost centers, continuous actions.
    Source: Hesabdary Information.xlsx
    """
    __tablename__ = "org_budget_map"
    id = Column(Integer, primary_key=True, index=True)
    zone_code = Column(String, index=True, nullable=False)
    budget_code = Column(String, index=True, nullable=True)
    cost_center_desc = Column(String, nullable=True)  # شرح مرکزهزینه
    continuous_action_desc = Column(String, nullable=True)  # شرح سرفصل حساب جزء


# --- سامانه‌های ۱۴ گانه ---

class Subsystem(Base):
    """
    سامانه‌های زیرمجموعه حسابداری (۱۴ سامانه)
    هر قسمت ممکن است ۱ تا چند سامانه را در اختیار داشته باشد
    """
    __tablename__ = "subsystems"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)  # PAYROLL, CONTRACTS, ...
    title = Column(String)  # حقوق و دستمزد، قراردادها، ...
    icon = Column(String, nullable=True)  # آیکون برای UI
    attachment_type = Column(String, default="upload")  # upload, api, both
    is_active = Column(Boolean, default=True)
    order = Column(Integer, default=0)  # ترتیب نمایش
    
    # Relationships
    activities = relationship("SubsystemActivity", back_populates="subsystem")


class SubsystemActivity(Base):
    """
    فعالیت‌های ویژه هر سامانه
    مثلاً: پرداخت حقوق، صدور چک، ثبت قرارداد، ...
    """
    __tablename__ = "subsystem_activities"
    id = Column(Integer, primary_key=True, index=True)
    subsystem_id = Column(Integer, ForeignKey("subsystems.id"))
    code = Column(String, index=True)  # SALARY_PAYMENT, CONTRACT_REGISTER, ...
    title = Column(String)  # پرداخت حقوق، ثبت قرارداد، ...
    form_type = Column(String, nullable=True)  # نوع فرم مخصوص (nullable = فرم عمومی)
    is_active = Column(Boolean, default=True)
    order = Column(Integer, default=0)
    
    # Service Catalog fields
    frequency = Column(Enum(ActivityFrequency), default=ActivityFrequency.MONTHLY)
    requires_file_upload = Column(Boolean, default=False)
    external_service_url = Column(String, nullable=True)  # URL for external API (e.g., PMIS)
    
    # Relationships
    subsystem = relationship("Subsystem", back_populates="activities")
    constraints = relationship("ActivityConstraint", back_populates="activity")


# --- ارتباط قسمت با سامانه‌ها ---

class SectionSubsystemAccess(Base):
    """
    ارتباط قسمت‌های سازمانی با سامانه‌ها
    هر قسمت می‌تواند به یک یا چند سامانه دسترسی داشته باشد
    """
    __tablename__ = "section_subsystem_access"
    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("org_units.id"))
    subsystem_id = Column(Integer, ForeignKey("subsystems.id"))
    
    # Relationships
    section = relationship("OrgUnit")
    subsystem = relationship("Subsystem")


class ActivityConstraint(Base):
    """
    Constraint Engine: defines valid Budget/CostCenter combinations per activity.
    
    Examples:
    - Activity "SALARY_PAYMENT" → budget_code_pattern="1%"  (starts with 1)
    - Activity "CONTRACT_REGISTER" → allowed_budget_types=["capital"]
    
    این جدول ترکیبات معتبر بودجه و مرکز هزینه را برای هر فعالیت تعریف می‌کند
    """
    __tablename__ = "activity_constraints"
    id = Column(Integer, primary_key=True, index=True)
    
    # Link to activity
    subsystem_activity_id = Column(Integer, ForeignKey("subsystem_activities.id"), nullable=False)
    
    # Budget constraints (mutually exclusive)
    budget_code_pattern = Column(String, nullable=True)     # SQL LIKE pattern, e.g., "1%"
    allowed_budget_types = Column(JSON, nullable=True)      # ["expense"] or ["capital"]
    
    # Cost Center constraints
    cost_center_pattern = Column(String, nullable=True)     # SQL LIKE pattern
    allowed_cost_centers = Column(JSON, nullable=True)      # List of specific IDs
    
    # Metadata
    constraint_type = Column(String, default="INCLUDE")     # INCLUDE or EXCLUDE
    priority = Column(Integer, default=0)                   # Higher = applied first
    description = Column(String, nullable=True)             # Admin description
    is_active = Column(Boolean, default=True)
    
    # Relationship
    activity = relationship("SubsystemActivity", back_populates="constraints")




# --- جداول کاربری و احراز هویت ---

class User(Base):
    """کاربران سیستم با نقش‌های چند سطحی
    
    نقش‌ها:
    - USER: کاربر عادی (ایجاد درخواست)
    - ADMIN_L1: متولی قسمت (تایید سطح ۱)
    - ADMIN_L2: ادمین اداره (تایید سطح ۲)
    - ADMIN_L3: ادمین حوزه (تایید سطح ۳)
    - ADMIN_L4: ذی‌حساب (تایید نهایی)
    - ACCOUNTANT: حسابدار (ثبت سند)
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    full_name = Column(String)
    role = Column(String, default="USER")  # USER, ADMIN_L1, ADMIN_L2, ADMIN_L3, ADMIN_L4, ACCOUNTANT
    
    # سطح ادمین (فقط برای نقش‌های ADMIN_L*)
    # 1=قسمت, 2=اداره, 3=حوزه, 4=ذی‌حساب
    admin_level = Column(Integer, nullable=True)
    
    # سامانه‌هایی که این ادمین مسئول آن‌هاست (فقط برای ADMIN_L1)
    # مثال: [1, 3, 5] یعنی حقوق، تنخواه، ضمانت‌نامه
    managed_subsystem_ids = Column(JSON, nullable=True)
    
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
    
    # RBAC: Subsystem access control (DENY ALL if empty)
    subsystem_access_list = relationship("UserSubsystemAccess", back_populates="user", cascade="all, delete-orphan")



class UserBudgetAccess(Base):
    """دسترسی کاربر به ردیف‌های بودجه"""
    __tablename__ = "user_budget_access"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    budget_item_id = Column(Integer, ForeignKey("budget_items.id"))
    
    user = relationship("User", backref="budget_accesses")
    budget_item = relationship("BudgetItem", backref="user_accesses")


class UserSubsystemAccess(Base):
    """
    دسترسی کاربر به زیرسامانه‌ها (RBAC)
    
    هر کاربر می‌تواند به یک یا چند زیرسامانه دسترسی داشته باشد.
    اگر کاربر هیچ رکوردی در این جدول نداشته باشد، به هیچ سامانه‌ای دسترسی ندارد (DENY ALL).
    """
    __tablename__ = "user_subsystem_access"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subsystem_id = Column(Integer, ForeignKey("subsystems.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    
    # Ensure one user can't be assigned the same subsystem twice
    __table_args__ = (
        UniqueConstraint('user_id', 'subsystem_id', name='user_subsystem_unique'),
    )
    
    # Relationships
    user = relationship("User", back_populates="subsystem_access_list")
    subsystem = relationship("Subsystem")


# --- تراکنش‌های مالی با workflow ---

class Transaction(Base):
    """تراکنش‌های مالی با workflow تایید چهار سطحی
    
    گردش کار:
    DRAFT → PENDING_L1 → PENDING_L2 → PENDING_L3 → PENDING_L4 → APPROVED → BOOKED
    در هر مرحله ممکن است به REJECTED تغییر کند
    """
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    unique_code = Column(String, unique=True, index=True)
    
    # وضعیت: DRAFT, PENDING_L1, PENDING_L2, PENDING_L3, PENDING_L4, APPROVED, REJECTED, BOOKED
    status = Column(String, default="DRAFT", index=True)
    
    # سطح تایید فعلی (1=قسمت، 2=اداره، 3=حوزه، 4=ذی‌حساب)
    current_approval_level = Column(Integer, default=0)
    
    # ایجادکننده
    created_by_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # تایید/رد (آخرین بررسی‌کننده)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)
    
    # Rejection tracking (specific rejector)
    rejected_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    
    # اطلاعات سازمانی
    zone_id = Column(Integer, ForeignKey("org_units.id"))
    department_id = Column(Integer, ForeignKey("org_units.id"), nullable=True)
    section_id = Column(Integer, ForeignKey("org_units.id"), nullable=True)
    
    # سامانه و فعالیت ویژه
    subsystem_id = Column(Integer, ForeignKey("subsystems.id"), nullable=True)
    subsystem_activity_id = Column(Integer, ForeignKey("subsystem_activities.id"), nullable=True)
    
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
    
    # مستندات پیوست (لیست فایل‌ها یا لینک‌های API)
    attachments = Column(JSON, nullable=True)
    
    # جزئیات اضافی (JSON برای فرم‌های پیچیده)
    form_data = Column(JSON, nullable=True)
    
    # سال مالی
    fiscal_year = Column(String, default="1403")
    
    # === Accounting Posting Module ===
    accounting_status = Column(Enum(AccountingStatus), nullable=True, index=True)
    posted_at = Column(DateTime, nullable=True)
    posted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    posting_ref = Column(String(100), nullable=True, index=True)
    posting_notes = Column(String(500), nullable=True)
    
    # Error tracking
    post_error_message = Column(String, nullable=True)
    post_error_at = Column(DateTime, nullable=True)
    post_retry_count = Column(Integer, default=0)
    
    # Export tracking
    export_count = Column(Integer, default=0)
    last_exported_at = Column(DateTime, nullable=True)
    last_exported_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Optimistic locking
    version = Column(Integer, default=1, nullable=False)
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id], backref="created_transactions")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id], backref="reviewed_transactions")
    rejected_by = relationship("User", foreign_keys=[rejected_by_user_id], backref="rejected_transactions")
    posted_by = relationship("User", foreign_keys=[posted_by_id], backref="posted_transactions")
    last_exported_by = relationship("User", foreign_keys=[last_exported_by_id])
    zone = relationship("OrgUnit", foreign_keys=[zone_id])
    department = relationship("OrgUnit", foreign_keys=[department_id])
    section = relationship("OrgUnit", foreign_keys=[section_id])
    budget_item = relationship("BudgetItem", backref="transactions")
    cost_center = relationship("CostCenterRef")
    continuous_action = relationship("ContinuousAction")
    financial_event = relationship("FinancialEventRef")
    subsystem = relationship("Subsystem")
    subsystem_activity = relationship("SubsystemActivity")


# --- تاریخچه گردش کار ---

class WorkflowLog(Base):
    """تاریخچه گردش کار - هر اقدام ادمین ثبت می‌شود
    
    این جدول تمام تاییدها، رد‌ها و برگشت‌ها را ذخیره می‌کند
    """
    __tablename__ = "workflow_logs"
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    admin_level = Column(Integer, nullable=False)  # 1, 2, 3, 4
    action = Column(String, nullable=False)  # APPROVE, REJECT, RETURN
    comment = Column(String, nullable=True)  # دلیل رد یا توضیح
    previous_status = Column(String, nullable=False)
    new_status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    transaction = relationship("Transaction", backref="workflow_logs")
    admin = relationship("User")


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


# ============================================
# Budget Control Module - Zero Trust
# ============================================

class BudgetRow(Base):
    """
    ردیف بودجه - ساختار "غیرقابل نفوذ"
    
    این جدول اطلاعات بودجه مصوب و مصرف شده را نگهداری می‌کند.
    با استفاده از CHECK Constraint در سطح دیتابیس، از خرج کردن بیش از بودجه جلوگیری می‌شود.
    
    Invariant: spent_amount + blocked_amount <= approved_amount (ALWAYS)
    """
    __tablename__ = "budget_rows"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Link to activity (strict referential integrity)
    activity_id = Column(Integer, ForeignKey("subsystem_activities.id"), nullable=False, index=True)
    
    # Zone-Based Budgeting: Link to organizational unit (zone/region)
    # NULL = Global/HQ budget (accessible by all zones)
    org_unit_id = Column(Integer, ForeignKey("org_units.id"), nullable=True, index=True)
    
    # Budget identification
    budget_coding = Column(String, unique=True, index=True)  # e.g., "20501001"
    description = Column(String)
    
    # Financial amounts (stored in smallest unit - Rials)
    approved_amount = Column(BigInteger, nullable=False)     # مبلغ مصوب
    blocked_amount = Column(BigInteger, default=0)           # مبلغ رزرو شده
    spent_amount = Column(BigInteger, default=0)             # مبلغ هزینه شده
    
    # Metadata
    fiscal_year = Column(String, default="1403", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    activity = relationship("SubsystemActivity", backref="budget_rows")
    org_unit = relationship("OrgUnit")  # Zone/Region this budget belongs to
    transactions = relationship("BudgetTransaction", back_populates="budget_row", cascade="all, delete-orphan")
    
    # Database-level constraint: ACID safety net
    __table_args__ = (
        CheckConstraint(
            'spent_amount + blocked_amount <= approved_amount',
            name='budget_balance_check'
        ),
    )
    
    @property
    def remaining_balance(self) -> int:
        """Calculate available budget for new operations."""
        return self.approved_amount - self.spent_amount - self.blocked_amount


class BudgetTransaction(Base):
    """
    تراکنش بودجه - دفتر حسابداری کامل
    
    هر تغییر در وضعیت بودجه در این جدول ثبت می‌شود.
    این جدول غیرقابل تغییر است (append-only audit log).
    """
    __tablename__ = "budget_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Link to budget row
    budget_row_id = Column(Integer, ForeignKey("budget_rows.id"), nullable=False, index=True)
    
    # Transaction details
    amount = Column(BigInteger, nullable=False)
    operation_type = Column(Enum(OperationType), nullable=False, index=True)
    reference_doc = Column(String, nullable=True, index=True)  # e.g., "Request-1024"
    
    # Audit fields
    performed_by = Column(String, nullable=False)            # User ID who performed
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    notes = Column(String, nullable=True)
    
    # Snapshot of state at transaction time (for forensics)
    balance_before = Column(BigInteger, nullable=True)       # remaining before operation
    balance_after = Column(BigInteger, nullable=True)        # remaining after operation
    
    # Relationship
    budget_row = relationship("BudgetRow", back_populates="transactions")


# ============================================
# Transaction History - Audit Log
# ============================================

class TransactionHistory(Base):
    """Audit log for transaction workflow.
    
    Tracks all actions taken on a transaction:
    - Initial submission
    - Approvals at each level
    - Rejections with reasons
    - Resubmissions after rejection
    """
    __tablename__ = "transaction_history"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    action = Column(Enum(HistoryAction), nullable=False, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    comment = Column(String, nullable=True)  # Notes or rejection reason
    
    # Snapshot for audit trail
    previous_status = Column(String, nullable=True)
    new_status = Column(String, nullable=True)
    
    # Relationships
    transaction = relationship("Transaction", backref="history_entries")
    actor = relationship("User")


# ============================================
# Accounting Posting Module
# ============================================

class JournalSnapshot(Base):
    """Immutable journal entry frozen at L4 approval.
    
    Contains the journal lines that represent the accounting entry
    for a transaction. Created when transaction reaches APPROVED status.
    """
    __tablename__ = "journal_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), unique=True, nullable=False)
    unique_code = Column(String(64), unique=True, nullable=True)  # Denormalized for lookups
    
    # Snapshot metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    snapshot_version = Column(Integer, default=1, nullable=False)
    snapshot_hash = Column(String(64), nullable=False)  # SHA-256
    
    # Aggregates (denormalized for performance)
    total_debit = Column(BigInteger, nullable=False)
    total_credit = Column(BigInteger, nullable=False)
    is_balanced = Column(Boolean, nullable=False)
    line_count = Column(Integer, nullable=False)
    
    # Validation state at snapshot
    validation_status = Column(String(20), default="VALID")  # VALID, WARNING, BLOCKED
    validation_errors_json = Column(JSON, nullable=True)
    
    # Relationships
    transaction = relationship("Transaction", backref="journal_snapshot")
    lines = relationship("JournalLine", back_populates="snapshot", cascade="all, delete-orphan")


class JournalLine(Base):
    """Individual debit/credit line within a journal snapshot."""
    __tablename__ = "journal_lines"
    
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("journal_snapshots.id"), nullable=False)
    
    # Line identification
    line_sequence = Column(Integer, nullable=False)  # 1, 2, 3...
    
    # Account reference
    account_code = Column(String(20), nullable=False, index=True)
    account_name = Column(String(200), nullable=False)
    account_type = Column(String(20), nullable=False)  # TEMPORARY, PERMANENT, BANK
    
    # Amounts (exactly one non-zero)
    debit_amount = Column(BigInteger, default=0, nullable=False)
    credit_amount = Column(BigInteger, default=0, nullable=False)
    
    # Optional classification
    cost_center_code = Column(String(20), nullable=True)
    budget_code = Column(String(20), nullable=True, index=True)
    
    # Description
    line_description = Column(String(500), nullable=True)
    
    # Audit trail
    source_budget_item_id = Column(Integer, nullable=True)
    
    # Relationships
    snapshot = relationship("JournalSnapshot", back_populates="lines")
    
    __table_args__ = (
        CheckConstraint(
            '(debit_amount > 0 AND credit_amount = 0) OR (debit_amount = 0 AND credit_amount > 0)',
            name='check_journal_line_single_side'
        ),
    )


class AccountingAuditLog(Base):
    """Immutable audit trail for all accounting operations."""
    __tablename__ = "accounting_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # What
    event_type = Column(Enum(AccountingEventType), nullable=False, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    
    # When
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Who
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    actor_username = Column(String, nullable=False)  # Denormalized for immutability
    actor_ip = Column(String(45), nullable=True)
    
    # Details
    posting_ref = Column(String(100), nullable=True)
    export_id = Column(String(50), nullable=True)
    error_message = Column(String, nullable=True)
    
    # State snapshot
    before_status = Column(String, nullable=True)
    after_status = Column(String, nullable=True)
    
    # Metadata
    request_id = Column(String(36), nullable=True)  # Correlation ID
    
    # Relationships
    transaction = relationship("Transaction")
    actor = relationship("User")

