import React, { useState } from 'react';
import { AlertCircle, Download, FileSpreadsheet, Loader2, Plus, Send, Trash2, UploadCloud } from 'lucide-react';
import { toast } from 'sonner';
import * as XLSX from 'xlsx';

import { AUTHORIZED_REGIONS } from '../../constants/regions';
import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
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

type RowData = {
  'ردیف': number;
  'مرکز هزینه': string;
  'عنوان': string;
  'متراژ': string;
  'فی': string;
  'جمع': string;
};

const EMPTY_ROW: Omit<RowData, 'ردیف'> = { 'مرکز هزینه': '', 'عنوان': '', 'متراژ': '', 'فی': '', 'جمع': '' };

export default function ContractorStatementUpload() {
  const [year, setYear] = useState('1403');
  const [month, setMonth] = useState('1');
  const [regionName, setRegionName] = useState('');
  const [declaredTotalAmount, setDeclaredTotalAmount] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [manualRows, setManualRows] = useState<RowData[]>([{ 'ردیف': 1, ...EMPTY_ROW }]);
  const [validationErrors, setValidationErrors] = useState<Set<string>>(new Set());
  const [activeTab, setActiveTab] = useState('upload');

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedDeclaredTotal = normalizeNumericInput(declaredTotalAmount);
    const declaredTotalValue = Number(normalizedDeclaredTotal);

    if (!year || !month || !regionName) {
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
        region_name: regionName,
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

  const addRow = () => {
    setManualRows((prev) => [...prev, { 'ردیف': prev.length + 1, ...EMPTY_ROW }]);
  };

  const deleteRow = (index: number) => {
    setManualRows((prev) => {
      const updated = prev.filter((_, i) => i !== index);
      // Re-index ردیف
      return updated.map((row, i) => ({ ...row, 'ردیف': i + 1 }));
    });
    setValidationErrors(new Set());
  };

  const updateCell = (rowIndex: number, field: keyof Omit<RowData, 'ردیف'>, value: string) => {
    setManualRows((prev) =>
      prev.map((row, i) => (i === rowIndex ? { ...row, [field]: value } : row))
    );
    setValidationErrors((prev) => {
      const updated = new Set(prev);
      updated.delete(`${rowIndex}-${field}`);
      return updated;
    });
  };

  const validateManualRows = (): boolean => {
    const errors = new Set<string>();
    manualRows.forEach((row, index) => {
      if (!row['مرکز هزینه'].trim()) errors.add(`${index}-مرکز هزینه`);
      if (!row['عنوان'].trim()) errors.add(`${index}-عنوان`);
    });
    setValidationErrors(errors);
    return errors.size === 0;
  };

  const generateWorkbook = (): XLSX.WorkBook => {
    const ws = XLSX.utils.json_to_sheet(manualRows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'صورت وضعیت');
    return wb;
  };

  const handleDownloadExcel = () => {
    if (!validateManualRows()) {
      toast.error('لطفاً تمامی فیلدهای الزامی (مرکز هزینه و عنوان) را تکمیل کنید.');
      return;
    }
    const wb = generateWorkbook();
    XLSX.writeFile(wb, `صورت-وضعیت-${year}-${month}.xlsx`);
    toast.success('فایل اکسل با موفقیت دانلود شد.');
  };

  const handleManualSubmit = async () => {
    const normalizedDeclaredTotal = normalizeNumericInput(declaredTotalAmount);
    const declaredTotalValue = Number(normalizedDeclaredTotal);

    if (!year || !month || !regionName) {
      setError('تمامی فیلدها الزامی هستند.');
      return;
    }

    if (!normalizedDeclaredTotal || declaredTotalValue <= 0) {
      setError('مبلغ کل درخواستی را به‌صورت صحیح وارد کنید.');
      return;
    }

    if (!validateManualRows()) {
      setError('لطفاً تمامی فیلدهای الزامی (مرکز هزینه و عنوان) را تکمیل کنید.');
      toast.error('لطفاً تمامی فیلدهای الزامی (مرکز هزینه و عنوان) را تکمیل کنید.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const wb = generateWorkbook();
      const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
      const blob = new Blob([wbout], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const generatedFile = new File([blob], `manual-entry-${year}-${month}.xlsx`, { type: blob.type });

      const sheet = await uploadContractorStatement({
        file: generatedFile,
        year: parseInt(year, 10),
        month: parseInt(month, 10),
        region_name: regionName,
        declared_total_amount: declaredTotalValue,
      });

      toast.success('صورت وضعیت دستی با موفقیت ثبت و به مدیر سیستم ارسال شد.');
      toast.message(`بارگذاری برای ${sheet.region} ثبت شد.`);
      
      setYear('1403');
      setMonth('1');
      setRegionName('');
      setDeclaredTotalAmount('');
      setManualRows([{ 'ردیف': 1, ...EMPTY_ROW }]);
      setValidationErrors(new Set());
    } catch (err) {
      const message = err instanceof Error ? err.message : 'ثبت صورت وضعیت ناموفق بود.';
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
    Boolean(regionName) &&
    Boolean(year) &&
    Boolean(month) &&
    Number(normalizeNumericInput(declaredTotalAmount)) > 0;
  const canManualSubmit = !isSubmitting && Boolean(regionName) && Boolean(year) && Boolean(month) && Number(normalizeNumericInput(declaredTotalAmount)) > 0;

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
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-8 bg-[var(--vault-surface-highest)]">
              <TabsTrigger value="upload" className="text-[var(--vault-on-surface)]">
                بارگذاری فایل اکسل
              </TabsTrigger>
              <TabsTrigger value="manual" className="text-[var(--vault-on-surface)]">
                ایجاد دستی فایل
              </TabsTrigger>
            </TabsList>

            <TabsContent value="upload">
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
                <label className="px-1 text-sm font-semibold text-[var(--vault-on-surface-variant)]" htmlFor="statement-region">
                  نام واحد سازمانی
                </label>
                <Select value={regionName} onValueChange={setRegionName}>
                  <SelectTrigger id="statement-region" className="input-vault h-12 rounded-xl text-right">
                    <SelectValue placeholder="واحد سازمانی را انتخاب کنید" />
                  </SelectTrigger>
                  <SelectContent>
                    {AUTHORIZED_REGIONS.map((region) => (
                      <SelectItem key={region} value={region}>
                        {region}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="hidden md:block"></div>

              <div className="space-y-3 text-right">
                <label className="px-1 text-sm font-semibold text-[var(--vault-on-surface-variant)]" htmlFor="statement-year">
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
                <label className="px-1 text-sm font-semibold text-[var(--vault-on-surface-variant)]" htmlFor="statement-month">
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
                <label className="px-1 text-sm font-semibold text-[var(--vault-on-surface-variant)]" htmlFor="statement-declared-total">
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
              <label className="px-1 text-sm font-semibold text-[var(--vault-on-surface-variant)]">
                فایل اکسل صورت وضعیت (۶ ستونی)
              </label>
              <label
                htmlFor="statement-file"
                className={cn(
                  'group relative flex min-h-[12rem] cursor-pointer flex-col items-center justify-center gap-4 rounded-3xl border-2 border-dashed border-[var(--vault-surface-highest)] bg-[var(--vault-surface-highest)]/30 px-6 py-10 text-center transition-all duration-300',
                  'hover:border-blue-400/30 hover:bg-blue-400/5 hover:shadow-[0_0_40px_rgba(137,206,255,0.05)]',
                  file && 'border-blue-400/40 bg-blue-400/5',
                )}
              >
                <div
                  className={cn(
                    'flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--vault-surface-highest)] text-blue-500 shadow-sm transition-transform duration-300 group-hover:scale-110',
                    file && 'bg-blue-400/10',
                  )}
                >
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
              <Button
                type="submit"
                disabled={!canSubmit}
                className={cn(
                  'h-14 min-w-[200px] rounded-2xl text-lg font-bold transition-all duration-300',
                  'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-900/20 hover:scale-[1.02] hover:shadow-blue-500/20 active:scale-95',
                )}
              >
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
            </TabsContent>

            <TabsContent value="manual">
              <div className="space-y-8">
                {error ? (
                  <Alert className="border-rose-500/20 bg-rose-500/5 text-rose-200 glass-vault">
                    <AlertCircle className="h-4 w-4 text-rose-400" />
                    <AlertTitle>خطا در پردازش</AlertTitle>
                    <AlertDescription className="text-rose-300/80">{error}</AlertDescription>
                  </Alert>
                ) : null}

                <div className="grid gap-6 md:grid-cols-2">
                  <div className="space-y-3 text-right">
                    <label className="px-1 text-sm font-semibold text-[var(--vault-on-surface-variant)]" htmlFor="manual-region">
                      نام واحد سازمانی
                    </label>
                    <Select value={regionName} onValueChange={setRegionName}>
                      <SelectTrigger id="manual-region" className="input-vault h-12 rounded-xl text-right">
                        <SelectValue placeholder="واحد سازمانی را انتخاب کنید" />
                      </SelectTrigger>
                      <SelectContent>
                        {AUTHORIZED_REGIONS.map((region) => (
                          <SelectItem key={region} value={region}>
                            {region}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="hidden md:block"></div>

                  <div className="space-y-3 text-right">
                    <label className="px-1 text-sm font-semibold text-[var(--vault-on-surface-variant)]" htmlFor="manual-year">
                      سال
                    </label>
                    <Input
                      id="manual-year"
                      type="text"
                      value={year}
                      onChange={(event) => setYear(normalizeNumericInput(event.target.value))}
                      className="input-vault h-12 rounded-xl text-right"
                      placeholder="1403"
                    />
                  </div>

                  <div className="space-y-3 text-right">
                    <label className="px-1 text-sm font-semibold text-[var(--vault-on-surface-variant)]" htmlFor="manual-month">
                      ماه
                    </label>
                    <Input
                      id="manual-month"
                      type="text"
                      value={month}
                      onChange={(event) => setMonth(normalizeNumericInput(event.target.value))}
                      className="input-vault h-12 rounded-xl text-right"
                      placeholder="1"
                    />
                  </div>

                  <div className="space-y-3 text-right md:col-span-2">
                    <label className="px-1 text-sm font-semibold text-[var(--vault-on-surface-variant)]" htmlFor="manual-amount">
                      مبلغ کل درخواستی (ریال)
                    </label>
                    <Input
                      id="manual-amount"
                      type="text"
                      value={formattedDeclaredTotal}
                      onChange={(event) => setDeclaredTotalAmount(event.target.value)}
                      className="input-vault h-12 rounded-xl text-right"
                      placeholder="مثال: ۱۰۰,۰۰۰,۰۰۰"
                    />
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-bold text-[var(--vault-on-surface)]">جدول ورود اطلاعات</h3>
                    <Button
                      type="button"
                      onClick={addRow}
                      className="h-10 gap-2 rounded-xl bg-blue-600 text-white hover:bg-blue-700"
                    >
                      <Plus className="h-4 w-4" />
                      افزودن ردیف جدید
                    </Button>
                  </div>

                  <div className="overflow-x-auto rounded-xl border border-[var(--vault-surface-highest)] bg-[var(--vault-surface)]">
                    <table className="w-full text-sm">
                      <thead className="bg-[var(--vault-surface-highest)] text-[var(--vault-on-surface)]">
                        <tr>
                          <th className="px-3 py-3 text-center font-semibold">عملیات</th>
                          <th className="px-3 py-3 text-right font-semibold">جمع</th>
                          <th className="px-3 py-3 text-right font-semibold">فی</th>
                          <th className="px-3 py-3 text-right font-semibold">متراژ</th>
                          <th className="px-3 py-3 text-right font-semibold">عنوان</th>
                          <th className="px-3 py-3 text-right font-semibold">مرکز هزینه</th>
                          <th className="px-3 py-3 text-center font-semibold">ردیف</th>
                        </tr>
                      </thead>
                      <tbody>
                        {manualRows.map((row, index) => (
                          <tr key={index} className="border-t border-[var(--vault-surface-highest)]">
                            <td className="px-3 py-2">
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => deleteRow(index)}
                                className="h-8 w-8 p-0 text-rose-400 hover:bg-rose-500/10 hover:text-rose-300"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </td>
                            <td className="px-3 py-2">
                              <Input
                                value={row['جمع']}
                                onChange={(e) => updateCell(index, 'جمع', e.target.value)}
                                className="h-9 rounded-lg border border-[var(--vault-surface-highest)] text-right"
                                placeholder="0"
                              />
                            </td>
                            <td className="px-3 py-2">
                              <Input
                                value={row['فی']}
                                onChange={(e) => updateCell(index, 'فی', e.target.value)}
                                className="h-9 rounded-lg border border-[var(--vault-surface-highest)] text-right"
                                placeholder="0"
                              />
                            </td>
                            <td className="px-3 py-2">
                              <Input
                                value={row['متراژ']}
                                onChange={(e) => updateCell(index, 'متراژ', e.target.value)}
                                className="h-9 rounded-lg border border-[var(--vault-surface-highest)] text-right"
                                placeholder="0"
                              />
                            </td>
                            <td className="px-3 py-2">
                              <Input
                                value={row['عنوان']}
                                onChange={(e) => updateCell(index, 'عنوان', e.target.value)}
                                className={cn(
                                  'h-9 rounded-lg border text-right',
                                  validationErrors.has(`${index}-عنوان`) ? 'border-rose-500 bg-rose-500/10' : 'border-[var(--vault-surface-highest)]'
                                )}
                                placeholder="حجم"
                              />
                            </td>
                            <td className="px-3 py-2">
                              <Input
                                value={row['مرکز هزینه']}
                                onChange={(e) => updateCell(index, 'مرکز هزینه', e.target.value)}
                                className={cn(
                                  'h-9 rounded-lg border text-right',
                                  validationErrors.has(`${index}-مرکز هزینه`) ? 'border-rose-500 bg-rose-500/10' : 'border-[var(--vault-surface-highest)]'
                                )}
                                placeholder="منطقه 1"
                              />
                            </td>
                            <td className="px-3 py-2 text-center text-[var(--vault-on-surface-variant)] font-medium">{row['ردیف']}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="flex gap-4 justify-center pt-4">
                  <Button
                    type="button"
                    onClick={handleDownloadExcel}
                    disabled={isSubmitting}
                    className="h-14 min-w-[180px] rounded-2xl text-lg font-bold bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-lg hover:scale-[1.02] active:scale-95"
                  >
                    <Download className="ml-2 h-5 w-5" />
                    دانلود فایل اکسل
                  </Button>

                  <Button
                    type="button"
                    onClick={() => void handleManualSubmit()}
                    disabled={!canManualSubmit}
                    className="h-14 min-w-[200px] rounded-2xl text-lg font-bold bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg hover:scale-[1.02] active:scale-95"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="ml-2 h-5 w-5 animate-spin" />
                        در حال ارسال...
                      </>
                    ) : (
                      <>
                        <Send className="ml-2 h-5 w-5" />
                        ثبت و ارسال به مدیر سیستم
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
