import api from './api';

export interface AttendanceRecord {
  id: number;
  sheet_id: number;
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
  rejection_reason?: string | null;
  created_at: string;
  records: AttendanceRecord[];
  attachments: AttachmentMeta[];
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

export interface PenaltyRecord {
  id: number;
  work_period_id: number;
  description: string;
  count: number;
  unit_amount: number;
  total_amount: number;
}

export interface WorkPeriodReconciliation {
  year: number;
  month: number;
  status: string;
  region_total: number;
  contractor_total: number;
  total_penalties_amount: number;
  final_payable_amount: number;
  financial_transaction_id?: number | null;
  financial_transaction_status?: string | null;
  financial_tracking_number?: string | null;
  financial_unique_code?: string | null;
  penalties: PenaltyRecord[];
}

export interface WorkPeriodStatus {
  status: string;
  total_uploaded: number;
  uploaded_regions: string[];
  missing_regions: string[];
}

export interface WorkPeriodApprovalResponse {
  success: boolean;
  status: string;
  message: string;
  financial_transaction_id?: number | null;
  financial_transaction_status?: string | null;
  financial_tracking_number?: string | null;
}

export interface CreatePenaltyPayload {
  description: string;
  count: number;
  unit_amount: number;
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

export async function fetchWorkPeriodReconciliation(
  year: number,
  month: number,
): Promise<WorkPeriodReconciliation> {
  return api.get<WorkPeriodReconciliation>(
    `/api/attendance/work-periods/${year}/${month}/reconciliation`,
  );
}

export async function fetchWorkPeriodStatus(
  year: number,
  month: number,
): Promise<WorkPeriodStatus> {
  return api.get<WorkPeriodStatus>(`/api/attendance/work-periods/${year}/${month}/status`);
}

export async function approveWorkPeriodAggregation(
  year: number,
  month: number,
): Promise<WorkPeriodApprovalResponse> {
  return api.post<WorkPeriodApprovalResponse>(
    `/api/attendance/work-periods/${year}/${month}/approve-aggregation`,
    {},
  );
}

export async function createPenaltyRecord(
  year: number,
  month: number,
  payload: CreatePenaltyPayload,
): Promise<PenaltyRecord> {
  return api.post<PenaltyRecord>(
    `/api/attendance/work-periods/${year}/${month}/penalties`,
    payload,
  );
}

export async function finalizeWorkPeriod(
  year: number,
  month: number,
): Promise<WorkPeriodApprovalResponse> {
  return api.post<WorkPeriodApprovalResponse>(
    `/api/attendance/work-periods/${year}/${month}/finalize`,
    {},
  );
}

export async function generateUniqueCode(
  _year?: number,
  _month?: number,
): Promise<WorkPeriodApprovalResponse> {
  throw new Error('Direct unique-code generation is removed. Continue in the finance dashboard.');
}

export interface AttendanceAuditLog {
  id: number;
  record_id: number;
  changed_by_user_id?: number | null;
  changed_by_full_name?: string | null;
  field_name: string;
  old_value: string;
  new_value: string;
  created_at: string;
}

export async function fetchRegionAttendanceRecords(
  year: number,
  month: number,
  regionName: string,
): Promise<AttendanceRecord[]> {
  return api.get<AttendanceRecord[]>(`/api/attendance/work-periods/${year}/${month}/regions/${encodeURIComponent(regionName)}/records`);
}

export async function updateAttendanceRecord(
  recordId: number,
  payload: Partial<AttendanceRecord>,
): Promise<AttendanceRecord> {
  return api.patch<AttendanceRecord>(`/api/attendance/records/${recordId}`, payload);
}

export async function fetchAttendanceAuditLogs(
  recordId: number,
): Promise<AttendanceAuditLog[]> {
  return api.get<AttendanceAuditLog[]>(`/api/attendance/records/${recordId}/audit-logs`);
}

export async function rejectAttendanceSheet(
  sheetId: number,
  payload: { reason: string },
): Promise<AttendanceSheet> {
  return api.post<AttendanceSheet>(`/api/attendance/sheets/${sheetId}/reject`, payload);
}

// ---------------------------------------------------------------------------
// Attachments (PDF / Image invoice documents)
// ---------------------------------------------------------------------------

export interface AttachmentMeta {
  id: number;
  sheet_id: number;
  file_path: string;
  file_name: string;
  file_type: 'pdf' | 'image';
  created_at: string;
}

export async function uploadSheetAttachments(
  sheetId: number,
  files: File[],
): Promise<AttachmentMeta[]> {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file);
  }
  return api.postForm<AttachmentMeta[]>(`/api/attendance/sheets/${sheetId}/attachments`, formData);
}

export async function fetchSheetAttachments(sheetId: number): Promise<AttachmentMeta[]> {
  return api.get<AttachmentMeta[]>(`/api/attendance/sheets/${sheetId}/attachments`);
}
