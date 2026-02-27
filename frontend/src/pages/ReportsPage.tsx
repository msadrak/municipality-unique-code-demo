import { useCallback, useEffect, useMemo, useState } from 'react';
import {
    AlertCircle,
    Banknote,
    FileText,
    Lock,
    Wallet,
    Download,
    Plus,
} from 'lucide-react';
import {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    Legend,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts';

import { BudgetProgressBar } from '../components/dashboard/BudgetProgressBar';
import { KPICard } from '../components/dashboard/KPICard';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '../components/ui/card';
import { Skeleton } from '../components/ui/skeleton';
import { formatAmountAbbreviated, getTodayJalaliDate } from '../lib/utils';
import { api } from '../services/api';
import type { DashboardSummaryResponse } from '../types/dashboard';

const CHART_TOOLTIP_STYLE = { direction: 'rtl', textAlign: 'right' } as const;

function ReportsSkeleton() {
    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <Skeleton className="h-8 w-44" />
                <Skeleton className="h-7 w-44" />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {Array.from({ length: 4 }).map((_, index) => (
                    <Skeleton key={index} className="h-36 rounded-xl" />
                ))}
            </div>

            <Skeleton className="h-16 rounded-xl" />

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
                <Skeleton className="h-[370px] rounded-xl xl:col-span-2" />
                <Skeleton className="h-[370px] rounded-xl" />
            </div>
        </div>
    );
}

interface ReportsErrorProps {
    message: string;
    onRetry: () => void;
}

function ReportsError({ message, onRetry }: ReportsErrorProps) {
    return (
        <div className="py-8">
            <Card className="mx-auto max-w-lg bg-white rounded-xl border-red-200">
                <CardContent className="flex flex-col items-center gap-3 p-8 text-center">
                    <AlertCircle className="h-10 w-10 text-red-600" />
                    <h2 className="text-lg font-semibold text-slate-900">
                        خطا در دریافت گزارش
                    </h2>
                    <p className="text-sm text-slate-600">{message}</p>
                    <Button variant="outline" className="rounded-lg" onClick={onRetry}>
                        تلاش مجدد
                    </Button>
                </CardContent>
            </Card>
        </div>
    );
}

export function ReportsPage() {
    const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const jalaliToday = useMemo(() => getTodayJalaliDate(), []);

    const fetchSummary = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const data = await api.get<DashboardSummaryResponse>('/reports/summary');
            setSummary(data);
        } catch (err) {
            const message =
                err instanceof Error ? err.message : 'خطا در بارگذاری داشبورد';
            setError(message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void fetchSummary();
    }, [fetchSummary]);

    if (loading) {
        return <ReportsSkeleton />;
    }

    if (error || !summary) {
        return (
            <ReportsError
                message={error ?? 'داده‌ای برای نمایش وجود ندارد.'}
                onRetry={fetchSummary}
            />
        );
    }

    return (
        <div className="space-y-6 text-right">
            {/* ── Header ─────────────────────────────────────── */}
            <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                        داشبورد اجرایی
                    </h1>
                    <p className="text-sm text-slate-500 mt-1">
                        نمای کلی وضعیت مالی و بودجه منطقه ۱۴
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <Badge
                        variant="secondary"
                        className="bg-slate-100 px-3 py-1. text-slate-700"
                    >
                        آخرین بروزرسانی: {jalaliToday}
                    </Badge>
                    <Button variant="outline" size="sm" className="rounded-lg">
                        <Download className="h-4 w-4 ml-2" />
                        دریافت گزارش
                    </Button>
                    <Button size="sm" className="rounded-lg">
                        <Plus className="h-4 w-4 ml-2" />
                        ثبت درخواست جدید
                    </Button>
                </div>
            </div>

            {/* ── KPI Cards ──────────────────────────────────── */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <KPICard
                    title="بودجه کل"
                    value={formatAmountAbbreviated(summary.total_budget)}
                    subtitle="ریال"
                    icon={Wallet}
                    colorScheme="blue"
                    trendValue="↑ ۱۲٪"
                    trendLabel="نسبت به سال گذشته"
                />
                <KPICard
                    title="اعتبار تعهد شده"
                    value={formatAmountAbbreviated(summary.committed_funds)}
                    subtitle="ریال"
                    icon={Lock}
                    colorScheme="amber"
                    className="bg-gradient-to-l from-blue-950 via-blue-900 to-blue-800 text-white border-0 [&_*]:text-white [&_.bg-amber-50]:bg-white/20"
                    trendValue="↑ ۸٪"
                    trendLabel="نسبت به ماه قبل"
                />
                <KPICard
                    title="هزینه انجام شده"
                    value={formatAmountAbbreviated(summary.executed_funds)}
                    subtitle="ریال"
                    icon={Banknote}
                    colorScheme="green"
                    trendValue="↑ ۱۵٪"
                    trendLabel="نسبت به فصل قبل"
                />
                <KPICard
                    title="قرارداد فعال"
                    value={summary.active_contracts.toLocaleString('fa-IR')}
                    subtitle="عدد"
                    icon={FileText}
                    colorScheme="purple"
                    trendValue="+۳"
                    trendLabel="قرارداد جدید این ماه"
                />
            </div>

            {/* ── Stacked Budget Progress Bar ────────────────── */}
            <BudgetProgressBar
                totalBudget={summary.total_budget}
                spentAmount={summary.executed_funds}
                blockedAmount={summary.committed_funds}
            />

            {/* ── Charts Grid ────────────────────────────────── */}
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
                {/* Pie Chart — Budget Distribution */}
                <Card className="bg-white rounded-xl border-slate-200 shadow-sm transition-shadow hover:shadow xl:order-1">
                    <CardHeader>
                        <CardTitle className="text-base font-semibold text-slate-900">
                            توزیع بودجه
                        </CardTitle>
                        <CardDescription className="text-slate-500">
                            سهم هر بخش از بودجه کل
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {summary.by_section.length === 0 ? (
                            <div className="flex h-[290px] items-center justify-center text-sm text-slate-500">
                                داده‌ای برای نمایش وجود ندارد.
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height={290}>
                                <PieChart>
                                    <Pie
                                        data={summary.by_section}
                                        dataKey="value"
                                        nameKey="name"
                                        cx="50%"
                                        cy="50%"
                                        outerRadius={95}
                                        innerRadius={55}
                                        paddingAngle={2}
                                    >
                                        {summary.by_section.map((section, index) => (
                                            <Cell
                                                key={`${section.name}-${index}`}
                                                fill={section.color}
                                            />
                                        ))}
                                    </Pie>
                                    <Tooltip
                                        contentStyle={CHART_TOOLTIP_STYLE}
                                        formatter={(value: number) =>
                                            formatAmountAbbreviated(value)
                                        }
                                    />
                                    <Legend
                                        verticalAlign="bottom"
                                        iconType="circle"
                                        wrapperStyle={{
                                            direction: 'rtl',
                                            fontSize: '12px',
                                            color: '#475569',
                                        }}
                                    />
                                </PieChart>
                            </ResponsiveContainer>
                        )}
                    </CardContent>
                </Card>

                {/* Bar Chart — Budget vs Expense */}
                <Card className="bg-white rounded-xl border-slate-200 shadow-sm transition-shadow hover:shadow xl:order-2 xl:col-span-2">
                    <CardHeader>
                        <CardTitle className="text-base font-semibold text-slate-900">
                            بودجه vs هزینه
                        </CardTitle>
                        <CardDescription className="text-slate-500">
                            مقایسه بودجه و هزینه بر اساس واحد سازمانی
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {summary.by_department.length === 0 ? (
                            <div className="flex h-[290px] items-center justify-center text-sm text-slate-500">
                                داده‌ای برای نمایش وجود ندارد.
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height={320}>
                                <BarChart
                                    data={summary.by_department}
                                    layout="vertical"
                                    margin={{ top: 8, right: 16, left: 16, bottom: 8 }}
                                >
                                    <CartesianGrid
                                        stroke="#e2e8f0"
                                        strokeDasharray="3 3"
                                        horizontal={false}
                                    />
                                    <XAxis
                                        type="number"
                                        tick={{ fill: '#64748b', fontSize: 12 }}
                                        tickFormatter={formatAmountAbbreviated}
                                    />
                                    <YAxis
                                        type="category"
                                        dataKey="name"
                                        orientation="right"
                                        width={130}
                                        interval={0}
                                        tickMargin={10}
                                        tick={{ fill: '#334155', fontSize: 12 }}
                                    />
                                    <Tooltip
                                        contentStyle={CHART_TOOLTIP_STYLE}
                                        formatter={(value: number) =>
                                            formatAmountAbbreviated(value)
                                        }
                                    />
                                    <Legend
                                        verticalAlign="top"
                                        align="right"
                                        wrapperStyle={{ direction: 'rtl' }}
                                    />
                                    <Bar
                                        dataKey="budget"
                                        name="بودجه"
                                        fill="#2563eb"
                                        radius={[6, 6, 6, 6]}
                                    />
                                    <Bar
                                        dataKey="spent"
                                        name="هزینه"
                                        fill="#059669"
                                        radius={[6, 6, 6, 6]}
                                    />
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* ── Recent Transactions Table ──────────────────── */}
            <Card className="bg-white rounded-xl border-slate-200 shadow-sm">
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle className="text-base font-semibold text-slate-900">
                                آخرین تراکنش‌ها
                            </CardTitle>
                            <CardDescription className="text-slate-500">
                                لیست آخرین تراکنش‌های مالی ثبت شده در سامانه
                            </CardDescription>
                        </div>
                        <Badge variant="secondary" className="bg-blue-50 text-blue-700">
                            {summary.active_contracts.toLocaleString('fa-IR')} قرارداد فعال
                        </Badge>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-slate-200 text-slate-500">
                                    <th className="py-3 px-4 text-right font-medium">واحد سازمانی</th>
                                    <th className="py-3 px-4 text-right font-medium">بودجه تخصیصی</th>
                                    <th className="py-3 px-4 text-right font-medium">هزینه شده</th>
                                    <th className="py-3 px-4 text-right font-medium">باقیمانده</th>
                                    <th className="py-3 px-4 text-right font-medium">وضعیت</th>
                                </tr>
                            </thead>
                            <tbody>
                                {summary.by_department.length === 0 ? (
                                    <tr>
                                        <td
                                            colSpan={5}
                                            className="py-10 text-center text-slate-500"
                                        >
                                            داده‌ای برای نمایش وجود ندارد.
                                        </td>
                                    </tr>
                                ) : (
                                    summary.by_department.map((dept, i) => {
                                        const usagePercent = dept.budget > 0
                                            ? ((dept.spent / dept.budget) * 100)
                                            : 0;
                                        let statusClass = 'bg-emerald-100 text-emerald-700';
                                        let statusLabel = 'عادی';
                                        if (usagePercent > 90) {
                                            statusClass = 'bg-red-100 text-red-700';
                                            statusLabel = 'بحرانی';
                                        } else if (usagePercent > 70) {
                                            statusClass = 'bg-amber-100 text-amber-700';
                                            statusLabel = 'هشدار';
                                        }

                                        return (
                                            <tr
                                                key={dept.name + i}
                                                className="border-b border-slate-100 last:border-0 transition-colors hover:bg-slate-50"
                                            >
                                                <td className="py-3 px-4 font-medium text-slate-800">
                                                    {dept.name}
                                                </td>
                                                <td className="py-3 px-4 font-mono text-slate-600">
                                                    {formatAmountAbbreviated(dept.budget)}
                                                </td>
                                                <td className="py-3 px-4 font-mono text-slate-600">
                                                    {formatAmountAbbreviated(dept.spent)}
                                                </td>
                                                <td className="py-3 px-4 font-mono text-slate-600">
                                                    {formatAmountAbbreviated(dept.remaining)}
                                                </td>
                                                <td className="py-3 px-4">
                                                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${statusClass}`}>
                                                        {statusLabel}
                                                    </span>
                                                </td>
                                            </tr>
                                        );
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

export default ReportsPage;
