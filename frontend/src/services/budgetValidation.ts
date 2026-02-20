/**
 * useBudgetValidation Hook
 * 
 * Provides real-time budget validation for the Transaction Wizard.
 * - Compares requested amount against available budget
 * - Returns validation state and error messages
 * - Used in Step 5 forms and Step 7 submission
 */

import { useState, useEffect, useMemo } from 'react';
import api from './api';
import { formatRial } from '../lib/utils';

// Types
export interface BudgetCheckResponse {
    budget_row_id: number;
    budget_code: string;
    description: string;
    activity_id?: number;
    activity_code?: string;
    fiscal_year: string;
    total_approved: number;
    total_blocked: number;
    total_spent: number;
    remaining_available: number;
    status: 'AVAILABLE' | 'LOW' | 'EXHAUSTED';
    utilization_percent: number;
}

export interface BlockFundsRequest {
    budget_row_id: number;
    amount: number;
    request_reference_id?: string;
    notes?: string;
}

export interface BlockFundsResponse {
    transaction_id: number;
    budget_row_id: number;
    budget_code: string;
    status: 'BLOCKED' | 'RELEASED' | 'SPENT';
    amount: number;
    reference_doc?: string;
    performed_by: string;
    created_at: string;
    new_remaining_balance: number;
}

export interface BudgetValidationState {
    isValid: boolean;
    errorMessage: string | null;
    warningMessage: string | null;
    remainingBudget: number;
    isLoading: boolean;
    canProceed: boolean;  // Controls "Next" button
}

// Error codes from Backend
export type BudgetErrorCode =
    | 'INSUFFICIENT_FUNDS'
    | 'BUDGET_NOT_FOUND'
    | 'INVALID_OPERATION'
    | 'DATABASE_ERROR';

export interface BudgetApiError {
    error: BudgetErrorCode;
    message: string;
    budget_row_id?: number;
    requested_amount?: number;
    available_balance?: number;
}

/**
 * @deprecated Use `formatRial` from `@/lib/utils` instead.
 * Kept as a re-export for backward-compatibility during migration.
 */
export const formatCurrencyRial = formatRial;

/**
 * useBudgetValidation - Custom Hook for Real-Time Budget Validation
 * 
 * @param budgetRowId - Selected budget row ID
 * @param requestedAmount - Amount entered by user (Rials)
 * @param availableBudget - Available budget from formData (optional, for offline validation)
 */
export function useBudgetValidation(
    budgetRowId: number | undefined,
    requestedAmount: number | undefined,
    availableBudget?: number
): BudgetValidationState {
    const [isLoading, setIsLoading] = useState(false);
    const [remoteBudget, setRemoteBudget] = useState<BudgetCheckResponse | null>(null);
    const [fetchError, setFetchError] = useState<string | null>(null);

    // Fetch latest budget from server when budgetRowId changes
    useEffect(() => {
        if (!budgetRowId) {
            setRemoteBudget(null);
            return;
        }

        const fetchBudget = async () => {
            setIsLoading(true);
            setFetchError(null);

            try {
                // Note: our api wrapper returns data directly, not axios-style { data }
                const budgetData = await api.get<BudgetCheckResponse>(`/budget/row/${budgetRowId}`);
                setRemoteBudget(budgetData);
            } catch (error: unknown) {
                console.error('Failed to fetch budget:', error);
                setFetchError('خطا در دریافت اطلاعات بودجه');
            } finally {
                setIsLoading(false);
            }
        };

        fetchBudget();
    }, [budgetRowId]);

    // Calculate validation state
    const validationState = useMemo((): BudgetValidationState => {
        // Use remote budget if available, fallback to offline
        const remaining = remoteBudget?.remaining_available ?? availableBudget ?? 0;
        const amount = requestedAmount ?? 0;

        // Default state
        const state: BudgetValidationState = {
            isValid: true,
            errorMessage: null,
            warningMessage: null,
            remainingBudget: remaining,
            isLoading,
            canProceed: true,
        };

        // If still loading, don't validate yet
        if (isLoading) {
            state.canProceed = false;
            return state;
        }

        // If fetch error, show warning but allow proceed (offline mode)
        if (fetchError && !availableBudget) {
            state.warningMessage = fetchError;
            return state;
        }

        // No amount entered yet - valid but incomplete
        if (!amount || amount <= 0) {
            return state;
        }

        // CRITICAL VALIDATION: Amount exceeds available budget
        if (amount > remaining) {
            state.isValid = false;
            state.canProceed = false;  // DISABLE NEXT BUTTON
            state.errorMessage = `مبلغ وارد شده (${formatRial(amount)}) بیشتر از مانده اعتبار (${formatRial(remaining)}) است.`;
            return state;
        }

        // Warning: If remaining budget is low (< 20% after this transaction)
        const remainingAfter = remaining - amount;
        const totalApproved = remoteBudget?.total_approved ?? remaining;
        if (totalApproved > 0) {
            const utilizationAfter = ((totalApproved - remainingAfter) / totalApproved) * 100;
            if (utilizationAfter > 80 && utilizationAfter < 100) {
                state.warningMessage = `توجه: پس از این تراکنش، تنها ${formatRial(remainingAfter)} از بودجه باقی می‌ماند.`;
            }
        }

        return state;
    }, [remoteBudget, availableBudget, requestedAmount, isLoading, fetchError]);

    return validationState;
}

/**
 * blockBudgetFunds - Call the Budget Block API
 * 
 * Call this in the final submission step BEFORE saving the transaction.
 * 
 * @returns BlockFundsResponse on success
 * @throws Error with Persian message on failure
 */
export async function blockBudgetFunds(
    budgetRowId: number,
    amount: number,
    referenceId?: string,
    notes?: string
): Promise<BlockFundsResponse> {
    try {
        const payload: BlockFundsRequest = {
            budget_row_id: budgetRowId,
            amount,
            request_reference_id: referenceId,
            notes,
        };

        // Note: our api wrapper returns data directly, not axios-style { data }
        const result = await api.post<BlockFundsResponse>('/budget/block', payload);
        return result;
    } catch (error: unknown) {
        // Parse error response
        const axiosError = error as { response?: { data?: BudgetApiError; status?: number } };
        const data = axiosError.response?.data;
        const status = axiosError.response?.status;

        if (status === 400 && data?.error === 'INSUFFICIENT_FUNDS') {
            throw new Error(
                `بودجه کافی نیست. مبلغ درخواستی: ${formatRial(data.requested_amount ?? 0)}، ` +
                `مانده قابل استفاده: ${formatRial(data.available_balance ?? 0)}`
            );
        }

        if (status === 404) {
            throw new Error('ردیف بودجه یافت نشد. لطفاً مجدداً تلاش کنید.');
        }

        if (status === 500) {
            throw new Error('خطای سرور. لطفاً با پشتیبانی تماس بگیرید.');
        }

        throw new Error('خطا در رزرو بودجه. لطفاً مجدداً تلاش کنید.');
    }
}

export default useBudgetValidation;
