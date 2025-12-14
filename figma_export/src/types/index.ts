// TypeScript types for the application

export interface User {
    id: number;
    username: string;
    full_name: string;
    role: 'user' | 'admin';
    zone_id?: number;
    dept_id?: number;
    section_id?: number;
}

export interface AuthResponse {
    authenticated: boolean;
    user?: User;
}

export interface LoginRequest {
    username: string;
    password: string;
}

export interface Zone {
    id: number;
    code: string;
    title: string;
}

export interface Department {
    id: number;
    code: string;
    title: string;
    zone_id: number;
}

export interface Section {
    id: number;
    code: string;
    title: string;
    dept_id: number;
}

export interface BudgetItem {
    id: number;
    code: string;
    title: string;
    zone_id: number;
    approved_amount: number;
    allocated_amount: number;
    spent_amount: number;
}

export interface FinancialEvent {
    id: number;
    code: string;
    title: string;
}

export interface CostCenter {
    id: number;
    code: string;
    title: string;
}

export interface ContinuousActivity {
    id: number;
    code: string;
    title: string;
}

export interface Transaction {
    id: number;
    unique_code: string;
    status: 'draft' | 'pending' | 'approved' | 'rejected' | 'paid';
    zone_id: number;
    zone_title?: string;
    dept_id?: number;
    dept_title?: string;
    section_id?: number;
    section_title?: string;
    budget_item_id: number;
    budget_code?: string;
    financial_event_id: number;
    financial_event_title?: string;
    cost_center_id?: number;
    beneficiary_name: string;
    beneficiary_code: string;
    amount: number;
    contract_number?: string;
    description?: string;
    created_by: number;
    created_by_name?: string;
    created_at: string;
    reviewed_by?: number;
    reviewed_by_name?: string;
    reviewed_at?: string;
    rejection_reason?: string;
}

export interface TransactionCreateRequest {
    transaction_type: string;
    fiscal_year: number;
    zone_id: number;
    dept_id?: number;
    section_id?: number;
    budget_item_id: number;
    financial_event_id: number;
    cost_center_id?: number;
    continuous_activity_id?: number;
    special_activity?: string;
    beneficiary_name: string;
    amount: number;
    contract_number?: string;
    description?: string;
}

export interface AdminTransactionsResponse {
    transactions: Transaction[];
    total: number;
    stats: {
        total: number;
        pending: number;
        approved: number;
        rejected: number;
        paid: number;
    };
}

export interface SpecialAction {
    id: number;
    local_record_id: string;
    unique_code?: string;
    financial_event_title?: string;
    amount: number;
    details?: {
        budget_row?: string;
        raw_date?: string;
        raw_rows?: any[];
    };
}
