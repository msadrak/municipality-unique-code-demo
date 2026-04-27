import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  Loader2,
  Paperclip,
  RefreshCw,
  ShieldCheck,
  TriangleAlert,
  Edit,
  History,
  X,
  Save,
} from 'lucide-react';
import { toast } from 'sonner';

import { AUTHORIZED_REGIONS } from '../../constants/regions';
import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Textarea } from '../../components/ui/textarea';
import { cn } from '../../components/ui/utils';
import {
  approveWorkPeriodAggregation,
  fetchWorkPeriodStatus,
  WorkPeriodStatus,
  fetchRegionAttendanceRecords,
  updateAttendanceRecord,
  fetchAttendanceAuditLogs,
  AttendanceRecord,
  AttendanceAuditLog,
  rejectAttendanceSheet,
  fetchSheetAttachments,
  AttachmentMeta,
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

const WORKFLOW_LABELS: Record<string, string> = {
  DRAFT_REGIONS: 'در حال دریافت فایل مناطق',
  PENDING_SECURITY_AGGREGATION: 'آماده تجمیع حراست',
  PENDING_CONTRACTOR_STATEMENT: 'در انتظار ارسال پیمانکار',
  PENDING_SECURITY_AUDIT: 'در انتظار ممیزی حراست',
  FINAL_APPROVED: 'تایید نهایی',
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

function formatNumber(value: number) {
  return new Intl.NumberFormat('fa-IR', {
    maximumFractionDigits: 0,
  }).format(value);
}

function formatOptionalNumber(value?: number | null) {
  if (value === null || value === undefined) {
    return '0';
  }

  return new Intl.NumberFormat('fa-IR', {
    maximumFractionDigits: 2,
  }).format(value);
}

function getSelectableYears(currentYear: number) {
  return Array.from({ length: 5 }, (_, index) => currentYear - 2 + index);
}

function isStatusPastAggregation(status?: string) {
  return status === 'PENDING_CONTRACTOR_STATEMENT' || status === 'PENDING_SECURITY_AUDIT' || status === 'FINAL_APPROVED';
}

const EDITABLE_NUMERIC_FIELDS = [
  'monthly_performance_days',
  'monthly_absence_days',
  'overtime_replacement',
  'overtime_hours',
  'total_overtime_given',
] as const;

type EditableNumericField = (typeof EDITABLE_NUMERIC_FIELDS)[number];

const EMPTY_EDITING_VALUES: Record<EditableNumericField, string> = {
  monthly_performance_days: '',
  monthly_absence_days: '',
  overtime_replacement: '',
  overtime_hours: '',
  total_overtime_given: '',
};

const EDITABLE_FIELD_LABELS: Record<EditableNumericField, string> = {
  monthly_performance_days: 'کارکرد ماهانه',
  monthly_absence_days: 'غیبت',
  overtime_replacement: 'جایگزین اضافه کار',
  overtime_hours: 'اضافه کار',
  total_overtime_given: 'کل اضافه کار پرداختی',
};

function toDraftValue(value?: number | null) {
  if (value === null || value === undefined) {
    return '';
  }
  return String(value);
}

function parseDraftNumber(value: string): number | null | undefined {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed.replace(/,/g, ''));
  return Number.isNaN(parsed) ? undefined : parsed;
}

function areNumericValuesEqual(left: number | null | undefined, right: number | null | undefined) {
  const normalizedLeft = left ?? null;
  const normalizedRight = right ?? null;

  if (normalizedLeft === null && normalizedRight === null) {
    return true;
  }

  if (normalizedLeft === null || normalizedRight === null) {
    return false;
  }

  return Number(normalizedLeft) === Number(normalizedRight);
}
interface RegionListCardProps {
  title: string;
  description: string;
  count: number;
  regions: string[];
  emptyLabel: string;
  tone: 'success' | 'warning';
  onRegionClick?: (region: string) => void;
}

function RegionListCard({
  title,
  description,
  count,
  regions,
  emptyLabel,
  tone,
  onRegionClick,
}: RegionListCardProps) {
  const isSuccess = tone === 'success';

  return (
    <Card className="border-none bg-white shadow-lg overflow-hidden">
      <CardHeader className="text-right pb-4">
        <div className="flex items-center justify-between gap-3">
          <Badge variant="secondary" className={cn(
            "font-black px-3 py-1 border-none",
            isSuccess ? "bg-emerald-50 text-emerald-700" : "bg-orange-50 text-orange-700"
          )}>
            {formatNumber(count)}
          </Badge>
          <div className="space-y-1">
            <CardTitle className="text-lg font-black text-slate-900">{title}</CardTitle>
            <CardDescription className="text-xs font-medium text-slate-400">{description}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {regions.length ? (
          <div className="grid gap-2 sm:grid-cols-2">
            {regions.map((region) => {
              const content = (
                <>
                  <span className="text-sm font-bold text-slate-700">{region}</span>
                  <div className={cn(
                    "h-2 w-2 rounded-full",
                    isSuccess ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.5)]"
                  )} />
                </>
              );
              const className = "flex items-center justify-between gap-3 rounded-2xl border border-slate-50 bg-slate-50/50 px-4 py-3 text-right transition-all hover:bg-white hover:shadow-md hover:border-white group";
              
              if (onRegionClick) {
                return (
                  <button key={region} className={className} onClick={() => onRegionClick(region)}>
                    {content}
                  </button>
                );
              }
              return (
                <div key={region} className={className}>
                  {content}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-100 bg-slate-50/30 px-4 py-10 text-center">
            <p className="text-sm font-medium text-slate-300">{emptyLabel}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
export default function AggregationDashboard() {
  const currentPeriod = useMemo(() => getCurrentPersianPeriod(), []);
  const [selectedYear, setSelectedYear] = useState(String(currentPeriod.year));
  const [selectedMonth, setSelectedMonth] = useState(String(currentPeriod.month));
  const [statusData, setStatusData] = useState<WorkPeriodStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isApproving, setIsApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  // Large Modal States
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
  const [selectedSheetId, setSelectedSheetId] = useState<number | null>(null);
  const [regionRecords, setRegionRecords] = useState<AttendanceRecord[]>([]);
  const [isRecordsLoading, setIsRecordsLoading] = useState(false);

  const [editingRowId, setEditingRowId] = useState<number | null>(null);
  const [editingValues, setEditingValues] = useState<Record<EditableNumericField, string>>({ ...EMPTY_EDITING_VALUES });
  const [isSavingRow, setIsSavingRow] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Partial<Record<EditableNumericField, string>>>({});

  const [auditLogs, setAuditLogs] = useState<AttendanceAuditLog[]>([]);
  const [isAuditModalOpen, setIsAuditModalOpen] = useState(false);
  const [isAuditLoading, setIsAuditLoading] = useState(false);
  const [isRejectDialogOpen, setIsRejectDialogOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [isRejecting, setIsRejecting] = useState(false);

  const [sheetAttachments, setSheetAttachments] = useState<AttachmentMeta[]>([]);
  const [isAttachmentsLoading, setIsAttachmentsLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const loadStatus = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetchWorkPeriodStatus(Number(selectedYear), Number(selectedMonth));
        if (!cancelled) {
          setStatusData(response);
        }
      } catch (err) {
        if (!cancelled) {
          setStatusData(null);
          setError(err instanceof Error ? err.message : 'دریافت وضعیت تجمیع ناموفق بود.');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void loadStatus();

    return () => {
      cancelled = true;
    };
  }, [refreshKey, selectedMonth, selectedYear]);

  const yearOptions = useMemo(() => getSelectableYears(currentPeriod.year), [currentPeriod.year]);
  const uploadedCount = statusData?.total_uploaded ?? 0;
  const totalRegions = AUTHORIZED_REGIONS.length;
  const progressPercentage = Math.round((uploadedCount / totalRegions) * 100);
  const workflowStatus = statusData?.status ?? 'DRAFT_REGIONS';
  const approvalDisabled = isApproving || isLoading || isStatusPastAggregation(workflowStatus);

  const resetInlineEditing = () => {
    setEditingRowId(null);
    setEditingValues({ ...EMPTY_EDITING_VALUES });
    setIsSavingRow(false);
    setValidationErrors({});
  };

  const loadRegionRecords = async (region: string) => {
    setIsRecordsLoading(true);
    try {
      const records = await fetchRegionAttendanceRecords(Number(selectedYear), Number(selectedMonth), region);
      setRegionRecords(records);
      setSelectedSheetId(records[0]?.sheet_id ?? null);
      return records;
    } catch (err) {
      toast.error('دریافت اطلاعات حضور و غیاب ناموفق بود.');
      return [];
    } finally {
      setIsRecordsLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!statusData) return;

    if (
      statusData.missing_regions.length > 0 &&
      !window.confirm(
        `هنوز ${formatNumber(statusData.missing_regions.length)} واحد فایل خود را ارسال نکرده‌اند. آیا از تایید نهایی و ادامه فرایند مطمئن هستید؟`,
      )
    ) {
      return;
    }

    setIsApproving(true);
    setError(null);

    try {
      const response = await approveWorkPeriodAggregation(Number(selectedYear), Number(selectedMonth));
      toast.success('تجمیع کارکرد مناطق تایید شد.');
      toast.message(response.message);
      setRefreshKey((current) => current + 1);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'تایید نهایی تجمیع ناموفق بود.';
      setError(message);
      toast.error(message);
    } finally {
      setIsApproving(false);
    }
  };

  const handleRegionClick = async (region: string) => {
    setSelectedRegion(region);
    setSelectedSheetId(null);
    resetInlineEditing();
    setIsModalOpen(true);
    await loadRegionRecords(region);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedRegion(null);
    setSelectedSheetId(null);
    setRegionRecords([]);
    setSheetAttachments([]);
    resetInlineEditing();
  };

  const handleHistoryClick = async (recordId: number) => {
    setIsAuditModalOpen(true);
    setIsAuditLoading(true);
    try {
      const logs = await fetchAttendanceAuditLogs(recordId);
      setAuditLogs(logs);
    } catch (err) {
      toast.error('دریافت تاریخچه ناموفق بود.');
    } finally {
      setIsAuditLoading(false);
    }
  };

  const handleViewAttachments = async () => {
    if (!selectedSheetId) return;
    setIsAttachmentsLoading(true);
    try {
      const list = await fetchSheetAttachments(selectedSheetId);
      setSheetAttachments(list);
      toast.success(`${list.length} پیوست یافت شد.`);
    } catch {
      toast.error('دریافت پیوست‌ها ناموفق بود.');
    } finally {
      setIsAttachmentsLoading(false);
    }
  };

  const startInlineEditing = (record: AttendanceRecord) => {
    setEditingRowId(record.id);
    setEditingValues({
      monthly_performance_days: toDraftValue(record.monthly_performance_days),
      monthly_absence_days: toDraftValue(record.monthly_absence_days),
      overtime_replacement: toDraftValue(record.overtime_replacement),
      overtime_hours: toDraftValue(record.overtime_hours),
      total_overtime_given: toDraftValue(record.total_overtime_given),
    });
    setValidationErrors({});
  };

  const updateInlineField = (field: EditableNumericField, value: string) => {
    setEditingValues((current) => ({
      ...current,
      [field]: value,
    }));
    
    if (validationErrors[field]) {
      setValidationErrors((current) => {
        const updated = { ...current };
        delete updated[field];
        return updated;
      });
    }
  };

  const validateFields = (): boolean => {
    const errors: Partial<Record<EditableNumericField, string>> = {};
    
    for (const field of EDITABLE_NUMERIC_FIELDS) {
      const parsedValue = parseDraftNumber(editingValues[field]);
      if (parsedValue === undefined) {
        errors[field] = 'مقدار معتبر نیست';
      }
    }
    
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSaveInlineEdit = async (record: AttendanceRecord) => {
    if (!validateFields()) {
      toast.error('لطفاً خطاهای فرم را برطرف کنید.');
      return;
    }

    const payload: Partial<AttendanceRecord> = {};

    for (const field of EDITABLE_NUMERIC_FIELDS) {
      const parsedValue = parseDraftNumber(editingValues[field]);

      if (!areNumericValuesEqual(record[field], parsedValue)) {
        payload[field] = parsedValue;
      }
    }

    if (Object.keys(payload).length === 0) {
      toast.message('تغییری برای ذخیره وجود ندارد.');
      resetInlineEditing();
      return;
    }

    setIsSavingRow(true);
    try {
      await updateAttendanceRecord(record.id, payload);
      toast.success('رکورد با موفقیت به‌روزرسانی شد.');
      resetInlineEditing();

      if (selectedRegion) {
        await loadRegionRecords(selectedRegion);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'به‌روزرسانی رکورد ناموفق بود.';
      toast.error(message);
    } finally {
      setIsSavingRow(false);
    }
  };

  const submitRejectSheet = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSheetId) {
      toast.error('شناسه شیت منطقه پیدا نشد.');
      return;
    }

    if (!rejectionReason.trim()) {
      toast.error('لطفاً دلیل رد را وارد کنید.');
      return;
    }

    setIsRejecting(true);
    try {
      await rejectAttendanceSheet(selectedSheetId, rejectionReason);
      toast.success('فایل رد شد و به منطقه ارجاع داده شد.');
      setIsRejectDialogOpen(false);
      setRejectionReason('');
      handleCloseModal();
      setRefreshKey((current) => current + 1);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'رد فایل ناموفق بود.';
      toast.error(message);
    } finally {
      setIsRejecting(false);
    }
  };
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-50 p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-black text-slate-900">تجمیع کارکرد مناطق</h1>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setRefreshKey((current) => current + 1)}
            disabled={isLoading}
            className="rounded-full"
          >
            <RefreshCw className={cn('h-5 w-5', isLoading && 'animate-spin')} />
          </Button>
        </div>

        <Card className="border-none bg-white shadow-lg">
          <CardHeader className="text-right">
            <CardTitle className="text-lg font-black text-slate-900">انتخاب دوره</CardTitle>
            <CardDescription className="text-xs font-medium text-slate-400">
              سال و ماه مورد نظر را انتخاب کنید
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-4 sm:flex-row">
              <div className="flex-1 space-y-2 text-right">
                <Label htmlFor="year-select" className="text-sm font-bold text-slate-700">
                  سال
                </Label>
                <Select value={selectedYear} onValueChange={setSelectedYear}>
                  <SelectTrigger id="year-select" className="rounded-xl border-slate-200 bg-slate-50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {yearOptions.map((year) => (
                      <SelectItem key={year} value={String(year)}>
                        {formatNumber(year)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex-1 space-y-2 text-right">
                <Label htmlFor="month-select" className="text-sm font-bold text-slate-700">
                  ماه
                </Label>
                <Select value={selectedMonth} onValueChange={setSelectedMonth}>
                  <SelectTrigger id="month-select" className="rounded-xl border-slate-200 bg-slate-50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(MONTH_LABELS).map(([monthNumber, monthLabel]) => (
                      <SelectItem key={monthNumber} value={monthNumber}>
                        {monthLabel}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {error && (
          <Alert variant="destructive" className="border-rose-200 bg-rose-50">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>خطا</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
          </div>
        ) : statusData ? (
          <>
            <Card className="border-none bg-gradient-to-br from-sky-500 to-blue-600 text-white shadow-xl">
              <CardHeader className="text-right">
                <div className="flex items-center justify-between">
                  <Badge className="bg-white/20 text-white border-none font-black px-3 py-1">
                    {WORKFLOW_LABELS[workflowStatus] || workflowStatus}
                  </Badge>
                  <CardTitle className="text-xl font-black">وضعیت فرایند</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between text-right">
                  <span className="text-3xl font-black">{formatNumber(uploadedCount)}</span>
                  <span className="text-sm font-medium opacity-90">از {formatNumber(totalRegions)} منطقه</span>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-white/20">
                  <div
                    className="h-full rounded-full bg-white shadow-lg transition-all duration-500"
                    style={{ width: `${progressPercentage}%` }}
                  />
                </div>
                <div className="flex items-center justify-between text-xs opacity-90">
                  <span>{formatNumber(progressPercentage)}٪ تکمیل</span>
                  <span>{formatNumber(totalRegions - uploadedCount)} منطقه باقیمانده</span>
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-6 lg:grid-cols-2">
              <RegionListCard
                title="مناطق ارسال‌کننده"
                description="واحدهایی که فایل خود را ارسال کرده‌اند"
                count={statusData.uploaded_regions.length}
                regions={statusData.uploaded_regions}
                emptyLabel="هنوز هیچ منطقه‌ای فایل ارسال نکرده است"
                tone="success"
                onRegionClick={handleRegionClick}
              />
              <RegionListCard
                title="مناطق باقیمانده"
                description="واحدهایی که هنوز فایل ارسال نکرده‌اند"
                count={statusData.missing_regions.length}
                regions={statusData.missing_regions}
                emptyLabel="همه مناطق فایل خود را ارسال کرده‌اند"
                tone="warning"
              />
            </div>

            <Card className="border-none bg-white shadow-lg">
              <CardContent className="pt-6">
                <Button
                  onClick={() => void handleApprove()}
                  disabled={approvalDisabled}
                  className="w-full rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 py-6 text-lg font-black shadow-lg hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50"
                >
                  {isApproving ? (
                    <>
                      <Loader2 className="ml-2 h-5 w-5 animate-spin" />
                      در حال پردازش...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="ml-2 h-5 w-5" />
                      تایید نهایی و ارسال به پیمانکار
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          </>
        ) : (
          <Alert className="border-amber-200 bg-amber-50">
            <TriangleAlert className="h-4 w-4 text-amber-600" />
            <AlertTitle className="text-amber-900">اطلاعاتی یافت نشد</AlertTitle>
            <AlertDescription className="text-amber-700">
              برای دوره انتخاب‌شده اطلاعاتی موجود نیست.
            </AlertDescription>
          </Alert>
        )}
      </div>
      {/* Large Centered Modal for Region Records */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="relative w-[95vw] max-w-7xl h-[90vh] bg-white dark:bg-slate-900 rounded-2xl shadow-2xl flex flex-col">
            {/* Fixed Header */}
            <div className="flex-shrink-0 border-b border-slate-200 dark:border-slate-700 px-8 py-6">
              <div className="flex items-center justify-between">
                <button
                  onClick={handleCloseModal}
                  className="rounded-full p-2 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  disabled={isSavingRow}
                >
                  <X className="h-6 w-6 text-slate-600 dark:text-slate-400" />
                </button>
                <div className="text-right">
                  <h2 className="text-2xl font-black text-slate-900 dark:text-white">
                    کارکرد منطقه {selectedRegion}
                  </h2>
                  <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                    لیست کامل کارکرد پرسنل ثبت شده در این منطقه
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between gap-3 mt-6 flex-wrap">
                <Button
                  variant="destructive"
                  className="rounded-xl gap-2"
                  disabled={!selectedSheetId || isRecordsLoading || isSavingRow}
                  onClick={() => setIsRejectDialogOpen(true)}
                >
                  <X className="h-4 w-4" />
                  رد فایل و ارجاع به منطقه
                </Button>
                <Button
                  variant="outline"
                  className="gap-2 rounded-xl border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100"
                  disabled={!selectedSheetId || isRecordsLoading}
                  onClick={() => void handleViewAttachments()}
                >
                  {isAttachmentsLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Paperclip className="h-4 w-4" />
                  )}
                  مستندات ({sheetAttachments.length})
                </Button>
              </div>
            </div>

            {/* Scrollable Body */}
            <div className="flex-1 overflow-y-auto px-8 py-6">
              {isRecordsLoading ? (
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="h-12 w-12 animate-spin text-slate-500" />
                </div>
              ) : regionRecords.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <p className="text-lg text-slate-500 dark:text-slate-400">هیچ رکوردی یافت نشد</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Records Table */}
                  <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-hidden">
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader className="bg-slate-100 dark:bg-slate-700 sticky top-0">
                          <TableRow>
                            <TableHead className="text-right font-bold">ردیف</TableHead>
                            <TableHead className="text-right font-bold">نام و نام خانوادگی</TableHead>
                            <TableHead className="text-right font-bold">کدملی</TableHead>
                            <TableHead className="text-right font-bold">کارکرد ماهانه (روز)</TableHead>
                            <TableHead className="text-right font-bold">غیبت (روز)</TableHead>
                            <TableHead className="text-right font-bold">جایگزین اضافه کار</TableHead>
                            <TableHead className="text-right font-bold">اضافه کار (ساعت)</TableHead>
                            <TableHead className="text-right font-bold">کل اضافه کار پرداختی</TableHead>
                            <TableHead className="text-left font-bold w-56">عملیات</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {regionRecords.map((r) => (
                            <TableRow 
                              key={r.id} 
                              className={cn(
                                "transition-colors",
                                editingRowId === r.id ? "bg-blue-50 dark:bg-blue-900/20" : "bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700"
                              )}
                            >
                              <TableCell className="text-right font-medium">{r.row_number}</TableCell>
                              <TableCell className="text-right font-medium">{r.full_name}</TableCell>
                              <TableCell className="text-right">{r.national_id}</TableCell>
                              
                              {/* Editable Fields */}
                              <TableCell className="min-w-32 text-right">
                                {editingRowId === r.id ? (
                                  <div className="space-y-1">
                                    <Input
                                      type="number"
                                      inputMode="decimal"
                                      step="0.01"
                                      value={editingValues.monthly_performance_days}
                                      onChange={(e) => updateInlineField('monthly_performance_days', e.target.value)}
                                      className={cn(
                                        "h-9 bg-white dark:bg-slate-900 text-right",
                                        validationErrors.monthly_performance_days && "border-rose-500"
                                      )}
                                    />
                                    {validationErrors.monthly_performance_days && (
                                      <p className="text-xs text-rose-600">{validationErrors.monthly_performance_days}</p>
                                    )}
                                  </div>
                                ) : (
                                  formatOptionalNumber(r.monthly_performance_days)
                                )}
                              </TableCell>
                              
                              <TableCell className="min-w-32 text-right">
                                {editingRowId === r.id ? (
                                  <div className="space-y-1">
                                    <Input
                                      type="number"
                                      inputMode="decimal"
                                      step="0.01"
                                      value={editingValues.monthly_absence_days}
                                      onChange={(e) => updateInlineField('monthly_absence_days', e.target.value)}
                                      className={cn(
                                        "h-9 bg-white dark:bg-slate-900 text-right",
                                        validationErrors.monthly_absence_days && "border-rose-500"
                                      )}
                                    />
                                    {validationErrors.monthly_absence_days && (
                                      <p className="text-xs text-rose-600">{validationErrors.monthly_absence_days}</p>
                                    )}
                                  </div>
                                ) : (
                                  formatOptionalNumber(r.monthly_absence_days)
                                )}
                              </TableCell>
                              
                              <TableCell className="min-w-36 text-right">
                                {editingRowId === r.id ? (
                                  <div className="space-y-1">
                                    <Input
                                      type="number"
                                      inputMode="decimal"
                                      step="0.01"
                                      value={editingValues.overtime_replacement}
                                      onChange={(e) => updateInlineField('overtime_replacement', e.target.value)}
                                      className={cn(
                                        "h-9 bg-white dark:bg-slate-900 text-right",
                                        validationErrors.overtime_replacement && "border-rose-500"
                                      )}
                                    />
                                    {validationErrors.overtime_replacement && (
                                      <p className="text-xs text-rose-600">{validationErrors.overtime_replacement}</p>
                                    )}
                                  </div>
                                ) : (
                                  formatOptionalNumber(r.overtime_replacement)
                                )}
                              </TableCell>
                              
                              <TableCell className="min-w-32 text-right">
                                {editingRowId === r.id ? (
                                  <div className="space-y-1">
                                    <Input
                                      type="number"
                                      inputMode="decimal"
                                      step="0.01"
                                      value={editingValues.overtime_hours}
                                      onChange={(e) => updateInlineField('overtime_hours', e.target.value)}
                                      className={cn(
                                        "h-9 bg-white dark:bg-slate-900 text-right",
                                        validationErrors.overtime_hours && "border-rose-500"
                                      )}
                                    />
                                    {validationErrors.overtime_hours && (
                                      <p className="text-xs text-rose-600">{validationErrors.overtime_hours}</p>
                                    )}
                                  </div>
                                ) : (
                                  formatOptionalNumber(r.overtime_hours)
                                )}
                              </TableCell>
                              
                              <TableCell className="min-w-36 text-right">
                                {editingRowId === r.id ? (
                                  <div className="space-y-1">
                                    <Input
                                      type="number"
                                      inputMode="decimal"
                                      step="0.01"
                                      value={editingValues.total_overtime_given}
                                      onChange={(e) => updateInlineField('total_overtime_given', e.target.value)}
                                      className={cn(
                                        "h-9 bg-white dark:bg-slate-900 text-right",
                                        validationErrors.total_overtime_given && "border-rose-500"
                                      )}
                                    />
                                    {validationErrors.total_overtime_given && (
                                      <p className="text-xs text-rose-600">{validationErrors.total_overtime_given}</p>
                                    )}
                                  </div>
                                ) : (
                                  formatOptionalNumber(r.total_overtime_given)
                                )}
                              </TableCell>
                              
                              {/* Action Buttons */}
                              <TableCell className="text-left">
                                <div className="flex items-center gap-2 justify-end">
                                  {editingRowId === r.id ? (
                                    <>
                                      <Button
                                        size="sm"
                                        className="gap-2 bg-emerald-600 hover:bg-emerald-700"
                                        onClick={() => void handleSaveInlineEdit(r)}
                                        disabled={isSavingRow}
                                      >
                                        {isSavingRow ? (
                                          <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                          <Save className="h-4 w-4" />
                                        )}
                                        ذخیره
                                      </Button>
                                      <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={resetInlineEditing}
                                        disabled={isSavingRow}
                                      >
                                        لغو
                                      </Button>
                                    </>
                                  ) : (
                                    <>
                                      <Button
                                        variant="outline"
                                        size="sm"
                                        className="gap-2"
                                        onClick={() => startInlineEditing(r)}
                                        disabled={editingRowId !== null}
                                      >
                                        <Edit className="h-4 w-4" />
                                        ویرایش
                                      </Button>
                                      <Button
                                        variant="outline"
                                        size="sm"
                                        className="gap-2"
                                        onClick={() => handleHistoryClick(r.id)}
                                      >
                                        <History className="h-4 w-4" />
                                        تاریخچه
                                      </Button>
                                    </>
                                  )}
                                </div>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>

                  {/* Attachments Section */}
                  {sheetAttachments.length > 0 && (
                    <div className="rounded-xl border border-amber-200 bg-amber-50 dark:bg-amber-900/20 p-6 text-right space-y-4">
                      <p className="text-base font-bold text-amber-800 dark:text-amber-200">
                        پیوست‌ها و مستندات ({sheetAttachments.length})
                      </p>
                      <ul className="space-y-3">
                        {sheetAttachments.map((att) => (
                          <li key={att.id} className="flex items-center justify-between gap-3 bg-white dark:bg-slate-800 rounded-lg p-4 border border-amber-100 dark:border-amber-800">
                            <a
                              href={`/${att.file_path}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-2 text-sm text-amber-700 dark:text-amber-300 hover:text-amber-900 dark:hover:text-amber-100 underline-offset-2 hover:underline"
                            >
                              {att.file_type === 'pdf' ? '📄' : '🖼️'}
                              {att.file_name}
                            </a>
                            <span className="text-xs text-slate-400" dir="ltr">
                              {new Date(att.created_at).toLocaleDateString('fa-IR')}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Fixed Footer */}
            <div className="flex-shrink-0 border-t border-slate-200 dark:border-slate-700 px-8 py-6">
              <div className="flex items-center justify-between gap-4">
                <Button
                  variant="outline"
                  onClick={handleCloseModal}
                  disabled={isSavingRow}
                  className="rounded-xl px-8"
                >
                  بستن
                </Button>
                <div className="text-sm text-slate-500 dark:text-slate-400">
                  {regionRecords.length > 0 && (
                    <span>تعداد رکوردها: {formatNumber(regionRecords.length)}</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      {/* Rejection Dialog */}
      <Dialog open={isRejectDialogOpen} onOpenChange={setIsRejectDialogOpen}>
        <DialogContent className="max-w-lg rtl border-rose-200 bg-white text-slate-900">
          <DialogHeader className="text-right">
            <DialogTitle className="text-rose-700">رد فایل و ارجاع به منطقه</DialogTitle>
            <DialogDescription>
              با رد این فایل، منطقه باید مجدداً فایل اصلاح‌شده را ارسال کند.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={(e) => void submitRejectSheet(e)} className="space-y-4">
            <div className="space-y-2 text-right">
              <Label htmlFor="rejection-reason" className="text-sm font-bold text-slate-700">
                دلیل رد
              </Label>
              <Textarea
                id="rejection-reason"
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="لطفاً دلیل رد فایل را به‌طور واضح توضیح دهید..."
                className="min-h-32 resize-none rounded-xl border-slate-200 bg-slate-50 text-right"
                required
              />
            </div>
            <div className="flex items-center gap-3 justify-end">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsRejectDialogOpen(false)}
                disabled={isRejecting}
                className="rounded-xl"
              >
                انصراف
              </Button>
              <Button
                type="submit"
                variant="destructive"
                disabled={isRejecting || !rejectionReason.trim()}
                className="rounded-xl gap-2"
              >
                {isRejecting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    در حال پردازش...
                  </>
                ) : (
                  <>
                    <X className="h-4 w-4" />
                    تایید رد فایل
                  </>
                )}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Audit History Dialog */}
      <Dialog open={isAuditModalOpen} onOpenChange={setIsAuditModalOpen}>
        <DialogContent className="max-w-2xl rtl border-slate-200 bg-white text-slate-900">
          <DialogHeader className="text-right">
            <DialogTitle className="text-slate-900">تاریخچه تغییرات</DialogTitle>
            <DialogDescription>
              لیست کامل تغییرات اعمال‌شده روی این رکورد
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[50vh] overflow-auto rounded-lg border bg-slate-50 p-4">
            {isAuditLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
              </div>
            ) : auditLogs.length === 0 ? (
              <div className="py-8 text-center text-slate-500 text-sm">
                هیچ تغییراتی ثبت نشده است.
              </div>
            ) : (
              <div className="space-y-4">
                {auditLogs.map((log) => (
                  <div
                    key={log.id}
                    className="bg-white border rounded-xl p-4 shadow-sm text-right space-y-2 transition-all hover:shadow-md"
                  >
                    <div className="flex items-center justify-between">
                      <Badge variant="outline" className="bg-sky-50 text-sky-700 border-sky-200">
                        {log.changed_by_full_name || 'سیستم'}
                      </Badge>
                      <span className="text-xs text-slate-500" dir="ltr">
                        {new Date(log.created_at).toLocaleString('fa-IR')}
                      </span>
                    </div>
                    <div className="text-sm font-medium text-slate-800">
                      فیلد{' '}
                      <span className="text-slate-900 font-bold bg-slate-100 px-2 py-0.5 rounded">
                        {log.field_name}
                      </span>{' '}
                      تغییر یافت:
                    </div>
                    <div className="flex items-center gap-3 text-sm flex-row-reverse" dir="ltr">
                      <span className="line-through text-rose-500 bg-rose-50 px-2 py-1 rounded">
                        {log.old_value !== null ? log.old_value : 'خالی'}
                      </span>
                      <span className="text-slate-400">←</span>
                      <span className="text-emerald-600 bg-emerald-50 px-2 py-1 rounded font-medium">
                        {log.new_value !== null ? log.new_value : 'خالی'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
