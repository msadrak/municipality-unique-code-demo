import React, { useCallback, useRef, useState } from 'react';
import {
  AlertTriangle,
  Banknote,
  Building2,
  CalendarDays,
  CheckCircle,
  FileText,
  Hash,
  Loader2,
  XCircle,
} from 'lucide-react';
import { ContractorSelect } from '../contracts/ContractorSelect';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import { Input } from '../ui/input';
import { formatRial } from '../../lib/utils';
import {
  type GaamValidationResult,
  validateContractorInGaam,
} from '../../services/mockGaamService';
import type { ContractorListItem } from '../../services/contracts';
import type { TransactionFormData } from '../TransactionWizard';

type Props = {
  formData: TransactionFormData;
  updateFormData: (data: Partial<TransactionFormData>) => void;
};

export function WizardStep_ContractorAndDetails({ formData, updateFormData }: Props) {
  const [selectedContractor, setSelectedContractor] = useState<ContractorListItem | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<GaamValidationResult | null>(null);
  const validationRequestRef = useRef(0);

  const [rawAmount, setRawAmount] = useState<string>(
    formData.contractTotalAmount ? String(formData.contractTotalAmount) : '',
  );

  const handleContractorChange = useCallback(
    async (contractor: ContractorListItem) => {
      const requestId = ++validationRequestRef.current;

      setSelectedContractor(contractor);
      setIsValidating(true);
      setValidationResult(null);

      updateFormData({
        contractorId: contractor.id,
        contractorName: contractor.company_name,
        contractorGaamStatus: undefined,
        contractorGaamMessage: undefined,
        contractorGaamMissingDocs: undefined,
        contractorGaamValidationPending: true,
      });

      try {
        const result = await validateContractorInGaam(contractor.national_id);
        if (requestId !== validationRequestRef.current) return;

        setValidationResult(result);
        updateFormData({
          contractorGaamStatus: result.status,
          contractorGaamMessage: result.message,
          contractorGaamMissingDocs: result.missingDocs,
          contractorGaamValidationPending: false,
        });
      } catch (error) {
        if (requestId !== validationRequestRef.current) return;

        const fallbackResult: GaamValidationResult = {
          status: 'BLACKLISTED',
          message: 'خطا: ارتباط با سامانه گام برقرار نشد. لطفاً مجدداً تلاش کنید.',
        };

        setValidationResult(fallbackResult);
        updateFormData({
          contractorGaamStatus: fallbackResult.status,
          contractorGaamMessage: fallbackResult.message,
          contractorGaamMissingDocs: undefined,
          contractorGaamValidationPending: false,
        });
        console.error('[WizardStep_ContractorAndDetails] Gaam validation failed:', error);
      } finally {
        if (requestId === validationRequestRef.current) {
          setIsValidating(false);
        }
      }
    },
    [updateFormData],
  );

  const handleAmountChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const raw = e.target.value.replace(/[^0-9]/g, '');
      setRawAmount(raw);
      const numericValue = raw ? parseInt(raw, 10) : undefined;
      updateFormData({ contractTotalAmount: numericValue });
    },
    [updateFormData],
  );

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold">اطلاعات پیمانکار و قرارداد</h3>
        <p className="text-sm text-muted-foreground mt-1">
          پیمانکار برنده مناقصه را انتخاب کرده و اطلاعات اولیه پیمان را وارد نمایید.
        </p>
      </div>

      {formData.civilProjectTitle && (
        <div className="flex items-center gap-3 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3">
          <Building2 className="h-5 w-5 text-primary flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-primary leading-snug truncate">
              پروژه انتخابی: {formData.civilProjectTitle}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
              <Hash className="h-3 w-3" />
              <span className="font-mono-num">{formData.civilProjectCode}</span>
              {formData.civilProjectZone && (
                <span className="mr-2">• {formData.civilProjectZone}</span>
              )}
            </p>
          </div>
        </div>
      )}

      <div className="space-y-3">
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm font-medium select-none">
            <span className="text-red-500">*</span>
            پیمانکار (برنده مناقصه)
          </label>
          <ContractorSelect value={selectedContractor} onChange={handleContractorChange} />
        </div>

        {isValidating && (
          <Alert className="border-sky-200 bg-sky-50 text-sky-900">
            <Loader2 className="h-4 w-4 animate-spin text-sky-700" />
            <AlertTitle>در حال استعلام صلاحیت از سامانه گام...</AlertTitle>
          </Alert>
        )}

        {!isValidating && validationResult?.status === 'VERIFIED' && (
          <Alert className="border-emerald-200 bg-emerald-50 text-emerald-900">
            <CheckCircle className="h-4 w-4 text-emerald-700" />
            <AlertTitle>وضعیت تایید شد</AlertTitle>
            <AlertDescription className="text-emerald-800">
              {validationResult.message}
            </AlertDescription>
          </Alert>
        )}

        {!isValidating && validationResult?.status === 'PENDING_DOCS' && (
          <Alert className="border-amber-200 bg-amber-50 text-amber-900">
            <AlertTriangle className="h-4 w-4 text-amber-700" />
            <AlertTitle>مدارک ناقص</AlertTitle>
            <AlertDescription className="text-amber-800 space-y-2">
              <p>{validationResult.message}</p>
              {validationResult.missingDocs && validationResult.missingDocs.length > 0 && (
                <ul className="list-disc pr-5 space-y-1">
                  {validationResult.missingDocs.map((doc) => (
                    <li key={doc}>{doc}</li>
                  ))}
                </ul>
              )}
            </AlertDescription>
          </Alert>
        )}

        {!isValidating && validationResult?.status === 'BLACKLISTED' && (
          <Alert variant="destructive" className="border-red-300 bg-red-50 text-red-900">
            <XCircle className="h-4 w-4 text-red-700" />
            <AlertTitle>عدم تایید صلاحیت</AlertTitle>
            <AlertDescription className="text-red-800">
              {validationResult.message}
            </AlertDescription>
          </Alert>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="space-y-2">
          <label
            htmlFor="contract_number"
            className="flex items-center gap-2 text-sm font-medium select-none"
          >
            <FileText className="h-4 w-4 text-muted-foreground" />
            <span className="text-red-500">*</span>
            شماره قرارداد
          </label>
          <Input
            id="contract_number"
            type="text"
            dir="rtl"
            placeholder="مثال: ۱۴۰۳/۱۲۳۴"
            value={formData.contractNumberNew ?? ''}
            onChange={(e) => updateFormData({ contractNumberNew: e.target.value })}
          />
        </div>

        <div className="space-y-2">
          <label
            htmlFor="contract_date"
            className="flex items-center gap-2 text-sm font-medium select-none"
          >
            <CalendarDays className="h-4 w-4 text-muted-foreground" />
            <span className="text-red-500">*</span>
            تاریخ ابلاغ/انعقاد
          </label>
          <Input
            id="contract_date"
            type="text"
            dir="ltr"
            placeholder="۱۴۰۳/۰۱/۰۱"
            className="font-mono-num text-center"
            value={formData.contractDate ?? ''}
            onChange={(e) => updateFormData({ contractDate: e.target.value })}
          />
        </div>

        <div className="space-y-2 md:col-span-2">
          <label
            htmlFor="total_amount"
            className="flex items-center gap-2 text-sm font-medium select-none"
          >
            <Banknote className="h-4 w-4 text-muted-foreground" />
            <span className="text-red-500">*</span>
            مبلغ اولیه پیمان (ریال)
          </label>
          <Input
            id="total_amount"
            type="text"
            inputMode="numeric"
            dir="ltr"
            placeholder="0"
            className="font-mono-num text-left"
            value={rawAmount}
            onChange={handleAmountChange}
          />
          {formData.contractTotalAmount != null && formData.contractTotalAmount > 0 && (
            <p className="text-xs text-muted-foreground font-mono-num pr-1">
              {formatRial(formData.contractTotalAmount)}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
