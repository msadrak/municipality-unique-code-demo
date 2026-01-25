/**
 * TypeScript types for Accounting Posting module
 * Based on frontend_architecture.md v2
 */

// ============ ENUMS ============
export type AccountingStatus = 'READY_TO_POST' | 'POSTED' | 'POST_ERROR';
export type ValidationStatus = 'VALID' | 'WARNING' | 'BLOCKED';
export type AccountType = 'TEMPORARY' | 'PERMANENT' | 'BANK';

// ============ INBOX LIST ============
export interface InboxFilters {
    status?: AccountingStatus | 'ALL';
    zone_id?: number;
    date_from?: string;
    date_to?: string;
    search?: string;
    limit?: number;
    offset?: number;
}

export interface InboxItem {
    id: number;
    unique_code: string;  // Primary identifier (display_id removed)
    approved_at: string | null;
    beneficiary_name: string;
    amount: number;
    zone_title: string;
    accounting_status: AccountingStatus | null;
    validation_status: ValidationStatus;
    warning_count: number;
    version: number;
}

export interface InboxResponse {
    items: InboxItem[];
    total: number;
    limit: number;
    offset: number;
}

// ============ JOURNAL PREVIEW ============
export interface JournalLine {
    sequence: number;
    account_code: string;
    account_name: string;
    account_type: AccountType;
    debit_amount: number;
    credit_amount: number;
    cost_center_code?: string;
    budget_code?: string;
    line_description?: string;
}

export interface JournalPreview {
    transaction_id: number;
    unique_code: string;  // Primary identifier (replaces display_id)
    snapshot_version: number;
    snapshot_at: string;
    snapshot_hash: string;
    lines: JournalLine[];
    total_debit: number;
    total_credit: number;
    is_balanced: boolean;
    validation_status: ValidationStatus;
    validation_errors: string[];
    warnings: string[];
    // Context info
    section_name?: string;   // قسمت
    subsystem_name?: string; // سامانه
}

// ============ POST REQUEST ============
export interface PostRequest {
    posting_ref: string;
    notes?: string;
    version: number;
}

export interface PostResponse {
    success: boolean;
    transaction_id: number;
    display_id: string;
    accounting_status: AccountingStatus;
    posted_at: string;
    posted_by: string;
    posting_ref: string;
    new_version: number;
    message?: string;
}

export interface PostError {
    success: false;
    error: 'CONFLICT' | 'VALIDATION_BLOCKED' | 'NOT_FOUND' | 'VERSION_MISMATCH';
    message: string;
    existing_ref?: string;
    current_version?: number;
    errors?: string[];
}

// ============ BATCH POST ============
export interface BatchPostItem {
    transaction_id: number;
    posting_ref: string;
    version: number;
}

export interface BatchPostRequest {
    items: BatchPostItem[];
    notes?: string;
}

export interface BatchPostResult {
    transaction_id: number;
    display_id: string;
    success: boolean;
    posting_ref?: string;
    new_version?: number;
    error?: 'VERSION_MISMATCH' | 'VALIDATION_BLOCKED' | 'ALREADY_POSTED' | 'UNKNOWN';
    error_message?: string;
}

export interface BatchPostResponse {
    total_requested: number;
    succeeded: number;
    failed: number;
    results: BatchPostResult[];
}

// ============ EXPORT ============
export interface ExportRequest {
    transaction_ids: number[];
    format: 'csv' | 'xlsx';
    include_journal_lines: boolean;
}
