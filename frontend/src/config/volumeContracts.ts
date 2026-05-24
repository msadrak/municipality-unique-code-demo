export const VOLUME_CONTRACT_DASHBOARD_PATH = "/volume-contracts/dashboard";
export const VOLUME_CONTRACT_DETAIL_PATH = "/volume-contracts";

export const VOLUME_CONTRACT_ROLE_VALUES = [
  "HR_ADMIN",
  "FINANCE_MANAGER",
  "YEKTA_ADMIN",
] as const;

export const VOLUME_CONTRACT_CATEGORIES = [
  "نظافت و پذیرایی",
  "مجموعه تخت فولاد",
  "ویلاهای چادگان",
  "ویلاهای چابکسر",
  "مجموعه هشت بهشت",
  "زائرسرای مشهد",
  "ترابری و لجستیک",
  "ساختمان خانه مطبوعات",
  "ساماندهی اتباع خارجی",
  "خدمات پیرایشگری",
  "حفاظت فیزیکی",
] as const;

export const VOLUME_CONTRACT_DEFAULT_PATH = `${VOLUME_CONTRACT_DASHBOARD_PATH}?category=${VOLUME_CONTRACT_CATEGORIES[0]}`;

export function getVolumeContractCategoryPath(category: string): string {
  return `${VOLUME_CONTRACT_DASHBOARD_PATH}?category=${category}`;
}

export function isVolumeContractRole(role?: string | null): boolean {
  return (
    !!role &&
    VOLUME_CONTRACT_ROLE_VALUES.includes(
      role.toUpperCase() as (typeof VOLUME_CONTRACT_ROLE_VALUES)[number],
    )
  );
}
