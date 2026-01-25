import React, { useEffect, useState } from 'react';
import { Card } from '../ui/card';
import { Loader2, ShoppingCart, Calculator, Vault, Building, Users, TrendingUp, FileText, Heart, Home, HardHat, Package, Handshake, CreditCard, MoreHorizontal, Activity } from "lucide-react";
import { Alert, AlertDescription } from "../ui/alert";

// Map strings to Lucide components
const ICON_MAP: Record<string, any> = {
    ShoppingCart, Calculator, Vault, Building, Users, TrendingUp, FileText, Heart, Home, HardHat, Package, Handshake, CreditCard, MoreHorizontal
};

interface AllowedActivity {
    id: number;
    name: string;
    code: string;
}

interface AllowedSubsystem {
    id: number;
    title: string;
    icon: string;
    activities: AllowedActivity[];
}

interface Step1Props {
    formData: any;
    updateFormData: (data: any) => void;
}

export function WizardStep1_AllowedActivities({ formData, updateFormData }: Step1Props) {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // FIX: Match the API response structure from main.py
    const [data, setData] = useState<{
        user: { full_name: string; role: string };
        user_section: { title: string | null; code: string | null };
        allowed_subsystems: AllowedSubsystem[];
    } | null>(null);

    useEffect(() => {
        fetchAllowedActivities();
    }, []);

    const fetchAllowedActivities = async () => {
        try {
            const response = await fetch('/portal/user/allowed-activities');
            if (!response.ok) throw new Error('Failed to fetch activities');
            const result = await response.json();
            setData(result);
        } catch (err) {
            setError('خطا در دریافت لیست فعالیت‌ها');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleActivitySelect = (subsystem: AllowedSubsystem, activity: AllowedActivity) => {
        updateFormData({
            subsystemId: subsystem.id,
            subsystemTitle: subsystem.title,
            specialActivityId: activity.id,
            specialActivityName: activity.name,
            // Clear previous steps data if any
            transactionType: '',
        });
    };

    // Helper to get icon component
    const getIcon = (iconName: string) => {
        const Icon = ICON_MAP[iconName] || Activity;
        return <Icon className="h-6 w-6" />;
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600 mb-4" />
                <p className="text-gray-500">در حال بررسی دسترسی‌های شما...</p>
            </div>
        );
    }

    if (error) {
        return (
            <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
            </Alert>
        );
    }

    if (!data || data.allowed_subsystems.length === 0) {
        return (
            <div className="text-center py-12">
                <div className="bg-yellow-50 text-yellow-800 p-4 rounded-lg inline-block">
                    هیچ سامانه یا فعالیتی برای قسمت سازمانی شما تعریف نشده است.
                </div>
            </div>
        );
    }

    // ASSUMPTION: Based on user feedback, user belongs to ONE subsystem usually.
    // We take the primary subsystem (first one) to display context.
    const primarySubsystem = data.allowed_subsystems[0];
    const allActivities = data.allowed_subsystems.flatMap(sub =>
        sub.activities.map(act => ({ ...act, subsystem: sub }))
    );

    return (
        <div className="space-y-8">
            {/* User Context Header */}
            <div className="bg-blue-50 border border-blue-100 rounded-xl p-6 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-32 h-32 bg-blue-100 rounded-full -translate-x-1/2 -translate-y-1/2 opacity-50" />

                <div className="relative z-10 flex items-start gap-4">
                    <div className="p-3 bg-white rounded-lg shadow-sm text-blue-600">
                        {getIcon(primarySubsystem.icon)}
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-gray-900">
                            {data.user.full_name} عزیز، خوش آمدید
                        </h3>
                        <p className="text-sm text-gray-600 mt-1">
                            شما کاربر <strong>سامانه {primarySubsystem.title}</strong> در {data.user_section?.title || 'بدون قسمت'} هستید.
                        </p>
                    </div>
                </div>
            </div>

            {/* Special Activities List */}
            <div>
                <h4 className="text-sm font-bold text-gray-500 mb-4 flex items-center gap-2">
                    <Activity className="h-4 w-4" />
                    وظایف و فعالیت‌های ویژه شما
                </h4>

                {allActivities.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {allActivities.map((item) => (
                            <div
                                key={`${item.subsystem.id}-${item.id}`}
                                className={`
                  relative cursor-pointer group transition-all duration-200
                  bg-white border rounded-xl p-4 hover:shadow-md
                  ${formData.specialActivityId === item.id
                                        ? 'border-blue-500 ring-1 ring-blue-500 bg-blue-50/10'
                                        : 'border-gray-200 hover:border-blue-300'}
                `}
                                onClick={() => handleActivitySelect(item.subsystem, item)}
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className={`
                      p-2 rounded-lg transition-colors
                      ${formData.specialActivityId === item.id
                                                ? 'bg-blue-100 text-blue-600'
                                                : 'bg-gray-100 text-gray-500 group-hover:bg-blue-50 group-hover:text-blue-600'}
                    `}>
                                            <FileText className="h-5 w-5" />
                                        </div>
                                        <div>
                                            <span className="font-bold text-gray-800 block text-sm">{item.name}</span>
                                            {data.allowed_subsystems.length > 1 && item.subsystem.id !== primarySubsystem.id && (
                                                <span className="text-[10px] text-gray-400 mt-1 block">مربوط به {item.subsystem.title}</span>
                                            )}
                                        </div>
                                    </div>

                                    <div className={`
                    w-4 h-4 rounded-full border flex items-center justify-center transition-colors
                    ${formData.specialActivityId === item.id
                                            ? 'border-blue-500 bg-blue-500'
                                            : 'border-gray-300'}
                  `}>
                                        {formData.specialActivityId === item.id && (
                                            <div className="w-1.5 h-1.5 bg-white rounded-full" />
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-8 bg-gray-50 rounded-xl border border-dashed border-gray-300 text-gray-400">
                        هیچ فعالیت ویژه‌ای برای این سامانه تعریف نشده است.
                    </div>
                )}
            </div>

            {/* Info Note */}
            <div className="text-center text-xs text-gray-400 mt-8">
                لیست فعالیت‌ها بر اساس بخش سازمانی شما بصورت خودکار به‌روزرسانی می‌شود.
            </div>
        </div>
    );
}
