from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, DateTime, Boolean, Enum, JSON, CheckConstraint, BigInteger, UniqueConstraint, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref, synonym
from app.database import Base
from datetime import datetime
import enum
import jdatetime


# --- Enums ---
class ActivityFrequency(enum.Enum):
    """تناوب اجرای فعالیت"""
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
    """User record for the platform's mixed legacy and workflow-specific RBAC."""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column("password_hash", String)
    password_hash = synonym("hashed_password")
    full_name = Column(String)
    role = Column(String, default="USER")  # e.g. USER, admin, ADMIN_L*, CIVIL_MANAGER, CONTRACTOR
    region_name = Column(String, nullable=True, index=True)
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=True, index=True)
    
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
    failed_attempts = Column(Integer, default=0, nullable=True)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    default_zone = relationship("OrgUnit", foreign_keys=[default_zone_id])
    default_dept = relationship("OrgUnit", foreign_keys=[default_dept_id])
    default_section = relationship("OrgUnit", foreign_keys=[default_section_id])
    contractor_profile = relationship("Contractor", foreign_keys=[contractor_id], back_populates="linked_users")
    
    # RBAC: Subsystem access control (DENY ALL if empty)
    subsystem_access_list = relationship("UserSubsystemAccess", back_populates="user", cascade="all, delete-orphan")

    @property
    def display_name(self) -> str:
        return self.full_name or self.region_name or self.username



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
    
    TWO-TIER IDENTIFICATION SYSTEM:
    ================================
    1. tracking_number: Internal routing identifier.
       - Generated immediately upon Transaction creation.
       - Pattern: "DRAFT-{year}-{sequence}" (e.g., "DRAFT-1403-0001")
       - NEVER changes after creation.
       - Used for internal tracking throughout the workflow.
    
    2. unique_code: Official payment code (کد یکتا).
       - Remains NULL until the APPROVED stage is reached.
       - Generated ONLY upon final approval (L4 → APPROVED transition).
       - Represents an irrevocable financial commitment.
       - Used for final payment processing and external references.
    
    WARNING: Do NOT auto-generate unique_code at creation time.
    The unique_code field must remain NULL until APPROVED.
    """
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    
    # --- Two-Tier Identification System ---
    # tracking_number: assigned at creation, never changes, for internal routing
    tracking_number = Column(String, unique=True, nullable=False, index=True)
    
    # unique_code: NULL until APPROVED, official payment code for external use
    # WARNING: Must remain NULL until the APPROVED stage is reached.
    unique_code = Column(String, unique=True, nullable=True, index=True)
    
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
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=True, index=True)
    
    # Stage 1 Gateway: link to approved CreditRequest (nullable for legacy rows)
    credit_request_id = Column(Integer, ForeignKey("credit_requests.id"), nullable=True, index=True)
    
    # Golden Thread: link to source ProgressStatement
    # One ProgressStatement can generate multiple Transactions (one-to-many)
    progress_statement_id = Column(Integer, ForeignKey("progress_statements.id"), nullable=True, index=True)
    
    # اطلاعات بودجه و مالی
    budget_item_id = Column(Integer, ForeignKey("budget_items.id"))
    cost_center_id = Column(Integer, ForeignKey("cost_center_refs.id"), nullable=True)
    continuous_action_id = Column(Integer, ForeignKey("continuous_actions.id"), nullable=True)
    financial_event_id = Column(Integer, ForeignKey("financial_event_refs.id"), nullable=True)
    
    # مشخصات تراکنش
    # Financial amount stored in smallest currency unit (Rials) as BigInteger
    # to avoid IEEE 754 floating-point precision errors.
    amount = Column(BigInteger)
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
    activity = relationship("Activity", back_populates="transactions")
    credit_request = relationship("CreditRequest", foreign_keys=[credit_request_id], backref="linked_transaction")
    progress_statement = relationship("ProgressStatement", back_populates="transactions")


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


# ============================================
# Stage 1 Gateway - Credit Provision Request
# ============================================

class CreditRequestStatus(enum.Enum):
    """State machine for Credit Provision Request (درخواست تامین اعتبار)"""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class CreditRequest(Base):
    """
    درخواست تامین اعتبار - Stage 1 Gateway Artifact
    
    This is the mandatory authorization gate. A downstream Transaction cannot be
    created unless it references an APPROVED CreditRequest with matching org
    context, budget_code, and sufficient amount.
    
    State machine (minimal):
        DRAFT -> SUBMITTED -> APPROVED (terminal)
        DRAFT -> CANCELLED (terminal)
        SUBMITTED -> REJECTED (terminal)
        SUBMITTED -> CANCELLED (terminal)
    
    Single-use enforcement: used_transaction_id is set when a Transaction
    consumes this CR. Once set, no further Transactions may reference this CR.
    """
    __tablename__ = "credit_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Display identifier: CR-<fiscal_year>-<zone_code>-<sequence>
    credit_request_code = Column(String, unique=True, index=True, nullable=False)
    
    # State machine
    status = Column(
        Enum(CreditRequestStatus),
        default=CreditRequestStatus.DRAFT,
        nullable=False,
        index=True
    )
    
    # Creator
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Approval / Rejection
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)
    
    # Org context (gate matching fields)
    zone_id = Column(Integer, ForeignKey("org_units.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("org_units.id"), nullable=True)
    section_id = Column(Integer, ForeignKey("org_units.id"), nullable=True)
    civil_project_id = Column(Integer, ForeignKey("civil_projects.id"), nullable=True, index=True)
    
    # Budget reference (string match for Stage 1)
    budget_code = Column(String, nullable=False, index=True)
    
    # Amounts
    amount_requested = Column(Float, nullable=False)
    amount_approved = Column(Float, nullable=True)  # Set on approval
    
    # Content
    description = Column(String, nullable=False)
    fiscal_year = Column(String, default="1403", nullable=False, index=True)
    attachments = Column(JSON, nullable=True)
    form_data = Column(JSON, nullable=True)
    
    # Single-use enforcement: once a transaction uses this CR, record it here
    used_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True, unique=True)
    
    # Optimistic locking
    version = Column(Integer, default=1, nullable=False)
    
    # Idempotency key (optional, unique per creator)
    client_request_id = Column(String, nullable=True)
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id], backref="credit_requests_created")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id], backref="credit_requests_reviewed")
    zone = relationship("OrgUnit", foreign_keys=[zone_id])
    department = relationship("OrgUnit", foreign_keys=[department_id])
    section = relationship("OrgUnit", foreign_keys=[section_id])
    civil_project = relationship("CivilProject", foreign_keys=[civil_project_id], back_populates="credit_requests")
    used_transaction = relationship("Transaction", foreign_keys=[used_transaction_id])
    logs = relationship("CreditRequestLog", back_populates="credit_request", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(
            'amount_requested > 0',
            name='cr_amount_requested_positive'
        ),
        CheckConstraint(
            'amount_approved IS NULL OR (amount_approved > 0 AND amount_approved <= amount_requested)',
            name='cr_amount_approved_valid'
        ),
        UniqueConstraint('created_by_id', 'client_request_id', name='cr_idempotency_key'),
    )


class CreditRequestLog(Base):
    """
    Append-only audit log for CreditRequest state transitions.
    Every approve/reject/submit/cancel is recorded here.
    """
    __tablename__ = "credit_request_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    credit_request_id = Column(Integer, ForeignKey("credit_requests.id"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)  # SUBMIT, APPROVE, REJECT, CANCEL
    previous_status = Column(String, nullable=False)
    new_status = Column(String, nullable=False)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    credit_request = relationship("CreditRequest", back_populates="logs")
    actor = relationship("User")


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


# ============================================
# Phase 2: Contract Lifecycle Models
# ============================================

class ContractStatus(enum.Enum):
    """Contract status state machine (Phase 2)"""
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NOTIFIED = "NOTIFIED"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_COMPLETION = "PENDING_COMPLETION"
    COMPLETED = "COMPLETED"
    GUARANTEE_PERIOD = "GUARANTEE_PERIOD"
    CLOSED = "CLOSED"


class ProgressStatementStatus(enum.Enum):
    """Progress Statement 4-stage approval workflow.
    
    Workflow stages:
        DRAFT      → Initial creation by staff
        PENDING_L1 → Section/Technical review
        PENDING_L2 → Department Head approval
        PENDING_L3 → Zone/Manager approval
        PENDING_L4 → Finance/Treasury processing
        APPROVED   → Final approval (triggers unique payment code generation on Transaction)
        REJECTED   → Rejection at any stage (terminal unless resubmitted)
    
    Note: Status transitions are enforced at the application layer
    (see statement_service.VALID_TRANSITIONS), not in the model.
    """
    DRAFT = "DRAFT"
    PENDING_L1 = "PENDING_L1"
    PENDING_L2 = "PENDING_L2"
    PENDING_L3 = "PENDING_L3"
    PENDING_L4 = "PENDING_L4"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ContractorType(str, enum.Enum):
    """Contractor legal identity type."""
    INDIVIDUAL = "INDIVIDUAL"
    CORPORATE = "CORPORATE"


class Contractor(Base):
    """
    پیمانکار - Contractor entity (data-only in Phase 2, no portal)
    
    Contractors are fetched from Setad (mock in Phase 2) or manually entered.
    The portal_enabled field is reserved for Phase 3 contractor portal activation.
    """
    __tablename__ = "contractors"
    contractor_type = Column(String, default=ContractorType.CORPORATE.value, nullable=False)
    
    id = Column(Integer, primary_key=True, index=True)
    national_id = Column(String, unique=True, nullable=False, index=True)  # کد ملی / شناسه ملی
    company_name = Column(String, nullable=False, index=True)  # نام شرکت
    registration_number = Column(String, nullable=True)  # شماره ثبت
    ceo_name = Column(String, nullable=True)  # نام مدیرعامل
    phone = Column(String, nullable=True)  # تلفن
    address = Column(String, nullable=True)  # آدرس

    # Contractor onboarding profile fields (public contractor-auth flow)
    corporate_id = Column(String, nullable=True)  # شناسه ملی شرکت
    economic_code = Column(String, nullable=True)  # شماره اقتصادی
    postal_code = Column(String, nullable=True)  # کد پستی
    province = Column(String, nullable=True)  # استان
    city = Column(String, nullable=True)  # شهر

    # Banking fields
    bank_name = Column(String, nullable=True)  # نام بانک
    account_number = Column(String, nullable=True)  # شماره حساب
    iban = Column(String, nullable=True)  # شماره شبا

    # Setad integration fields
    setad_ref_id = Column(String, nullable=True, index=True)  # شناسه سامانه ستاد
    source_system = Column(String, default="MANUAL")  # MANUAL | SETAD
    
    # Verification
    is_verified = Column(Boolean, default=False)  # تایید شده توسط کارشناس
    portal_enabled = Column(Boolean, default=False)  # Phase 3: فعال‌سازی پرتال پیمانکار
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    contracts = relationship("Contract", back_populates="contractor")
    linked_users = relationship("User", back_populates="contractor_profile")


class ContractTemplate(Base):
    """
    قالب قرارداد - Dynamic Contract Template with JSON Schema
    
    Admins define contract types (e.g., Civil Type A, Green Space Type B)
    using a JSON Schema stored in schema_definition. The frontend renders
    dynamic forms from this schema. New contract types = new DB row, zero code changes.
    
    Versioning: version increments on edit. Existing contracts keep their
    template_id pointing to the version they were created with.
    """
    __tablename__ = "contract_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)  # e.g., CIVIL_TYPE_A
    title = Column(String, nullable=False)  # عنوان فارسی
    category = Column(String, nullable=True, index=True)  # CIVIL, GREEN_SPACE, SERVICES, ...
    
    # JSON Schema definition for dynamic form fields
    schema_definition = Column(JSON, nullable=False)  # JSON Schema (type, properties, required)
    default_values = Column(JSON, nullable=True)  # Default field values
    required_fields = Column(JSON, nullable=True)  # Override required fields list
    
    # Approval workflow configuration
    approval_workflow_config = Column(JSON, nullable=True)  # {required_levels, requires_legal_review, ...}
    
    # Status & Versioning
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    contracts = relationship("Contract", back_populates="template")


class Contract(Base):
    """
    قرارداد - Contract entity (shell for Sprint 1, lifecycle in Sprint 2)
    
    The Golden Thread: Activity → BudgetRow → CreditRequest → Contract → ProgressStatement → Transaction
    Every entity links back to its parent, creating an auditable chain from Activity to Payment.
    """
    __tablename__ = "contracts"
    
    id = Column(Integer, primary_key=True, index=True)
    contract_number = Column(String, unique=True, nullable=False, index=True)  # شماره قرارداد
    title = Column(String, nullable=False)  # عنوان قرارداد
    
    # Golden Thread: Foreign Keys
    credit_request_id = Column(Integer, ForeignKey("credit_requests.id"), nullable=True, index=True)
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=False, index=True)
    activity_id = Column(Integer, ForeignKey("subsystem_activities.id"), nullable=True, index=True)
    budget_row_id = Column(Integer, ForeignKey("budget_rows.id"), nullable=True, index=True)
    template_id = Column(Integer, ForeignKey("contract_templates.id"), nullable=True, index=True)
    org_unit_id = Column(Integer, ForeignKey("org_units.id"), nullable=True, index=True)
    civil_project_id = Column(Integer, ForeignKey("civil_projects.id"), nullable=True, index=True)
    
    # Status machine
    status = Column(
        Enum(ContractStatus),
        default=ContractStatus.DRAFT,
        nullable=False,
        index=True
    )
    
    # Financial
    total_amount = Column(BigInteger, nullable=False)  # مبلغ کل قرارداد (ریال)
    paid_amount = Column(BigInteger, default=0)  # مبلغ پرداخت شده
    
    # Dates
    start_date = Column(Date, nullable=True)  # تاریخ شروع
    end_date = Column(Date, nullable=True)  # تاریخ پایان
    
    # Dynamic template data (filled from ContractTemplate.schema_definition)
    template_data = Column(JSON, nullable=True)  # Data filled against template schema
    metadata_extra = Column(JSON, nullable=True)  # Additional metadata
    
    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Optimistic locking
    version = Column(Integer, default=1, nullable=False)
    
    # Relationships
    credit_request = relationship("CreditRequest", foreign_keys=[credit_request_id])
    contractor = relationship("Contractor", back_populates="contracts")
    activity = relationship("SubsystemActivity")
    budget_row = relationship("BudgetRow")
    template = relationship("ContractTemplate", back_populates="contracts")
    org_unit = relationship("OrgUnit", foreign_keys=[org_unit_id])
    civil_project = relationship("CivilProject", foreign_keys=[civil_project_id], back_populates="contracts")
    created_by = relationship("User", foreign_keys=[created_by_id])
    progress_statements = relationship("ProgressStatement", back_populates="contract", cascade="all, delete-orphan")
    guarantees = relationship("ContractGuarantee", back_populates="contract", cascade="all, delete-orphan")


class ProgressStatement(Base):
    """
    صورت وضعیت - Progress Statement (Generalized, Department-Agnostic)
    
    ARCHITECTURAL DESIGN — GENERALIZATION STRATEGY:
    ================================================
    This model serves ALL municipal organs (Civil Engineering, Urban Services,
    Traffic & Transport, Urban Planning, Subsidiary Organizations, etc.) through
    a single table without schema changes.
    
    How it works:
      1. UNIVERSAL FINANCIAL FIELDS: gross_amount, deductions, net_amount,
         cumulative_amount — these are present in every physical document
         regardless of department.
      2. UNIVERSAL REFERENCE FIELDS: contract_ref_number, credit_ref_number,
         statement_number — present in all document types.
      3. STRUCTURED DEDUCTION BREAKDOWN: insurance_deduction, tax_deduction,
         advance_payment_amount, other_deductions — covers all deduction
         categories across departments.
      4. JSONB template_data: Department-specific variables (e.g., asphalt
         volume for civil, IFAS capacity for water treatment, tree count for
         green space) are stored as a JSON object. A ContractTemplate defines
         the schema, and the frontend renders dynamic forms.
      5. JSONB line_items: Work breakdown items specific to the statement.
    
    Adding a new department type = new ContractTemplate row, ZERO schema changes.
    
    Workflow (4-stage approval):
      DRAFT → PENDING_L1 → PENDING_L2 → PENDING_L3 → PENDING_L4 → APPROVED
      At any stage → REJECTED
    
    Upon APPROVED, a linked Transaction is created/advanced, which receives
    the unique payment code (کد یکتا) only at the Transaction's own final approval.
    """
    __tablename__ = "progress_statements"
    
    id = Column(Integer, primary_key=True, index=True)
    statement_number = Column(String, unique=True, nullable=False, index=True)  # شماره صورت وضعیت
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    sequence_number = Column(Integer, nullable=False)  # شماره ترتیب (1, 2, 3, ...)
    
    # Type: INTERIM (موقت), FINAL (قطعی), ADJUSTMENT (تعدیل), FINAL_ADJUSTMENT (تعدیل قطعی)
    statement_type = Column(String, default="INTERIM")
    
    # --- Originating Organ (department-agnostic identifier) ---
    # e.g., "معاونت عمران شهری", "معاونت خدمات شهری", "معاونت شهرسازی و معماری",
    #       "سازمان نوسازی و بهسازی"
    originating_organ = Column(String, nullable=True, index=True)
    
    # --- Content ---
    description = Column(String, nullable=True)  # شرح صورت وضعیت
    period_start = Column(Date, nullable=True)   # تاریخ شروع دوره
    period_end = Column(Date, nullable=True)     # تاریخ پایان دوره
    
    # --- Contract & Credit References (extracted from physical documents) ---
    contract_ref_number = Column(String, nullable=True, index=True)  # شماره قرارداد (original)
    contract_ref_date = Column(String, nullable=True)    # تاریخ قرارداد (Persian calendar string)
    credit_ref_number = Column(String, nullable=True)    # شماره تامین اعتبار
    credit_ref_amount = Column(BigInteger, nullable=True) # مبلغ تامین اعتبار (Rials)
    
    # --- Core Financial Fields (universal across ALL departments) ---
    # All amounts stored in smallest currency unit (Rials) as BigInteger
    # to avoid IEEE 754 floating-point precision errors.
    gross_amount = Column(BigInteger, nullable=False)             # مبلغ ناخالص
    net_amount = Column(BigInteger, nullable=False)               # مبلغ خالص قابل پرداخت
    cumulative_amount = Column(BigInteger, default=0)             # مبلغ تجمیعی تا این مرحله
    previous_statement_amount = Column(BigInteger, default=0)     # مبلغ صورت وضعیت قبلی
    
    # --- Deduction Breakdown (covers all department deduction types) ---
    deductions = Column(BigInteger, default=0)                    # کسورات کل (sum of below)
    insurance_deduction = Column(BigInteger, default=0)           # بیمه
    tax_deduction = Column(BigInteger, default=0)                 # مالیات
    advance_payment_amount = Column(BigInteger, default=0)        # پیش‌پرداخت / علی‌الحساب
    other_deductions = Column(BigInteger, default=0)              # سایر کسورات
    
    # --- Price Adjustment (تعدیل) ---
    price_index_base = Column(String, nullable=True)  # شاخص مبنای تعدیل (e.g., "اسفند ماه سال ۱۴۰۳")
    
    # --- 4-Stage Approval Workflow ---
    status = Column(
        Enum(ProgressStatementStatus),
        default=ProgressStatementStatus.DRAFT,
        nullable=False,
        index=True
    )
    current_approval_level = Column(Integer, default=0)  # 0=draft, 1=L1, 2=L2, 3=L3, 4=L4
    
    # --- Department-Specific Data (JSONB for generalization) ---
    # Department-specific variables stored as JSON. Schema defined by ContractTemplate.
    # Examples:
    #   Civil: {"work_volume": "5200 m³", "mobilization_cost": 1175200000}
    #   Consulting: {"service_percentage": 50, "design_scope": "بازآفرینی"}
    #   Water Treatment: {"ifas_capacity": "5200 m³/day", "flow_rate": "60 L/s"}
    template_data = Column(JSON, nullable=True)
    
    # Work breakdown items: [{description, quantity, unit_price, total}, ...]
    line_items = Column(JSON, nullable=True)
    
    # Uploaded supporting documents: [{filename, url, type}, ...]
    attachments = Column(JSON, nullable=True)
    
    # --- Workflow Tracking ---
    submitted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejected_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_comment = Column(String, nullable=True)
    rejection_reason = Column(String, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    
    # --- Metadata ---
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Optimistic locking
    version = Column(Integer, default=1, nullable=False)
    
    # --- Relationships ---
    contract = relationship("Contract", back_populates="progress_statements")
    submitted_by = relationship("User", foreign_keys=[submitted_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    rejected_by = relationship("User", foreign_keys=[rejected_by_id])
    transactions = relationship("Transaction", back_populates="progress_statement")


class ContractGuarantee(Base):
    """
    ضمانت‌نامه قرارداد - Contract Guarantee (bank guarantees, performance bonds)
    """
    __tablename__ = "contract_guarantees"
    
    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    
    # Guarantee details
    guarantee_type = Column(String, nullable=False)  # PERFORMANCE (حسن انجام کار), ADVANCE (پیش‌پرداخت), TENDER (شرکت در مناقصه)
    amount = Column(BigInteger, nullable=False)  # مبلغ ضمانت‌نامه (ریال)
    bank_name = Column(String, nullable=True)  # نام بانک
    guarantee_number = Column(String, nullable=True, index=True)  # شماره ضمانت‌نامه
    
    # Dates
    issue_date = Column(Date, nullable=True)  # تاریخ صدور
    expiry_date = Column(Date, nullable=True)  # تاریخ انقضا
    
    # Status: ACTIVE, RELEASED, EXPIRED, CLAIMED
    status = Column(String, default="ACTIVE", index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    contract = relationship("Contract", back_populates="guarantees")

# ============================================
# HR Funding Module (Standalone Process)
# ============================================


def _current_persian_date() -> str:
    return jdatetime.date.today().strftime("%Y/%m/%d")

class FundingStatus(str, enum.Enum):
    """HR funding workflow states.

    Legacy states are kept for backward compatibility with pre-workflow data.
    New requests start at PENDING_VP_PLANNING.
    """

    PENDING_VP_PLANNING = "PENDING_VP_PLANNING"
    PENDING_VP_FINANCE_REVIEW = "PENDING_VP_FINANCE_REVIEW"
    BUDGET_WELFARE_DEPT = "BUDGET_WELFARE_DEPT"
    BUDGET_GM_HC = "BUDGET_GM_HC"
    BUDGET_FINANCE_UNIT = "BUDGET_FINANCE_UNIT"
    BUDGET_VP_FINANCE = "BUDGET_VP_FINANCE"
    CHARGE_LETTER_REGISTERED = "CHARGE_LETTER_REGISTERED"
    PENDING_FINAL_CHARGE = "PENDING_FINAL_CHARGE"
    FINAL_APPROVED = "FINAL_APPROVED"
    CHARGING_IN_PROGRESS = "CHARGING_IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"

    # Legacy statuses from the earlier isolated funding flow.
    DRAFT = "DRAFT"
    PENDING_VP_FINANCE_INITIAL = "PENDING_VP_FINANCE_INITIAL"
    PENDING_BUDGET_ALLOCATION = "PENDING_BUDGET_ALLOCATION"
    PENDING_VP_FINANCE_FINAL = "PENDING_VP_FINANCE_FINAL"
    APPROVED_FOR_CHARGE = "APPROVED_FOR_CHARGE"


class UserRole(str, enum.Enum):
    CIVIL_MANAGER = "CIVIL_MANAGER"
    TENDERING_OFFICER = "TENDERING_OFFICER"
    CONTRACTS_OFFICER = "CONTRACTS_OFFICER"
    SUPERVISOR = "SUPERVISOR"
    DELIVERY_COMMISSION = "DELIVERY_COMMISSION"
    CONTRACTOR = "CONTRACTOR"
    FINANCE_MANAGER = "FINANCE_MANAGER"
    FINANCE_OFFICER = "FINANCE_OFFICER"
    YEKTA_ADMIN = "YEKTA_ADMIN"
    OPERATIONAL_MANAGER = "OPERATIONAL_MANAGER"
    TREASURY = "TREASURY"
    GM_HC = "GM_HC"
    VP_PLANNING = "VP_PLANNING"
    VP_FINANCE = "VP_FINANCE"
    WELFARE_DEPT = "WELFARE_DEPT"
    FINANCE_UNIT = "FINANCE_UNIT"
    GM_FINANCE = "GM_FINANCE"
    ISFAHAN_CARD = "ISFAHAN_CARD"
    ADMIN = "ADMIN"


# Backward-compatible alias used by older imports.
FundingRequestStatus = FundingStatus

class FundingRequest(Base):
    """
    مدل اصلی برای ماژول منابع انسانی
    کاملاً ایزوله از ProgressStatement و Contracts
    """
    __tablename__ = "hr_funding_requests"

    id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String, unique=True, index=True, nullable=False) # e.g., HR-1403-001

    # Official letter fields
    letter_number = Column(String(64), nullable=True)
    letter_date = Column(String(16), default=_current_persian_date, nullable=False)
    receiver_title = Column(String(256), nullable=False)
    sender_title = Column(String(256), nullable=False)
    subject = Column(String(512), nullable=False)
    body_text = Column(Text, nullable=False)
    cc_list = Column(Text, nullable=True)
    attachment_count = Column(Integer, default=0, nullable=False)

    # Legacy aliases kept for compatibility with older UI/reporting paths.
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Request metadata
    amount = Column(BigInteger, nullable=True) # Rials
    request_type = Column(String(64), nullable=True)
    status = Column(
        Enum(FundingStatus),
        default=FundingStatus.PENDING_VP_PLANNING,
        nullable=False, 
        index=True
    )

    # Budget tracking
    budget_code = Column(String(64), nullable=True, index=True)
    budget_year = Column(Integer, nullable=True)

    # Charge letter tracking
    charge_letter_number = Column(String(64), nullable=True)
    charge_letter_date = Column(DateTime, nullable=True)
    
    # ارتباط با کاربر ثبت‌کننده
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id], backref="funding_requests")
    logs = relationship(
        "FundingWorkflowLog",
        back_populates="request",
        order_by="FundingWorkflowLog.timestamp",
        cascade="all, delete-orphan",
    )


class FundingWorkflowLog(Base):
    __tablename__ = "hr_funding_workflow_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("hr_funding_requests.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    from_status = Column(Enum(FundingStatus), nullable=False)
    to_status = Column(Enum(FundingStatus), nullable=False)
    action = Column(String(64), nullable=False)
    comment = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    request = relationship("FundingRequest", back_populates="logs")
    user = relationship("User")

    @property
    def actor_name(self):
        return self.user.full_name if self.user else None

    @property
    def actor_role(self):
        return self.user.role if self.user else None

