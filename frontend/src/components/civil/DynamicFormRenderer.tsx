import React, { DragEvent, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { AlertCircle, Paperclip, UploadCloud, X } from 'lucide-react';
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
  CivilUploadResponse,
  submitDocument,
  uploadCivilAttachment,
} from '../../services/civil';

interface DynamicFormRendererProps {
  projectId: string | number;
  documentType: string;
  formSchema?: any;
  assignedRole?: string | null;
  currentUserRole?: string | null;
  onSuccess: () => void;
}

type FormValues = Record<string, any>;

export function DynamicFormRenderer({
  projectId,
  documentType,
  formSchema,
  assignedRole,
  currentUserRole,
  onSuccess,
}: DynamicFormRendererProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const form = useForm<FormValues>();
  const normalizedAssignedRole = assignedRole?.trim().toUpperCase();
  const normalizedCurrentUserRole = currentUserRole?.trim().toUpperCase();
  const canExecuteStep =
    !normalizedAssignedRole ||
    normalizedCurrentUserRole === 'ADMIN' ||
    normalizedCurrentUserRole === normalizedAssignedRole;

  const appendFiles = (selectedFiles: FileList | File[]) => {
    const nextFiles = Array.from(selectedFiles);
    if (!nextFiles.length) return;
    setFiles((current) => [...current, ...nextFiles]);
  };

  const removeFile = (index: number) => {
    setFiles((current) => current.filter((_, itemIndex) => itemIndex !== index));
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    appendFiles(event.dataTransfer.files);
  };

  const onSubmit = async (data: FormValues) => {
    try {
      setIsSubmitting(true);

      const uploadedFiles: CivilUploadResponse[] = [];
      for (const file of files) {
        uploadedFiles.push(await uploadCivilAttachment(file));
      }

      const payload = {
        ...data,
        _attachments: uploadedFiles.map((item) => ({
          file_name: item.file_name,
          file_url: item.file_url,
          content_type: item.content_type,
          size: item.size,
        })),
      };

      await submitDocument(projectId, documentType, payload);
      toast.success('فرم و پیوست‌ها با موفقیت ثبت شد');
      setFiles([]);
      onSuccess();
    } catch (error) {
      console.error('Submit document error:', error);
      toast.error('خطا در ثبت فرم یا بارگذاری پیوست‌ها');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!canExecuteStep) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          این مرحله نیازمند تایید توسط نقش {assignedRole} است. کارتابل شما دسترسی اقدام در این مرحله را ندارد.
        </AlertDescription>
      </Alert>
    );
  }

  if (!formSchema || !formSchema.properties) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>فرم در حال ساخت است</CardTitle>
          <CardDescription>
            ساختار فرم {documentType} هنوز در سیستم تعریف نشده است.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            لطفا مستندات فنی را پس از تعریف ساختار فرم یا از مسیر پیوست‌های مرحله بارگذاری کنید.
          </p>
        </CardContent>
      </Card>
    );
  }

  const properties = Object.entries(formSchema.properties) as [string, any][];
  const requiredFields = formSchema.required || [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>{formSchema.title || `فرم ${documentType}`}</CardTitle>
        <CardDescription>
          {formSchema.description || 'لطفا اطلاعات زیر را با دقت وارد نمایید.'}
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
                const inputType = fieldSchema.format === 'date'
                  ? 'date'
                  : isNumber
                    ? 'number'
                    : 'text';

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
                              <Checkbox
                                checked={Boolean(field.value)}
                                onCheckedChange={(checked) => field.onChange(Boolean(checked))}
                                disabled={isReadOnly}
                              />
                              <span className="text-sm font-medium text-slate-700">
                                {fieldSchema.description || 'تایید می‌کنم'}
                              </span>
                            </label>
                          ) : isTextarea ? (
                            <Textarea
                              placeholder={fieldSchema.placeholder || ''}
                              {...field}
                              value={field.value || ''}
                              readOnly={isReadOnly}
                              disabled={isReadOnly}
                            />
                          ) : (
                            <Input
                              type={inputType}
                              placeholder={
                                fieldSchema.placeholder
                                || (isReadOnly ? 'پس از ثبت این مرحله به صورت خودکار تکمیل می‌شود' : '')
                              }
                              {...field}
                              value={field.value ?? ''}
                              readOnly={isReadOnly}
                              disabled={isReadOnly}
                              step={isNumber ? 'any' : undefined}
                              onChange={(event) => {
                                const nextValue = event.target.value;
                                if (isNumber) {
                                  field.onChange(nextValue === '' ? undefined : Number(nextValue));
                                  return;
                                }
                                field.onChange(nextValue);
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

            <section className="space-y-3 rounded-lg border border-dashed border-slate-300 bg-slate-50/70 p-4 dark:border-slate-700 dark:bg-slate-900/50">
              <div className="flex items-center gap-2">
                <Paperclip className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                <div>
                  <h4 className="text-sm font-bold">پیوست مستندات</h4>
                  <p className="text-xs text-muted-foreground">
                    نقشه‌ها، فرم‌های طراحی، مکاتبات و بسته‌های فنی را اینجا بارگذاری کنید.
                  </p>
                </div>
              </div>

              <div
                role="button"
                tabIndex={0}
                onClick={() => fileInputRef.current?.click()}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    fileInputRef.current?.click();
                  }
                }}
                onDragOver={(event) => {
                  event.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                className={`flex min-h-28 cursor-pointer flex-col items-center justify-center gap-2 rounded-md border bg-white px-4 py-6 text-center transition-colors dark:bg-slate-950 ${
                  isDragging
                    ? 'border-teal-500 ring-2 ring-teal-100 dark:ring-teal-900/40'
                    : 'border-slate-200 dark:border-slate-800'
                }`}
              >
                <UploadCloud className="h-7 w-7 text-slate-400" />
                <div className="text-sm font-medium text-slate-700 dark:text-slate-200">
                  فایل‌ها را رها کنید یا برای انتخاب کلیک کنید
                </div>
                <div className="text-xs text-muted-foreground">
                  PDF، تصویر، Word، Excel یا ZIP
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  className="hidden"
                  accept=".pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx,.zip"
                  onChange={(event) => {
                    if (event.target.files) {
                      appendFiles(event.target.files);
                      event.target.value = '';
                    }
                  }}
                />
              </div>

              {files.length > 0 && (
                <div className="space-y-2">
                  {files.map((file, index) => (
                    <div
                      key={`${file.name}-${file.lastModified}-${index}`}
                      className="flex items-center justify-between gap-3 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-800 dark:bg-slate-950"
                    >
                      <div className="min-w-0">
                        <div className="truncate font-medium">{file.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {(file.size / 1024).toFixed(1)} KB
                        </div>
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(index)}
                        aria-label="حذف پیوست"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <div className="flex justify-end pt-2">
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'در حال ثبت...' : 'ثبت و ارسال'}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
