import React from 'react';
import { useFormContext } from 'react-hook-form';
import type { ProgressStatementFormData } from '../ProgressStatementWizard';
import type { ContractTemplateSchema, ContractTemplateSchemaProperty } from '../../services/contracts';
import { getTodayJalaliDate } from '../../lib/utils';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
interface PSStep3Props {
    schema?: ContractTemplateSchema | null;
    schemaLoading?: boolean;
}

// ---------------------------------------------------------------------------
// Icon map for common field names → Material Symbols icon name
// ---------------------------------------------------------------------------
const FIELD_ICON_MAP: Record<string, string> = {
    tracking_code: 'qr_code',
    volume: 'straighten',
    area: 'square_foot',
    weight: 'scale',
    length: 'straighten',
    fee: 'payments',
    cost: 'payments',
    amount: 'payments',
    price: 'payments',
    date: 'calendar_today',
    description: 'notes',
    note: 'notes',
    count: 'tag',
    quantity: 'tag',
};

function getFieldIcon(key: string): string {
    const lower = key.toLowerCase();
    for (const [pattern, icon] of Object.entries(FIELD_ICON_MAP)) {
        if (lower.includes(pattern)) return icon;
    }
    return 'data_object';
}

// ---------------------------------------------------------------------------
// Determine if a field should render as textarea
// ---------------------------------------------------------------------------
function isTextArea(key: string, prop: ContractTemplateSchemaProperty): boolean {
    const lower = key.toLowerCase();
    const titleLower = (prop.title || '').toLowerCase();
    const descLower = (prop.description || '').toLowerCase();

    // Persian keywords that hint at multi-line input
    const multilineHints = ['توضیحات', 'شرح', 'یادداشت', 'description', 'note', 'comment', 'remarks'];
    return multilineHints.some(
        (h) => lower.includes(h) || titleLower.includes(h) || descLower.includes(h),
    );
}

// ---------------------------------------------------------------------------
// Single dynamic field component
// ---------------------------------------------------------------------------
function DynamicField({
    fieldKey,
    prop,
    isRequired,
}: {
    fieldKey: string;
    prop: ContractTemplateSchemaProperty;
    isRequired: boolean;
}) {
    const { register } = useFormContext<ProgressStatementFormData>();
    const fieldName = `template_data.${fieldKey}` as const;
    const label = prop.title || fieldKey;
    const icon = getFieldIcon(fieldKey);
    const id = `ps-dyn-${fieldKey}`;

    // ---- Boolean → checkbox ----
    if (prop.type === 'boolean') {
        return (
            <div className="flex items-center gap-3 p-4 bg-slate-50 rounded-xl border border-slate-200">
                <input
                    id={id}
                    type="checkbox"
                    className="h-5 w-5 rounded border-slate-300 text-primary focus:ring-primary"
                    {...register(fieldName as any)}
                />
                <label htmlFor={id} className="text-sm font-medium text-slate-700 select-none">
                    {label}
                    {isRequired && <span className="text-red-500 mr-1">*</span>}
                </label>
            </div>
        );
    }

    // ---- Enum → select ----
    if (prop.type === 'string' && prop.enum && prop.enum.length > 0) {
        return (
            <div className="flex flex-col gap-2">
                <label className="text-sm font-bold text-slate-700" htmlFor={id}>
                    {label}
                    {isRequired && <span className="text-red-500 mr-1">*</span>}
                </label>
                <div className="relative">
                    <select
                        id={id}
                        className="w-full h-12 rounded-xl border border-slate-300 bg-white text-slate-900 px-4 pr-10 focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all shadow-sm appearance-none"
                        {...register(fieldName as any)}
                        defaultValue={prop.default as string | undefined}
                    >
                        <option value="">انتخاب کنید...</option>
                        {prop.enum.map((opt) => (
                            <option key={opt} value={opt}>
                                {opt}
                            </option>
                        ))}
                    </select>
                    <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none text-slate-400">
                        <span className="material-symbols-outlined text-lg">{icon}</span>
                    </div>
                </div>
                {prop.description && <p className="text-xs text-slate-500">{prop.description}</p>}
            </div>
        );
    }

    // ---- Textarea ----
    if (prop.type === 'string' && isTextArea(fieldKey, prop)) {
        return (
            <div className="flex flex-col gap-2 md:col-span-2">
                <label className="text-sm font-bold text-slate-700" htmlFor={id}>
                    {label}
                    {isRequired && <span className="text-red-500 mr-1">*</span>}
                </label>
                <textarea
                    id={id}
                    rows={4}
                    placeholder={prop.description || `${label} را وارد کنید...`}
                    className="w-full rounded-xl border border-slate-300 bg-white text-slate-900 p-4 focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all shadow-sm resize-none"
                    {...register(fieldName as any)}
                ></textarea>
                {prop.description && <p className="text-xs text-slate-500">{prop.description}</p>}
            </div>
        );
    }

    // ---- Number / Integer ----
    if (prop.type === 'number' || prop.type === 'integer') {
        return (
            <div className="flex flex-col gap-2">
                <label className="text-sm font-bold text-slate-700" htmlFor={id}>
                    {label}
                    {isRequired && <span className="text-red-500 mr-1">*</span>}
                </label>
                <div className="relative">
                    <input
                        id={id}
                        type="number"
                        dir="ltr"
                        placeholder={prop.description || '0'}
                        min={prop.minimum}
                        max={prop.maximum}
                        className="w-full h-12 rounded-xl border border-slate-300 bg-white text-slate-900 px-4 pl-10 focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all shadow-sm text-right placeholder:text-right"
                        {...register(fieldName as any, { valueAsNumber: true })}
                    />
                    <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none text-slate-400">
                        <span className="material-symbols-outlined text-lg">{icon}</span>
                    </div>
                </div>
                {prop.description && <p className="text-xs text-slate-500">{prop.description}</p>}
            </div>
        );
    }

    // ---- Default: text input ----
    return (
        <div className="flex flex-col gap-2">
            <label className="text-sm font-bold text-slate-700" htmlFor={id}>
                {label}
                {isRequired && <span className="text-red-500 mr-1">*</span>}
            </label>
            <div className="relative">
                <input
                    id={id}
                    type="text"
                    placeholder={prop.description || `${label} را وارد کنید`}
                    className="w-full h-12 rounded-xl border border-slate-300 bg-white text-slate-900 px-4 pr-10 focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all shadow-sm"
                    {...register(fieldName as any)}
                />
                <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none text-slate-400">
                    <span className="material-symbols-outlined text-lg">{icon}</span>
                </div>
            </div>
            {prop.description && <p className="text-xs text-slate-500">{prop.description}</p>}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export function PSStep3_DepartmentSpecifics({ schema, schemaLoading }: PSStep3Props) {
    const { register } = useFormContext<ProgressStatementFormData>();

    const properties = schema?.properties ?? {};
    const requiredKeys = schema?.required ?? [];
    const entries = Object.entries(properties);

    return (
        <div className="flex flex-col gap-8">
            {/* Header Section */}
            <div className="flex items-start gap-4">
                <div className="hidden md:flex size-14 bg-primary/10 rounded-xl items-center justify-center text-primary shrink-0">
                    <span className="material-symbols-outlined text-3xl">folder_special</span>
                </div>
                <div className="flex-1">
                    <h2 className="text-xl md:text-2xl font-bold text-slate-900 mb-2">مرحله ۳: اطلاعات اختصاصی</h2>
                    <p className="text-slate-500 text-base leading-relaxed">
                        اطلاعات تکمیلی صورت‌وضعیت شامل معاونت صادرکننده، دوره زمانی و داده‌های اختصاصی را وارد کنید.
                    </p>
                </div>
            </div>

            {/* Originating Organ & Period Section — always present */}
            <section>
                <h3 className="text-base font-bold text-slate-800 mb-4 flex items-center gap-2">
                    <span className="w-1 h-5 bg-primary rounded-full"></span>
                    مشخصات سازمانی و دوره
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Originating Organ */}
                    <div className="flex flex-col gap-2">
                        <label className="text-sm font-bold text-slate-700" htmlFor="ps-organ">
                            معاونت / حوزه صادرکننده
                        </label>
                        <div className="relative">
                            <input
                                id="ps-organ"
                                type="text"
                                placeholder="مثال: معاونت عمران شهری"
                                className="w-full h-12 rounded-xl border border-slate-300 bg-white text-slate-900 px-4 pr-10 focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all shadow-sm"
                                {...register('originatingOrgan')}
                            />
                            <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none text-slate-400">
                                <span className="material-symbols-outlined text-lg">corporate_fare</span>
                            </div>
                        </div>
                        <p className="text-xs text-slate-500">نام معاونت یا سازمان وابسته صادرکننده صورت‌وضعیت</p>
                    </div>

                    {/* Period Start */}
                    <div className="flex flex-col gap-2">
                        <label className="text-sm font-bold text-slate-700" htmlFor="ps-period-start">
                            تاریخ شروع دوره
                        </label>
                        <div className="relative">
                            <input
                                id="ps-period-start"
                                type="text"
                                placeholder={getTodayJalaliDate()}
                                className="w-full h-12 rounded-xl border border-slate-300 bg-white text-slate-900 px-4 pr-10 focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all shadow-sm"
                                {...register('periodStart')}
                            />
                            <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none text-slate-400">
                                <span className="material-symbols-outlined text-lg">calendar_today</span>
                            </div>
                        </div>
                    </div>

                    {/* Period End */}
                    <div className="flex flex-col gap-2">
                        <label className="text-sm font-bold text-slate-700" htmlFor="ps-period-end">
                            تاریخ پایان دوره
                        </label>
                        <div className="relative">
                            <input
                                id="ps-period-end"
                                type="text"
                                placeholder={getTodayJalaliDate()}
                                className="w-full h-12 rounded-xl border border-slate-300 bg-white text-slate-900 px-4 pr-10 focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all shadow-sm"
                                {...register('periodEnd')}
                            />
                            <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none text-slate-400">
                                <span className="material-symbols-outlined text-lg">event</span>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <div className="h-px bg-slate-100 w-full"></div>

            {/* Department-Specific Data Section — Dynamic */}
            <section>
                <h3 className="text-base font-bold text-slate-800 mb-4 flex items-center gap-2">
                    <span className="w-1 h-5 bg-sky-500 rounded-full"></span>
                    داده‌های اختصاصی
                </h3>

                {/* Info Banner */}
                <div className="flex items-start gap-3 p-4 bg-sky-50 border border-sky-100 rounded-xl text-sky-800 mb-6">
                    <span className="material-symbols-outlined shrink-0 text-sky-600">info</span>
                    <p className="text-sm font-medium leading-6">این بخش بسته به حوزه تخصصی هر معاونت و نوع قرارداد، فیلدهای متفاوتی را نمایش می‌دهد. اطلاعات وارد شده به صورت JSONB در سیستم ذخیره می‌شوند.</p>
                </div>

                {/* Loading state */}
                {schemaLoading && (
                    <div className="flex items-center justify-center py-12 gap-3 text-slate-400">
                        <span className="h-5 w-5 border-2 border-slate-300 border-t-primary rounded-full animate-spin"></span>
                        <span className="text-sm">در حال بارگذاری فیلدهای اختصاصی...</span>
                    </div>
                )}

                {/* Empty state — no schema or no properties */}
                {!schemaLoading && entries.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-12 gap-3 text-slate-400">
                        <span className="material-symbols-outlined text-4xl">playlist_remove</span>
                        <p className="text-sm">هیچ فیلد اختصاصی برای این قالب قرارداد تعریف نشده است.</p>
                    </div>
                )}

                {/* Dynamic fields */}
                {!schemaLoading && entries.length > 0 && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {entries.map(([key, prop]) => (
                            <DynamicField
                                key={key}
                                fieldKey={key}
                                prop={prop}
                                isRequired={requiredKeys.includes(key)}
                            />
                        ))}
                    </div>
                )}
            </section>
        </div>
    );
}
