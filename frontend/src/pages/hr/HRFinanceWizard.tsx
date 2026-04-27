import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleDashed,
  Copy,
  FileStack,
  Loader2,
  MapPinned,
  ReceiptText,
  ShieldCheck,
  Split,
  Sparkles,
} from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '../../components/ui/accordion';
import { Badge } from '../../components/ui/badge';
import { Checkbox } from '../../components/ui/checkbox';
import { Button } from '../../components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table';
import { cn } from '../../components/ui/utils';
import { formatNumber, formatRial } from '../../lib/utils';
import {
  AllocationLine,
  fetchHRFinanceWorkflowContext,
  GeneratedHRTransactionCode,
  HRFinanceWorkflowContext,
  submitHRTransaction,
} from '../../services/hrFinance';
import { toast } from 'sonner';

type StepId = 1 | 2 | 3 | 4 | 5;

type EditableAllocationField =
  | 'orgUnitLabel'
  | 'costCenterCode'
  | 'budgetLineCode'
  | 'financialEventType'
  | 'allocatedAmount'
  | 'legalDeductions'
  | 'penalties';

const WIZARD_STEPS: Array<{ id: StepId; title: string; subtitle: string }> = [
  { id: 1, title: 'اطلاعات پایه قرارداد', subtitle: 'Base Info' },
  { id: 2, title: 'تفکیک مناطق و ردیف بودجه', subtitle: 'Regional Allocation' },
  { id: 3, title: 'اعمال کسورات', subtitle: 'Deductions' },
  { id: 4, title: 'پیش‌نمایش و تایید', subtitle: 'Preview' },
  { id: 5, title: 'صدور کدهای یکتا', subtitle: 'Generate Codes' },
];

const REGION_LABELS = [
  'منطقه ۱ - معاونت خدمات شهری',
  'منطقه ۳ - خدمات پشتیبانی',
  'منطقه ۷ - حوزه حفاظت فیزیکی',
];

const DIGIT_MAP: Record<string, string> = {
  '۰': '0',
  '۱': '1',
  '۲': '2',
  '۳': '3',
  '۴': '4',
  '۵': '5',
  '۶': '6',
  '۷': '7',
  '۸': '8',
  '۹': '9',
  '٠': '0',
  '١': '1',
  '٢': '2',
  '٣': '3',
  '٤': '4',
  '٥': '5',
  '٦': '6',
  '٧': '7',
  '٨': '8',
  '٩': '9',
};

function normalizeDigits(value: string) {
  return value
    .split('')
    .map((char) => DIGIT_MAP[char] ?? char)
    .join('');
}

function parseAmountInput(value: string) {
  const normalized = normalizeDigits(value).replace(/[^\d-]/g, '');
  if (!normalized) {
    return 0;
  }

  const parsed = Number.parseInt(normalized, 10);
  return Number.isFinite(parsed) ? Math.max(parsed, 0) : 0;
}

function createAllocationLine(
  line: Omit<AllocationLine, 'netAmount'> & { netAmount?: number },
): AllocationLine {
  return {
    ...line,
    legalDeductions: Math.max(line.legalDeductions, 0),
    penalties: Math.max(line.penalties, 0),
    allocatedAmount: Math.max(line.allocatedAmount, 0),
    netAmount: Math.max(line.allocatedAmount, 0) - Math.max(line.legalDeductions, 0) - Math.max(line.penalties, 0),
  };
}

function getTotalDeductions(line: AllocationLine) {
  return line.legalDeductions + line.penalties;
}

function buildMockContext(transactionId: number): HRFinanceWorkflowContext {
  return {
    transaction: {
      id: transactionId,
      status: 'DRAFT',
      gross_amount: 875000000,
      activity_id: 2,
      activity_name: 'تسویه کارکرد پیمانکاران',
      contract_number: `ATT-1405-${String(transactionId).padStart(4, '0')}`,
    },
    operational_context: {
      work_period_id: 9,
      name: 'کارکرد 1405/01',
      year: 1405,
      month: 1,
      date_range: {
        start: '1405/01/01',
        end: '1405/01/31',
      },
      contractor_name: 'شرکت نمونه پیمانکاری',
      contract_number: `ATT-1405-${String(transactionId).padStart(4, '0')}`,
    },
    financial_rules: {
      cost_center_code: 'CC-102',
      budget_line_code: 'BL-2020-8',
      financial_event_type: 'CONTRACTOR_PAYROLL',
    },
  };
}

function buildSuggestedAllocations(context: HRFinanceWorkflowContext): AllocationLine[] {
  const grossAmount = context.transaction.gross_amount ?? 0;
  const providedLines = context.allocation_lines ?? [];

  if (providedLines.length > 0) {
    return providedLines.map((line, index) =>
      createAllocationLine({
        id: String(line.id ?? `api-${index + 1}`),
        orgUnitLabel: line.org_unit_name,
        costCenterCode: line.cost_center_code,
        budgetLineCode: line.budget_line_code,
        financialEventType: line.financial_event_type,
        allocatedAmount: line.allocated_amount,
        legalDeductions: line.legal_deductions ?? 0,
        penalties: line.penalties ?? 0,
      }),
    );
  }

  const shares = [0.45, 0.35, 0.2];
  let remainingAmount = grossAmount;

  return REGION_LABELS.map((label, index) => {
    const suggestedAmount =
      index === REGION_LABELS.length - 1
        ? remainingAmount
        : Math.floor(grossAmount * shares[index]);

    remainingAmount -= suggestedAmount;

    return createAllocationLine({
      id: `mock-${index + 1}`,
      orgUnitLabel: label,
      costCenterCode: context.financial_rules.cost_center_code,
      budgetLineCode: context.financial_rules.budget_line_code,
      financialEventType: context.financial_rules.financial_event_type,
      allocatedAmount: suggestedAmount,
      legalDeductions: 0,
      penalties: 0,
    });
  });
}

function buildGeneratedCodesFromContext(
  context: HRFinanceWorkflowContext,
): GeneratedHRTransactionCode[] {
  return (context.allocation_lines ?? []).flatMap((line) =>
    line.unique_code
      ? [
          {
            region: line.org_unit_name,
            code: line.unique_code,
          },
        ]
      : [],
  );
}

function StepperCard({
  step,
  isActive,
  isComplete,
  isLocked,
  onClick,
}: {
  step: { id: StepId; title: string; subtitle: string };
  isActive: boolean;
  isComplete: boolean;
  isLocked: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={isLocked}
      onClick={onClick}
      className={cn(
        'group relative flex min-h-[110px] flex-col justify-between overflow-hidden rounded-3xl border px-4 py-4 text-right transition-all duration-200',
        isActive
          ? 'border-[#008099] bg-[#008099] text-white shadow-lg shadow-[#008099]/15'
          : 'border-slate-200 bg-white/85 text-slate-700 hover:border-[#008099]/40 hover:bg-white',
        isLocked && 'cursor-not-allowed opacity-45 hover:border-slate-200 hover:bg-white/85',
      )}
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.18),transparent_52%)]" />
      <div className="relative flex items-center justify-between gap-3">
        <Badge
          variant="outline"
          className={cn(
            'rounded-full border px-2 py-1 text-[10px]',
            isActive
              ? 'border-white/30 bg-white/10 text-white'
              : 'border-slate-200 bg-slate-50 text-slate-500',
          )}
        >
          {step.subtitle}
        </Badge>
        <div
          className={cn(
            'flex h-10 w-10 items-center justify-center rounded-2xl text-sm font-black',
            isActive
              ? 'bg-white/15 text-white'
              : isComplete
                ? 'bg-emerald-50 text-emerald-600'
                : 'bg-slate-100 text-slate-500',
          )}
        >
          {isComplete ? <CheckCircle2 className="h-5 w-5" /> : step.id}
        </div>
      </div>
      <div className="relative space-y-2">
        <div className={cn('text-sm font-black leading-6', isActive ? 'text-white' : 'text-slate-900')}>
          {step.title}
        </div>
        <div className={cn('text-xs leading-5', isActive ? 'text-white/80' : 'text-slate-500')}>
          {step.id === 2
            ? 'هر ردیف مبنای یک کد یکتای مستقل خواهد بود.'
            : 'جریان مرحله‌های پرونده منابع انسانی و امور مالی.'}
        </div>
      </div>
    </button>
  );
}

function SummaryCard({
  title,
  value,
  caption,
  icon: Icon,
}: {
  title: string;
  value: string;
  caption: string;
  icon: React.ElementType;
}) {
  return (
    <Card className="overflow-hidden border-slate-200/80 bg-white/90 shadow-sm">
      <CardContent className="relative p-5">
        <div className="absolute -left-6 -top-6 h-20 w-20 rounded-full bg-[#008099]/8 blur-2xl" />
        <div className="relative flex items-start justify-between gap-4">
          <div className="space-y-2 text-right">
            <div className="text-xs font-bold tracking-wide text-slate-500">{title}</div>
            <div className="text-lg font-black leading-8 text-slate-900">{value}</div>
            <div className="text-xs leading-5 text-slate-500">{caption}</div>
          </div>
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#008099]/10 text-[#008099]">
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function PlaceholderStep({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <Card className="border-dashed border-slate-300 bg-white/80">
      <CardContent className="flex min-h-[260px] flex-col items-center justify-center gap-4 p-10 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">
          <CircleDashed className="h-6 w-6" />
        </div>
        <div className="space-y-2">
          <div className="text-lg font-black text-slate-900">{title}</div>
          <div className="max-w-xl text-sm leading-7 text-slate-500">{description}</div>
        </div>
        <Badge variant="outline" className="border-slate-200 bg-slate-50 text-slate-600">
          Step Shell Ready
        </Badge>
      </CardContent>
    </Card>
  );
}

export default function HRFinanceWizard() {
  const params = useParams<{ transactionId: string }>();
  const transactionId = Number.parseInt(params.transactionId ?? '0', 10) || 0;
  const navigate = useNavigate();

  const [currentStep, setCurrentStep] = useState<StepId>(1);
  const [workflowContext, setWorkflowContext] = useState<HRFinanceWorkflowContext | null>(null);
  const [allocationLines, setAllocationLines] = useState<AllocationLine[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [contextMode, setContextMode] = useState<'api' | 'fallback'>('api');
  const [isPreviewConfirmed, setIsPreviewConfirmed] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [generatedCodes, setGeneratedCodes] = useState<GeneratedHRTransactionCode[]>([]);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadWorkflowContext() {
      if (!transactionId) {
        const fallbackContext = buildMockContext(101);
        setCurrentStep(1);
        setWorkflowContext(fallbackContext);
        setAllocationLines(buildSuggestedAllocations(fallbackContext));
        setGeneratedCodes([]);
        setContextMode('fallback');
        setIsLoading(false);
        setError('شناسه تراکنش نامعتبر بود؛ صفحه با داده نمایشی بارگذاری شد.');
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const response = await fetchHRFinanceWorkflowContext(transactionId);
        if (!isMounted) {
          return;
        }

        setWorkflowContext(response);
        setAllocationLines(buildSuggestedAllocations(response));
        const persistedCodes = buildGeneratedCodesFromContext(response);
        setGeneratedCodes(persistedCodes);
        setCurrentStep(persistedCodes.length > 0 ? 5 : 1);
        setContextMode('api');
      } catch (fetchError) {
        if (!isMounted) {
          return;
        }

        const fallbackContext = buildMockContext(transactionId);
        setCurrentStep(1);
        setWorkflowContext(fallbackContext);
        setAllocationLines(buildSuggestedAllocations(fallbackContext));
        setGeneratedCodes([]);
        setContextMode('fallback');
        setError(
          fetchError instanceof Error
            ? `${fetchError.message}؛ برای ادامه طراحی رابط، داده نمایشی بارگذاری شد.`
            : 'دریافت اطلاعات زمینه ناموفق بود و داده نمایشی جایگزین شد.',
        );
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadWorkflowContext();

    return () => {
      isMounted = false;
    };
  }, [transactionId]);

  useEffect(() => {
    setIsPreviewConfirmed(false);
    setSubmitError(null);
    setCopiedCode(null);
  }, [allocationLines]);

  const grossAmount = workflowContext?.transaction.gross_amount ?? 0;
  const allocatedTotal = allocationLines.reduce((sum, line) => sum + line.allocatedAmount, 0);
  const allocationDelta = grossAmount - allocatedTotal;
  const isAllocationBalanced = grossAmount > 0 && allocationDelta === 0;
  const totalLegalDeductions = allocationLines.reduce((sum, line) => sum + line.legalDeductions, 0);
  const totalPenalties = allocationLines.reduce((sum, line) => sum + line.penalties, 0);
  const totalDeductions = totalLegalDeductions + totalPenalties;
  const totalNetPayable = allocationLines.reduce((sum, line) => sum + line.netAmount, 0);
  const hasNegativeNetAmount = allocationLines.some((line) => line.netAmount < 0);
  const isPreviewReady = isAllocationBalanced && !hasNegativeNetAmount;
  const activeStepMeta = WIZARD_STEPS.find((step) => step.id === currentStep) ?? WIZARD_STEPS[0];
  const contractNumber =
    workflowContext?.transaction.contract_number ||
    workflowContext?.operational_context.contract_number ||
    `ATT-${String(transactionId || 101).padStart(4, '0')}`;
  const usingMockAllocation = !workflowContext?.allocation_lines?.length;

  function updateAllocationLine(
    lineId: string,
    key: EditableAllocationField,
    value: string | number,
  ) {
    setAllocationLines((currentLines) =>
      currentLines.map((line) =>
        line.id === lineId
          ? createAllocationLine({
              ...line,
              [key]: value,
            })
          : line,
      ),
    );
  }

  function addAllocationLine() {
    const nextIndex = allocationLines.length + 1;
    setAllocationLines((currentLines) => [
      ...currentLines,
      createAllocationLine({
        id: `manual-${Date.now()}`,
        orgUnitLabel: `واحد سازمانی ${formatNumber(nextIndex)}`,
        costCenterCode: workflowContext?.financial_rules.cost_center_code ?? '',
        budgetLineCode: workflowContext?.financial_rules.budget_line_code ?? '',
        financialEventType: workflowContext?.financial_rules.financial_event_type ?? '',
        allocatedAmount: 0,
        legalDeductions: 0,
        penalties: 0,
      }),
    ]);
  }

  function removeAllocationLine(lineId: string) {
    setAllocationLines((currentLines) => currentLines.filter((line) => line.id !== lineId));
  }

  function resetSuggestedAllocation() {
    if (!workflowContext) {
      return;
    }
    setAllocationLines(buildSuggestedAllocations(workflowContext));
  }

  async function handleCopyCode(code: string) {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedCode(code);
      toast.success('کد یکتا در کلیپ‌بورد کپی شد.');
      window.setTimeout(() => {
        setCopiedCode((currentCode) => (currentCode === code ? null : currentCode));
      }, 1800);
    } catch {
      const message = 'کپی کد یکتا ناموفق بود. لطفاً به‌صورت دستی کد را انتخاب کنید.';
      setSubmitError(message);
      toast.error(message);
    }
  }

  async function handleSubmitTransaction() {
    if (!workflowContext || !isPreviewConfirmed || isSubmitting || !isPreviewReady) {
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const submissionPayload: AllocationLine[] = allocationLines.map((line) => ({ ...line }));
      const result = await submitHRTransaction(
        String(workflowContext.transaction.id || transactionId || 101),
        submissionPayload,
      );

      setGeneratedCodes(result);
      setWorkflowContext((currentContext) =>
        currentContext
          ? {
              ...currentContext,
              transaction: {
                ...currentContext.transaction,
                status: 'SENT_TO_FINANCE',
              },
              allocation_lines: submissionPayload.map((line, index) => ({
                id: index + 1,
                org_unit_name: line.orgUnitLabel,
                cost_center_code: line.costCenterCode,
                budget_line_code: line.budgetLineCode,
                financial_event_type: line.financialEventType,
                allocated_amount: line.allocatedAmount,
                legal_deductions: line.legalDeductions,
                penalties: line.penalties,
                net_amount: line.netAmount,
                unique_code: result[index]?.code ?? null,
              })),
            }
          : currentContext,
      );
      toast.success('کدهای یکتای مالی با موفقیت صادر و ذخیره شدند.');
      setCurrentStep(5);
    } catch (submissionError) {
      const message =
        submissionError instanceof Error
          ? submissionError.message
          : 'صدور کدهای یکتا ناموفق بود. لطفاً مجدداً تلاش کنید.';
      setSubmitError(message);
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  function goToNextStep() {
    setCurrentStep((current) => {
      if (current >= 5) {
        return current;
      }
      return (current + 1) as StepId;
    });
  }

  function goToPreviousStep() {
    setCurrentStep((current) => {
      if (current <= 1) {
        return current;
      }
      return (current - 1) as StepId;
    });
  }

  function canAccessStep(stepId: StepId) {
    if (!workflowContext) {
      return false;
    }
    if (stepId <= 2) {
      return true;
    }
    if (stepId === 3) {
      return isAllocationBalanced;
    }
    if (stepId === 4) {
      return isPreviewReady;
    }
    return generatedCodes.length > 0;
  }

  function renderStepContent() {
    if (isLoading) {
      return (
        <Card className="border-slate-200 bg-white/90">
          <CardContent className="flex min-h-[340px] items-center justify-center gap-3 p-10 text-slate-500">
            <Loader2 className="h-5 w-5 animate-spin" />
            در حال آماده‌سازی اطلاعات پرونده مالی...
          </CardContent>
        </Card>
      );
    }

    if (!workflowContext) {
      return (
        <Alert variant="destructive" className="border-red-200 bg-red-50 text-right">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>اطلاعات پرونده در دسترس نیست</AlertTitle>
          <AlertDescription>بدون داده زمینه‌ای، ویزارد قابل نمایش نیست.</AlertDescription>
        </Alert>
      );
    }

    if (currentStep === 1) {
      return (
        <div className="space-y-6">
          <Card className="border-slate-200 bg-white/90 shadow-sm">
            <CardHeader className="border-b border-slate-100 text-right">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="space-y-2">
                  <CardTitle className="text-2xl font-black text-slate-900">
                    اطلاعات پایه قرارداد
                  </CardTitle>
                  <CardDescription className="text-sm leading-7 text-slate-500">
                    این بخش ورودی دستی ندارد و از زمینه عملیاتی و مالی پرونده پر می‌شود.
                  </CardDescription>
                </div>
                <Badge className="bg-[#008099] text-white shadow-sm">Read Only</Badge>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 p-6 md:grid-cols-2 xl:grid-cols-4">
              <SummaryCard
                title="فعالیت"
                value={workflowContext.transaction.activity_name || 'نامشخص'}
                caption="فعالیت مالی مبنای صدور کدهای منطقه‌ای"
                icon={Sparkles}
              />
              <SummaryCard
                title="پیمانکار و شماره قرارداد"
                value={`${workflowContext.operational_context.contractor_name || 'پیمانکار نامشخص'} / ${contractNumber}`}
                caption="ترکیب ذی‌نفع و شماره قرارداد برای کنترل نهایی"
                icon={FileStack}
              />
              <SummaryCard
                title="تاریخ / دوره کارکرد"
                value={workflowContext.operational_context.name}
                caption={`${workflowContext.operational_context.date_range.start} تا ${workflowContext.operational_context.date_range.end}`}
                icon={ReceiptText}
              />
              <SummaryCard
                title="مبلغ کل ناخالص"
                value={formatRial(grossAmount)}
                caption="مبنای کنترل مجموع ردیف‌های تخصیص در مرحله بعد"
                icon={ShieldCheck}
              />
            </CardContent>
          </Card>
        </div>
      );
    }

    if (currentStep === 2) {
      return (
        <div className="space-y-6">
          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="border-slate-200 bg-white/90 shadow-sm">
              <CardContent className="p-5 text-right">
                <div className="text-xs font-bold text-slate-500">مبلغ کل ناخالص</div>
                <div className="mt-2 text-2xl font-black text-slate-900">{formatRial(grossAmount)}</div>
                <div className="mt-2 text-xs text-slate-500">هدف کنترل تمام ردیف‌های منطقه‌ای</div>
              </CardContent>
            </Card>
            <Card className="border-slate-200 bg-white/90 shadow-sm">
              <CardContent className="p-5 text-right">
                <div className="text-xs font-bold text-slate-500">جمع تخصیص فعلی</div>
                <div className="mt-2 text-2xl font-black text-slate-900">{formatRial(allocatedTotal)}</div>
                <div className="mt-2 text-xs text-slate-500">
                  {allocationLines.length} ردیف تخصیص آماده صدور کد
                </div>
              </CardContent>
            </Card>
            <Card className="border-slate-200 bg-white/90 shadow-sm">
              <CardContent className="p-5 text-right">
                <div className="text-xs font-bold text-slate-500">وضعیت تراز</div>
                <div className="mt-2 flex items-center justify-between gap-3">
                  <Badge
                    className={cn(
                      'rounded-full px-3 py-1 text-xs font-bold',
                      isAllocationBalanced
                        ? 'bg-emerald-100 text-emerald-700'
                        : 'bg-rose-100 text-rose-700',
                    )}
                  >
                    {isAllocationBalanced ? 'مغایرت ندارد' : 'نیازمند اصلاح'}
                  </Badge>
                  <div className="text-lg font-black text-slate-900">{formatRial(Math.abs(allocationDelta))}</div>
                </div>
                <div className="mt-2 text-xs text-slate-500">
                  {allocationDelta > 0
                    ? 'مانده مبلغی که هنوز به مناطق تخصیص داده نشده'
                    : allocationDelta < 0
                      ? 'مازاد ثبت‌شده نسبت به مبلغ ناخالص'
                      : 'جمع ردیف‌ها دقیقاً با مبلغ ناخالص برابر است'}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="border-slate-200 bg-white/90 shadow-sm">
            <CardHeader className="border-b border-slate-100 text-right">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="space-y-2">
                  <CardTitle className="text-2xl font-black text-slate-900">
                    تفکیک مناطق و ردیف بودجه
                  </CardTitle>
                  <CardDescription className="text-sm leading-7 text-slate-500">
                    هر ردیف این جدول یک واحد سازمانی مستقل است و در Step 5 به یک کد یکتای مجزا تبدیل می‌شود.
                  </CardDescription>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {usingMockAllocation ? (
                    <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-700">
                      داده پیشنهادی برای نمایش اولیه
                    </Badge>
                  ) : null}
                  <Badge variant="outline" className="border-slate-200 bg-slate-50 text-slate-600">
                    State: AllocationLine[]
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-5 p-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    type="button"
                    size="sm"
                    className="bg-[#008099] text-white hover:bg-[#006b80]"
                    onClick={addAllocationLine}
                  >
                    <Split className="h-4 w-4" />
                    افزودن ردیف تخصیص
                  </Button>
                  <Button type="button" size="sm" variant="outline" onClick={resetSuggestedAllocation}>
                    بازنشانی الگوی پیشنهادی
                  </Button>
                </div>
                <div className="text-sm text-slate-500">
                  مجموع تخصیص باید دقیقاً با <span className="font-black text-slate-900">{formatRial(grossAmount)}</span> برابر باشد.
                </div>
              </div>

              <div className="overflow-hidden rounded-3xl border border-slate-200">
                <Table>
                  <TableHeader className="bg-slate-50/80">
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="px-4 text-right font-black text-slate-600">واحد سازمانی</TableHead>
                      <TableHead className="px-4 text-right font-black text-slate-600">مرکز هزینه</TableHead>
                      <TableHead className="px-4 text-right font-black text-slate-600">ردیف بودجه (سطح ۵)</TableHead>
                      <TableHead className="px-4 text-right font-black text-slate-600">رویداد مالی</TableHead>
                      <TableHead className="px-4 text-right font-black text-slate-600">مبلغ کارکرد منطقه</TableHead>
                      <TableHead className="w-[90px] px-4 text-right font-black text-slate-600">عملیات</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {allocationLines.map((line, index) => (
                      <TableRow key={line.id} className="bg-white/80">
                        <TableCell className="px-4 py-3 align-top">
                          <div className="space-y-2 text-right">
                            <Badge variant="outline" className="border-slate-200 bg-slate-50 text-slate-600">
                              ردیف {formatNumber(index + 1)}
                            </Badge>
                            <Input
                              value={line.orgUnitLabel}
                              onChange={(event) => updateAllocationLine(line.id, 'orgUnitLabel', event.target.value)}
                              className="h-11 border-slate-200 text-right"
                            />
                          </div>
                        </TableCell>
                        <TableCell className="px-4 py-3 align-top">
                          <Input
                            value={line.costCenterCode}
                            onChange={(event) => updateAllocationLine(line.id, 'costCenterCode', event.target.value)}
                            className="h-11 border-slate-200 text-right font-mono"
                            dir="ltr"
                          />
                        </TableCell>
                        <TableCell className="px-4 py-3 align-top">
                          <Input
                            value={line.budgetLineCode}
                            onChange={(event) => updateAllocationLine(line.id, 'budgetLineCode', event.target.value)}
                            className="h-11 border-slate-200 text-right font-mono"
                            dir="ltr"
                          />
                        </TableCell>
                        <TableCell className="px-4 py-3 align-top">
                          <Input
                            value={line.financialEventType}
                            onChange={(event) => updateAllocationLine(line.id, 'financialEventType', event.target.value)}
                            className="h-11 border-slate-200 text-right font-mono"
                            dir="ltr"
                          />
                        </TableCell>
                        <TableCell className="px-4 py-3 align-top">
                          <div className="space-y-2">
                            <Input
                              value={line.allocatedAmount === 0 ? '' : String(line.allocatedAmount)}
                              onChange={(event) =>
                                updateAllocationLine(
                                  line.id,
                                  'allocatedAmount',
                                  parseAmountInput(event.target.value),
                                )
                              }
                              className="h-11 border-slate-200 text-left font-mono"
                              inputMode="numeric"
                              dir="ltr"
                              placeholder="0"
                            />
                            <div className="text-right text-xs text-slate-500">
                              {formatRial(line.allocatedAmount)}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="px-4 py-3 align-top">
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            className="text-rose-600 hover:bg-rose-50 hover:text-rose-700"
                            onClick={() => removeAllocationLine(line.id)}
                            disabled={allocationLines.length === 1}
                          >
                            حذف
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                  <TableFooter className="bg-slate-50/80">
                    <TableRow className="hover:bg-transparent">
                      <TableCell colSpan={4} className="px-4 py-4 text-right">
                        <div className="space-y-1">
                          <div className="text-sm font-black text-slate-900">جمع کل تخصیص منطقه‌ای</div>
                          <div className="text-xs text-slate-500">
                            شرط عبور به مرحله بعد: برابر بودن جمع ردیف‌ها با مبلغ کل ناخالص
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="px-4 py-4 text-right">
                        <div className="space-y-2">
                          <div className="font-mono text-lg font-black text-slate-900" dir="ltr">
                            {formatRial(allocatedTotal)}
                          </div>
                          <Badge
                            className={cn(
                              'rounded-full px-3 py-1 text-xs font-bold',
                              isAllocationBalanced
                                ? 'bg-emerald-100 text-emerald-700'
                                : 'bg-rose-100 text-rose-700',
                            )}
                          >
                            {isAllocationBalanced
                              ? 'تراز کامل'
                              : `اختلاف ${formatRial(Math.abs(allocationDelta))}`}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell className="px-4 py-4 text-right text-xs text-slate-500">
                        {isAllocationBalanced ? 'آماده ادامه' : 'نیازمند بازبینی'}
                      </TableCell>
                    </TableRow>
                  </TableFooter>
                </Table>
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }

    if (currentStep === 3) {
      return (
        <div className="space-y-6">
          <Card className="border-slate-200 bg-white/90 shadow-sm">
            <CardHeader className="border-b border-slate-100 text-right">
              <CardTitle className="text-2xl font-black text-slate-900">
                اعمال کسورات و جریمه‌ها
              </CardTitle>
              <CardDescription className="text-sm leading-7 text-slate-500">
                کسورات برای هر منطقه به‌صورت مستقل ثبت می‌شود تا مبلغ خالص پرداختی هر واحد سازمانی پیش از پیش‌نمایش نهایی مشخص باشد.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 p-6 md:grid-cols-3">
              <Card className="border-slate-200 bg-slate-50/80 shadow-none">
                <CardContent className="p-5 text-right">
                  <div className="text-xs font-bold text-slate-500">کل ناخالص</div>
                  <div className="mt-2 text-2xl font-black text-slate-900">{formatRial(allocatedTotal)}</div>
                  <div className="mt-2 text-xs text-slate-500">مجموع کارکرد تخصیص‌یافته بین مناطق</div>
                </CardContent>
              </Card>
              <Card className="border-slate-200 bg-slate-50/80 shadow-none">
                <CardContent className="p-5 text-right">
                  <div className="text-xs font-bold text-slate-500">کل کسورات</div>
                  <div className="mt-2 text-2xl font-black text-slate-900">{formatRial(totalDeductions)}</div>
                  <div className="mt-2 text-xs text-slate-500">
                    قانونی: {formatRial(totalLegalDeductions)} | جرایم: {formatRial(totalPenalties)}
                  </div>
                </CardContent>
              </Card>
              <Card className="border-slate-200 bg-slate-50/80 shadow-none">
                <CardContent className="p-5 text-right">
                  <div className="text-xs font-bold text-slate-500">وضعیت کنترل</div>
                  <div className="mt-2 flex items-center justify-between gap-3">
                    <Badge
                      className={cn(
                        'rounded-full px-3 py-1 text-xs font-bold',
                        hasNegativeNetAmount
                          ? 'bg-rose-100 text-rose-700'
                          : 'bg-emerald-100 text-emerald-700',
                      )}
                    >
                      {hasNegativeNetAmount ? 'نیازمند اصلاح' : 'آماده پیش‌نمایش'}
                    </Badge>
                    <div
                      className={cn(
                        'text-lg font-black',
                        hasNegativeNetAmount ? 'text-rose-600' : 'text-emerald-700',
                      )}
                    >
                      {formatRial(totalNetPayable)}
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-slate-500">
                    تا زمانی که خالص هیچ‌یک از مناطق منفی نشود، مرحله بعد باز می‌شود.
                  </div>
                </CardContent>
              </Card>
            </CardContent>
          </Card>

          <Accordion
            type="multiple"
            className="space-y-4"
            defaultValue={allocationLines.map((line) => line.id)}
          >
            {allocationLines.map((line, index) => {
              const totalLineDeductions = getTotalDeductions(line);
              const isLineInvalid = totalLineDeductions > line.allocatedAmount;

              return (
                <AccordionItem
                  key={line.id}
                  value={line.id}
                  className="overflow-hidden rounded-3xl border border-slate-200 bg-white/90 shadow-sm"
                >
                  <AccordionTrigger className="px-6 py-5 text-right hover:no-underline">
                    <div className="flex flex-1 flex-wrap items-center justify-between gap-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge
                          className={cn(
                            'rounded-full px-3 py-1 text-xs font-bold',
                            isLineInvalid
                              ? 'bg-rose-100 text-rose-700'
                              : 'bg-slate-100 text-slate-700',
                          )}
                        >
                          {isLineInvalid ? 'کسورات بیش از حد مجاز' : `ردیف ${formatNumber(index + 1)}`}
                        </Badge>
                        <Badge variant="outline" className="border-slate-200 bg-slate-50 text-slate-600">
                          ناخالص منطقه: {formatRial(line.allocatedAmount)}
                        </Badge>
                      </div>
                      <div className="space-y-1 text-right">
                        <div className="text-lg font-black text-slate-900">{line.orgUnitLabel}</div>
                        <div className="text-xs text-slate-500">
                          مرکز هزینه {line.costCenterCode} | ردیف {line.budgetLineCode}
                        </div>
                      </div>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-6 pb-6">
                    <div className="grid gap-4 xl:grid-cols-[1fr_1fr_0.9fr]">
                      <Card className="border-slate-200 bg-slate-50/70 shadow-none">
                        <CardContent className="space-y-2 p-5">
                          <div className="text-right">
                            <div className="text-sm font-black text-slate-900">کسورات قانونی (ریال)</div>
                            <div className="mt-1 text-xs text-slate-500">
                              بیمه، مالیات و سپرده حسن انجام کار
                            </div>
                          </div>
                          <Input
                            value={line.legalDeductions === 0 ? '' : String(line.legalDeductions)}
                            onChange={(event) =>
                              updateAllocationLine(
                                line.id,
                                'legalDeductions',
                                parseAmountInput(event.target.value),
                              )
                            }
                            className="h-12 border-slate-200 text-left font-mono"
                            inputMode="numeric"
                            dir="ltr"
                            placeholder="0"
                          />
                          <div className="text-right text-xs text-slate-500">
                            ثبت‌شده: {formatRial(line.legalDeductions)}
                          </div>
                        </CardContent>
                      </Card>

                      <Card className="border-slate-200 bg-slate-50/70 shadow-none">
                        <CardContent className="space-y-2 p-5">
                          <div className="text-right">
                            <div className="text-sm font-black text-slate-900">جرایم عملیاتی (ریال)</div>
                            <div className="mt-1 text-xs text-slate-500">
                              غیبت، تاخیر یا کسورات عملکردی منطقه
                            </div>
                          </div>
                          <Input
                            value={line.penalties === 0 ? '' : String(line.penalties)}
                            onChange={(event) =>
                              updateAllocationLine(
                                line.id,
                                'penalties',
                                parseAmountInput(event.target.value),
                              )
                            }
                            className="h-12 border-slate-200 text-left font-mono"
                            inputMode="numeric"
                            dir="ltr"
                            placeholder="0"
                          />
                          <div className="text-right text-xs text-slate-500">
                            ثبت‌شده: {formatRial(line.penalties)}
                          </div>
                        </CardContent>
                      </Card>

                      <Card className="border-slate-200 bg-white shadow-none">
                        <CardContent className="space-y-4 p-5 text-right">
                          <div>
                            <div className="text-sm font-black text-slate-900">مبلغ خالص پرداختی</div>
                            <div className="mt-1 text-xs text-slate-500">
                              خالص = مبلغ منطقه - کسورات قانونی - جرایم عملیاتی
                            </div>
                          </div>
                          <div
                            className={cn(
                              'text-2xl font-black',
                              isLineInvalid ? 'text-rose-600' : 'text-emerald-700',
                            )}
                          >
                            {formatRial(line.netAmount)}
                          </div>
                          <Badge
                            className={cn(
                              'rounded-full px-3 py-1 text-xs font-bold',
                              isLineInvalid
                                ? 'bg-rose-100 text-rose-700'
                                : 'bg-emerald-100 text-emerald-700',
                            )}
                          >
                            {isLineInvalid ? 'نامعتبر' : 'قابل پرداخت'}
                          </Badge>
                          {isLineInvalid ? (
                            <div className="text-sm font-semibold leading-6 text-rose-600">
                              مجموع کسورات این منطقه از مبلغ کارکرد آن بیشتر شده است. ارقام را اصلاح کنید.
                            </div>
                          ) : (
                            <div className="text-sm leading-6 text-slate-500">
                              مجموع کسورات این منطقه برابر است با {formatRial(totalLineDeductions)}.
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    </div>
                  </AccordionContent>
                </AccordionItem>
              );
            })}
          </Accordion>

          <div className="sticky bottom-4 z-10">
            <Card className="border-slate-900 bg-slate-900 text-white shadow-2xl shadow-slate-900/15">
              <CardContent className="grid gap-4 p-5 md:grid-cols-3 xl:grid-cols-4">
                <div className="space-y-1 text-right">
                  <div className="text-xs font-bold text-slate-300">کل ناخالص</div>
                  <div className="text-xl font-black">{formatRial(allocatedTotal)}</div>
                </div>
                <div className="space-y-1 text-right">
                  <div className="text-xs font-bold text-slate-300">کل کسورات</div>
                  <div className="text-xl font-black">{formatRial(totalDeductions)}</div>
                  <div className="text-xs text-slate-400">
                    قانونی: {formatRial(totalLegalDeductions)} | جرایم: {formatRial(totalPenalties)}
                  </div>
                </div>
                <div className="space-y-1 text-right">
                  <div className="text-xs font-bold text-slate-300">کل خالص پرداختی</div>
                  <div className={cn('text-xl font-black', hasNegativeNetAmount ? 'text-rose-300' : 'text-emerald-300')}>
                    {formatRial(totalNetPayable)}
                  </div>
                </div>
                <div className="flex items-center justify-end">
                  <Badge
                    className={cn(
                      'rounded-full px-3 py-1 text-xs font-bold',
                      hasNegativeNetAmount
                        ? 'bg-rose-100 text-rose-700'
                        : 'bg-emerald-100 text-emerald-700',
                    )}
                  >
                    {hasNegativeNetAmount ? 'پیش‌نمایش قفل است' : 'آماده ورود به پیش‌نمایش'}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      );
    }

    if (currentStep === 4) {
      return (
        <div className="space-y-6">
          <Card className="border-slate-200 bg-white/90 shadow-sm">
            <CardHeader className="border-b border-slate-100 text-right">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="space-y-2">
                  <CardTitle className="text-2xl font-black text-slate-900">
                    پیش‌نمایش و تایید نهایی
                  </CardTitle>
                  <CardDescription className="text-sm leading-7 text-slate-500">
                    این نما فقط خواندنی است و آخرین جمع‌بندی مالی پرونده را پیش از صدور کدهای یکتا نمایش می‌دهد.
                  </CardDescription>
                </div>
                <Badge className="bg-slate-900 text-white">Read Only Summary</Badge>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 p-6 md:grid-cols-3">
              <SummaryCard
                title="کل ناخالص"
                value={formatRial(allocatedTotal)}
                caption="مجموع قطعی تسهیم منطقه‌ای پیش از صدور کد"
                icon={ReceiptText}
              />
              <SummaryCard
                title="کل کسورات"
                value={formatRial(totalDeductions)}
                caption={`قانونی ${formatRial(totalLegalDeductions)} | جرایم ${formatRial(totalPenalties)}`}
                icon={ShieldCheck}
              />
              <SummaryCard
                title="کل خالص پرداختی"
                value={formatRial(totalNetPayable)}
                caption="مبلغ نهایی قابل پرداخت پس از اعمال همه کسورات"
                icon={Sparkles}
              />
            </CardContent>
          </Card>

          <Card className="overflow-hidden border-slate-200 bg-white/95 shadow-sm">
            <CardHeader className="border-b border-slate-100 text-right">
              <CardTitle className="text-xl font-black text-slate-900">
                ماتریس نهایی تسهیم به تفکیک منطقه / واحد
              </CardTitle>
              <CardDescription className="text-sm leading-7 text-slate-500">
                هر سطر از این جدول یک payload مستقل برای صدور یک کد یکتای منطقه‌ای خواهد بود.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader className="bg-slate-50/80">
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="px-4 text-right font-black text-slate-600">منطقه/واحد</TableHead>
                      <TableHead className="px-4 text-right font-black text-slate-600">ناخالص</TableHead>
                      <TableHead className="px-4 text-right font-black text-slate-600">کسورات قانونی</TableHead>
                      <TableHead className="px-4 text-right font-black text-slate-600">جرایم</TableHead>
                      <TableHead className="px-4 text-right font-black text-slate-600">خالص پرداختی</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {allocationLines.map((line, index) => (
                      <TableRow key={line.id} className="bg-white/90">
                        <TableCell className="px-4 py-4 text-right">
                          <div className="space-y-2">
                            <Badge variant="outline" className="border-slate-200 bg-slate-50 text-slate-600">
                              ردیف {formatNumber(index + 1)}
                            </Badge>
                            <div className="text-sm font-black text-slate-900">{line.orgUnitLabel}</div>
                            <div className="text-xs text-slate-500">
                              {line.costCenterCode} | {line.budgetLineCode}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="px-4 py-4 text-right font-mono text-sm text-slate-900">
                          {formatRial(line.allocatedAmount)}
                        </TableCell>
                        <TableCell className="px-4 py-4 text-right font-mono text-sm text-slate-900">
                          {formatRial(line.legalDeductions)}
                        </TableCell>
                        <TableCell className="px-4 py-4 text-right font-mono text-sm text-slate-900">
                          {formatRial(line.penalties)}
                        </TableCell>
                        <TableCell className="px-4 py-4 text-right">
                          <div className="font-mono text-sm font-black text-emerald-700">
                            {formatRial(line.netAmount)}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                  <TableFooter className="bg-slate-50/80">
                    <TableRow className="hover:bg-transparent">
                      <TableCell className="px-4 py-4 text-right font-black text-slate-900">جمع نهایی</TableCell>
                      <TableCell className="px-4 py-4 text-right font-mono text-sm font-black text-slate-900">
                        {formatRial(allocatedTotal)}
                      </TableCell>
                      <TableCell className="px-4 py-4 text-right font-mono text-sm font-black text-slate-900">
                        {formatRial(totalLegalDeductions)}
                      </TableCell>
                      <TableCell className="px-4 py-4 text-right font-mono text-sm font-black text-slate-900">
                        {formatRial(totalPenalties)}
                      </TableCell>
                      <TableCell className="px-4 py-4 text-right font-mono text-sm font-black text-emerald-700">
                        {formatRial(totalNetPayable)}
                      </TableCell>
                    </TableRow>
                  </TableFooter>
                </Table>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 bg-white/95 shadow-sm">
            <CardHeader className="border-b border-slate-100 text-right">
              <CardTitle className="text-xl font-black text-slate-900">گیت تایید نهایی</CardTitle>
              <CardDescription className="text-sm leading-7 text-slate-500">
                تا زمانی که تاییدیه کاربر ثبت نشود، صدور کدهای یکتا قفل می‌ماند.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 p-6">
              <div className="flex items-start gap-3 rounded-3xl border border-slate-200 bg-slate-50/80 p-4">
                <Checkbox
                  id="hr-preview-confirm"
                  checked={isPreviewConfirmed}
                  onCheckedChange={(checked) => setIsPreviewConfirmed(checked === true)}
                  className="mt-1 data-[state=checked]:border-[#008099] data-[state=checked]:bg-[#008099]"
                />
                <label
                  htmlFor="hr-preview-confirm"
                  className="cursor-pointer text-sm font-semibold leading-7 text-slate-700"
                >
                  صحت اطلاعات فوق و مبالغ تسهیم‌شده مورد تایید اینجانب می‌باشد.
                </label>
              </div>

              <div className="rounded-3xl border border-dashed border-[#008099]/30 bg-[#008099]/5 p-4 text-right">
                <div className="text-sm font-black text-slate-900">خروجی این اقدام</div>
                <div className="mt-1 text-sm leading-7 text-slate-600">
                  به محض صدور، برای {formatNumber(allocationLines.length)} منطقه/واحد، کد یکتای مالی مستقل تولید می‌شود.
                </div>
              </div>

              {submitError ? (
                <Alert variant="destructive" className="border-red-200 bg-red-50 text-right">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>خطا در صدور کدها</AlertTitle>
                  <AlertDescription>{submitError}</AlertDescription>
                </Alert>
              ) : null}
            </CardContent>
            <CardFooter className="flex flex-col-reverse gap-3 border-t border-slate-100 pt-6 sm:flex-row sm:items-center sm:justify-between">
              <Button type="button" variant="outline" onClick={goToPreviousStep} disabled={isSubmitting}>
                <ChevronRight className="h-4 w-4" />
                مرحله قبل
              </Button>
              <Button
                type="button"
                onClick={handleSubmitTransaction}
                disabled={!isPreviewConfirmed || isSubmitting || !isPreviewReady}
                className="min-w-[220px] bg-[#008099] text-white hover:bg-[#006b80]"
              >
                {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                {isSubmitting ? 'در حال صدور کدهای یکتا...' : 'صدور کدهای یکتا'}
              </Button>
            </CardFooter>
          </Card>
        </div>
      );
    }

    if (generatedCodes.length === 0) {
      return (
        <PlaceholderStep
          title="کدهای یکتا هنوز ایجاد نشده‌اند"
          description="پس از تایید پیش‌نمایش نهایی، در این بخش کدهای صادرشده برای هر منطقه یا واحد نمایش داده می‌شود."
        />
      );
    }

    return (
      <div className="space-y-6">
        <Card className="overflow-hidden border-emerald-200 bg-[linear-gradient(135deg,#ecfdf5_0%,#f0fdf4_46%,#ffffff_100%)] shadow-xl shadow-emerald-100/60">
          <CardContent className="relative flex flex-col items-center gap-5 p-10 text-center">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(16,185,129,0.12),transparent_42%)]" />
            <div className="relative flex h-20 w-20 items-center justify-center rounded-[28px] bg-emerald-500 text-white shadow-lg shadow-emerald-500/25">
              <CheckCircle2 className="h-10 w-10" />
            </div>
            <div className="relative space-y-3">
              <div className="text-3xl font-black tracking-tight text-slate-900">
                کدهای یکتا با موفقیت صادر شد
              </div>
              <div className="max-w-2xl text-sm leading-8 text-slate-600">
                برای هر منطقه/واحد یک شناسه مستقل مالی تولید شد. این کدها آماده ثبت، پیگیری و ارسال در گردش کار هستند.
              </div>
            </div>
            <div className="relative flex flex-wrap items-center justify-center gap-2">
              <Badge className="bg-emerald-500 text-white">{formatNumber(generatedCodes.length)} کد یکتا</Badge>
              <Badge variant="outline" className="border-emerald-200 bg-white/80 text-emerald-700">
                قرارداد {contractNumber}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {submitError ? (
          <Alert variant="destructive" className="border-red-200 bg-red-50 text-right">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>هشدار عملیات</AlertTitle>
            <AlertDescription>{submitError}</AlertDescription>
          </Alert>
        ) : null}

        <div className="grid gap-4 xl:grid-cols-2">
          {generatedCodes.map((item, index) => {
            const matchingLine = allocationLines.find((line) => line.orgUnitLabel === item.region);
            const isCopied = copiedCode === item.code;

            return (
              <Card key={item.code} className="overflow-hidden border-slate-200 bg-white/95 shadow-sm">
                <CardContent className="space-y-4 p-6">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge className="bg-slate-900 text-white">ردیف {formatNumber(index + 1)}</Badge>
                      {matchingLine ? (
                        <Badge variant="outline" className="border-emerald-200 bg-emerald-50 text-emerald-700">
                          {matchingLine.costCenterCode}
                        </Badge>
                      ) : null}
                    </div>
                    <div className="space-y-1 text-right">
                      <div className="text-lg font-black text-slate-900">{item.region}</div>
                      <div className="text-xs text-slate-500">
                        {matchingLine
                          ? `ردیف بودجه ${matchingLine.budgetLineCode} | خالص ${formatRial(matchingLine.netAmount)}`
                          : 'کد یکتای آماده ثبت'}
                      </div>
                    </div>
                  </div>

                  <div className="rounded-3xl border border-dashed border-emerald-300 bg-emerald-50/70 p-4" dir="ltr">
                    <div className="text-xs font-bold uppercase tracking-[0.3em] text-emerald-700">Unique Code</div>
                    <div className="mt-3 break-all text-lg font-black tracking-[0.18em] text-emerald-900">
                      {item.code}
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="text-sm leading-7 text-slate-500">
                      {matchingLine ? `رویداد مالی: ${matchingLine.financialEventType}` : 'کد جهت پیگیری منطقه‌ای صادر شد.'}
                    </div>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="border-slate-200"
                      onClick={() => void handleCopyCode(item.code)}
                    >
                      {isCopied ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
                      {isCopied ? 'کپی شد' : 'کپی کد'}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <Card className="border-slate-200 bg-white/95 shadow-sm">
          <CardContent className="flex flex-col gap-4 p-6 text-right sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-2">
              <div className="text-lg font-black text-slate-900">فرآیند صدور به پایان رسید</div>
              <div className="text-sm leading-7 text-slate-500">
                برای بازگشت به فهرست پرونده‌های امنیت و تسهیم، از دکمه زیر استفاده کنید.
              </div>
            </div>
            <Button
              type="button"
              onClick={() => navigate('/attendance/security-reconciliation')}
              className="bg-[#008099] text-white hover:bg-[#006b80]"
            >
              بازگشت به داشبورد
              <ChevronLeft className="h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div dir="rtl" className="mx-auto flex w-full max-w-7xl flex-col gap-6 pb-10 font-sans text-slate-900">
      <div className="fixed inset-0 -z-10 bg-[#f7fafb]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(0,128,153,0.08),transparent_32%),radial-gradient(circle_at_bottom_left,rgba(15,118,110,0.06),transparent_35%)]" />
        <div className="absolute inset-0 opacity-[0.03] [background-image:radial-gradient(#0f766e_1px,transparent_1px)] [background-size:20px_20px]" />
      </div>

      <Card className="overflow-hidden border-none bg-white/85 shadow-xl backdrop-blur-xl">
        <CardHeader className="border-b border-slate-100 text-right">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-3">
              <div className="flex items-center justify-end gap-3">
                <Badge className="bg-[#008099] text-white">HR Finance Wizard</Badge>
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#008099] text-white shadow-lg shadow-[#008099]/20">
                  <MapPinned className="h-5 w-5" />
                </div>
              </div>
              <CardTitle className="text-3xl font-black tracking-tight text-slate-900">
                ویزارد مالی منابع انسانی
              </CardTitle>
              <CardDescription className="max-w-3xl text-sm leading-7 text-slate-500">
                این ویزارد برای شکستن کارکرد یک پیمانکار بین چند واحد سازمانی طراحی شده است تا در پایان برای هر منطقه یا معاونت یک کد یکتای مستقل صادر شود.
              </CardDescription>
            </div>
            <div className="rounded-3xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-right">
              <div className="text-xs font-bold tracking-wide text-slate-500">Transaction</div>
              <div className="mt-1 text-lg font-black text-slate-900">#{formatNumber(transactionId || 101)}</div>
              <div className="mt-1 text-xs text-slate-500">
                وضعیت: {workflowContext?.transaction.status || 'در حال بارگذاری'}
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-5 p-6">
          {error ? (
            <Alert className="border-amber-200 bg-amber-50 text-right">
              <AlertCircle className="h-4 w-4 text-amber-700" />
              <AlertTitle className="text-amber-900">وضعیت دریافت داده</AlertTitle>
              <AlertDescription className="text-amber-700">{error}</AlertDescription>
            </Alert>
          ) : null}

          <div className="flex flex-wrap items-center gap-2">
            <Badge
              variant="outline"
              className={cn(
                'border px-3 py-1',
                contextMode === 'api'
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                  : 'border-amber-200 bg-amber-50 text-amber-700',
              )}
            >
              {contextMode === 'api' ? 'Context API متصل' : 'Context نمایشی'}
            </Badge>
            <Badge variant="outline" className="border-slate-200 bg-white text-slate-600">
              Step {activeStepMeta.id} / 5
            </Badge>
          </div>

          <div className="grid gap-3 xl:grid-cols-5">
            {WIZARD_STEPS.map((step) => (
              <StepperCard
                key={step.id}
                step={step}
                isActive={step.id === currentStep}
                isComplete={step.id < currentStep || (step.id === 2 && isAllocationBalanced && currentStep > 2)}
                isLocked={!canAccessStep(step.id) || isSubmitting}
                onClick={() => setCurrentStep(step.id)}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      {renderStepContent()}

      {currentStep <= 3 ? (
        <Card className="border-slate-200 bg-white/90 shadow-sm">
          <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
            <Button type="button" variant="outline" onClick={goToPreviousStep} disabled={currentStep === 1}>
              <ChevronRight className="h-4 w-4" />
              مرحله قبل
            </Button>

            <div className="text-center text-sm text-slate-500">
              {currentStep === 2 ? (
                <span>
                  {isAllocationBalanced
                    ? 'جمع تخصیص‌ها معتبر است و می‌توانید به مرحله بعد بروید.'
                    : 'تا زمانی که جمع تخصیص‌ها با مبلغ ناخالص برابر نشود، عبور به مرحله بعد قفل می‌ماند.'}
                </span>
              ) : currentStep === 3 ? (
                <span>
                  {hasNegativeNetAmount
                    ? 'تا وقتی کسورات هر منطقه از مبلغ ناخالص آن بیشتر باشد، ورود به پیش‌نمایش ممکن نیست.'
                    : 'خالص پرداختی تمام مناطق معتبر است و می‌توانید وارد مرحله پیش‌نمایش شوید.'}
                </span>
              ) : (
                <span>پس از تکمیل کنترل‌های اولیه، پیش‌نمایش نهایی و صدور کد یکتا در گام‌های بعدی فعال می‌شود.</span>
              )}
            </div>

            <Button
              type="button"
              onClick={goToNextStep}
              disabled={
                currentStep === 5 ||
                (currentStep === 2 && !isAllocationBalanced) ||
                (currentStep === 3 && hasNegativeNetAmount)
              }
              className="bg-[#008099] text-white hover:bg-[#006b80]"
            >
              مرحله بعد
              <ChevronLeft className="h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}


