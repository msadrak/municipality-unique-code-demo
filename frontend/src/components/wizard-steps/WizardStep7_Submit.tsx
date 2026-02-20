import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    AlertTriangle,
    CheckCircle,
    ClipboardCopy,
    LayoutDashboard,
    Loader2,
    RefreshCcw,
    ShieldCheck,
} from 'lucide-react';

import type { TransactionFormData } from '../TransactionWizard';
import { createTransaction, type TransactionCreateData } from '../../services/adapters';
import { blockBudgetFunds } from '../../services/budgetValidation';
import { formatRial } from '../../lib/utils';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import { Button } from '../ui/button';
import { Card } from '../ui/card';

type SubmissionPhase = 'gate' | 'block' | 'create';

type SubmissionError = {
    phase: SubmissionPhase;
    message: string;
};

type Props = {
    formData: TransactionFormData;
    onResetWizard?: () => void;
};

const budgetService = {
    blockFunds: async (params: {
        budgetRowId: number;
        amount: number;
        referenceId?: string;
        notes?: string;
    }) => {
        return blockBudgetFunds(
            params.budgetRowId,
            params.amount,
            params.referenceId,
            params.notes
        );
    },
};

const transactionService = {
    create: async (formData: TransactionFormData): Promise<{ unique_code: string }> => {
        if (
            !formData.zoneId ||
            !formData.budgetCode ||
            !formData.beneficiaryName ||
            !formData.amount
        ) {
            throw new Error('اطلاعات اجباری تراکنش کامل نیست.');
        }

        const payload: TransactionCreateData = {
            credit_request_id: formData.creditRequestId,
            zone_id: formData.zoneId,
            department_id: formData.departmentId,
            section_id: formData.sectionId,
            budget_code: formData.budgetCode,
            cost_center_code: formData.costCenterCode,
            continuous_activity_code: formData.continuousActionCode,
            financial_event_code: formData.financialEventCode,
            beneficiary_name: formData.beneficiaryName,
            contract_number: formData.contractNumber,
            amount: formData.amount,
            description: formData.description,
            form_data: formData.formData,
        };

        const response = await createTransaction(payload);
        return { unique_code: response.unique_code };
    },
};

export function WizardStep7_Submit({ formData, onResetWizard }: Props) {
    const navigate = useNavigate();

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [uniqueCode, setUniqueCode] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);
    const [submitError, setSubmitError] = useState<SubmissionError | null>(null);

    const canSubmit = useMemo(() => {
        return Boolean(
            formData.creditRequestId &&
                formData.zoneId &&
                formData.budgetItemId &&
                formData.budgetCode &&
                formData.beneficiaryName &&
                formData.amount &&
                formData.amount > 0
        );
    }, [formData]);

    const phaseTitle: Record<SubmissionPhase, string> = {
        gate: 'خطا در مرحله گیت اعتباری',
        block: 'خطا در مسدودسازی بودجه',
        create: 'خطا در ایجاد تراکنش',
    };

    const handleSubmit = async () => {
        setSubmitError(null);

        if (!formData.creditRequestId) {
            setSubmitError({
                phase: 'gate',
                message: 'درخواست تامین اعتبار انتخاب نشده است.',
            });
            return;
        }

        if (!formData.budgetItemId || !formData.amount) {
            setSubmitError({
                phase: 'block',
                message: 'اطلاعات بودجه برای مسدودسازی کامل نیست.',
            });
            return;
        }

        setIsSubmitting(true);

        try {
            await budgetService.blockFunds({
                budgetRowId: formData.budgetItemId,
                amount: formData.amount,
                referenceId: formData.uniqueCode || `TXN-${Date.now()}`,
                notes: `Block before transaction create: ${formData.beneficiaryName || '-'}`,
            });
        } catch (error) {
            const detail = error instanceof Error ? error.message : 'خطای نامشخص';
            setSubmitError({
                phase: 'block',
                message: `بودجه مسدود نشد. ${detail}`,
            });
            setIsSubmitting(false);
            return;
        }

        try {
            const result = await transactionService.create(formData);
            setUniqueCode(result.unique_code);
        } catch (error) {
            const detail = error instanceof Error ? error.message : 'خطای نامشخص';
            setSubmitError({
                phase: 'create',
                message: `ایجاد تراکنش انجام نشد. ${detail}`,
            });
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleCopyCode = async () => {
        if (!uniqueCode) return;
        try {
            await navigator.clipboard.writeText(uniqueCode);
            setCopied(true);
            window.setTimeout(() => setCopied(false), 1500);
        } catch {
            setSubmitError({
                phase: 'create',
                message: 'کپی کد امکان‌پذیر نیست. لطفا کد را دستی کپی کنید.',
            });
        }
    };

    const handleNewTransaction = () => {
        if (onResetWizard) {
            onResetWizard();
            return;
        }
        setUniqueCode(null);
        setSubmitError(null);
        setCopied(false);
    };

    if (uniqueCode) {
        return (
            <Card className="border-emerald-200 bg-emerald-50/40 p-8 text-center">
                <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-emerald-100">
                    <CheckCircle className="h-12 w-12 animate-pulse text-emerald-600" />
                </div>

                <h3 className="text-2xl font-bold text-emerald-900">
                    تراکنش با موفقیت ثبت شد
                </h3>
                <p className="mt-2 text-sm text-emerald-800">
                    شناسه یکتای تراکنش ایجاد و ذخیره شد.
                </p>

                <div className="mx-auto mt-6 max-w-xl rounded-xl border border-slate-200 bg-slate-100 px-4 py-6">
                    <p className="mb-2 text-xs text-slate-500">کد یکتای تراکنش</p>
                    <div className="text-3xl font-mono font-bold tracking-wider text-slate-900">
                        {uniqueCode}
                    </div>
                </div>

                <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-3">
                    <Button variant="outline" onClick={handleCopyCode} className="gap-2">
                        <ClipboardCopy className="h-4 w-4" />
                        {copied ? 'کپی شد' : 'Copy Code'}
                    </Button>

                    <Button
                        variant="outline"
                        onClick={handleNewTransaction}
                        className="gap-2"
                    >
                        <RefreshCcw className="h-4 w-4" />
                        New Transaction
                    </Button>

                    <Button onClick={() => navigate('/portal')} className="gap-2">
                        <LayoutDashboard className="h-4 w-4" />
                        Go to Dashboard
                    </Button>
                </div>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h3 className="text-xl font-semibold">ثبت نهایی تراکنش</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                    در این مرحله ابتدا بودجه مسدود می‌شود و سپس تراکنش ایجاد خواهد شد.
                </p>
            </div>

            <Card className="space-y-3 p-5">
                <div className="flex items-center justify-between border-b pb-2 text-sm">
                    <span className="text-muted-foreground">درخواست تامین اعتبار</span>
                    <span className="font-mono">
                        {formData.creditRequestCode || 'انتخاب نشده'}
                    </span>
                </div>
                <div className="flex items-center justify-between border-b pb-2 text-sm">
                    <span className="text-muted-foreground">ردیف بودجه</span>
                    <span className="font-mono">{formData.budgetCode || '-'}</span>
                </div>
                <div className="flex items-center justify-between border-b pb-2 text-sm">
                    <span className="text-muted-foreground">ذینفع</span>
                    <span>{formData.beneficiaryName || '-'}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">مبلغ</span>
                    <span className="font-mono-num">{formatRial(formData.amount)}</span>
                </div>
            </Card>

            {!formData.creditRequestId && (
                <Alert className="border-amber-200 bg-amber-50 text-amber-900">
                    <ShieldCheck className="h-4 w-4 text-amber-700" />
                    <AlertTitle>گیت اعتباری فعال است</AlertTitle>
                    <AlertDescription className="text-amber-800">
                        ابتدا باید یک درخواست تامین اعتبار تایید‌شده انتخاب شود.
                    </AlertDescription>
                </Alert>
            )}

            {submitError && (
                <Alert className="border-rose-200 bg-rose-50 text-rose-900">
                    <AlertTriangle className="h-4 w-4 text-rose-700" />
                    <AlertTitle>{phaseTitle[submitError.phase]}</AlertTitle>
                    <AlertDescription className="text-rose-800">
                        {submitError.message}
                    </AlertDescription>
                </Alert>
            )}

            <div className="pt-2">
                <Button
                    onClick={handleSubmit}
                    className="w-full bg-emerald-600 hover:bg-emerald-700"
                    disabled={isSubmitting || !canSubmit}
                >
                    {isSubmitting ? (
                        <>
                            <Loader2 className="ml-2 h-4 w-4 animate-spin" />
                            در حال ثبت تراکنش...
                        </>
                    ) : (
                        'ثبت نهایی تراکنش'
                    )}
                </Button>
            </div>
        </div>
    );
}

export default WizardStep7_Submit;
