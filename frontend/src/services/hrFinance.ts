import api from './api';

export interface AllocationLine {
  id: string;
  orgUnitLabel: string;
  costCenterCode: string;
  budgetLineCode: string;
  financialEventType: string;
  allocatedAmount: number;
  legalDeductions: number;
  penalties: number;
  netAmount: number;
}

export interface HRFinanceAllocationLine {
  id?: number | string;
  org_unit_name: string;
  cost_center_code: string;
  budget_line_code: string;
  financial_event_type: string;
  allocated_amount: number;
  legal_deductions?: number | null;
  penalties?: number | null;
  net_amount?: number | null;
  unique_code?: string | null;
}

export interface GeneratedHRTransactionCode {
  region: string;
  code: string;
}

export interface HRFinanceWorkflowContext {
  transaction: {
    id: number;
    status: string;
    gross_amount?: number | null;
    activity_id?: number | null;
    activity_name?: string | null;
    contract_number?: string | null;
  };
  operational_context: {
    work_period_id: number;
    name: string;
    year: number;
    month: number;
    date_range: {
      start: string;
      end: string;
    };
    contractor_name?: string | null;
    contract_number?: string | null;
  };
  financial_rules: {
    cost_center_code: string;
    budget_line_code: string;
    financial_event_type: string;
  };
  allocation_lines?: HRFinanceAllocationLine[] | null;
}

export async function fetchHRFinanceWorkflowContext(
  transactionId: number,
): Promise<HRFinanceWorkflowContext> {
  return api.get<HRFinanceWorkflowContext>(
    `/api/hr-finance/workflow/${transactionId}/context`,
  );
}

export async function submitHRTransaction(
  transactionId: string | number,
  allocations: AllocationLine[],
): Promise<GeneratedHRTransactionCode[]> {
  return api.post<GeneratedHRTransactionCode[]>(
    `/api/hr-finance/workflow/${transactionId}/finalize`,
    {
      allocations: allocations.map((allocation) => ({
        org_unit_name: allocation.orgUnitLabel,
        cost_center_code: allocation.costCenterCode,
        budget_line_code: allocation.budgetLineCode,
        financial_event_type: allocation.financialEventType,
        allocated_amount: allocation.allocatedAmount,
        legal_deductions: allocation.legalDeductions,
        penalties: allocation.penalties,
        net_amount: allocation.netAmount,
      })),
    },
  );
}

