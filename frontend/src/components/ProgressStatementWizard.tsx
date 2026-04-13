import React, { useState, useCallback, useEffect } from 'react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { motion, AnimatePresence } from 'framer-motion';
import { useParams, useNavigate } from 'react-router-dom';
import {
    CheckCircle2,
    FileText,
    Banknote,
    Settings2,
    Eye,
} from 'lucide-react';
import { Button } from './ui/button';
import { PSStep1_BasicInfo } from './ps-wizard-steps/PSStep1_BasicInfo';
import { PSStep2_Financials } from './ps-wizard-steps/PSStep2_Financials';
import { PSStep3_DepartmentSpecifics } from './ps-wizard-steps/PSStep3_DepartmentSpecifics';
import { PSStep4_ReviewSubmit } from './ps-wizard-steps/PSStep4_ReviewSubmit';
import { toast } from 'sonner';
import { createStatement, submitStatement, fetchContract, fetchContractTemplate } from '../services/contracts';
import type { StatementCreateRequest, StatementTypeEnum, ContractTemplateSchema } from '../services/contracts';

// ---------------------------------------------------------------------------
// Zod Schema — aligned with backend StatementCreate Pydantic schema
// ---------------------------------------------------------------------------
const progressStatementSchema = z.object({
    // Step 1: Basic Info
    statementType: z.enum(['INTERIM', 'FINAL', 'ADJUSTMENT', 'FINAL_ADJUSTMENT'], {
        message: 'نوع صورت‌وضعیت را انتخاب کنید',
    }),
    description: z
        .string({ required_error: 'شرح صورت‌وضعیت الزامی است' })
        .min(1, { message: 'شرح صورت‌وضعیت الزامی است' }),

    // Step 2: Financials (all amounts in Rials as integers)
    grossAmount: z
        .number({ required_error: 'مبلغ ناخالص الزامی است' })
        .int()
        .positive({ message: 'مبلغ ناخالص باید بزرگ‌تر از صفر باشد' }),
    insuranceDeduction: z
        .number()
        .int()
        .nonnegative({ message: 'مبلغ بیمه نمی‌تواند منفی باشد' })
        .default(0),
    taxDeduction: z
        .number()
        .int()
        .nonnegative({ message: 'مبلغ مالیات نمی‌تواند منفی باشد' })
        .default(0),
    advancePaymentAmount: z
        .number()
        .int()
        .nonnegative({ message: 'مبلغ پیش‌پرداخت نمی‌تواند منفی باشد' })
        .default(0),
    otherDeductions: z
        .number()
        .int()
        .nonnegative({ message: 'سایر کسورات نمی‌تواند منفی باشد' })
        .default(0),

    // Step 3: Department Specifics
    originatingOrgan: z.string().optional(),
    periodStart: z.string().optional(),
    periodEnd: z.string().optional(),

    // Dynamic department-specific fields (driven by ContractTemplate.schema_definition)
    template_data: z.record(z.any()).optional(),
});

export type ProgressStatementFormData = z.infer<typeof progressStatementSchema>;

// ---------------------------------------------------------------------------
// Step definitions
// ---------------------------------------------------------------------------
const STEPS = [
    {
        id: 0,
        title: 'اطلاعات پایه',
        icon: FileText,
        fields: ['statementType', 'description'] as const,
    },
    {
        id: 1,
        title: 'مبالغ مالی',
        icon: Banknote,
        fields: ['grossAmount', 'insuranceDeduction', 'taxDeduction', 'advancePaymentAmount', 'otherDeductions'] as const,
    },
    {
        id: 2,
        title: 'اطلاعات اختصاصی',
        icon: Settings2,
        fields: ['originatingOrgan', 'periodStart', 'periodEnd', 'template_data'] as const,
    },
    {
        id: 3,
        title: 'پیش‌نمایش و ارجاع',
        icon: Eye,
        fields: [] as const,
    },
] as const;

// Slide animation variants
const slideVariants = {
    enter: (direction: number) => ({
        x: direction > 0 ? 300 : -300,
        opacity: 0,
    }),
    center: {
        x: 0,
        opacity: 1,
    },
    exit: (direction: number) => ({
        x: direction > 0 ? -300 : 300,
        opacity: 0,
    }),
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export function ProgressStatementWizard() {
    const { contractId } = useParams<{ contractId: string }>();
    const navigate = useNavigate();

    const [currentStep, setCurrentStep] = useState(0);
    const [direction, setDirection] = useState(0); // 1 = forward, -1 = backward
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isSubmitted, setIsSubmitted] = useState(false);
    const [createdStatementNumber, setCreatedStatementNumber] = useState('');

    // Schema fetched from ContractTemplate for dynamic Step 3 fields
    const [schemaDefinition, setSchemaDefinition] = useState<ContractTemplateSchema | null>(null);
    const [schemaLoading, setSchemaLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        async function loadSchema() {
            if (!contractId) { setSchemaLoading(false); return; }
            try {
                const contract = await fetchContract(parseInt(contractId, 10));
                if (cancelled) return;
                if (contract.template_id) {
                    const template = await fetchContractTemplate(contract.template_id);
                    if (!cancelled) setSchemaDefinition(template.schema_definition ?? null);
                }
            } catch (err) {
                console.warn('Failed to load template schema:', err);
            } finally {
                if (!cancelled) setSchemaLoading(false);
            }
        }
        loadSchema();
        return () => { cancelled = true; };
    }, [contractId]);

    const methods = useForm<ProgressStatementFormData>({
        resolver: zodResolver(progressStatementSchema) as any,
        mode: 'onTouched',
        defaultValues: {
            description: '',
            grossAmount: undefined,
            insuranceDeduction: 0,
            taxDeduction: 0,
            advancePaymentAmount: 0,
            otherDeductions: 0,
            originatingOrgan: '',
            periodStart: '',
            periodEnd: '',
            template_data: {},
        },
    });

    const { trigger, getValues, reset } = methods;

    // Validate current step fields before moving forward
    const nextStep = useCallback(async () => {
        const step = STEPS[currentStep];
        if (step.fields.length > 0) {
            const valid = await trigger(step.fields as unknown as (keyof ProgressStatementFormData)[]);
            if (!valid) return;
        }
        setDirection(1);
        setCurrentStep((prev) => Math.min(prev + 1, STEPS.length - 1));
    }, [currentStep, trigger]);

    const prevStep = useCallback(() => {
        setDirection(-1);
        setCurrentStep((prev) => Math.max(prev - 1, 0));
    }, []);

    // Final submission — real API call
    const handleSubmit = useCallback(async () => {
        // Validate all fields one last time
        const valid = await trigger();
        if (!valid) {
            toast.error('لطفاً تمام فیلدهای الزامی را تکمیل کنید');
            return;
        }

        if (!contractId) {
            toast.error('شناسه قرارداد یافت نشد');
            return;
        }

        setIsSubmitting(true);

        try {
            const data = getValues();

            const totalDeductions =
                (data.insuranceDeduction || 0) +
                (data.taxDeduction || 0) +
                (data.advancePaymentAmount || 0) +
                (data.otherDeductions || 0);

            // Build the payload matching backend StatementCreate schema exactly
            const payload: StatementCreateRequest = {
                gross_amount: data.grossAmount,
                deductions: totalDeductions,
                description: data.description,
                statement_type: data.statementType as StatementTypeEnum,

                // Deduction breakdown
                insurance_deduction: data.insuranceDeduction || 0,
                tax_deduction: data.taxDeduction || 0,
                advance_payment_amount: data.advancePaymentAmount || 0,
                other_deductions: data.otherDeductions || 0,

                // Optional fields — only include if non-empty
                ...(data.originatingOrgan ? { originating_organ: data.originatingOrgan } : {}),
                ...(data.periodStart ? { period_start: data.periodStart } : {}),
                ...(data.periodEnd ? { period_end: data.periodEnd } : {}),

                // Department-specific JSONB data (dynamic from template schema)
                template_data: data.template_data || {},
            };

            // Step 1: Create the draft statement
            const created = await createStatement(parseInt(contractId, 10), payload);

            // Step 2: Immediately submit (DRAFT → PENDING_L1)
            await submitStatement(created.id);

            setCreatedStatementNumber(created.statement_number);
            toast.success('صورت‌وضعیت با موفقیت ثبت و ارجاع شد');
            setIsSubmitted(true);
        } catch (error: any) {
            console.error('Submission failed:', error);
            const message = error?.message || 'خطا در ثبت صورت‌وضعیت';
            toast.error(message);
        } finally {
            setIsSubmitting(false);
        }
    }, [trigger, getValues, contractId]);

    // Reset for new submission
    const handleReset = useCallback(() => {
        reset();
        setCurrentStep(0);
        setDirection(0);
        setIsSubmitted(false);
        setCreatedStatementNumber('');
    }, [reset]);

    // Success state
    if (isSubmitted) {
        return (
            <div className="min-h-screen flex items-center justify-center p-8 bg-slate-50 font-vazirmatn" dir="rtl">
                <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-10 max-w-md w-full text-center space-y-6">
                    <div className="flex justify-center">
                        <div className="bg-emerald-100 p-5 rounded-full">
                            <CheckCircle2 className="h-12 w-12 text-emerald-600" />
                        </div>
                    </div>
                    <div className="space-y-2">
                        <h2 className="text-xl font-bold text-slate-800">صورت‌وضعیت با موفقیت ثبت شد</h2>
                        {createdStatementNumber && (
                            <p className="text-sm text-slate-500">
                                شماره صورت‌وضعیت:
                                <span className="font-mono font-bold text-primary mx-1" dir="ltr">{createdStatementNumber}</span>
                            </p>
                        )}
                        <p className="text-sm text-slate-500">
                            صورت‌وضعیت شما به مرحله
                            <span className="font-semibold text-blue-600 mx-1">«در انتظار تایید ناظر»</span>
                            ارجاع شد
                        </p>
                    </div>
                    <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl text-sm leading-relaxed text-amber-800">
                        پس از بررسی و تایید ناظر، صورت‌وضعیت به مرحله تایید مدیر ارسال خواهد شد.
                    </div>
                    <div className="flex flex-col gap-3">
                        <Button onClick={handleReset} className="w-full h-12 rounded-xl">
                            ثبت صورت‌وضعیت جدید
                        </Button>
                        <Button
                            variant="outline"
                            onClick={() => navigate(`/contracts/${contractId}`)}
                            className="w-full h-12 rounded-xl"
                        >
                            بازگشت به قرارداد
                        </Button>
                    </div>
                </div>
            </div>
        );
    }

    const progress = ((currentStep + 1) / STEPS.length) * 100;

    return (
        <div className="w-full max-w-5xl mx-auto font-vazirmatn bg-slate-50 min-h-screen p-8" dir="rtl">
            {/* Page Title */}
            <div className="mb-8">
                <h1 className="text-3xl font-black text-slate-800 tracking-tight mb-2">ایجاد صورت‌وضعیت جدید</h1>
                <p className="text-slate-500 text-base">لطفاً مراحل زیر را برای ثبت اطلاعات صورت‌وضعیت بادقت تکمیل کنید.</p>
            </div>

            {/* Stepper */}
            <div className="mb-8 bg-white rounded-2xl p-6 shadow-sm border border-slate-100 hidden md:block">
                <div className="flex items-center justify-between relative">
                    <div className="absolute top-1/2 left-12 right-12 h-1 bg-slate-100 -translate-y-1/2 rounded-full z-0"></div>
                    <div
                        className="absolute top-1/2 right-12 h-1 bg-primary -translate-y-1/2 rounded-full z-0 transition-all duration-500"
                        style={{ width: STEPS.length > 1 ? `calc((100% - 6rem) * ${currentStep / (STEPS.length - 1)})` : '0%' }}
                    ></div>

                    {STEPS.map((step, idx) => {
                        const iconMap = ['description', 'payments', 'folder_special', 'summarize'];
                        const iconName = iconMap[idx];

                        const isCompleted = idx < currentStep;
                        const isCurrent = idx === currentStep;

                        let circleClass = "";
                        let textClass = "";

                        if (isCompleted) {
                            circleClass = "bg-primary text-white shadow-lg shadow-primary/30 border-4 border-white";
                            textClass = "text-sm font-bold text-slate-800";
                        } else if (isCurrent) {
                            circleClass = "bg-primary text-white shadow-lg shadow-primary/30 transform scale-110 border-4 border-white";
                            textClass = "text-sm font-bold text-primary";
                        } else {
                            circleClass = "bg-slate-50 text-slate-400 shadow-sm border-4 border-white";
                            textClass = "text-sm font-medium text-slate-400";
                        }

                        return (
                            <div key={step.id} className="relative z-10 flex flex-col items-center gap-3">
                                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center transition-all ${circleClass}`}>
                                    {isCompleted ? (
                                        <span className="material-symbols-outlined text-[24px]">check</span>
                                    ) : (
                                        <span className="material-symbols-outlined text-[24px]">{iconName}</span>
                                    )}
                                </div>
                                <span className={textClass}>{step.title}</span>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Step Content */}
            <FormProvider {...methods}>
                <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
                    {/* Animated step content */}
                    <AnimatePresence mode="wait" custom={direction}>
                        <motion.div
                            key={currentStep}
                            custom={direction}
                            variants={slideVariants}
                            initial="enter"
                            animate="center"
                            exit="exit"
                            transition={{ duration: 0.3, ease: 'easeInOut' }}
                        >
                            {currentStep === 0 && <PSStep1_BasicInfo />}
                            {currentStep === 1 && <PSStep2_Financials />}
                            {currentStep === 2 && <PSStep3_DepartmentSpecifics schema={schemaDefinition} schemaLoading={schemaLoading} />}
                            {currentStep === 3 && (
                                <PSStep4_ReviewSubmit
                                    onSubmit={handleSubmit}
                                    isSubmitting={isSubmitting}
                                    onPrev={prevStep}
                                    schema={schemaDefinition}
                                />
                            )}
                        </motion.div>
                    </AnimatePresence>

                    {/* Step Navigation for steps 1 to 3 */}
                    {currentStep < STEPS.length - 1 && (
                        <div className="mt-12 pt-6 border-t border-slate-200 flex items-center justify-between">
                            <button
                                type="button"
                                onClick={prevStep}
                                disabled={currentStep === 0}
                                className="group flex items-center gap-2 px-6 h-12 rounded-xl border border-slate-300 text-slate-700 font-bold hover:bg-slate-50 focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">arrow_forward</span>
                                مرحله قبل
                            </button>

                            <button
                                type="button"
                                onClick={nextStep}
                                className="group flex items-center gap-2 px-8 h-12 rounded-xl bg-primary text-white font-bold hover:bg-blue-700 shadow-sm focus:ring-4 focus:ring-primary/20 transition-all active:scale-95"
                            >
                                مرحله بعد
                                <span className="material-symbols-outlined group-hover:-translate-x-1 transition-transform">arrow_back</span>
                            </button>
                        </div>
                    )}
                </div>
            </FormProvider>
        </div>
    );
}
