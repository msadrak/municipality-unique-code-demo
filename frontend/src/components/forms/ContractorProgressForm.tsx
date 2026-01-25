import React, { useState, useEffect, useMemo } from 'react';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Card } from '../ui/card';
import { TransactionFormData } from '../TransactionWizard';
import { User, FileText, DollarSign, Building2, Calculator, Percent } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';

type Props = {
    formData: TransactionFormData;
    updateFormData: (data: Partial<TransactionFormData>) => void;
    onFormDataChange: (data: Record<string, unknown>) => void;
};

/**
 * محاسبه صورت وضعیت پیمانکاران - Contractor Progress Form
 * Based on employer image 1: Full contractor payment form with deductions
 * 
 * Fields:
 * - شماره پیمانکار, شماره قرارداد, مبلغ قرارداد, صورت وضعیت
 * - نوع قرارداد, دریافت کننده وجه, شماره موضوع, مرکز هزینه
 * - Deductions: مالیات 3%, بیمه 5%, حسن انجام کار 10%, کارآموزی 0.2%
 * - توضیحات
 */
export function ContractorProgressForm({ formData, updateFormData, onFormDataChange }: Props) {
    const [localData, setLocalData] = useState({
        contractorNumber: '',
        contractNumber: formData.contractNumber || '',
        contractAmount: 0,
        progressNumber: '',
        contractType: 'عمرانی',
        recipientName: formData.beneficiaryName || '',
        subjectNumber: '',
        costCenter: formData.costCenterName || '',
        grossAmount: 0,
        notes: formData.description || '',
        // Deduction percentages
        taxRate: 3,
        insuranceRate: 5,
        performanceRate: 10,
        apprenticeRate: 0.2,
    });

    // Calculate deductions
    const calculations = useMemo(() => {
        const gross = localData.grossAmount;
        const tax = Math.round(gross * localData.taxRate / 100);
        const insurance = Math.round(gross * localData.insuranceRate / 100);
        const performance = Math.round(gross * localData.performanceRate / 100);
        const apprentice = Math.round(gross * localData.apprenticeRate / 100);
        const totalDeductions = tax + insurance + performance + apprentice;
        const netAmount = gross - totalDeductions;

        return { tax, insurance, performance, apprentice, totalDeductions, netAmount };
    }, [localData.grossAmount, localData.taxRate, localData.insuranceRate, localData.performanceRate, localData.apprenticeRate]);

    useEffect(() => {
        // Sync with main form
        updateFormData({
            beneficiaryName: localData.recipientName,
            contractNumber: localData.contractNumber,
            amount: calculations.netAmount,
            description: localData.notes,
        });

        // Store extended form data
        onFormDataChange({
            formType: 'contractor_progress',
            contractorNumber: localData.contractorNumber,
            contractAmount: localData.contractAmount,
            progressNumber: localData.progressNumber,
            contractType: localData.contractType,
            subjectNumber: localData.subjectNumber,
            grossAmount: localData.grossAmount,
            deductions: {
                tax: calculations.tax,
                insurance: calculations.insurance,
                performance: calculations.performance,
                apprentice: calculations.apprentice,
                total: calculations.totalDeductions,
            },
            netAmount: calculations.netAmount,
        });
    }, [localData, calculations]);

    const formatNumber = (value: number) => {
        return new Intl.NumberFormat('fa-IR').format(value);
    };

    const handleNumberChange = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
        const rawValue = e.target.value.replace(/\D/g, '');
        setLocalData(prev => ({ ...prev, [field]: parseInt(rawValue || '0') }));
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-2 text-primary">
                <Calculator className="h-5 w-5" />
                <h3>محاسبه صورت وضعیت پیمانکاران</h3>
            </div>
            <p className="text-sm text-muted-foreground">
                پرداخت صورت وضعیت پیمانکاران با محاسبه خودکار کسورات قانونی
            </p>

            {/* Contractor Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                    <Label htmlFor="contractorNumber">شماره پیمانکار</Label>
                    <Input
                        id="contractorNumber"
                        value={localData.contractorNumber}
                        onChange={(e) => setLocalData(prev => ({ ...prev, contractorNumber: e.target.value }))}
                        placeholder="شماره پیمانکار"
                    />
                </div>

                <div className="space-y-2">
                    <Label htmlFor="contractNumber">شماره قرارداد</Label>
                    <Input
                        id="contractNumber"
                        value={localData.contractNumber}
                        onChange={(e) => setLocalData(prev => ({ ...prev, contractNumber: e.target.value }))}
                        placeholder="شماره قرارداد"
                    />
                </div>

                <div className="space-y-2">
                    <Label htmlFor="contractAmount">مبلغ قرارداد (ریال)</Label>
                    <Input
                        id="contractAmount"
                        type="number"
                        value={localData.contractAmount || ''}
                        onChange={(e) => setLocalData(prev => ({ ...prev, contractAmount: parseFloat(e.target.value) || 0 }))}
                        placeholder="مبلغ قرارداد"
                        className="font-mono"
                    />
                </div>

                <div className="space-y-2">
                    <Label htmlFor="progressNumber">شماره صورت وضعیت</Label>
                    <Input
                        id="progressNumber"
                        value={localData.progressNumber}
                        onChange={(e) => setLocalData(prev => ({ ...prev, progressNumber: e.target.value }))}
                        placeholder="شماره صورت وضعیت"
                    />
                </div>

                <div className="space-y-2">
                    <Label htmlFor="contractType">نوع قرارداد</Label>
                    <Select
                        value={localData.contractType}
                        onValueChange={(v) => setLocalData(prev => ({ ...prev, contractType: v }))}
                    >
                        <SelectTrigger>
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="عمرانی">عمرانی</SelectItem>
                            <SelectItem value="خدماتی">خدماتی</SelectItem>
                            <SelectItem value="خرید">خرید</SelectItem>
                            <SelectItem value="سایر">سایر</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label htmlFor="recipientName">
                        دریافت کننده وجه <span className="text-destructive">*</span>
                    </Label>
                    <div className="relative">
                        <User className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                            id="recipientName"
                            value={localData.recipientName}
                            onChange={(e) => setLocalData(prev => ({ ...prev, recipientName: e.target.value }))}
                            placeholder="نام پیمانکار"
                            className="pr-10"
                        />
                    </div>
                </div>

                <div className="space-y-2">
                    <Label htmlFor="subjectNumber">شماره موضوع</Label>
                    <Input
                        id="subjectNumber"
                        value={localData.subjectNumber}
                        onChange={(e) => setLocalData(prev => ({ ...prev, subjectNumber: e.target.value }))}
                        placeholder="شماره موضوع"
                    />
                </div>

                <div className="space-y-2">
                    <Label htmlFor="costCenter">مرکز هزینه</Label>
                    <div className="relative">
                        <Building2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                            id="costCenter"
                            value={localData.costCenter}
                            onChange={(e) => setLocalData(prev => ({ ...prev, costCenter: e.target.value }))}
                            placeholder="مرکز هزینه"
                            className="pr-10"
                        />
                    </div>
                </div>
            </div>

            {/* Gross Amount */}
            <div className="space-y-2">
                <Label htmlFor="grossAmount">
                    مبلغ ناخالص صورت وضعیت (ریال) <span className="text-destructive">*</span>
                </Label>
                <div className="relative">
                    <DollarSign className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                        id="grossAmount"
                        type="number"
                        value={localData.grossAmount || ''}
                        onChange={(e) => setLocalData(prev => ({ ...prev, grossAmount: parseFloat(e.target.value) || 0 }))}
                        placeholder="مبلغ ناخالص"
                        className="pr-10 font-mono text-lg"
                    />
                </div>
            </div>

            {/* Deductions Calculation */}
            {localData.grossAmount > 0 && (
                <Card className="p-4 space-y-3">
                    <h4 className="flex items-center gap-2">
                        <Percent className="h-4 w-4" />
                        کسورات قانونی
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div className="space-y-1">
                            <p className="text-muted-foreground">مالیات ({localData.taxRate}%)</p>
                            <p className="font-mono text-red-600">{formatNumber(calculations.tax)}-</p>
                        </div>
                        <div className="space-y-1">
                            <p className="text-muted-foreground">بیمه ({localData.insuranceRate}%)</p>
                            <p className="font-mono text-red-600">{formatNumber(calculations.insurance)}-</p>
                        </div>
                        <div className="space-y-1">
                            <p className="text-muted-foreground">حسن انجام کار ({localData.performanceRate}%)</p>
                            <p className="font-mono text-red-600">{formatNumber(calculations.performance)}-</p>
                        </div>
                        <div className="space-y-1">
                            <p className="text-muted-foreground">کارآموزی ({localData.apprenticeRate}%)</p>
                            <p className="font-mono text-red-600">{formatNumber(calculations.apprentice)}-</p>
                        </div>
                    </div>

                    <div className="border-t pt-3 flex justify-between items-center">
                        <span className="text-muted-foreground">جمع کسورات:</span>
                        <span className="font-mono text-red-600">{formatNumber(calculations.totalDeductions)}- ریال</span>
                    </div>

                    <div className="border-t pt-3 flex justify-between items-center bg-green-50 -mx-4 px-4 py-2 -mb-4 rounded-b-lg">
                        <span className="font-medium">خالص قابل پرداخت:</span>
                        <span className="font-mono text-lg text-green-700">{formatNumber(calculations.netAmount)} ریال</span>
                    </div>
                </Card>
            )}

            {/* Notes */}
            <div className="space-y-2">
                <Label htmlFor="notes">توضیحات</Label>
                <Textarea
                    id="notes"
                    value={localData.notes}
                    onChange={(e) => setLocalData(prev => ({ ...prev, notes: e.target.value }))}
                    placeholder="توضیحات تکمیلی..."
                    rows={3}
                />
            </div>
        </div>
    );
}

export default ContractorProgressForm;
