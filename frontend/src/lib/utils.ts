const FA_INT = new Intl.NumberFormat('fa-IR');
const FA_DEC = new Intl.NumberFormat('fa-IR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
});

/**
 * Canonical currency formatter for the entire application.
 * Returns Persian-digit comma-separated value with ریال suffix.
 * Use the `font-mono-num` CSS class on the wrapping element for tabular alignment.
 */
export function formatRial(amount: number | null | undefined): string {
    if (amount == null || isNaN(amount)) return '۰ ریال';
    return `${FA_INT.format(amount)} ریال`;
}

/**
 * Format a number with Persian digits and comma separators (no currency suffix).
 * Useful for inline figures where the suffix is rendered separately.
 */
export function formatNumber(amount: number | null | undefined): string {
    if (amount == null || isNaN(amount)) return '۰';
    return FA_INT.format(amount);
}

/**
 * Abbreviated format for dashboard KPI cards.
 * >= 1 billion  -> "X.Y میلیارد"
 * >= 1 million  -> "X.Y میلیون"
 * else          -> comma-separated
 */
export function formatAmountAbbreviated(value: number): string {
    const absoluteValue = Math.abs(value);

    if (absoluteValue >= 1_000_000_000) {
        return `${FA_DEC.format(value / 1_000_000_000)} میلیارد`;
    }

    if (absoluteValue >= 1_000_000) {
        return `${FA_DEC.format(value / 1_000_000)} میلیون`;
    }

    return FA_INT.format(value);
}

export function getTodayJalaliDate(): string {
    return new Intl.DateTimeFormat('fa-IR-u-ca-persian', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
    }).format(new Date());
}
