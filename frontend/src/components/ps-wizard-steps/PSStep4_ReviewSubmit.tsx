import React from 'react';
import { useFormContext } from 'react-hook-form';
import type { ProgressStatementFormData } from '../ProgressStatementWizard';
import type { ContractTemplateSchema } from '../../services/contracts';
import { formatNumber } from '../../lib/utils';

const TYPE_LABELS: Record<string, string> = {
    INTERIM: 'موقت',
    FINAL: 'قطعی',
    ADJUSTMENT: 'تعدیل',
    FINAL_ADJUSTMENT: 'تعدیل قطعی',
};

interface PSStep4Props {
    onSubmit: () => void;
    isSubmitting: boolean;
    onPrev?: () => void;
    schema?: ContractTemplateSchema | null;
}

export function PSStep4_ReviewSubmit({ onSubmit, isSubmitting, onPrev, schema }: PSStep4Props) {
    const { getValues } = useFormContext<ProgressStatementFormData>();
    const data = getValues();

    // Collect dynamic template_data entries with human-readable labels
    const templateData = data.template_data || {};
    const schemaProps = schema?.properties ?? {};
    const templateEntries = Object.entries(templateData).filter(
        ([, v]) => v !== undefined && v !== '' && v !== null,
    );

    const totalDeductions =
        (data.insuranceDeduction || 0) +
        (data.taxDeduction || 0) +
        (data.advancePaymentAmount || 0) +
        (data.otherDeductions || 0);
    const netAmount = (data.grossAmount || 0) - totalDeductions;

    return (
        <div className="space-y-8">
            {/* Header Section */}
            <div>
                <h2 className="text-2xl md:text-3xl font-black text-slate-900 mb-2 tracking-tight">پیش‌نمایش و ارجاع</h2>
                <p className="text-slate-500">لطفاً اطلاعات زیر را با دقت بررسی کرده و سپس جهت تایید به ناظر پروژه ارسال نمایید.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Main Content Card */}
                <div className="lg:col-span-2 space-y-6">
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
                        <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                            <h3 className="font-bold text-slate-800 flex items-center gap-2">
                                <span className="material-symbols-outlined text-primary">summarize</span>
                                خلاصه صورت‌وضعیت
                            </h3>
                            <span className="bg-blue-100 text-blue-700 text-xs px-3 py-1 rounded-full font-medium border border-blue-200">پیش‌نویس</span>
                        </div>

                        {/* Section 1: Basic Info */}
                        <div className="p-6">
                            <div className="flex flex-wrap gap-4 items-center justify-between mb-2">
                                <h4 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">اطلاعات پایه</h4>
                                <button type="button" className="text-primary text-xs hover:underline flex items-center gap-1" onClick={onPrev}>
                                    <span className="material-symbols-outlined text-[14px]">edit</span>
                                    ویرایش
                                </button>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-slate-50 p-4 rounded-lg border border-slate-100">
                                <div>
                                    <span className="block text-xs text-slate-500 mb-1">نوع صورت‌وضعیت</span>
                                    <span className="block text-slate-800 font-medium">
                                        {TYPE_LABELS[data.statementType || ''] || '—'}
                                    </span>
                                </div>
                                <div>
                                    <span className="block text-xs text-slate-500 mb-1">شرح</span>
                                    <span className="block text-slate-800 font-medium text-sm leading-relaxed">
                                        {data.description || '—'}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div className="w-full h-px bg-slate-100"></div>

                        {/* Section 2: Financial Amounts */}
                        <div className="p-6">
                            <div className="flex flex-wrap gap-4 items-center justify-between mb-4">
                                <h4 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">مبالغ مالی (ریال)</h4>
                            </div>
                            <div className="space-y-3">
                                <div className="flex justify-between items-center text-sm">
                                    <span className="text-slate-600">مبلغ ناخالص دوره:</span>
                                    <span className="font-mono font-medium text-slate-900" dir="ltr">{formatNumber(data.grossAmount || 0)}</span>
                                </div>
                                <div className="flex justify-between items-center text-sm">
                                    <span className="text-slate-600">کسور بیمه:</span>
                                    <span className="font-mono font-medium text-red-500" dir="ltr">- {formatNumber(data.insuranceDeduction || 0)}</span>
                                </div>
                                <div className="flex justify-between items-center text-sm">
                                    <span className="text-slate-600">کسور مالیات:</span>
                                    <span className="font-mono font-medium text-red-500" dir="ltr">- {formatNumber(data.taxDeduction || 0)}</span>
                                </div>
                                <div className="flex justify-between items-center text-sm">
                                    <span className="text-slate-600">کسر پیش‌پرداخت:</span>
                                    <span className="font-mono font-medium text-red-500" dir="ltr">- {formatNumber(data.advancePaymentAmount || 0)}</span>
                                </div>
                                <div className="flex justify-between items-center text-sm">
                                    <span className="text-slate-600">سایر کسورات:</span>
                                    <span className="font-mono font-medium text-red-500" dir="ltr">- {formatNumber(data.otherDeductions || 0)}</span>
                                </div>
                                <div className="mt-4 pt-4 border-t border-dashed border-slate-200 flex justify-between items-center">
                                    <span className="text-base font-bold text-slate-800">مبلغ قابل پرداخت (خالص):</span>
                                    <span className="text-xl md:text-2xl font-black text-primary font-mono" dir="ltr">{formatNumber(netAmount)} ریال</span>
                                </div>
                            </div>
                        </div>

                        <div className="w-full h-px bg-slate-100"></div>

                        {/* Section 3: Specific Info */}
                        <div className="p-6">
                            <div className="flex flex-wrap gap-4 items-center justify-between mb-4">
                                <h4 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">اطلاعات اختصاصی</h4>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <div>
                                    <span className="block text-xs text-slate-500 mb-1">معاونت صادرکننده</span>
                                    <span className="block text-slate-800 font-medium text-sm">
                                        {data.originatingOrgan || '—'}
                                    </span>
                                </div>
                                <div>
                                    <span className="block text-xs text-slate-500 mb-1">دوره</span>
                                    <span className="block text-slate-800 font-medium text-sm">
                                        {data.periodStart && data.periodEnd
                                            ? `${data.periodStart} تا ${data.periodEnd}`
                                            : data.periodStart || data.periodEnd || '—'}
                                    </span>
                                </div>
                            </div>

                            {/* Dynamic template_data fields */}
                            {templateEntries.length > 0 && (
                                <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {templateEntries.map(([key, value]) => {
                                        const label = schemaProps[key]?.title || key;
                                        const displayValue = typeof value === 'boolean'
                                            ? (value ? 'بله' : 'خیر')
                                            : String(value);
                                        const isLong = displayValue.length > 60;

                                        return (
                                            <div key={key} className={isLong ? 'md:col-span-2' : ''}>
                                                <span className="block text-xs text-slate-500 mb-1">{label}</span>
                                                {isLong ? (
                                                    <p className="text-sm text-slate-700 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-100">
                                                        {displayValue}
                                                    </p>
                                                ) : (
                                                    <span className="inline-flex items-center gap-2 px-3 py-1 bg-slate-100 rounded text-sm font-mono text-slate-700">
                                                        <span className="material-symbols-outlined text-[16px]">data_object</span>
                                                        {displayValue}
                                                    </span>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Workflow Visualizer */}
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
                        <h4 className="text-sm font-bold text-slate-800 mb-6 flex items-center gap-2">
                            <span className="material-symbols-outlined text-primary">timeline</span>
                            مسیر گردش کار (۴ سطح تأیید)
                        </h4>
                        <div className="flex flex-col md:flex-row items-center justify-between relative gap-4 text-xs">
                            <div className="hidden md:block absolute top-[14px] right-8 left-8 h-[2px] bg-slate-100 -z-0"></div>

                            {/* Step: Draft */}
                            <div className="flex flex-col items-center gap-2 z-10 opacity-50">
                                <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-500 flex items-center justify-center border-2 border-white">
                                    <span className="material-symbols-outlined text-[18px]">edit_note</span>
                                </div>
                                <span className="font-medium text-slate-500">پیش‌نویس</span>
                            </div>

                            {/* Step: Pending L1 */}
                            <div className="flex flex-col items-center gap-2 z-10 relative">
                                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-white text-[10px] px-2 py-0.5 rounded-full whitespace-nowrap shadow-sm animate-bounce">
                                    مرحله بعدی
                                </div>
                                <div className="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center border-4 border-blue-100 shadow-lg">
                                    <span className="material-symbols-outlined text-[18px]">supervisor_account</span>
                                </div>
                                <span className="font-bold text-primary">ناظر قسمت</span>
                            </div>

                            {/* Step: Pending L2 */}
                            <div className="flex flex-col items-center gap-2 z-10 opacity-40 grayscale">
                                <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-500 flex items-center justify-center border-2 border-white">
                                    <span className="material-symbols-outlined text-[18px]">engineering</span>
                                </div>
                                <span className="font-medium text-slate-500">مدیر اداره</span>
                            </div>

                            {/* Step: Pending L3 */}
                            <div className="flex flex-col items-center gap-2 z-10 opacity-40 grayscale">
                                <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-500 flex items-center justify-center border-2 border-white">
                                    <span className="material-symbols-outlined text-[18px]">domain</span>
                                </div>
                                <span className="font-medium text-slate-500">معاون حوزه</span>
                            </div>

                            {/* Step: Pending L4 */}
                            <div className="flex flex-col items-center gap-2 z-10 opacity-40 grayscale">
                                <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-500 flex items-center justify-center border-2 border-white">
                                    <span className="material-symbols-outlined text-[18px]">account_balance</span>
                                </div>
                                <span className="font-medium text-slate-500">ذی‌حساب</span>
                            </div>

                            {/* Step: Approved */}
                            <div className="flex flex-col items-center gap-2 z-10 opacity-40 grayscale">
                                <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-500 flex items-center justify-center border-2 border-white">
                                    <span className="material-symbols-outlined text-[18px]">verified</span>
                                </div>
                                <span className="font-medium text-slate-500">تصویب نهایی</span>
                            </div>
                        </div>

                        <div className="mt-6 bg-blue-50 p-3 rounded border border-blue-100 flex gap-3 items-start">
                            <span className="material-symbols-outlined text-primary mt-0.5">info</span>
                            <p className="text-xs text-blue-800 leading-relaxed">
                                این صورت‌وضعیت پس از ثبت به ترتیب توسط ناظر قسمت، مدیر اداره، معاون حوزه و ذی‌حساب بررسی و تأیید خواهد شد. پس از تأیید نهایی، کد یکتای پرداخت صادر می‌شود.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Sidebar / Actions */}
                <div className="lg:col-span-1 space-y-6">
                    {/* Action Buttons */}
                    <div className="sticky top-24 space-y-4">
                        <button
                            type="button"
                            onClick={onSubmit}
                            disabled={isSubmitting}
                            className="w-full h-12 bg-primary text-white font-bold rounded-xl shadow-sm hover:bg-blue-700 focus:ring-4 focus:ring-primary/20 transition-all flex items-center justify-center gap-3 group disabled:opacity-50"
                        >
                            {isSubmitting ? (
                                <span className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                            ) : (
                                <>
                                    <span>ثبت و ارجاع به ناظر</span>
                                    <span className="material-symbols-outlined group-hover:-translate-x-1 transition-transform">send</span>
                                </>
                            )}
                        </button>

                        {onPrev && (
                            <button
                                type="button"
                                onClick={onPrev}
                                className="w-full bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 hover:text-slate-900 font-bold h-12 rounded-xl transition-colors flex items-center justify-center gap-2 focus:ring-4 focus:ring-slate-100"
                            >
                                <span className="material-symbols-outlined">arrow_forward</span>
                                مرحله قبل
                            </button>
                        )}

                        <div className="flex items-center justify-center gap-4 pt-2">
                            <button type="button" className="text-slate-400 hover:text-slate-600 text-xs flex items-center gap-1 transition-colors">
                                <span className="material-symbols-outlined text-[16px]">save</span>
                                ذخیره موقت
                            </button>
                            <button type="button" className="text-slate-400 hover:text-red-500 text-xs flex items-center gap-1 transition-colors">
                                <span className="material-symbols-outlined text-[16px]">delete</span>
                                لغو
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
