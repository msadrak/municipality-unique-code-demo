import React, { useEffect } from 'react';
import { TransactionFormData } from '../TransactionWizard';
import { Card } from '../ui/card';
import { Separator } from '../ui/separator';
import { Hash, Calendar, Building2, Wallet, User, FileText } from 'lucide-react';

type Props = {
  formData: TransactionFormData;
  updateFormData: (data: Partial<TransactionFormData>) => void;
};

export function WizardStep6_Preview({ formData, updateFormData }: Props) {
  useEffect(() => {
    // Generate the unique 11-part code
    const code = generateUniqueCode(formData);
    updateFormData({ uniqueCode: code });
  }, [formData, updateFormData]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('fa-IR').format(amount) + ' ریال';
  };

  return (
    <div className="space-y-6">
      <div>
        <h3>پیش‌نمایش کد یکتا و اطلاعات تراکنش</h3>
        <p className="text-sm text-muted-foreground mt-1">
          کد یکتای تراکنش به صورت خودکار تولید شده است. لطفاً اطلاعات را بررسی کنید
        </p>
      </div>

      {/* Unique Code Display - Prominent */}
      <Card className="p-6 bg-gradient-to-br from-primary/5 to-primary/10 border-2 border-primary/20">
        <div className="text-center space-y-3">
          <div className="flex justify-center">
            <div className="bg-primary p-3 rounded-full">
              <Hash className="h-6 w-6 text-primary-foreground" />
            </div>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">کد یکتای تراکنش</p>
            <p className="text-2xl font-mono mt-2 tracking-wider" dir="ltr">
              {formData.uniqueCode}
            </p>
          </div>
          <p className="text-xs text-muted-foreground">
            این کد برای شناسایی یکتای تراکنش در سامانه استفاده می‌شود
          </p>
        </div>
      </Card>

      {/* Code Breakdown - Progressive Disclosure */}
      <Card className="p-4">
        <h4 className="mb-3">اجزای کد یکتا</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground min-w-[100px]">منطقه/معاونت:</span>
            <span className="font-mono">{formData.zoneCode}</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground min-w-[100px]">اداره:</span>
            <span className="font-mono">{formData.departmentCode}</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground min-w-[100px]">قسمت:</span>
            <span className="font-mono">{formData.sectionCode}</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground min-w-[100px]">بودجه:</span>
            <span className="font-mono">{formData.budgetCode}</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground min-w-[100px]">مرکز هزینه:</span>
            <span className="font-mono">{formData.costCenterCode}</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-muted-foreground min-w-[100px]">رویداد مالی:</span>
            <span className="font-mono">{formData.financialEventCode}</span>
          </div>
        </div>
      </Card>

      <Separator />

      {/* Transaction Summary - Grouped Information */}
      <div className="space-y-4">
        <h4>خلاصه اطلاعات تراکنش</h4>

        {/* General Info */}
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Calendar className="h-4 w-4 text-primary" />
            <h5>اطلاعات عمومی</h5>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-muted-foreground">نوع تراکنش</p>
              <p>{formData.transactionType === 'expense' ? 'هزینه‌ای' : 'سرمایه‌ای'}</p>
            </div>
            <div>
              <p className="text-muted-foreground">سال مالی</p>
              <p>{formData.fiscalYear}</p>
            </div>
          </div>
        </Card>

        {/* Organization */}
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Building2 className="h-4 w-4 text-primary" />
            <h5>واحد سازمانی</h5>
          </div>
          <div className="space-y-2 text-sm">
            <p>{formData.zoneName} ← {formData.departmentName} ← {formData.sectionName}</p>
            <p className="text-muted-foreground text-xs">
              کد: {formData.zoneCode}-{formData.departmentCode}-{formData.sectionCode}
            </p>
          </div>
        </Card>

        {/* Budget */}
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Wallet className="h-4 w-4 text-primary" />
            <h5>ردیف بودجه</h5>
          </div>
          <div className="space-y-2 text-sm">
            <p className="font-mono">{formData.budgetCode}</p>
            <p>{formData.budgetDescription}</p>
          </div>
        </Card>

        {/* Financial Details */}
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <FileText className="h-4 w-4 text-primary" />
            <h5>اطلاعات مالی</h5>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-muted-foreground">رویداد مالی</p>
              <p>{formData.financialEventName}</p>
            </div>
            <div>
              <p className="text-muted-foreground">مرکز هزینه</p>
              <p>{formData.costCenterName}</p>
            </div>
            {formData.continuousActionName && (
              <div>
                <p className="text-muted-foreground">اقدام مستمر</p>
                <p>{formData.continuousActionName}</p>
              </div>
            )}
          </div>
        </Card>

        {/* Beneficiary & Amount */}
        <Card className="p-4 bg-accent/50">
          <div className="flex items-center gap-2 mb-3">
            <User className="h-4 w-4 text-primary" />
            <h5>ذینفع و مبلغ</h5>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            {formData.beneficiaryName && (
              <div>
                <p className="text-muted-foreground">نام ذینفع</p>
                <p>{formData.beneficiaryName}</p>
              </div>
            )}
            {formData.contractNumber && (
              <div>
                <p className="text-muted-foreground">شماره قرارداد</p>
                <p>{formData.contractNumber}</p>
              </div>
            )}
            <div className="md:col-span-2">
              <p className="text-muted-foreground">مبلغ</p>
              <p className="text-xl font-mono text-primary">
                {formData.amount ? formatCurrency(formData.amount) : '-'}
              </p>
            </div>
            {formData.description && (
              <div className="md:col-span-2">
                <p className="text-muted-foreground">توضیحات</p>
                <p className="text-sm">{formData.description}</p>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Warning */}
      <Card className="p-4 bg-amber-50 border-amber-200">
        <p className="text-sm text-amber-900">
          ⚠️ لطفاً تمامی اطلاعات را با دقت بررسی کنید. پس از ثبت نهایی، تراکنش برای تایید به مدیر ارسال می‌شود.
        </p>
      </Card>
    </div>
  );
}

// Helper function to generate unique code
function generateUniqueCode(data: TransactionFormData): string {
  const parts = [
    data.zoneCode || '??',
    data.departmentCode || '??',
    data.sectionCode || '???',
    data.budgetCode || '????????',
    data.costCenterCode || '???',
    data.continuousActionCode || '??',
    '000', // Specific activity (placeholder)
    'A1B2C3', // Beneficiary hash (placeholder)
    data.financialEventCode || '???',
    data.fiscalYear || '????',
    '001', // Sequence (placeholder)
  ];
  
  return parts.join('-');
}
