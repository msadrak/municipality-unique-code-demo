import { formatAmountAbbreviated } from '../../lib/utils';

interface BudgetProgressBarProps {
    totalBudget: number;
    spentAmount: number;
    blockedAmount: number;
}

function formatPercent(value: number): string {
    if (value <= 0) return '۰٪';
    if (value < 1) return '<۱٪';
    return new Intl.NumberFormat('fa-IR', {
        maximumFractionDigits: 0,
    }).format(Math.round(value)) + '٪';
}

export function BudgetProgressBar({
    totalBudget,
    spentAmount,
    blockedAmount,
}: BudgetProgressBarProps) {
    const safeTotalBudget = Math.max(totalBudget, 1);
    const spentPercent = Math.max(0, (spentAmount / safeTotalBudget) * 100);
    const blockedPercent = Math.max(0, (blockedAmount / safeTotalBudget) * 100);
    const remainingPercent = Math.max(0, 100 - spentPercent - blockedPercent);

    const halfBudget = totalBudget / 2;

    return (
        <div className="rounded-xl bg-white border border-slate-200 shadow-sm p-6">
            <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <h3 className="text-lg font-bold text-slate-900">
                    وضعیت مصرف بودجه عمرانی
                </h3>
                <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-1.5">
                        <div className="h-3 w-3 rounded-full bg-emerald-500" />
                        <span className="text-slate-600">مصرف قطعی</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <div className="h-3 w-3 rounded-full bg-amber-400" />
                        <span className="text-slate-600">مسدود شده</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <div className="h-3 w-3 rounded-full bg-slate-200" />
                        <span className="text-slate-600">باقی‌مانده</span>
                    </div>
                </div>
            </div>

            {/* Stacked progress bar */}
            <div className="relative h-6 w-full overflow-hidden rounded-full bg-slate-100 flex" dir="ltr">
                {/* Spent (Green) */}
                {spentPercent > 0 && (
                    <div
                        className="flex h-full items-center justify-center bg-emerald-500 text-[10px] font-bold text-white transition-all duration-500"
                        style={{ width: `${spentPercent}%` }}
                    >
                        {spentPercent >= 8 && formatPercent(spentPercent)}
                    </div>
                )}

                {/* Blocked (Amber) */}
                {blockedPercent > 0 && (
                    <div
                        className="flex h-full items-center justify-center bg-amber-400 text-[10px] font-bold text-slate-900 transition-all duration-500"
                        style={{ width: `${blockedPercent}%` }}
                    >
                        {blockedPercent >= 8 && formatPercent(blockedPercent)}
                    </div>
                )}

                {/* Remaining (Slate) */}
                {remainingPercent > 0 && (
                    <div
                        className="flex h-full items-center justify-center bg-slate-200 text-[10px] font-bold text-slate-500 transition-all duration-500"
                        style={{ width: `${remainingPercent}%` }}
                    >
                        {remainingPercent >= 8 && formatPercent(remainingPercent)}
                    </div>
                )}
            </div>

            {/* Min / Mid / Max labels */}
            <div className="mt-3 flex justify-between text-xs font-medium text-slate-500">
                <span>۰ ریال</span>
                <span>{formatAmountAbbreviated(halfBudget)}</span>
                <span>{formatAmountAbbreviated(totalBudget)}</span>
            </div>
        </div>
    );
}

export default BudgetProgressBar;
