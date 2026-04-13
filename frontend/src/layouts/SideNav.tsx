import React from 'react';
import { useAuthStore } from '../stores/useAuthStore';
import {
    Home,
    FileText,
    BarChart3,
    Wallet,
    Settings,
    LogOut,
    Inbox,
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';

interface NavItem {
    title: string;
    icon: React.ElementType;
    path: string;
}

interface NavSection {
    title?: string;
    items: NavItem[];
}

/**
 * Navigation items matching the Stitch design
 * Sidebar shows: پورتال کاربر / قراردادها / گزارش‌ها / حسابداری (admin) / مالی (user) / مدیریت
 */
const hrFundingNavItems: NavItem[] = [
    { title: 'ثبت درخواست تامین اعتبار', icon: Wallet, path: '/hr/funding/new' },
    { title: 'درخواست‌های من', icon: FileText, path: '/hr/funding/my-requests' },
    { title: 'کارتابل مدیران', icon: Inbox, path: '/hr/funding/inbox' },
];

const userNavSections: NavSection[] = [
    {
        items: [
            { title: 'پورتال کاربر', icon: Home, path: '/portal' },
            { title: 'قراردادها', icon: FileText, path: '/contracts' },
            { title: 'گزارش‌ها', icon: BarChart3, path: '/reports' },
            { title: 'مالی', icon: Wallet, path: '/accounting' },
        ],
    },
    {
        title: 'منابع انسانی',
        items: hrFundingNavItems,
    },
];

const adminNavSections: NavSection[] = [
    {
        items: [
            { title: 'پورتال کاربر', icon: Home, path: '/portal' },
            { title: 'قراردادها', icon: FileText, path: '/contracts' },
            { title: 'گزارش‌ها', icon: BarChart3, path: '/reports' },
            { title: 'حسابداری', icon: Wallet, path: '/accounting' },
            { title: 'مدیریت', icon: Settings, path: '/admin' },
        ],
    },
    {
        title: 'منابع انسانی',
        items: hrFundingNavItems,
    },
];

/**
 * SideNav — Dark right-aligned sidebar matching Stitch design
 * - Dark slate-900 background
 * - Municipality logo + title at top
 * - Navigation links with active state
 * - Settings + Logout at bottom
 */
export function SideNav() {
    const { user, logout } = useAuthStore();
    const navigate = useNavigate();
    const location = useLocation();

    const isAdmin = user?.role === 'admin';
    const navSections = isAdmin ? adminNavSections : userNavSections;

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    const handleNavigate = (path: string) => {
        navigate(path);
    };

    const isActive = (path: string) =>
        location.pathname === path || location.pathname.startsWith(`${path}/`);

    return (
        <aside className="w-72 flex-shrink-0 bg-slate-900 text-white flex flex-col justify-between p-6 min-h-screen">
            <div className="flex flex-col gap-8">
                {/* Logo / Branding */}
                <div className="flex items-center gap-4 px-2">
                    <div className="h-12 w-12 rounded-full bg-blue-600/20 flex items-center justify-center border-2 border-blue-600/30">
                        <Home className="h-6 w-6 text-blue-400" />
                    </div>
                    <div className="flex flex-col">
                        <h1 className="text-base font-bold leading-tight text-white">منابع انسانی</h1>
                        <p className="text-slate-400 text-sm">شهرداری مرکزی</p>
                    </div>
                </div>

                {/* Navigation */}
                <nav className="flex flex-col gap-6">
                    {navSections.map((section, sectionIndex) => (
                        <div key={section.title ?? `section-${sectionIndex}`} className="flex flex-col gap-2">
                            {section.title ? (
                                <div className="px-4 text-[11px] font-bold tracking-wide text-slate-500">
                                    {section.title}
                                </div>
                            ) : null}

                            {section.items.map((item) => {
                                const active = isActive(item.path);
                                return (
                                    <button
                                        key={item.path + item.title}
                                        onClick={() => handleNavigate(item.path)}
                                        className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all text-right w-full ${active
                                                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
                                                : 'text-slate-400 hover:text-white hover:bg-white/10'
                                            }`}
                                    >
                                        <item.icon className="h-5 w-5" />
                                        <span className="text-sm font-medium">{item.title}</span>
                                    </button>
                                );
                            })}
                        </div>
                    ))}
                </nav>
            </div>

            {/* Sidebar Footer */}
            <div className="flex flex-col gap-4 mt-8 pt-6 border-t border-slate-800">
                {/* User Info */}
                <div className="flex items-center gap-3 px-2">
                    <div className="h-9 w-9 rounded-full bg-slate-700 flex items-center justify-center">
                        <span className="text-sm font-medium text-slate-300">
                            {user?.full_name?.charAt(0) || 'U'}
                        </span>
                    </div>
                    <div className="flex flex-col">
                        <span className="text-sm font-medium text-white">{user?.full_name || 'کاربر'}</span>
                        <span className="text-xs text-slate-500">
                            {isAdmin ? 'مدیر سیستم' : 'کارشناس مالی'}
                        </span>
                    </div>
                </div>

                {/* Settings */}
                <button
                    onClick={() => navigate('/admin')}
                    className="flex items-center gap-3 px-4 py-2 text-slate-400 hover:text-white transition-colors"
                >
                    <Settings className="h-5 w-5" />
                    <span className="text-sm">تنظیمات</span>
                </button>

                {/* Logout */}
                <button
                    onClick={handleLogout}
                    className="flex items-center gap-3 px-4 py-2 text-red-400 hover:text-red-300 transition-colors"
                >
                    <LogOut className="h-5 w-5" />
                    <span className="text-sm">خروج</span>
                </button>
            </div>
        </aside>
    );
}

export default SideNav;
