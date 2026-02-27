import React, { useState, useEffect, useMemo } from 'react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Progress } from './ui/progress';
import { ChevronRight, ChevronLeft, CheckCircle2, Loader2, Zap, AlertTriangle } from 'lucide-react';
import { WizardStep_CivilProjectSelect } from './wizard-steps/WizardStep_CivilProjectSelect';
import { WizardStep_ContractorAndDetails } from './wizard-steps/WizardStep_ContractorAndDetails';
import { WizardStep1_TransactionType } from './wizard-steps/WizardStep1_TransactionType';
import { WizardStep2_Organization } from './wizard-steps/WizardStep2_Organization';
import { WizardStep3_Budget } from './wizard-steps/WizardStep3_Budget';
import { WizardStep3_CivilCredit } from './wizard-steps/WizardStep3_CivilCredit';
import { WizardStep4_ContractFetch } from './wizard-steps/WizardStep4_ContractFetch';
import { WizardStep4_FinancialEvent } from './wizard-steps/WizardStep4_FinancialEvent';
import { WizardStep5_Attachments } from './wizard-steps/WizardStep5_Attachments';
import { WizardStep6_Preview } from './wizard-steps/WizardStep6_Preview';
import { WizardStep7_Submit } from './wizard-steps/WizardStep7_Submit';
import { createTransaction, TransactionCreateData } from '../services/adapters';
import { useTransactionStore } from '../stores/useTransactionStore';
import { ActivityConstraint } from '../types/dashboard';
import { useBudgetValidation, blockBudgetFunds } from '../services/budgetValidation';
import { formatRial } from '../lib/utils';
import { CreditRequestGateSelector } from './CreditRequestGateSelector';
import type { CreditRequestListItem } from '../types/creditRequest';
import type { GaamStatus } from '../services/mockGaamService';

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

  // Step 3 - Transaction Type & Fiscal Year
  transactionType?: 'expense' | 'capital';
  fiscalYear?: string;

  // Step 4 - Organization
  zoneId?: number;
  zoneName?: string;
  zoneCode?: string;
  departmentId?: number;
  departmentName?: string;
  departmentCode?: string;
  sectionId?: number;
  sectionName?: string;
  sectionCode?: string;

  // Step 2 - Budget
  budgetItemId?: number;
  budgetCode?: string;
  budgetDescription?: string;
  budgetType?: string;  // 'expense' or 'capital'
  budgetRowType?: string;  // 'مستمر' or 'غیرمستمر' - for form selection in Step 5
  availableBudget?: number;

  // Step 5 - Attachments (NEW)
  attachments?: any[];

  // Step 5 (Legacy - Kept for API Payload compatibility)
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

  // Stage 1 Gateway
  creditRequestId?: number;
  creditRequestCode?: string;
  creditRequestAmount?: number;

  // Civil Project (Step 0 - pilot)
  civilProjectId?: string;
  civilProjectCode?: string;
  civilProjectTitle?: string;
  civilProjectZone?: string;

  // Step 2 - Civil Credit Provision
  civilCreditFormNumber?: string;
  civilBudgetRowCode?: string;
  civilBudgetRowTitle?: string;
  civilEstimatedAmount?: number;

  // Step 1 - Contractor & Contract Details
  contractorId?: number;
  contractorName?: string;
  contractNumberNew?: string;
  contractDate?: string;
  contractTotalAmount?: number;
  contractorGaamStatus?: GaamStatus;
  contractorGaamMessage?: string;
  contractorGaamMissingDocs?: string[];
  contractorGaamValidationPending?: boolean;

  // Step 3 - Contract & Guarantees (fetched from upstream)
  fetchedContractNumber?: string;
  fetchedContractDate?: string;
  fetchedGuaranteeNumber?: string;
  fetchedGuaranteeBank?: string;
  fetchedGuaranteeAmount?: number;
  fetchedGuaranteeExpiryDate?: string;
};


type TransactionWizardProps = {
  userId: number;
};

// Base steps - will be filtered dynamically
const BASE_STEPS = [
  { number: 0, title: 'انتخاب پروژه عمرانی', skippable: true },
  { number: 1, title: 'اطلاعات پیمانکار و قرارداد', skippable: false },
  { number: 2, title: 'تأمین اعتبار', skippable: false },
  { number: 3, title: 'قرارداد و تضامین', skippable: false },
  { number: 4, title: 'نوع تراکنش و سال مالی', skippable: true },
  { number: 5, title: 'انتخاب واحد سازمانی', skippable: true },
  { number: 6, title: 'رویداد مالی و مرکز هزینه', skippable: false },
  { number: 7, title: 'مستندات و پیوست‌ها', skippable: false },
  { number: 8, title: 'پیش‌نمایش کد یکتا', skippable: false },
  { number: 9, title: 'ثبت نهایی', skippable: false },
];

export function TransactionWizard({ userId }: TransactionWizardProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<TransactionFormData>({});
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isContextAware, setIsContextAware] = useState(false);

  // Budget validation hook - real-time check against available budget
  const budgetValidation = useBudgetValidation(
    formData.budgetItemId,
    formData.amount,
    formData.availableBudget
  );

  // Computed: Is budget exceeded? (used to disable Next button)
  const isBudgetExceeded = useMemo(() => {
    if (!formData.amount || !formData.availableBudget) return false;
    return formData.amount > formData.availableBudget;
  }, [formData.amount, formData.availableBudget]);


  // FIXED: Use atomic Zustand selectors to prevent infinite re-renders
  const selectedActivity = useTransactionStore((s) => s.selectedActivity);
  const dashboardData = useTransactionStore((s) => s.dashboardData);

  // Derive userContext from dashboardData (not a selector)
  const userContext = dashboardData?.user_context;

  // Smart initialization: auto-fill from store when activity is pre-selected.
  // Navigation remains linear and always starts from step 0.
  useEffect(() => {
    if (selectedActivity && userContext && !isContextAware) {
      console.log('Context-aware initialization:', { selectedActivity, userContext });

      // Determine budget type from constraints
      let autoTransactionType: 'expense' | 'capital' | undefined;
      if (selectedActivity.constraints?.allowed_budget_types?.length === 1) {
        autoTransactionType = selectedActivity.constraints.allowed_budget_types[0] as 'expense' | 'capital';
      }

      // Auto-fill form data from context
      const autoFillData: Partial<TransactionFormData> = {
        // From user context
        zoneId: userContext.zone_id ?? undefined,
        zoneName: userContext.zone_title ?? undefined,
        zoneCode: userContext.zone_code ?? undefined,
        sectionId: userContext.section_id ?? undefined,
        sectionName: userContext.section_title ?? undefined,
        sectionCode: userContext.section_code ?? undefined,

        // From selected activity
        subsystemActivityId: selectedActivity.id,
        subsystemActivityCode: selectedActivity.code,
        subsystemActivityTitle: selectedActivity.title,
        formType: selectedActivity.form_type ?? undefined,

        // From constraints (if single type allowed)
        transactionType: autoTransactionType,
        fiscalYear: '1403', // Current fiscal year
      };

      // Also set subsystem info if available
      if (dashboardData?.subsystem) {
        autoFillData.subsystemId = dashboardData.subsystem.id;
        autoFillData.subsystemCode = dashboardData.subsystem.code;
        autoFillData.subsystemTitle = dashboardData.subsystem.title;
        autoFillData.attachmentType = dashboardData.subsystem.attachment_type ?? undefined;
      }

      setFormData(prev => ({ ...prev, ...autoFillData }));
      setIsContextAware(true);
    }
  }, [selectedActivity, userContext, dashboardData, isContextAware]);

  // Get active constraint for budget filtering
  const budgetConstraints = useMemo((): ActivityConstraint | null => {
    if (selectedActivity?.constraints) {
      return selectedActivity.constraints;
    }
    return null;
  }, [selectedActivity]);

  const updateFormData = (data: Partial<TransactionFormData>) => {
    setFormData(prev => ({ ...prev, ...data }));
  };

  const nextStep = () => {
    setCurrentStep(prev => Math.min(prev + 1, BASE_STEPS.length - 1));
  };

  const prevStep = () => {
    setCurrentStep(prev => Math.max(prev - 1, 0));
  };

  const handleSubmit = async () => {
    // Stage 1 Gateway check: credit request is mandatory
    if (!formData.creditRequestId) {
      setSubmitError('انتخاب درخواست تامین اعتبار تایید شده الزامی است. لطفاً به مرحله ۹ بازگردید و درخواست را انتخاب کنید.');
      return;
    }

    // Build the payload for the API
    if (!formData.zoneId || !formData.budgetCode || !formData.beneficiaryName || !formData.amount) {
      setSubmitError('لطفاً تمام فیلدهای الزامی را تکمیل کنید');
      return;
    }

    // VALIDATION: Check if amount exceeds available budget
    if (formData.amount > (formData.availableBudget || 0)) {
      setSubmitError(
        `مبلغ وارد شده (${formatRial(formData.amount)}) بیشتر از مانده اعتبار ` +
        `(${formatRial(formData.availableBudget || 0)}) است. امکان ثبت وجود ندارد.`
      );
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      // STEP 1: Block budget funds FIRST (Zero-Trust Budget Control)
      // This ensures atomic budget reservation before transaction creation
      if (formData.budgetItemId && formData.amount) {
        console.log('Blocking budget funds...', {
          budgetRowId: formData.budgetItemId,
          amount: formData.amount
        });

        try {
          const blockResult = await blockBudgetFunds(
            formData.budgetItemId,
            formData.amount,
            `TXN-${Date.now()}`, // Temporary reference ID
            `Wizard submission for ${formData.beneficiaryName}`
          );
          console.log('Budget blocked successfully:', blockResult);
        } catch (blockError) {
          // Budget blocking failed - DO NOT proceed with transaction
          console.error('Budget blocking failed:', blockError);
          setSubmitError(blockError instanceof Error ? blockError.message : 'خطا در رزرو بودجه');
          setIsSubmitting(false);
          return; // CRITICAL: Stop submission
        }
      }

      // STEP 2: Create the transaction (only if blocking succeeded)
      const payload: TransactionCreateData = {
        credit_request_id: formData.creditRequestId,
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
        form_data: formData.formData,
      };

      const result = await createTransaction(payload);

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
    setCurrentStep(0);
    setFormData({});
    setIsSubmitted(false);
    setSubmitError(null);

    // Re-trigger context-aware initialization
    if (isContextAware) {
      setIsContextAware(false);
    }
  };

  const progress = ((currentStep + 1) / 10) * 100;
  const connectorProgress = BASE_STEPS.length > 1 ? currentStep / (BASE_STEPS.length - 1) : 0;

  // Validation: Step 1 (Contractor & Details) - all 4 fields required
  const isStep1Complete = Boolean(
    formData.contractorId &&
    formData.contractNumberNew?.trim() &&
    formData.contractDate?.trim() &&
    formData.contractTotalAmount && formData.contractTotalAmount > 0
  );

  const isStep1ValidationLocked = Boolean(
    formData.contractorGaamValidationPending ||
    formData.contractorGaamStatus === 'BLACKLISTED',
  );

  const isCivilCreditFetched = Boolean(formData.civilBudgetRowCode);
  const isContractFetched = Boolean(formData.fetchedContractNumber);

  const renderCurrentStep = () => {
    switch (currentStep) {
      case 0:
        // Civil flow entrypoint: activity selection is intentionally not rendered here.
        return (
          <WizardStep_CivilProjectSelect
            formData={formData}
            updateFormData={updateFormData}
            onNext={nextStep}
          />
        );
      case 1:
        return (
          <WizardStep_ContractorAndDetails
            formData={formData}
            updateFormData={updateFormData}
          />
        );
      case 2:
        return (
          <WizardStep3_CivilCredit
            formData={formData}
            updateFormData={updateFormData}
          />
        );
      case 3:
        return (
          <WizardStep4_ContractFetch
            formData={formData}
            updateFormData={updateFormData}
          />
        );
      case 4:
        return (
          <WizardStep1_TransactionType
            formData={formData}
            updateFormData={updateFormData}
          />
        );
      case 5:
        return (
          <WizardStep2_Organization
            formData={formData}
            updateFormData={updateFormData}
          />
        );
      case 6:
        return (
          <WizardStep4_FinancialEvent
            formData={formData}
            updateFormData={updateFormData}
          />
        );
      case 7:
        return (
          <WizardStep5_Attachments
            formData={formData}
            updateFormData={updateFormData}
          />
        );
      case 8:
        return (
          <WizardStep6_Preview
            formData={formData}
            updateFormData={updateFormData}
          />
        );
      case 9:
        return (
          <div className="space-y-6">
            {/* Stage 1 Gateway: CR selector */}
            <CreditRequestGateSelector
              zoneId={formData.zoneId}
              departmentId={formData.departmentId}
              sectionId={formData.sectionId}
              budgetCode={formData.budgetCode}
              selectedCRId={formData.creditRequestId}
              onSelect={(cr: CreditRequestListItem) => {
                updateFormData({
                  creditRequestId: cr.id,
                  creditRequestCode: cr.credit_request_code,
                  creditRequestAmount: cr.amount_approved ?? cr.amount_requested,
                });
              }}
              onCreateNew={() => {
                // Open credit request manager in a new tab/view
                // For now, show a helpful message
                window.open('/portal#credit-requests', '_blank');
              }}
            />
            {formData.creditRequestId && (
              <div className="bg-green-50 border border-green-200 p-3 rounded text-sm leading-tight text-green-700">
                Selected credit request: <strong>{formData.creditRequestCode}</strong>
                {' - '}Cap: <span className="font-mono-num">{formData.creditRequestAmount
                  ? formatRial(formData.creditRequestAmount)
                  : '-'}</span>
              </div>
            )}
            <hr className="border-border" />
            <WizardStep7_Submit formData={formData} onResetWizard={resetWizard} />
          </div>
        );
      default:
        return null;
    }
  };

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
          <div className="bg-amber-50 border border-amber-200 p-4 rounded text-sm leading-snug text-amber-900">
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
    <div className="w-full max-w-[1200px] mx-auto space-y-6">
      {/* Context-Aware Banner */}
      {isContextAware && (
        <div className="bg-primary/10 border border-primary/20 px-4 py-3 rounded-lg flex items-center gap-3">
          <Zap className="h-5 w-5 text-primary" />
          <div className="flex-1">
            <p className="text-sm leading-snug font-medium text-primary">حالت هوشمند فعال</p>
            <p className="text-xs leading-tight text-muted-foreground">
              اطلاعات سازمانی و نوع فعالیت از داشبورد دریافت شد • فعالیت: {selectedActivity?.title}
            </p>
          </div>
        </div>
      )}

      {/* Progress Header */}
      <Card className="p-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="leading-snug">مرحله {currentStep + 1} از ۱۰</h2>
              <p className="text-sm leading-tight text-muted-foreground">{BASE_STEPS[currentStep].title}</p>
            </div>
            <div className="text-left text-sm leading-tight text-muted-foreground">
              {Math.round(progress)}% تکمیل شده
            </div>
          </div>
          <Progress value={progress} className="h-2" />
        </div>
      </Card>

      {/* Step Indicator */}
      <div className="relative w-full">
        <div className="absolute left-4 right-4 top-4 h-0.5 bg-border" />
        <div
          className="absolute left-4 top-4 h-0.5 bg-green-600 transition-all duration-300"
          style={{ width: `calc((100% - 2rem) * ${connectorProgress})` }}
        />
        <div className="relative flex w-full justify-between">
          {BASE_STEPS.map((step) => (
            <div key={step.number} className="flex min-w-0 flex-1 flex-col items-center gap-2">
              <div
                className={`relative z-10 h-8 w-8 rounded-full flex items-center justify-center text-sm leading-none transition-colors ${step.number === currentStep
                  ? 'bg-primary text-primary-foreground'
                  : step.number < currentStep
                    ? 'bg-green-600 text-white'
                    : 'bg-muted text-muted-foreground'
                  }`}
                title={step.title}
              >
                {step.number < currentStep ? <CheckCircle2 className="h-4 w-4" /> : step.number}
              </div>
              <p className={`hidden w-24 max-w-[96px] min-h-[2.25rem] text-center text-xs leading-tight whitespace-normal break-words md:block ${step.number === currentStep ? 'text-foreground' : 'text-muted-foreground'
                }`}>
                {step.title}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Current Step Content */}
      <Card className="p-6">
        {renderCurrentStep()}
      </Card>

      {/* Navigation */}
      <Card className="p-4">
        {submitError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded mb-4 text-sm leading-tight flex items-center">
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

          {currentStep < 9 ? (
            <Button
              onClick={nextStep}
              size="lg"
              disabled={
                (currentStep === 1 && (!isStep1Complete || isStep1ValidationLocked)) ||
                (currentStep === 2 && !isCivilCreditFetched) ||
                (currentStep === 3 && !isContractFetched) ||
                (currentStep >= 7 && isBudgetExceeded)
              }
            >
              {currentStep === 2 && !isCivilCreditFetched ? (
                <span className="text-muted-foreground">ابتدا استعلام تأمین اعتبار انجام دهید</span>
              ) : currentStep === 3 && !isContractFetched ? (
                <span className="text-muted-foreground">ابتدا استعلام قرارداد و تضامین انجام دهید</span>
              ) : currentStep === 1 && formData.contractorGaamValidationPending ? (
                <>
                  <Loader2 className="h-4 w-4 ml-2 animate-spin" />
                  در حال استعلام صلاحیت
                </>
              ) : currentStep === 1 && formData.contractorGaamStatus === 'BLACKLISTED' ? (
                <span className="text-red-600">پیمانکار غیرمجاز</span>
              ) : currentStep === 1 && !isStep1Complete ? (
                <span className="text-muted-foreground">تکمیل اطلاعات الزامی</span>
              ) : isBudgetExceeded && currentStep >= 7 ? (
                <>
                  <AlertTriangle className="h-4 w-4 ml-2 text-amber-500" />
                  بودجه ناکافی
                </>
              ) : (
                <>
                  مرحله بعد
                  <ChevronLeft className="h-4 w-4 mr-2" />
                </>
              )}
            </Button>
          ) : (
            <div className="px-3 text-sm text-muted-foreground">
              Final submission is handled inside Step 7.
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}

