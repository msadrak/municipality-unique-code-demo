import api from './api';

export interface CivilProjectListItem {
  id: number;
  project_code: string;
  title: string;
  current_phase: number;
  current_step: number;
  contract_category?: string | null;
  yekta_code?: string | null;
  activity_name?: string | null;
  budget_line?: string | null;
  owning_org_unit_name?: string | null;
}

export interface CivilProjectDetail {
  id: number;
  project_code: string;
  title: string;
  contract_category?: string | null;
  yekta_code?: string | null;
  budget_line?: string | null;
  current_step_info: {
    step_name: string;
    step_number: number;
    total_steps: number;
    assigned_role?: string | null;
    required_form_type?: string | null;
    form_schema?: any;
  };
  documents: Array<{
    id: number;
    document_type: string;
    payload: any;
    submitted_by?: string;
    submitted_at?: string;
  }>;
  approval_tasks: Array<{
    id: number;
    role: string;
    status: 'PENDING' | 'APPROVED' | 'REJECTED';
    comments?: string | null;
    approver_name?: string | null;
  }>;
  can_advance: boolean;
}

export async function getCivilProjects(category?: string | null): Promise<CivilProjectListItem[]> {
  const query = category ? `?category=${encodeURIComponent(category)}` : '';
  return api.get<CivilProjectListItem[]>(`/api/civil/projects${query}`);
}

export async function getCivilProject(id: string | number): Promise<CivilProjectDetail> {
  return api.get<CivilProjectDetail>(`/api/civil/projects/${id}`);
}

export interface CivilProjectCreateInput {
  contract_category?: string;
  contract_title: string;
  contractor_name: string;
  total_amount: number;
  start_date: string;
  end_date: string;
}

export async function createCivilProject(payload: CivilProjectCreateInput): Promise<CivilProjectDetail> {
  return api.post<CivilProjectDetail>('/api/civil/projects', payload);
}

export async function createVolumeContractProject(payload: CivilProjectCreateInput): Promise<CivilProjectDetail> {
  return api.post<CivilProjectDetail>('/api/civil/volume-contracts/projects', payload);
}

export async function submitDocument(projectId: string | number, documentType: string, payload: Record<string, any>): Promise<any> {
  return api.post(`/api/civil/projects/${projectId}/documents`, {
    document_type: documentType,
    payload
  });
}

export interface CivilUploadResponse {
  file_name: string;
  file_url: string;
  content_type?: string | null;
  size: number;
}

export async function uploadCivilAttachment(file: File): Promise<CivilUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  return api.postForm<CivilUploadResponse>('/api/civil/upload', formData);
}

export async function approveTask(taskId: string | number, status: 'APPROVED' | 'REJECTED', comments?: string): Promise<any> {
  return api.post(`/api/civil/tasks/${taskId}/approve`, {
    status,
    comments
  });
}

export async function advanceProject(projectId: string | number): Promise<any> {
  return api.post(`/api/civil/projects/${projectId}/advance`);
}
