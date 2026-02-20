// Dashboard types matching the /portal/dashboard/init API response
// These types are used for the dynamic dashboard initialization

export interface UserContext {
    user_id: number;
    user_name: string;
    zone_id: number | null;
    zone_code: string | null;
    zone_title: string | null;
    section_id: number | null;
    section_code: string | null;
    section_title: string | null;
}

export interface SubsystemInfo {
    id: number;
    code: string;
    title: string;
    icon: string | null;
    attachment_type: string | null;
}

export interface ActivityConstraint {
    budget_code_pattern: string | null;
    allowed_budget_types: string[] | null;
    cost_center_pattern: string | null;
    allowed_cost_centers: number[] | null;
    constraint_type: 'INCLUDE' | 'EXCLUDE';
}

export interface AllowedActivity {
    id: number;
    code: string;
    title: string;
    form_type: string | null;
    frequency: 'daily' | 'monthly' | 'yearly' | null;
    requires_file_upload: boolean;
    external_service_url: string | null;
    constraints: ActivityConstraint | null;
}

export interface DashboardInitResponse {
    user_context: UserContext;
    subsystem: SubsystemInfo | null;
    allowed_activities: AllowedActivity[];
    has_subsystem: boolean;
    message: string | null;
}

// ============ Executive Dashboard Report Types ============

export interface DashboardSummaryResponse {
    total_budget: number;
    committed_funds: number;
    executed_funds: number;
    active_contracts: number;
    by_department: Array<{
        name: string; // Persian name
        budget: number;
        spent: number;
        remaining: number;
    }>;
    by_section: Array<{
        name: string;
        value: number; // Budget amount
        color: string; // Hex code
    }>;
}
