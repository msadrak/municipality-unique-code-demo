import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  AlertTriangle,
  Banknote,
  FileImage,
  FileText,
  Gavel,
  Loader2,
  Paperclip,
  ReceiptText,
  RefreshCw,
  ShieldCheck,
  Activity,
  TrendingDown,
} from 'lucide-react';
import { toast } from 'sonner';

import { PENALTY_OPTIONS } from '../../constants/penalties';
import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Textarea } from '../../components/ui/textarea';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../../components/ui/tooltip';
import { Input } from '../../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
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
import {
  createPenaltyRecord,
  fetchWorkPeriodReconciliation,
  fetchWorkPeriodStatus,
  finalizeWorkPeriod,
  generateUniqueCode,
  fetchSheetAttachments,
  fetchRegionAttendanceRecords,
  AttachmentMeta,
  WorkPeriodReconciliation,
} from '../../services/attendance';

const MONTH_LABELS: Record<number, string> = {
  1: 'فروردین',
  2: 'اردیبهشت',
  3: 'خرداد',
  4: 'تیر',
  5: 'مرداد',
  6: 'شهریور',
  7: 'مهر',
  8: 'آبان',
  9: 'آذر',
  10: 'دی',
  11: 'بهمن',
  12: 'اسفند',
};

const STATUS_LABELS: Record<string, string> = {
  DRAFT_REGIONS: 'پیش‌نویس دریافت مناطق',
  PENDING_SECURITY_AGGREGATION: 'در انتظار تجمیع حراست',
  PENDING_CONTRACTOR_STATEMENT: 'در انتظار صورت‌وضعیت پیمانکار',
  PENDING_SECURITY_AUDIT: 'در حال بررسی جرائم و تایید نهایی',
  FINAL_APPROVED: 'تایید نهایی شده',
  PENDING_UNIQUE_CODE: 'در انتظار صدور کد یکتا (امور مالی)',
  SENT_TO_FINANCE: 'ارسال شده به ذیحسابی (دارای کد یکتا)',
};

function getCurrentPersianPeriod() {
  const formatter = new Intl.DateTimeFormat('fa-IR-u-ca-persian', {
    year: 'numeric',
    month: 'numeric',
  });
  const parts = formatter.formatToParts(new Date());
  const year = Number(parts.find((part) => part.type === 'year')?.value ?? '1403');
  const month = Number(parts.find((part) => part.type === 'month')?.value ?? '1');
  return {
    year: Number.isFinite(year) ? year : 1403,
    month: Number.isFinite(month) ? month : 1,
  };
}

function getSelectableYears(currentYear: number) {
  return Array.from({ length: 5 }, (_, index) => currentYear - 2 + index);
}

function formatNumber(value?: number | null) {
  return new Intl.NumberFormat('fa-IR', {
    maximumFractionDigits: 0,
  }).format(Number(value ?? 0));
}

function formatCurrency(value?: number | null) {
  return `${formatNumber(value)} ریال`;
}

interface SummaryCardProps {
  title: string;
  value: string;
  description: string;
  icon: React.ElementType;
  accentClassName: string;
}

function SummaryCard({ title, value, description, icon: Icon, accentClassName }: SummaryCardProps) {
  return (
    <Card className={cn('relative overflow-hidden border-none shadow-lg transition-all hover:shadow-xl', accentClassName)}>
      <div className="absolute -right-6 -top-6 h-32 w-32 rounded-full bg-white/10 blur-2xl" />
      <div className="absolute -bottom-6 -left-6 h-24 w-24 rounded-full bg-black/5 blur-xl" />
      <CardContent className="relative flex flex-col gap-4 p-6 pt-7">
        <div className="flex items-center justify-between gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-white/20 backdrop-blur-md shadow-sm">
            <Icon className="h-6 w-6 text-white" />
          </div>
          <div className="text-right">
            <div className="text-[10px] font-black uppercase tracking-[0.15em] text-white/70">{title}</div>
          </div>
        </div>
        
        <div className="space-y-1 text-right">
          <div className="text-2xl font-black text-white leading-none tracking-tight">
            {value}
          </div>
          <div className="text-[11px] font-medium leading-relaxed text-white/80 line-clamp-2 min-h-[32px]">
            {description}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function SecurityReconciliationDashboard() {
  const navigate = useNavigate();
  const currentPeriod = useMemo(() => getCurrentPersianPeriod(), []);
  const [selectedYear, setSelectedYear] = useState(String(currentPeriod.year));
  const [selectedMonth, setSelectedMonth] = useState(String(currentPeriod.month));
  const [selectedPenaltyId, setSelectedPenaltyId] = useState(
    PENALTY_OPTIONS.length ? String(PENALTY_OPTIONS[0].id) : '',
  );
  const [penaltyDescription, setPenaltyDescription] = useState('');
  const [countInput, setCountInput] = useState('1');
  const [reconciliation, setReconciliation] = useState<WorkPeriodReconciliation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingPenalty, setIsSavingPenalty] = useState(false);
  const [isFinalizing, setIsFinalizing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  // Regional documents viewer state
  const [uploadedRegions, setUploadedRegions] = useState<string[]>([]);
  const [selectedDocRegion, setSelectedDocRegion] = useState<string>('');
  const [regionDocs, setRegionDocs] = useState<AttachmentMeta[]>([]);
  const [isDocsLoading, setIsDocsLoading] = useState(false);

  const yearOptions = useMemo(() => getSelectableYears(currentPeriod.year), [currentPeriod.year]);
  const selectedPenalty = PENALTY_OPTIONS.find((item) => String(item.id) === selectedPenaltyId) ?? null;

  useEffect(() => {
    let cancelled = false;

    const loadReconciliation = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetchWorkPeriodReconciliation(Number(selectedYear), Number(selectedMonth));
        if (!cancelled) {
          setReconciliation(response);
        }
      } catch (err) {
        if (!cancelled) {
          setReconciliation(null);
          setError(err instanceof Error ? err.message : 'دریافت اطلاعات تسویه نهایی ناموفق بود.');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void loadReconciliation();

    // Also load uploaded region list for the document viewer
    fetchWorkPeriodStatus(Number(selectedYear), Number(selectedMonth))
      .then((status) => setUploadedRegions(status.uploaded_regions))
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [refreshKey, selectedMonth, selectedYear]);

  const handleLoadRegionDocs = async (regionName: string) => {
    if (!regionName) return;
    setSelectedDocRegion(regionName);
    setRegionDocs([]);
    setIsDocsLoading(true);
    try {
      const records = await fetchRegionAttendanceRecords(
        Number(selectedYear),
        Number(selectedMonth),
        regionName,
      );
      const sheetId = records[0]?.sheet_id;
      if (!sheetId) {
        setRegionDocs([]);
        return;
      }
      const docs = await fetchSheetAttachments(sheetId);
      setRegionDocs(docs);
    } catch {
      setRegionDocs([]);
    } finally {
      setIsDocsLoading(false);
    }
  };

  const regionTotal = Number(reconciliation?.region_total ?? 0);
  const contractorTotal = Number(reconciliation?.contractor_total ?? 0);
  const totalPenaltiesAmount = Number(reconciliation?.total_penalties_amount ?? 0);
  const finalPayableAmount = Number(reconciliation?.final_payable_amount ?? 0);
  const isFinalApproved = reconciliation?.status === 'FINAL_APPROVED' || reconciliation?.status === 'PENDING_UNIQUE_CODE' || reconciliation?.status === 'SENT_TO_FINANCE';
  const isPendingUniqueCode = reconciliation?.status === 'PENDING_UNIQUE_CODE';
  const isSentToFinance = reconciliation?.status === 'SENT_TO_FINANCE';
  
  // STATE LOCKING: Lock the dashboard if already finalized (has transaction_id or is in post-finalize status)
  const isLocked = Boolean(reconciliation?.financial_transaction_id) || isPendingUniqueCode || isSentToFinance;
  const shouldShowReentryButton = isLocked && reconciliation?.financial_transaction_id;

  const handleAddPenalty = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedDescription = penaltyDescription.trim();
    if (!trimmedDescription) {
      setError('لطفاً شرح تخلف را وارد کنید.');
      toast.error('لطفاً شرح تخلف را وارد کنید');
      return;
    }

    const numericCount = Number(countInput);
    if (!selectedPenalty) {
      setError('نوع جریمه را انتخاب کنید.');
      return;
    }

    if (!Number.isInteger(numericCount) || numericCount <= 0) {
      setError('تعداد/روز باید یک عدد صحیح بزرگ‌تر از صفر باشد.');
      return;
    }

    setIsSavingPenalty(true);
    setError(null);

    try {
      await createPenaltyRecord(Number(selectedYear), Number(selectedMonth), {
        description: trimmedDescription,
        count: numericCount,
        unit_amount: selectedPenalty.unitAmount,
      });
      toast.success('جریمه با موفقیت ثبت شد.');
      setCountInput('1');
      setPenaltyDescription('');
      setRefreshKey((current) => current + 1);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'ثبت جریمه ناموفق بود.';
      setError(message);
      toast.error(message);
    } finally {
      setIsSavingPenalty(false);
    }
  };

  const handleFinalize = async () => {
    setIsFinalizing(true);
    setError(null);

    try {
      const response = await finalizeWorkPeriod(Number(selectedYear), Number(selectedMonth));
      
      // Extract transaction_id from response
      const transactionId = response.financial_transaction_id;
      
      setReconciliation((current) => (
        current
          ? {
              ...current,
              status: response.status,
              financial_transaction_id: response.financial_transaction_id ?? current.financial_transaction_id,
              financial_transaction_status: response.financial_transaction_status ?? current.financial_transaction_status,
              financial_tracking_number: response.financial_tracking_number ?? current.financial_tracking_number,
            }
          : current
      ));
      
      toast.success('پرونده با موفقیت به گردش‌کار مالی ارجاع شد. در حال انتقال...');
      
      // IMMEDIATE REDIRECT: Navigate to workflow page
      if (transactionId) {
        navigate(`/hr-finance/workflow/${transactionId}`);
      } else {
        toast.error('شناسه تراکنش مالی دریافت نشد. لطفاً صفحه را بازخوانی کنید.');
        setRefreshKey((current) => current + 1);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'تایید نهایی ناموفق بود.';
      setError(message);
      toast.error(message);
    } finally {
      setIsFinalizing(false);
    }
  };

  const handleEnterFinancialDashboard = () => {
    const transactionId = reconciliation?.financial_transaction_id;
    if (!transactionId) {
      const message = 'شناسه تراکنش مالی هنوز ایجاد نشده است. یک‌بار بازخوانی کنید.';
      setError(message);
      toast.error(message);
      return;
    }

    navigate(`/hr-finance/workflow/${transactionId}`);
  };

  const handleGenerateUniqueCode = async () => {
    setIsFinalizing(true);
    setError(null);

    try {
      const response = await generateUniqueCode(Number(selectedYear), Number(selectedMonth));
      setReconciliation((current) => (
        current ? { ...current, status: response.status } : current
      ));
      toast.success('کد یکتای مالی با موفقیت صادر و پرونده به ذیحسابی ارسال شد');
      setRefreshKey((current) => current + 1);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'ورود به کارتابل مالی ناموفق بود.';
      setError(message);
      toast.error(message);
    } finally {
      setIsFinalizing(false);
    }
  };

  return (
    <div dir="rtl" className="relative mx-auto flex w-full max-w-7xl flex-col gap-8 pb-12 text-slate-900 font-sans">
      <div className="fixed inset-0 -z-10 bg-[#f8fafc]">
        <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(circle_at_top_right,rgba(0,128,153,0.03),transparent_40%),radial-gradient(circle_at_bottom_left,rgba(0,128,153,0.05),transparent_40%)]" />
        <div className="absolute inset-0 opacity-[0.02] [background-image:radial-gradient(#008099_1px,transparent_1px)] [background-size:24px_24px]" />
      </div>

      <Card className="relative overflow-hidden border-none bg-white/60 backdrop-blur-2xl shadow-xl">
        <div className="absolute inset-y-0 left-0 w-1/3 bg-[radial-gradient(circle_at_top_left,rgba(0,128,153,0.03),transparent_65%)]" />
        <div className="absolute inset-y-0 right-0 w-1/3 bg-[radial-gradient(circle_at_top_right,rgba(0,128,153,0.02),transparent_62%)]" />
        <div className="absolute inset-0 bg-white/[0.01] bg-[size:32px_32px]" />
        <CardHeader className="relative gap-6 z-10 border-b border-slate-100 pb-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-3 text-right">
              <div className="flex items-center justify-end gap-3">
                <Badge variant="secondary" className="bg-[#008099]/10 text-[#008099] border-none font-bold">
                  داشبورد کسر جرائم و تایید نهایی
                </Badge>
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#008099] text-white shadow-lg shadow-[#008099]/20">
                  <Activity className="h-6 w-6" />
                </div>
              </div>
              <CardTitle className="text-3xl font-black tracking-tight text-slate-900">
                موتور جرائم و تسویه نهایی
              </CardTitle>
              <CardDescription className="max-w-3xl text-base leading-relaxed text-slate-500">
                تحلیل مبالغ فاکتور پیمانکار، تطبیق با محاسبات سیستمی و اعمال کسورات قانونی جهت صدور تاییدیه نهایی.
              </CardDescription>
            </div>

            <Button
              variant="outline"
              className="gap-2 self-start border-slate-200 bg-white hover:bg-slate-50 text-slate-600"
              onClick={() => setRefreshKey((current) => current + 1)}
              disabled={isLoading || isSavingPenalty || isFinalizing}
            >
              <RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
              بازخوانی داده‌ها
            </Button>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[1fr_1fr_auto]">
            <div className="space-y-2 text-right">
              <span className="text-xs font-bold uppercase tracking-widest text-slate-400 pr-1">سال مالی</span>
              <Select value={selectedYear} onValueChange={setSelectedYear}>
                <SelectTrigger className="h-12 rounded-2xl border-slate-100 bg-slate-50/50 text-right text-slate-700 focus:ring-[#008099]/20">
                  <SelectValue placeholder="انتخاب سال" />
                </SelectTrigger>
                <SelectContent className="border-slate-100 bg-white text-slate-700">
                  {yearOptions.map((year) => (
                    <SelectItem key={year} value={String(year)} className="focus:bg-slate-50 focus:text-[#008099]">
                      {formatNumber(year)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2 text-right">
              <span className="text-xs font-bold uppercase tracking-widest text-slate-400 pr-1">دوره ماهانه</span>
              <Select value={selectedMonth} onValueChange={setSelectedMonth}>
                <SelectTrigger className="h-12 rounded-2xl border-slate-100 bg-slate-50/50 text-right text-slate-700 focus:ring-[#008099]/20">
                  <SelectValue placeholder="انتخاب ماه" />
                </SelectTrigger>
                <SelectContent className="border-slate-100 bg-white text-slate-700">
                  {Object.entries(MONTH_LABELS).map(([month, label]) => (
                    <SelectItem key={month} value={month} className="focus:bg-slate-50 focus:text-[#008099]">
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col items-end justify-end gap-2">
              <span className="text-xs font-bold uppercase tracking-widest text-slate-400 pr-1">وضعیت فرآیند</span>
              <Badge
                variant="secondary"
                className={cn(
                  'px-4 py-2.5 text-sm text-right border-none font-black',
                  isSentToFinance
                    ? 'bg-emerald-50 text-emerald-700'
                    : isPendingUniqueCode
                    ? 'bg-[#008099]/10 text-[#008099] animate-pulse'
                    : isFinalApproved
                    ? 'bg-blue-50 text-blue-700'
                    : 'bg-slate-100 text-slate-500',
                )}
              >
                {STATUS_LABELS[reconciliation?.status || ''] || reconciliation?.status || 'نامشخص'}
              </Badge>
            </div>
          </div>
        </CardHeader>
      </Card>

      {error ? (
        <Alert className="border-rose-500/30 bg-rose-500/10 text-rose-300">
          <AlertCircle className="h-4 w-4 text-rose-400" />
          <AlertTitle>خطا در دریافت یا ثبت اطلاعات</AlertTitle>
          <AlertDescription className="text-rose-200">{error}</AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <SummaryCard
          title="محاسبات سیستمی"
          value={formatCurrency(regionTotal)}
          description="بر اساس آنالیز حقوق ۱۴۰۵ (تایید شده)"
          icon={Activity}
          accentClassName="bg-gradient-to-br from-[#008099] to-[#006b80]"
        />
        <SummaryCard
          title="فاکتور پیمانکار"
          value={formatCurrency(contractorTotal)}
          description="مبلغ اظهارشده توسط پیمانکار برای این دوره"
          icon={ReceiptText}
          accentClassName="bg-gradient-to-br from-[#5C92B1] to-[#4a7a94]"
        />
        <SummaryCard
          title="خالص قابل پرداخت"
          value={formatCurrency(finalPayableAmount)}
          description="مبلغ نهایی پس از کسر تمامی جرائم و کسورات"
          icon={ShieldCheck}
          accentClassName="bg-gradient-to-br from-emerald-600 to-teal-700"
        />
      </div>

      {reconciliation && !isLoading && (
        <div className="flex flex-col gap-6 w-full animate-in fade-in slide-in-from-bottom-4 duration-700">
          <Card className="border-none bg-white shadow-lg p-8">
            <div className="mb-5 flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-widest text-slate-400">تحلیل انطباق مالی</span>
              <span className="text-sm font-black text-[#008099]">
                {Math.min(100, Math.round((regionTotal / (contractorTotal || 1)) * 100) || 0)}% انطباق سیستمی
              </span>
            </div>
            <div className="relative h-4 w-full overflow-hidden rounded-full bg-slate-100 shadow-inner">
               <div 
                  className="absolute left-0 top-0 h-full bg-rose-500/10 transition-all duration-1000"
                  style={{ width: '100%' }}
               />
               <div 
                  className="absolute right-0 top-0 h-full bg-[#008099] shadow-[0_0_15px_rgba(0,128,153,0.3)] transition-all duration-1000"
                  style={{ width: `${Math.min(100, (regionTotal / (contractorTotal || 1)) * 100 || 0)}%` }}
               />
            </div>
            <div className="mt-5 flex justify-between text-[11px] font-bold uppercase tracking-wider">
               <div className="flex items-center gap-2 text-[#008099]">
                 <div className="h-2 w-2 rounded-full bg-[#008099]"></div>
                 تایید شده (سیستمی): {formatCurrency(regionTotal)}
               </div>
               <div className="flex items-center gap-2 text-rose-500">
                 ادعای پیمانکار: {formatCurrency(contractorTotal)}
                 <div className="h-2 w-2 rounded-full bg-rose-500"></div>
               </div>
            </div>
          </Card>

          <div className={cn(
            "relative overflow-hidden rounded-[2rem] border p-8 font-semibold shadow-xl transition-all duration-500 flex items-center gap-6 justify-between",
            (contractorTotal - regionTotal) > 0
              ? "border-rose-100 bg-rose-50 text-rose-700"
              : "border-emerald-100 bg-emerald-50 text-emerald-700"
          )}>
            <div className="flex items-center gap-6">
              <div className={cn(
                "flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-white shadow-sm",
              )}>
                {(contractorTotal - regionTotal) > 0 ? <AlertTriangle className="h-8 w-8 text-rose-500" /> : <ShieldCheck className="h-8 w-8 text-emerald-500" />}
              </div>
              <div className="flex flex-col gap-1 z-10 text-right">
                <span className="text-xs font-bold uppercase tracking-widest opacity-60">
                  {(contractorTotal - regionTotal) > 0 ? 'کسری تاییدنشده (مغایرت بحرانی)' : 'تطابق کامل حساب'}
                </span>
                <span className="text-4xl font-black tracking-tighter" dir="rtl">
                  {formatCurrency(contractorTotal - regionTotal)}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {isLoading ? (
        <Card className="border-white/5 bg-slate-900/40 backdrop-blur-xl shadow-2xl">
          <CardContent className="flex min-h-[280px] items-center justify-center">
            <div className="flex items-center gap-3 text-slate-400">
              <Loader2 className="h-5 w-5 animate-spin" />
              در حال دریافت اطلاعات تسویه و جرائم...
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
            <Card className="border-none bg-white shadow-lg">
              <CardHeader className="text-right pb-4">
                <div className="flex items-center justify-between gap-3">
                  <Badge variant="secondary" className="bg-slate-50 text-slate-500 font-bold border-none">
                    جمع جرائم: {formatCurrency(totalPenaltiesAmount)}
                  </Badge>
                  <div className="space-y-1">
                    <CardTitle className="text-xl font-black text-slate-900">افزودن کسر جریمه</CardTitle>
                    <CardDescription className="text-xs font-medium text-slate-400">
                      ثبت تخلفات قراردادی جهت کسر از صورت‌وضعیت نهایی
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <form className="space-y-6" onSubmit={handleAddPenalty}>
                  <div className="space-y-2 text-right">
                    <span className="text-xs font-bold uppercase tracking-widest text-slate-400 pr-1">نوع جریمه قراردادی</span>
                    <Select value={selectedPenaltyId} onValueChange={setSelectedPenaltyId} disabled={isLocked}>
                      <SelectTrigger className="h-12 rounded-2xl border-slate-100 bg-slate-50/50 text-slate-700 text-right focus:ring-[#008099]/20">
                        <SelectValue placeholder="انتخاب نوع جریمه" />
                      </SelectTrigger>
                      <SelectContent className="bg-white border-slate-100">
                        {PENALTY_OPTIONS.map((penalty) => (
                          <SelectItem key={penalty.id} value={String(penalty.id)} className="focus:bg-slate-50 focus:text-[#008099]">
                            {penalty.title}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2 text-right">
                    <span className="text-xs font-bold uppercase tracking-widest text-slate-400 pr-1">شرح تخلف / علت جریمه *</span>
                    <Textarea
                      value={penaltyDescription}
                      onChange={(event) => setPenaltyDescription(event.target.value)}
                      placeholder="توضیحات کامل در مورد تخلف و دلیل اعمال جریمه را وارد کنید..."
                      disabled={isLocked}
                      className="min-h-[100px] rounded-2xl border-slate-100 bg-slate-50/50 text-slate-700 text-right focus:ring-[#008099]/20 resize-none"
                    />
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2 text-right">
                      <span className="text-xs font-bold uppercase tracking-widest text-slate-400 pr-1">تعداد / روز</span>
                      <Input
                        type="number"
                        min={1}
                        value={countInput}
                        onChange={(event) => setCountInput(event.target.value)}
                        disabled={isLocked}
                        className="h-12 rounded-2xl border-slate-100 bg-slate-50/50 text-slate-700 text-right focus:ring-[#008099]/20"
                      />
                    </div>
                    <div className="space-y-2 text-right">
                      <span className="text-xs font-bold uppercase tracking-widest text-slate-400 pr-1">مبلغ واحد (ریال)</span>
                      <div className="flex h-12 items-center justify-end rounded-2xl border border-slate-100 bg-slate-50/30 px-4 text-sm font-bold text-[#008099]">
                        {formatCurrency(selectedPenalty?.unitAmount ?? 0)}
                      </div>
                    </div>
                  </div>

                  <div className="rounded-2xl bg-[#008099]/5 border border-[#008099]/10 p-4 text-right">
                    <span className="text-xs font-bold text-slate-400">مجموع این ردیف:</span>
                    {' '}
                    <span className="text-lg font-black text-[#008099]">
                      {formatCurrency((selectedPenalty?.unitAmount ?? 0) * Number(countInput || 0))}
                    </span>
                  </div>

                  <Button
                    type="submit"
                    className="h-14 w-full gap-2 rounded-2xl bg-[#008099] text-white text-base font-black hover:bg-[#006b80] shadow-lg shadow-[#008099]/20 transition-all"
                    disabled={isSavingPenalty || isFinalApproved || isLocked}
                  >
                    {isSavingPenalty ? <Loader2 className="h-5 w-5 animate-spin" /> : <Gavel className="h-5 w-5" />}
                    {isLocked ? 'پرونده قفل شده است' : 'ثبت در لیست کسورات'}
                  </Button>
                </form>
              </CardContent>
            </Card>

            <Card className="border-none bg-white shadow-lg overflow-hidden">
              <CardHeader className="text-right border-b border-slate-50 pb-6">
                <CardTitle className="text-xl font-black text-slate-900">فهرست کسورات اعمال‌شده</CardTitle>
                <CardDescription className="text-xs font-medium text-slate-400">
                  جرائم ثبت‌شده که از مبلغ نهایی کسر خواهند شد
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-hidden">
                  <Table>
                    <TableHeader className="bg-slate-50/50">
                      <TableRow className="border-b border-slate-100 hover:bg-transparent">
                        <TableHead className="text-right text-xs font-bold text-slate-400 uppercase tracking-widest">شرح تخلف</TableHead>
                        <TableHead className="text-right text-xs font-bold text-slate-400 uppercase tracking-widest">مقدار</TableHead>
                        <TableHead className="text-right text-xs font-bold text-slate-400 uppercase tracking-widest">مبلغ واحد</TableHead>
                        <TableHead className="text-right text-xs font-bold text-slate-400 uppercase tracking-widest">جمع کسر</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      <TooltipProvider>
                      {reconciliation?.penalties.length ? (
                        reconciliation.penalties.map((penalty) => (
                          <TableRow key={penalty.id} className="border-b border-slate-50 hover:bg-slate-50/30 transition-colors">
                            <TableCell className="text-right font-bold text-slate-700 py-4">
                              {penalty.description.length > 50 ? (
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <span className="cursor-help">
                                      {penalty.description.substring(0, 50)}...
                                    </span>
                                  </TooltipTrigger>
                                  <TooltipContent side="top" className="max-w-md bg-slate-900 text-white p-3 text-sm">
                                    <p className="text-right leading-relaxed">{penalty.description}</p>
                                  </TooltipContent>
                                </Tooltip>
                              ) : (
                                penalty.description
                              )}
                            </TableCell>
                            <TableCell className="text-right font-mono text-slate-500">{formatNumber(penalty.count)}</TableCell>
                            <TableCell className="text-right font-mono text-slate-500">{formatCurrency(penalty.unit_amount)}</TableCell>
                            <TableCell className="text-right font-mono font-bold text-rose-500">
                              -{formatCurrency(penalty.total_amount)}
                            </TableCell>
                          </TableRow>
                        ))
                      ) : null}
                      </TooltipProvider>
                      {!reconciliation?.penalties.length ? (
                        <TableRow className="hover:bg-transparent">
                          <TableCell colSpan={4} className="py-20 text-center">
                            <div className="flex flex-col items-center gap-2 text-slate-300">
                              <ShieldCheck className="h-10 w-10 opacity-20" />
                              <p className="text-sm font-medium">هیچ جریمه‌ای ثبت نشده است.</p>
                            </div>
                          </TableCell>
                        </TableRow>
                      ) : null}
                    </TableBody>
                    {reconciliation?.penalties.length ? (
                      <TableFooter className="bg-slate-50/50 border-t border-slate-100">
                        <TableRow className="hover:bg-transparent">
                          <TableCell colSpan={3} className="text-right font-black text-slate-900">
                            مجموع کسورات دوره
                          </TableCell>
                          <TableCell className="text-right font-mono font-black text-rose-600">
                            {formatCurrency(totalPenaltiesAmount)}
                          </TableCell>
                        </TableRow>
                      </TableFooter>
                    ) : null}
                  </Table>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Regional Documents Viewer */}
          <Card className="border-none bg-white shadow-lg overflow-hidden">
            <CardHeader className="text-right bg-slate-50/50 border-b border-slate-100">
              <div className="flex items-center justify-between gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#008099]/10 text-[#008099]">
                  <Paperclip className="h-6 w-6" />
                </div>
                <div className="space-y-1">
                  <CardTitle className="text-xl font-black text-slate-900">مستندات ارسالی مناطق</CardTitle>
                  <CardDescription className="text-xs font-medium text-slate-400">مشاهده پیوست‌های تاییدیه حضور و غیاب هر منطقه</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-8 space-y-6">
              {uploadedRegions.length === 0 ? (
                <div className="py-12 text-center text-sm font-medium text-slate-300">هنوز هیچ منطقه‌ای برای این دوره فایلی ارسال نکرده است.</div>
              ) : (
                <>
                  <div className="space-y-2 text-right">
                    <span className="text-xs font-bold uppercase tracking-widest text-slate-400 pr-1">انتخاب واحد سازمانی</span>
                    <Select
                      value={selectedDocRegion}
                      onValueChange={(val) => void handleLoadRegionDocs(val)}
                    >
                      <SelectTrigger className="h-12 rounded-2xl border-slate-100 bg-slate-50/50 text-slate-700 text-right focus:ring-[#008099]/20">
                        <SelectValue placeholder="منطقه را انتخاب کنید" />
                      </SelectTrigger>
                      <SelectContent className="bg-white border-slate-100">
                        {uploadedRegions.map((r) => (
                          <SelectItem key={r} value={r} className="focus:bg-slate-50">{r}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {isDocsLoading && (
                    <div className="flex items-center justify-center gap-3 py-12 text-slate-400">
                      <Loader2 className="h-5 w-5 animate-spin" />
                      <span className="text-sm font-medium">در حال واکشی مستندات...</span>
                    </div>
                  )}

                  {!isDocsLoading && selectedDocRegion && regionDocs.length === 0 && (
                    <div className="py-12 text-center text-sm font-medium text-slate-300">
                      هیچ سندی برای این منطقه یافت نشد.
                    </div>
                  )}

                  {regionDocs.length > 0 && (
                    <div className="grid gap-3 sm:grid-cols-2">
                      {regionDocs.map((doc) => (
                        <a
                          key={doc.id}
                          href={`/${doc.file_path}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center justify-between gap-4 rounded-2xl border border-slate-100 bg-slate-50/30 p-4 transition-all hover:bg-white hover:shadow-md group"
                        >
                          <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white shadow-sm">
                              {doc.file_type === 'pdf'
                                ? <FileText className="h-5 w-5 text-rose-500" />
                                : <FileImage className="h-5 w-5 text-[#008099]" />}
                            </div>
                            <div className="text-right">
                              <p className="text-sm font-bold text-slate-700 truncate max-w-[150px]">{doc.file_name}</p>
                              <p className="text-[10px] font-mono text-slate-400" dir="ltr">
                                {new Date(doc.created_at).toLocaleDateString('fa-IR')}
                              </p>
                            </div>
                          </div>
                          <ArrowLeft className="h-4 w-4 text-slate-300 group-hover:text-[#008099] transition-colors" />
                        </a>
                      ))}
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          <Card className="border-none bg-white shadow-lg overflow-hidden">
            <CardHeader className="text-right border-b border-slate-50">
              <CardTitle className="text-xl font-black text-slate-900">تایید نهایی و صدور حواله</CardTitle>
              <CardDescription className="text-xs font-medium text-slate-400">
                قفل کردن مبالغ و ارجاع پرونده به ذیحسابی جهت پرداخت نهایی
              </CardDescription>
            </CardHeader>
            <CardContent className="p-8 space-y-8">
              {isLocked && !isSentToFinance && (
                <Alert className="border-amber-200 bg-amber-50/50">
                  <AlertCircle className="h-5 w-5 text-amber-600" />
                  <AlertTitle className="text-amber-900 font-bold text-right">پرونده قفل شده است</AlertTitle>
                  <AlertDescription className="text-amber-700 text-right text-sm leading-relaxed">
                    این دوره کاری به گردش‌کار مالی ارجاع شده و امکان ویرایش وجود ندارد. برای ادامه فرآیند صدور کد یکتا، از دکمه زیر استفاده کنید.
                  </AlertDescription>
                </Alert>
              )}

              {isSentToFinance && reconciliation?.financial_unique_code && (
                <div className="rounded-[2rem] border border-[#008099]/10 bg-[#008099]/5 p-8 text-right shadow-sm">
                  <div className="flex items-center justify-end gap-3 mb-4">
                    <span className="text-lg font-black text-[#008099]">پرونده مختومه و ارسال شد</span>
                    <ShieldCheck className="h-7 w-7 text-[#008099]" />
                  </div>
                  <p className="text-sm text-slate-500 leading-relaxed mb-6">
                    تمامی محاسبات حضور و غیاب و جرائم تایید گردید. کد یکتای مالی صادر شده و پرونده در اختیار واحد ذیحسابی قرار دارد.
                  </p>
                  <div className="flex items-center justify-between rounded-2xl bg-white p-6 shadow-inner border border-slate-100">
                    <div className="text-2xl font-black text-[#008099] font-mono tracking-[0.2em]">{reconciliation.financial_unique_code}</div>
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Financial Token</div>
                  </div>
                </div>
              )}

              <Button
                className={cn(
                  "h-16 w-full gap-3 rounded-[1.5rem] text-white text-lg font-black transition-all duration-300 shadow-lg shadow-[#008099]/20",
                  isSentToFinance 
                    ? "bg-slate-100 text-slate-400 shadow-none cursor-default border border-slate-200" 
                    : shouldShowReentryButton
                    ? "bg-[#008099] hover:bg-[#006b80] hover:scale-[1.01]"
                    : "bg-[#008099] hover:bg-[#006b80] hover:scale-[1.01]"
                )}
                disabled={isFinalizing || isSentToFinance || !reconciliation}
                onClick={() => void (shouldShowReentryButton ? handleEnterFinancialDashboard() : handleFinalize())}
              >
                {isFinalizing ? <Loader2 className="h-6 w-6 animate-spin" /> : <ShieldCheck className="h-6 w-6" />}
                {isSentToFinance 
                  ? 'عملیات با موفقیت پایان یافته است' 
                  : shouldShowReentryButton
                  ? 'ادامه فرآیند صدور کد یکتا'
                  : 'تایید نهایی و ارسال به امور مالی'}
              </Button>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
