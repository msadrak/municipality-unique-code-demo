import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { submitDocument } from '../../services/civil';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '../ui/form';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { toast } from 'sonner';

interface DynamicFormRendererProps {
  projectId: string | number;
  documentType: string;
  formSchema?: any;
  onSuccess: () => void;
}

export function DynamicFormRenderer({ projectId, documentType, formSchema, onSuccess }: DynamicFormRendererProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const form = useForm();

  if (!formSchema || !formSchema.properties) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>فرم در حال ساخت است</CardTitle>
          <CardDescription>
            رابط کاربری برای نوع فرم {documentType} هنوز پیاده‌سازی نشده یا ساختار آن در سیستم تعریف نشده است.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            لطفاً با پشتیبانی سیستم تماس بگیرید یا منتظر بروزرسانی‌های بعدی باشید.
          </p>
        </CardContent>
      </Card>
    );
  }

  const onSubmit = async (data: any) => {
    try {
      setIsSubmitting(true);
      await submitDocument(projectId, documentType, data);
      toast.success('فرم با موفقیت ثبت شد');
      onSuccess();
    } catch (error) {
      console.error('Submit document error:', error);
      toast.error('خطا در ثبت فرم');
    } finally {
      setIsSubmitting(false);
    }
  };

  const properties = Object.entries(formSchema.properties) as [string, any][];
  const requiredFields = formSchema.required || [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>{formSchema.title || `فرم ${documentType}`}</CardTitle>
        <CardDescription>
          {formSchema.description || 'لطفاً اطلاعات زیر را با دقت وارد نمایید.'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {properties.map(([fieldName, fieldSchema]) => {
                const isRequired = requiredFields.includes(fieldName);
                const isTextarea = fieldSchema.widget === 'textarea';

                return (
                  <FormField
                    key={fieldName}
                    control={form.control}
                    name={fieldName}
                    rules={{ required: isRequired ? 'این فیلد الزامی است' : false }}
                    render={({ field }) => (
                      <FormItem className={isTextarea ? "md:col-span-2" : ""}>
                        <FormLabel>
                          {fieldSchema.title || fieldName}
                          {isRequired && <span className="text-red-500 mr-1">*</span>}
                        </FormLabel>
                        <FormControl>
                          {isTextarea ? (
                            <Textarea placeholder={fieldSchema.placeholder || ''} {...field} value={field.value || ''} />
                          ) : (
                            <Input placeholder={fieldSchema.placeholder || ''} {...field} value={field.value || ''} />
                          )}
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                );
              })}
            </div>
            <div className="flex justify-end pt-4">
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
