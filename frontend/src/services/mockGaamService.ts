export type GaamStatus = 'VERIFIED' | 'PENDING_DOCS' | 'BLACKLISTED';

export interface GaamValidationResult {
  status: GaamStatus;
  message: string;
  missingDocs?: string[];
}

export async function validateContractorInGaam(
  nationalId: string,
): Promise<GaamValidationResult> {
  await new Promise((resolve) => setTimeout(resolve, 1000));

  const lastChar = nationalId.slice(-1);

  if (lastChar === '0' || lastChar === '1') {
    return {
      status: 'BLACKLISTED',
      message: 'خطا: پیمانکار در لیست سیاه سامانه گام قرار دارد.',
    };
  }

  if (lastChar === '2' || lastChar === '3') {
    return {
      status: 'PENDING_DOCS',
      message: 'هشدار: مدارک پیمانکار ناقص است.',
      missingDocs: ['ضمانت‌نامه حسن انجام تعهدات', 'مفاصا حساب مالیاتی'],
    };
  }

  return {
    status: 'VERIFIED',
    message: 'پیمانکار مجاز و تایید شده است.',
  };
}
