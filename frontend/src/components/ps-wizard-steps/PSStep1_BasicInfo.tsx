import React from 'react';
import { useFormContext } from 'react-hook-form';
import type { ProgressStatementFormData } from '../ProgressStatementWizard';

const STATEMENT_TYPES = [
    {
        value: 'INTERIM' as const,
        label: 'موقت',
        description: 'صورت‌وضعیت علی‌الحساب',
        icon: 'schedule',
        accent: 'blue',
        hoverBorder: 'hover:border-blue-300',
        hoverBg: 'hover:bg-blue-50',
        activeBorder: 'border-primary',
        activeBg: 'bg-blue-50/50',
        iconBg: 'bg-blue-100 text-blue-600',
        activeIconBg: 'bg-primary text-white',
        checkColor: 'text-primary',
    },
    {
        value: 'FINAL' as const,
        label: 'قطعی',
        description: 'صورت‌وضعیت نهایی پروژه',
        icon: 'verified',
        accent: 'emerald',
        hoverBorder: 'hover:border-emerald-300',
        hoverBg: 'hover:bg-emerald-50',
        activeBorder: 'border-emerald-500',
        activeBg: 'bg-emerald-50/50',
        iconBg: 'bg-emerald-100 text-emerald-600',
        activeIconBg: 'bg-emerald-500 text-white',
        checkColor: 'text-emerald-500',
    },
    {
        value: 'ADJUSTMENT' as const,
        label: 'تعدیل',
        description: 'محاسبه مابه‌التفاوت نرخ',
        icon: 'sync_alt',
        accent: 'amber',
        hoverBorder: 'hover:border-amber-300',
        hoverBg: 'hover:bg-amber-50',
        activeBorder: 'border-amber-500',
        activeBg: 'bg-amber-50/50',
        iconBg: 'bg-amber-100 text-amber-600',
        activeIconBg: 'bg-amber-500 text-white',
        checkColor: 'text-amber-500',
    },
] as const;

export function PSStep1_BasicInfo() {
    const {
        register,
        watch,
        setValue,
        formState: { errors },
    } = useFormContext<ProgressStatementFormData>();

    const selectedType = watch('statementType');

    return (
        <div className="flex flex-col gap-8">
            {/* Type Selection Section */}
            <section>
                <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
                    <span className="w-1 h-6 bg-primary rounded-full"></span>
                    نوع صورت‌وضعیت
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {STATEMENT_TYPES.map((type) => {
                        const isSelected = selectedType === type.value;

                        return (
                            <label key={type.value} className="cursor-pointer group relative">
                                <input
                                    type="radio"
                                    className="peer sr-only"
                                    name="statement_type"
                                    value={type.value}
                                    checked={isSelected}
                                    onChange={() => setValue('statementType', type.value, { shouldValidate: true })}
                                />
                                <div className={`flex flex-col items-center justify-center gap-4 rounded-xl border-2 p-6 transition-all ${type.hoverBorder} ${type.hoverBg} ${isSelected ? `${type.activeBorder} ${type.activeBg} shadow-md` : 'border-slate-200 bg-white'}`}>
                                    <div className={`size-14 rounded-full flex items-center justify-center transition-colors ${isSelected ? type.activeIconBg : type.iconBg}`}>
                                        <span className="material-symbols-outlined text-3xl">{type.icon}</span>
                                    </div>
                                    <div className="text-center">
                                        <h4 className="text-lg font-bold text-slate-900">{type.label}</h4>
                                        <p className="text-sm text-slate-500 mt-1">{type.description}</p>
                                    </div>
                                    <div className={`absolute top-4 right-4 transition-opacity ${isSelected ? `opacity-100 ${type.checkColor}` : 'opacity-0'}`}>
                                        <span className="material-symbols-outlined">check_circle</span>
                                    </div>
                                </div>
                            </label>
                        );
                    })}
                </div>
                {errors.statementType && (
                    <p className="text-sm text-red-500 mt-2">{errors.statementType.message}</p>
                )}
            </section>

            <div className="h-px bg-slate-100 w-full my-2"></div>

            {/* Description Field */}
            <section>
                <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
                    <span className="w-1 h-6 bg-primary rounded-full"></span>
                    شرح صورت‌وضعیت
                </h3>
                <div className="flex flex-col gap-2">
                    <label className="text-sm font-bold text-slate-700" htmlFor="ps_description">
                        توضیحات <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                        <div className="absolute top-3 right-3 pointer-events-none text-slate-400">
                            <span className="material-symbols-outlined">edit_note</span>
                        </div>
                        <textarea
                            id="ps_description"
                            rows={4}
                            className="block w-full rounded-xl border border-slate-300 bg-white pr-10 pt-3 focus:border-primary focus:ring-4 focus:ring-primary/10 text-slate-900 resize-none transition-all shadow-sm"
                            placeholder="شرح مختصر صورت‌وضعیت، مثلاً: صورت‌وضعیت موقت شماره ۳ - عملیات خاکبرداری فاز ۲"
                            {...register('description')}
                        ></textarea>
                    </div>
                    <p className="text-xs text-slate-400">این شرح در سیستم به عنوان توضیحات اصلی صورت‌وضعیت ثبت خواهد شد.</p>
                    {errors.description && (
                        <p className="text-sm text-red-500">{errors.description.message}</p>
                    )}
                </div>
            </section>
        </div>
    );
}
