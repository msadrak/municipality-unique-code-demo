import React, { useState, useEffect } from 'react';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Card } from '../ui/card';
import { TransactionFormData } from '../TransactionWizard';
import { User, FileText, DollarSign, Building2, Calendar, ClipboardCheck } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';

type Props = {
    formData: TransactionFormData;
    updateFormData: (data: Partial<TransactionFormData>) => void;
    onFormDataChange: (data: Record<string, unknown>) => void;
};

/**
 * استرداد سپرده حسن انجام کار - Performance Bond Return Form
 * Based on employer image 3: Performance bond return with handover protocol
 * 
 * Fields:
 * - شماره پیمانکار, ردیف قرارداد, شماره قرارداد, مبلغ قرارداد
 * - نام پروژه, نوع قرارداد, دریافت کننده وجه, شماره موضوع
 * - مرکز هزینه, مبلغ قابل پرداخت, مبلغ به حروف
 * - صورتجلسه تحویل موقت (شماره/تاریخ)
 * - صورتجلسه تحویل قطعی (شماره/تاریخ)
 */
export function PerformanceBondForm({ formData, updateFormData, onFormDataChange }: Props) {
    const [localData, setLocalData] = useState({
        contractorNumber: '',
        contractRow: '',
        contractNumber: formData.contractNumber || '',
        contractAmount: 0,
        projectName: '',
        contractType: 'عمرانی',
        recipientName: formData.beneficiaryName || '',
        subjectNumber: '',
        costCenter: formData.costCenterName || '',
        payableAmount: formData.amount || 0,
        amountInWords: '',
        // Handover Protocol - Temporary
        tempHandoverNumber: '',
        tempHandoverDate: '',
        // Handover Protocol - Final
        finalHandoverNumber: '',
        finalHandoverDate: '',
        // Performance Bond Balance
        bondDeposit: 0,
        bondDeducted: 0,
        bondPaid: 0,
        bondBalance: 0,
        notes: formData.description || '',
    });

    useEffect(() => {
        // Sync with main form
        updateFormData({
            beneficiaryName: localData.recipientName,
            contractNumber: localData.contractNumber,
            amount: localData.payableAmount,
            description: localData.notes,
        });

        // Store extended form data
        onFormDataChange({
            formType: 'performance_bond',
            contractorNumber: localData.contractorNumber,
            contractRow: localData.contractRow,
            contractAmount: localData.contractAmount,
            projectName: localData.projectName,
            contractType: localData.contractType,
            subjectNumber: localData.subjectNumber,
            amountInWords: localData.amountInWords,
            tempHandover: {
                number: localData.tempHandoverNumber,
                date: localData.tempHandoverDate,
            },
            finalHandover: {
                number: localData.finalHandoverNumber,
                date: localData.finalHandoverDate,
            },
            bondBalance: {
                deposit: localData.bondDeposit,
                deducted: localData.bondDeducted,
                paid: localData.bondPaid,
                balance: localData.bondBalance,
            },
        });
    }, [localData]);

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
                <ClipboardCheck className="h-5 w-5" />
                <h3>استرداد سپرده حسن انجام کار</h3>
            </div>
            <p className="text-sm text-muted-foreground">
                فرم استرداد سپرده حسن انجام کار پیمانکار بدون پرداخت
            </p>

            {/* Contract Info */}
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
                    <Label htmlFor="contractRow">ردیف قرارداد</Label>
                    <Input
                        id="contractRow"
                        value={localData.contractRow}
                        onChange={(e) => setLocalData(prev => ({ ...prev, contractRow: e.target.value }))}
                        placeholder="ردیف قرارداد"
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
                    <Label htmlFor="projectName">نام پروژه</Label>
                    <Input
                        id="projectName"
                        value={localData.projectName}
                        onChange={(e) => setLocalData(prev => ({ ...prev, projectName: e.target.value }))}
                        placeholder="نام پروژه"
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

                <div className="space-y-2">
                    <Label htmlFor="payableAmount">
                        مبلغ قابل پرداخت (ریال) <span className="text-destructive">*</span>
                    </Label>
                    <div className="relative">
                        <DollarSign className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                            id="payableAmount"
                            type="number"
                            value={localData.payableAmount || ''}
                            onChange={(e) => setLocalData(prev => ({ ...prev, payableAmount: parseFloat(e.target.value) || 0 }))}
                            placeholder="مبلغ"
                            className="pr-10 font-mono"
                        />
                    </div>
                </div>
            </div>

            {/* Handover Protocol - Temporary */}
            <Card className="p-4 space-y-4">
                <h4 className="flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    صورتجلسه تحویل موقت
                </h4>
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <Label htmlFor="tempHandoverNumber">شماره</Label>
                        <Input
                            id="tempHandoverNumber"
                            value={localData.tempHandoverNumber}
                            onChange={(e) => setLocalData(prev => ({ ...prev, tempHandoverNumber: e.target.value }))}
                            placeholder="شماره صورتجلسه"
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="tempHandoverDate">تاریخ</Label>
                        <Input
                            id="tempHandoverDate"
                            value={localData.tempHandoverDate}
                            onChange={(e) => setLocalData(prev => ({ ...prev, tempHandoverDate: e.target.value }))}
                            placeholder="۱۴۰۳/۰۱/۰۱"
                        />
                    </div>
                </div>
            </Card>

            {/* Handover Protocol - Final */}
            <Card className="p-4 space-y-4">
                <h4 className="flex items-center gap-2">
                    <ClipboardCheck className="h-4 w-4" />
                    صورتجلسه تحویل قطعی
                </h4>
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <Label htmlFor="finalHandoverNumber">شماره</Label>
                        <Input
                            id="finalHandoverNumber"
                            value={localData.finalHandoverNumber}
                            onChange={(e) => setLocalData(prev => ({ ...prev, finalHandoverNumber: e.target.value }))}
                            placeholder="شماره صورتجلسه"
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="finalHandoverDate">تاریخ</Label>
                        <Input
                            id="finalHandoverDate"
                            value={localData.finalHandoverDate}
                            onChange={(e) => setLocalData(prev => ({ ...prev, finalHandoverDate: e.target.value }))}
                            placeholder="۱۴۰۳/۰۱/۰۱"
                        />
                    </div>
                </div>
            </Card>

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

            {/* Summary */}
            {localData.payableAmount > 0 && (
                <Card className="p-4 bg-accent/50">
                    <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">مبلغ قابل پرداخت:</span>
                        <span className="font-mono text-lg text-primary">
                            {formatNumber(localData.payableAmount)} ریال
                        </span>
                    </div>
                </Card>
            )}
        </div>
    );
}

export default PerformanceBondForm;
