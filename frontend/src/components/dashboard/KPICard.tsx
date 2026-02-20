import type { LucideIcon } from 'lucide-react';

import { Card, CardContent } from '../ui/card';
import { cn } from '../ui/utils';

type KPICardColorScheme = 'blue' | 'amber' | 'green' | 'purple' | 'red';

const colorSchemeMap: Record<
    KPICardColorScheme,
    {
        iconBg: string;
        iconText: string;
        valueText: string;
    }
> = {
    blue: {
        iconBg: 'bg-blue-50',
        iconText: 'text-blue-600',
        valueText: 'text-blue-600',
    },
    amber: {
        iconBg: 'bg-amber-50',
        iconText: 'text-amber-600',
        valueText: 'text-amber-600',
    },
    green: {
        iconBg: 'bg-green-50',
        iconText: 'text-green-600',
        valueText: 'text-green-600',
    },
    purple: {
        iconBg: 'bg-purple-50',
        iconText: 'text-purple-600',
        valueText: 'text-purple-600',
    },
    red: {
        iconBg: 'bg-red-100',
        iconText: 'text-red-700',
        valueText: 'text-red-700',
    },
};

export interface KPICardProps {
    title: string;
    value: string;
    subtitle: string;
    icon: LucideIcon;
    colorScheme: KPICardColorScheme;
    className?: string;
}

export function KPICard({
    title,
    value,
    subtitle,
    icon: Icon,
    colorScheme,
    className,
}: KPICardProps) {
    const scheme = colorSchemeMap[colorScheme];

    return (
        <Card className={cn("bg-white rounded-xl border-slate-200 shadow-sm transition-shadow hover:shadow", className)}>
            <CardContent className="p-6">
                <div className="flex items-start justify-between gap-4">
                    <div
                        className={cn(
                            'flex shrink-0 items-center justify-center p-3 rounded-lg',
                            scheme.iconBg
                        )}
                    >
                        <Icon className={cn('h-5 w-5', scheme.iconText)} />
                    </div>

                    <div className="min-w-0 flex-1 text-right">
                        <p className="text-sm font-medium text-slate-600">{title}</p>
                        <p
                            className={cn(
                                'mt-2 text-2xl font-bold font-mono-num tracking-tight',
                                scheme.valueText
                            )}
                        >
                            {value}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">{subtitle}</p>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

export default KPICard;
