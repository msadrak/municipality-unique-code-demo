import React from 'react';
import { TransactionFormData } from '../TransactionWizard';
import { ContractorProgressForm } from './ContractorProgressForm';
import { CurrentExpenseForm } from './CurrentExpenseForm';
import { PerformanceBondForm } from './PerformanceBondForm';
import { AccountTransferForm } from './AccountTransferForm';

type FormSelectorProps = {
    formData: TransactionFormData;
    updateFormData: (data: Partial<TransactionFormData>) => void;
};

/**
 * Form type determination logic based on budget type and row type:
 * 
 * Expense (هزینه‌ای):
 *   - مستمر (continuous) → CurrentExpenseForm (هزینه‌های جاری)
 *   - غیرمستمر (non-continuous) → ContractorProgressForm (صورت وضعیت پیمانکاران)
 * 
 * Capital (سرمایه‌ای):
 *   - Default → PerformanceBondForm (استرداد سپرده حسن انجام کار)
 *   - Transfer context → AccountTransferForm (جابجایی حساب)
 */
export function getFormType(budgetType?: string, rowType?: string): 'contractor' | 'current' | 'bond' | 'transfer' {
    if (budgetType === 'capital') {
        // For capital budgets, default to performance bond form
        // Account transfer form would need explicit selection (future enhancement)
        return 'bond';
    }

    // For expense budgets
    if (rowType === 'مستمر') {
        return 'current';
    }

    // Default to contractor progress for non-continuous or undefined
    return 'contractor';
}

export function FormSelector({ formData, updateFormData }: FormSelectorProps) {
    const formType = getFormType(formData.budgetType, formData.budgetRowType);

    const handleFormDataChange = (data: Record<string, unknown>) => {
        updateFormData({
            formData: { ...formData.formData, ...data, _formType: formType }
        });
    };

    switch (formType) {
        case 'current':
            return (
                <CurrentExpenseForm
                    formData={formData}
                    updateFormData={updateFormData}
                    onFormDataChange={handleFormDataChange}
                />
            );
        case 'contractor':
            return (
                <ContractorProgressForm
                    formData={formData}
                    updateFormData={updateFormData}
                    onFormDataChange={handleFormDataChange}
                />
            );
        case 'bond':
            return (
                <PerformanceBondForm
                    formData={formData}
                    updateFormData={updateFormData}
                    onFormDataChange={handleFormDataChange}
                />
            );
        case 'transfer':
            return (
                <AccountTransferForm
                    formData={formData}
                    updateFormData={updateFormData}
                    onFormDataChange={handleFormDataChange}
                />
            );
        default:
            return (
                <CurrentExpenseForm
                    formData={formData}
                    updateFormData={updateFormData}
                    onFormDataChange={handleFormDataChange}
                />
            );
    }
}

export default FormSelector;
