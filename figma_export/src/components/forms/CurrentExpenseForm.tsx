import React, { useState, useEffect } from 'react';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Card } from '../ui/card';
import { TransactionFormData } from '../TransactionWizard';
import { User, FileText, DollarSign, Building2, Calculator } from 'lucide-react';

type Props = {
    formData: TransactionFormData;
    updateFormData: (data: Partial<TransactionFormData>) => void;
    onFormDataChange: (data: Record<string, unknown>) => void;
};

/**
 * هزینه‌های جاری - Current Expense Form
 * Based on employer image 2: Simple expense payment form
 * 
 * Fields:
 * - دریافت کننده وجه (Recipient)
 * - شماره موضوع (Subject Number)
 * - امور حسابداری (Accounting Department)
 * - مرکز هزینه (Cost Center)
 * - مبلغ قابل پرداخت (Payable Amount)
 * - شماره لیست (List Number)
 * - واحد سازمانی (Org Unit)
 * - توضیحات (Description)
 */
export function CurrentExpenseForm({ formData, updateFormData, onFormDataChange }: Props) {
    const [localData, setLocalData] = useState({
        recipientName: formData.beneficiaryName || '',
        subjectNumber: '',
        accountingDept: 'هزینه‌های جاری',
        costCenter: formData.costCenterName || '',
        payableAmount: formData.amount || 0,
        listNumber: '',
        orgUnit: formData.sectionName || formData.departmentName || '',
        notes: formData.description || '',
    });

    useEffect(() => {
        // Sync with main form
        updateFormData({
            beneficiaryName: localData.recipientName,
            amount: localData.payableAmount,
            description: localData.notes,
        });

        // Store extended form data
        onFormDataChange({
            formType: 'current_expense',
            subjectNumber: localData.subjectNumber,
            accountingDept: localData.accountingDept,
            listNumber: localData.listNumber,
            orgUnit: localData.orgUnit,
        });
    }, [localData]);

    const formatNumber = (value: string) => {
        const numbers = value.replace(/\D/g, '');
        return new Intl.NumberFormat('fa-IR').format(parseInt(numbers || '0'));
    };

    const handleAmountChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const rawValue = e.target.value.replace(/\D/g, '');
        setLocalData(prev => ({ ...prev, payableAmount: parseInt(rawValue || '0') }));
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-2 text-primary">
                <FileText className="h-5 w-5" />
                <h3>هزینه‌های جاری</h3>
            </div>
            <p className="text-sm text-muted-foreground">
                فرم پرداخت هزینه‌های جاری و روزمره
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Recipient Name */}
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
                            placeholder="نام دریافت‌کننده"
                            className="pr-10"
                        />
                    </div>
                </div>

                {/* Subject Number */}
                <div className="space-y-2">
                    <Label htmlFor="subjectNumber">شماره موضوع</Label>
                    <Input
                        id="subjectNumber"
                        value={localData.subjectNumber}
                        onChange={(e) => setLocalData(prev => ({ ...prev, subjectNumber: e.target.value }))}
                        placeholder="شماره موضوع"
                    />
                </div>

                {/* Accounting Department */}
                <div className="space-y-2">
                    <Label htmlFor="accountingDept">امور حسابداری</Label>
                    <Input
                        id="accountingDept"
                        value={localData.accountingDept}
                        disabled
                        className="bg-muted"
                    />
                </div>

                {/* Cost Center */}
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

                {/* Payable Amount */}
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

                {/* List Number */}
                <div className="space-y-2">
                    <Label htmlFor="listNumber">شماره لیست</Label>
                    <Input
                        id="listNumber"
                        value={localData.listNumber}
                        onChange={(e) => setLocalData(prev => ({ ...prev, listNumber: e.target.value }))}
                        placeholder="شماره لیست"
                    />
                </div>

                {/* Org Unit */}
                <div className="space-y-2 md:col-span-2">
                    <Label htmlFor="orgUnit">واحد سازمانی</Label>
                    <Input
                        id="orgUnit"
                        value={localData.orgUnit}
                        onChange={(e) => setLocalData(prev => ({ ...prev, orgUnit: e.target.value }))}
                        placeholder="واحد سازمانی"
                    />
                </div>
            </div>

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

            {/* Summary Card */}
            {localData.payableAmount > 0 && (
                <Card className="p-4 bg-accent/50">
                    <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">مبلغ قابل پرداخت:</span>
                        <span className="font-mono text-lg text-primary">
                            {formatNumber(localData.payableAmount.toString())} ریال
                        </span>
                    </div>
                </Card>
            )}
        </div>
    );
}

export default CurrentExpenseForm;
