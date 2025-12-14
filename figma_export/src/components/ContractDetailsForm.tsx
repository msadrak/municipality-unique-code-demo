import React, { useState, useEffect } from 'react';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { X, Calculator, FileText, User, Hash, DollarSign, Percent, Building2 } from 'lucide-react';

type ContractDetailsProps = {
    isOpen: boolean;
    onClose: () => void;
    onSave: (data: ContractFormData) => void;
    initialData?: ContractFormData;
};

export type ContractFormData = {
    requestNo: string;
    accountingDept: string;
    requestDate: string;
    contractorNo: string;
    contractorName: string;
    contractNo: string;
    statementNo: number;
    contractAmount: number;
    projectName: string;
    contractType: string;
    grossAmount: number;
    // Auto-calculated fields
    tax3: number;        // مالیات 3%
    insurance5: number;  // بیمه 5%
    performance10: number; // حسن انجام کار 10%
    training: number;    // آموزش 0.2%
    advance: number;     // پیش‌پرداخت
    prepay: number;      // علی‌الحساب
    misc: number;        // سایر کسورات
    vat: number;         // مالیات ارزش افزوده
    totalDeductions: number;
    netAmount1: number;  // خالص پس از کسورات
    netAmount2: number;  // خالص نهایی با ارزش افزوده
};

const defaultData: ContractFormData = {
    requestNo: '',
    accountingDept: 'پروژه‌های عمرانی',
    requestDate: '1403/09/16',
    contractorNo: '',
    contractorName: '',
    contractNo: '',
    statementNo: 0,
    contractAmount: 0,
    projectName: '',
    contractType: '',
    grossAmount: 0,
    tax3: 0,
    insurance5: 0,
    performance10: 0,
    training: 0,
    advance: 0,
    prepay: 0,
    misc: 0,
    vat: 0,
    totalDeductions: 0,
    netAmount1: 0,
    netAmount2: 0,
};

export function ContractDetailsForm({ isOpen, onClose, onSave, initialData }: ContractDetailsProps) {
    const [data, setData] = useState<ContractFormData>(initialData || defaultData);

    // Auto-calculate when grossAmount changes
    useEffect(() => {
        if (data.grossAmount > 0) {
            const gross = data.grossAmount;
            const tax3 = Math.round(gross * 0.03);
            const insurance5 = Math.round(gross * 0.05);
            const performance10 = Math.round(gross * 0.10);
            const training = Math.round(gross * 0.002);

            const totalDeductions = tax3 + insurance5 + performance10 + training +
                data.advance + data.prepay + data.misc;
            const netAmount1 = gross - totalDeductions;
            const netAmount2 = netAmount1 + data.vat;

            setData(prev => ({
                ...prev,
                tax3,
                insurance5,
                performance10,
                training,
                totalDeductions,
                netAmount1,
                netAmount2,
            }));
        }
    }, [data.grossAmount, data.advance, data.prepay, data.misc, data.vat]);

    const formatNumber = (value: number) => {
        return new Intl.NumberFormat('fa-IR').format(value);
    };

    const parseNumber = (value: string): number => {
        return parseInt(value.replace(/\D/g, '') || '0');
    };

    const handleNumberChange = (field: keyof ContractFormData) => (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = parseNumber(e.target.value);
        setData(prev => ({ ...prev, [field]: value }));
    };

    const handleTextChange = (field: keyof ContractFormData) => (e: React.ChangeEvent<HTMLInputElement>) => {
        setData(prev => ({ ...prev, [field]: e.target.value }));
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b bg-primary text-primary-foreground rounded-t-lg">
                    <div className="flex items-center gap-2">
                        <FileText className="h-5 w-5" />
                        <h3 className="font-bold">اطلاعات تکمیلی قرارداد</h3>
                    </div>
                    <Button variant="ghost" size="icon" onClick={onClose} className="text-primary-foreground hover:bg-primary-foreground/20">
                        <X className="h-5 w-5" />
                    </Button>
                </div>

                <div className="p-6 space-y-6">
                    {/* Row 1: Basic Info */}
                    <div className="grid grid-cols-3 gap-4">
                        <div className="space-y-2">
                            <Label className="flex items-center gap-1">
                                <Hash className="h-3 w-3" />
                                شماره درخواست
                            </Label>
                            <Input
                                value={data.requestNo}
                                onChange={handleTextChange('requestNo')}
                                className="bg-muted"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="flex items-center gap-1">
                                <Building2 className="h-3 w-3" />
                                امور حسابداری
                            </Label>
                            <Input
                                value={data.accountingDept}
                                onChange={handleTextChange('accountingDept')}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>تاریخ درخواست</Label>
                            <Input
                                value={data.requestDate}
                                onChange={handleTextChange('requestDate')}
                            />
                        </div>
                    </div>

                    {/* Row 2: Contractor Info */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label className="flex items-center gap-1">
                                <Hash className="h-3 w-3" />
                                شماره پیمانکار
                            </Label>
                            <Input
                                value={data.contractorNo}
                                onChange={handleTextChange('contractorNo')}
                                placeholder="کد پیمانکار"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="flex items-center gap-1">
                                <User className="h-3 w-3" />
                                نام پیمانکار
                            </Label>
                            <Input
                                value={data.contractorName}
                                onChange={handleTextChange('contractorName')}
                                placeholder="نام شرکت/شخص پیمانکار"
                            />
                        </div>
                    </div>

                    {/* Row 3: Contract Info */}
                    <div className="grid grid-cols-3 gap-4">
                        <div className="space-y-2">
                            <Label className="flex items-center gap-1">
                                <FileText className="h-3 w-3" />
                                شماره قرارداد
                            </Label>
                            <Input
                                value={data.contractNo}
                                onChange={handleTextChange('contractNo')}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>شماره صورت وضعیت</Label>
                            <Input
                                type="number"
                                value={data.statementNo || ''}
                                onChange={(e) => setData(prev => ({ ...prev, statementNo: parseInt(e.target.value || '0') }))}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="flex items-center gap-1">
                                <DollarSign className="h-3 w-3" />
                                مبلغ قرارداد
                            </Label>
                            <Input
                                value={data.contractAmount ? formatNumber(data.contractAmount) : ''}
                                onChange={handleNumberChange('contractAmount')}
                                className="font-mono"
                            />
                        </div>
                    </div>

                    {/* Row 4: Project Info */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>نام پروژه</Label>
                            <Input
                                value={data.projectName}
                                onChange={handleTextChange('projectName')}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>نوع قرارداد</Label>
                            <Input
                                value={data.contractType}
                                onChange={handleTextChange('contractType')}
                            />
                        </div>
                    </div>

                    {/* Gross Amount - Main Input */}
                    <div className="bg-accent p-4 rounded-lg space-y-2">
                        <Label className="flex items-center gap-2">
                            <Calculator className="h-4 w-4 text-primary" />
                            <span className="font-bold">مبلغ ناخالص (برای محاسبه کسورات)</span>
                        </Label>
                        <Input
                            value={data.grossAmount ? formatNumber(data.grossAmount) : ''}
                            onChange={handleNumberChange('grossAmount')}
                            className="font-mono text-lg"
                            placeholder="مبلغ ناخالص را وارد کنید"
                        />
                    </div>

                    {/* Auto-calculated Deductions */}
                    {data.grossAmount > 0 && (
                        <div className="grid grid-cols-2 gap-6">
                            {/* Left Column - Auto calculated */}
                            <div className="bg-slate-50 p-4 rounded-lg space-y-3">
                                <h4 className="font-bold text-sm text-slate-700 flex items-center gap-2">
                                    <Percent className="h-4 w-4" />
                                    کسورات قانونی (محاسبه خودکار)
                                </h4>

                                <div className="space-y-2">
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm text-muted-foreground">مالیات (۳٪):</span>
                                        <span className="font-mono bg-white px-2 py-1 rounded">{formatNumber(data.tax3)}</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm text-muted-foreground">بیمه تامین اجتماعی (۵٪):</span>
                                        <span className="font-mono bg-white px-2 py-1 rounded">{formatNumber(data.insurance5)}</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm text-muted-foreground">حسن انجام کار (۱۰٪):</span>
                                        <span className="font-mono bg-white px-2 py-1 rounded">{formatNumber(data.performance10)}</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm text-muted-foreground">آموزش (۰.۲٪):</span>
                                        <span className="font-mono bg-white px-2 py-1 rounded">{formatNumber(data.training)}</span>
                                    </div>
                                </div>
                            </div>

                            {/* Right Column - Manual inputs */}
                            <div className="bg-slate-50 p-4 rounded-lg space-y-3">
                                <h4 className="font-bold text-sm text-slate-700">کسورات دستی</h4>

                                <div className="space-y-2">
                                    <div className="flex items-center gap-2">
                                        <Label className="min-w-24 text-sm">پیش‌پرداخت:</Label>
                                        <Input
                                            value={data.advance ? formatNumber(data.advance) : ''}
                                            onChange={handleNumberChange('advance')}
                                            className="font-mono text-sm"
                                        />
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Label className="min-w-24 text-sm">علی‌الحساب:</Label>
                                        <Input
                                            value={data.prepay ? formatNumber(data.prepay) : ''}
                                            onChange={handleNumberChange('prepay')}
                                            className="font-mono text-sm"
                                        />
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Label className="min-w-24 text-sm">سایر کسورات:</Label>
                                        <Input
                                            value={data.misc ? formatNumber(data.misc) : ''}
                                            onChange={handleNumberChange('misc')}
                                            className="font-mono text-sm"
                                        />
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Label className="min-w-24 text-sm">مالیات ارزش افزوده:</Label>
                                        <Input
                                            value={data.vat ? formatNumber(data.vat) : ''}
                                            onChange={handleNumberChange('vat')}
                                            className="font-mono text-sm"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Summary */}
                    {data.grossAmount > 0 && (
                        <div className="bg-green-50 border border-green-200 p-4 rounded-lg space-y-2">
                            <h4 className="font-bold text-green-800 flex items-center gap-2">
                                <Calculator className="h-4 w-4" />
                                نتیجه محاسبات
                            </h4>
                            <div className="grid grid-cols-3 gap-4 text-sm">
                                <div>
                                    <span className="text-green-700">جمع کسورات:</span>
                                    <span className="font-mono font-bold text-red-600 mr-2">{formatNumber(data.totalDeductions)}</span>
                                </div>
                                <div>
                                    <span className="text-green-700">خالص پس از کسورات:</span>
                                    <span className="font-mono font-bold mr-2">{formatNumber(data.netAmount1)}</span>
                                </div>
                                <div>
                                    <span className="text-green-700">خالص نهایی:</span>
                                    <span className="font-mono font-bold text-green-600 mr-2">{formatNumber(data.netAmount2)}</span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex justify-end gap-3 p-4 border-t bg-muted/50">
                    <Button variant="outline" onClick={onClose}>
                        انصراف
                    </Button>
                    <Button onClick={() => onSave(data)}>
                        ذخیره اطلاعات
                    </Button>
                </div>
            </Card>
        </div>
    );
}
