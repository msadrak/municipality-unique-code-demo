import React, { useCallback } from 'react';
import { useFormContext } from 'react-hook-form';
import type { ProgressStatementFormData } from '../ProgressStatementWizard';
import { formatNumber, formatAmountAbbreviated } from '../../lib/utils';

/**
 * Format a raw numeric string with commas for display while typing.
 * Strips non-digits, returns the formatted string + the raw integer.
 */
function parseAndFormat(raw: string): { display: string; value: number } {
    const digits = raw.replace(/[^\d]/g, '');
    if (!digits) return { display: '', value: 0 };
    const num = parseInt(digits, 10);
    const display = num.toLocaleString('en-US');
    return { display, value: num };
}

/** Convert Rials to a human-readable Toman equivalent */
function rialToTomanLabel(rials: number): string {
    if (!rials || rials === 0) return '';
    const tomans = Math.floor(rials / 10);
    return `معادل ${formatAmountAbbreviated(tomans)} تومان`;
}

/** Deduction field config for rendering */
const DEDUCTION_FIELDS = [
    {
        key: 'insuranceDeduction' as const,
        label: 'کسور بیمه',
        icon: 'health_and_safety',
        placeholder: '۰',
    },
    {
        key: 'taxDeduction' as const,
        label: 'کسور مالیات',
        icon: 'receipt_long',
        placeholder: '۰',
    },
    {
        key: 'advancePaymentAmount' as const,
        label: 'کسر پیش‌پرداخت',
        icon: 'currency_exchange',
        placeholder: '۰',
    },
    {
        key: 'otherDeductions' as const,
        label: 'سایر کسورات',
        icon: 'more_horiz',
        placeholder: '۰',
    },
] as const;

type DeductionFieldKey = typeof DEDUCTION_FIELDS[number]['key'];

export function PSStep2_Financials() {
    const {
        watch,
        setValue,
        formState: { errors },
    } = useFormContext<ProgressStatementFormData>();

    const grossAmount = watch('grossAmount') || 0;
    const insuranceDeduction = watch('insuranceDeduction') || 0;
    const taxDeduction = watch('taxDeduction') || 0;
    const advancePaymentAmount = watch('advancePaymentAmount') || 0;
    const otherDeductions = watch('otherDeductions') || 0;

    const totalDeductions = insuranceDeduction + taxDeduction + advancePaymentAmount + otherDeductions;
    const netAmount = grossAmount - totalDeductions;

    // Controlled input handler for Rial fields
    const handleRialChange = useCallback(
        (field: 'grossAmount' | DeductionFieldKey, inputValue: string) => {
            const { value } = parseAndFormat(inputValue);
            setValue(field, value, { shouldValidate: true });
        },
        [setValue]
    );

    // Display value for inputs (formatted with commas)
    const grossDisplay = grossAmount ? grossAmount.toLocaleString('en-US') : '';

    const deductionValues: Record<DeductionFieldKey, number> = {
        insuranceDeduction,
        taxDeduction,
        advancePaymentAmount,
        otherDeductions,
    };

    return (
        <div className="flex flex-col gap-8">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-xl font-bold text-slate-900 mb-1">مبالغ مالی صورت‌وضعیت</h2>
                    <p className="text-slate-500 text-sm">لطفاً مبالغ مالی اصلی صورت‌وضعیت را با دقت وارد کنید.</p>
                </div>
                <div className="bg-blue-50 text-blue-700 px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2">
                    <span className="material-symbols-outlined text-[20px]">info</span>
                    <span>مبالغ به ریال وارد شود</span>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-8">
                {/* Gross Amount */}
                <div className="group">
                    <label className="block text-slate-700 text-sm font-bold mb-3" htmlFor="ps-gross">
                        مبلغ ناخالص کارکرد (ریال) <span className="text-red-500">*</span>
                    </label>
                    <div className="relative flex items-center">
                        <input
                            id="ps-gross"
                            type="text"
                            inputMode="numeric"
                            dir="ltr"
                            value={grossDisplay}
                            onChange={(e) => handleRialChange('grossAmount', e.target.value)}
                            placeholder="0"
                            className="w-full h-12 pr-4 pl-12 rounded-xl bg-white border border-slate-300 text-slate-900 text-lg font-mono focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all shadow-sm placeholder-slate-400"
                            style={{ textAlign: 'right' }}
                        />
                        <div className="absolute left-4 text-slate-400 pointer-events-none flex items-center">
                            <span className="material-symbols-outlined">attach_money</span>
                        </div>
                    </div>
                    {grossAmount > 0 && (
                        <div className="mt-2 flex items-center gap-2 text-slate-500 text-xs font-medium pr-1">
                            <span className="material-symbols-outlined text-[16px] text-green-500">check_circle</span>
                            <span>{rialToTomanLabel(grossAmount)}</span>
                        </div>
                    )}
                    {errors.grossAmount && (
                        <p className="text-sm text-red-500 mt-1">{errors.grossAmount.message}</p>
                    )}
                </div>

                {/* Deduction Breakdown */}
                <div>
                    <h3 className="text-base font-bold text-slate-800 mb-4 flex items-center gap-2">
                        <span className="w-1 h-5 bg-red-400 rounded-full"></span>
                        جزئیات کسورات
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                        {DEDUCTION_FIELDS.map((field) => {
                            const fieldValue = deductionValues[field.key];
                            const display = fieldValue ? fieldValue.toLocaleString('en-US') : '';

                            return (
                                <div key={field.key} className="group">
                                    <label className="block text-slate-700 text-sm font-bold mb-2" htmlFor={`ps-${field.key}`}>
                                        {field.label}
                                    </label>
                                    <div className="relative flex items-center">
                                        <input
                                            id={`ps-${field.key}`}
                                            type="text"
                                            inputMode="numeric"
                                            dir="ltr"
                                            value={display}
                                            onChange={(e) => handleRialChange(field.key, e.target.value)}
                                            placeholder="0"
                                            className="w-full h-12 pr-4 pl-10 rounded-xl bg-white border border-slate-300 text-slate-900 text-base font-mono focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all shadow-sm placeholder-slate-400"
                                            style={{ textAlign: 'right' }}
                                        />
                                        <div className="absolute left-3 text-slate-400 pointer-events-none flex items-center">
                                            <span className="material-symbols-outlined text-[20px]">{field.icon}</span>
                                        </div>
                                    </div>
                                    {fieldValue > 0 && (
                                        <div className="mt-1 text-xs text-slate-400 pr-1">
                                            {rialToTomanLabel(fieldValue)}
                                        </div>
                                    )}
                                    {errors[field.key] && (
                                        <p className="text-sm text-red-500 mt-1">{(errors[field.key] as any)?.message}</p>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Summary Box */}
                <div className={`rounded-xl p-6 border flex flex-col gap-4 mt-2 ${netAmount < 0
                    ? 'bg-gradient-to-l from-red-50 to-red-100 border-red-200'
                    : 'bg-gradient-to-l from-primary/5 to-primary/10 border-primary/20'
                    }`}>
                    {/* Total deductions row */}
                    <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-600 font-medium">جمع کسورات:</span>
                        <span className="font-mono font-bold text-red-500" dir="ltr">- {formatNumber(totalDeductions)} ریال</span>
                    </div>

                    <div className="h-px bg-slate-200/50"></div>

                    {/* Net amount row */}
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="bg-white p-2 rounded-lg text-primary shadow-sm" style={netAmount < 0 ? { color: '#dc2626' } : {}}>
                                <span className="material-symbols-outlined">calculate</span>
                            </div>
                            <div className="flex flex-col">
                                <span className="text-sm text-slate-600 font-medium">مبلغ خالص (محاسبه‌شده)</span>
                                {netAmount < 0 ? (
                                    <span className="text-xs text-red-500 font-bold">⚠ کسورات بیشتر از کارکرد است</span>
                                ) : (
                                    <span className="text-xs text-slate-400">مبلغ نهایی پرداختی به پیمانکار</span>
                                )}
                            </div>
                        </div>
                        <div className="text-2xl font-black text-primary tracking-tight font-mono" style={netAmount < 0 ? { color: '#dc2626' } : {}}>
                            <span dir="ltr">{formatNumber(netAmount)}</span> <span className="text-sm font-bold text-slate-500 align-middle mr-1">ریال</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
