// Adapter layer to transform backend data to Figma component format
// This keeps both backend and Figma components unchanged

// ==================== Types ====================

export interface FigmaOrgUnit {
    id: number;
    code: string;
    name: string;  // Figma expects 'name', backend returns 'title'
}

export interface FigmaBudgetItem {
    id: number;
    code: string;
    name: string;
    allocated: number;
    remaining: number;
    type?: string;  // 'expense' or 'capital'
    rowType?: string;  // 'مستمر' or 'غیرمستمر'
    trustee?: string;  // متولی
}

export interface FigmaFinancialEvent {
    id: number;
    code: string;
    name: string;
}

export interface FigmaCostCenter {
    id: number;
    code: string;
    name: string;
}

export interface FigmaTransaction {
    id: number;
    uniqueCode: string;
    beneficiaryName: string;
    amount: number;
    status: 'draft' | 'pending' | 'approved' | 'rejected' | 'paid';
    zoneName?: string;
    createdAt?: string;
    rejectionReason?: string;
}

// ==================== Adapter Functions ====================

/**
 * Adapt backend OrgUnit to Figma format
 * Backend: { id, code, title }
 * Figma: { id, code, name }
 */
export function adaptOrgUnit(backend: any): FigmaOrgUnit {
    return {
        id: backend.id,
        code: backend.code || '',
        name: backend.title || backend.name || '',
    };
}

export function adaptOrgUnits(backendArray: any[]): FigmaOrgUnit[] {
    return (backendArray || []).map(adaptOrgUnit);
}

/**
 * Adapt backend BudgetItem to Figma format
 * Backend: { id, budget_code, description, allocated_1403, remaining_budget }
 * Figma: { id, code, name, allocated, remaining }
 */
export function adaptBudgetItem(backend: any): FigmaBudgetItem {
    return {
        id: backend.id,
        code: backend.budget_code || backend.code || '',
        name: backend.description || backend.title || '',
        allocated: backend.allocated_1403 || backend.allocated || 0,
        remaining: backend.remaining_budget || backend.remaining || 0,
        type: backend.budget_type,
        rowType: backend.row_type,
        trustee: backend.trustee,
    };
}

export function adaptBudgetItems(backendArray: any[]): FigmaBudgetItem[] {
    return (backendArray || []).map(adaptBudgetItem);
}

/**
 * Adapt backend FinancialEvent to Figma format
 */
export function adaptFinancialEvent(backend: any): FigmaFinancialEvent {
    return {
        id: backend.id,
        code: backend.code || '',
        name: backend.title || backend.name || '',
    };
}

export function adaptFinancialEvents(backendArray: any[]): FigmaFinancialEvent[] {
    return (backendArray || []).map(adaptFinancialEvent);
}

/**
 * Adapt backend CostCenter to Figma format
 */
export function adaptCostCenter(backend: any): FigmaCostCenter {
    return {
        id: backend.id,
        code: backend.code || '',
        name: backend.title || backend.name || '',
    };
}

export function adaptCostCenters(backendArray: any[]): FigmaCostCenter[] {
    return (backendArray || []).map(adaptCostCenter);
}

/**
 * Adapt backend Transaction to Figma format
 */
export function adaptTransaction(backend: any): FigmaTransaction {
    // Normalize legacy statuses to new PENDING_L format
    let status = backend.status || 'PENDING_L1';
    // Map old 'pending' to PENDING_L1
    if (status === 'pending') status = 'PENDING_L1';
    if (status === 'approved') status = 'APPROVED';
    if (status === 'rejected') status = 'REJECTED';

    return {
        id: backend.id,
        uniqueCode: backend.unique_code || '',
        beneficiaryName: backend.beneficiary_name || '',
        amount: backend.amount || 0,
        status: status,
        zoneName: backend.zone_title,
        createdAt: backend.created_at,
        rejectionReason: backend.rejection_reason,
    };
}

export function adaptTransactions(backendArray: any[]): FigmaTransaction[] {
    return (backendArray || []).map(adaptTransaction);
}

// ==================== API Fetchers with Adapters ====================

/**
 * Fetch zones (root org units) and adapt to Figma format
 */
export async function fetchZones(): Promise<FigmaOrgUnit[]> {
    const response = await fetch('/portal/org/roots', { credentials: 'include' });
    if (!response.ok) throw new Error('Failed to fetch zones');
    const data = await response.json();
    return adaptOrgUnits(data);
}

/**
 * Fetch children of an org unit and adapt to Figma format
 */
export async function fetchOrgChildren(parentId: number): Promise<FigmaOrgUnit[]> {
    const response = await fetch(`/portal/org/children/${parentId}`, { credentials: 'include' });
    if (!response.ok) throw new Error('Failed to fetch org children');
    const data = await response.json();
    return adaptOrgUnits(data);
}

/**
 * Fetch trustees for a zone (for trustee dropdown)
 */
export async function fetchTrustees(zoneCode: string): Promise<{ trustees: string[]; zoneTitle: string }> {
    const response = await fetch(`/portal/budgets/trustees/${zoneCode}`, { credentials: 'include' });
    if (!response.ok) throw new Error('Failed to fetch trustees');
    const data = await response.json();
    return {
        trustees: data.trustees || [],
        zoneTitle: data.zone_title || ''
    };
}

/**
 * Fetch budgets by zone and optionally by trustee, adapt to Figma format
 */
export async function fetchBudgets(zoneCode: string, trustee?: string): Promise<FigmaBudgetItem[]> {
    let url = `/portal/budgets/by-zone/${zoneCode}`;
    if (trustee) {
        url += `?trustee=${encodeURIComponent(trustee)}`;
    }
    const response = await fetch(url, { credentials: 'include' });
    if (!response.ok) throw new Error('Failed to fetch budgets');
    const data = await response.json();
    return adaptBudgetItems(data);
}


/**
 * Fetch financial events and adapt to Figma format
 */
export async function fetchFinancialEvents(): Promise<FigmaFinancialEvent[]> {
    const response = await fetch('/portal/financial-events', { credentials: 'include' });
    if (!response.ok) throw new Error('Failed to fetch financial events');
    const data = await response.json();
    return adaptFinancialEvents(data);
}

/**
 * Fetch cost centers and adapt to Figma format
 */
export async function fetchCostCenters(): Promise<FigmaCostCenter[]> {
    const response = await fetch('/portal/cost-centers', { credentials: 'include' });
    if (!response.ok) throw new Error('Failed to fetch cost centers');
    const data = await response.json();
    return adaptCostCenters(data);
}

// Continuous Action Type
export interface FigmaContinuousAction {
    id: number;
    code: string;
    name: string;
}

/**
 * Adapt backend ContinuousAction to Figma format
 */
export function adaptContinuousAction(backend: any): FigmaContinuousAction {
    return {
        id: backend.id,
        code: backend.code || '',
        name: backend.title || backend.name || '',
    };
}

export function adaptContinuousActions(backendArray: any[]): FigmaContinuousAction[] {
    return (backendArray || []).map(adaptContinuousAction);
}

/**
 * Fetch continuous actions and adapt to Figma format
 */
export async function fetchContinuousActions(): Promise<FigmaContinuousAction[]> {
    const response = await fetch('/portal/continuous-actions', { credentials: 'include' });
    if (!response.ok) throw new Error('Failed to fetch continuous actions');
    const data = await response.json();
    return adaptContinuousActions(data);
}

// ==================== ORG-CONTEXT FILTERED API FETCHERS ====================
// These use the new /for-org endpoints that derive data from Hesabdary Information.xlsx
// No trustee selection required - data is filtered by org context only

/**
 * Fetch budgets filtered by org context (zone/department/section).
 * This replaces the trustee-based budget fetching.
 * @deprecated Use fetchBudgetsByActivity for Zero-Trust budget access
 */
export async function fetchBudgetsForOrg(
    zoneId: number,
    departmentId?: number,
    sectionId?: number
): Promise<FigmaBudgetItem[]> {
    const params = new URLSearchParams();
    params.append('zone_id', zoneId.toString());
    if (departmentId) params.append('department_id', departmentId.toString());
    if (sectionId) params.append('section_id', sectionId.toString());

    const response = await fetch(`/portal/budgets/for-org?${params}`, { credentials: 'include' });
    if (!response.ok) throw new Error('Failed to fetch budgets for org');
    const data = await response.json();
    return adaptBudgetItems(data);
}

// ==================== ZERO-TRUST BUDGET API ====================
// New API that fetches from BudgetRow table with activity-based filtering

/**
 * Response type from /budget/list/{activity_id} endpoint
 */
export interface BudgetRowResponse {
    budget_row_id: number;
    budget_code: string;
    description: string;
    activity_id: number;
    activity_code: string | null;
    fiscal_year: string;
    total_approved: number;
    total_blocked: number;
    total_spent: number;
    remaining_available: number;
    status: 'AVAILABLE' | 'LOW' | 'EXHAUSTED';
    utilization_percent: number;
}

/**
 * Fetch budget rows by activity ID (Zero-Trust API)
 * This is the NEW recommended way to fetch budgets for WizardStep3
 * 
 * @param activityId - The selected activity ID
 * @param zoneId - Optional zone ID for zone-based filtering
 * @param fiscalYear - Optional fiscal year (defaults to "1403")
 */
export async function fetchBudgetsByActivity(
    activityId: number,
    zoneId?: number,
    fiscalYear?: string
): Promise<BudgetRowResponse[]> {
    console.group("🔍 Budget API Request");
    console.log("Inputs:", { activityId, zoneId, fiscalYear });

    const params = new URLSearchParams();
    if (zoneId) params.append('zone_id', zoneId.toString());
    if (fiscalYear) params.append('fiscal_year', fiscalYear);

    const url = `/budget/list/${activityId}${params.toString() ? '?' + params : ''}`;
    console.log("Request URL:", url);

    const response = await fetch(url, { credentials: 'include' });
    console.log("Response Status:", response.status);

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to fetch budgets' }));
        console.error("❌ API Error:", error);
        console.groupEnd();
        throw new Error(error.detail || 'Failed to fetch budgets');
    }

    const data = await response.json();
    console.log("Rows Received:", data.budget_rows?.length ?? 0);
    console.log("Raw Response:", data);
    console.groupEnd();

    // FIXED: Unwrap the response object (backend returns { budget_rows: [...] })
    // Ensure we return the array directly, not the wrapper object
    if (Array.isArray(data.budget_rows)) {
        return data.budget_rows;
    }

    // Defensive fallback
    console.warn("⚠️ API response structure mismatch: 'budget_rows' not found or not an array");
    return [];
}

/**
 * Adapt BudgetRowResponse to FigmaBudgetItem for backwards compatibility
 */
export function adaptBudgetRowToFigma(budgetRow: BudgetRowResponse): FigmaBudgetItem {
    return {
        id: budgetRow.budget_row_id,
        code: budgetRow.budget_code,
        name: budgetRow.description,
        allocated: budgetRow.total_approved,
        remaining: budgetRow.remaining_available,
        type: undefined, // Not available in new API
        rowType: undefined,
        trustee: undefined,
    };
}

/**
 * Fetch cost centers filtered by org context.
 * Source: OrgBudgetMap.cost_center_desc from Hesabdary Information.xlsx
 */
export async function fetchCostCentersForOrg(
    zoneId: number,
    departmentId?: number,
    sectionId?: number
): Promise<FigmaCostCenter[]> {
    const params = new URLSearchParams();
    params.append('zone_id', zoneId.toString());
    if (departmentId) params.append('department_id', departmentId.toString());
    if (sectionId) params.append('section_id', sectionId.toString());

    const response = await fetch(`/portal/cost-centers/for-org?${params}`, { credentials: 'include' });
    if (!response.ok) throw new Error('Failed to fetch cost centers for org');
    const data = await response.json();
    return adaptCostCenters(data);
}

/**
 * Fetch continuous actions filtered by org context.
 * Source: OrgBudgetMap.continuous_action_desc (سرفصل جزء) from Hesabdary Information.xlsx
 */
export async function fetchContinuousActionsForOrg(
    zoneId: number,
    departmentId?: number,
    sectionId?: number
): Promise<FigmaContinuousAction[]> {
    const params = new URLSearchParams();
    params.append('zone_id', zoneId.toString());
    if (departmentId) params.append('department_id', departmentId.toString());
    if (sectionId) params.append('section_id', sectionId.toString());

    const response = await fetch(`/portal/continuous-actions/for-org?${params}`, { credentials: 'include' });
    if (!response.ok) throw new Error('Failed to fetch continuous actions for org');
    const data = await response.json();
    return adaptContinuousActions(data);
}

/**
 * Fetch user's transactions and adapt to Figma format
 */
export async function fetchMyTransactions(): Promise<FigmaTransaction[]> {
    const response = await fetch('/portal/my-transactions', { credentials: 'include' });
    if (!response.ok) throw new Error('Failed to fetch transactions');
    const data = await response.json();
    return adaptTransactions(data.transactions || []);
}

/**
 * Fetch all transactions for admin and adapt to Figma format
 */
export async function fetchAdminTransactions(params?: {
    status?: string;
    search?: string;
    page?: number;
}): Promise<{ transactions: FigmaTransaction[]; total: number; stats: any }> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.append('status', params.status);
    if (params?.search) searchParams.append('search', params.search);
    if (params?.page) searchParams.append('page', params.page.toString());

    const response = await fetch(`/admin/transactions?${searchParams}`, { credentials: 'include' });
    if (!response.ok) throw new Error('Failed to fetch admin transactions');
    const data = await response.json();
    return {
        transactions: adaptTransactions(data.transactions || []),
        total: data.total,
        stats: data.stats,
    };
}

// Transaction Creation Types
export interface TransactionCreateData {
    credit_request_id?: number;  // Stage 1 Gateway
    zone_id: number;
    department_id?: number;
    section_id?: number;
    budget_code: string;
    cost_center_code?: string;
    continuous_activity_code?: string;
    special_activity?: string;
    financial_event_code?: string;
    beneficiary_name: string;
    contract_number?: string;
    amount: number;
    description?: string;
    form_data?: Record<string, unknown>;
}

export interface TransactionCreateResponse {
    status: string;
    message: string;
    transaction_id: number;
    unique_code: string;
    parts: Record<string, string>;
}

/**
 * Create a new transaction
 */
export async function createTransaction(data: TransactionCreateData): Promise<TransactionCreateResponse> {
    const response = await fetch('/portal/transactions/create', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'خطا در ایجاد تراکنش' }));
        throw new Error(error.detail || 'خطا در ایجاد تراکنش');
    }
    return response.json();
}

// ==================== ADMIN APPROVAL WORKFLOW ====================

export interface ApprovalResponse {
    status: string;
    message: string;
    new_status: string;
    approved_by_level?: number;
    rejected_by_level?: number;
}

/**
 * Approve a transaction (calls backend API)
 * Advances the transaction to the next approval level
 */
export async function approveTransaction(txId: number): Promise<ApprovalResponse> {
    const response = await fetch(`/admin/transactions/${txId}/approve`, {
        method: 'POST',
        credentials: 'include',
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'خطا در تایید تراکنش' }));
        throw new Error(error.detail || 'خطا در تایید تراکنش');
    }
    return response.json();
}

/**
 * Reject a transaction (calls backend API)
 * @param txId - Transaction ID
 * @param reason - Rejection reason (required)
 * @param returnToUser - If true, returns to DRAFT for user to fix; if false, REJECTED (final)
 */
export async function rejectTransaction(
    txId: number,
    reason: string,
    returnToUser: boolean = false
): Promise<ApprovalResponse> {
    const response = await fetch(`/admin/transactions/${txId}/reject`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason, return_to_user: returnToUser }),
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'خطا در رد تراکنش' }));
        throw new Error(error.detail || 'خطا در رد تراکنش');
    }
    return response.json();
}

export default {
    fetchZones,
    fetchOrgChildren,
    fetchBudgets,
    fetchBudgetsForOrg,
    fetchFinancialEvents,
    fetchCostCenters,
    fetchCostCentersForOrg,
    fetchContinuousActions,
    fetchContinuousActionsForOrg,
    fetchMyTransactions,
    fetchAdminTransactions,
    createTransaction,
    approveTransaction,
    rejectTransaction,
};
