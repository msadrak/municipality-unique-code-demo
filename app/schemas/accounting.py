"""
Pydantic schemas for the Accounting Posting module.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ============ ENUMS ============
class AccountingStatusEnum(str, Enum):
    READY_TO_POST = "READY_TO_POST"
    POSTED = "POSTED"
    POST_ERROR = "POST_ERROR"


class ValidationStatusEnum(str, Enum):
    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class AccountTypeEnum(str, Enum):
    TEMPORARY = "TEMPORARY"
    PERMANENT = "PERMANENT"
    BANK = "BANK"


# ============ INBOX ============
class InboxFilters(BaseModel):
    status: Optional[str] = "READY_TO_POST"
    zone_id: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    search: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class InboxItem(BaseModel):
    id: int
    unique_code: str  # Primary identifier (display_id removed per data lineage spec)
    approved_at: Optional[datetime]
    beneficiary_name: str
    amount: float
    zone_title: str
    accounting_status: Optional[AccountingStatusEnum]
    validation_status: ValidationStatusEnum = ValidationStatusEnum.VALID
    warning_count: int = 0
    version: int
    
    class Config:
        from_attributes = True


class InboxResponse(BaseModel):
    items: List[InboxItem]
    total: int
    limit: int
    offset: int


# ============ JOURNAL PREVIEW ============
class JournalLineSchema(BaseModel):
    sequence: int
    account_code: str
    account_name: str
    account_type: AccountTypeEnum
    debit_amount: int
    credit_amount: int
    cost_center_code: Optional[str] = None
    budget_code: Optional[str] = None
    line_description: Optional[str] = None
    
    class Config:
        from_attributes = True


class JournalPreviewResponse(BaseModel):
    transaction_id: int
    unique_code: str  # Primary identifier (replaces display_id)
    snapshot_version: int
    snapshot_at: datetime
    snapshot_hash: str
    lines: List[JournalLineSchema]
    total_debit: int
    total_credit: int
    is_balanced: bool
    validation_status: ValidationStatusEnum
    validation_errors: List[str] = []
    warnings: List[str] = []
    # Context info for preview
    section_name: Optional[str] = None  # قسمت
    subsystem_name: Optional[str] = None  # سامانه


# ============ POST REQUEST ============
class PostRequest(BaseModel):
    posting_ref: str = Field(..., min_length=1, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)
    version: int


class PostResponse(BaseModel):
    success: bool
    transaction_id: int
    unique_code: str  # Primary identifier
    accounting_status: AccountingStatusEnum
    posted_at: datetime
    posted_by: str
    posting_ref: str
    new_version: int
    message: Optional[str] = None


class PostErrorResponse(BaseModel):
    success: bool = False
    error: str  # CONFLICT, VALIDATION_BLOCKED, NOT_FOUND, VERSION_MISMATCH
    message: str
    existing_ref: Optional[str] = None
    current_version: Optional[int] = None
    errors: Optional[List[str]] = None


# ============ BATCH POST ============
class BatchPostItem(BaseModel):
    transaction_id: int
    posting_ref: str
    version: int


class BatchPostRequest(BaseModel):
    items: List[BatchPostItem]
    notes: Optional[str] = None


class BatchPostResult(BaseModel):
    transaction_id: int
    unique_code: str  # Primary identifier
    success: bool
    posting_ref: Optional[str] = None
    new_version: Optional[int] = None
    error: Optional[str] = None
    error_message: Optional[str] = None


class BatchPostResponse(BaseModel):
    total_requested: int
    succeeded: int
    failed: int
    results: List[BatchPostResult]


# ============ EXPORT ============
class ExportRequest(BaseModel):
    transaction_ids: List[int]
    format: str = Field(default="xlsx", pattern="^(csv|xlsx)$")
    include_journal_lines: bool = True
