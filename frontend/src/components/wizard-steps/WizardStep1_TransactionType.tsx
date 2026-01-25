import React from 'react';
import { Label } from '../ui/label';
import { RadioGroup, RadioGroupItem } from '../ui/radio-group';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { TransactionFormData } from '../TransactionWizard';
import { Wallet, Building } from 'lucide-react';

type Props = {
  formData: TransactionFormData;
  updateFormData: (data: Partial<TransactionFormData>) => void;
};

export function WizardStep1_TransactionType({ formData, updateFormData }: Props) {
  return (
    <div className="space-y-6">
      <div>
        <h3>انتخاب نوع تراکنش و سال مالی</h3>
        <p className="text-sm text-muted-foreground mt-1">
          ابتدا نوع تراکنش و سال مالی مورد نظر را مشخص کنید
        </p>
      </div>

      {/* Transaction Type - ONE CLEAR DECISION */}
      <div className="space-y-3">
        <Label>نوع تراکنش</Label>
        <RadioGroup
          value={formData.transactionType}
          onValueChange={(value: 'expense' | 'capital') => updateFormData({ transactionType: value })}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Expense Option */}
            <label
              className={`flex items-start gap-3 p-4 border-2 rounded-lg cursor-pointer transition-all ${
                formData.transactionType === 'expense'
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
              }`}
            >
              <RadioGroupItem value="expense" id="expense" className="mt-1" />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <Wallet className="h-5 w-5 text-primary" />
                  <span className="font-medium">هزینه‌ای</span>
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  تراکنش‌های هزینه‌ای و جاری شهرداری
                </p>
              </div>
            </label>

            {/* Capital Option */}
            <label
              className={`flex items-start gap-3 p-4 border-2 rounded-lg cursor-pointer transition-all ${
                formData.transactionType === 'capital'
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
              }`}
            >
              <RadioGroupItem value="capital" id="capital" className="mt-1" />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <Building className="h-5 w-5 text-primary" />
                  <span className="font-medium">سرمایه‌ای</span>
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  تراکنش‌های تملک دارایی‌های سرمایه‌ای
                </p>
              </div>
            </label>
          </div>
        </RadioGroup>
      </div>

      {/* Fiscal Year */}
      <div className="space-y-3">
        <Label htmlFor="fiscalYear">سال مالی</Label>
        <Select
          value={formData.fiscalYear}
          onValueChange={(value) => updateFormData({ fiscalYear: value })}
        >
          <SelectTrigger id="fiscalYear">
            <SelectValue placeholder="انتخاب سال مالی" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="1403">۱۴۰۳</SelectItem>
            <SelectItem value="1402">۱۴۰۲</SelectItem>
            <SelectItem value="1404">۱۴۰۴</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          سال مالی که تراکنش در آن ثبت می‌شود
        </p>
      </div>

      {/* Summary */}
      {formData.transactionType && formData.fiscalYear && (
        <div className="bg-accent p-4 rounded-lg border border-border">
          <p className="text-sm">
            <span className="text-muted-foreground">انتخاب شما:</span>{' '}
            تراکنش {formData.transactionType === 'expense' ? 'هزینه‌ای' : 'سرمایه‌ای'} برای سال مالی {formData.fiscalYear}
          </p>
        </div>
      )}
    </div>
  );
}
