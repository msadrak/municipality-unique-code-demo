import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  ReceiptText,
  RefreshCw,
  Scale,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from 'lucide-react';
import { toast } from 'sonner';

import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Textarea } from '../../components/ui/textarea';
import { cn } from '../../components/ui/utils';
import {
  AttendanceSheet,
  AttendanceReconciliation,
  fetchAttendanceReconciliation,
  fetchAttendanceSheets,
  transitionAttendanceSheet,
} from '../../services/attendance';

const STATUS_LABELS: Record<string, string> = {
  DRAFT: 'پیش‌نویس',
  CREATOR_APPROVED: 'تایید ثبت‌کننده',
  COMPANY_REP_APPROVED: 'تایید نماینده شرکت',
  SECURITY_APPROVED: 'تایید حراست',
  GM_APPROVED: 'تایید نهایی',
  NEEDS_CORRECTION: 'نیازمند اصلاح',
  REJECTED: 'رد شده',
};

const PERSIAN_MONTHS: Record<number, string> = {
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

const NON_REJECTABLE_STATUSES = new Set(['DRAFT', 'NEEDS_CORRECTION', 'REJECTED']);

function normalizeRegion(value?: string | null) {
  return (value || '').trim();
}

function formatNumber(value?: number | null) {
  const numeric = Number(value ?? 0);
  return new Intl.NumberFormat('fa-IR', {
    maximumFractionDigits: 0,
  }).format(Number.isFinite(numeric) ? numeric : 0);
}

function formatCurrency(value?: number | null) {
  return `${formatNumber(value)} ریال`;
}

function formatDate(value?: string | null) {
  if (!value) return '-';
  return new Intl.DateTimeFormat('fa-IR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(new Date(value));
}

function getUniqueYears(sheets: AttendanceSheet[]) {
  return Array.from(
    new Set(
      sheets
        .map((sheet) => sheet.year)
        .filter((value): value is number => value !== null && value !== undefined),
    ),
  ).sort((a, b) => b - a);
}

function getMonthsForYear(sheets: AttendanceSheet[], year?: number) {
  if (!year) return [];
  return Array.from(
    new Set(
      sheets
        .filter((sheet) => sheet.year === year)
        .map((sheet) => sheet.month)
        .filter((value): value is number => value !== null && value !== undefined),
    ),
  ).sort((a, b) => a - b);
}

function getRegionsForPeriod(sheets: AttendanceSheet[], year?: number, month?: number) {
  if (!year || !month) return [];
  const seen = new Set<string>();
  const regions: string[] = [];

  for (const sheet of sheets) {
    if (sheet.year !== year || sheet.month !== month) continue;
    const region = normalizeRegion(sheet.region);
    if (!region || seen.has(region)) continue;
    seen.add(region);
    regions.push(region);
  }

  return regions.sort((left, right) => left.localeCompare(right, 'fa'));
}

interface MetricCardProps {
  title: string;
  value: string;
  description: string;
  icon: React.ElementType;
  accentClassName: string;
  iconWrapClassName: string;
}

function MetricCard({
  title,
  value,
  description,
  icon: Icon,
  accentClassName,
  iconWrapClassName,
}: MetricCardProps) {
  return (
    <Card className={cn('relative overflow-hidden border-0 text-white shadow-xl', accentClassName)}>
      <div className="absolute -right-10 top-0 h-28 w-28 rounded-full bg-white/10 blur-2xl" />
      <div className="absolute bottom-0 left-0 h-24 w-24 rounded-full bg-black/10 blur-2xl" />
      <CardContent className="relative flex min-h-[188px] flex-col justify-between p-6">
        <div className="flex items-start justify-between gap-4">
          <div className={cn('flex h-14 w-14 items-center justify-center rounded-2xl border border-white/20', iconWrapClassName)}>
            <Icon className="h-7 w-7" />
          </div>
          <div className="text-right">
            <div className="text-sm font-medium text-white/75">{title}</div>
            <div className="mt-4 text-3xl font-black leading-tight">{value}</div>
          </div>
        </div>
        <div className="text-right text-sm leading-7 text-white/80">{description}</div>
      </CardContent>
    </Card>
  );
}

export default function ReconciliationDashboard() {
  const [sheets, setSheets] = useState<AttendanceSheet[]>([]);
  const [selectedYear, setSelectedYear] = useState('');
  const [selectedMonth, setSelectedMonth] = useState('');
  const [selectedRegion, setSelectedRegion] = useState('');
  const [reconciliation, setReconciliation] = useState<AttendanceReconciliation | null>(null);
  const [note, setNote] = useState('');
  const [catalogueLoading, setCatalogueLoading] = useState(true);
  const [dataLoading, setDataLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<'approve' | 'reject' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const loadSheets = async () => {
      setCatalogueLoading(true);
      setError(null);

      try {
        const response = await fetchAttendanceSheets();
        if (cancelled) return;

        setSheets(response);

        const firstEligibleSheet = response.find(
          (sheet) => sheet.year && sheet.month && normalizeRegion(sheet.region),
        );

        if (firstEligibleSheet) {
          setSelectedYear((current) => current || String(firstEligibleSheet.year));
          setSelectedMonth((current) => current || String(firstEligibleSheet.month));
          setSelectedRegion((current) => current || normalizeRegion(firstEligibleSheet.region));
        }
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'دریافت فهرست دوره‌ها ناموفق بود.');
      } finally {
        if (!cancelled) {
          setCatalogueLoading(false);
        }
      }
    };

    void loadSheets();

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  const years = getUniqueYears(sheets);
  const availableMonths = getMonthsForYear(sheets, selectedYear ? Number(selectedYear) : undefined);
  const availableRegions = getRegionsForPeriod(
    sheets,
    selectedYear ? Number(selectedYear) : undefined,
    selectedMonth ? Number(selectedMonth) : undefined,
  );

  useEffect(() => {
    if (!years.length) return;

    if (!selectedYear || !years.includes(Number(selectedYear))) {
      setSelectedYear(String(years[0]));
      return;
    }

    if (!availableMonths.length) {
      if (selectedMonth) setSelectedMonth('');
      if (selectedRegion) setSelectedRegion('');
      return;
    }

    if (!selectedMonth || !availableMonths.includes(Number(selectedMonth))) {
      setSelectedMonth(String(availableMonths[0]));
      return;
    }

    if (!availableRegions.length) {
      if (selectedRegion) setSelectedRegion('');
      return;
    }

    if (!availableRegions.some((region) => normalizeRegion(region) === normalizeRegion(selectedRegion))) {
      setSelectedRegion(availableRegions[0]);
    }
  }, [availableMonths, availableRegions, selectedMonth, selectedRegion, selectedYear, years]);

  useEffect(() => {
    if (!selectedYear || !selectedMonth || !selectedRegion) {
      setReconciliation(null);
      return;
    }

    let cancelled = false;

    const loadReconciliation = async () => {
      setDataLoading(true);
      setError(null);

      try {
        const response = await fetchAttendanceReconciliation(
          Number(selectedYear),
          Number(selectedMonth),
          selectedRegion,
        );

        if (!cancelled) {
          setReconciliation(response);
        }
      } catch (err) {
        if (!cancelled) {
          setReconciliation(null);
          setError(err instanceof Error ? err.message : 'دریافت گزارش مغایرت ناموفق بود.');
        }
      } finally {
        if (!cancelled) {
          setDataLoading(false);
        }
      }
    };

    void loadReconciliation();

    return () => {
      cancelled = true;
    };
  }, [selectedMonth, selectedRegion, selectedYear, refreshKey]);

  const selectedSheet =
    sheets.find(
      (sheet) =>
        sheet.year === Number(selectedYear) &&
        sheet.month === Number(selectedMonth) &&
        normalizeRegion(sheet.region) === normalizeRegion(selectedRegion),
    ) || null;

  const regionTotal = Number(reconciliation?.region_total ?? 0);
  const contractorTotal = Number(reconciliation?.contractor_total ?? 0);
  const difference = Number(reconciliation?.difference ?? 0);
  const isMatched = Boolean(reconciliation?.is_matched);
  const selectedSheetStatus = selectedSheet?.status ?? '';

  const maxComparable = Math.max(regionTotal, contractorTotal, 1);
  const regionBarWidth = `${Math.min((regionTotal / maxComparable) * 100, 100)}%`;
  const contractorBarWidth = `${Math.min((contractorTotal / maxComparable) * 100, 100)}%`;

  const canApprove =
    Boolean(reconciliation?.is_matched) &&
    Boolean(selectedSheet) &&
    selectedSheetStatus === 'COMPANY_REP_APPROVED' &&
    actionLoading === null;
  const canReject =
    Boolean(selectedSheet) &&
    actionLoading === null &&
    !NON_REJECTABLE_STATUSES.has(selectedSheetStatus);

  const handleWorkflowAction = async (action: 'approve' | 'reject') => {
    if (!selectedSheet) {
      toast.error('برای این دوره شیت متناظر پیدا نشد.');
      return;
    }

    setActionLoading(action);
    setError(null);

    try {
      const updatedSheet = await transitionAttendanceSheet(selectedSheet.id, {
        action,
        rejection_reason:
          action === 'reject'
            ? note.trim() || 'رد در داشبورد تطبیق و مغایرت‌گیری'
            : undefined,
      });

      setSheets((current) =>
        current.map((sheet) => (sheet.id === updatedSheet.id ? { ...sheet, ...updatedSheet } : sheet)),
      );

      if (action === 'reject') {
        setNote('');
      }

      toast.success(
        action === 'approve'
          ? 'صورت‌وضعیت با موفقیت تایید شد.'
          : 'صورت‌وضعیت برای اصلاح به پیمانکار بازگردانده شد.',
      );

      setRefreshKey((current) => current + 1);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'انجام عملیات ناموفق بود.';
      setError(message);
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div dir="rtl" className="mx-auto flex w-full max-w-7xl flex-col gap-6 pb-8">
      <Card className="relative overflow-hidden border-slate-200 bg-white shadow-sm">
        <div className="absolute inset-y-0 left-0 w-1/3 bg-[radial-gradient(circle_at_top_left,rgba(59,130,246,0.18),transparent_62%)]" />
        <div className="absolute inset-y-0 right-0 w-1/3 bg-[radial-gradient(circle_at_top_right,rgba(16,185,129,0.12),transparent_65%)]" />
        <CardHeader className="relative gap-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-3 text-right">
              <div className="flex items-center justify-end gap-3">
                <Badge variant="outline" className="border-emerald-200 bg-emerald-50 text-emerald-700">
                  داشبورد تطبیق و مغایرت‌گیری
                </Badge>
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-900 text-white shadow-lg">
                  <ShieldCheck className="h-6 w-6" />
                </div>
              </div>
              <CardTitle className="text-3xl font-black tracking-tight text-slate-900">
                کنترل انطباق محاسبات منطقه با صورت‌وضعیت پیمانکار
              </CardTitle>
              <CardDescription className="max-w-3xl text-base leading-8 text-slate-600">
                این نما اختلاف مالی بین خروجی منطقه و صورت‌وضعیت ارسالی پیمانکار را برای همان سال، ماه و منطقه
                محاسبه می‌کند و فقط در حالت بدون مغایرت اجازه تایید را فعال می‌سازد.
              </CardDescription>
            </div>

            <Button
              variant="outline"
              className="gap-2 self-start border-slate-200 bg-white/90"
              onClick={() => setRefreshKey((current) => current + 1)}
              disabled={catalogueLoading || dataLoading || actionLoading !== null}
            >
              <RefreshCw className={cn('h-4 w-4', (catalogueLoading || dataLoading) && 'animate-spin')} />
              بازخوانی
            </Button>
          </div>

          <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr_1fr]">
            <label className="space-y-2 text-right">
              <span className="text-sm font-semibold text-slate-700">سال</span>
              <select
                value={selectedYear}
                onChange={(event) => setSelectedYear(event.target.value)}
                className="h-12 w-full rounded-2xl border border-slate-200 bg-white px-4 text-right text-sm shadow-sm outline-none transition focus:border-sky-400 focus:ring-4 focus:ring-sky-100"
                disabled={catalogueLoading || !years.length}
              >
                <option value="">انتخاب سال</option>
                {years.map((year) => (
                  <option key={year} value={year}>
                    {formatNumber(year)}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-2 text-right">
              <span className="text-sm font-semibold text-slate-700">ماه</span>
              <select
                value={selectedMonth}
                onChange={(event) => setSelectedMonth(event.target.value)}
                className="h-12 w-full rounded-2xl border border-slate-200 bg-white px-4 text-right text-sm shadow-sm outline-none transition focus:border-sky-400 focus:ring-4 focus:ring-sky-100"
                disabled={catalogueLoading || !availableMonths.length}
              >
                <option value="">انتخاب ماه</option>
                {availableMonths.map((month) => (
                  <option key={month} value={month}>
                    {PERSIAN_MONTHS[month] || `ماه ${formatNumber(month)}`}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-2 text-right">
              <span className="text-sm font-semibold text-slate-700">منطقه</span>
              <select
                value={selectedRegion}
                onChange={(event) => setSelectedRegion(event.target.value)}
                className="h-12 w-full rounded-2xl border border-slate-200 bg-white px-4 text-right text-sm shadow-sm outline-none transition focus:border-sky-400 focus:ring-4 focus:ring-sky-100"
                disabled={catalogueLoading || !availableRegions.length}
              >
                <option value="">انتخاب منطقه</option>
                {availableRegions.map((region) => (
                  <option key={region} value={region}>
                    {region}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-3 text-sm text-slate-500">
            <span>
              آخرین بازه انتخابی:
              {' '}
              <span className="font-semibold text-slate-900">
                {selectedRegion || '-'}
                {' / '}
                {selectedMonth ? PERSIAN_MONTHS[Number(selectedMonth)] || selectedMonth : '-'}
                {' / '}
                {selectedYear ? formatNumber(Number(selectedYear)) : '-'}
              </span>
            </span>
            {selectedSheet ? (
              <Badge variant="outline" className="border-slate-200 bg-slate-50 text-slate-700">
                وضعیت شیت: {STATUS_LABELS[selectedSheet.status] || selectedSheet.status}
              </Badge>
            ) : null}
          </div>
        </CardHeader>
      </Card>

      {error ? (
        <Alert className="border-rose-200 bg-rose-50 text-rose-900">
          <AlertTriangle className="h-4 w-4 text-rose-700" />
          <AlertTitle>خطا در دریافت یا پردازش اطلاعات</AlertTitle>
          <AlertDescription className="text-rose-800">{error}</AlertDescription>
        </Alert>
      ) : null}

      {catalogueLoading ? (
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="flex min-h-[240px] items-center justify-center">
            <div className="flex items-center gap-3 text-slate-500">
              <Loader2 className="h-5 w-5 animate-spin" />
              در حال بارگذاری فهرست دوره‌های قابل تطبیق...
            </div>
          </CardContent>
        </Card>
      ) : !years.length ? (
        <Card className="border-dashed border-slate-300 bg-slate-50 shadow-sm">
          <CardContent className="flex min-h-[240px] flex-col items-center justify-center gap-4 text-center text-slate-600">
            <ShieldAlert className="h-10 w-10 text-slate-400" />
            <div className="space-y-2">
              <p className="text-lg font-semibold text-slate-900">هیچ دوره‌ای برای مغایرت‌گیری در دسترس نیست.</p>
              <p>ابتدا فایل حضور و غیاب منطقه و صورت‌وضعیت پیمانکار را برای یک بازه مشترک بارگذاری کنید.</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {dataLoading && !reconciliation ? (
            <Card className="border-slate-200 shadow-sm">
              <CardContent className="flex min-h-[280px] items-center justify-center">
                <div className="flex items-center gap-3 text-slate-500">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  در حال محاسبه مغایرت مالی...
                </div>
              </CardContent>
            </Card>
          ) : !reconciliation ? (
            <Card className="border-slate-200 shadow-sm">
              <CardContent className="flex min-h-[240px] flex-col items-center justify-center gap-4 text-center text-slate-600">
                <ShieldAlert className="h-10 w-10 text-slate-400" />
                <div className="space-y-2">
                  <p className="text-lg font-semibold text-slate-900">برای این بازه داده‌ی قابل تطبیق پیدا نشد.</p>
                  <p>سال، ماه و منطقه را تغییر دهید یا کامل بودن هر دو فایل منطقه و پیمانکار را بررسی کنید.</p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="grid gap-4 xl:grid-cols-3">
                <MetricCard
                  title="محاسبات منطقه"
                  value={formatCurrency(regionTotal)}
                  description="جمع ستون سرانه نهایی و اضافه‌کار داده‌شده از فایل منطقه"
                  icon={Scale}
                  accentClassName="bg-gradient-to-br from-sky-600 via-blue-600 to-cyan-500"
                  iconWrapClassName="bg-white/10 text-white"
                />
                <MetricCard
                  title="صورت‌وضعیت پیمانکار"
                  value={formatCurrency(contractorTotal)}
                  description="مبلغ کل صورت‌وضعیت بر مبنای جمع ردیف‌های مالی معتبر پیمانکار"
                  icon={ReceiptText}
                  accentClassName="bg-gradient-to-br from-amber-500 via-orange-500 to-red-500"
                  iconWrapClassName="bg-white/10 text-white"
                />
                <MetricCard
                  title="مغایرت"
                  value={formatCurrency(difference)}
                  description={
                    isMatched
                      ? 'عدد اختلاف صفر است و صورت‌وضعیت از منظر مالی با محاسبات منطقه منطبق است.'
                      : 'عدد اختلاف غیرصفر است و باید پیش از تایید، بررسی و اصلاح انجام شود.'
                  }
                  icon={isMatched ? CheckCircle2 : ShieldAlert}
                  accentClassName={
                    isMatched
                      ? 'bg-gradient-to-br from-emerald-600 via-green-600 to-teal-500'
                      : 'bg-gradient-to-br from-rose-700 via-red-600 to-orange-500'
                  }
                  iconWrapClassName="bg-white/10 text-white"
                />
              </div>

              <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
                <Card className="border-slate-200 shadow-sm">
                  <CardHeader className="text-right">
                    <CardTitle className="text-xl font-bold text-slate-900">نمای تحلیلی اختلاف</CardTitle>
                    <CardDescription>
                      مقایسه دیداری مبلغ منطقه و مبلغ پیمانکار برای بازه انتخاب‌شده
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div className="space-y-4 rounded-[1.75rem] bg-slate-950 p-6 text-white shadow-xl">
                      <div className="flex items-center justify-between gap-4">
                        <div className="text-left">
                          <div className="text-xs text-white/60">وضعیت تطبیق</div>
                          <div className="mt-1 text-2xl font-black">
                            {isMatched ? 'بدون مغایرت' : 'دارای اختلاف'}
                          </div>
                        </div>
                        <Badge
                          variant="outline"
                          className={cn(
                            'border-white/15 px-3 py-1 text-sm',
                            isMatched ? 'bg-emerald-500/15 text-emerald-200' : 'bg-rose-500/15 text-rose-200',
                          )}
                        >
                          {isMatched ? 'قابل تایید' : 'نیازمند بازگشت'}
                        </Badge>
                      </div>

                      <div className="space-y-5">
                        <div className="space-y-2">
                          <div className="flex items-center justify-between gap-3 text-sm text-white/75">
                            <span>{formatCurrency(regionTotal)}</span>
                            <span>محاسبات منطقه</span>
                          </div>
                          <div className="h-3 overflow-hidden rounded-full bg-white/10">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-blue-400"
                              style={{ width: regionBarWidth }}
                            />
                          </div>
                        </div>

                        <div className="space-y-2">
                          <div className="flex items-center justify-between gap-3 text-sm text-white/75">
                            <span>{formatCurrency(contractorTotal)}</span>
                            <span>صورت‌وضعیت پیمانکار</span>
                          </div>
                          <div className="h-3 overflow-hidden rounded-full bg-white/10">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-amber-300 to-rose-300"
                              style={{ width: contractorBarWidth }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="grid gap-4 md:grid-cols-3">
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-right">
                        <div className="text-xs text-slate-500">اختلاف مطلق</div>
                        <div className="mt-2 text-lg font-bold text-slate-900">
                          {formatCurrency(Math.abs(difference))}
                        </div>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-right">
                        <div className="text-xs text-slate-500">آخرین ثبت شیت</div>
                        <div className="mt-2 text-lg font-bold text-slate-900">
                          {formatDate(selectedSheet?.created_at)}
                        </div>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-right">
                        <div className="text-xs text-slate-500">عنوان شیت</div>
                        <div className="mt-2 line-clamp-2 text-lg font-bold text-slate-900">
                          {selectedSheet?.title || '-'}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-slate-200 shadow-sm">
                  <CardHeader className="text-right">
                    <CardTitle className="text-xl font-bold text-slate-900">تصمیم نهایی حراست</CardTitle>
                    <CardDescription>
                      تایید فقط وقتی فعال می‌شود که عدد مغایرت صفر باشد و شیت در مرحله مناسب قرار داشته باشد.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-5">
                    <div
                      className={cn(
                        'rounded-[1.5rem] border p-5 text-right',
                        isMatched
                          ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                          : 'border-rose-200 bg-rose-50 text-rose-900',
                      )}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="text-left">
                          {isMatched ? (
                            <CheckCircle2 className="h-6 w-6 text-emerald-600" />
                          ) : (
                            <ShieldAlert className="h-6 w-6 text-rose-600" />
                          )}
                        </div>
                        <div className="space-y-2">
                          <div className="text-lg font-bold">
                            {isMatched ? 'تطبیق کامل انجام شد' : 'مغایرت مالی شناسایی شد'}
                          </div>
                          <p className="text-sm leading-7">
                            {isMatched
                              ? 'مبالغ دو طرف برابر است و امکان عبور به مرحله بعدی فرآیند فعال شده است.'
                              : 'تا زمان رفع اختلاف، تایید نهایی باید متوقف بماند و صورت‌وضعیت برای اصلاح بازگردد.'}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-2 text-right">
                      <label className="text-sm font-semibold text-slate-700" htmlFor="reconciliation-note">
                        توضیح برای ارجاع به پیمانکار
                      </label>
                      <Textarea
                        id="reconciliation-note"
                        value={note}
                        onChange={(event) => setNote(event.target.value)}
                        placeholder="در صورت رد، علت مغایرت یا توضیح اصلاحی را ثبت کنید."
                        className="min-h-28 rounded-2xl border-slate-200 bg-slate-50"
                      />
                    </div>

                    <div className="space-y-3">
                      <Button
                        className="h-12 w-full gap-2 rounded-2xl bg-emerald-600 text-base font-bold hover:bg-emerald-700"
                        disabled={!canApprove}
                        onClick={() => void handleWorkflowAction('approve')}
                      >
                        {actionLoading === 'approve' ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <CheckCircle2 className="h-4 w-4" />
                        )}
                        تایید و ارسال به مالی
                      </Button>

                      <Button
                        variant="destructive"
                        className="h-12 w-full gap-2 rounded-2xl text-base font-bold"
                        disabled={!canReject}
                        onClick={() => void handleWorkflowAction('reject')}
                      >
                        {actionLoading === 'reject' ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <XCircle className="h-4 w-4" />
                        )}
                        رد صورت‌وضعیت
                      </Button>
                    </div>

                    <div className="space-y-2 rounded-2xl bg-slate-50 p-4 text-right text-sm leading-7 text-slate-600">
                      <div>
                        شرط تایید:
                        {' '}
                        <span className="font-semibold text-slate-900">
                          مغایرت صفر و وضعیت شیت = تایید نماینده شرکت
                        </span>
                      </div>
                      <div>
                        وضعیت فعلی:
                        {' '}
                        <span className="font-semibold text-slate-900">
                          {selectedSheet ? STATUS_LABELS[selectedSheet.status] || selectedSheet.status : 'نامشخص'}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </>
      )}

      {dataLoading && reconciliation && !catalogueLoading ? (
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="flex items-center justify-center py-8 text-slate-500">
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin" />
              در حال محاسبه مغایرت مالی...
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
