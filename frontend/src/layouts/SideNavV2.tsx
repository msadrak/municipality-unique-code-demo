import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  BarChart3,
  ChevronLeft,
  ChevronRight,
  FileText,
  Home,
  Inbox,
  LogOut,
  Settings,
  ShieldAlert,
  ShieldCheck,
  UploadCloud,
  Wallet,
} from 'lucide-react';

import { useAuthStore } from '../stores/useAuthStore';
import { useUIStore } from '../stores/useUIStore';
import {
  canAccessAttendanceAggregationDashboard,
  canAccessAttendanceModule,
  canAccessCivilModule,
  canAccessHrModule,
  canSeeFundingArchive,
  canCreateFundingRequest,
  canSeeFundingInbox,
  canSeeFundingMyRequests,
  getRoleDisplayName,
  isAdminRole,
} from '../components/funding/workflow';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../components/ui/tooltip';
import { cn } from '../components/ui/utils';

interface NavItem {
  title: string;
  icon: React.ElementType;
  path: string;
  visible?: (role?: string | null) => boolean;
}

interface NavSection {
  title?: string;
  items: NavItem[];
}

const baseSections: NavSection[] = [
  {
    title: 'عمران',
    items: [
      {
        title: 'پرتال کاربر',
        icon: Home,
        path: '/portal',
        visible: (role) => canAccessCivilModule(role),
      },
      {
        title: 'قراردادها',
        icon: FileText,
        path: '/contracts',
        visible: (role) => canAccessCivilModule(role),
      },
      {
        title: 'گزارش‌ها',
        icon: BarChart3,
        path: '/reports',
        visible: (role) => canAccessCivilModule(role),
      },
      {
        title: 'مالی',
        icon: Wallet,
        path: '/accounting',
        visible: (role) => canAccessCivilModule(role),
      },
    ],
  },
];

const fundingSection: NavSection = {
  title: 'منابع انسانی',
  items: [
    {
      title: 'ثبت درخواست بن',
      icon: Wallet,
      path: '/hr/funding/new',
      visible: (role) => canAccessHrModule(role) && canCreateFundingRequest(role),
    },
    {
      title: 'درخواست‌های من',
      icon: FileText,
      path: '/hr/funding/my-requests',
      visible: (role) => canAccessHrModule(role) && canSeeFundingMyRequests(role),
    },
    {
      title: 'کارتابل درخواست‌ها',
      icon: Inbox,
      path: '/hr/funding/inbox',
      visible: (role) => canAccessHrModule(role) && canSeeFundingInbox(role),
    },
    {
      title: 'بایگانی نامه‌ها',
      icon: FileText,
      path: '/hr/funding/archive',
      visible: (role) => canAccessHrModule(role) && canSeeFundingArchive(role),
    },
  ],
};

const attendanceSection: NavSection = {
  title: 'کارکرد مناطق',
  items: [
    {
      title: 'بارگذاری کارکرد',
      icon: UploadCloud,
      path: '/region/attendance/upload',
      visible: (role) => canAccessAttendanceModule(role),
    },
    {
      title: 'ارسال صورت وضعیت',
      icon: FileText,
      path: '/contractor/statement/upload',
      visible: (role) => canAccessAttendanceModule(role),
    },
    {
      title: 'کارتابل شیت‌ها',
      icon: ShieldCheck,
      path: '/attendance/inbox',
      visible: (role) => canAccessAttendanceModule(role),
    },
    {
      title: 'داشبورد تطبیق و مغایرت',
      icon: ShieldAlert,
      path: '/security/reconciliation',
      visible: (role) => canAccessAttendanceAggregationDashboard(role),
    },
    {
      title: 'داشبورد تجمیعی حراست',
      icon: BarChart3,
      path: '/security/aggregation',
      visible: (role) => canAccessAttendanceAggregationDashboard(role),
    },
  ],
};

const adminSection: NavSection = {
  items: [{ title: 'مدیریت', icon: Settings, path: '/admin' }],
};

export function SideNavV2() {
  const { user, logout } = useAuthStore();
  const { isSidebarExpanded, toggleSidebar } = useUIStore();
  const navigate = useNavigate();
  const location = useLocation();
  const currentRole = user?.role;

  const sections = [
    ...baseSections.map((section) => ({
      ...section,
      items: section.items.filter((item) => !item.visible || item.visible(currentRole)),
    })),
    ...(isAdminRole(currentRole) ? [adminSection] : []),
    ...(canAccessHrModule(currentRole)
      ? [
        {
          ...fundingSection,
          items: fundingSection.items.filter((item) => !item.visible || item.visible(currentRole)),
        },
      ]
      : []),
    ...(canAccessAttendanceModule(currentRole)
      ? [
        {
          ...attendanceSection,
          items: attendanceSection.items.filter((item) => !item.visible || item.visible(currentRole)),
        },
      ]
      : []),
  ].filter((section) => section.items.length > 0);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(`${path}/`);

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          'flex min-h-screen flex-shrink-0 flex-col justify-between transition-all duration-300 ease-in-out',
          'bg-[var(--vault-bg)] text-[var(--vault-on-surface)] border-l border-[var(--vault-surface-highest)]',
          isSidebarExpanded ? 'w-72 p-6' : 'w-20 p-4'
        )}
      >
        <div className="flex flex-col gap-8">
          <div className="flex items-center justify-between">
            <div className={cn("flex items-center gap-4 px-2 overflow-hidden transition-all duration-300", !isSidebarExpanded && "w-0 opacity-0 px-0")}>
              <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-3xl bg-[var(--vault-primary)]/10 text-[var(--vault-primary)] glass-vault shadow-[0_0_15px_rgba(137,206,255,0.1)]">
                <Home className="h-6 w-6" />
              </div>
              <div className="flex flex-col whitespace-nowrap">
                <h1 className="text-base font-bold leading-tight text-[var(--vault-on-surface)]">منابع انسانی</h1>
                <p className="text-sm text-[var(--vault-on-surface-variant)]">شهرداری مرکزی</p>
              </div>
            </div>

            <button
              onClick={() => toggleSidebar()}
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--vault-surface-high)] text-[var(--vault-on-surface-variant)] transition-all hover:bg-[var(--vault-surface-highest)] hover:text-[var(--vault-primary)]",
                !isSidebarExpanded && "mx-auto"
              )}
            >
              {isSidebarExpanded ? <ChevronRight className="h-5 w-5" /> : <ChevronLeft className="h-5 w-5" />}
            </button>
          </div>

          <nav className="flex flex-col gap-8">
            {sections.map((section, sectionIndex) => (
              <div key={section.title ?? `section-${sectionIndex}`} className="flex flex-col gap-3">
                {section.title && isSidebarExpanded ? (
                  <div className="px-4 text-[10px] uppercase font-bold tracking-[0.1em] text-[var(--vault-on-surface-variant)]/50 whitespace-nowrap">
                    {section.title}
                  </div>
                ) : null}

                {section.items.map((item) => {
                  const active = isActive(item.path);
                  const buttonContent = (
                    <button
                      onClick={() => navigate(item.path)}
                      className={cn(
                        "flex w-full items-center gap-3 rounded-2xl py-3.5 transition-all duration-300",
                        isSidebarExpanded ? "px-4 text-right" : "justify-center px-0",
                        active
                          ? 'bg-[var(--vault-primary)]/10 text-[var(--vault-primary)] shadow-[0_0_20px_rgba(37,99,235,0.05)] font-bold'
                          : 'text-[var(--vault-on-surface-variant)] hover:bg-[var(--vault-surface-highest)] hover:text-[var(--vault-primary)]'
                      )}
                    >
                      <item.icon className="h-5 w-5 flex-shrink-0" />
                      {isSidebarExpanded && <span className="text-sm font-medium whitespace-nowrap">{item.title}</span>}
                    </button>
                  );

                  if (!isSidebarExpanded) {
                    return (
                      <Tooltip key={item.path + item.title}>
                        <TooltipTrigger asChild>
                          {buttonContent}
                        </TooltipTrigger>
                        <TooltipContent side="left" className="font-medium">
                          {item.title}
                        </TooltipContent>
                      </Tooltip>
                    );
                  }

                  return <React.Fragment key={item.path + item.title}>{buttonContent}</React.Fragment>;
                })}
              </div>
            ))}
          </nav>
        </div>

        <div className={cn("mt-8 flex flex-col gap-5 border-t border-[var(--vault-surface-highest)] pt-8 transition-all duration-300", !isSidebarExpanded && "items-center px-0")}>
          <div className={cn("flex items-center gap-3 px-2 overflow-hidden transition-all", !isSidebarExpanded && "px-0")}>
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-[var(--vault-surface-highest)] text-[var(--vault-primary)] shadow-sm">
              <span className="text-sm font-bold">{user?.full_name?.charAt(0) || 'U'}</span>
            </div>
            {isSidebarExpanded && (
              <div className="flex flex-col whitespace-nowrap">
                <span className="text-sm font-bold text-[var(--vault-on-surface)]">{user?.full_name || 'کاربر'}</span>
                <span className="text-xs text-[var(--vault-on-surface-variant)]">{getRoleDisplayName(currentRole)}</span>
              </div>
            )}
          </div>

          {isAdminRole(currentRole) && (
            <Tooltip delayDuration={0} disableHoverableContent={isSidebarExpanded}>
              <TooltipTrigger asChild>
                <button
                  onClick={() => navigate('/admin')}
                  className={cn(
                    "flex items-center gap-3 py-2 text-[var(--vault-on-surface-variant)] transition-colors hover:text-[var(--vault-primary)]",
                    isSidebarExpanded ? "px-4" : "justify-center px-0"
                  )}
                >
                  <Settings className="h-5 w-5 flex-shrink-0" />
                  {isSidebarExpanded && <span className="text-sm">تنظیمات</span>}
                </button>
              </TooltipTrigger>
              {!isSidebarExpanded && (
                <TooltipContent side="left">
                  تنظیمات
                </TooltipContent>
              )}
            </Tooltip>
          )}

          <Tooltip delayDuration={0} disableHoverableContent={isSidebarExpanded}>
            <TooltipTrigger asChild>
              <button
                onClick={handleLogout}
                className={cn(
                  "flex items-center gap-3 py-2 text-rose-400/80 transition-all hover:text-rose-400 hover:scale-[1.02]",
                  isSidebarExpanded ? "px-4" : "justify-center px-0"
                )}
              >
                <LogOut className="h-5 w-5 flex-shrink-0" />
                {isSidebarExpanded && <span className="text-sm">خروج</span>}
              </button>
            </TooltipTrigger>
            {!isSidebarExpanded && (
              <TooltipContent side="left">
                خروج
              </TooltipContent>
            )}
          </Tooltip>
        </div>
      </aside>
    </TooltipProvider>
  );
}

export default SideNavV2;
