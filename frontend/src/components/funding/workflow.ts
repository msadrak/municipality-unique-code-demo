import {
  VOLUME_CONTRACT_DEFAULT_PATH,
  VOLUME_CONTRACT_ROLE_VALUES,
} from "../../config/volumeContracts";

export type FundingActionButton = {
  label: string;
  action: string;
  variant: "success" | "danger" | "primary";
};

const SYSTEM_ADMIN_PREFIXES = ["ADMIN_L"];

const HR_ROLES = new Set([
  "GM_HC",
  "VP_PLANNING",
  "VP_FINANCE",
  "WELFARE_DEPT",
  "FINANCE_UNIT",
  "GM_FINANCE",
  "ISFAHAN_CARD",
]);

const ATTENDANCE_ROLES = new Set([
  "REGION_USER",
  "SECURITY_AGGREGATOR",
  "CONTRACTOR",
  "SECURITY_DIRECTOR",
  "PAYROLL_MANAGER",
  "OPERATOR",
  "HR_ADMIN",
]);

const REGION_UPLOAD_ROLES = new Set(["REGION_USER", "OPERATOR"]);
const CONTRACTOR_UPLOAD_ROLES = new Set(["CONTRACTOR"]);
const SECURITY_AGGREGATION_ROLES = new Set([
  "SECURITY_AGGREGATOR",
  "PAYROLL_MANAGER",
]);
const SECURITY_RECONCILIATION_ROLES = new Set(["SECURITY_DIRECTOR"]);
const VOLUME_CONTRACT_ROLES = new Set(VOLUME_CONTRACT_ROLE_VALUES);

export const STATUS_LABELS: Record<string, string> = {
  PENDING_VP_PLANNING: "در انتظار تایید معاون برنامه‌ریزی",
  PENDING_VP_FINANCE_REVIEW: "در انتظار بررسی معاون مالی",
  BUDGET_WELFARE_DEPT: "تخصیص بودجه - اداره رفاه",
  BUDGET_GM_HC: "تخصیص بودجه - مدیرکل سرمایه انسانی",
  BUDGET_FINANCE_UNIT: "تخصیص بودجه - واحد مالی",
  BUDGET_VP_FINANCE: "تخصیص بودجه - معاون مالی",
  CHARGE_LETTER_REGISTERED: "نامه شارژ ثبت شده",
  PENDING_FINAL_CHARGE: "در انتظار دستور شارژ نهایی",
  FINAL_APPROVED: "تایید نهایی - در انتظار اجرا",
  CHARGING_IN_PROGRESS: "در حال شارژ",
  COMPLETED: "تکمیل شده",
  REJECTED: "رد شده",
  DRAFT: "پیش‌نویس قدیمی",
  PENDING_VP_FINANCE_INITIAL: "مسیر قدیمی - بررسی اولیه مالی",
  PENDING_BUDGET_ALLOCATION: "مسیر قدیمی - تخصیص بودجه",
  PENDING_VP_FINANCE_FINAL: "مسیر قدیمی - تایید نهایی مالی",
  APPROVED_FOR_CHARGE: "مسیر قدیمی - آماده شارژ",
};

export const ROLE_LABELS: Record<string, string> = {
  REGION_USER: "کاربر منطقه",
  SECURITY_AGGREGATOR: "تجمیع کارکرد مناطق",
  CONTRACTOR: "پیمانکار",
  SECURITY_DIRECTOR: "مدیر سیستم منابع انسانی",
  GM_HC: "مدیرکل سرمایه انسانی",
  VP_PLANNING: "معاون برنامه‌ریزی",
  VP_FINANCE: "معاون مالی",
  WELFARE_DEPT: "اداره رفاه",
  FINANCE_UNIT: "واحد مالی",
  GM_FINANCE: "مدیرکل امور مالی",
  ISFAHAN_CARD: "اصفهان کارت",
  PAYROLL_MANAGER: "مدیر حقوق و دستمزد",
  OPERATOR: "اپراتور",
  HR_ADMIN: "کارشناس حضور و غیاب",
  ADMIN: "ادمین سیستم",
  CIVIL_MANAGER: "مدیر عمران",
  FINANCE_MANAGER: "مدیر مالی",
  YEKTA_ADMIN: "مدیر کد یکتا",
  TENDERING_OFFICER: "مسئول مناقصات",
  CONTRACTS_OFFICER: "مسئول قراردادها",
  DELIVERY_COMMISSION: "کمیسیون تحویل",
  SUPERVISOR: "ناظر مقیم",
  MAYOR: "شهردار",
  SECURITY: "حراست",
  COUNCIL: "شورا",
  DESIGN_ORG: "سازمان طراحی",
  REGION_MANAGER: "مدیر منطقه",
};

const ACTION_MAP: Record<string, Record<string, FundingActionButton[]>> = {
  VP_PLANNING: {
    PENDING_VP_PLANNING: [
      { label: "تایید", action: "approve", variant: "success" },
      { label: "رد", action: "reject", variant: "danger" },
    ],
  },
  VP_FINANCE: {
    PENDING_VP_FINANCE_REVIEW: [
      {
        label: "تایید و ارجاع به بودجه",
        action: "approve",
        variant: "success",
      },
      { label: "رد", action: "reject", variant: "danger" },
    ],
    BUDGET_VP_FINANCE: [
      { label: "تایید تخصیص بودجه", action: "approve", variant: "success" },
      { label: "رد", action: "reject", variant: "danger" },
    ],
    PENDING_FINAL_CHARGE: [
      { label: "صدور دستور شارژ نهایی", action: "approve", variant: "success" },
      { label: "رد", action: "reject", variant: "danger" },
    ],
  },
  WELFARE_DEPT: {
    BUDGET_WELFARE_DEPT: [
      { label: "تایید بودجه رفاه", action: "approve", variant: "success" },
      { label: "رد", action: "reject", variant: "danger" },
    ],
  },
  GM_HC: {
    BUDGET_GM_HC: [
      { label: "تایید", action: "approve", variant: "success" },
      { label: "رد", action: "reject", variant: "danger" },
    ],
    CHARGE_LETTER_REGISTERED: [
      {
        label: "ثبت درخواست شارژ نهایی",
        action: "register",
        variant: "primary",
      },
    ],
  },
  FINANCE_UNIT: {
    BUDGET_FINANCE_UNIT: [
      { label: "تایید", action: "approve", variant: "success" },
      { label: "رد", action: "reject", variant: "danger" },
    ],
  },
  ISFAHAN_CARD: {
    FINAL_APPROVED: [
      { label: "شروع شارژ", action: "execute", variant: "primary" },
    ],
    CHARGING_IN_PROGRESS: [
      { label: "اتمام شارژ", action: "complete", variant: "success" },
    ],
  },
  ADMIN: {
    PENDING_VP_PLANNING: [
      { label: "تایید", action: "approve", variant: "success" },
      { label: "رد", action: "reject", variant: "danger" },
    ],
    PENDING_VP_FINANCE_REVIEW: [
      {
        label: "تایید و ارجاع به بودجه",
        action: "approve",
        variant: "success",
      },
      { label: "رد", action: "reject", variant: "danger" },
    ],
    BUDGET_WELFARE_DEPT: [
      { label: "تایید بودجه رفاه", action: "approve", variant: "success" },
      { label: "رد", action: "reject", variant: "danger" },
    ],
    BUDGET_GM_HC: [
      { label: "تایید", action: "approve", variant: "success" },
      { label: "رد", action: "reject", variant: "danger" },
    ],
    BUDGET_FINANCE_UNIT: [
      { label: "تایید", action: "approve", variant: "success" },
      { label: "رد", action: "reject", variant: "danger" },
    ],
    BUDGET_VP_FINANCE: [
      { label: "تایید تخصیص بودجه", action: "approve", variant: "success" },
      { label: "رد", action: "reject", variant: "danger" },
    ],
    CHARGE_LETTER_REGISTERED: [
      {
        label: "ثبت درخواست شارژ نهایی",
        action: "register",
        variant: "primary",
      },
    ],
    PENDING_FINAL_CHARGE: [
      { label: "صدور دستور شارژ نهایی", action: "approve", variant: "success" },
      { label: "رد", action: "reject", variant: "danger" },
    ],
    FINAL_APPROVED: [
      { label: "شروع شارژ", action: "execute", variant: "primary" },
    ],
    CHARGING_IN_PROGRESS: [
      { label: "اتمام شارژ", action: "complete", variant: "success" },
    ],
  },
};

export function isAdminRole(role?: string | null): boolean {
  if (!role) return false;
  return (
    role === "admin" ||
    role === "ADMIN" ||
    SYSTEM_ADMIN_PREFIXES.some((prefix) => role.startsWith(prefix))
  );
}

export function normalizeFundingRole(role?: string | null): string | undefined {
  if (!role) return undefined;
  if (isAdminRole(role)) return "ADMIN";
  return role.toUpperCase();
}

export function isHrRole(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized || normalized === "ADMIN") return false;
  return HR_ROLES.has(normalized);
}

export function canAccessHrModule(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized) return false;
  return normalized === "ADMIN" || HR_ROLES.has(normalized);
}

export function canAccessCivilModule(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized) return false;
  return (
    normalized === "ADMIN" ||
    (!HR_ROLES.has(normalized) &&
      !ATTENDANCE_ROLES.has(normalized) &&
      !VOLUME_CONTRACT_ROLES.has(normalized))
  );
}

export function canAccessCivilProjectScreens(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized) return false;
  return (
    normalized === "ADMIN" ||
    (canAccessCivilModule(role) && !VOLUME_CONTRACT_ROLES.has(normalized))
  );
}

export function canAccessVolumeContractsModule(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized) return false;
  return (
    normalized === "ADMIN" ||
    normalized === "CONTRACTOR" ||
    VOLUME_CONTRACT_ROLES.has(normalized)
  );
}

export function canAccessFinanceWorkflow(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized) return false;
  return normalized === "SECURITY_DIRECTOR" || canAccessCivilModule(role);
}

export function canAccessAttendanceModule(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized) return false;
  return normalized === "ADMIN" || ATTENDANCE_ROLES.has(normalized);
}

export function canUploadRegionalAttendance(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized) return false;
  return normalized === "ADMIN" || REGION_UPLOAD_ROLES.has(normalized);
}

export function canUploadContractorStatement(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized) return false;
  return normalized === "ADMIN" || CONTRACTOR_UPLOAD_ROLES.has(normalized);
}

export function canAccessAttendanceInbox(role?: string | null): boolean {
  return canAccessAttendanceModule(role);
}

export function canAccessAttendanceAggregationDashboard(
  role?: string | null,
): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized) return false;
  return (
    normalized === "ADMIN" ||
    SECURITY_AGGREGATION_ROLES.has(normalized) ||
    SECURITY_RECONCILIATION_ROLES.has(normalized)
  );
}

export function canAccessSecurityAggregation(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized) return false;
  return normalized === "ADMIN" || SECURITY_AGGREGATION_ROLES.has(normalized);
}

export function canAccessSecurityReconciliation(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized) return false;
  return (
    normalized === "ADMIN" || SECURITY_RECONCILIATION_ROLES.has(normalized)
  );
}

export function canTransitionAttendanceSheet(
  role?: string | null,
  status?: string | null,
): boolean {
  const normalized = normalizeFundingRole(role);
  if (!normalized || !status) return false;
  if (normalized === "ADMIN") return true;

  const statusRoleMap: Record<string, Set<string>> = {
    DRAFT: REGION_UPLOAD_ROLES,
    NEEDS_CORRECTION: REGION_UPLOAD_ROLES,
    CREATOR_APPROVED: CONTRACTOR_UPLOAD_ROLES,
    COMPANY_REP_APPROVED: SECURITY_AGGREGATION_ROLES,
    SECURITY_APPROVED: SECURITY_RECONCILIATION_ROLES,
  };

  return statusRoleMap[status]?.has(normalized) ?? false;
}

export function getDefaultHomePath(role?: string | null): string {
  const normalized = normalizeFundingRole(role);

  if (normalized && VOLUME_CONTRACT_ROLES.has(normalized))
    return VOLUME_CONTRACT_DEFAULT_PATH;

  if (normalized === "REGION_USER" || normalized === "OPERATOR")
    return "/region/attendance/upload";
  if (normalized === "CONTRACTOR") return "/contractor/statement/upload";
  if (normalized === "SECURITY_AGGREGATOR" || normalized === "PAYROLL_MANAGER")
    return "/security/aggregation";
  if (normalized === "SECURITY_DIRECTOR")
    return "/attendance/security-reconciliation";

  if (canAccessHrModule(role) && !canAccessCivilModule(role)) {
    return canSeeFundingInbox(role)
      ? "/hr/funding/inbox"
      : "/hr/funding/my-requests";
  }

  if (canAccessCivilModule(role) && !isAdminRole(role)) {
    return "/civil/dashboard";
  }

  if (isAdminRole(role)) {
    return "/admin";
  }
  return "/portal";
}

export function canCreateFundingRequest(role?: string | null): boolean {
  const normalized = normalizeFundingRole(role);
  return normalized === "GM_HC" || normalized === "ADMIN";
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
    "ADMIN",
    "GM_HC",
    "VP_PLANNING",
    "VP_FINANCE",
    "WELFARE_DEPT",
    "FINANCE_UNIT",
    "GM_FINANCE",
    "ISFAHAN_CARD",
  ]).has(normalized);
}

export function getRoleDisplayName(role?: string | null): string {
  const normalized = normalizeFundingRole(role);
  if (normalized && ROLE_LABELS[normalized]) {
    return ROLE_LABELS[normalized];
  }
  if (role === "user") {
    return "کاربر سامانه";
  }
  return role || "کاربر";
}

export function getFundingActions(
  role?: string | null,
  status?: string | null,
): FundingActionButton[] {
  const normalized = normalizeFundingRole(role);
  if (!normalized || !status) return [];
  return ACTION_MAP[normalized]?.[status] || [];
}

export function getFundingStatusLabel(status?: string | null): string {
  if (!status) return "-";
  return STATUS_LABELS[status] || status;
}
