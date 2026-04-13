import React, { useState } from 'react';
import { AlertCircle, FileSpreadsheet, Loader2, UploadCloud } from 'lucide-react';
import { toast } from 'sonner';

import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { uploadContractorStatement } from '../../services/attendance';
import { cn } from '../../components/ui/utils';

const persianDigitMap: Record<string, string> = {
  '۰': '0',
  '۱': '1',
  '۲': '2',
  '۳': '3',
  '۴': '4',
  '۵': '5',
  '۶': '6',
  '۷': '7',
  '۸': '8',
  '۹': '9',
};

function normalizeNumericInput(value: string): string {
  return value
    .replace(/[۰-۹]/g, (digit) => persianDigitMap[digit] ?? digit)
    .replace(/[^\d]/g, '');
}

function formatCurrencyInput(value: string): string {
  if (!value) return '';
  return new Intl.NumberFormat('fa-IR').format(Number(value));
}

export default function ContractorStatementUpload() {
  const [year, setYear] = useState('1403');
  const [month, setMonth] = useState('1');
  const [regionName, setRegionName] = useState('');
  const [declaredTotalAmount, setDeclaredTotalAmount] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedDeclaredTotal = normalizeNumericInput(declaredTotalAmount);
    const declaredTotalValue = Number(normalizedDeclaredTotal);

    if (!year || !month || !regionName.trim()) {
      setError('تمامی فیلدها الزامی هستند.');
      return;
    }

    if (!normalizedDeclaredTotal || declaredTotalValue <= 0) {
      setError('مبلغ کل درخواستی را به‌صورت صحیح وارد کنید.');
      return;
    }

    if (!file) {
      setError('فایل اکسل را انتخاب کنید.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const sheet = await uploadContractorStatement({
        file,
        year: parseInt(year, 10),
        month: parseInt(month, 10),
        region_name: regionName.trim(),
        declared_total_amount: declaredTotalValue,
      });
      toast.success('فایل صورت وضعیت با موفقیت بارگذاری شد.');
      toast.message(`بارگذاری برای ${sheet.region} ثبت شد.`);
      setYear('1403');
      setMonth('1');
      setRegionName('');
      setDeclaredTotalAmount('');
      setFile(null);
      const fileInput = document.getElementById('statement-file') as HTMLInputElement | null;
      if (fileInput) {
        fileInput.value = '';
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'بارگذاری فایل ناموفق بود.';
      setError(message);
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const formattedDeclaredTotal = formatCurrencyInput(normalizeNumericInput(declaredTotalAmount));
  const canSubmit =
    !isSubmitting &&
    Boolean(file) &&
    Boolean(regionName.trim()) &&
    Boolean(year) &&
    Boolean(month) &&
    Number(normalizeNumericInput(declaredTotalAmount)) > 0;

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-8 py-8 animate-fade-in-up">
      <div className="flex flex-col items-center justify-center gap-4 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-blue-500/10 text-blue-400 glass-vault shadow-[0_0_20px_rgba(137,206,255,0.1)]">
          <UploadCloud className="h-8 w-8" />
        </div>
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight text-[var(--vault-on-surface)]">آپلود صورت وضعیت مالی</h1>
          <p className="text-lg text-[var(--vault-on-surface-variant)]">
            ارسال فایل ۶ ستونی صورت وضعیت پیمانکار (The Ice Vault)
          </p>
        </div>
      </div>

      <div className="glass-vault overflow-hidden rounded-[2rem] border border-[var(--vault-surface-highest)] bg-transparent p-1">
        <div className="rounded-[1.9rem] bg-[var(--vault-surface-low)] p-8 shadow-2xl">
          <form className="space-y-8" onSubmit={handleSubmit}>
            {error ? (
              <Alert className="border-rose-500/20 bg-rose-500/5 text-rose-200 glass-vault">
                <AlertCircle className="h-4 w-4 text-rose-400" />
                <AlertTitle>خطا در پردازش فایل</AlertTitle>
                <AlertDescription className="text-rose-300/80">{error}</AlertDescription>
              </Alert>
            ) : null}

            <div className="grid gap-6 md:grid-cols-2">
              <div className="space-y-3 text-right">
                <label className="text-sm font-semibold text-[var(--vault-on-surface-variant)] px-1" htmlFor="statement-region">
                  نام منطقه (جهت تطبیق)
                </label>
                <Input
                  id="statement-region"
                  value={regionName}
                  onChange={(event) => setRegionName(event.target.value)}
                  placeholder="مثلاً منطقه ۵"
                  className="input-vault h-12 rounded-xl"
                />
              </div>

              <div className="hidden md:block"></div>

              <div className="space-y-3 text-right">
                <label className="text-sm font-semibold text-[var(--vault-on-surface-variant)] px-1" htmlFor="statement-year">
                  سال
                </label>
                <Input
                  id="statement-year"
                  type="number"
                  value={year}
                  onChange={(event) => setYear(event.target.value)}
                  placeholder="مثلاً ۱۴۰۳"
                  className="input-vault h-12 rounded-xl"
                />
              </div>

              <div className="space-y-3 text-right">
                <label className="text-sm font-semibold text-[var(--vault-on-surface-variant)] px-1" htmlFor="statement-month">
                  ماه
                </label>
                <Input
                  id="statement-month"
                  type="number"
                  value={month}
                  onChange={(event) => setMonth(event.target.value)}
                  placeholder="مثلاً ۱"
                  min={1}
                  max={12}
                  className="input-vault h-12 rounded-xl"
                />
              </div>
              <div className="space-y-3 text-right md:col-span-2">
                <label className="text-sm font-semibold text-[var(--vault-on-surface-variant)] px-1" htmlFor="statement-declared-total">
                  مبلغ کل درخواستی (ریال)
                </label>
                <Input
                  id="statement-declared-total"
                  type="text"
                  inputMode="numeric"
                  dir="ltr"
                  value={formattedDeclaredTotal}
                  onChange={(event) => setDeclaredTotalAmount(event.target.value)}
                  placeholder="مثلاً ۱۲۳,۴۵۶,۷۸۹"
                  className="input-vault h-12 rounded-xl text-left"
                />
              </div>
            </div>

            <div className="space-y-3 text-right">
              <label className="text-sm font-semibold text-[var(--vault-on-surface-variant)] px-1">
                فایل اکسل صورت وضعیت (۶ ستونی)
              </label>
              <label
                htmlFor="statement-file"
                className={cn(
                  "group relative flex min-h-[12rem] cursor-pointer flex-col items-center justify-center gap-4 rounded-3xl border-2 border-dashed border-[var(--vault-surface-highest)] bg-[var(--vault-surface-highest)]/30 px-6 py-10 text-center transition-all duration-300",
                  "hover:border-blue-400/30 hover:bg-blue-400/5 hover:shadow-[0_0_40px_rgba(137,206,255,0.05)]",
                  file && "border-blue-400/40 bg-blue-400/5"
                )}
              >
                <div className={cn(
                  "flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--vault-surface-highest)] text-blue-500 shadow-sm transition-transform duration-300 group-hover:scale-110",
                  file && "bg-blue-400/10"
                )}>
                  <FileSpreadsheet className="h-7 w-7" />
                </div>
                <div className="space-y-2">
                  <p className="text-base font-medium text-[var(--vault-on-surface)]">
                    {file ? file.name : 'برای انتخاب فایل کلیک کنید یا فایل را اینجا رها کنید'}
                  </p>
                  <p className="text-sm text-[var(--vault-on-surface-variant)]">فرمت‌های پشتیبانی‌شده: xlsx و xls</p>
                </div>
              </label>
              <Input
                id="statement-file"
                type="file"
                accept=".xlsx,.xls"
                className="hidden"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            </div>

            <div className="flex justify-center pt-4">
              <Button type="submit" disabled={!canSubmit} className={cn(
                "h-14 min-w-[200px] rounded-2xl text-lg font-bold transition-all duration-300",
                "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-900/20 hover:scale-[1.02] hover:shadow-blue-500/20 active:scale-95"
              )}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="ml-2 h-5 w-5 animate-spin" />
                    در حال ارسال...
                  </>
                ) : (
                  'ارسال صورت وضعیت نهایی'
                )}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
