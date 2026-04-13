import api from './api';

export interface AttendanceRecord {
  id: number;
  row_number: number;
  location?: string | null;
  full_name: string;
  father_name?: string | null;
  national_id?: string | null;
  marital_status?: string | null;
  children_count?: number | null;
  start_date?: string | null;
  average_per_capita?: number | null;
  min_paid_hours?: number | null;
  max_paid_hours?: number | null;
  monthly_performance_days?: number | null;
  monthly_absence_days?: number | null;
  overtime_replacement?: number | null;
  overtime_hours?: number | null;
  total_average_per_capita?: number | null;
  total_overtime_given?: number | null;
  performance_balance?: string | null;
}

export interface AttendanceSheet {
  id: number;
  title: string;
  year?: number | null;
  month?: number | null;
  region?: string | null;
  original_filename: string;
  row_count: number;
  status: string;
  created_at: string;
  records: AttendanceRecord[];
}

export interface AttendanceTransitionPayload {
  action: 'approve' | 'reject';
  rejection_reason?: string;
}

export interface AggregationSheetMeta {
  sheet_id: number;
  title: string;
  year?: number | null;
  month?: number | null;
  region_name?: string | null;
  original_filename: string;
  row_count: number;
  created_at: string;
  creator_approved_at?: string | null;
  company_rep_approved_at?: string | null;
  security_approved_at?: string | null;
  gm_approved_at?: string | null;
}

export interface AttendanceAggregationItem {
  sheet: AggregationSheetMeta;
  workflow_status: string;
  workflow_status_label: string;
  total_personnel: number;
  total_worked_hours: number;
  total_amount: number;
  total_amount_formatted: string;
}

export interface AttendanceAggregationResponse {
  count: number;
  items: AttendanceAggregationItem[];
}

export interface AttendanceReconciliation {
  year: number;
  month: number;
  region_name: string;
  region_total: number;
  contractor_total: number;
  difference: number;
  is_matched: boolean;
}

export async function fetchAttendanceSheets(): Promise<AttendanceSheet[]> {
  return api.get<AttendanceSheet[]>('/api/attendance');
}

export async function fetchAttendanceSheet(id: number): Promise<AttendanceSheet> {
  return api.get<AttendanceSheet>(`/api/attendance/${id}`);
}

export async function uploadAttendanceSheet(payload: {
  file: File;
  title: string;
  year: number;
  month: number;
  region_name: string;
}): Promise<AttendanceSheet> {
  const formData = new FormData();
  formData.append('file', payload.file);
  formData.append('title', payload.title);
  formData.append('year', payload.year.toString());
  formData.append('month', payload.month.toString());
  formData.append('region_name', payload.region_name);
  return api.postForm<AttendanceSheet>('/api/attendance/upload', formData);
}

export async function uploadContractorStatement(payload: {
  file: File;
  year: number;
  month: number;
  region_name: string;
  declared_total_amount: number;
}): Promise<AttendanceSheet> {
  const formData = new FormData();
  formData.append('file', payload.file);
  formData.append('year', payload.year.toString());
  formData.append('month', payload.month.toString());
  formData.append('region_name', payload.region_name);
  formData.append('declared_total_amount', payload.declared_total_amount.toString());
  return api.postForm<AttendanceSheet>('/api/attendance/upload/statement', formData);
}

export async function transitionAttendanceSheet(
  id: number,
  payload: AttendanceTransitionPayload,
): Promise<AttendanceSheet> {
  return api.post<AttendanceSheet>(`/api/attendance/${id}/transition`, payload);
}

export async function fetchAttendanceAggregation(params?: {
  region?: string;
  status?: string;
}): Promise<AttendanceAggregationResponse> {
  return api.get<AttendanceAggregationResponse>('/api/attendance/reports/aggregation', params);
}

export async function fetchAttendanceReconciliation(
  year: number,
  month: number,
  regionName: string,
): Promise<AttendanceReconciliation> {
  return api.get<AttendanceReconciliation>(
    `/api/attendance/reconciliation/${year}/${month}/${encodeURIComponent(regionName)}`,
  );
}
