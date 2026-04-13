import React, { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, FileSpreadsheet, Loader2, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import { useNavigate, useParams } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Textarea } from '../../components/ui/textarea';
import {
  AttendanceSheet,
  fetchAttendanceSheet,
  transitionAttendanceSheet,
} from '../../services/attendance';
import { useUIStore } from '../../stores/useUIStore';
import { cn } from '../../components/ui/utils';

const STATUS_LABELS: Record<string, string> = {
  DRAFT: 'پیش‌نویس',
  CREATOR_APPROVED: 'تایید ثبت‌کننده',
  COMPANY_REP_APPROVED: 'تایید نماینده',
  SECURITY_APPROVED: 'تایید حراست',
  GM_APPROVED: 'تایید نهایی',
  NEEDS_CORRECTION: 'نیازمند اصلاح',
  REJECTED: 'رد شده',
};

function formatDate(value?: string) {
  if (!value) return '-';
  return new Intl.DateTimeFormat('fa-IR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function formatNumber(value?: string | number | null) {
  if (value === null || value === undefined || value === '') return '-';
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return new Intl.NumberFormat('fa-IR').format(numeric);
}

export default function AttendanceDetail() {
  const params = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [sheet, setSheet] = useState<AttendanceSheet | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [submittingAction, setSubmittingAction] = useState<'approve' | 'reject' | null>(null);

  const { isSidebarExpanded } = useUIStore();

  const sheetId = Number(params.id);

  const loadSheet = async () => {
    if (!sheetId) {
      setError('شناسه شیت معتبر نیست.');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchAttendanceSheet(sheetId);
      setSheet(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'دریافت جزئیات شیت ناموفق بود.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadSheet();
  }, [sheetId]);

  const handleTransition = async (action: 'approve' | 'reject') => {
    if (!sheet) return;

    if (action === 'reject' && !rejectionReason.trim()) {
      const message = 'ثبت دلیل رد الزامی است.';
      setError(message);
      toast.error(message);
      return;
    }

    setSubmittingAction(action);
    setError(null);

    try {
      const updatedSheet = await transitionAttendanceSheet(sheet.id, {
        action,
        rejection_reason: action === 'reject' ? rejectionReason.trim() : undefined,
      });
      setSheet(updatedSheet);
      if (action === 'reject') {
        setRejectionReason('');
      }
      toast.success(action === 'approve' ? 'شیت با موفقیت تایید شد.' : 'شیت با موفقیت رد شد.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'انجام عملیات ناموفق بود.';
      setError(message);
      toast.error(message);
    } finally {
      setSubmittingAction(null);
    }
  };

  if (isLoading) {
    return (
      <Card className="border-slate-200 shadow-sm">
        <CardContent className="flex min-h-80 items-center justify-center">
          <div className="flex items-center gap-3 text-slate-500">
            <Loader2 className="h-5 w-5 animate-spin" />
            در حال بارگذاری جزئیات شیت...
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error && !sheet) {
    return (
      <Card className="border-slate-200 shadow-sm">
        <CardContent className="py-8">
          <Alert className="border-rose-200 bg-rose-50 text-rose-900">
            <AlertCircle className="h-4 w-4 text-rose-700" />
            <AlertTitle>خطا در دریافت اطلاعات</AlertTitle>
            <AlertDescription className="space-y-4 text-rose-800">
              <p>{error}</p>
              <div className="flex justify-start gap-2">
                <Button variant="outline" onClick={() => void loadSheet()}>
                  تلاش مجدد
                </Button>
                <Button variant="ghost" onClick={() => navigate('/attendance/inbox')}>
                  بازگشت به کارتابل
                </Button>
              </div>
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!sheet) {
    return null;
  }

  return (
    <div className="space-y-6 pb-36">
      <Card className="border-slate-200 shadow-sm">
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div className="space-y-2 text-right">
            <CardTitle className="text-xl font-bold text-slate-900">{sheet.title}</CardTitle>
            <CardDescription className="text-sm text-slate-500">
              جزئیات فایل بارگذاری‌شده و ردیف‌های استخراج‌شده از اکسل
            </CardDescription>
          </div>
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-50 text-sky-700">
            <FileSpreadsheet className="h-6 w-6" />
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl bg-slate-50 p-4 text-right">
            <div className="text-xs text-slate-500">منطقه</div>
            <div className="mt-2 font-medium text-slate-900">{sheet.region || '-'}</div>
          </div>
          <div className="rounded-2xl bg-slate-50 p-4 text-right">
            <div className="text-xs text-slate-500">نام فایل</div>
            <div className="mt-2 truncate font-medium text-slate-900">{sheet.original_filename}</div>
          </div>
          <div className="rounded-2xl bg-slate-50 p-4 text-right">
            <div className="text-xs text-slate-500">تعداد ردیف</div>
            <div className="mt-2 font-mono text-lg font-semibold text-slate-900">{sheet.row_count}</div>
          </div>
          <div className="rounded-2xl bg-slate-50 p-4 text-right">
            <div className="text-xs text-slate-500">وضعیت</div>
            <div className="mt-2">
              <Badge variant="outline" className="bg-white text-slate-700">
                {STATUS_LABELS[sheet.status] || sheet.status}
              </Badge>
            </div>
            <div className="mt-2 text-xs text-slate-500">{formatDate(sheet.created_at)}</div>
          </div>
        </CardContent>
      </Card>

      {error ? (
        <Alert className="border-rose-200 bg-rose-50 text-rose-900">
          <AlertCircle className="h-4 w-4 text-rose-700" />
          <AlertTitle>خطا در انجام عملیات</AlertTitle>
          <AlertDescription className="text-rose-800">{error}</AlertDescription>
        </Alert>
      ) : null}

      <Card className="border-slate-200 shadow-sm">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-slate-900">ردیف‌های اکسل</CardTitle>
          <CardDescription>خروجی parse‌شده فایل برای بازبینی قبل از تایید یا رد.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto w-full rounded-2xl border border-slate-200">
            <Table>
              <TableHeader className="bg-slate-100/80">
                <TableRow>
                  <TableHead className="whitespace-nowrap text-right">ردیف</TableHead>
                  <TableHead className="whitespace-nowrap text-right">موقعیت</TableHead>
                  <TableHead className="whitespace-nowrap text-right">نام و نام خانوادگی</TableHead>
                  <TableHead className="whitespace-nowrap text-right">نام پدر</TableHead>
                  <TableHead className="whitespace-nowrap text-right">کد ملی</TableHead>
                  <TableHead className="whitespace-nowrap text-right">وضعیت تاهل</TableHead>
                  <TableHead className="whitespace-nowrap text-right">تعداد فرزند</TableHead>
                  <TableHead className="whitespace-nowrap text-right">تاریخ شروع</TableHead>
                  <TableHead className="whitespace-nowrap text-right">میانگین سرانه</TableHead>
                  <TableHead className="whitespace-nowrap text-right">حداقل ساعت</TableHead>
                  <TableHead className="whitespace-nowrap text-right">حداکثر ساعت</TableHead>
                  <TableHead className="whitespace-nowrap text-right">کارکرد ماهانه</TableHead>
                  <TableHead className="whitespace-nowrap text-right">غیبت</TableHead>
                  <TableHead className="whitespace-nowrap text-right">جایگزین اضافه کار</TableHead>
                  <TableHead className="whitespace-nowrap text-right">ساعت اضافه کار</TableHead>
                  <TableHead className="whitespace-nowrap text-right">جمع سرانه</TableHead>
                  <TableHead className="whitespace-nowrap text-right">جمع اضافه کار</TableHead>
                  <TableHead className="whitespace-nowrap text-right">مانده کارکرد</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sheet.records.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={18} className="py-16 text-center text-slate-500">
                      هیچ ردیفی از فایل استخراج نشده است.
                    </TableCell>
                  </TableRow>
                ) : (
                  sheet.records.map((record) => (
                    <TableRow key={record.id}>
                      <TableCell className="whitespace-nowrap text-right font-mono">{record.row_number}</TableCell>
                      <TableCell className="whitespace-nowrap text-right">{record.location || '-'}</TableCell>
                      <TableCell className="whitespace-nowrap text-right font-medium text-slate-900">
                        {record.full_name}
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-right">{record.father_name || '-'}</TableCell>
                      <TableCell className="whitespace-nowrap text-right font-mono">{record.national_id || '-'}</TableCell>
                      <TableCell className="whitespace-nowrap text-right">{record.marital_status || '-'}</TableCell>
                      <TableCell className="whitespace-nowrap text-right">{formatNumber(record.children_count)}</TableCell>
                      <TableCell className="whitespace-nowrap text-right font-mono">{record.start_date || '-'}</TableCell>
                      <TableCell className="whitespace-nowrap text-right">{formatNumber(record.average_per_capita)}</TableCell>
                      <TableCell className="whitespace-nowrap text-right">{formatNumber(record.min_paid_hours)}</TableCell>
                      <TableCell className="whitespace-nowrap text-right">{formatNumber(record.max_paid_hours)}</TableCell>
                      <TableCell className="whitespace-nowrap text-right">{formatNumber(record.monthly_performance_days)}</TableCell>
                      <TableCell className="whitespace-nowrap text-right">{formatNumber(record.monthly_absence_days)}</TableCell>
                      <TableCell className="whitespace-nowrap text-right">{formatNumber(record.overtime_replacement)}</TableCell>
                      <TableCell className="whitespace-nowrap text-right">{formatNumber(record.overtime_hours)}</TableCell>
                      <TableCell className="whitespace-nowrap text-right font-medium text-emerald-700">
                        {formatNumber(record.total_average_per_capita)}
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-right font-medium text-sky-700">
                        {formatNumber(record.total_overtime_given)}
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-right font-medium">
                        {record.performance_balance || '-'}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <div
        className={cn(
          "fixed bottom-0 left-0 z-40 border-t border-slate-200 bg-white/95 shadow-lg backdrop-blur transition-all duration-300",
          isSidebarExpanded ? "right-72" : "right-20"
        )}
      >
        <div className="flex w-full flex-col gap-4 px-6 py-4 lg:px-10">
          <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
            <div className="space-y-2 text-right">
              <label className="text-sm font-medium text-slate-700" htmlFor="attendance-rejection-reason">
                دلیل رد
              </label>
              <Textarea
                id="attendance-rejection-reason"
                value={rejectionReason}
                onChange={(event) => setRejectionReason(event.target.value)}
                placeholder="در صورت رد، دلیل را وارد کنید."
                className="min-h-24 bg-slate-50"
              />
            </div>
            <div className="flex items-center justify-start gap-3">
              <Button
                variant="destructive"
                disabled={submittingAction !== null}
                onClick={() => void handleTransition('reject')}
                className="min-w-28"
              >
                {submittingAction === 'reject' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <XCircle className="h-4 w-4" />
                )}
                رد
              </Button>
              <Button
                disabled={submittingAction !== null}
                onClick={() => void handleTransition('approve')}
                className="min-w-28 bg-emerald-600 hover:bg-emerald-700"
              >
                {submittingAction === 'approve' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-4 w-4" />
                )}
                تایید
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
