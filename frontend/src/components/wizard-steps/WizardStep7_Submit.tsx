import React from 'react';
import { TransactionFormData } from '../TransactionWizard';
import { Card } from '../ui/card';
import { CheckCircle2, AlertTriangle, Info } from 'lucide-react';

type Props = {
  formData: TransactionFormData;
};

export function WizardStep7_Submit({ formData }: Props) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('fa-IR').format(amount) + ' ریال';
  };

  const hasAllRequiredFields = () => {
    return (
      formData.transactionType &&
      formData.fiscalYear &&
      formData.zoneId &&
      formData.departmentId &&
      formData.sectionId &&
      formData.budgetItemId &&
      formData.financialEventId &&
      formData.costCenterId &&
      formData.amount
    );
  };

  const hasWarnings = () => {
    if (!formData.amount || !formData.availableBudget) return false;
    return formData.amount > formData.availableBudget;
  };

  return (
    <div className="space-y-6">
      <div>
        <h3>آماده ثبت نهایی</h3>
        <p className="text-sm text-muted-foreground mt-1">
          تراکنش شما آماده ثبت در سامانه است
        </p>
      </div>

      {/* Validation Status */}
      {hasAllRequiredFields() ? (
        <Card className="p-4 bg-green-50 border-green-200">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
            <div className="flex-1">
              <h5 className="text-green-900">تمامی فیلدهای الزامی تکمیل شده است</h5>
              <p className="text-sm text-green-700 mt-1">
                تراکنش شما آماده ثبت و ارسال برای تایید است
              </p>
            </div>
          </div>
        </Card>
      ) : (
        <Card className="p-4 bg-destructive/10 border-destructive/20">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-destructive mt-0.5" />
            <div className="flex-1">
              <h5 className="text-destructive">برخی فیلدهای الزامی تکمیل نشده است</h5>
              <p className="text-sm text-destructive/80 mt-1">
                لطفاً به مراحل قبل برگردید و فیلدهای الزامی را تکمیل کنید
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Warnings */}
      {hasWarnings() && (
        <Card className="p-4 bg-amber-50 border-amber-200">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5" />
            <div className="flex-1">
              <h5 className="text-amber-900">هشدار</h5>
              <p className="text-sm text-amber-700 mt-1">
                مبلغ تراکنش ({formData.amount ? formatCurrency(formData.amount) : '-'}) بیشتر از مانده بودجه ({formData.availableBudget ? formatCurrency(formData.availableBudget) : '-'}) است. این تراکنش نیاز به تایید ویژه دارد.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Transaction Summary Card */}
      <Card className="p-6">
        <h4 className="mb-4">خلاصه تراکنش</h4>
        <div className="space-y-3">
          <div className="flex justify-between text-sm pb-2 border-b">
            <span className="text-muted-foreground">کد یکتا</span>
            <span className="font-mono">{formData.uniqueCode}</span>
          </div>
          <div className="flex justify-between text-sm pb-2 border-b">
            <span className="text-muted-foreground">نوع تراکنش</span>
            <span>{formData.transactionType === 'expense' ? 'هزینه‌ای' : 'سرمایه‌ای'}</span>
          </div>
          <div className="flex justify-between text-sm pb-2 border-b">
            <span className="text-muted-foreground">سال مالی</span>
            <span>{formData.fiscalYear}</span>
          </div>
          <div className="flex justify-between text-sm pb-2 border-b">
            <span className="text-muted-foreground">واحد سازمانی</span>
            <span className="text-left">{formData.zoneName} / {formData.departmentName}</span>
          </div>
          <div className="flex justify-between text-sm pb-2 border-b">
            <span className="text-muted-foreground">ردیف بودجه</span>
            <span className="font-mono">{formData.budgetCode}</span>
          </div>
          <div className="flex justify-between text-sm pb-2 border-b">
            <span className="text-muted-foreground">رویداد مالی</span>
            <span>{formData.financialEventName}</span>
          </div>
          {formData.beneficiaryName && (
            <div className="flex justify-between text-sm pb-2 border-b">
              <span className="text-muted-foreground">ذینفع</span>
              <span>{formData.beneficiaryName}</span>
            </div>
          )}
          <div className="flex justify-between text-lg pt-2">
            <span>مبلغ</span>
            <span className="font-mono text-primary">
              {formData.amount ? formatCurrency(formData.amount) : '-'}
            </span>
          </div>
        </div>
      </Card>

      {/* Workflow Information */}
      <Card className="p-4 bg-blue-50 border-blue-200">
        <div className="flex items-start gap-3">
          <Info className="h-5 w-5 text-blue-600 mt-0.5" />
          <div className="flex-1 text-sm text-blue-900">
            <h5 className="mb-2">گردش کار تایید</h5>
            <ol className="list-decimal list-inside space-y-1 text-blue-700">
              <li>پس از ثبت، تراکنش در وضعیت "در انتظار تایید" قرار می‌گیرد</li>
              <li>مدیر مالی تراکنش را بررسی می‌کند</li>
              <li>در صورت تایید، تراکنش برای پرداخت آماده می‌شود</li>
              <li>در صورت رد، دلیل رد به شما اطلاع داده می‌شود</li>
            </ol>
          </div>
        </div>
      </Card>

      {/* Final Checklist */}
      <Card className="p-4">
        <h5 className="mb-3">چک‌لیست نهایی</h5>
        <div className="space-y-2 text-sm">
          <label className="flex items-center gap-2">
            <input type="checkbox" className="rounded" defaultChecked disabled />
            <span>اطلاعات واحد سازمانی صحیح است</span>
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" className="rounded" defaultChecked disabled />
            <span>ردیف بودجه مناسب انتخاب شده است</span>
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" className="rounded" defaultChecked disabled />
            <span>مبلغ تراکنش صحیح وارد شده است</span>
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" className="rounded" defaultChecked disabled />
            <span>کد یکتای تولید شده را بررسی کرده‌ام</span>
          </label>
        </div>
      </Card>

      {/* Primary Action Prompt */}
      <div className="bg-gradient-to-r from-primary/10 to-primary/5 p-6 rounded-lg text-center border-2 border-primary/20">
        <p className="text-lg mb-2">آماده ثبت نهایی تراکنش هستید؟</p>
        <p className="text-sm text-muted-foreground">
          با کلیک بر روی دکمه "ثبت نهایی تراکنش" در پایین صفحه، تراکنش شما ثبت و برای تایید ارسال می‌شود
        </p>
      </div>
    </div>
  );
}
