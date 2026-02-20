import api from './api';

export interface ContractorListItem {
  id: number;
  national_id: string;
  company_name: string;
  ceo_name?: string | null;
  source_system: string;
  is_verified: boolean;
  created_at?: string | null;
}

export interface ContractorListResponse {
  items: ContractorListItem[];
  total: number;
  page: number;
  limit: number;
}

export interface ContractTemplateSchemaProperty {
  type?: string;
  title?: string;
  description?: string;
  enum?: string[];
  format?: string;
  default?: unknown;
  minimum?: number;
  maximum?: number;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
}

export interface ContractTemplateSchema {
  type?: string;
  properties?: Record<string, ContractTemplateSchemaProperty>;
  required?: string[];
}

export interface ContractTemplateListItem {
  id: number;
  code: string;
  title: string;
  category?: string | null;
  is_active: boolean;
  version: number;
  created_at?: string | null;
}

export interface ContractTemplateListResponse {
  items: ContractTemplateListItem[];
  total: number;
  page: number;
  limit: number;
}

export interface ContractTemplateResponse extends ContractTemplateListItem {
  schema_definition: ContractTemplateSchema;
  default_values?: Record<string, unknown> | null;
  required_fields?: string[] | null;
  approval_workflow_config?: Record<string, unknown> | null;
  updated_at?: string | null;
}

export interface ContractDraftRequest {
  budget_row_id: number;
  contractor_id: number;
  template_id: number;
  title: string;
  total_amount: number;
  template_data?: Record<string, unknown>;
  start_date?: string;
  end_date?: string;
}

export interface ContractResponse {
  id: number;
  contract_number: string;
  title: string;
  status: string;
  contractor_id: number;
  contractor_name?: string | null;
  template_id?: number | null;
  template_title?: string | null;
  budget_row_id?: number | null;
  credit_request_id?: number | null;
  org_unit_id?: number | null;
  total_amount: number;
  paid_amount?: number | null;
  start_date?: string | null;
  end_date?: string | null;
  template_data?: Record<string, unknown> | null;
  metadata_extra?: Record<string, unknown> | null;
  created_at?: string | null;
  updated_at?: string | null;
  version?: number | null;
}

export interface ContractListItem {
  id: number;
  contract_number: string;
  title: string;
  status: string;
  contractor_name?: string | null;
  total_amount: number;
  paid_amount?: number | null;
  created_at?: string | null;
}

export interface ContractListResponse {
  items: ContractListItem[];
  total: number;
  page: number;
  limit: number;
}

export async function fetchContractors(params?: {
  search?: string;
  verified_only?: boolean;
  page?: number;
  limit?: number;
}): Promise<ContractorListResponse> {
  return api.get<ContractorListResponse>('/contractors', params);
}

export async function fetchContractTemplates(params?: {
  category?: string;
  active_only?: boolean;
  page?: number;
  limit?: number;
}): Promise<ContractTemplateListResponse> {
  return api.get<ContractTemplateListResponse>('/contract-templates', params);
}

export async function fetchContractTemplate(templateId: number): Promise<ContractTemplateResponse> {
  return api.get<ContractTemplateResponse>(`/contract-templates/${templateId}`);
}

export async function fetchContracts(params?: {
  status?: string;
  page?: number;
  limit?: number;
}): Promise<ContractListResponse> {
  return api.get<ContractListResponse>('/contracts', params);
}

export async function createContractDraft(payload: ContractDraftRequest): Promise<ContractResponse> {
  return api.post<ContractResponse>('/contracts/draft', payload);
}

export async function fetchContract(contractId: number): Promise<ContractResponse> {
  return api.get<ContractResponse>(`/contracts/${contractId}`);
}

export async function submitContract(contractId: number): Promise<ContractResponse> {
  return api.put<ContractResponse>(`/contracts/${contractId}/submit`);
}

export async function transitionContractStatus(
  id: number,
  action: 'approve' | 'reject',
): Promise<ContractResponse> {
  const new_status = action === 'approve' ? 'APPROVED' : 'REJECTED';
  return api.put<ContractResponse>(`/contracts/${id}/transition`, { new_status });
}

// ============================================================
// Progress Statement Types & API (Sprint 3)
// ============================================================

export interface StatementListItem {
  id: number;
  statement_number: string;
  sequence_number: number;
  status: string;
  net_amount: number;
  cumulative_amount: number;
  created_at?: string | null;
}

export interface StatementListResponse {
  items: StatementListItem[];
  total: number;
  contract_id: number;
}

export interface StatementResponse {
  id: number;
  statement_number: string;
  contract_id: number;
  sequence_number: number;
  statement_type: string;
  status: string;
  description?: string | null;
  period_start?: string | null;
  period_end?: string | null;
  gross_amount: number;
  deductions: number;
  net_amount: number;
  cumulative_amount: number;
  submitted_by_id?: number | null;
  reviewed_by_id?: number | null;
  review_comment?: string | null;
  submitted_at?: string | null;
  reviewed_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  version: number;
}

export interface StatementCreateRequest {
  amount?: number;
  gross_amount?: number;
  deductions?: number;
  description: string;
  period_start?: string;
  period_end?: string;
  statement_type?: string;
}

export async function fetchStatements(contractId: number): Promise<StatementListResponse> {
  return api.get<StatementListResponse>(`/contracts/${contractId}/statements`);
}

export async function createStatement(
  contractId: number,
  payload: StatementCreateRequest,
): Promise<StatementResponse> {
  return api.post<StatementResponse>(`/contracts/${contractId}/statements`, payload);
}

export async function submitStatement(statementId: number): Promise<StatementResponse> {
  return api.put<StatementResponse>(`/statements/${statementId}/submit`);
}

export async function approveStatement(
  statementId: number,
  reviewComment?: string,
): Promise<StatementResponse> {
  return api.put<StatementResponse>(`/statements/${statementId}/approve`, {
    review_comment: reviewComment ?? null,
  });
}

export async function payStatement(statementId: number): Promise<StatementResponse> {
  return api.put<StatementResponse>(`/statements/${statementId}/pay`);
}
