import React, { useEffect, useMemo, useState } from 'react';
import { ContractorSelect } from './ContractorSelect';
import { useForm, Controller } from 'react-hook-form';
import { Button } from '../ui/button';
import { Card } from '../ui/card';
import { Progress } from '../ui/progress';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { Textarea } from '../ui/textarea';
import { Checkbox } from '../ui/checkbox';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  FileText,
  Loader2,
  User,
  Wallet,
} from 'lucide-react';
import api from '../../services/api';
import { type BudgetCheckResponse } from '../../services/budgetValidation';
import { formatRial, formatNumber } from '../../lib/utils';
import {
  createContractDraft,
  fetchContractTemplate,
  fetchContractTemplates,
  submitContract,
  type ContractResponse,
  type ContractTemplateListItem,
  type ContractTemplateResponse,
  type ContractTemplateSchemaProperty,
  type ContractorListItem,
} from '../../services/contracts';

type ContractWizardProps = {
  budgetRowId: number;
  budgetCode?: string;
  budgetDescription?: string;
  budgetRemaining?: number;
  onSubmitted?: (contractId: number) => void;
};

type ContractWizardFormValues = {
  contractTitle: string;
  totalAmount: number | undefined;
} & Record<string, unknown>;

const STEPS = [
  { number: 0, title: 'انتخاب پیمانکار' },
  { number: 1, title: 'قالب و جزئیات قرارداد' },
  { number: 2, title: 'بازبینی و ارسال' },
];

const REQUIRED_MESSAGE = 'تکمیل این فیلد الزامی است';

const getErrorMessage = (error: unknown, fallback: string) => {
  if (error instanceof Error) return error.message;
  if (typeof error === 'string') return error;
  return fallback;
};

const isInsufficientCredit = (message: string) => {
  const normalized = message.toLowerCase();
  return normalized.includes('insufficient') || normalized.includes('funds') || message.includes('اعتبار');
};

const buildDefaultTitle = (templateTitle?: string, contractorName?: string) => {
  const parts = [templateTitle, contractorName].filter(Boolean);
  return parts.length ? parts.join(' - ') : 'قرارداد جدید';
};

const buildTemplateDefaults = (template: ContractTemplateResponse | null) => {
  const defaults: Record<string, unknown> = {};
  const properties = template?.schema_definition?.properties ?? {};

  Object.entries(properties).forEach(([key, property]) => {
    const predefined = template?.default_values?.[key];
    const schemaDefault = property.default;

    if (predefined !== undefined) {
      defaults[key] = predefined;
      return;
    }

    if (schemaDefault !== undefined) {
      defaults[key] = schemaDefault;
      return;
    }

    if (property.type === 'boolean') {
      defaults[key] = false;
      return;
    }

    if (property.type === 'number' || property.type === 'integer') {
      defaults[key] = undefined;
      return;
    }

    defaults[key] = '';
  });

  return defaults;
};

const formatAmount = (value?: number | null) => {
  if (value === undefined || value === null) return '—';
  return formatRial(value);
};

const toTemplateData = (values: ContractWizardFormValues) => {
  const { contractTitle, totalAmount, ...rest } = values;
  return Object.fromEntries(
    Object.entries(rest).filter(([_, value]) => {
      if (value === undefined || value === null) return false;
      if (typeof value === 'string' && value.trim() === '') return false;
      return true;
    }),
  );
};

function ContractorSummaryPanel({ contractor }: { contractor: ContractorListItem | null }) {
  if (!contractor) {
    return (
      <div className="bg-white rounded-lg border border-dashed border-slate-300 p-5 text-center shadow-sm">
        <User className="h-8 w-8 text-slate-400 mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">لطفاً یک پیمانکار را انتخاب کنید</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm space-y-4">
      <div className="flex items-center gap-2 text-slate-700">
        <User className="h-4 w-4" />
        <p className="text-xs text-muted-foreground">پیمانکار انتخاب شده</p>
      </div>
      <p className="text-sm font-medium leading-6 text-right">{contractor.company_name}</p>
      <div className="border-t border-slate-100 pt-4 space-y-2 text-sm text-muted-foreground">
        <div className="flex items-center justify-between">
          <span>کد ملی</span>
          <span dir="ltr" className="font-mono text-foreground">{contractor.national_id}</span>
        </div>
        {contractor.ceo_name && (
          <div className="flex items-center justify-between">
            <span>مدیرعامل</span>
            <span className="text-foreground">{contractor.ceo_name}</span>
          </div>
        )}
        <div className="flex items-center justify-between">
          <span>وضعیت</span>
          <Badge variant={contractor.is_verified ? 'default' : 'secondary'} className="text-xs">
            {contractor.is_verified ? 'تایید شده' : 'در انتظار تایید'}
          </Badge>
        </div>
      </div>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right text-foreground">{value}</span>
    </div>
  );
}

export function ContractWizard({
  budgetRowId,
  budgetCode,
  budgetDescription,
  budgetRemaining,
  onSubmitted,
}: ContractWizardProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedContractor, setSelectedContractor] = useState<ContractorListItem | null>(null);

  const [templates, setTemplates] = useState<ContractTemplateListItem[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [templatesError, setTemplatesError] = useState<string | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<ContractTemplateResponse | null>(null);
  const [templateLoadingId, setTemplateLoadingId] = useState<number | null>(null);
  const [templateError, setTemplateError] = useState<string | null>(null);

  const [draft, setDraft] = useState<ContractResponse | null>(null);
  const [draftError, setDraftError] = useState<string | null>(null);
  const [isDrafting, setIsDrafting] = useState(false);

  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const [budgetInfo, setBudgetInfo] = useState<BudgetCheckResponse | null>(null);
  const [budgetError, setBudgetError] = useState<string | null>(null);

  const form = useForm<ContractWizardFormValues>({
    defaultValues: {
      contractTitle: '',
      totalAmount: undefined,
    },
  });

  const { register, handleSubmit, control, reset, getValues, watch, formState } = form;
  const watchedValues = watch();



  const requiredFields = useMemo(() => {
    const required = new Set<string>();
    selectedTemplate?.schema_definition?.required?.forEach((field) => required.add(field));
    selectedTemplate?.required_fields?.forEach((field) => required.add(field));
    return required;
  }, [selectedTemplate]);

  const templateProperties = selectedTemplate?.schema_definition?.properties ?? {};
  const templateEntries = useMemo(() => Object.entries(templateProperties), [templateProperties]);

  const resolvedBudgetCode = budgetInfo?.budget_code ?? budgetCode ?? budgetRowId?.toString();
  const resolvedBudgetDescription = budgetInfo?.description ?? budgetDescription;
  const resolvedBudgetRemaining =
    budgetInfo?.remaining_available ?? budgetRemaining;



  useEffect(() => {
    const loadTemplates = async () => {
      setTemplatesLoading(true);
      setTemplatesError(null);
      try {
        const response = await fetchContractTemplates({ active_only: true, limit: 100 });
        setTemplates(response.items ?? []);
      } catch (error) {
        setTemplatesError(getErrorMessage(error, 'خطا در بارگیری قالب‌ها'));
      } finally {
        setTemplatesLoading(false);
      }
    };

    loadTemplates();
  }, []);

  useEffect(() => {
    if (!budgetRowId) return;

    const loadBudgetInfo = async () => {
      setBudgetError(null);
      try {
        const data = await api.get<BudgetCheckResponse>(`/budget/row/${budgetRowId}`);
        setBudgetInfo(data);
      } catch (error) {
        setBudgetError(getErrorMessage(error, 'خطا در دریافت اطلاعات بودجه'));
      }
    };

    loadBudgetInfo();
  }, [budgetRowId]);

  useEffect(() => {
    if (!selectedTemplate) return;

    const currentValues = getValues();
    const nextTitle = currentValues.contractTitle?.trim()
      ? currentValues.contractTitle
      : buildDefaultTitle(selectedTemplate.title, selectedContractor?.company_name);

    reset({
      contractTitle: nextTitle,
      totalAmount: currentValues.totalAmount,
      ...buildTemplateDefaults(selectedTemplate),
    });
  }, [selectedTemplate, selectedContractor, reset, getValues]);

  const handleSelectTemplate = async (template: ContractTemplateListItem) => {
    setTemplateError(null);
    setTemplateLoadingId(template.id);
    try {
      const detail = await fetchContractTemplate(template.id);
      setSelectedTemplate(detail);
    } catch (error) {
      setTemplateError(getErrorMessage(error, 'خطا در دریافت قالب قرارداد'));
    } finally {
      setTemplateLoadingId(null);
    }
  };

  const onFormError = (errors: Record<string, unknown>) => {
    console.error('[ContractWizard] Form Validation Errors:', errors);
    setDraftError('لطفاً تمام فیلدهای الزامی را تکمیل کنید');
  };

  const handleCreateDraft = handleSubmit(async (values) => {
    console.log('[ContractWizard] Submitting form data:', values);

    if (!selectedContractor) {
      setDraftError('انتخاب پیمانکار الزامی است');
      return;
    }
    if (!selectedTemplate) {
      setDraftError('انتخاب قالب قرارداد الزامی است');
      return;
    }
    if (!budgetRowId) {
      setDraftError('ردیف بودجه مشخص نشده است');
      return;
    }

    const totalAmount = Number(values.totalAmount ?? 0);
    if (resolvedBudgetRemaining !== undefined && totalAmount > resolvedBudgetRemaining) {
      setDraftError('اعتبار ردیف بودجه کافی نیست');
      return;
    }

    setDraftError(null);
    setIsDrafting(true);

    try {
      const templateData = toTemplateData(values);
      const payload = {
        budget_row_id: budgetRowId,
        contractor_id: selectedContractor.id,
        template_id: selectedTemplate.id,
        title: values.contractTitle,
        total_amount: totalAmount,
        template_data: templateData,
        start_date: typeof templateData.start_date === 'string' ? templateData.start_date : undefined,
        end_date: typeof templateData.end_date === 'string' ? templateData.end_date : undefined,
      };

      const response = await createContractDraft(payload);
      setDraft(response);
      setCurrentStep(2);
    } catch (error) {
      setDraftError(getErrorMessage(error, 'خطا در ایجاد پیش‌نویس قرارداد'));
    } finally {
      setIsDrafting(false);
    }
  }, onFormError);

  const handleSubmitContract = async () => {
    if (!draft) return;
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      const response = await submitContract(draft.id);
      setDraft(response);
      setIsSubmitted(true);
      onSubmitted?.(response.id);
    } catch (error) {
      setSubmitError(getErrorMessage(error, 'خطا در ارسال قرارداد برای تایید'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const nextStep = () => {
    setCurrentStep((prev) => Math.min(prev + 1, STEPS.length - 1));
  };

  const prevStep = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 0));
  };

  const progress = ((currentStep + 1) / STEPS.length) * 100;
  const totalAmountValue = watchedValues.totalAmount;
  const templateDataPreview = toTemplateData(watchedValues);

  if (isSubmitted && draft) {
    return (
      <div className="max-w-2xl mx-auto">
        <Card className="p-8 text-center space-y-6">
          <div className="flex justify-center">
            <div className="bg-green-100 p-4 rounded-full">
              <CheckCircle2 className="h-12 w-12 text-green-600" />
            </div>
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl">قرارداد با موفقیت ارسال شد</h2>
            <p className="text-muted-foreground">
              شماره قرارداد: <span className="font-mono">{draft.contract_number}</span>
            </p>
          </div>
          <div className="bg-amber-50 border border-amber-200 p-4 rounded text-sm text-amber-900">
            قرارداد شما در وضعیت "در انتظار تایید" قرار دارد و پس از بررسی مدیر، تایید یا رد خواهد شد.
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <Card className="p-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2>مرحله {currentStep + 1} از {STEPS.length}</h2>
              <p className="text-sm text-muted-foreground">{STEPS[currentStep].title}</p>
            </div>
            <div className="text-left text-sm text-muted-foreground">
              {Math.round(progress)}% تکمیل شده
            </div>
          </div>
          <Progress value={progress} className="h-2" />
        </div>
      </Card>

      <div className="flex items-center justify-between gap-2">
        {STEPS.map((step, index) => (
          <React.Fragment key={step.number}>
            <div className="flex flex-col items-center gap-1 flex-1">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm transition-colors ${step.number === currentStep
                  ? 'bg-primary text-primary-foreground'
                  : step.number < currentStep
                    ? 'bg-green-600 text-white'
                    : 'bg-muted text-muted-foreground'
                  }`}
              >
                {step.number < currentStep ? '✓' : step.number + 1}
              </div>
              <p className={`text-xs text-center hidden md:block ${step.number === currentStep ? 'text-foreground' : 'text-muted-foreground'
                }`}>
                {step.title}
              </p>
            </div>
            {index < STEPS.length - 1 && (
              <div className={`h-0.5 flex-1 ${step.number < currentStep ? 'bg-green-600' : 'bg-border'
                }`} />
            )}
          </React.Fragment>
        ))}
      </div>

      <Card className="p-6">
        {currentStep === 0 && (
          <div className="space-y-6">
            <div>
              <h3>انتخاب پیمانکار</h3>
              <p className="text-sm text-muted-foreground mt-1">
                پیمانکار موردنظر را بر اساس نام شرکت یا کد ملی انتخاب کنید
              </p>
            </div>

            <div className="grid grid-cols-12 gap-6">
              <div className="col-span-12 lg:col-span-8 space-y-4">
                <div className="space-y-3">
                  <Label>انتخاب پیمانکار</Label>
                  <ContractorSelect
                    value={selectedContractor}
                    onChange={setSelectedContractor}
                  />
                </div>
              </div>

              <div className="col-span-12 lg:col-span-4">
                <div className="sticky top-4 space-y-3">
                  <Label>خلاصه پیمانکار</Label>
                  <ContractorSummaryPanel contractor={selectedContractor} />
                </div>
              </div>
            </div>
          </div>
        )}

        {currentStep === 1 && (
          <div className="space-y-6">
            <div>
              <h3>قالب قرارداد و جزئیات</h3>
              <p className="text-sm text-muted-foreground mt-1">
                قالب مناسب را انتخاب کرده و اطلاعات قرارداد را تکمیل کنید
              </p>
            </div>

            <div className="grid grid-cols-12 gap-6">
              <div className="col-span-12 lg:col-span-8 space-y-4">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label>لیست قالب‌های قرارداد</Label>
                    {templates.length > 0 && (
                      <span className="text-xs text-muted-foreground">
                        {templates.length} قالب فعال
                      </span>
                    )}
                  </div>

                  {templatesLoading ? (
                    <div className="flex items-center justify-center py-8 bg-white rounded-lg border border-slate-200">
                      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                      <span className="mr-2 text-muted-foreground">در حال بارگیری...</span>
                    </div>
                  ) : templatesError ? (
                    <div className="text-center py-8 text-red-600 bg-white rounded-lg border border-red-100">
                      {templatesError}
                    </div>
                  ) : templates.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground bg-white rounded-lg border border-slate-200">
                      قالب فعالی یافت نشد
                    </div>
                  ) : (
                    <div className="space-y-3 max-h-[300px] overflow-y-auto pl-1">
                      {templates.map((template) => {
                        const isSelected = selectedTemplate?.id === template.id;
                        const isLoading = templateLoadingId === template.id;
                        return (
                          <button
                            key={template.id}
                            type="button"
                            onClick={() => handleSelectTemplate(template)}
                            className={`w-full text-right bg-white shadow-sm rounded-lg border p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-blue-500 ${isSelected
                              ? 'border-l-4 border-green-500 bg-green-50/50 border-green-200 scale-[1.01] shadow-md'
                              : 'border-slate-200'
                              }`}
                          >
                            <div className="flex items-start gap-3">
                              <div className="mt-1 flex-shrink-0">
                                {isLoading ? (
                                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                                ) : isSelected ? (
                                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                                ) : (
                                  <div className="h-5 w-5 rounded-full border border-slate-300" />
                                )}
                              </div>
                              <div className="flex-1 min-w-0 space-y-2">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="font-semibold text-base">{template.title}</span>
                                  <Badge variant="outline" className="text-xs">
                                    نسخه {template.version}
                                  </Badge>
                                </div>
                                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                                  <span className="font-mono">{template.code}</span>
                                  {template.category && <span>دسته: {template.category}</span>}
                                </div>
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>

                {templateError && (
                  <Alert variant="destructive">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>خطا در دریافت قالب</AlertTitle>
                    <AlertDescription>{templateError}</AlertDescription>
                  </Alert>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="contractTitle">عنوان قرارداد</Label>
                    <Input
                      id="contractTitle"
                      placeholder="عنوان قرارداد"
                      {...register('contractTitle', { required: REQUIRED_MESSAGE })}
                    />
                    {formState.errors.contractTitle && (
                      <p className="text-xs text-destructive">{String(formState.errors.contractTitle.message)}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="totalAmount">مبلغ کل قرارداد (ریال)</Label>
                    <Input
                      id="totalAmount"
                      type="number"
                      placeholder="مبلغ را وارد کنید"
                      {...register('totalAmount', {
                        required: REQUIRED_MESSAGE,
                        min: { value: 1, message: 'مبلغ باید بیشتر از صفر باشد' },
                        setValueAs: (value) => (value === '' ? undefined : Number(value)),
                      })}
                    />
                    {formState.errors.totalAmount && (
                      <p className="text-xs text-destructive">{String(formState.errors.totalAmount.message)}</p>
                    )}
                  </div>
                </div>

                {selectedTemplate && (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <ClipboardCheck className="h-4 w-4 text-primary" />
                      <h4 className="text-sm font-semibold">اطلاعات تکمیلی قالب</h4>
                    </div>

                    {templateEntries.length === 0 ? (
                      <div className="text-sm text-muted-foreground bg-muted/40 border border-dashed border-slate-200 p-4 rounded-lg">
                        این قالب فیلد تکمیلی ندارد.
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {templateEntries.map(([name, property]) => {
                          const isRequired = requiredFields.has(name);
                          const errorMessage = formState.errors[name]?.message;
                          const label = property.title ?? name;

                          if (property.enum && property.enum.length > 0) {
                            return (
                              <div key={name} className="space-y-2">
                                <Label>
                                  {label}
                                  {isRequired && <span className="text-destructive mr-1">*</span>}
                                </Label>
                                <Controller
                                  name={name}
                                  control={control}
                                  rules={{ required: isRequired ? REQUIRED_MESSAGE : false }}
                                  render={({ field }) => (
                                    <Select value={(field.value as string) ?? ''} onValueChange={field.onChange}>
                                      <SelectTrigger>
                                        <SelectValue placeholder="انتخاب کنید" />
                                      </SelectTrigger>
                                      <SelectContent>
                                        {property.enum?.map((option) => (
                                          <SelectItem key={option} value={String(option)}>
                                            {option}
                                          </SelectItem>
                                        ))}
                                      </SelectContent>
                                    </Select>
                                  )}
                                />
                                {property.description && (
                                  <p className="text-xs text-muted-foreground">{property.description}</p>
                                )}
                                {errorMessage && (
                                  <p className="text-xs text-destructive">{String(errorMessage)}</p>
                                )}
                              </div>
                            );
                          }

                          if (property.type === 'boolean') {
                            return (
                              <div key={name} className="flex items-start gap-3 rounded-lg border border-slate-200 p-3 bg-white">
                                <Controller
                                  name={name}
                                  control={control}
                                  rules={{ required: isRequired ? REQUIRED_MESSAGE : false }}
                                  render={({ field }) => (
                                    <Checkbox
                                      checked={field.value === true}
                                      onCheckedChange={(checked) => field.onChange(checked === true)}
                                    />
                                  )}
                                />
                                <div className="space-y-1">
                                  <Label className="text-sm">
                                    {label}
                                    {isRequired && <span className="text-destructive mr-1">*</span>}
                                  </Label>
                                  {property.description && (
                                    <p className="text-xs text-muted-foreground">{property.description}</p>
                                  )}
                                  {errorMessage && (
                                    <p className="text-xs text-destructive">{String(errorMessage)}</p>
                                  )}
                                </div>
                              </div>
                            );
                          }

                          const isTextArea =
                            property.format === 'textarea' || property.format === 'multiline';
                          const isDate = property.format === 'date';
                          const isNumber = property.type === 'number' || property.type === 'integer';
                          const sharedRules = {
                            required: isRequired ? REQUIRED_MESSAGE : false,
                            min: property.minimum !== undefined
                              ? { value: property.minimum, message: `حداقل مقدار ${property.minimum}` }
                              : undefined,
                            max: property.maximum !== undefined
                              ? { value: property.maximum, message: `حداکثر مقدار ${property.maximum}` }
                              : undefined,
                            minLength: property.minLength !== undefined
                              ? { value: property.minLength, message: `حداقل ${property.minLength} کاراکتر` }
                              : undefined,
                            maxLength: property.maxLength !== undefined
                              ? { value: property.maxLength, message: `حداکثر ${property.maxLength} کاراکتر` }
                              : undefined,
                            setValueAs: isNumber ? (value: string) => (value === '' ? undefined : Number(value)) : undefined,
                          };

                          return (
                            <div key={name} className="space-y-2">
                              <Label>
                                {label}
                                {isRequired && <span className="text-destructive mr-1">*</span>}
                              </Label>
                              {isTextArea ? (
                                <Textarea
                                  rows={3}
                                  placeholder={label}
                                  {...register(name, sharedRules)}
                                />
                              ) : (
                                <Input
                                  type={isDate ? 'date' : isNumber ? 'number' : 'text'}
                                  placeholder={label}
                                  {...register(name, sharedRules)}
                                />
                              )}
                              {property.description && (
                                <p className="text-xs text-muted-foreground">{property.description}</p>
                              )}
                              {errorMessage && (
                                <p className="text-xs text-destructive">{String(errorMessage)}</p>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="col-span-12 lg:col-span-4">
                <div className="sticky top-4 space-y-3">
                  <Label>خلاصه قرارداد</Label>
                  <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm space-y-4">
                    <div className="flex items-center gap-2 text-slate-700">
                      <FileText className="h-4 w-4" />
                      <p className="text-xs text-muted-foreground">پیش‌نمایش انتخاب‌ها</p>
                    </div>
                    <div className="space-y-2">
                      <SummaryRow label="پیمانکار" value={selectedContractor?.company_name ?? '—'} />
                      <SummaryRow label="قالب" value={selectedTemplate?.title ?? '—'} />
                      <SummaryRow label="ردیف بودجه" value={resolvedBudgetCode ?? '—'} />
                      <SummaryRow label="مانده اعتبار" value={formatAmount(resolvedBudgetRemaining)} />
                      <SummaryRow label="مبلغ قرارداد" value={formatAmount(totalAmountValue as number)} />
                    </div>
                    {budgetError && (
                      <p className="text-xs text-destructive">{budgetError}</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {currentStep === 2 && (
          <div className="space-y-6">
            <div>
              <h3>بازبینی نهایی</h3>
              <p className="text-sm text-muted-foreground mt-1">
                اطلاعات وارد شده را بررسی کرده و قرارداد را برای تایید ارسال کنید
              </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
                <div className="flex items-center gap-2 text-slate-700">
                  <User className="h-4 w-4" />
                  <h4 className="text-sm font-semibold">پیمانکار</h4>
                </div>
                <SummaryRow label="نام" value={selectedContractor?.company_name ?? '—'} />
                <SummaryRow label="کد ملی" value={selectedContractor?.national_id ?? '—'} />
                <SummaryRow label="مدیرعامل" value={selectedContractor?.ceo_name ?? '—'} />
              </div>

              <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
                <div className="flex items-center gap-2 text-slate-700">
                  <Wallet className="h-4 w-4" />
                  <h4 className="text-sm font-semibold">بودجه</h4>
                </div>
                <SummaryRow label="ردیف بودجه" value={resolvedBudgetCode ?? '—'} />
                <SummaryRow label="شرح" value={resolvedBudgetDescription ?? '—'} />
                <SummaryRow label="مانده اعتبار" value={formatAmount(resolvedBudgetRemaining)} />
              </div>

              <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
                <div className="flex items-center gap-2 text-slate-700">
                  <FileText className="h-4 w-4" />
                  <h4 className="text-sm font-semibold">اطلاعات قرارداد</h4>
                </div>
                <SummaryRow label="عنوان قرارداد" value={watchedValues.contractTitle || '—'} />
                <SummaryRow label="قالب" value={selectedTemplate?.title ?? '—'} />
                <SummaryRow label="مبلغ کل" value={formatAmount(totalAmountValue as number)} />
                <SummaryRow label="شماره قرارداد" value={draft?.contract_number ?? '—'} />
              </div>

              <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
                <div className="flex items-center gap-2 text-slate-700">
                  <ClipboardCheck className="h-4 w-4" />
                  <h4 className="text-sm font-semibold">جزئیات قالب</h4>
                </div>
                {Object.keys(templateDataPreview).length === 0 ? (
                  <p className="text-sm text-muted-foreground">جزئیات تکمیلی ثبت نشده است.</p>
                ) : (
                  <div className="space-y-2">
                    {Object.entries(templateDataPreview).map(([key, value]) => {
                      const property = templateProperties[key] as ContractTemplateSchemaProperty | undefined;
                      const label = property?.title ?? key;
                      const displayValue =
                        typeof value === 'boolean'
                          ? value ? 'بله' : 'خیر'
                          : typeof value === 'number'
                            ? formatNumber(value)
                            : String(value);
                      return <SummaryRow key={key} label={label} value={displayValue} />;
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </Card>

      <Card className="p-4">
        {draftError && (
          <Alert variant="destructive" className="mb-4">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>
              {isInsufficientCredit(draftError) ? 'اعتبار ناکافی' : 'خطا در ایجاد پیش‌نویس'}
            </AlertTitle>
            <AlertDescription>{draftError}</AlertDescription>
          </Alert>
        )}
        {submitError && (
          <Alert variant="destructive" className="mb-4">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>خطا در ارسال قرارداد</AlertTitle>
            <AlertDescription>{submitError}</AlertDescription>
          </Alert>
        )}

        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={prevStep}
            disabled={currentStep === 0 || isDrafting || isSubmitting}
          >
            <ChevronRight className="h-4 w-4 ml-2" />
            مرحله قبل
          </Button>

          {currentStep < 2 ? (
            <Button
              onClick={currentStep === 1 ? handleCreateDraft : nextStep}
              size="lg"
              disabled={
                (currentStep === 0 && !selectedContractor) ||
                (currentStep === 1 && (!selectedTemplate || isDrafting)) ||
                !budgetRowId
              }
            >
              {currentStep === 1 ? (
                isDrafting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    در حال رزرو بودجه...
                  </>
                ) : (
                  <>
                    رزرو و ادامه
                    <ChevronLeft className="h-4 w-4 mr-2" />
                  </>
                )
              ) : (
                <>
                  مرحله بعد
                  <ChevronLeft className="h-4 w-4 mr-2" />
                </>
              )}
            </Button>
          ) : (
            <Button
              onClick={handleSubmitContract}
              size="lg"
              className="bg-green-600 hover:bg-green-700"
              disabled={isSubmitting || !draft}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  در حال ارسال...
                </>
              ) : (
                <>
                  ارسال برای تایید
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                </>
              )}
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}
