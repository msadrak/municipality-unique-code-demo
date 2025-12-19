import React, { useState, useEffect } from 'react';
import { Label } from '../ui/label';
import { TransactionFormData } from '../TransactionWizard';
import { Loader2, ShoppingCart, Calculator, Vault, Building, Users, TrendingUp, FileText, Heart, Home, HardHat, Package, Handshake, CreditCard, MoreHorizontal } from 'lucide-react';

type Props = {
    formData: TransactionFormData;
    updateFormData: (data: Partial<TransactionFormData>) => void;
};

interface Subsystem {
    id: number;
    code: string;
    title: string;
    icon: string;
    attachment_type: string;
    order: number;
}

// Icon mapping
const iconMap: Record<string, React.ElementType> = {
    ShoppingCart,
    Calculator,
    Vault,
    Building,
    Users,
    TrendingUp,
    FileText,
    Heart,
    Home,
    HardHat,
    Package,
    Handshake,
    CreditCard,
    MoreHorizontal,
};

export function WizardStep0_SubsystemSelect({ formData, updateFormData }: Props) {
    const [subsystems, setSubsystems] = useState<Subsystem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchSubsystems();
    }, []);

    const fetchSubsystems = async () => {
        try {
            setLoading(true);
            const response = await fetch('/portal/subsystems');
            if (!response.ok) throw new Error('Failed to fetch subsystems');
            const data = await response.json();
            setSubsystems(data.subsystems || []);
        } catch (err) {
            setError('خطا در دریافت سامانه‌ها');
            console.error('Error fetching subsystems:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleSelect = (subsystem: Subsystem) => {
        updateFormData({
            subsystemId: subsystem.id,
            subsystemCode: subsystem.code,
            subsystemTitle: subsystem.title,
            attachmentType: subsystem.attachment_type,
        });
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <span className="mr-3 text-muted-foreground">در حال بارگذاری سامانه‌ها...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-center py-8 text-destructive">
                <p>{error}</p>
                <button onClick={fetchSubsystems} className="mt-2 text-primary underline">
                    تلاش مجدد
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h3>انتخاب سامانه</h3>
                <p className="text-sm text-muted-foreground mt-1">
                    سامانه مرتبط با درخواست خود را انتخاب کنید (متولی بر اساس انتخاب شما مشخص می‌شود)
                </p>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {subsystems.map((subsystem) => {
                    const IconComponent = iconMap[subsystem.icon] || MoreHorizontal;
                    const isSelected = formData.subsystemId === subsystem.id;

                    return (
                        <button
                            key={subsystem.id}
                            onClick={() => handleSelect(subsystem)}
                            className={`
                flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-all
                hover:shadow-md hover:border-primary/50
                ${isSelected
                                    ? 'border-primary bg-primary/10 shadow-lg'
                                    : 'border-border bg-card hover:bg-accent'
                                }
              `}
                        >
                            <div className={`
                p-3 rounded-full mb-2
                ${isSelected ? 'bg-primary/20' : 'bg-muted'}
              `}>
                                <IconComponent className={`h-6 w-6 ${isSelected ? 'text-primary' : 'text-muted-foreground'}`} />
                            </div>
                            <span className={`text-sm font-medium text-center ${isSelected ? 'text-primary' : ''}`}>
                                {subsystem.title}
                            </span>
                        </button>
                    );
                })}
            </div>

            {/* Selection Summary */}
            {formData.subsystemId && (
                <div className="bg-accent p-4 rounded-lg border border-border">
                    <Label className="text-muted-foreground">سامانه انتخابی:</Label>
                    <p className="font-medium text-lg mt-1">{formData.subsystemTitle}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                        {formData.attachmentType === 'api' && 'مستندات از طریق اتصال به سامانه دریافت می‌شود'}
                        {formData.attachmentType === 'upload' && 'مستندات به صورت فایل آپلود می‌شود'}
                        {formData.attachmentType === 'both' && 'مستندات از طریق سامانه یا آپلود فایل'}
                    </p>
                </div>
            )}
        </div>
    );
}
