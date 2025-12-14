import React, { useState } from 'react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Progress } from './ui/progress';
import { ChevronRight, ChevronLeft, CheckCircle2, Loader2 } from 'lucide-react';
import { WizardStep1_TransactionType } from './wizard-steps/WizardStep1_TransactionType';
import { WizardStep2_Organization } from './wizard-steps/WizardStep2_Organization';
import { WizardStep3_Budget } from './wizard-steps/WizardStep3_Budget';
import { WizardStep4_FinancialEvent } from './wizard-steps/WizardStep4_FinancialEvent';
import { WizardStep5_Beneficiary } from './wizard-steps/WizardStep5_Beneficiary';
import { WizardStep6_Preview } from './wizard-steps/WizardStep6_Preview';
import { WizardStep7_Submit } from './wizard-steps/WizardStep7_Submit';
import { createTransaction, TransactionCreateData } from '../services/adapters';

export type TransactionFormData = {
  // Step 1
  transactionType?: 'expense' | 'capital';
  fiscalYear?: string;

  // Step 2
  zoneId?: number;
  zoneName?: string;
  zoneCode?: string;
  departmentId?: number;
  departmentName?: string;
  departmentCode?: string;
  sectionId?: number;
  sectionName?: string;
  sectionCode?: string;

  // Step 3
  budgetItemId?: number;
  budgetCode?: string;
  budgetDescription?: string;
  budgetType?: string;
  availableBudget?: number;

  // Step 4
  financialEventId?: number;
  financialEventCode?: string;
  financialEventName?: string;
  costCenterId?: number;
  costCenterCode?: string;
  costCenterName?: string;
  continuousActionId?: number;
  continuousActionCode?: string;
  continuousActionName?: string;

  // Step 5
  beneficiaryName?: string;
  contractNumber?: string;
  amount?: number;
  description?: string;

  // Step 6
  uniqueCode?: string;
};

type TransactionWizardProps = {
  userId: number;
};

const STEPS = [
  { number: 1, title: 'نوع تراکنش و سال مالی' },
  { number: 2, title: 'انتخاب واحد سازمانی' },
  { number: 3, title: 'انتخاب ردیف بودجه' },
  { number: 4, title: 'رویداد مالی و مرکز هزینه' },
  { number: 5, title: 'اطلاعات ذینفع و قرارداد' },
  { number: 6, title: 'پیش‌نمایش کد یکتا' },
  { number: 7, title: 'ثبت نهایی' },
];

export function TransactionWizard({ userId }: TransactionWizardProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<TransactionFormData>({});
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const updateFormData = (data: Partial<TransactionFormData>) => {
    setFormData(prev => ({ ...prev, ...data }));
  };

  const nextStep = () => {
    if (currentStep < 7) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
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
    setCurrentStep(1);
    setFormData({});
    setIsSubmitted(false);
    setSubmitError(null);
  };

  const progress = (currentStep / 7) * 100;

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
              <h2>مرحله {currentStep} از ۷</h2>
              <p className="text-sm text-muted-foreground">{STEPS[currentStep - 1].title}</p>
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

      {/* Current Step Content - ONE DECISION AT A TIME */}
      <Card className="p-6">
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
            disabled={currentStep === 1 || isSubmitting}
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
