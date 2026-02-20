/**
 * Credit Request API service (Stage 1 Gateway)
 * All calls go to /credit-requests/* endpoints.
 */

import type {
  CreditRequest,
  CreditRequestListResponse,
  CreditRequestCreateData,
  CreditRequestApproveData,
  CreditRequestRejectData,
  CreditRequestCancelData,
  CreditRequestActionResponse,
  CreditRequestLogEntry,
} from '../types/creditRequest';

// ============================================================
// Helpers
// ============================================================

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'خطای سرور' }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }
  return response.json();
}

// ============================================================
// CRUD
// ============================================================

/** Create a new DRAFT credit request */
export async function createCreditRequest(data: CreditRequestCreateData): Promise<CreditRequest> {
  const response = await fetch('/credit-requests', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<CreditRequest>(response);
}

/** Get credit request detail */
export async function getCreditRequest(id: number): Promise<CreditRequest> {
  const response = await fetch(`/credit-requests/${id}`, { credentials: 'include' });
  return handleResponse<CreditRequest>(response);
}

/** List credit requests with filters */
export async function listCreditRequests(params?: {
  zone_id?: number;
  department_id?: number;
  section_id?: number;
  status?: string;
  fiscal_year?: string;
  budget_code?: string;
  mine_only?: boolean;
  available_only?: boolean;
  page?: number;
  limit?: number;
}): Promise<CreditRequestListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.zone_id) searchParams.append('zone_id', params.zone_id.toString());
  if (params?.department_id) searchParams.append('department_id', params.department_id.toString());
  if (params?.section_id) searchParams.append('section_id', params.section_id.toString());
  if (params?.status) searchParams.append('status', params.status);
  if (params?.fiscal_year) searchParams.append('fiscal_year', params.fiscal_year);
  if (params?.budget_code) searchParams.append('budget_code', params.budget_code);
  if (params?.mine_only) searchParams.append('mine_only', 'true');
  if (params?.available_only) searchParams.append('available_only', 'true');
  if (params?.page) searchParams.append('page', params.page.toString());
  if (params?.limit) searchParams.append('limit', params.limit.toString());

  const url = `/credit-requests${searchParams.toString() ? '?' + searchParams : ''}`;
  const response = await fetch(url, { credentials: 'include' });
  return handleResponse<CreditRequestListResponse>(response);
}

// ============================================================
// State Transitions
// ============================================================

/** Submit a DRAFT credit request */
export async function submitCreditRequest(id: number): Promise<CreditRequestActionResponse> {
  const response = await fetch(`/credit-requests/${id}/submit`, {
    method: 'POST',
    credentials: 'include',
  });
  return handleResponse<CreditRequestActionResponse>(response);
}

/** Approve a SUBMITTED credit request (admin) */
export async function approveCreditRequest(
  id: number,
  data?: CreditRequestApproveData
): Promise<CreditRequestActionResponse> {
  const response = await fetch(`/credit-requests/${id}/approve`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data || {}),
  });
  return handleResponse<CreditRequestActionResponse>(response);
}

/** Reject a SUBMITTED credit request (admin) */
export async function rejectCreditRequest(
  id: number,
  data: CreditRequestRejectData
): Promise<CreditRequestActionResponse> {
  const response = await fetch(`/credit-requests/${id}/reject`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<CreditRequestActionResponse>(response);
}

/** Cancel a DRAFT/SUBMITTED credit request */
export async function cancelCreditRequest(
  id: number,
  data?: CreditRequestCancelData
): Promise<CreditRequestActionResponse> {
  const response = await fetch(`/credit-requests/${id}/cancel`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data || {}),
  });
  return handleResponse<CreditRequestActionResponse>(response);
}

/** Get audit trail for a credit request */
export async function getCreditRequestLogs(id: number): Promise<CreditRequestLogEntry[]> {
  const response = await fetch(`/credit-requests/${id}/logs`, { credentials: 'include' });
  return handleResponse<CreditRequestLogEntry[]>(response);
}
