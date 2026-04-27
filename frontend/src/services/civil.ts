import api from './api';

export interface CivilProjectListItem {
  id: number;
  project_code: string;
  title: string;
  current_phase: number;
  current_step: number;
  activity_name?: string | null;
  budget_line?: string | null;
  owning_org_unit_name?: string | null;
}

export interface CivilProjectDetail {
  id: number;
  project_code: string;
  title: string;
  budget_line?: string | null;
  current_step_info: {
    step_name: string;
    step_number: number;
    total_steps: number;
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

export async function getCivilProjects(): Promise<CivilProjectListItem[]> {
  return api.get<CivilProjectListItem[]>('/api/civil/projects');
}

export async function getCivilProject(id: string | number): Promise<CivilProjectDetail> {
  return api.get<CivilProjectDetail>(`/api/civil/projects/${id}`);
}

export async function submitDocument(projectId: string | number, documentType: string, payload: Record<string, any>): Promise<any> {
  return api.post(`/api/civil/projects/${projectId}/documents`, {
    document_type: documentType,
    payload
  });
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
