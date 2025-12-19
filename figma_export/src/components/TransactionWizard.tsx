import React, { useState } from 'react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Progress } from './ui/progress';
import { ChevronRight, ChevronLeft, CheckCircle2, Loader2 } from 'lucide-react';
import { WizardStep1_AllowedActivities } from './wizard-steps/WizardStep1_AllowedActivities';
import { WizardStep1_TransactionType } from './wizard-steps/WizardStep1_TransactionType';
import { WizardStep2_Organization } from './wizard-steps/WizardStep2_Organization';
import { WizardStep3_Budget } from './wizard-steps/WizardStep3_Budget';
import { WizardStep4_FinancialEvent } from './wizard-steps/WizardStep4_FinancialEvent';
import { WizardStep5_Beneficiary } from './wizard-steps/WizardStep5_Beneficiary';
import { WizardStep6_Preview } from './wizard-steps/WizardStep6_Preview';
import { WizardStep7_Submit } from './wizard-steps/WizardStep7_Submit';
import { createTransaction, TransactionCreateData } from '../services/adapters';

export type TransactionFormData = {
  // Step 0 - Subsystem Selection (NEW)
  subsystemId?: number;
  subsystemCode?: string;
  subsystemTitle?: string;
  attachmentType?: string;  // 'upload', 'api', 'both'

  // Step 1 - Special Activity (NEW)
  subsystemActivityId?: number;
  subsystemActivityCode?: string;
  subsystemActivityTitle?: string;
  formType?: string;  // Form type for attachments

  // Step 2 - Transaction Type & Fiscal Year
  transactionType?: 'expense' | 'capital';
  fiscalYear?: string;

  // Step 3 - Organization
  zoneId?: number;
  zoneName?: string;
  zoneCode?: string;
  departmentId?: number;
  departmentName?: string;
  departmentCode?: string;
  sectionId?: number;
  sectionName?: string;
  sectionCode?: string;

  // Step 4 - Budget
  budgetItemId?: number;
  budgetCode?: string;
  budgetDescription?: string;
  budgetType?: string;  // 'expense' or 'capital'
  budgetRowType?: string;  // 'مستمر' or 'غیرمستمر' - for form selection in Step 5
  availableBudget?: number;

  // Step 5 - Financial Event & Cost Center
  financialEventId?: number;
  financialEventCode?: string;
  financialEventName?: string;
  costCenterId?: number;
  costCenterCode?: string;
  costCenterName?: string;
  continuousActionId?: number;
  continuousActionCode?: string;
  continuousActionName?: string;

  // Step 6 - Beneficiary & Contract
  beneficiaryName?: string;
  contractNumber?: string;
  amount?: number;
  description?: string;
  formData?: Record<string, unknown>;  // Holds form-specific data from image-based forms

  // Step 7 - Preview
  uniqueCode?: string;
};


type TransactionWizardProps = {
  userId: number;
};

// مراحل جدید: Step 0 (انتخاب سامانه) حذف شد
// کاربر مستقیماً فعالیت‌های مجاز خود را می‌بیند
const STEPS = [
  { number: 0, title: 'انتخاب فعالیت' },
  { number: 1, title: 'نوع تراکنش و سال مالی' },
  { number: 2, title: 'انتخاب واحد سازمانی' },
  { number: 3, title: 'انتخاب ردیف بودجه' },
  { number: 4, title: 'رویداد مالی و مرکز هزینه' },
  { number: 5, title: 'اطلاعات ذینفع و قرارداد' },
  { number: 6, title: 'پیش‌نمایش کد یکتا' },
  { number: 7, title: 'ثبت نهایی' },
];

export function TransactionWizard({ userId }: TransactionWizardProps) {
  const [currentStep, setCurrentStep] = useState(0);  // Start from step 0
  const [formData, setFormData] = useState<TransactionFormData>({});
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const updateFormData = (data: Partial<TransactionFormData>) => {
    setFormData(prev => ({ ...prev, ...data }));
  };

  const nextStep = () => {
    if (currentStep < 7) {  // Max step is 7 (8 total steps: 0-7)
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {  // Min step is 0
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async () => {
    // Build the payload for the API
    if (!formData.zoneId || !formData.budgetCode || !formData.beneficiaryName || !formData.amount) {
      setSubmitError('لطفاً تمام فیلدهای الزامی را تکمیل کنید');
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const payload: TransactionCreateData = {
        zone_id: formData.zoneId,
        department_id: formData.departmentId,
        section_id: formData.sectionId,
        budget_code: formData.budgetCode,
        cost_center_code: formData.costCenterCode,
        continuous_activity_code: formData.continuousActionCode,
        financial_event_code: formData.financialEventCode,
        beneficiary_name: formData.beneficiaryName,
        contract_number: formData.contractNumber,
        amount: formData.amount,
        description: formData.description,
        form_data: formData.formData,  // Include Step 5 form data
      };

      const result = await createTransaction(payload);

      // Update form data with the returned unique code
      updateFormData({ uniqueCode: result.unique_code });
      setIsSubmitted(true);
    } catch (error) {
      console.error('Transaction creation failed:', error);
      setSubmitError(error instanceof Error ? error.message : 'خطا در ثبت تراکنش');
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetWizard = () => {
    setCurrentStep(0);  // Reset to step 0
    setFormData({});
    setIsSubmitted(false);
    setSubmitError(null);
  };

  const progress = ((currentStep + 1) / 8) * 100;  // 8 total steps (0-7)

  if (isSubmitted) {
    return (
      <div className="max-w-2xl mx-auto">
        <Card className="p-8 text-center space-y-6">
          <div className="flex justify-center">
            <div className="bg-green-100 p-4 rounded-full">
              <CheckCircle2 className="h-12 w-12 text-green-600" />
            </div>
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl">تراکنش با موفقیت ثبت شد</h2>
            <p className="text-muted-foreground">
              کد یکتای تراکنش: <span className="font-mono">{formData.uniqueCode}</span>
            </p>
          </div>
          <div className="bg-amber-50 border border-amber-200 p-4 rounded text-sm text-amber-900">
            تراکنش شما در وضعیت "در انتظار تایید" قرار دارد و پس از بررسی مدیر، تایید یا رد خواهد شد.
          </div>
          <Button onClick={resetWizard} className="w-full">
            ایجاد تراکنش جدید
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Progress Header - Shows Current Position */}
      <Card className="p-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2>مرحله {currentStep + 1} از ۸</h2>
              <p className="text-sm text-muted-foreground">{STEPS[currentStep].title}</p>
            </div>
            <div className="text-left text-sm text-muted-foreground">
              {Math.round(progress)}% تکمیل شده
            </div>
          </div>
          <Progress value={progress} className="h-2" />
        </div>
      </Card>

      {/* Step Indicator - Visual Hierarchy */}
      <div className="flex items-center justify-between gap-2">
        {STEPS.map((step, index) => (
          <React.Fragment key={step.number}>
            <div className="flex flex-col items-center gap-1 flex-1">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm transition-colors ${step.number === currentStep
                  ? 'bg-primary text-primary-foreground'
                  : step.number < currentStep
                    ? 'bg-green-600 text-white'
                    : 'bg-muted text-muted-foreground'
                  }`}
              >
                {step.number < currentStep ? '✓' : step.number}
              </div>
              <p className={`text-xs text-center hidden md:block ${step.number === currentStep ? 'text-foreground' : 'text-muted-foreground'
                }`}>
                {step.title}
              </p>
            </div>
            {index < STEPS.length - 1 && (
              <div className={`h-0.5 flex-1 ${step.number < currentStep ? 'bg-green-600' : 'bg-border'
                }`} />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Current Step Content - مراحل بازنویسی شده */}
      <Card className="p-6">
        {currentStep === 0 && (
          <WizardStep1_AllowedActivities formData={formData} updateFormData={updateFormData} />
        )}
        {currentStep === 1 && (
          <WizardStep1_TransactionType formData={formData} updateFormData={updateFormData} />
        )}
        {currentStep === 2 && (
          <WizardStep2_Organization formData={formData} updateFormData={updateFormData} />
        )}
        {currentStep === 3 && (
          <WizardStep3_Budget formData={formData} updateFormData={updateFormData} />
        )}
        {currentStep === 4 && (
          <WizardStep4_FinancialEvent formData={formData} updateFormData={updateFormData} />
        )}
        {currentStep === 5 && (
          <WizardStep5_Beneficiary formData={formData} updateFormData={updateFormData} />
        )}
        {currentStep === 6 && (
          <WizardStep6_Preview formData={formData} updateFormData={updateFormData} />
        )}
        {currentStep === 7 && (
          <WizardStep7_Submit formData={formData} />
        )}
      </Card>

      {/* Navigation - Primary Action Dominant */}
      <Card className="p-4">
        {submitError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded mb-4 text-sm">
            {submitError}
          </div>
        )}
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={prevStep}
            disabled={currentStep === 0 || isSubmitting}
          >
            <ChevronRight className="h-4 w-4 ml-2" />
            مرحله قبل
          </Button>

          {currentStep < 7 ? (
            <Button onClick={nextStep} size="lg">
              مرحله بعد
              <ChevronLeft className="h-4 w-4 mr-2" />
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              size="lg"
              className="bg-green-600 hover:bg-green-700"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  در حال ثبت...
                </>
              ) : (
                <>
                  ثبت نهایی تراکنش
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                </>
              )}
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}
