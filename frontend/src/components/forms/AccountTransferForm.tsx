import React, { useState, useEffect } from 'react';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Card } from '../ui/card';
import { TransactionFormData } from '../TransactionWizard';
import { Building2, DollarSign, ArrowLeftRight, Plus, Trash2, CheckSquare } from 'lucide-react';
import { Button } from '../ui/button';
import { Checkbox } from '../ui/checkbox';

type Props = {
    formData: TransactionFormData;
    updateFormData: (data: Partial<TransactionFormData>) => void;
    onFormDataChange: (data: Record<string, unknown>) => void;
};

type TransferRow = {
    id: string;
    payerAccount: string;
    payerOwner: string;
    payerBank: string;
    payerBranch: string;
    receiverAccount: string;
    receiverOwner: string;
    receiverBank: string;
    receiverBranch: string;
    amount: number;
};

/**
 * جابجایی حساب مناطق و سازمان‌ها - Account Transfer Form
 * Based on employer image 4: Inter-zone/organization account transfers
 * 
 * Fields:
 * - شماره تنخواه, بدون تنخواه checkbox
 * - شماره موضوع, نوع تخصیص (هزینه‌ای/سرمایه‌ای)
 * - سهم منطقه, سهم مرکزی, سهم صندوق, سایر checkboxes
 * - جدول واریز به حساب (multiple rows)
 */
export function AccountTransferForm({ formData, updateFormData, onFormDataChange }: Props) {
    const [localData, setLocalData] = useState({
        treasuryNumber: '',
        noTreasury: false,
        subjectNumber: '',
        allocationType: 'هزینه‌ای و سرمایه‌ای',
        notes: formData.description || '',
        // Share checkboxes
        shareZone: true,
        shareCentral1: false,
        shareCentral2: false,
        shareFund: false,
        shareOther1: false,
        shareOther2: false,
    });

    const [transferRows, setTransferRows] = useState<TransferRow[]>([
        {
            id: '1',
            payerAccount: '',
            payerOwner: '',
            payerBank: '',
            payerBranch: '',
            receiverAccount: '',
            receiverOwner: '',
            receiverBank: '',
            receiverBranch: '',
            amount: 0,
        }
    ]);

    const totalAmount = transferRows.reduce((sum, row) => sum + row.amount, 0);

    useEffect(() => {
        // Sync with main form
        updateFormData({
            amount: totalAmount,
            description: localData.notes,
        });

        // Store extended form data
        onFormDataChange({
            formType: 'account_transfer',
            treasuryNumber: localData.treasuryNumber,
            noTreasury: localData.noTreasury,
            subjectNumber: localData.subjectNumber,
            allocationType: localData.allocationType,
            shares: {
                zone: localData.shareZone,
                central1: localData.shareCentral1,
                central2: localData.shareCentral2,
                fund: localData.shareFund,
                other1: localData.shareOther1,
                other2: localData.shareOther2,
            },
            transfers: transferRows,
            totalAmount,
        });
    }, [localData, transferRows, totalAmount]);

    const formatNumber = (value: number) => {
        return new Intl.NumberFormat('fa-IR').format(value);
    };

    const addRow = () => {
        setTransferRows(prev => [
            ...prev,
            {
                id: Date.now().toString(),
                payerAccount: '',
                payerOwner: '',
                payerBank: '',
                payerBranch: '',
                receiverAccount: '',
                receiverOwner: '',
                receiverBank: '',
                receiverBranch: '',
                amount: 0,
            }
        ]);
    };

    const removeRow = (id: string) => {
        if (transferRows.length > 1) {
            setTransferRows(prev => prev.filter(row => row.id !== id));
        }
    };

    const updateRow = (id: string, field: keyof TransferRow, value: string | number) => {
        setTransferRows(prev => prev.map(row =>
            row.id === id ? { ...row, [field]: value } : row
        ));
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-2 text-primary">
                <ArrowLeftRight className="h-5 w-5" />
                <h3>جابجایی حساب مناطق و سازمان‌ها</h3>
            </div>
            <p className="text-sm text-muted-foreground">
                فرم جابجایی وجوه بین حساب‌های مناطق و سازمان‌ها
            </p>

            {/* Treasury Info */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                    <Label htmlFor="treasuryNumber">شماره تنخواه خزانه‌داری</Label>
                    <Input
                        id="treasuryNumber"
                        value={localData.treasuryNumber}
                        onChange={(e) => setLocalData(prev => ({ ...prev, treasuryNumber: e.target.value }))}
                        placeholder="شماره تنخواه"
                        disabled={localData.noTreasury}
                    />
                </div>

                <div className="flex items-center gap-2 pt-8">
                    <Checkbox
                        id="noTreasury"
                        checked={localData.noTreasury}
                        onCheckedChange={(checked) => setLocalData(prev => ({
                            ...prev,
                            noTreasury: checked as boolean,
                            treasuryNumber: checked ? '' : prev.treasuryNumber
                        }))}
                    />
                    <Label htmlFor="noTreasury" className="cursor-pointer">بدون تنخواه</Label>
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
            </div>

            {/* Allocation Type */}
            <div className="space-y-2">
                <Label>نوع تخصیص</Label>
                <Input
                    value={localData.allocationType}
                    disabled
                    className="bg-muted max-w-sm"
                />
            </div>

            {/* Share Checkboxes */}
            <Card className="p-4">
                <h4 className="mb-3">بخش‌های سهم</h4>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <div className="flex items-center gap-2">
                        <Checkbox
                            id="shareZone"
                            checked={localData.shareZone}
                            onCheckedChange={(checked) => setLocalData(prev => ({ ...prev, shareZone: checked as boolean }))}
                        />
                        <Label htmlFor="shareZone" className="cursor-pointer">سهم منطقه</Label>
                    </div>
                    <div className="flex items-center gap-2">
                        <Checkbox
                            id="shareCentral1"
                            checked={localData.shareCentral1}
                            onCheckedChange={(checked) => setLocalData(prev => ({ ...prev, shareCentral1: checked as boolean }))}
                        />
                        <Label htmlFor="shareCentral1" className="cursor-pointer">سهم مرکزی۱</Label>
                    </div>
                    <div className="flex items-center gap-2">
                        <Checkbox
                            id="shareCentral2"
                            checked={localData.shareCentral2}
                            onCheckedChange={(checked) => setLocalData(prev => ({ ...prev, shareCentral2: checked as boolean }))}
                        />
                        <Label htmlFor="shareCentral2" className="cursor-pointer">سهم مرکزی۲</Label>
                    </div>
                    <div className="flex items-center gap-2">
                        <Checkbox
                            id="shareFund"
                            checked={localData.shareFund}
                            onCheckedChange={(checked) => setLocalData(prev => ({ ...prev, shareFund: checked as boolean }))}
                        />
                        <Label htmlFor="shareFund" className="cursor-pointer">وام صندوق</Label>
                    </div>
                    <div className="flex items-center gap-2">
                        <Checkbox
                            id="shareOther1"
                            checked={localData.shareOther1}
                            onCheckedChange={(checked) => setLocalData(prev => ({ ...prev, shareOther1: checked as boolean }))}
                        />
                        <Label htmlFor="shareOther1" className="cursor-pointer">سایر۱</Label>
                    </div>
                    <div className="flex items-center gap-2">
                        <Checkbox
                            id="shareOther2"
                            checked={localData.shareOther2}
                            onCheckedChange={(checked) => setLocalData(prev => ({ ...prev, shareOther2: checked as boolean }))}
                        />
                        <Label htmlFor="shareOther2" className="cursor-pointer">سایر۲</Label>
                    </div>
                </div>
            </Card>

            {/* Transfer Rows Table */}
            <Card className="p-4 space-y-4">
                <div className="flex items-center justify-between">
                    <h4 className="flex items-center gap-2">
                        <Building2 className="h-4 w-4" />
                        واریز به حساب
                    </h4>
                    <Button variant="outline" size="sm" onClick={addRow}>
                        <Plus className="h-4 w-4 ml-1" />
                        افزودن ردیف
                    </Button>
                </div>

                <div className="space-y-4">
                    {transferRows.map((row, index) => (
                        <Card key={row.id} className="p-3 bg-accent/30">
                            <div className="flex items-center justify-between mb-3">
                                <span className="text-sm text-muted-foreground">ردیف {index + 1}</span>
                                {transferRows.length > 1 && (
                                    <Button variant="ghost" size="sm" onClick={() => removeRow(row.id)}>
                                        <Trash2 className="h-4 w-4 text-destructive" />
                                    </Button>
                                )}
                            </div>

                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                                <div>
                                    <Label className="text-xs">حساب پرداخت کننده</Label>
                                    <Input
                                        value={row.payerAccount}
                                        onChange={(e) => updateRow(row.id, 'payerAccount', e.target.value)}
                                        placeholder="شماره حساب"
                                        className="h-8"
                                    />
                                </div>
                                <div>
                                    <Label className="text-xs">صاحب حساب</Label>
                                    <Input
                                        value={row.payerOwner}
                                        onChange={(e) => updateRow(row.id, 'payerOwner', e.target.value)}
                                        placeholder="نام"
                                        className="h-8"
                                    />
                                </div>
                                <div>
                                    <Label className="text-xs">بانک</Label>
                                    <Input
                                        value={row.payerBank}
                                        onChange={(e) => updateRow(row.id, 'payerBank', e.target.value)}
                                        placeholder="بانک"
                                        className="h-8"
                                    />
                                </div>
                                <div>
                                    <Label className="text-xs">شعبه</Label>
                                    <Input
                                        value={row.payerBranch}
                                        onChange={(e) => updateRow(row.id, 'payerBranch', e.target.value)}
                                        placeholder="شعبه"
                                        className="h-8"
                                    />
                                </div>
                                <div>
                                    <Label className="text-xs">حساب دریافت کننده</Label>
                                    <Input
                                        value={row.receiverAccount}
                                        onChange={(e) => updateRow(row.id, 'receiverAccount', e.target.value)}
                                        placeholder="شماره حساب"
                                        className="h-8"
                                    />
                                </div>
                                <div>
                                    <Label className="text-xs">صاحب حساب</Label>
                                    <Input
                                        value={row.receiverOwner}
                                        onChange={(e) => updateRow(row.id, 'receiverOwner', e.target.value)}
                                        placeholder="نام"
                                        className="h-8"
                                    />
                                </div>
                                <div>
                                    <Label className="text-xs">بانک</Label>
                                    <Input
                                        value={row.receiverBank}
                                        onChange={(e) => updateRow(row.id, 'receiverBank', e.target.value)}
                                        placeholder="بانک"
                                        className="h-8"
                                    />
                                </div>
                                <div>
                                    <Label className="text-xs">مبلغ جابجایی</Label>
                                    <Input
                                        value={row.amount ? formatNumber(row.amount) : ''}
                                        onChange={(e) => {
                                            const raw = e.target.value.replace(/\D/g, '');
                                            updateRow(row.id, 'amount', parseInt(raw || '0'));
                                        }}
                                        placeholder="مبلغ"
                                        className="h-8 font-mono"
                                    />
                                </div>
                            </div>
                        </Card>
                    ))}
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

            {/* Total */}
            <Card className="p-4 bg-primary/5">
                <div className="flex items-center justify-between">
                    <span className="font-medium">سرجمع مبالغ:</span>
                    <span className="font-mono text-xl text-primary">
                        {formatNumber(totalAmount)} ریال
                    </span>
                </div>
            </Card>
        </div>
    );
}

export default AccountTransferForm;
