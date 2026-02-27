import React, { useMemo, useState } from 'react';
import { Building2, Landmark, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '../components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { cn } from '../components/ui/utils';
import { IRAN_PROVINCES } from '../data/iranProvinces';

type ContractorRegistrationForm = {
  applicant_name: string;
  national_id: string;
  corporate_id: string;
  economic_code: string;
  postal_code: string;
  province: string;
  city: string;
  phone: string;
  address: string;
  bank_name: string;
  account_number: string;
  iban: string;
};

type FormField = keyof ContractorRegistrationForm;
type FormErrors = Partial<Record<FormField, string>>;

const INITIAL_FORM: ContractorRegistrationForm = {
  applicant_name: '',
  national_id: '',
  corporate_id: '',
  economic_code: '',
  postal_code: '',
  province: '',
  city: '',
  phone: '',
  address: '',
  bank_name: '',
  account_number: '',
  iban: '',
};

const BANK_OPTIONS = [
  'ملی',
  'ملت',
  'تجارت',
  'صادرات',
  'سپه',
  'پارسیان',
  'پاسارگاد',
  'سامان',
];

const monoInputClassName = 'font-mono-num text-left tracking-[0.06em]';

const onlyDigits = (value: string) => value.replace(/\D/g, '');

const validateField = (
  field: FormField,
  value: string,
  form: ContractorRegistrationForm,
): string | undefined => {
  switch (field) {
    case 'applicant_name':
      if (!value.trim()) return 'نام متقاضی/شرکت الزامی است.';
      break;
    case 'national_id':
      if (!/^\d{10}$/.test(value)) return 'کد ملی مدیرعامل باید دقیقاً ۱۰ رقم باشد.';
      break;
    case 'corporate_id':
      if (!/^\d{11}$/.test(value)) return 'شناسه ملی شرکت باید دقیقاً ۱۱ رقم باشد.';
      break;
    case 'economic_code':
      if (!value.trim()) return 'شماره اقتصادی الزامی است.';
      break;
    case 'postal_code':
      if (!/^\d{10}$/.test(value)) return 'کد پستی باید دقیقاً ۱۰ رقم باشد.';
      break;
    case 'province':
      if (!value) return 'انتخاب استان الزامی است.';
      break;
    case 'city':
      if (!value) return 'انتخاب شهر الزامی است.';
      break;
    case 'phone':
      if (!/^\d{10,11}$/.test(value)) return 'شماره تماس باید ۱۰ یا ۱۱ رقم باشد.';
      break;
    case 'address':
      if (!value.trim()) return 'آدرس کامل الزامی است.';
      break;
    case 'bank_name':
      if (!value) return 'نام بانک را انتخاب کنید.';
      break;
    case 'account_number':
      if (!/^\d{6,20}$/.test(value)) return 'شماره حساب باید فقط عدد و بین ۶ تا ۲۰ رقم باشد.';
      break;
    case 'iban':
      if (!/^\d{24}$/.test(value)) return 'پس از پیشوند IR باید دقیقاً ۲۴ رقم وارد شود.';
      break;
    default:
      break;
  }

  if (field === 'city' && form.province) {
    const allowedCities = IRAN_PROVINCES.find((item) => item.name === form.province)?.cities ?? [];
    if (value && !allowedCities.includes(value)) {
      return 'شهر انتخاب‌شده برای استان معتبر نیست.';
    }
  }

  return undefined;
};

const validateForm = (form: ContractorRegistrationForm): FormErrors => {
  const errors: FormErrors = {};

  (Object.keys(form) as FormField[]).forEach((field) => {
    const message = validateField(field, form[field], form);
    if (message) {
      errors[field] = message;
    }
  });

  return errors;
};

export function ContractorRegistration() {
  const [form, setForm] = useState<ContractorRegistrationForm>(INITIAL_FORM);
  const [errors, setErrors] = useState<FormErrors>({});
  const [touched, setTouched] = useState<Partial<Record<FormField, boolean>>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const provinces = useMemo(() => IRAN_PROVINCES.map((item) => item.name), []);
  const cities = useMemo(() => {
    if (!form.province) return [];
    return IRAN_PROVINCES.find((item) => item.name === form.province)?.cities ?? [];
  }, [form.province]);

  const setFieldValue = (field: FormField, value: string) => {
    setForm((prev) => {
      if (field === 'province') {
        return { ...prev, province: value, city: '' };
      }
      return { ...prev, [field]: value };
    });

    if (touched[field]) {
      const nextForm =
        field === 'province'
          ? { ...form, province: value, city: '' }
          : { ...form, [field]: value };
      const nextError = validateField(field, value, nextForm);
      setErrors((prev) => {
        const updated = { ...prev };
        if (nextError) updated[field] = nextError;
        else delete updated[field];
        if (field === 'province') delete updated.city;
        return updated;
      });
    }
  };

  const handleBlur = (field: FormField) => {
    setTouched((prev) => ({ ...prev, [field]: true }));
    const message = validateField(field, form[field], form);
    setErrors((prev) => {
      const updated = { ...prev };
      if (message) updated[field] = message;
      else delete updated[field];
      return updated;
    });
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const fullTouched = (Object.keys(form) as FormField[]).reduce((acc, field) => {
      acc[field] = true;
      return acc;
    }, {} as Partial<Record<FormField, boolean>>);
    setTouched(fullTouched);

    const validationErrors = validateForm(form);
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) {
      toast.error('لطفاً خطاهای فرم را اصلاح کنید.');
      return;
    }

    setIsSubmitting(true);

    await new Promise((resolve) => setTimeout(resolve, 1000));

    setIsSubmitting(false);
    toast.success('اطلاعات شما با موفقیت دریافت شد. سیستم در حال تطبیق پرونده شماست.');
  };

  const getFieldError = (field: FormField) => (touched[field] ? errors[field] : undefined);

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top,_#e2e8f0_0%,_#f8fafc_45%,_#ffffff_100%)] px-4 py-8 sm:px-6 lg:px-8">
      <div className="pointer-events-none absolute -top-20 left-1/2 h-72 w-72 -translate-x-1/2 rounded-full bg-primary/10 blur-3xl" />

      <Card className="relative mx-auto w-full max-w-6xl border-primary/20 bg-card/95 shadow-xl backdrop-blur font-sans">
        <CardHeader className="border-b border-primary/10 bg-gradient-to-l from-primary/10 via-primary/5 to-transparent">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-primary p-3 text-primary-foreground shadow-sm">
              <Building2 className="h-6 w-6" />
            </div>
            <div className="space-y-1">
              <CardTitle className="text-xl sm:text-2xl">
                احراز هویت و تکمیل اطلاعات پیمانکاران
              </CardTitle>
              <CardDescription>
                اطلاعات هویتی و بانکی خود را برای ثبت یا به‌روزرسانی پرونده پیمانکاری وارد کنید.
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="pt-6 sm:pt-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
              <Card className="border-primary/20 shadow-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">اطلاعات هویتی و ارتباطی</CardTitle>
                  <CardDescription>مشخصات ثبتی، محل فعالیت و اطلاعات تماس</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="applicant_name">نام متقاضی/شرکت</Label>
                      <Input
                        id="applicant_name"
                        value={form.applicant_name}
                        onChange={(event) => setFieldValue('applicant_name', event.target.value)}
                        onBlur={() => handleBlur('applicant_name')}
                        placeholder="نام شخص یا شرکت"
                        aria-invalid={!!getFieldError('applicant_name')}
                      />
                      {getFieldError('applicant_name') && (
                        <p className="text-xs text-destructive">{getFieldError('applicant_name')}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="national_id">کد ملی مدیرعامل</Label>
                      <Input
                        id="national_id"
                        dir="ltr"
                        inputMode="numeric"
                        maxLength={10}
                        value={form.national_id}
                        onChange={(event) =>
                          setFieldValue('national_id', onlyDigits(event.target.value).slice(0, 10))
                        }
                        onBlur={() => handleBlur('national_id')}
                        placeholder="XXXXXXXXXX"
                        className={monoInputClassName}
                        aria-invalid={!!getFieldError('national_id')}
                      />
                      {getFieldError('national_id') && (
                        <p className="text-xs text-destructive">{getFieldError('national_id')}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="corporate_id">شناسه ملی شرکت</Label>
                      <Input
                        id="corporate_id"
                        dir="ltr"
                        inputMode="numeric"
                        maxLength={11}
                        value={form.corporate_id}
                        onChange={(event) =>
                          setFieldValue('corporate_id', onlyDigits(event.target.value).slice(0, 11))
                        }
                        onBlur={() => handleBlur('corporate_id')}
                        placeholder="XXXXXXXXXXX"
                        className={monoInputClassName}
                        aria-invalid={!!getFieldError('corporate_id')}
                      />
                      {getFieldError('corporate_id') && (
                        <p className="text-xs text-destructive">{getFieldError('corporate_id')}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="economic_code">شماره اقتصادی</Label>
                      <Input
                        id="economic_code"
                        dir="ltr"
                        value={form.economic_code}
                        onChange={(event) => setFieldValue('economic_code', event.target.value)}
                        onBlur={() => handleBlur('economic_code')}
                        placeholder="شماره اقتصادی"
                        className={monoInputClassName}
                        aria-invalid={!!getFieldError('economic_code')}
                      />
                      {getFieldError('economic_code') && (
                        <p className="text-xs text-destructive">{getFieldError('economic_code')}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="postal_code">کد پستی</Label>
                      <Input
                        id="postal_code"
                        dir="ltr"
                        inputMode="numeric"
                        maxLength={10}
                        value={form.postal_code}
                        onChange={(event) =>
                          setFieldValue('postal_code', onlyDigits(event.target.value).slice(0, 10))
                        }
                        onBlur={() => handleBlur('postal_code')}
                        placeholder="XXXXXXXXXX"
                        className={monoInputClassName}
                        aria-invalid={!!getFieldError('postal_code')}
                      />
                      {getFieldError('postal_code') && (
                        <p className="text-xs text-destructive">{getFieldError('postal_code')}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="province">استان</Label>
                      <Select
                        value={form.province}
                        onValueChange={(value) => {
                          setFieldValue('province', value);
                        }}
                      >
                        <SelectTrigger id="province" aria-invalid={!!getFieldError('province')}>
                          <SelectValue placeholder="انتخاب استان" />
                        </SelectTrigger>
                        <SelectContent>
                          {provinces.map((province) => (
                            <SelectItem key={province} value={province}>
                              {province}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {getFieldError('province') && (
                        <p className="text-xs text-destructive">{getFieldError('province')}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="city">شهر</Label>
                      <Select
                        value={form.city}
                        onValueChange={(value) => setFieldValue('city', value)}
                        disabled={!form.province}
                      >
                        <SelectTrigger id="city" aria-invalid={!!getFieldError('city')}>
                          <SelectValue
                            placeholder={form.province ? 'انتخاب شهر' : 'ابتدا استان را انتخاب کنید'}
                          />
                        </SelectTrigger>
                        <SelectContent>
                          {cities.map((city) => (
                            <SelectItem key={city} value={city}>
                              {city}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {getFieldError('city') && (
                        <p className="text-xs text-destructive">{getFieldError('city')}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="phone">شماره تماس</Label>
                      <Input
                        id="phone"
                        dir="ltr"
                        inputMode="tel"
                        maxLength={11}
                        value={form.phone}
                        onChange={(event) =>
                          setFieldValue('phone', onlyDigits(event.target.value).slice(0, 11))
                        }
                        onBlur={() => handleBlur('phone')}
                        placeholder="09XXXXXXXXX"
                        className={monoInputClassName}
                        aria-invalid={!!getFieldError('phone')}
                      />
                      {getFieldError('phone') && (
                        <p className="text-xs text-destructive">{getFieldError('phone')}</p>
                      )}
                    </div>

                    <div className="space-y-2 md:col-span-2">
                      <Label htmlFor="address">آدرس کامل</Label>
                      <Textarea
                        id="address"
                        value={form.address}
                        onChange={(event) => setFieldValue('address', event.target.value)}
                        onBlur={() => handleBlur('address')}
                        placeholder="نشانی کامل محل شرکت/دفتر مرکزی"
                        rows={4}
                        aria-invalid={!!getFieldError('address')}
                      />
                      {getFieldError('address') && (
                        <p className="text-xs text-destructive">{getFieldError('address')}</p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-primary/20 shadow-sm">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <Landmark className="h-5 w-5 text-primary" />
                    <CardTitle className="text-lg">اطلاعات بانکی</CardTitle>
                  </div>
                  <CardDescription>برای واریزها و تطبیق‌های مالی پرونده پیمانکار</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="bank_name">نام بانک</Label>
                      <Select value={form.bank_name} onValueChange={(value) => setFieldValue('bank_name', value)}>
                        <SelectTrigger id="bank_name" aria-invalid={!!getFieldError('bank_name')}>
                          <SelectValue placeholder="انتخاب بانک" />
                        </SelectTrigger>
                        <SelectContent>
                          {BANK_OPTIONS.map((bank) => (
                            <SelectItem key={bank} value={bank}>
                              {bank}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {getFieldError('bank_name') && (
                        <p className="text-xs text-destructive">{getFieldError('bank_name')}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="account_number">شماره حساب</Label>
                      <Input
                        id="account_number"
                        dir="ltr"
                        inputMode="numeric"
                        maxLength={20}
                        value={form.account_number}
                        onChange={(event) =>
                          setFieldValue('account_number', onlyDigits(event.target.value).slice(0, 20))
                        }
                        onBlur={() => handleBlur('account_number')}
                        placeholder="شماره حساب"
                        className={monoInputClassName}
                        aria-invalid={!!getFieldError('account_number')}
                      />
                      {getFieldError('account_number') && (
                        <p className="text-xs text-destructive">{getFieldError('account_number')}</p>
                      )}
                    </div>

                    <div className="space-y-2 md:col-span-2">
                      <Label htmlFor="iban">شماره شبا</Label>
                      <div className="relative">
                        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 font-mono-num text-sm text-muted-foreground">
                          IR
                        </span>
                        <Input
                          id="iban"
                          dir="ltr"
                          inputMode="numeric"
                          maxLength={24}
                          value={form.iban}
                          onChange={(event) =>
                            setFieldValue('iban', onlyDigits(event.target.value).slice(0, 24))
                          }
                          onBlur={() => handleBlur('iban')}
                          placeholder="000000000000000000000000"
                          className={cn(monoInputClassName, 'pl-10')}
                          aria-invalid={!!getFieldError('iban')}
                        />
                      </div>
                      <p className="text-xs text-muted-foreground">فرمت نهایی: IR + 24 digits</p>
                      {getFieldError('iban') && (
                        <p className="text-xs text-destructive">{getFieldError('iban')}</p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="flex justify-end">
              <Button type="submit" size="lg" className="w-full md:w-auto md:min-w-64" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="ml-2 h-4 w-4 animate-spin" />
                    در حال ثبت اطلاعات...
                  </>
                ) : (
                  'ثبت و احراز اطلاعات'
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

export default ContractorRegistration;
