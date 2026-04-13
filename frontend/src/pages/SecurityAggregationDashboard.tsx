import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  ArrowLeft,
  Banknote,
  Building2,
  Clock3,
  RefreshCw,
  ShieldCheck,
  Users,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '../components/ui/alert';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  AttendanceAggregationItem,
  fetchAttendanceAggregation,
} from '../services/attendance';

const STATUS_STYLES: Record<string, string> = {
  DRAFT: 'bg-slate-100 text-slate-700',
  CREATOR_APPROVED: 'bg-blue-100 text-blue-700',
  COMPANY_REP_APPROVED: 'bg-violet-100 text-violet-700',
  SECURITY_APPROVED: 'bg-amber-100 text-amber-800',
  GM_APPROVED: 'bg-emerald-100 text-emerald-700',
  NEEDS_CORRECTION: 'bg-orange-100 text-orange-700',
  REJECTED: 'bg-rose-100 text-rose-700',
};

function formatDate(value?: string | null) {
  if (!value) return '-';
  return new Intl.DateTimeFormat('fa-IR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function formatNumber(value?: number | null) {
  if (value === null || value === undefined) return '۰';
  return new Intl.NumberFormat('fa-IR', {
    maximumFractionDigits: 2,
  }).format(value);
}

function formatCurrency(value?: number | null) {
  return `${formatNumber(value)} ریال`;
}

interface SummaryCardProps {
  title: string;
  value: string;
  description: string;
  icon: React.ElementType;
  accent: string;
}

function SummaryCard({ title, value, description, icon: Icon, accent }: SummaryCardProps) {
  return (
    <Card className="border-slate-200 shadow-sm">
      <CardContent className="flex items-center justify-between gap-4 p-6">
        <div className="space-y-1 text-right">
          <div className="text-sm text-slate-500">{title}</div>
          <div className="text-2xl font-bold text-slate-900">{value}</div>
          <div className="text-xs text-slate-500">{description}</div>
        </div>
        <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${accent}`}>
          <Icon className="h-6 w-6" />
        </div>
      </CardContent>
    </Card>
  );
}

export default function SecurityAggregationDashboard() {
  const navigate = useNavigate();
  const [items, setItems] = useState<AttendanceAggregationItem[]>([]);
  const [count, setCount] = useState(0);
  const [regionFilter, setRegionFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadAggregation = async () => {
      setIsLoading(true);
      setError(null);
      setItems([]);
      setCount(0);

      try {
        const response = await fetchAttendanceAggregation({
          region: regionFilter.trim() || undefined,
          status: statusFilter || undefined,
        });

        if (!cancelled) {
          setItems(response.items);
          setCount(response.count);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'دریافت گزارش تجمیعی ناموفق بود.');
          setItems([]);
          setCount(0);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void loadAggregation();

    return () => {
      cancelled = true;
    };
  }, [regionFilter, statusFilter, refreshKey]);

  const totals = items.reduce(
    (accumulator, item) => ({
      personnel: accumulator.personnel + item.total_personnel,
      workedHours: accumulator.workedHours + item.total_worked_hours,
      amount: accumulator.amount + item.total_amount,
    }),
    {
      personnel: 0,
      workedHours: 0,
      amount: 0,
    },
  );

  return (
    <div className="space-y-6">
      <Card className="border-slate-200 shadow-sm">
        <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-2 text-right">
            <div className="flex items-center justify-end gap-3">
              <Badge variant="outline" className="bg-sky-50 text-sky-700">
                {formatNumber(count)} شیت
              </Badge>
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-50 text-sky-700">
                <ShieldCheck className="h-6 w-6" />
              </div>
            </div>
            <CardTitle className="text-2xl font-bold text-slate-900">
              داشبورد تجمیعی حراست
            </CardTitle>
            <CardDescription>
              خلاصه تجمیعی شیت‌های حضور و غیاب مناطق با امکان فیلتر بر اساس نام منطقه و وضعیت گردش کار.
            </CardDescription>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <Input
              value={regionFilter}
              onChange={(event) => setRegionFilter(event.target.value)}
              placeholder="نام منطقه"
              className="text-right"
            />
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              className="flex h-10 min-w-0 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-right shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <option value="">همه وضعیت‌ها</option>
              <option value="DRAFT">پیش‌نویس</option>
              <option value="CREATOR_APPROVED">تأیید ثبت‌کننده</option>
              <option value="COMPANY_REP_APPROVED">تأیید نماینده شرکت</option>
              <option value="SECURITY_APPROVED">تأیید حراست</option>
              <option value="GM_APPROVED">تأیید نهایی</option>
              <option value="NEEDS_CORRECTION">نیازمند اصلاح</option>
              <option value="REJECTED">رد شده</option>
            </select>
            <Button
              variant="outline"
              onClick={() => setRefreshKey((current) => current + 1)}
              disabled={isLoading}
              className="gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
              بازخوانی
            </Button>
          </div>
        </CardHeader>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <SummaryCard
          title="مجموع پرسنل"
          value={formatNumber(totals.personnel)}
          description="تعداد کل ردیف‌های پرسنلی در خروجی تجمیع"
          icon={Users}
          accent="bg-blue-50 text-blue-700"
        />
        <SummaryCard
          title="مجموع کارکرد"
          value={formatNumber(totals.workedHours)}
          description="جمع کارکرد یا متراژ ثبت‌شده در شیت‌ها"
          icon={Clock3}
          accent="bg-emerald-50 text-emerald-700"
        />
        <SummaryCard
          title="مجموع مبلغ"
          value={formatCurrency(totals.amount)}
          description="جمع ستون مبلغ در همه شیت‌های فیلترشده"
          icon={Banknote}
          accent="bg-amber-50 text-amber-700"
        />
      </div>

      {error ? (
        <Alert className="border-rose-200 bg-rose-50 text-rose-900">
          <AlertCircle className="h-4 w-4 text-rose-700" />
          <AlertTitle>خطا در دریافت گزارش</AlertTitle>
          <AlertDescription className="text-rose-800">{error}</AlertDescription>
        </Alert>
      ) : null}

      <Card className="border-slate-200 shadow-sm">
        <CardHeader className="text-right">
          <CardTitle className="text-lg font-semibold text-slate-900">فهرست شیت‌های تجمیع‌شده</CardTitle>
          <CardDescription>
            هر ردیف نماینده یک شیت حضور و غیاب است و جمع ردیف‌های آن را نشان می‌دهد.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-hidden rounded-2xl border border-slate-200">
            <Table>
              <TableHeader className="bg-slate-100/80">
                <TableRow>
                  <TableHead className="text-right">#</TableHead>
                  <TableHead className="text-right">منطقه</TableHead>
                  <TableHead className="text-right">شیت</TableHead>
                  <TableHead className="text-right">تعداد پرسنل</TableHead>
                  <TableHead className="text-right">کارکرد</TableHead>
                  <TableHead className="text-right">مبلغ کل</TableHead>
                  <TableHead className="text-right">وضعیت</TableHead>
                  <TableHead className="text-right">عملیات</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={8} className="py-16 text-center text-slate-500">
                      در حال بارگذاری گزارش تجمیعی...
                    </TableCell>
                  </TableRow>
                ) : items.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="py-16 text-center text-slate-500">
                      داده‌ای برای نمایش پیدا نشد.
                    </TableCell>
                  </TableRow>
                ) : (
                  items.map((item, index) => (
                    <TableRow key={item.sheet.sheet_id}>
                      <TableCell className="text-right font-mono">{formatNumber(index + 1)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2 text-slate-700">
                          <span>{item.sheet.region_name || 'نامشخص'}</span>
                          <Building2 className="h-4 w-4 text-slate-400" />
                        </div>
                      </TableCell>
                      <TableCell className="max-w-[320px] whitespace-normal text-right">
                        <div className="font-medium text-slate-900">{item.sheet.title}</div>
                        <div className="mt-1 text-xs text-slate-500">
                          فایل: {item.sheet.original_filename}
                        </div>
                        <div className="mt-1 text-xs text-slate-500">
                          تاریخ ثبت: {formatDate(item.sheet.created_at)}
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatNumber(item.total_personnel)}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatNumber(item.total_worked_hours)}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatCurrency(item.total_amount)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Badge
                          variant="outline"
                          className={STATUS_STYLES[item.workflow_status] || 'bg-slate-100 text-slate-700'}
                        >
                          {item.workflow_status_label}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => navigate(`/attendance/${item.sheet.sheet_id}`)}
                          className="gap-2"
                        >
                          <ArrowLeft className="h-4 w-4" />
                          جزئیات
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
              {!isLoading && items.length > 0 ? (
                <TableFooter className="bg-slate-50">
                  <TableRow>
                    <TableCell colSpan={3} className="text-right font-bold text-slate-900">
                      جمع کل
                    </TableCell>
                    <TableCell className="text-right font-mono">{formatNumber(totals.personnel)}</TableCell>
                    <TableCell className="text-right font-mono">{formatNumber(totals.workedHours)}</TableCell>
                    <TableCell className="text-right font-mono">{formatCurrency(totals.amount)}</TableCell>
                    <TableCell colSpan={2} />
                  </TableRow>
                </TableFooter>
              ) : null}
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
