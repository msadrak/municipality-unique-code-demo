/**
 * Stage 1 Gateway: Credit Request types (درخواست تامین اعتبار)
 */

export type CreditRequestStatus = 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED' | 'CANCELLED';

export interface CreditRequest {
  id: number;
  credit_request_code: string;
  status: CreditRequestStatus;
  zone_id: number;
  zone_title?: string;
  department_id?: number;
  department_title?: string;
  section_id?: number;
  section_title?: string;
  budget_code: string;
  amount_requested: number;
  amount_approved?: number;
  description: string;
  fiscal_year: string;
  attachments?: unknown;
  form_data?: Record<string, unknown>;
  created_by_id: number;
  created_by_name?: string;
  reviewed_by_id?: number;
  reviewed_by_name?: string;
  reviewed_at?: string;
  rejection_reason?: string;
  used_transaction_id?: number;
  version: number;
  created_at?: string;
  updated_at?: string;
}

export interface CreditRequestListItem {
  id: number;
  credit_request_code: string;
  status: CreditRequestStatus;
  zone_title?: string;
  budget_code: string;
  amount_requested: number;
  amount_approved?: number;
  description: string;
  created_by_name?: string;
  used_transaction_id?: number;
  created_at?: string;
}

export interface CreditRequestListResponse {
  items: CreditRequestListItem[];
  total: number;
  page: number;
  limit: number;
}

export interface CreditRequestCreateData {
  zone_id: number;
  department_id?: number;
  section_id?: number;
  budget_code: string;
  amount_requested: number;
  description: string;
  fiscal_year?: string;
  attachments?: unknown;
  form_data?: Record<string, unknown>;
  client_request_id?: string;
}

export interface CreditRequestApproveData {
  amount_approved?: number;
  comment?: string;
}

export interface CreditRequestRejectData {
  reason: string;
}

export interface CreditRequestCancelData {
  reason?: string;
}

export interface CreditRequestActionResponse {
  status: string;
  message: string;
  new_status: CreditRequestStatus;
  credit_request_code: string;
}

export interface CreditRequestLogEntry {
  id: number;
  action: string;
  previous_status: string;
  new_status: string;
  actor_name?: string;
  comment?: string;
  created_at?: string;
}

/** Status display config */
export const CR_STATUS_CONFIG: Record<CreditRequestStatus, { label: string; color: string; bgClass: string }> = {
  DRAFT: { label: 'پیش‌نویس', color: '#6b7280', bgClass: 'bg-gray-100 text-gray-700' },
  SUBMITTED: { label: 'ارسال شده', color: '#d97706', bgClass: 'bg-amber-100 text-amber-700' },
  APPROVED: { label: 'تایید شده', color: '#16a34a', bgClass: 'bg-green-100 text-green-700' },
  REJECTED: { label: 'رد شده', color: '#dc2626', bgClass: 'bg-red-100 text-red-700' },
  CANCELLED: { label: 'لغو شده', color: '#9ca3af', bgClass: 'bg-gray-100 text-gray-500' },
};
