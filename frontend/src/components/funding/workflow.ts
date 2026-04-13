export type FundingActionButton = {
  label: string;
  action: string;
  variant: 'success' | 'danger' | 'primary';
};

const SYSTEM_ADMIN_PREFIXES = ['ADMIN_L'];
const HR_ROLES = new Set([
  'GM_HC',
  'VP_PLANNING',
  'VP_FINANCE',
  'WELFARE_DEPT',
  'FINANCE_UNIT',
  'GM_FINANCE',
  'ISFAHAN_CARD',
  'SECURITY_DIRECTOR',
  'PAYROLL_MANAGER',
  'OPERATOR',
  'HR_ADMIN',
]);
const ATTENDANCE_ROLES = new Set([
  'SECURITY_DIRECTOR',
  'PAYROLL_MANAGER',
  'OPERATOR',
  'HR_ADMIN',
]);

export const STATUS_LABELS: Record<string, string> = {
  PENDING_VP_PLANNING: 'در انتظار تایید معاون برنامه‌ریزی',
  PENDING_VP_FINANCE_REVIEW: 'در انتظار بررسی معاون مالی',
  BUDGET_WELFARE_DEPT: 'تخصیص بودجه - اداره رفاه',
  BUDGET_GM_HC: 'تخصیص بودجه - مدیرکل سرمایه انسانی',
  BUDGET_FINANCE_UNIT: 'تخصیص بودجه - واحد مالی',
  BUDGET_VP_FINANCE: 'تخصیص بودجه - معاون مالی',
  CHARGE_LETTER_REGISTERED: 'نامه شارژ ثبت شده',
  PENDING_FINAL_CHARGE: 'در انتظار دستور شارژ نهایی',
  FINAL_APPROVED: 'تایید نهایی - در انتظار اجرا',
  CHARGING_IN_PROGRESS: 'در حال شارژ',
  COMPLETED: 'تکمیل شده',
  REJECTED: 'رد شده',
  DRAFT: 'پیش‌نویس قدیمی',
  PENDING_VP_FINANCE_INITIAL: 'مسیر قدیمی - بررسی اولیه مالی',
  PENDING_BUDGET_ALLOCATION: 'مسیر قدیمی - تخصیص بودجه',
  PENDING_VP_FINANCE_FINAL: 'مسیر قدیمی - تایید نهایی مالی',
  APPROVED_FOR_CHARGE: 'مسیر قدیمی - آماده شارژ',
};

export const ROLE_LABELS: Record<string, string> = {
  GM_HC: 'مدیرکل سرمایه انسانی',
  VP_PLANNING: 'معاون برنامه‌ریزی',
  VP_FINANCE: 'معاون مالی',
  WELFARE_DEPT: 'اداره رفاه',
  FINANCE_UNIT: 'واحد مالی',
  GM_FINANCE: 'مدیرکل امور مالی',
  ISFAHAN_CARD: 'اصفهان کارت',
  SECURITY_DIRECTOR: 'مدیر حراست',
  PAYROLL_MANAGER: 'مدیر حقوق و دستمزد',
  OPERATOR: 'اپراتور',
  ADMIN: 'ادمین سیستم',
};

const ACTION_MAP: Record<string, Record<string, FundingActionButton[]>> = {
  VP_PLANNING: {
    PENDING_VP_PLANNING: [
      { label: 'تایید', action: 'approve', variant: 'success' },
      { label: 'رد', action: 'reject', variant: 'danger' },
    ],
  },
  VP_FINANCE: {
    PENDING_VP_FINANCE_REVIEW: [
      { label: 'تایید و ارجاع به بودجه', action: 'approve', variant: 'success' },
      { label: 'رد', action: 'reject', variant: 'danger' },
    ],
    BUDGET_VP_FINANCE: [
      { label: 'تایید تخصیص بودجه', action: 'approve', variant: 'success' },
      { label: 'رد', action: 'reject', variant: 'danger' },
    ],
    PENDING_FINAL_CHARGE: [
      { label: 'صدور دستور شارژ نهایی', action: 'approve', variant: 'success' },
      { label: 'رد', action: 'reject', variant: 'danger' },
    ],
  },
  WELFARE_DEPT: {
    BUDGET_WELFARE_DEPT: [
      { label: 'تایید بودجه رفاه', action: 'approve', variant: 'success' },
      { label: 'رد', action: 'reject', variant: 'danger' },
    ],
  },
  GM_HC: {
    BUDGET_GM_HC: [
      { label: 'تایید', action: 'approve', variant: 'success' },
      { label: 'رد', action: 'reject', variant: 'danger' },
    ],
    CHARGE_LETTER_REGISTERED: [
      { label: 'ثبت درخواست شارژ نهایی', action: 'register', variant: 'primary' },
    ],
  },
  FINANCE_UNIT: {
    BUDGET_FINANCE_UNIT: [
      { label: 'تایید', action: 'approve', variant: 'success' },
      { label: 'رد', action: 'reject', variant: 'danger' },
    ],
  },
  ISFAHAN_CARD: {
    FINAL_APPROVED: [
      { label: 'شروع شارژ', action: 'execute', variant: 'primary' },
    ],
    CHARGING_IN_PROGRESS: [
      { label: 'اتمام شارژ', action: 'complete', variant: 'success' },
    ],
  },
  ADMIN: {
    PENDING_VP_PLANNING: [
      { label: 'تایید', action: 'approve', variant: 'success' },
      { label: 'رد', action: 'reject', variant: 'danger' },
    ],
    PENDING_VP_FINANCE_REVIEW: [
      { label: 'تایید و ارجاع به بودجه', action: 'approve', variant: 'success' },
      { label: 'رد', action: 'reject', variant: 'danger' },
    ],
    BUDGET_WELFARE_DEPT: [
      { label: 'تایید بودجه رفاه', action: 'approve', variant: 'success' },
      { label: 'رد', action: 'reject', variant: 'danger' },
    ],
    BUDGET_GM_HC: [
      { label: 'تایید', action: 'approve', variant: 'success' },
      { label: 'رد', action: 'reject', variant: 'danger' },
    ],
    BUDGET_FINANCE_UNIT: [
      { label: 'تایید', action: 'approve', variant: 'success' },
      { label: 'رد', action: 'reject', variant: 'danger' },
    ],
    BUDGET_VP_FINANCE: [
      { label: 'تایید تخصیص بودجه', action: 'approve', variant: 'success' },
      { label: 'رد', action: 'reject', variant: 'danger' },
    ],
    CHARGE_LETTER_REGISTERED: [
      { label: 'ثبت درخواست شارژ نهایی', action: 'register', variant: 'primary' },
    ],
    PENDING_FINAL_CHARGE: [
      { label: 'صدور دستور شارژ نهایی', action: 'approve', variant: 'success' },
      { label: 'رد', action: 'reject', variant: 'danger' },
    ],
    FINAL_APPROVED: [
      { label: 'شروع شارژ', action: 'execute', variant: 'primary' },
    ],
    CHARGING_IN_PROGRESS: [
      { label: 'اتمام شارژ', action: 'complete', variant: 'success' },
    ],
  },
};

export function isAdminRole(role?: string | null): boolean {
  if (!role) return false;
  return role === 'admin' || role === 'ADMIN' || SYSTEM_ADMIN_PREFIXES.some((prefix) => role.startsWith(prefix));
}

export function normalizeFundingRole(role?: string | null): string | undefined {
  if (!role) return undefined;
  if (isAdminRole(role)) return 'ADMIN';
  return role.toUpperCase();
}

export function isHrRole(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized || normalized === 'ADMIN') return false;
  return HR_ROLES.has(normalized);
}

export function canAccessHrModule(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized) return false;
  return normalized === 'ADMIN' || HR_ROLES.has(normalized);
}

export function canAccessCivilModule(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized) return false;
  return normalized === 'ADMIN' || !HR_ROLES.has(normalized);
}

export function canAccessAttendanceModule(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized) return false;
  return normalized === 'ADMIN' || ATTENDANCE_ROLES.has(normalized);
}

export function canAccessAttendanceAggregationDashboard(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized) return false;
  return normalized === 'ADMIN' || normalized === 'SECURITY_DIRECTOR';
}

export function getDefaultHomePath(role?: string | null): string {
  const normalized = normalizeFundingRole(role);
  
  // Specific redirects for Attendance domain
  if (normalized === 'OPERATOR') return '/attendance/inbox';
  if (normalized === 'SECURITY_DIRECTOR') return '/security/reconciliation';

  if (canAccessHrModule(role) && !canAccessCivilModule(role)) {
    return canSeeFundingInbox(role) ? '/hr/funding/inbox' : '/hr/funding/my-requests';
  }
  if (isAdminRole(role)) {
    return '/admin';
  }
  return '/portal';
}

export function canCreateFundingRequest(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  return normalized === 'GM_HC' || normalized === 'ADMIN';
}

export function canSeeFundingInbox(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized) return false;
  return normalized in ACTION_MAP;
}

export function canSeeFundingMyRequests(role?: string | null): boolean {
  return canAccessHrModule(role);
}

export function canSeeFundingArchive(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized) return false;
  return new Set([
    'ADMIN',
    'GM_HC',
    'VP_PLANNING',
    'VP_FINANCE',
    'WELFARE_DEPT',
    'FINANCE_UNIT',
    'GM_FINANCE',
    'ISFAHAN_CARD',
  ]).has(normalized);
}

export function getRoleDisplayName(role?: string | null): string {
  const normalized = normalizeFundingRole(role);
  if (normalized && ROLE_LABELS[normalized]) {
    return ROLE_LABELS[normalized];
  }
  if (role === 'user') {
    return 'کاربر سامانه';
  }
  return role || 'کاربر';
}

export function getFundingActions(role?: string | null, status?: string | null): FundingActionButton[] {
  const normalized = normalizeFundingRole(role);
  if (!normalized || !status) return [];
  return ACTION_MAP[normalized]?.[status] || [];
}

export function getFundingStatusLabel(status?: string | null): string {
  if (!status) return '-';
  return STATUS_LABELS[status] || status;
}
