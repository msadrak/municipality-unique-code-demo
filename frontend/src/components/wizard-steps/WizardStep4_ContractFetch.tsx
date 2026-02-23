import React, { useState, useCallback } from 'react';
import {
    Search,
    Loader2,
    CheckCircle2,
    AlertCircle,
    FileText,
    Download,
    ExternalLink,
    Building2,
    Hash,
    CalendarDays,
    Landmark,
    ShieldCheck,
} from 'lucide-react';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Alert, AlertTitle, AlertDescription } from '../ui/alert';
import { formatRial } from '../../lib/utils';
import {
    fetchContractByNumber,
    type ContractData,
} from '../../services/mockContractService';
import type { TransactionFormData } from '../TransactionWizard';

type Props = {
    formData: TransactionFormData;
    updateFormData: (data: Partial<TransactionFormData>) => void;
};

export function WizardStep4_ContractFetch({ formData, updateFormData }: Props) {
    const [inputCode, setInputCode] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [fetchedContract, setFetchedContract] = useState<ContractData | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleFetch = useCallback(async () => {
        const trimmed = inputCode.trim();
        if (!trimmed) return;

        setIsLoading(true);
        setError(null);
        setFetchedContract(null);

        // Clear previous fetched data from wizard state
        updateFormData({
            fetchedContractNumber: undefined,
            fetchedContractDate: undefined,
            fetchedGuaranteeNumber: undefined,
            fetchedGuaranteeBank: undefined,
            fetchedGuaranteeAmount: undefined,
            fetchedGuaranteeExpiryDate: undefined,
        });

        try {
            const result = await fetchContractByNumber(trimmed);
            setFetchedContract(result);

            // Push fetched data into wizard state
            updateFormData({
                fetchedContractNumber: result.contract_number,
                fetchedContractDate: result.contract_date,
                fetchedGuaranteeNumber: result.guarantee_number,
                fetchedGuaranteeBank: result.guarantee_bank,
                fetchedGuaranteeAmount: result.guarantee_amount,
                fetchedGuaranteeExpiryDate: result.guarantee_expiry_date,
            });
        } catch (err) {
            setError(
                err instanceof Error ? err.message : 'خطا در استعلام اطلاعات قرارداد',
            );
        } finally {
            setIsLoading(false);
        }
    }, [inputCode, updateFormData]);

    const handleKeyDown = useCallback(
        (e: React.KeyboardEvent) => {
            if (e.key === 'Enter' && inputCode.trim() && !isLoading) {
                handleFetch();
            }
        },
        [handleFetch, inputCode, isLoading],
    );

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h3 className="text-lg font-semibold">قرارداد و تضامین</h3>
                <p className="text-sm text-muted-foreground mt-1">
                    شماره ابلاغ قرارداد را وارد کنید تا اطلاعات قرارداد و ضمانت‌نامه از سامانه قراردادها دریافت شود.
                </p>
            </div>

            {/* Project context banner */}
            {formData.civilProjectTitle && (
                <div className="flex items-center gap-3 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3">
                    <Building2 className="h-5 w-5 text-primary flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-primary leading-snug truncate">
                            پروژه: {formData.civilProjectTitle}
                        </p>
                        <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
                            <Hash className="h-3 w-3" />
                            <span className="font-mono-num">{formData.civilProjectCode}</span>
                        </p>
                    </div>
                </div>
            )}

            {/* Input row */}
            <div className="flex items-end gap-3">
                <div className="flex-1 space-y-2">
                    <label className="flex items-center gap-2 text-sm font-medium select-none">
                        <span className="text-red-500">*</span>
                        شماره ابلاغ قرارداد
                    </label>
                    <Input
                        dir="ltr"
                        placeholder="شماره ابلاغ قرارداد را وارد کنید (مثال: 04/14120/س)"
                        className="font-mono-num text-left"
                        value={inputCode}
                        onChange={(e) => setInputCode(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={isLoading}
                    />
                </div>
                <Button
                    type="button"
                    onClick={handleFetch}
                    disabled={isLoading || !inputCode.trim()}
                >
                    {isLoading ? (
                        <Loader2 className="h-4 w-4 ml-2 animate-spin" />
                    ) : (
                        <Search className="h-4 w-4 ml-2" />
                    )}
                    استعلام از سامانه قراردادها
                </Button>
            </div>

            {/* Error alert */}
            {error && (
                <Alert variant="destructive" className="border-red-300 bg-red-50 text-red-900">
                    <AlertCircle className="h-4 w-4 text-red-700" />
                    <AlertTitle>خطا در استعلام</AlertTitle>
                    <AlertDescription className="text-red-800">{error}</AlertDescription>
                </Alert>
            )}

            {/* Contract & Guarantee Summary Card */}
            {fetchedContract && (
                <div className="space-y-4">
                    <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm space-y-5">
                        <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
                            <FileText className="h-5 w-5 text-primary" />
                            <h4 className="font-semibold text-primary">خلاصه قرارداد و تضامین</h4>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                            {/* Contract Number */}
                            <div className="space-y-1">
                                <p className="text-xs text-muted-foreground">شماره قرارداد</p>
                                <p className="font-mono-num text-sm font-medium">
                                    {fetchedContract.contract_number}
                                </p>
                            </div>

                            {/* Contract Date */}
                            <div className="space-y-1">
                                <p className="text-xs text-muted-foreground flex items-center gap-1">
                                    <CalendarDays className="h-3 w-3" />
                                    تاریخ قرارداد
                                </p>
                                <p
                                    dir="ltr"
                                    className="font-mono-num text-sm font-medium text-left"
                                >
                                    {fetchedContract.contract_date}
                                </p>
                            </div>

                            {/* Guarantee Bank */}
                            <div className="space-y-1">
                                <p className="text-xs text-muted-foreground flex items-center gap-1">
                                    <Landmark className="h-3 w-3" />
                                    بانک ضمانت‌نامه
                                </p>
                                <p className="text-sm font-medium leading-6">
                                    {fetchedContract.guarantee_bank}
                                </p>
                            </div>

                            {/* Guarantee Number */}
                            <div className="space-y-1">
                                <p className="text-xs text-muted-foreground flex items-center gap-1">
                                    <ShieldCheck className="h-3 w-3" />
                                    شماره ضمانت‌نامه
                                </p>
                                <p
                                    dir="ltr"
                                    className="font-mono-num text-sm font-medium text-left"
                                >
                                    {fetchedContract.guarantee_number}
                                </p>
                            </div>

                            {/* Guarantee Expiry Date */}
                            <div className="space-y-1">
                                <p className="text-xs text-muted-foreground flex items-center gap-1">
                                    <CalendarDays className="h-3 w-3" />
                                    تاریخ انقضای ضمانت‌نامه
                                </p>
                                <p
                                    dir="ltr"
                                    className="font-mono-num text-sm font-medium text-left"
                                >
                                    {fetchedContract.guarantee_expiry_date}
                                </p>
                            </div>

                            {/* Guarantee Amount */}
                            <div className="space-y-1 md:col-span-2 pt-2 border-t border-slate-100">
                                <p className="text-xs text-muted-foreground">مبلغ ضمانت‌نامه (ریال)</p>
                                <p className="font-mono-num text-xl font-bold text-primary">
                                    {formatRial(fetchedContract.guarantee_amount)}
                                </p>
                            </div>
                        </div>

                        <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t border-slate-100">
                            <Button variant="outline" asChild className="sm:w-auto">
                                <a
                                    href={fetchedContract.contract_file_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    <ExternalLink className="h-4 w-4" />
                                    مشاهده تصویر قرارداد
                                </a>
                            </Button>
                            <Button variant="outline" asChild className="sm:w-auto">
                                <a
                                    href={fetchedContract.guarantee_file_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    download
                                >
                                    <Download className="h-4 w-4" />
                                    دانلود سند ضمانت‌نامه
                                </a>
                            </Button>
                        </div>
                    </div>

                    <Alert className="border-emerald-200 bg-emerald-50 text-emerald-900">
                        <CheckCircle2 className="h-4 w-4 text-emerald-700" />
                        <AlertTitle>اطلاعات قرارداد و تضامین دریافت شد</AlertTitle>
                        <AlertDescription className="text-emerald-800">
                            اطلاعات مالی تأیید شده و آماده ثبت نهایی است. برای ادامه به مرحله بعد بروید.
                        </AlertDescription>
                    </Alert>
                </div>
            )}
        </div>
    );
}
