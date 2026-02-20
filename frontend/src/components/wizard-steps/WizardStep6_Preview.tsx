import React, { useEffect, useState } from 'react';
import { TransactionFormData } from '../TransactionWizard';
import { Card } from '../ui/card';
import { Separator } from '../ui/separator';
import { Hash, Calendar, Building2, Wallet, User, FileText } from 'lucide-react';
import { CodeSegmentItem, SEGMENT_MAP, SegmentInfo } from '../ui/SegmentPopover';
import { formatRial } from '../../lib/utils';

type Props = {
  formData: TransactionFormData;
  updateFormData: (data: Partial<TransactionFormData>) => void;
};

export function WizardStep6_Preview({ formData, updateFormData }: Props) {
  const [segments, setSegments] = useState<SegmentInfo[]>([]);

  useEffect(() => {
    // Generate the unique 11-part code and segments
    const generatedSegments = generateSegments(formData);
    setSegments(generatedSegments);

    // Build unique code from segments
    const code = generatedSegments.map(s => s.value).join('-');
    updateFormData({ uniqueCode: code });
  }, [formData.zoneCode, formData.departmentCode, formData.sectionCode, formData.budgetCode,
  formData.costCenterCode, formData.continuousActionCode, formData.financialEventCode,
  formData.fiscalYear, formData.beneficiaryName]);

  return (
    <div className="space-y-6">
      <div>
        <h3>پیش‌نمایش کد یکتا و اطلاعات تراکنش</h3>
        <p className="text-sm text-muted-foreground mt-1">
          کد یکتای تراکنش به صورت خودکار تولید شده است. روی هر قسمت کد کلیک کنید تا جزئیات آن را ببینید
        </p>
      </div>

      {/* Unique Code Display - Interactive Segments */}
      <Card className="p-6 bg-gradient-to-br from-primary/5 to-primary/10 border-2 border-primary/20">
        <div className="text-center space-y-3">
          <div className="flex justify-center">
            <div className="bg-primary p-3 rounded-full">
              <Hash className="h-6 w-6 text-primary-foreground" />
            </div>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">کد یکتای تراکنش (کلیک کنید)</p>
            <div className="relative mt-2">
              <div className="flex flex-wrap justify-center items-center gap-1 text-lg" dir="ltr">
                {segments.map((segment, index) => (
                  <React.Fragment key={index}>
                    <CodeSegmentItem segment={segment} />
                    {index < segments.length - 1 && (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            این کد برای شناسایی یکتای تراکنش در سامانه استفاده می‌شود
          </p>
        </div>
      </Card>

      {/* Code Breakdown Summary */}
      <Card className="p-4">
        <h4 className="mb-3">اجزای کد یکتا</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
          {segments.slice(0, 6).map((segment) => (
            <div key={segment.index} className="flex items-start gap-2">
              <span className="text-muted-foreground min-w-[80px]">{segment.name}:</span>
              <span className="font-mono">{segment.value}</span>
            </div>
          ))}
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
            <p>{formData.zoneName} ← {formData.departmentName || '-'} ← {formData.sectionName || '-'}</p>
            <p className="text-muted-foreground text-xs">
              کد: {formData.zoneCode}-{formData.departmentCode || '00'}-{formData.sectionCode || '000'}
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
              <p>{formData.financialEventName || '-'}</p>
            </div>
            <div>
              <p className="text-muted-foreground">مرکز هزینه</p>
              <p>{formData.costCenterName || '-'}</p>
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
              <p className="text-xl font-mono-num text-primary">
                {formData.amount ? formatRial(formData.amount) : '-'}
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
    </div >
  );
}

// Helper function to generate segment info with source values
function generateSegments(data: TransactionFormData): SegmentInfo[] {
  const hashString = (str: string, length: number) => {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return Math.abs(hash).toString(16).toUpperCase().padStart(length, '0').slice(0, length);
  };

  return SEGMENT_MAP.map((meta) => {
    let value = '??';
    let sourceTitle = '';
    let sourceCode = '';

    switch (meta.key) {
      case 'zone':
        value = (data.zoneCode || '00').padStart(2, '0');
        sourceTitle = data.zoneName || '';
        sourceCode = data.zoneCode || '';
        break;
      case 'department':
        value = (data.departmentCode || '00').padStart(2, '0');
        sourceTitle = data.departmentName || '';
        sourceCode = data.departmentCode || '';
        break;
      case 'section':
        value = (data.sectionCode || '000').padStart(3, '0');
        sourceTitle = data.sectionName || '';
        sourceCode = data.sectionCode || '';
        break;
      case 'budget':
        value = data.budgetCode || '????????';
        sourceTitle = data.budgetDescription || '';
        sourceCode = data.budgetCode || '';
        break;
      case 'costCenter':
        value = (data.costCenterCode || '000').padStart(3, '0');
        sourceTitle = data.costCenterName || '';
        sourceCode = data.costCenterCode || '';
        break;
      case 'continuousAction':
        value = (data.continuousActionCode || '00').padStart(2, '0');
        sourceTitle = data.continuousActionName || '';
        sourceCode = data.continuousActionCode || '';
        break;
      case 'specialActivity':
        value = '000'; // Placeholder for special activity hash
        sourceTitle = 'فعالیت خاص';
        break;
      case 'beneficiary':
        value = data.beneficiaryName ? hashString(data.beneficiaryName, 6) : 'XXXXXX';
        sourceTitle = data.beneficiaryName || '';
        break;
      case 'financialEvent':
        value = (data.financialEventCode || '000').padStart(3, '0');
        sourceTitle = data.financialEventName || '';
        sourceCode = data.financialEventCode || '';
        break;
      case 'fiscalYear':
        value = data.fiscalYear || '1403';
        sourceTitle = `سال مالی ${data.fiscalYear || '1403'}`;
        break;
      case 'sequence':
        value = '001'; // Will be set by backend
        sourceTitle = 'شماره ترتیب (توسط سیستم تعیین می‌شود)';
        break;
    }

    return {
      ...meta,
      value,
      sourceTitle,
      sourceCode,
    };
  });
}

export default WizardStep6_Preview;
