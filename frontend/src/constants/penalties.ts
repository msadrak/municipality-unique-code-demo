export interface PenaltyDefinition {
  id: number;
  title: string;
  unitAmount: number;
}

export const PENALTY_OPTIONS: PenaltyDefinition[] = [
  { id: 1, title: 'عدم استفاده از البسه و کفش', unitAmount: 500000 },
  { id: 2, title: 'غیبت یا ترک پست', unitAmount: 500000 },
  { id: 3, title: 'تاخیر در پرداخت حق بیمه (روزانه)', unitAmount: 1500000 },
];
