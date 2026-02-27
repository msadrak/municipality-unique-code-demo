import React, { useState, useCallback } from 'react';
import { Search, Loader2, CheckCircle2, AlertCircle, FileText, Building2, Hash } from 'lucide-react';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Alert, AlertTitle, AlertDescription } from '../ui/alert';
import { formatRial } from '../../lib/utils';
import {
  fetchCivilCreditByNumber,
  type CivilCreditInfo,
} from '../../services/mockCivilCreditService';
import type { TransactionFormData } from '../TransactionWizard';

type Props = {
  formData: TransactionFormData;
  updateFormData: (data: Partial<TransactionFormData>) => void;
};

export function WizardStep3_CivilCredit({ formData, updateFormData }: Props) {
  const [inputCode, setInputCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [fetchedData, setFetchedData] = useState<CivilCreditInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFetch = useCallback(async () => {
    const trimmed = inputCode.trim();
    if (!trimmed) return;

    setIsLoading(true);
    setError(null);
    setFetchedData(null);

    updateFormData({
      civilCreditFormNumber: undefined,
      civilBudgetRowCode: undefined,
      civilBudgetRowTitle: undefined,
      civilEstimatedAmount: undefined,
    });

    try {
      const result = await fetchCivilCreditByNumber(
        trimmed,
        formData.civilProjectCode || '',
      );
      setFetchedData(result);

      updateFormData({
        civilCreditFormNumber: result.credit_form_number,
        civilBudgetRowCode: result.budget_row_code,
        civilBudgetRowTitle: result.budget_row_title,
        civilEstimatedAmount: result.estimated_amount,
      });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'خطا در استعلام تأمین اعتبار',
      );
    } finally {
      setIsLoading(false);
    }
  }, [inputCode, formData.civilProjectCode, updateFormData]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && inputCode.trim() && !isLoading) {
        handleFetch();
      }
    },
    [handleFetch, inputCode, isLoading],
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold">تأمین اعتبار پروژه عمرانی</h3>
        <p className="text-sm text-muted-foreground mt-1">
          شماره فرم تأمین اعتبار را وارد نمایید تا اطلاعات مالی از سامانه عمران دریافت شود.
        </p>
      </div>

      {/* Project context banner */}
      {formData.civilProjectTitle && (
        <div className="flex items-center gap-3 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3">
          <Building2 className="h-5 w-5 text-primary flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-primary leading-snug truncate">
              پروژه: {formData.civilProjectTitle}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
              <Hash className="h-3 w-3" />
              <span className="font-mono-num">{formData.civilProjectCode}</span>
            </p>
          </div>
        </div>
      )}

      {/* Input row */}
      <div className="flex items-end gap-3">
        <div className="flex-1 space-y-2">
          <label className="flex items-center gap-2 text-sm font-medium select-none">
            <span className="text-red-500">*</span>
            شماره فرم تأمین اعتبار
          </label>
          <Input
            dir="ltr"
            placeholder="کد/شماره فرم تأمین اعتبار را وارد کنید (مثال: ۴۰۴۱۵۰۲۴۸)"
            className="font-mono-num text-left"
            value={inputCode}
            onChange={(e) => setInputCode(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
        </div>
        <Button
          type="button"
          onClick={handleFetch}
          disabled={isLoading || !inputCode.trim()}
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 ml-2 animate-spin" />
          ) : (
            <Search className="h-4 w-4 ml-2" />
          )}
          استعلام از سامانه عمران
        </Button>
      </div>

      {/* Error alert */}
      {error && (
        <Alert variant="destructive" className="border-red-300 bg-red-50 text-red-900">
          <AlertCircle className="h-4 w-4 text-red-700" />
          <AlertTitle>خطا در استعلام</AlertTitle>
          <AlertDescription className="text-red-800">{error}</AlertDescription>
        </Alert>
      )}

      {/* Credit provision card */}
      {fetchedData && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm space-y-5">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
              <FileText className="h-5 w-5 text-primary" />
              <h4 className="font-semibold text-primary">کارت تأمین اعتبار</h4>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">شماره فرم</p>
                <p className="font-mono-num text-sm font-medium">
                  {fetchedData.credit_form_number}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">کد ردیف بودجه</p>
                <p
                  dir="ltr"
                  className="font-mono-num text-sm font-medium text-left"
                >
                  {fetchedData.budget_row_code}
                </p>
              </div>
              <div className="space-y-1 md:col-span-2">
                <p className="text-xs text-muted-foreground">عنوان ردیف بودجه</p>
                <p className="text-sm font-medium leading-6">
                  {fetchedData.budget_row_title}
                </p>
              </div>
              <div className="space-y-1 md:col-span-2 pt-2 border-t border-slate-100">
                <p className="text-xs text-muted-foreground">برآورد مالی (ریال)</p>
                <p className="font-mono-num text-xl font-bold text-primary">
                  {formatRial(fetchedData.estimated_amount)}
                </p>
              </div>
            </div>
          </div>

          <Alert className="border-emerald-200 bg-emerald-50 text-emerald-900">
            <CheckCircle2 className="h-4 w-4 text-emerald-700" />
            <AlertTitle>اطلاعات تأمین اعتبار دریافت شد</AlertTitle>
            <AlertDescription className="text-emerald-800">
              برای مسدودی این مبلغ، به مرحله بعد بروید.
            </AlertDescription>
          </Alert>
        </div>
      )}
    </div>
  );
}
