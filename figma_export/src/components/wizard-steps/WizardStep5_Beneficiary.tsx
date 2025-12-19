import React from 'react';
import { TransactionFormData } from '../TransactionWizard';
import { FormSelector, getFormType } from '../forms/FormSelector';
import { Card } from '../ui/card';
import { AlertCircle, FileText } from 'lucide-react';


type Props = {
  formData: TransactionFormData;
  updateFormData: (data: Partial<TransactionFormData>) => void;
};

/**
 * WizardStep5_Beneficiary - Step 5 of the transaction wizard
 * 
 * This step shows one of 4 forms based on budget_type and row_type:
 * - expense + مستمر → CurrentExpenseForm
 * - expense + غیرمستمر → ContractorProgressForm
 * - capital → PerformanceBondForm or AccountTransferForm
 */
export function WizardStep5_Beneficiary({ formData, updateFormData }: Props) {
  const formType = getFormType(formData.budgetType, formData.budgetRowType);

  // Helper to get form title
  const getFormTitle = () => {
    switch (formType) {
      case 'current':
        return 'فرم هزینه‌های جاری';
      case 'contractor':
        return 'فرم محاسبه صورت وضعیت پیمانکاران';
      case 'bond':
        return 'فرم استرداد سپرده حسن انجام کار';
      case 'transfer':
        return 'فرم جابجایی حساب مناطق و سازمان‌ها';
      default:
        return 'فرم اطلاعات ذینفع و قرارداد';
    }
  };

  // Check if budget is selected
  if (!formData.budgetItemId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-amber-600">
          <AlertCircle className="h-5 w-5" />
          <h3>انتخاب ردیف بودجه</h3>
        </div>
        <Card className="p-8 text-center text-muted-foreground">
          <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p>لطفاً ابتدا ردیف بودجه را در مرحله قبل انتخاب کنید</p>
          <p className="text-sm mt-2">فرم مناسب بر اساس نوع بودجه انتخاب شده نمایش داده خواهد شد</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Form Type Indicator */}
      <div className="bg-accent/50 border border-border rounded-lg p-3 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">نوع فرم:</span>
          <span className="font-medium">{getFormTitle()}</span>
        </div>
        <div className="flex items-center justify-between mt-1">
          <span className="text-muted-foreground">نوع بودجه:</span>
          <span className={`px-2 py-0.5 rounded text-xs ${formData.budgetType === 'expense'
            ? 'bg-blue-100 text-blue-700'
            : 'bg-purple-100 text-purple-700'
            }`}>
            {formData.budgetType === 'expense' ? 'هزینه‌ای' : 'سرمایه‌ای'}
          </span>
        </div>
        {formData.budgetRowType && (
          <div className="flex items-center justify-between mt-1">
            <span className="text-muted-foreground">نوع ردیف:</span>
            <span className="text-xs">{formData.budgetRowType}</span>
          </div>
        )}
      </div>

      {/* Dynamic Form based on budget_type and row_type */}
      <FormSelector formData={formData} updateFormData={updateFormData} />
    </div>
  );
}

export default WizardStep5_Beneficiary;
