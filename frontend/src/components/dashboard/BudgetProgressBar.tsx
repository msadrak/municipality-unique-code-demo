import { cn } from '../ui/utils';

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

    return (
        <div className="rounded-xl bg-white border border-slate-200 shadow-sm p-5">
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-slate-700">
                    وضعیت مصرف بودجه
                </h3>
                <span className="text-xs text-slate-500">
                    درصد تخصیص کل
                </span>
            </div>

            {/* Stacked bar */}
            <div className="h-5 w-full overflow-hidden rounded-full bg-slate-100 flex" dir="ltr">
                {/* Spent (Green) */}
                {spentPercent > 0 && (
                    <div
                        className="h-full bg-green-500 transition-all duration-500"
                        style={{ width: `${spentPercent}%` }}
                        title={`هزینه شده: ${formatPercent(spentPercent)}`}
                    />
                )}

                {/* Blocked (Amber with CSS stripes) */}
                {blockedPercent > 0 && (
                    <div
                        className="h-full transition-all duration-500"
                        style={{
                            width: `${blockedPercent}%`,
                            background: `repeating-linear-gradient(
                                -45deg,
                                #f59e0b,
                                #f59e0b 4px,
                                #fbbf24 4px,
                                #fbbf24 8px
                            )`,
                        }}
                        title={`مسدود شده: ${formatPercent(blockedPercent)}`}
                    />
                )}

                {/* Remaining (Slate) — implied by the container bg */}
            </div>

            {/* Legend */}
            <div className="flex flex-wrap items-center gap-5 mt-3">
                <LegendItem
                    color="bg-green-500"
                    label="هزینه شده"
                    percent={formatPercent(spentPercent)}
                />
                <LegendItem
                    color="bg-amber-400"
                    label="مسدود شده"
                    percent={formatPercent(blockedPercent)}
                    striped
                />
                <LegendItem
                    color="bg-slate-200"
                    label="باقیمانده"
                    percent={formatPercent(remainingPercent)}
                />
            </div>
        </div>
    );
}

interface LegendItemProps {
    color: string;
    label: string;
    percent: string;
    striped?: boolean;
}

function LegendItem({ color, label, percent, striped }: LegendItemProps) {
    return (
        <div className="flex items-center gap-1.5 text-xs text-slate-600">
            <span
                className={cn('inline-block h-3 w-3 rounded-sm', !striped && color)}
                style={
                    striped
                        ? {
                            background: `repeating-linear-gradient(
                                  -45deg,
                                  #f59e0b,
                                  #f59e0b 2px,
                                  #fbbf24 2px,
                                  #fbbf24 4px
                              )`,
                        }
                        : undefined
                }
            />
            <span className="font-medium">{label}</span>
            <span className="font-mono text-slate-500">{percent}</span>
        </div>
    );
}

export default BudgetProgressBar;
