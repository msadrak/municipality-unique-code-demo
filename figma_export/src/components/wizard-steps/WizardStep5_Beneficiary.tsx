import React, { useState } from 'react';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Button } from '../ui/button';
import { TransactionFormData } from '../TransactionWizard';
import { User, FileText, DollarSign, ClipboardList } from 'lucide-react';
import { ContractDetailsForm, ContractFormData } from '../ContractDetailsForm';

type Props = {
  formData: TransactionFormData;
  updateFormData: (data: Partial<TransactionFormData>) => void;
};

export function WizardStep5_Beneficiary({ formData, updateFormData }: Props) {
  const [showContractDetails, setShowContractDetails] = useState(false);
  const [contractData, setContractData] = useState<ContractFormData | undefined>();

  const formatNumber = (value: string) => {
    // Remove non-digits
    const numbers = value.replace(/\D/g, '');
    // Format with thousand separators
    return new Intl.NumberFormat('fa-IR').format(parseInt(numbers || '0'));
  };

  const handleAmountChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const rawValue = e.target.value.replace(/\D/g, '');
    updateFormData({ amount: parseInt(rawValue || '0') });
  };

  const handleContractSave = (data: ContractFormData) => {
    setContractData(data);
    // Update main form with contract data
    if (data.contractorName) {
      updateFormData({ beneficiaryName: data.contractorName });
    }
    if (data.contractNo) {
      updateFormData({ contractNumber: data.contractNo });
    }
    if (data.netAmount2 > 0) {
      updateFormData({ amount: data.netAmount2 });
    }
    setShowContractDetails(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <h3>اطلاعات ذینفع و قرارداد</h3>
        <p className="text-sm text-muted-foreground mt-1">
          مشخصات مالی و قراردادی تراکنش را وارد کنید
        </p>
      </div>

      {/* Contract Details Button */}
      <div className="bg-accent/50 border border-border rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ClipboardList className="h-5 w-5 text-primary" />
            <div>
              <p className="font-medium">اطلاعات تکمیلی قرارداد</p>
              <p className="text-sm text-muted-foreground">
                محاسبه خودکار کسورات قانونی و جزئیات پیمانکار
              </p>
            </div>
          </div>
          <Button
            variant={contractData ? "outline" : "default"}
            onClick={() => setShowContractDetails(true)}
          >
            {contractData ? 'ویرایش اطلاعات' : 'تکمیل اطلاعات'}
          </Button>
        </div>
        {contractData && (
          <div className="mt-3 pt-3 border-t border-border text-sm grid grid-cols-2 gap-2">
            <span className="text-muted-foreground">پیمانکار: <span className="text-foreground">{contractData.contractorName || '-'}</span></span>
            <span className="text-muted-foreground">قرارداد: <span className="text-foreground">{contractData.contractNo || '-'}</span></span>
            <span className="text-muted-foreground">مبلغ ناخالص: <span className="font-mono">{new Intl.NumberFormat('fa-IR').format(contractData.grossAmount)}</span></span>
            <span className="text-muted-foreground">خالص نهایی: <span className="font-mono text-green-600">{new Intl.NumberFormat('fa-IR').format(contractData.netAmount2)}</span></span>
          </div>
        )}
      </div>

      {/* Contract Details Modal */}
      <ContractDetailsForm
        isOpen={showContractDetails}
        onClose={() => setShowContractDetails(false)}
        onSave={handleContractSave}
        initialData={contractData}
      />

      {/* Beneficiary Name - Conditional Required */}
      <div className="space-y-3">
        <Label htmlFor="beneficiaryName">
          نام ذینفع / پیمانکار
          {formData.financialEventName?.includes('پیش‌پرداخت') && (
            <span className="text-destructive"> *</span>
          )}
        </Label>
        <div className="relative">
          <User className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            id="beneficiaryName"
            value={formData.beneficiaryName || ''}
            onChange={(e) => updateFormData({ beneficiaryName: e.target.value })}
            placeholder="نام شخص/شرکت دریافت‌کننده وجه"
            className="pr-10"
          />
        </div>
        <p className="text-xs text-muted-foreground">
          شخص یا شرکتی که وجه به آن پرداخت می‌شود
        </p>
      </div>

      {/* Contract Number - Optional */}
      <div className="space-y-3">
        <Label htmlFor="contractNumber">
          شماره قرارداد <span className="text-muted-foreground">(اختیاری)</span>
        </Label>
        <div className="relative">
          <FileText className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            id="contractNumber"
            value={formData.contractNumber || ''}
            onChange={(e) => updateFormData({ contractNumber: e.target.value })}
            placeholder="شماره قرارداد مرتبط (در صورت وجود)"
            className="pr-10"
          />
        </div>
      </div>

      {/* Amount - Required */}
      <div className="space-y-3">
        <Label htmlFor="amount">
          مبلغ (ریال) <span className="text-destructive">*</span>
        </Label>
        <div className="relative">
          <DollarSign className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            id="amount"
            value={formData.amount ? formatNumber(formData.amount.toString()) : ''}
            onChange={handleAmountChange}
            placeholder="مبلغ تراکنش را وارد کنید"
            className="pr-10 font-mono"
          />
        </div>
        {formData.amount && formData.amount > 0 && (
          <p className="text-xs text-muted-foreground">
            معادل: {formatNumber(formData.amount.toString())} ریال
          </p>
        )}

        {/* Budget Validation */}
        {formData.amount && formData.availableBudget && (
          <div className="space-y-2">
            {formData.amount > formData.availableBudget ? (
              <div className="bg-destructive/10 border border-destructive/20 text-destructive p-3 rounded text-sm">
                ⚠️ مبلغ وارد شده بیشتر از مانده بودجه است ({formatNumber(formData.availableBudget.toString())} ریال)
              </div>
            ) : (
              <div className="bg-green-50 border border-green-200 text-green-700 p-3 rounded text-sm">
                ✓ مبلغ در محدوده مانده بودجه است
              </div>
            )}
          </div>
        )}
      </div>

      {/* Description - Optional */}
      <div className="space-y-3">
        <Label htmlFor="description">
          توضیحات <span className="text-muted-foreground">(اختیاری)</span>
        </Label>
        <Textarea
          id="description"
          value={formData.description || ''}
          onChange={(e) => updateFormData({ description: e.target.value })}
          placeholder="توضیحات تکمیلی درباره تراکنش..."
          rows={4}
          className="resize-none"
        />
        <p className="text-xs text-muted-foreground">
          حداکثر ۵۰۰ کاراکتر
        </p>
      </div>

      {/* Summary */}
      {formData.amount && formData.amount > 0 && (
        <div className="bg-accent p-4 rounded-lg border border-border space-y-2">
          <p className="text-sm text-muted-foreground">خلاصه اطلاعات مالی:</p>
          <div className="space-y-1 text-sm">
            {formData.beneficiaryName && (
              <p>
                <span className="text-muted-foreground">ذینفع:</span>{' '}
                {formData.beneficiaryName}
              </p>
            )}
            {formData.contractNumber && (
              <p>
                <span className="text-muted-foreground">قرارداد:</span>{' '}
                {formData.contractNumber}
              </p>
            )}
            <p>
              <span className="text-muted-foreground">مبلغ:</span>{' '}
              <span className="font-mono">{formatNumber(formData.amount.toString())} ریال</span>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
