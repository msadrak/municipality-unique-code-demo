import React, { DragEvent, useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import {
  AlertCircle,
  CheckCircle2,
  FileSpreadsheet,
  FileText,
  Paperclip,
  UploadCloud,
  X,
} from 'lucide-react';
import { toast } from 'sonner';

import { Alert, AlertDescription } from '../ui/alert';
import { Button } from '../ui/button';
import { Checkbox } from '../ui/checkbox';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '../ui/form';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import {
  calculateVolumeContractStatement,
  submitVolumeContractCalculation,
  submitVolumeContractDocument,
  uploadVolumeContractAttachment,
  VolumeContractCalculation,
  VolumeContractUploadResponse,
} from '../../services/volumeContracts';
import { formatRialCurrency } from '../../config/volumeContractWorkflow';

interface VolumeContractFormRendererProps {
  projectId: string | number;
  documentType: string;
  formSchema?: any;
  assignedRole?: string | null;
  currentUserRole?: string | null;
  onSuccess: () => void;
}

type FormValues = Record<string, any>;
type UploadBucket = 'statement' | 'excel18' | 'excel6' | 'generic';

const STATEMENT_UPLOAD_TYPES = new Set([
  'APPENDIX_5_TIMESHEET',
  'MONTHLY_TIMESHEET',
  'CONTRACTOR_STATEMENT_UPLOAD',
]);

const EXCEL_ACCEPT = '.xls,.xlsx,.xlsm,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
const STATEMENT_ACCEPT = `${EXCEL_ACCEPT},.pdf,.doc,.docx,.jpg,.jpeg,.png,image/*,application/pdf`;

function isExcelFile(file: File) {
  const name = file.name.toLowerCase();
  return name.endsWith('.xls') || name.endsWith('.xlsx') || name.endsWith('.xlsm');
}

function toAttachment(item: VolumeContractUploadResponse, uploadCategory: UploadBucket) {
  return {
    file_name: item.file_name,
    file_url: item.file_url,
    content_type: item.content_type,
    size: item.size,
    upload_category: uploadCategory,
  };
}

export function VolumeContractFormRenderer({
  projectId,
  documentType,
  formSchema,
  assignedRole,
  currentUserRole,
  onSuccess,
}: VolumeContractFormRendererProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDragging, setIsDragging] = useState<UploadBucket | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [statementFiles, setStatementFiles] = useState<File[]>([]);
  const [excel18Files, setExcel18Files] = useState<File[]>([]);
  const [excel6Files, setExcel6Files] = useState<File[]>([]);
  const [calculation, setCalculation] = useState<VolumeContractCalculation | null>(null);
  const [isLoadingCalculation, setIsLoadingCalculation] = useState(false);

  const form = useForm<FormValues>();
  const normalizedAssignedRole = assignedRole?.trim().toUpperCase();
  const normalizedCurrentUserRole = currentUserRole?.trim().toUpperCase();
  const canExecuteStep =
    !normalizedAssignedRole ||
    normalizedCurrentUserRole === 'ADMIN' ||
    normalizedCurrentUserRole === normalizedAssignedRole;

  const isStatementUploadStep = STATEMENT_UPLOAD_TYPES.has(documentType);
  const isAutoCalculationStep = documentType === 'AUTO_STATEMENT_CALCULATION';

  useEffect(() => {
    if (isAutoCalculationStep && canExecuteStep) {
      setIsLoadingCalculation(true);
      calculateVolumeContractStatement(projectId)
        .then(setCalculation)
        .catch((error) => {
          console.error('Failed to load statement matrix preview:', error);
          toast.error('خطا در بارگذاری ماتریس مالی صورت‌وضعیت');
        })
        .finally(() => setIsLoadingCalculation(false));
    }
  }, [isAutoCalculationStep, canExecuteStep, projectId]);

  const appendGenericFiles = (selectedFiles: FileList | File[]) => {
    const nextFiles = Array.from(selectedFiles);
    if (nextFiles.length) setFiles((current) => [...current, ...nextFiles]);
  };

  const appendBucketFiles = (bucket: UploadBucket, selectedFiles: FileList | File[]) => {
    const nextFiles = Array.from(selectedFiles);
    if (!nextFiles.length) return;
    const setter =
      bucket === 'statement'
        ? setStatementFiles
        : bucket === 'excel18'
          ? setExcel18Files
          : setExcel6Files;
    setter((current) => [...current, ...nextFiles]);
  };

  const removeBucketFile = (bucket: UploadBucket, index: number) => {
    const setter =
      bucket === 'statement'
        ? setStatementFiles
        : bucket === 'excel18'
          ? setExcel18Files
          : setExcel6Files;
    setter((current) => current.filter((_, itemIndex) => itemIndex !== index));
  };

  const uploadFiles = async (items: File[], category: UploadBucket) => {
    const uploaded: ReturnType<typeof toAttachment>[] = [];
    for (const file of items) {
      uploaded.push(toAttachment(await uploadVolumeContractAttachment(file), category));
    }
    return uploaded;
  };

  const handleGenericDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(null);
    appendGenericFiles(event.dataTransfer.files);
  };

  const handleBucketDrop = (bucket: UploadBucket, event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(null);
    appendBucketFiles(bucket, event.dataTransfer.files);
  };

  const onSubmit = async (data: FormValues) => {
    if (isStatementUploadStep) {
      if (!statementFiles.length || !excel18Files.length || !excel6Files.length) {
        toast.error('بارگذاری صورت‌وضعیت، فایل ۱۸ ستونی و فایل ۶ ستونی الزامی است');
        return;
      }
      if (![...excel18Files, ...excel6Files].every(isExcelFile)) {
        toast.error('فایل‌های ۱۸ ستونی و ۶ ستونی باید Excel باشند');
        return;
      }
    }

    try {
      setIsSubmitting(true);

      if (isStatementUploadStep) {
        const statementUploads = await uploadFiles(statementFiles, 'statement');
        const excel18Uploads = await uploadFiles(excel18Files, 'excel18');
        const excel6Uploads = await uploadFiles(excel6Files, 'excel6');
        const allUploads = [...statementUploads, ...excel18Uploads, ...excel6Uploads];

        await submitVolumeContractDocument(projectId, documentType, {
          ...data,
          statement_file: statementUploads[0],
          statement_files: statementUploads,
          attendance_18_column_file: excel18Uploads[0],
          attendance_18_column_files: excel18Uploads,
          statement_6_column_file: excel6Uploads[0],
          statement_6_column_files: excel6Uploads,
          _attachments: allUploads,
        });

        toast.success('صورت‌وضعیت و فایل‌های Excel برای بررسی آقای بهادری ارسال شد');
        setStatementFiles([]);
        setExcel18Files([]);
        setExcel6Files([]);
        onSuccess();
        return;
      }

      const uploadedFiles: VolumeContractUploadResponse[] = [];
      for (const file of files) {
        uploadedFiles.push(await uploadVolumeContractAttachment(file));
      }
      await submitVolumeContractDocument(projectId, documentType, {
        ...data,
        _attachments: uploadedFiles.map((item) => toAttachment(item, 'generic')),
      });
      toast.success('اطلاعات مرحله با موفقیت ثبت شد');
      setFiles([]);
      onSuccess();
    } catch (error) {
      console.error('Submit volume contract document error:', error);
      toast.error('خطا در ثبت اطلاعات یا بارگذاری پیوست‌ها');
    } finally {
      setIsSubmitting(false);
    }
  };

  // ── CRITICAL GUARD: APPENDIX_5_TIMESHEET must ALWAYS render the file upload UI.
  // This fires before canExecuteStep / schema fallback, making it impossible
  // for stale cache or old schema data to render numeric inputs.
  if (documentType === 'APPENDIX_5_TIMESHEET' || documentType === 'MONTHLY_TIMESHEET' || documentType === 'CONTRACTOR_STATEMENT_UPLOAD') {
    if (!canExecuteStep) {
      return (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            این مرحله در اختیار نقش {assignedRole} است و کارتابل شما امکان اقدام مستقیم در آن را ندارد.
          </AlertDescription>
        </Alert>
      );
    }
    return <StatementUploadForm />;
  }

  if (!canExecuteStep) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          این مرحله در اختیار نقش {assignedRole} است و کارتابل شما امکان اقدام مستقیم در آن را ندارد.
        </AlertDescription>
      </Alert>
    );
  }

  const UploadBucketCard = ({
    bucket,
    title,
    description,
    accept,
    bucketFiles,
    icon,
  }: {
    bucket: UploadBucket;
    title: string;
    description: string;
    accept: string;
    bucketFiles: File[];
    icon: React.ReactNode;
  }) => {
    const inputId = `${documentType}-${bucket}-upload`;
    return (
      <section className="rounded-lg border border-dashed border-slate-300 bg-white p-4 shadow-sm">
        <div className="mb-3 flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-[#e8f7fb] text-[#04697a]">
            {icon}
          </div>
          <div>
            <h4 className="text-sm font-black text-slate-800">{title}</h4>
            <p className="mt-1 text-xs leading-6 text-slate-500">{description}</p>
          </div>
        </div>
        <label
          htmlFor={inputId}
          onDrop={(event) => handleBucketDrop(bucket, event)}
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(bucket);
          }}
          onDragLeave={() => setIsDragging(null)}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed p-5 text-center transition ${
            isDragging === bucket ? 'border-[#04697a] bg-[#e8f7fb]' : 'border-slate-300 bg-slate-50 hover:bg-slate-100'
          }`}
        >
          <UploadCloud className="mb-2 h-7 w-7 text-slate-400" />
          <span className="text-sm font-bold text-slate-700">انتخاب فایل یا رها کردن در این بخش</span>
          <span className="mt-1 text-xs text-slate-500">چند فایل هم قابل بارگذاری است.</span>
          <input
            id={inputId}
            type="file"
            multiple
            accept={accept}
            className="hidden"
            onChange={(event) => {
              if (event.target.files) appendBucketFiles(bucket, event.target.files);
              event.currentTarget.value = '';
            }}
          />
        </label>
        {bucketFiles.length > 0 ? (
          <div className="mt-3 space-y-2">
            {bucketFiles.map((file, index) => (
              <div key={`${bucket}-${file.name}-${index}`} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm">
                <div className="min-w-0">
                  <div className="truncate font-bold text-slate-700">{file.name}</div>
                  <div className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB</div>
                </div>
                <Button type="button" variant="ghost" size="icon" onClick={() => removeBucketFile(bucket, index)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        ) : null}
      </section>
    );
  };

  const StatementUploadForm = () => (
    <Card>
      <CardHeader>
        <CardTitle>بارگذاری صورت‌وضعیت پیمانکار</CardTitle>
        <CardDescription>
          فایل صورت‌وضعیت رسمی، فایل ۱۸ ستونی و فایل ۶ ستونی Excel پس از ثبت به کارتابل آقای بهادری ارسال می‌شود.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <FormField
                control={form.control}
                name="statement_number"
                rules={{ required: 'شماره صورت‌وضعیت الزامی است' }}
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>شماره صورت‌وضعیت <span className="mr-1 text-red-500">*</span></FormLabel>
                    <FormControl><Input placeholder="مثال: 1405/02-01" {...field} value={field.value || ''} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="work_period"
                rules={{ required: 'دوره کارکرد الزامی است' }}
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>دوره کارکرد <span className="mr-1 text-red-500">*</span></FormLabel>
                    <FormControl><Input placeholder="مثال: اردیبهشت ۱۴۰۵" {...field} value={field.value || ''} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <UploadBucketCard
                bucket="statement"
                title="صورت وضعیت تایید شده"
                description="نسخه رسمی امضا شده (PDF یا تصویر) — فرمت‌های PDF و JPG/PNG پذیرفته می‌شوند."
                accept={STATEMENT_ACCEPT}
                bucketFiles={statementFiles}
                icon={<FileText className="h-5 w-5" />}
              />
              <UploadBucketCard
                bucket="excel18"
                title="فایل اکسل ۱۸ ستونی حقوق"
                description="فایل Excel استاندارد ۱۸ ستونی برای احراز کارکرد و حقوق — فقط .xlsx / .xls"
                accept={EXCEL_ACCEPT}
                bucketFiles={excel18Files}
                icon={<FileSpreadsheet className="h-5 w-5" />}
              />
              <UploadBucketCard
                bucket="excel6"
                title="فایل اکسل ۶ ستونی بیمه"
                description="فایل Excel استاندارد ۶ ستونی لیست بیمه سازمان تأمین اجتماعی — فقط .xlsx / .xls"
                accept={EXCEL_ACCEPT}
                bucketFiles={excel6Files}
                icon={<FileSpreadsheet className="h-5 w-5" />}
              />
            </div>

            <div className="rounded-lg border border-[#cbe7f5] bg-[#e8f7fb] p-4 text-sm font-medium leading-7 text-[#005867]">
              پس از تایید آقای بهادری، همین بسته اسنادی به ردیف‌های جداگانه ماتریس مالی تبدیل می‌شود و برای هر ردیف کد یکتای مستقل صادر خواهد شد.
            </div>

            <div className="flex justify-end">
              <Button type="submit" disabled={isSubmitting} className="min-w-48">
                {isSubmitting ? 'در حال بارگذاری...' : 'ارسال برای بررسی بهادری'}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );

  const AutoCalculationSummary = () => {
    const handleSubmitCalculation = async () => {
      try {
        setIsSubmitting(true);
        await submitVolumeContractCalculation(projectId);
        toast.success('خلاصه ماتریس مالی صورت‌وضعیت ثبت شد');
        onSuccess();
      } catch (error) {
        console.error('Submit calculation error:', error);
        toast.error('خطا در ثبت خلاصه ماتریس مالی');
      } finally {
        setIsSubmitting(false);
      }
    };

    if (!calculation) {
      return (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">
              {isLoadingCalculation ? 'در حال بارگذاری ماتریس مالی...' : 'ماتریس مالی در دسترس نیست'}
            </p>
          </CardContent>
        </Card>
      );
    }

    return (
      <div className="space-y-5">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="rounded-lg border bg-slate-50 p-4">
            <div className="text-xs font-bold text-slate-500">شماره صورت‌وضعیت</div>
            <div className="mt-1 font-black text-slate-900">{calculation.statement_number || '—'}</div>
          </div>
          <div className="rounded-lg border bg-slate-50 p-4">
            <div className="text-xs font-bold text-slate-500">دوره کارکرد</div>
            <div className="mt-1 font-black text-slate-900">{calculation.work_period || '—'}</div>
          </div>
          <div className="rounded-lg border bg-slate-50 p-4">
            <div className="text-xs font-bold text-slate-500">مبلغ ناخالص مستخرج</div>
            <div className="mt-1 font-black text-[#04697a]">{formatRialCurrency(calculation.gross_amount)}</div>
          </div>
        </div>

        <div className="overflow-hidden rounded-lg border bg-white">
          <div className="overflow-x-auto">
            <table className="w-full text-right text-sm">
              <thead className="bg-slate-50 text-xs font-bold text-slate-500">
                <tr>
                  <th className="whitespace-nowrap p-4">ردیف</th>
                  <th className="whitespace-nowrap p-4">رویداد مالی</th>
                  <th className="whitespace-nowrap p-4">مبلغ</th>
                  <th className="whitespace-nowrap p-4">کد یکتا</th>
                  <th className="whitespace-nowrap p-4">وضعیت صف</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {calculation.financial_events.map((event) => (
                  <tr key={event.event_code} className="hover:bg-slate-50">
                    <td className="p-4 font-mono text-slate-500">{event.event_sequence}</td>
                    <td className="p-4">
                      <div className="font-black text-slate-800">{event.event_label}</div>
                      <div className="mt-1 font-mono text-xs text-slate-500">{event.event_code}</div>
                    </td>
                    <td className="p-4 font-black text-[#04697a]">{formatRialCurrency(event.amount)}</td>
                    <td className="p-4 font-mono text-xs font-bold text-slate-700" dir="ltr">
                      {event.yekta_code || 'در انتظار تایید'}
                    </td>
                    <td className="p-4">
                      {event.payment_queue_status === 'READY_FOR_PAYMENT_QUEUE' ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          آماده پرداخت
                        </span>
                      ) : (
                        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-500">پیش‌نمایش</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="flex justify-end">
          <Button onClick={handleSubmitCalculation} disabled={isSubmitting} className="min-w-48">
            {isSubmitting ? 'در حال ثبت...' : 'ثبت خلاصه ماتریس مالی'}
          </Button>
        </div>
      </div>
    );
  };

  const AttachmentSection = () => (
    <section className="space-y-3 rounded-lg border border-dashed border-slate-300 bg-slate-50/70 p-4">
      <div className="flex items-center gap-2">
        <Paperclip className="h-4 w-4 text-[#04697a]" />
        <div>
          <h4 className="text-sm font-bold">پیوست‌ها</h4>
          <p className="text-xs text-muted-foreground">مستندات پشتیبان این مرحله را بارگذاری کنید.</p>
        </div>
      </div>
      <div
        role="button"
        tabIndex={0}
        onClick={() => document.getElementById(`${documentType}-generic-upload`)?.click()}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            document.getElementById(`${documentType}-generic-upload`)?.click();
          }
        }}
        onDrop={handleGenericDrop}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging('generic');
        }}
        onDragLeave={() => setIsDragging(null)}
        className={`rounded-lg border border-dashed p-6 text-center transition ${
          isDragging === 'generic' ? 'border-[#04697a] bg-[#e8f7fb]' : 'border-slate-300 bg-white hover:bg-slate-50'
        }`}
      >
        <UploadCloud className="mx-auto mb-3 h-8 w-8 text-slate-400" />
        <p className="text-sm font-medium text-slate-700">فایل‌ها را اینجا رها کنید یا برای انتخاب کلیک کنید</p>
        <input
          id={`${documentType}-generic-upload`}
          type="file"
          multiple
          className="hidden"
          onChange={(event) => {
            if (event.target.files) appendGenericFiles(event.target.files);
            event.currentTarget.value = '';
          }}
        />
      </div>
      {files.length > 0 ? (
        <div className="space-y-2">
          {files.map((file, index) => (
            <div key={`${file.name}-${index}`} className="flex items-center justify-between rounded-md bg-white px-3 py-2 text-sm shadow-sm">
              <div className="truncate font-medium text-slate-700">{file.name}</div>
              <Button type="button" variant="ghost" size="icon" onClick={() => setFiles((current) => current.filter((_, itemIndex) => itemIndex !== index))}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );

  if (isStatementUploadStep) return <StatementUploadForm />;

  if (isAutoCalculationStep) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>ماتریس مالی چندرویدادی صورت‌وضعیت</CardTitle>
          <CardDescription>
            هر ردیف مالی مستقل، کد یکتای مستقل و وضعیت آماده‌سازی برای صف پرداخت دارد.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AutoCalculationSummary />
        </CardContent>
      </Card>
    );
  }

  if (!formSchema || !formSchema.properties) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>فرم این مرحله هنوز آماده نشده است</CardTitle>
          <CardDescription>ساختار فرم {documentType} در سامانه تعریف نشده است.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const properties = Object.entries(formSchema.properties as Record<string, any>);
  const requiredFields: string[] = formSchema.required ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>{formSchema.title || `فرم ${documentType}`}</CardTitle>
        <CardDescription>
          {formSchema.description || 'لطفا اطلاعات مرحله جاری قرارداد حجمی را با دقت تکمیل کنید.'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {properties.map(([fieldName, fieldSchema]) => {
                const isRequired = requiredFields.includes(fieldName);
                const isTextarea = fieldSchema.widget === 'textarea';
                const isBoolean = fieldSchema.type === 'boolean';
                const isNumber = fieldSchema.type === 'number' || fieldSchema.type === 'integer';
                const isReadOnly = Boolean(fieldSchema.readOnly);
                const inputType = fieldSchema.format === 'date' ? 'date' : isNumber ? 'number' : 'text';
                return (
                  <FormField
                    key={fieldName}
                    control={form.control}
                    name={fieldName}
                    rules={{ required: isRequired ? 'این فیلد الزامی است' : false }}
                    render={({ field }) => (
                      <FormItem className={isTextarea || isBoolean ? 'md:col-span-2' : ''}>
                        <FormLabel>
                          {fieldSchema.title || fieldName}
                          {isRequired && <span className="mr-1 text-red-500">*</span>}
                        </FormLabel>
                        <FormControl>
                          {isBoolean ? (
                            <label className="flex min-h-12 cursor-pointer items-center gap-3 rounded-md border border-slate-200 bg-slate-50 px-4 py-3">
                              <Checkbox checked={Boolean(field.value)} onCheckedChange={(checked) => field.onChange(Boolean(checked))} disabled={isReadOnly} />
                              <span className="text-sm font-medium text-slate-700">{fieldSchema.description || 'تایید می‌کنم'}</span>
                            </label>
                          ) : isTextarea ? (
                            <Textarea placeholder={fieldSchema.placeholder || ''} {...field} value={field.value || ''} readOnly={isReadOnly} disabled={isReadOnly} />
                          ) : (
                            <Input
                              type={inputType}
                              placeholder={fieldSchema.placeholder || ''}
                              {...field}
                              value={field.value ?? ''}
                              readOnly={isReadOnly}
                              disabled={isReadOnly}
                              step={isNumber ? 'any' : undefined}
                              onChange={(event) => {
                                const nextValue = event.target.value;
                                field.onChange(isNumber ? (nextValue === '' ? undefined : Number(nextValue)) : nextValue);
                              }}
                            />
                          )}
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                );
              })}
            </div>
            <AttachmentSection />
            <div className="flex justify-end">
              <Button type="submit" disabled={isSubmitting} className="min-w-40">
                {isSubmitting ? 'در حال ثبت...' : 'ثبت اطلاعات مرحله'}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

export default VolumeContractFormRenderer;
