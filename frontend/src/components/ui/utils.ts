import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export { formatRial, formatNumber, formatAmountAbbreviated } from '../../lib/utils';

/** Alias kept for backward-compat: delegates to the canonical formatRial */
export { formatRial as formatTooltipAmount } from '../../lib/utils';

export function getJalaliToday(): string {
  return new Date().toLocaleDateString('fa-IR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}
