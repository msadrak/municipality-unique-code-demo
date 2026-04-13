import React, { useState } from 'react';
import { AlertCircle, FileSpreadsheet, Loader2, UploadCloud } from 'lucide-react';
import { toast } from 'sonner';

import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { uploadAttendanceSheet } from '../../services/attendance';
import { cn } from '../../components/ui/utils';

export default function RegionalAttendanceUpload() {
  const [title, setTitle] = useState('');
  const [year, setYear] = useState('1403');
  const [month, setMonth] = useState('1');
  const [regionName, setRegionName] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!title.trim() || !year || !month || !regionName.trim()) {
      setError('تمامی فیلدها الزامی هستند.');
      return;
    }

    if (!file) {
      setError('فایل اکسل را انتخاب کنید.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const sheet = await uploadAttendanceSheet({
        file,
        title: title.trim(),
        year: parseInt(year, 10),
        month: parseInt(month, 10),
        region_name: regionName.trim(),
      });
      toast.success('فایل کارکرد با موفقیت بارگذاری شد.');
      toast.message(`شیت ${sheet.title} با ${sheet.row_count} ردیف ثبت شد.`);
      setTitle('');
      setYear('1403');
      setMonth('1');
      setRegionName('');
      setFile(null);
      const fileInput = document.getElementById('attendance-file') as HTMLInputElement | null;
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

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-8 py-8 animate-fade-in-up">
      <div className="flex flex-col items-center justify-center gap-4 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-emerald-500/10 text-emerald-400 glass-vault shadow-[0_0_20px_rgba(78,222,163,0.1)]">
          <UploadCloud className="h-8 w-8" />
        </div>
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight text-[var(--vault-on-surface)]">آپلود ریز کارکرد پرسنل</h1>
          <p className="text-lg text-[var(--vault-on-surface-variant)]">
            بارگذاری فایل ۱۸ ستونی ویژه مناطق و نواحی (The Emerald Day)
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
                <label className="text-sm font-semibold text-[var(--vault-on-surface-variant)] px-1" htmlFor="attendance-title">
                  عنوان شیت
                </label>
                <Input
                  id="attendance-title"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="مثلاً کارکرد فروردین"
                  className="input-vault h-12 rounded-xl"
                />
              </div>

              <div className="space-y-3 text-right">
                <label className="text-sm font-semibold text-[var(--vault-on-surface-variant)] px-1" htmlFor="attendance-region">
                  نام منطقه
                </label>
                <Input
                  id="attendance-region"
                  value={regionName}
                  onChange={(event) => setRegionName(event.target.value)}
                  placeholder="مثلاً منطقه ۵"
                  className="input-vault h-12 rounded-xl"
                />
              </div>

              <div className="space-y-3 text-right">
                <label className="text-sm font-semibold text-[var(--vault-on-surface-variant)] px-1" htmlFor="attendance-year">
                  سال
                </label>
                <Input
                  id="attendance-year"
                  type="number"
                  value={year}
                  onChange={(event) => setYear(event.target.value)}
                  placeholder="مثلاً ۱۴۰۳"
                  className="input-vault h-12 rounded-xl"
                />
              </div>

              <div className="space-y-3 text-right">
                <label className="text-sm font-semibold text-[var(--vault-on-surface-variant)] px-1" htmlFor="attendance-month">
                  ماه
                </label>
                <Input
                  id="attendance-month"
                  type="number"
                  value={month}
                  onChange={(event) => setMonth(event.target.value)}
                  placeholder="مثلاً ۱"
                  min={1}
                  max={12}
                  className="input-vault h-12 rounded-xl"
                />
              </div>
            </div>

            <div className="space-y-3 text-right">
              <label className="text-sm font-semibold text-[var(--vault-on-surface-variant)] px-1">
                فایل اکسل (۱۸ ستونی)
              </label>
              <label
                htmlFor="attendance-file"
                className={cn(
                  "group relative flex min-h-[12rem] cursor-pointer flex-col items-center justify-center gap-4 rounded-3xl border-2 border-dashed border-[var(--vault-surface-highest)] bg-[var(--vault-surface-highest)]/30 px-6 py-10 text-center transition-all duration-300",
                  "hover:border-[var(--vault-secondary)]/30 hover:bg-[var(--vault-secondary)]/5 hover:shadow-[0_0_40px_rgba(78,222,163,0.05)]",
                  file && "border-[var(--vault-secondary)]/40 bg-[var(--vault-secondary)]/5"
                )}
              >
                <div className={cn(
                  "flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--vault-surface-highest)] text-[var(--vault-secondary)] shadow-sm transition-transform duration-300 group-hover:scale-110",
                  file && "bg-[var(--vault-secondary)]/10"
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
                id="attendance-file"
                type="file"
                accept=".xlsx,.xls"
                className="hidden"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            </div>

            <div className="flex justify-center pt-4">
              <Button type="submit" disabled={isSubmitting} className="btn-premium h-14 min-w-[200px] rounded-2xl text-lg">
                {isSubmitting ? (
                  <>
                    <Loader2 className="ml-2 h-5 w-5 animate-spin" />
                    در حال پردازش...
                  </>
                ) : (
                  'ثبت و پردازش فایل'
                )}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
