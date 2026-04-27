import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  FileSpreadsheet,
  FileText,
  Image as ImageIcon,
  Inbox,
  Loader2,
  Paperclip,
  RefreshCw,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { AttendanceSheet, AttachmentMeta, fetchAttendanceSheets } from '../../services/attendance';

const STATUS_STYLES: Record<string, string> = {
  DRAFT: 'bg-slate-100 text-slate-700',
  CREATOR_APPROVED: 'bg-blue-100 text-blue-700',
  COMPANY_REP_APPROVED: 'bg-violet-100 text-violet-700',
  SECURITY_APPROVED: 'bg-amber-100 text-amber-800',
  GM_APPROVED: 'bg-emerald-100 text-emerald-700',
  NEEDS_CORRECTION: 'bg-orange-100 text-orange-700',
  REJECTED: 'bg-rose-100 text-rose-700',
};

const STATUS_LABELS: Record<string, string> = {
  DRAFT: 'پیش‌نویس',
  CREATOR_APPROVED: 'تایید ثبت‌کننده',
  COMPANY_REP_APPROVED: 'تایید نماینده',
  SECURITY_APPROVED: 'تایید حراست',
  GM_APPROVED: 'تایید نهایی',
  NEEDS_CORRECTION: 'نیازمند اصلاح',
  REJECTED: 'رد شده',
};

function formatDate(value?: string) {
  if (!value) return '-';
  return new Intl.DateTimeFormat('fa-IR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function resolveAttachmentUrl(filePath: string) {
  if (!filePath) return '#';
  if (/^https?:\/\//i.test(filePath)) return filePath;
  return filePath.startsWith('/') ? filePath : `/${filePath}`;
}

function isImageAttachment(attachment: AttachmentMeta) {
  if (attachment.file_type === 'image') return true;

  const imageExtensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.svg'];
  const normalizedFileName = attachment.file_name.toLowerCase();
  const normalizedFilePath = attachment.file_path.toLowerCase();

  return imageExtensions.some(
    (extension) =>
      normalizedFileName.endsWith(extension) || normalizedFilePath.endsWith(extension),
  );
}

function AttachmentIndicator({ attachments }: { attachments: AttachmentMeta[] }) {
  if (!attachments.length) {
    return <span className="text-sm text-slate-400">ندارد</span>;
  }

  return (
    <div className="flex flex-col items-center gap-1">
      <Badge variant="outline" className="border-slate-200 bg-slate-50 text-slate-700">
        {`دارد (${attachments.length} فایل)`}
      </Badge>
      <div className="flex items-center justify-center gap-1 text-slate-400">
        {attachments.slice(0, 3).map((attachment) =>
          isImageAttachment(attachment) ? (
            <ImageIcon key={attachment.id} className="h-3.5 w-3.5" />
          ) : (
            <FileText key={attachment.id} className="h-3.5 w-3.5" />
          ),
        )}
        {attachments.length > 3 ? (
          <span className="text-[11px] font-medium">+{attachments.length - 3}</span>
        ) : null}
      </div>
    </div>
  );
}

export default function AttendanceInbox() {
  const navigate = useNavigate();
  const [sheets, setSheets] = useState<AttendanceSheet[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attachmentSheet, setAttachmentSheet] = useState<AttendanceSheet | null>(null);

  const loadSheets = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchAttendanceSheets();
      setSheets(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'دریافت کارتابل ناموفق بود.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadSheets();
  }, []);

  const handleOpenSheet = (sheetId: number) => {
    navigate(`/attendance/${sheetId}`);
  };

  return (
    <div className="flex flex-col gap-6">
      <Card className="border-slate-200 shadow-sm">
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div className="space-y-1 text-right">
            <CardTitle className="text-xl font-bold text-slate-900">
              کارتابل کارکرد و مستندات مناطق
            </CardTitle>
            <CardDescription>
              همه شیت‌ها و مستندات ضمیمه بارگذاری‌شده را ببینید و برای بررسی جزئیات یا مشاهده اسناد از ستون عملیات استفاده کنید.
            </CardDescription>
          </div>
          <Button variant="outline" onClick={() => void loadSheets()} disabled={isLoading}>
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            به‌روزرسانی
          </Button>
        </CardHeader>

        <CardContent className="space-y-4">
          {error ? (
            <Alert className="border-rose-200 bg-rose-50 text-rose-900">
              <AlertCircle className="h-4 w-4 text-rose-700" />
              <AlertTitle>خطا در دریافت لیست</AlertTitle>
              <AlertDescription className="text-rose-800">{error}</AlertDescription>
            </Alert>
          ) : null}

          <div className="overflow-hidden rounded-2xl border border-slate-200">
            <Table>
              <TableHeader className="bg-slate-100/80">
                <TableRow>
                  <TableHead className="text-center">عنوان</TableHead>
                  <TableHead className="text-center">منطقه</TableHead>
                  <TableHead className="text-center">تعداد ردیف</TableHead>
                  <TableHead className="text-center">پیوست‌ها</TableHead>
                  <TableHead className="text-center">تاریخ بارگذاری</TableHead>
                  <TableHead className="text-center">وضعیت</TableHead>
                  <TableHead className="text-center">عملیات</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={7} className="py-16 text-center text-slate-500">
                      <div className="flex items-center justify-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        در حال بارگذاری اطلاعات...
                      </div>
                    </TableCell>
                  </TableRow>
                ) : sheets.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="py-16 text-center text-slate-500">
                      <div className="flex flex-col items-center justify-center gap-3">
                        <Inbox className="h-8 w-8 text-slate-300" />
                        <span>هیچ فایل کارکردی ثبت نشده است.</span>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  sheets.map((sheet) => (
                    <TableRow key={sheet.id} className="hover:bg-slate-50/80">
                      <TableCell className="text-center font-medium text-slate-900">{sheet.title}</TableCell>
                      <TableCell className="text-center text-slate-600">{sheet.region || '-'}</TableCell>
                      <TableCell className="text-center font-mono">{sheet.row_count}</TableCell>
                      <TableCell className="text-center">
                        <AttachmentIndicator attachments={sheet.attachments ?? []} />
                      </TableCell>
                      <TableCell className="text-center text-sm text-slate-500">
                        {formatDate(sheet.created_at)}
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge
                          className={STATUS_STYLES[sheet.status] || 'bg-slate-100 text-slate-700'}
                          variant="outline"
                        >
                          {STATUS_LABELS[sheet.status] || sheet.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex justify-center gap-2">
                          <Button
                            type="button"
                            size="sm"
                            className="bg-slate-900 text-white hover:bg-slate-800"
                            onClick={() => handleOpenSheet(sheet.id)}
                          >
                            <FileSpreadsheet className="h-4 w-4" />
                            بررسی کارکرد
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            disabled={!sheet.attachments?.length}
                            onClick={() => setAttachmentSheet(sheet)}
                          >
                            <Paperclip className="h-4 w-4" />
                            مستندات
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Dialog open={!!attachmentSheet} onOpenChange={(isOpen) => !isOpen && setAttachmentSheet(null)}>
        <DialogContent className="max-w-2xl border-slate-200 bg-white text-slate-900 rtl">
          <DialogHeader className="text-right">
            <DialogTitle>مستندات ضمیمه</DialogTitle>
            <DialogDescription>
              {attachmentSheet
                ? `فهرست فایل‌های ضمیمه برای «${attachmentSheet.title}»`
                : 'فهرست فایل‌های ضمیمه'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            {attachmentSheet?.attachments?.length ? (
              attachmentSheet.attachments.map((attachment) => {
                const isImage = isImageAttachment(attachment);
                return (
                  <a
                    key={attachment.id}
                    href={resolveAttachmentUrl(attachment.file_path)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-right transition-colors hover:border-slate-300 hover:bg-slate-100"
                  >
                    <span className="text-xs text-slate-400">{formatDate(attachment.created_at)}</span>
                    <div className="flex items-center gap-2 text-sm font-medium text-slate-800">
                      {isImage ? (
                        <ImageIcon className="h-4 w-4 text-sky-600" />
                      ) : (
                        <FileText className="h-4 w-4 text-rose-600" />
                      )}
                      <span>{attachment.file_name}</span>
                    </div>
                  </a>
                );
              })
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-10 text-center text-sm text-slate-500">
                برای این فایل، مستندات ضمیمه‌ای ثبت نشده است.
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
