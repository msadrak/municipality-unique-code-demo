import api from "./api";

export interface VolumeContractListItem {
  id: number;
  project_code: string;
  title: string;
  current_phase: number;
  current_step: number;
  contract_category?: string | null;
  yekta_code?: string | null;
  current_step_code?: string | null;
  current_step_name?: string | null;
  activity_name?: string | null;
  budget_line?: string | null;
  owning_org_unit_name?: string | null;
  created_at?: string | null;
  paid_amount?: number | null;
}

export interface VolumeContractDocument {
  id: number;
  document_type: string;
  payload: Record<string, any>;
  submitted_by?: string | null;
  submitted_at?: string | null;
}

export interface VolumeContractApprovalTask {
  id: number;
  role: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  comments?: string | null;
  approver_name?: string | null;
}

export interface VolumeContractFinancialSummary {
  total_budget?: number | null;
  committed_amount?: number | null;
  total_paid_net?: number | null;
}

export interface VolumeContractTransaction {
  id: number;
  document_number: string;
  unique_code?: string | null;
  date?: string | null;
  amount?: number | null;
  description?: string | null;
  status?: string | null;
  financial_event?: string | null;
  financial_event_label?: string | null;
  financial_matrix_id?: number | null;
}

export interface VolumeContractFinancialMatrixRow {
  id: number;
  transaction_id?: number | null;
  event_sequence?: number | null;
  event_code: string;
  event_label?: string | null;
  event_group?: string | null;
  event_direction?: string | null;
  amount?: number | null;
  yekta_code?: string | null;
  payment_queue_status?: string | null;
  period_key?: string | null;
}

export interface VolumeContractStepInfo {
  step_name: string;
  step_number: number;
  total_steps: number;
  assigned_role?: string | null;
  required_form_type?: string | null;
  form_schema?: Record<string, any> | null;
}

export interface VolumeContractDetail {
  id: number;
  project_code: string;
  title: string;
  contract_category?: string | null;
  yekta_code?: string | null;
  budget_line?: string | null;
  current_step_info: VolumeContractStepInfo;
  documents: VolumeContractDocument[];
  approval_tasks: VolumeContractApprovalTask[];
  can_advance: boolean;
  financial_summary?: VolumeContractFinancialSummary | null;
  transactions: VolumeContractTransaction[];
  financial_matrix: VolumeContractFinancialMatrixRow[];
}

export interface VolumeContractCreateInput {
  contract_category: string;
  contract_title: string;
  contractor_name: string;
  contractor_id?: number;
  total_amount: number;
  start_date: string;
  end_date: string;
}

export interface ContractorUser {
  id: number;
  username: string;
  full_name?: string | null;
}

export interface ContractorDashboardStats {
  total_contracts: number;
  active_contracts: number;
  completed_contracts: number;
  pending_invitations: number;
}

export interface ContractorDashboardData {
  contractor_name: string;
  contractor_type: string;
  is_verified: boolean;
  stats: ContractorDashboardStats;
  invitations: VolumeContractListItem[];
  active_contracts: VolumeContractListItem[];
  completed_contracts: VolumeContractListItem[];
}

export interface VolumeContractUploadResponse {
  file_name: string;
  file_url: string;
  content_type?: string | null;
  size: number;
}

export async function getVolumeContracts(
  category?: string | null,
): Promise<VolumeContractListItem[]> {
  const query = category ? `?category=${encodeURIComponent(category)}` : "";
  return api.get<VolumeContractListItem[]>(
    `/api/volume-contracts/projects${query}`,
  );
}

export async function getVolumeContract(
  id: string | number,
): Promise<VolumeContractDetail> {
  return api.get<VolumeContractDetail>(`/api/volume-contracts/projects/${id}`);
}

export async function createVolumeContract(
  payload: VolumeContractCreateInput,
): Promise<VolumeContractDetail> {
  return api.post<VolumeContractDetail>(
    "/api/volume-contracts/projects",
    payload,
  );
}

export async function fetchContractorUsers(): Promise<ContractorUser[]> {
  return api.get<ContractorUser[]>("/api/volume-contracts/contractor-users");
}

export async function getContractorDashboard(): Promise<ContractorDashboardData> {
  return api.get<ContractorDashboardData>("/api/volume-contracts/contractor-dashboard");
}

export async function submitVolumeContractDocument(
  projectId: string | number,
  documentType: string,
  payload: Record<string, any>,
): Promise<any> {
  return api.post(`/api/volume-contracts/projects/${projectId}/documents`, {
    document_type: documentType,
    payload,
  });
}

export async function uploadVolumeContractAttachment(
  file: File,
): Promise<VolumeContractUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return api.postForm<VolumeContractUploadResponse>(
    "/api/volume-contracts/attachments",
    formData,
  );
}

export async function approveVolumeContractTask(
  taskId: string | number,
  status: "APPROVED" | "REJECTED",
  comments?: string,
): Promise<any> {
  return api.post(`/api/volume-contracts/tasks/${taskId}/approve`, {
    status,
    comments,
  });
}

export async function advanceVolumeContract(
  projectId: string | number,
): Promise<any> {
  return api.post(`/api/volume-contracts/projects/${projectId}/advance`);
}

export interface VolumeContractCalculation {
  project_id: number;
  project_code: string;
  statement_document_id: number;
  statement_number?: string | null;
  work_period?: string | null;
  gross_amount: number;
  financial_events: Array<{
    id?: number;
    transaction_id?: number | null;
    event_sequence: number;
    event_code: string;
    event_label: string;
    event_group?: string | null;
    event_direction?: string | null;
    amount: number;
    yekta_code?: string | null;
    payment_queue_status?: string | null;
    period_key?: string | null;
  }>;
}

export async function calculateVolumeContractStatement(
  projectId: string | number,
): Promise<VolumeContractCalculation> {
  return api.get<VolumeContractCalculation>(
    `/api/volume-contracts/projects/${projectId}/calculate-statement`,
  );
}

export async function submitVolumeContractCalculation(
  projectId: string | number,
): Promise<any> {
  return api.post(
    `/api/volume-contracts/projects/${projectId}/submit-calculation`,
  );
}

// ---------------------------------------------------------------------------
// Lookup APIs used by the Step 103 Bahadori Yekta Sub-Process form
// ---------------------------------------------------------------------------

export interface PortalOrgUnit {
  id: number;
  code?: string | null;
  title?: string | null;
  parent_id?: number | null;
}

export interface PortalBudgetItem {
  id: number;
  budget_code: string;
  title?: string | null;
  description?: string | null;
  allocated_1403?: number | null;
  remaining_budget?: number | null;
}

export interface PortalCostCenter {
  id: number;
  code: string;
  title?: string | null;
}

export interface PortalContinuousAction {
  id: number;
  code: string;
  title?: string | null;
}

export interface PortalFinancialEvent {
  id: number;
  code: string;
  title?: string | null;
}

export async function fetchOrgRoots(): Promise<PortalOrgUnit[]> {
  return api.get<PortalOrgUnit[]>("/portal/org/roots");
}

export async function fetchOrgChildren(
  parentId: number,
): Promise<PortalOrgUnit[]> {
  return api.get<PortalOrgUnit[]>(`/portal/org/children/${parentId}`);
}

export async function fetchBudgetsForOrg(
  zoneId: number,
  deptId?: number,
  sectionId?: number,
): Promise<PortalBudgetItem[]> {
  return api.get<PortalBudgetItem[]>("/portal/budgets/for-org", {
    zone_id: zoneId,
    ...(deptId ? { department_id: deptId } : {}),
    ...(sectionId ? { section_id: sectionId } : {}),
  });
}

export async function fetchAllBudgets(): Promise<PortalBudgetItem[]> {
  return api.get<PortalBudgetItem[]>("/portal/budgets/all", { limit: 200 });
}

export async function fetchCostCenters(): Promise<PortalCostCenter[]> {
  return api.get<PortalCostCenter[]>("/portal/cost-centers");
}

export async function fetchContinuousActions(): Promise<
  PortalContinuousAction[]
> {
  return api.get<PortalContinuousAction[]>("/portal/continuous-actions");
}

export async function fetchFinancialEvents(): Promise<PortalFinancialEvent[]> {
  return api.get<PortalFinancialEvent[]>("/portal/financial-events");
}
