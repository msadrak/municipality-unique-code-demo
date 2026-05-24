export type VolumeContractAttachmentSection = 'contract' | 'monthly';

export interface VolumeContractWorkflowStepMeta {
  stepNumber: number;
  title: string;
  documentType: string;
  attachmentSection: VolumeContractAttachmentSection;
  description: string;
}

export const VOLUME_CONTRACT_ATTACHMENT_SECTION_LABELS: Record<VolumeContractAttachmentSection, string> = {
  contract: 'اسناد و پیوست‌های قرارداد',
  monthly: 'مستندات و صورت‌جلسات ماهانه',
};

export const VOLUME_CONTRACT_WORKFLOW_STEPS: VolumeContractWorkflowStepMeta[] = [
  {
    stepNumber: 101,
    title: 'ثبت پایه قرارداد',
    documentType: 'VOLUME_CONTRACT_BASE',
    attachmentSection: 'contract',
    description: 'ثبت اطلاعات پایه قرارداد، پیمانکار خدماتی و بازه زمانی اجرا.',
  },
  {
    stepNumber: 102,
    title: 'تدقیق آنالیز حقوق - پیوست ۵',
    documentType: 'APPENDIX_5_SALARY_ANALYSIS',
    attachmentSection: 'contract',
    description: 'ثبت جزییات حقوق و دستمزد، مزایا و نرخ‌های محاسباتی قرارداد.',
  },
  {
    stepNumber: 103,
    title: 'تخصیص ماتریس مالی',
    documentType: 'FINANCIAL_MATRIX_LINK',
    attachmentSection: 'contract',
    description: 'اتصال قرارداد به ردیف بودجه و مرکز هزینه مربوطه.',
  },
  {
    stepNumber: 104,
    title: 'صدور کد یکتا',
    documentType: 'YEKTA_CODE_ISSUANCE',
    attachmentSection: 'contract',
    description: 'تایید ماتریس مالی و تولید کد یکتای تخصیص برای قرارداد.',
  },
  {
    stepNumber: 105,
    title: 'ثبت کارکرد ماهانه',
    documentType: 'MONTHLY_TIMESHEET',
    attachmentSection: 'monthly',
    description: 'ثبت روزهای کارکرد، اضافه‌کار و غیبت‌های ماه جاری.',
  },
  {
    stepNumber: 106,
    title: 'محاسبه خودکار صورت‌وضعیت',
    documentType: 'AUTO_STATEMENT_CALCULATION',
    attachmentSection: 'monthly',
    description: 'محاسبه خودکار مبلغ ناخالص، حقوق کارکرد و جمع مزایا.',
  },
  {
    stepNumber: 107,
    title: 'اعمال کسورات قانونی',
    documentType: 'LEGAL_DEDUCTIONS',
    attachmentSection: 'monthly',
    description: 'اعمال مالیات، بیمه و تضمین حسن انجام کار روی صورت‌وضعیت.',
  },
  {
    stepNumber: 108,
    title: 'تایید ناظر عملیاتی',
    documentType: 'OPERATIONAL_APPROVAL',
    attachmentSection: 'monthly',
    description: 'ثبت نظر ناظر عملیاتی درباره کارکرد و کیفیت اجرای خدمات.',
  },
  {
    stepNumber: 109,
    title: 'ممیزی نهایی و کنترل بودجه',
    documentType: 'FINAL_BUDGET_AUDIT',
    attachmentSection: 'monthly',
    description: 'کنترل مانده بودجه و تایید نهایی برای پرداخت.',
  },
  {
    stepNumber: 110,
    title: 'خروجی خزانه و پرداخت',
    documentType: 'TREASURY_PAYMENT_EXPORT',
    attachmentSection: 'monthly',
    description: 'ثبت تاریخ پرداخت و شماره رهگیری خروجی خزانه.',
  },
];

export const APPENDIX_5_FIELD_DEFINITIONS = [
  { key: 'base_salary', label: 'حقوق پایه' },
  { key: 'housing_allowance', label: 'حق مسکن' },
  { key: 'grocery_allowance', label: 'بن خواروبار' },
  { key: 'child_family_allowance', label: 'حق اولاد / عائله‌مندی' },
  { key: 'overtime_rate', label: 'نرخ اضافه کار' },
  { key: 'employer_insurance_premium', label: 'حق بیمه سهم کارفرما' },
] as const;

export function getVolumeContractStepByDocumentType(documentType?: string | null): VolumeContractWorkflowStepMeta | undefined {
  if (!documentType) return undefined;
  return VOLUME_CONTRACT_WORKFLOW_STEPS.find((step) => step.documentType === documentType);
}

export function getVolumeContractStepByNumber(stepNumber?: number | null): VolumeContractWorkflowStepMeta | undefined {
  if (!stepNumber) return undefined;
  return VOLUME_CONTRACT_WORKFLOW_STEPS.find((step) => step.stepNumber === stepNumber);
}

export function formatRialCurrency(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return '—';
  return `${new Intl.NumberFormat('fa-IR').format(numericValue)} ریال`;
}

export function formatPersianDateTime(value?: string | null): string {
  if (!value) return '—';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString('fa-IR');
}
