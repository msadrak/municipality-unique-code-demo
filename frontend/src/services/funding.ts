import api from './api';

export interface FundingRequest {
  id: number;
  tracking_number: string;
  letter_number?: string | null;
  letter_date: string;
  receiver_title: string;
  sender_title: string;
  subject: string;
  body_text: string;
  cc_list?: string | null;
  attachment_count: number;
  amount?: number | null;
  request_type?: string | null;
  status: string;
  created_by_id: number;
  created_at: string;
  updated_at: string;
  budget_year?: number | null;
  budget_code?: string | null;
  charge_letter_number?: string | null;
  charge_letter_date?: string | null;
}

export interface FundingWorkflowLog {
  id: number;
  request_id: number;
  user_id: number;
  actor_name?: string | null;
  actor_role?: string | null;
  from_status: string;
  to_status: string;
  action: string;
  comment?: string | null;
  timestamp: string;
}

export interface FundingTransitionPayload {
  action: string;
  comment?: string;
  extra_fields?: Record<string, unknown>;
}

export async function fetchFundingRequest(id: number): Promise<FundingRequest> {
  return api.get<FundingRequest>(`/funding/requests/${id}`);
}

export async function fetchFundingWorkflowHistory(id: number): Promise<FundingWorkflowLog[]> {
  return api.get<FundingWorkflowLog[]>(`/funding/requests/${id}/history`);
}

export async function fetchFundingArchive(): Promise<FundingRequest[]> {
  return api.get<FundingRequest[]>('/funding/archive');
}

export async function transitionFundingRequest(
  id: number,
  payload: FundingTransitionPayload,
): Promise<FundingRequest> {
  return api.post<FundingRequest>(`/funding/requests/${id}/transition`, payload);
}
