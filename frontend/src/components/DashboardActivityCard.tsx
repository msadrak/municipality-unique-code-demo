import React from 'react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import {
    FileText,
    Wallet,
    Users,
    Building2,
    Receipt,
    CreditCard,
    FileCheck,
    ClipboardList,
    Briefcase,
    CircleDollarSign,
    Upload,
    ExternalLink,
    ChevronLeft
} from 'lucide-react';
import { AllowedActivity } from '../types/dashboard';

interface DashboardActivityCardProps {
    activity: AllowedActivity;
    onClick: () => void;
}

// Map activity codes to icons
const getActivityIcon = (code: string): React.ReactNode => {
    const iconClass = "h-6 w-6";
    const iconMap: Record<string, React.ReactNode> = {
        'SALARY_PAYMENT': <Wallet className={iconClass} />,
        'OVERTIME_PAYMENT': <CreditCard className={iconClass} />,
        'BONUS_PAYMENT': <CircleDollarSign className={iconClass} />,
        'CONTRACT_REGISTER': <FileCheck className={iconClass} />,
        'CONTRACT_AMENDMENT': <ClipboardList className={iconClass} />,
        'PROGRESS_PAYMENT': <Receipt className={iconClass} />,
        'ADVANCE_PAYMENT': <CreditCard className={iconClass} />,
        'PERFORMANCE_BOND': <FileText className={iconClass} />,
        'CHECK_ISSUE': <Receipt className={iconClass} />,
        'BANK_TRANSFER': <CreditCard className={iconClass} />,
        'PURCHASE_REQUEST': <Briefcase className={iconClass} />,
        'INVOICE_PAYMENT': <Receipt className={iconClass} />,
        'LOAN_PAYMENT': <Wallet className={iconClass} />,
        'AID_PAYMENT': <Users className={iconClass} />,
    };
    return iconMap[code] || <FileText className={iconClass} />;
};

// Map frequency to Persian labels and colors (handles both uppercase and lowercase)
const getFrequencyBadge = (frequency: string | null): { label: string; variant: 'default' | 'secondary' | 'outline' } | null => {
    if (!frequency) return null;
    const normalizedFreq = frequency.toLowerCase(); // Normalize to lowercase
    const map: Record<string, { label: string; variant: 'default' | 'secondary' | 'outline' }> = {
        'daily': { label: 'روزانه', variant: 'default' },
        'monthly': { label: 'ماهانه', variant: 'secondary' },
        'yearly': { label: 'سالانه', variant: 'outline' },
    };
    return map[normalizedFreq] || null;
};

export function DashboardActivityCard({ activity, onClick }: DashboardActivityCardProps) {
    const frequencyBadge = getFrequencyBadge(activity.frequency);
    const hasConstraints = activity.constraints !== null;

    return (
        <Card
            className="group cursor-pointer transition-all duration-200 hover:shadow-lg hover:border-primary/50 hover:-translate-y-0.5"
            onClick={onClick}
        >
            <CardContent className="p-6">
                <div className="flex items-start gap-4">
                    {/* Icon */}
                    <div className="flex-shrink-0 p-3 rounded-lg bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                        {getActivityIcon(activity.code)}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors">
                            {activity.title}
                        </h3>

                        {/* Badges row */}
                        <div className="flex flex-wrap items-center gap-2 mt-2">
                            {frequencyBadge && (
                                <Badge variant={frequencyBadge.variant} className="text-xs">
                                    {frequencyBadge.label}
                                </Badge>
                            )}

                            {activity.requires_file_upload && (
                                <Badge variant="outline" className="text-xs gap-1">
                                    <Upload className="h-3 w-3" />
                                    نیاز به فایل
                                </Badge>
                            )}

                            {activity.external_service_url && (
                                <Badge variant="outline" className="text-xs gap-1">
                                    <ExternalLink className="h-3 w-3" />
                                    اتصال خارجی
                                </Badge>
                            )}

                            {hasConstraints && (
                                <Badge variant="secondary" className="text-xs">
                                    محدودیت بودجه
                                </Badge>
                            )}
                        </div>

                        {/* Form type hint */}
                        {activity.form_type && (
                            <p className="text-xs text-muted-foreground mt-2">
                                فرم: {activity.form_type}
                            </p>
                        )}
                    </div>

                    {/* Arrow indicator */}
                    <div className="flex-shrink-0 text-muted-foreground group-hover:text-primary transition-colors">
                        <ChevronLeft className="h-5 w-5" />
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

export default DashboardActivityCard;
