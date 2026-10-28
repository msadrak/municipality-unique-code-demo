import type { LucideIcon } from 'lucide-react';
import {
  AlertTriangle,
  BarChart3,
  BriefcaseBusiness,
  Calendar,
  ClipboardCheck,
  ClipboardList,
  GitBranch,
  Home,
  Inbox,
  LayoutDashboard,
  Settings,
  ShieldCheck,
  UploadCloud,
  Users,
  Wallet,
} from 'lucide-react';

import {
  canAccessAttendanceInbox,
  canAccessCivilModule,
  canAccessFinanceWorkflow,
  canAccessHrModule,
  canAccessSecurityAggregation,
  canAccessSecurityReconciliation,
  canCreateFundingRequest,
  canSeeFundingArchive,
  canSeeFundingInbox,
  canSeeFundingMyRequests,
  canUploadContractorStatement,
  canUploadRegionalAttendance,
  isAdminRole,
} from '../components/funding/workflow';
import {
  getVolumeContractCategoryPath,
  isVolumeContractRole,
  VOLUME_CONTRACT_CATEGORIES,
  VOLUME_CONTRACT_DEFAULT_PATH,
  VOLUME_CONTRACT_ROLE_VALUES,
} from './volumeContracts';

type RoleVisibility = (role?: string | null) => boolean;

type SidebarEntryBase = {
  id: string;
  title: string;
  roles?: readonly string[];
  visible?: RoleVisibility;
};

export interface SidebarNavChildItem extends SidebarEntryBase {
  path: string;
}

export interface SidebarNavItem extends SidebarEntryBase {
  icon: LucideIcon;
  path?: string;
  defaultOpen?: boolean;
  children?: SidebarNavChildItem[];
}

export interface SidebarNavSection {
  id: string;
  title?: string;
  items: SidebarNavItem[];
}

export interface SidebarFooterItem extends SidebarEntryBase {
  icon: LucideIcon;
  path: string;
}

const civilSection: SidebarNavSection = {
  id: 'civil-module',
  title: 'ماژول عمران',
  items: [
    {
      id: 'civil-dashboard',
      title: 'تخته پروژه‌های عمرانی',
      icon: LayoutDashboard,
      path: '/civil/dashboard',
      visible: (role) => canAccessCivilModule(role),
    },
    {
      id: 'user-portal',
      title: 'پرتال کاربر',
      icon: Home,
      path: '/portal',
      visible: (role) => canAccessFinanceWorkflow(role),
    },
    {
      id: 'contracts',
      title: 'قراردادها',
      icon: FileText,
      path: '/contracts',
      visible: (role) => canAccessCivilModule(role),
    },
    {
      id: 'reports',
      title: 'گزارش‌ها',
      icon: BarChart3,
      path: '/reports',
      visible: (role) => canAccessCivilModule(role),
    },
    {
      id: 'accounting',
      title: 'مالی',
      icon: Wallet,
      path: '/accounting',
      visible: (role) => canAccessCivilModule(role),
    },
  ],
};

const preAccountingSection: SidebarNavSection = {
  id: 'pre-accounting-module',
  title: 'کنترل مالی',
  items: [
    {
      id: 'pre-accounting-package',
      title: 'بسته‌های پیش‌حسابداری',
      icon: ClipboardCheck,
      path: '/pre-accounting',
    },
  ],
};

const volumeContractsSection: SidebarNavSection = {
  id: 'volume-contracts-module',
  items: [
    {
      id: 'volume-contract-management',
      title: 'مدیریت قراردادهای حجمی',
      icon: ClipboardList,
      path: VOLUME_CONTRACT_DEFAULT_PATH,
      roles: VOLUME_CONTRACT_ROLE_VALUES,
      defaultOpen: true,
      visible: (role) => role?.toUpperCase() !== 'CONTRACTOR',
      children: VOLUME_CONTRACT_CATEGORIES.map((category, index) => ({
        id: `volume-contract-category-${index + 1}`,
        title: category,
        path: getVolumeContractCategoryPath(category),
        roles: VOLUME_CONTRACT_ROLE_VALUES,
      })),
    },
    {
      id: 'contractor-my-contracts',
      title: 'قراردادهای من',
      icon: BriefcaseBusiness,
      path: '/volume-contracts/dashboard',
      roles: ['CONTRACTOR'],
    },
  ],
};

const fundingSection: SidebarNavSection = {
  id: 'hr-funding-module',
  title: 'ماژول منابع انسانی',
  items: [
    {
      id: 'funding-new-request',
      title: 'ثبت درخواست بن',
      icon: Wallet,
      path: '/hr/funding/new',
      visible: (role) => canAccessHrModule(role) && canCreateFundingRequest(role),
    },
    {
      id: 'funding-my-requests',
      title: 'درخواست‌های من',
      icon: FileText,
      path: '/hr/funding/my-requests',
      visible: (role) => canAccessHrModule(role) && canSeeFundingMyRequests(role),
    },
    {
      id: 'funding-inbox',
      title: 'کارتابل درخواست‌ها',
      icon: Inbox,
      path: '/hr/funding/inbox',
      visible: (role) => canAccessHrModule(role) && canSeeFundingInbox(role),
    },
    {
      id: 'funding-archive',
      title: 'بایگانی نامه‌ها',
      icon: FileText,
      path: '/hr/funding/archive',
      visible: (role) => canAccessHrModule(role) && canSeeFundingArchive(role),
    },
  ],
};

const attendanceSection: SidebarNavSection = {
  id: 'attendance-module',
  title: 'ماژول حضور و غیاب',
  items: [
    {
      id: 'attendance-upload',
      title: 'بارگذاری کارکرد',
      icon: UploadCloud,
      path: '/region/attendance/upload',
      visible: (role) => canUploadRegionalAttendance(role),
    },
    {
      id: 'contractor-statement-upload',
      title: 'ارسال صورت وضعیت',
      icon: FileText,
      path: '/contractor/statement/upload',
      visible: (role) => canUploadContractorStatement(role),
    },
  ],
};

const securitySection: SidebarNavSection = {
  id: 'security-module',
  title: 'ماژول مدیریت تردد',
  items: [
    {
      id: 'security-operations',
      title: 'حفاظت فیزیکی',
      icon: ShieldCheck,
      visible: (role) => canAccessSecurityReconciliation(role) || canAccessAttendanceInbox(role),
      children: [
        {
          id: 'security-reconciliation-dashboard',
          title: 'داشبورد مغایرتگیری',
          path: '/attendance/security-reconciliation',
          visible: (role) => canAccessSecurityReconciliation(role),
        },
        {
          id: 'security-aggregation',
          title: 'صفحه تجمیع کارکرد',
          path: '/security/aggregation',
          visible: (role) => canAccessSecurityAggregation(role),
        },
        {
          id: 'attendance-inbox',
          title: 'کارتابل مستندات مناطق',
          path: '/attendance/inbox',
          visible: (role) => canAccessAttendanceInbox(role),
        },
      ],
    },
    {
      id: 'nowruz-headquarters',
      title: 'ستاد نوروزی',
      icon: Calendar,
      path: '/hr/nowruz',
      visible: (role) => canAccessSecurityReconciliation(role),
    },
    {
      id: 'war-headquarters',
      title: 'ستاد جنگ',
      icon: AlertTriangle,
      path: '/hr/war-hq',
      visible: (role) => canAccessSecurityReconciliation(role),
    },
    {
      id: 'hr-workflow',
      title: 'گردش کار',
      icon: GitBranch,
      path: '/hr/workflow',
      visible: (role) => canAccessSecurityReconciliation(role),
    },
    {
      id: 'volumetric-forces',
      title: 'نیروهای حجمی',
      icon: Users,
      path: '/hr/volumetric-forces',
      visible: (role) => canAccessSecurityReconciliation(role),
    },
  ],
};

const adminSection: SidebarNavSection = {
  id: 'admin-module',
  items: [
    {
      id: 'admin-dashboard',
      title: 'مدیریت',
      icon: Settings,
      path: '/admin',
      visible: (role) => isAdminRole(role),
    },
  ],
};

const sidebarFooterItems: SidebarFooterItem[] = [
  {
    id: 'admin-settings',
    title: 'تنظیمات',
    icon: Settings,
    path: '/admin',
    visible: (role) => isAdminRole(role),
  },
];

function hasAllowedRole(allowedRoles: readonly string[] | undefined, role?: string | null): boolean {
  if (!allowedRoles) return true;
  if (!role) return false;
  return allowedRoles.includes(role.toUpperCase());
}

function isVisibleEntry(
  item: Pick<SidebarEntryBase, 'roles' | 'visible'>,
  role?: string | null,
): boolean {
  return hasAllowedRole(item.roles, role) && (!item.visible || item.visible(role));
}

function filterChildItem(
  child: SidebarNavChildItem,
  role?: string | null,
): SidebarNavChildItem | null {
  return isVisibleEntry(child, role) ? { ...child } : null;
}

function filterNavItem(
  item: SidebarNavItem,
  role?: string | null,
): SidebarNavItem | null {
  if (!isVisibleEntry(item, role)) return null;

  const children = item.children
    ?.map((child) => filterChildItem(child, role))
    .filter((child): child is SidebarNavChildItem => child !== null);

  if (!item.path && (!children || children.length === 0)) {
    return null;
  }

  return {
    ...item,
    children,
  };
}

export function resolveSidebarSections(role?: string | null): SidebarNavSection[] {
  const normalizedRole = role?.toUpperCase();
  const sections = [
    ...(isVolumeContractRole(role) || normalizedRole === 'CONTRACTOR'
      ? [volumeContractsSection, preAccountingSection]
      : [civilSection, preAccountingSection]),
    ...(isAdminRole(role) ? [adminSection] : []),
    ...(canAccessHrModule(role) ? [fundingSection] : []),
    attendanceSection,
    ...(canAccessSecurityAggregation(role) || canAccessSecurityReconciliation(role) ? [securitySection] : []),
  ];

  return sections
    .map((section) => ({
      ...section,
      items: section.items
        .map((item) => filterNavItem(item, role))
        .filter((item): item is SidebarNavItem => item !== null),
    }))
    .filter((section) => section.items.length > 0);
}

export function resolveSidebarFooterItems(role?: string | null): SidebarFooterItem[] {
  return sidebarFooterItems.filter((item) => isVisibleEntry(item, role));
}
