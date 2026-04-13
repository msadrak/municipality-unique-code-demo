export type FinancialEventOption = {
  value: string;
  label: string;
};

export const FINANCIAL_EVENTS: FinancialEventOption[] = [
  { value: 'guarantee_receipt', label: 'دریافت تضامین' },
  {
    value: 'guarantee_prepayment',
    label: 'دریافت تضامین و پرداخت پیش پرداخت',
  },
  { value: 'violations_fines', label: 'تخلفات و جرایم' },
  { value: 'delay_penalty', label: 'جریمه تاخیر' },
  { value: 'contractor_debt_payment', label: 'پرداخت بدهی توسط پیمانکار' },
  {
    value: 'temporary_statement_payment',
    label: 'پرداخت صورت وضعیت موقت',
  },
  { value: 'statement_payment', label: 'پرداخت صورت وضعیت' },
  {
    value: 'final_statement_payment',
    label: 'پرداخت صورت وضعیت قطعی',
  },
  { value: 'guarantee_release', label: 'آزاد سازی تضامین' },
  {
    value: 'equipment_supply_payment',
    label: 'پرداخت هزینه تامین تجهیزات',
  },
];