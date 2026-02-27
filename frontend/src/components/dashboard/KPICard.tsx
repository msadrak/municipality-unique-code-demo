import { TrendingUp, Plus } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import { cn } from '../ui/utils';

type KPICardColorScheme = 'blue' | 'amber' | 'green' | 'purple' | 'red';

const colorSchemeMap: Record<
    KPICardColorScheme,
    {
        iconBg: string;
        iconText: string;
        valueText: string;
        trendText: string;
    }
> = {
    blue: {
        iconBg: 'bg-blue-50',
        iconText: 'text-blue-600',
        valueText: 'text-slate-900',
        trendText: 'text-emerald-600',
    },
    amber: {
        iconBg: 'bg-amber-50',
        iconText: 'text-amber-600',
        valueText: 'text-slate-900',
        trendText: 'text-emerald-600',
    },
    green: {
        iconBg: 'bg-emerald-50',
        iconText: 'text-emerald-600',
        valueText: 'text-slate-900',
        trendText: 'text-emerald-600',
    },
    purple: {
        iconBg: 'bg-purple-50',
        iconText: 'text-purple-600',
        valueText: 'text-slate-900',
        trendText: 'text-purple-600',
    },
    red: {
        iconBg: 'bg-red-100',
        iconText: 'text-red-700',
        valueText: 'text-slate-900',
        trendText: 'text-red-600',
    },
};

export interface KPICardProps {
    title: string;
    value: string;
    subtitle: string;
    icon: LucideIcon;
    colorScheme: KPICardColorScheme;
    className?: string;
    /** e.g. "۱۲٪" */
    trendValue?: string;
    /** e.g. "نسبت به سال گذشته" */
    trendLabel?: string;
}

export function KPICard({
    title,
    value,
    subtitle,
    icon: Icon,
    colorScheme,
    className,
    trendValue,
    trendLabel,
}: KPICardProps) {
    const scheme = colorSchemeMap[colorScheme];

    return (
        <div
            className={cn(
                'group relative overflow-hidden rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-all hover:shadow-md',
                className,
            )}
        >
            <div className="flex items-center justify-between">
                <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-500">{title}</p>
                    <h3 className="mt-2 text-2xl font-bold tracking-tight">
                        <span className={scheme.valueText}>{value}</span>
                        {subtitle && (
                            <span className="text-lg font-normal text-slate-500 mr-1">
                                {subtitle}
                            </span>
                        )}
                    </h3>
                </div>
                <div
                    className={cn(
                        'flex shrink-0 items-center justify-center p-3 rounded-full',
                        scheme.iconBg,
                    )}
                >
                    <Icon className={cn('h-6 w-6', scheme.iconText)} />
                </div>
            </div>

            {/* Trend indicator */}
            {trendValue && (
                <div className="mt-4 flex items-center text-sm">
                    <span className={cn('flex items-center font-medium', scheme.trendText)}>
                        {colorScheme === 'purple' ? (
                            <Plus className="h-4 w-4 ml-1" />
                        ) : (
                            <TrendingUp className="h-4 w-4 ml-1" />
                        )}
                        {trendValue}
                    </span>
                    {trendLabel && (
                        <span className="mr-2 text-slate-400">{trendLabel}</span>
                    )}
                </div>
            )}
        </div>
    );
}

export default KPICard;
