import React, { useEffect, useState } from 'react';
import { AlertCircle, Inbox, Loader2, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { AttendanceSheet, fetchAttendanceSheets } from '../../services/attendance';

const STATUS_STYLES: Record<string, string> = {
  DRAFT: 'bg-slate-100 text-slate-700',
  CREATOR_APPROVED: 'bg-blue-100 text-blue-700',
  COMPANY_REP_APPROVED: 'bg-violet-100 text-violet-700',
  SECURITY_APPROVED: 'bg-amber-100 text-amber-800',
  GM_APPROVED: 'bg-emerald-100 text-emerald-700',
  NEEDS_CORRECTION: 'bg-orange-100 text-orange-700',
  REJECTED: 'bg-rose-100 text-rose-700',
};

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
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

export default function AttendanceInbox() {
  const navigate = useNavigate();
  const [sheets, setSheets] = useState<AttendanceSheet[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSheets = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchAttendanceSheets();
      setSheets(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'دریافت کارتابل ناموفق بود.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadSheets();
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <Card className="border-slate-200 shadow-sm">
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div className="space-y-1 text-right">
            <CardTitle className="text-xl font-bold text-slate-900">کارتابل کارکرد مناطق</CardTitle>
            <CardDescription>
              همه شیت‌های بارگذاری‌شده را ببینید و برای بررسی جزئیات وارد صفحه هر شیت شوید.
            </CardDescription>
          </div>
          <Button variant="outline" onClick={() => void loadSheets()} disabled={isLoading}>
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            به‌روزرسانی
          </Button>
        </CardHeader>

        <CardContent className="space-y-4">
          {error ? (
            <Alert className="border-rose-200 bg-rose-50 text-rose-900">
              <AlertCircle className="h-4 w-4 text-rose-700" />
              <AlertTitle>خطا در دریافت لیست</AlertTitle>
              <AlertDescription className="text-rose-800">{error}</AlertDescription>
            </Alert>
          ) : null}

          <div className="overflow-hidden rounded-2xl border border-slate-200">
            <Table>
              <TableHeader className="bg-slate-100/80">
                <TableRow>
                  <TableHead className="text-right">عنوان</TableHead>
                  <TableHead className="text-right">منطقه</TableHead>
                  <TableHead className="text-right">تعداد ردیف</TableHead>
                  <TableHead className="text-right">وضعیت</TableHead>
                  <TableHead className="text-right">تاریخ بارگذاری</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={5} className="py-16 text-center text-slate-500">
                      <div className="flex items-center justify-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        در حال بارگذاری اطلاعات...
                      </div>
                    </TableCell>
                  </TableRow>
                ) : sheets.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="py-16 text-center text-slate-500">
                      <div className="flex flex-col items-center justify-center gap-3">
                        <Inbox className="h-8 w-8 text-slate-300" />
                        <span>هیچ شیتی ثبت نشده است.</span>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  sheets.map((sheet) => (
                    <TableRow
                      key={sheet.id}
                      className="cursor-pointer"
                      onClick={() => navigate(`/attendance/${sheet.id}`)}
                    >
                      <TableCell className="text-right font-medium text-slate-900">{sheet.title}</TableCell>
                      <TableCell className="text-right text-slate-600">{sheet.region || '-'}</TableCell>
                      <TableCell className="text-right font-mono">{sheet.row_count}</TableCell>
                      <TableCell className="text-right">
                        <Badge
                          className={STATUS_STYLES[sheet.status] || 'bg-slate-100 text-slate-700'}
                          variant="outline"
                        >
                          {STATUS_LABELS[sheet.status] || sheet.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right text-sm text-slate-500">
                        {formatDate(sheet.created_at)}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
