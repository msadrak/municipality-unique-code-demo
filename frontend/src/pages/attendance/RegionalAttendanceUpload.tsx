import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  FileImage,
  FileSpreadsheet,
  FileText,
  Loader2,
  Paperclip,
  UploadCloud,
  X,
} from 'lucide-react';
import { toast } from 'sonner';

import { AUTHORIZED_REGIONS } from '../../constants/regions';
import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { uploadAttendanceSheet, uploadSheetAttachments } from '../../services/attendance';
import { useAuthStore } from '../../stores/useAuthStore';
import { cn } from '../../components/ui/utils';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const ALLOWED_ATTACHMENT_TYPES = ['application/pdf', 'image/jpeg', 'image/png'];
const ALLOWED_ATTACHMENT_EXTS = '.pdf,.jpg,.jpeg,.png';

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function AttachmentIcon({ mimeType }: { mimeType: string }) {
  if (mimeType === 'application/pdf') {
    return <FileText className="h-5 w-5 text-rose-400" />;
  }
  return <FileImage className="h-5 w-5 text-sky-400" />;
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function RegionalAttendanceUpload() {
  const user = useAuthStore((state) => state.user);

  // ── Excel state ─────────────────────────────────────────────────────────
  const [title, setTitle] = useState('');
  const [year, setYear] = useState('1403');
  const [month, setMonth] = useState('1');
  const [regionName, setRegionName] = useState('');
  const [file, setFile] = useState<File | null>(null);

  // ── Attachment state ─────────────────────────────────────────────────────
  const [attachments, setAttachments] = useState<File[]>([]);
  const [isDraggingAttachment, setIsDraggingAttachment] = useState(false);
  const attachmentInputRef = useRef<HTMLInputElement>(null);

  // ── UI state ─────────────────────────────────────────────────────────────
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isRegionLocked = useMemo(
    () => (user?.role || '').toUpperCase() === 'REGION_USER' && Boolean(user?.region_name),
    [user?.region_name, user?.role],
  );

  useEffect(() => {
    if (isRegionLocked && user?.region_name) {
      setRegionName(user.region_name);
    }
  }, [isRegionLocked, user?.region_name]);

  // ── Attachment drag handlers ─────────────────────────────────────────────
  const addAttachmentFiles = useCallback((incoming: FileList | File[]) => {
    const arr = Array.from(incoming);
    const valid = arr.filter((f) => ALLOWED_ATTACHMENT_TYPES.includes(f.type));
    const invalid = arr.filter((f) => !ALLOWED_ATTACHMENT_TYPES.includes(f.type));
    if (invalid.length) {
      toast.warning(`${invalid.length} فایل رد شد (فقط PDF، JPG و PNG مجاز است).`);
    }
    if (valid.length) {
      setAttachments((prev) => [...prev, ...valid]);
    }
  }, []);

  const handleAttachmentDrop = useCallback(
    (e: React.DragEvent<HTMLLabelElement>) => {
      e.preventDefault();
      setIsDraggingAttachment(false);
      addAttachmentFiles(e.dataTransfer.files);
    },
    [addAttachmentFiles],
  );

  const removeAttachment = (index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  };

  // ── Form submit ──────────────────────────────────────────────────────────
  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!title.trim() || !year || !month || !regionName) {
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
      // ── Step 1: upload Excel ─────────────────────────────────────────────
      const sheet = await uploadAttendanceSheet({
        file,
        title: title.trim(),
        year: parseInt(year, 10),
        month: parseInt(month, 10),
        region_name: regionName,
      });

      toast.success('فایل کارکرد با موفقیت بارگذاری شد.');
      toast.message(`شیت ${sheet.title} با ${sheet.row_count} ردیف ثبت شد.`);

      // ── Step 2: upload attachments (non-fatal) ───────────────────────────
      if (attachments.length > 0) {
        try {
          await uploadSheetAttachments(sheet.id, attachments);
          toast.success(`${attachments.length} پیوست با موفقیت بارگذاری شد.`);
        } catch {
          toast.warning('فایل اکسل ثبت شد، اما بارگذاری پیوست‌ها ناموفق بود. لطفاً بعداً دوباره امتحان کنید.');
        }
      }

      // ── Reset ────────────────────────────────────────────────────────────
      setTitle('');
      setYear('1403');
      setMonth('1');
      setRegionName(isRegionLocked ? user?.region_name || '' : '');
      setFile(null);
      setAttachments([]);
      const fileInput = document.getElementById('attendance-file') as HTMLInputElement | null;
      if (fileInput) fileInput.value = '';
      if (attachmentInputRef.current) attachmentInputRef.current.value = '';
    } catch (err) {
      const message = err instanceof Error ? err.message : 'بارگذاری فایل ناموفق بود.';
      setError(message);
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-8 py-8 animate-fade-in-up">
      {/* Header */}
      <div className="flex flex-col items-center justify-center gap-4 text-center">
        <div className="glass-vault flex h-16 w-16 items-center justify-center rounded-3xl bg-emerald-500/10 text-emerald-400 shadow-[0_0_20px_rgba(78,222,163,0.1)]">
          <UploadCloud className="h-8 w-8" />
        </div>
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight text-[var(--vault-on-surface)]">حفاظت فیزیکی</h1>
          <p className="text-lg text-[var(--vault-on-surface-variant)]">
            بارگذاری ۱۸ ستونی ویژه مناطق/سازمانها/شرکتها
          </p>
        </div>
      </div>

      {/* Card */}
      <div className="glass-vault overflow-hidden rounded-[2rem] border border-[var(--vault-surface-highest)] bg-transparent p-1">
        <div className="rounded-[1.9rem] bg-[var(--vault-surface-low)] p-8 shadow-2xl">
          <form className="space-y-8" onSubmit={handleSubmit}>
            {/* Error */}
            {error ? (
              <Alert className="glass-vault border-rose-500/20 bg-rose-500/5 text-rose-200">
                <AlertCircle className="h-4 w-4 text-rose-400" />
                <AlertTitle>خطا در پردازش فایل</AlertTitle>
                <AlertDescription className="text-rose-300/80">{error}</AlertDescription>
              </Alert>
            ) : null}

            {/* Meta fields */}
            <div className="grid gap-6 md:grid-cols-2">
              <div className="space-y-3 text-right">
                <label className="px-1 text-sm font-semibold text-[var(--vault-on-surface-variant)]" htmlFor="attendance-title">
                  عنوان جدول
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
                <label className="px-1 text-sm font-semibold text-[var(--vault-on-surface-variant)]" htmlFor="attendance-region">
                  نام واحد سازمانی
                </label>
                <Select value={regionName} onValueChange={setRegionName} disabled={isRegionLocked}>
                  <SelectTrigger id="attendance-region" className="input-vault h-12 rounded-xl text-right">
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
                {isRegionLocked ? (
                  <p className="text-xs text-[var(--vault-on-surface-variant)]">
                    این حساب فقط برای منطقه تخصیص‌یافته خودش مجاز به بارگذاری است.
                  </p>
                ) : null}
              </div>

              <div className="space-y-3 text-right">
                <label className="px-1 text-sm font-semibold text-[var(--vault-on-surface-variant)]" htmlFor="attendance-year">
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
                <label className="px-1 text-sm font-semibold text-[var(--vault-on-surface-variant)]" htmlFor="attendance-month">
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

            {/* ── Excel Dropzone ───────────────────────────────────────────── */}
            <div className="space-y-3 text-right">
              <label className="px-1 text-sm font-semibold text-[var(--vault-on-surface-variant)]">
                فایل اکسل (۱۸ ستونی)
              </label>
              <label
                htmlFor="attendance-file"
                className={cn(
                  'group relative flex min-h-[12rem] cursor-pointer flex-col items-center justify-center gap-4 rounded-3xl border-2 border-dashed border-[var(--vault-surface-highest)] bg-[var(--vault-surface-highest)]/30 px-6 py-10 text-center transition-all duration-300',
                  'hover:border-[var(--vault-secondary)]/30 hover:bg-[var(--vault-secondary)]/5 hover:shadow-[0_0_40px_rgba(78,222,163,0.05)]',
                  file && 'border-[var(--vault-secondary)]/40 bg-[var(--vault-secondary)]/5',
                )}
              >
                <div
                  className={cn(
                    'flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--vault-surface-highest)] text-[var(--vault-secondary)] shadow-sm transition-transform duration-300 group-hover:scale-110',
                    file && 'bg-[var(--vault-secondary)]/10',
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
                id="attendance-file"
                type="file"
                accept=".xlsx,.xls"
                className="hidden"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            </div>

            {/* ── Attachment Dropzone ───────────────────────────────────────── */}
            <div className="space-y-4 text-right">
              {/* Section header */}
              <div className="flex items-center justify-end gap-3">
                <div className="space-y-0.5">
                  <p className="px-1 text-sm font-semibold text-[var(--vault-on-surface-variant)]">
                    پیوست‌ها و مستندات (فاکتور)
                  </p>
                  <p className="px-1 text-xs text-[var(--vault-on-surface-variant)]/60">
                    اختیاری — PDF، JPG یا PNG
                  </p>
                </div>
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-500/10 text-amber-400">
                  <Paperclip className="h-5 w-5" />
                </div>
              </div>

              {/* Dropzone label */}
              <label
                htmlFor="attachment-files"
                onDragOver={(e) => { e.preventDefault(); setIsDraggingAttachment(true); }}
                onDragLeave={() => setIsDraggingAttachment(false)}
                onDrop={handleAttachmentDrop}
                className={cn(
                  'group relative flex min-h-[9rem] cursor-pointer flex-col items-center justify-center gap-3 rounded-3xl border-2 border-dashed px-6 py-8 text-center transition-all duration-300',
                  isDraggingAttachment
                    ? 'border-amber-400/60 bg-amber-500/10 shadow-[0_0_30px_rgba(251,191,36,0.1)]'
                    : 'border-[var(--vault-surface-highest)] bg-[var(--vault-surface-highest)]/20 hover:border-amber-400/30 hover:bg-amber-500/5',
                )}
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-500/10 text-amber-400 transition-transform duration-300 group-hover:scale-110">
                  <Paperclip className="h-6 w-6" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium text-[var(--vault-on-surface)]">
                    فایل‌های پیوست را بکشید اینجا یا کلیک کنید
                  </p>
                  <p className="text-xs text-[var(--vault-on-surface-variant)]">
                    PDF، JPG، JPEG، PNG — چندین فایل همزمان مجاز است
                  </p>
                </div>
              </label>
              <input
                ref={attachmentInputRef}
                id="attachment-files"
                type="file"
                accept={ALLOWED_ATTACHMENT_EXTS}
                multiple
                className="hidden"
                onChange={(e) => {
                  if (e.target.files) addAttachmentFiles(e.target.files);
                }}
              />

              {/* Staged attachments list */}
              {attachments.length > 0 && (
                <div className="space-y-2 rounded-2xl border border-[var(--vault-surface-highest)] bg-[var(--vault-surface-highest)]/20 p-3">
                  <p className="px-1 text-xs font-semibold text-[var(--vault-on-surface-variant)]">
                    فایل‌های انتخاب‌شده ({attachments.length})
                  </p>
                  <ul className="space-y-2">
                    {attachments.map((att, idx) => (
                      <li
                        key={`${att.name}-${idx}`}
                        className="flex items-center gap-3 rounded-xl border border-[var(--vault-surface-highest)] bg-[var(--vault-surface-low)] px-3 py-2"
                      >
                        <button
                          type="button"
                          onClick={() => removeAttachment(idx)}
                          className="ml-auto flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 transition-colors"
                          aria-label="حذف"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                        <div className="flex flex-1 flex-col items-end overflow-hidden text-right">
                          <span className="max-w-full truncate text-sm font-medium text-[var(--vault-on-surface)]">
                            {att.name}
                          </span>
                          <span className="text-xs text-[var(--vault-on-surface-variant)]">
                            {formatFileSize(att.size)}
                          </span>
                        </div>
                        <AttachmentIcon mimeType={att.type} />
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Submit */}
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
