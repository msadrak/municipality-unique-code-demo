import React, { useState, useEffect } from 'react';
import { Label } from '../ui/label';
import { TransactionFormData } from '../TransactionWizard';
import { Loader2, CheckCircle2 } from 'lucide-react';

type Props = {
    formData: TransactionFormData;
    updateFormData: (data: Partial<TransactionFormData>) => void;
};

interface Activity {
    id: number;
    code: string;
    title: string;
    form_type: string | null;
}

export function WizardStep1_SpecialActivity({ formData, updateFormData }: Props) {
    const [activities, setActivities] = useState<Activity[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (formData.subsystemId) {
            fetchActivities(formData.subsystemId);
        }
    }, [formData.subsystemId]);

    const fetchActivities = async (subsystemId: number) => {
        try {
            setLoading(true);
            setError(null);
            const response = await fetch(`/portal/subsystems/${subsystemId}/activities`);
            if (!response.ok) throw new Error('Failed to fetch activities');
            const data = await response.json();
            setActivities(data.activities || []);
        } catch (err) {
            setError('خطا در دریافت فعالیت‌ها');
            console.error('Error fetching activities:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleSelect = (activity: Activity) => {
        updateFormData({
            subsystemActivityId: activity.id,
            subsystemActivityCode: activity.code,
            subsystemActivityTitle: activity.title,
            formType: activity.form_type || undefined,
        });
    };

    if (!formData.subsystemId) {
        return (
            <div className="text-center py-8 text-muted-foreground">
                لطفاً ابتدا سامانه را انتخاب کنید
            </div>
        );
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <span className="mr-3 text-muted-foreground">در حال بارگذاری فعالیت‌ها...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-center py-8 text-destructive">
                <p>{error}</p>
                <button
                    onClick={() => formData.subsystemId && fetchActivities(formData.subsystemId)}
                    className="mt-2 text-primary underline"
                >
                    تلاش مجدد
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h3>انتخاب فعالیت ویژه</h3>
                <p className="text-sm text-muted-foreground mt-1">
                    سامانه انتخابی: <span className="font-medium text-foreground">{formData.subsystemTitle}</span>
                </p>
            </div>

            {activities.length === 0 ? (
                <div className="text-center py-8 bg-muted/50 rounded-lg">
                    <p className="text-muted-foreground">
                        فعالیت ویژه‌ای برای این سامانه تعریف نشده است.
                    </p>
                    <p className="text-sm text-muted-foreground mt-2">
                        می‌توانید بدون انتخاب فعالیت ویژه ادامه دهید.
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {activities.map((activity) => {
                        const isSelected = formData.subsystemActivityId === activity.id;

                        return (
                            <button
                                key={activity.id}
                                onClick={() => handleSelect(activity)}
                                className={`
                  flex items-center justify-between p-4 rounded-xl border-2 transition-all text-right
                  hover:shadow-md hover:border-primary/50
                  ${isSelected
                                        ? 'border-primary bg-primary/10 shadow-lg'
                                        : 'border-border bg-card hover:bg-accent'
                                    }
                `}
                            >
                                <div className="flex-1">
                                    <span className={`font-medium ${isSelected ? 'text-primary' : ''}`}>
                                        {activity.title}
                                    </span>
                                    {activity.form_type && (
                                        <span className="text-xs text-muted-foreground block mt-1">
                                            فرم: {activity.form_type}
                                        </span>
                                    )}
                                </div>
                                {isSelected && (
                                    <CheckCircle2 className="h-5 w-5 text-primary mr-2" />
                                )}
                            </button>
                        );
                    })}
                </div>
            )}

            {/* Selection Summary */}
            {formData.subsystemActivityId && (
                <div className="bg-accent p-4 rounded-lg border border-border">
                    <Label className="text-muted-foreground">فعالیت انتخابی:</Label>
                    <p className="font-medium text-lg mt-1">{formData.subsystemActivityTitle}</p>
                </div>
            )}
        </div>
    );
}
