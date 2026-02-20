import React from 'react';
import { useAuthStore } from '../stores/useAuthStore';
import {
    LayoutDashboard,
    FileText,
    CreditCard,
    CheckSquare,
    Calculator,
    Users,
    LogOut,
    BarChart3,
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
    Sidebar,
    SidebarContent,
    SidebarGroup,
    SidebarGroupLabel,
    SidebarGroupContent,
    SidebarMenu,
    SidebarMenuItem,
    SidebarMenuButton,
    SidebarHeader,
    SidebarFooter,
    SidebarSeparator,
} from '../components/ui/sidebar';
import { Button } from '../components/ui/button';

interface NavItem {
    title: string;
    icon: React.ElementType;
    path: string;
    adminOnly?: boolean;
}

const userNavItems: NavItem[] = [
    { title: 'داشبورد', icon: LayoutDashboard, path: '/portal' },
    { title: 'تراکنش‌های من', icon: FileText, path: '/portal' },
    { title: 'قراردادها', icon: FileText, path: '/contracts' },
    { title: 'درخواست اعتبار', icon: CreditCard, path: '/portal' },
];

const adminNavItems: NavItem[] = [
    { title: 'داشبورد مدیریت', icon: LayoutDashboard, path: '/admin' },
    { title: 'گزارش مدیریتی', icon: BarChart3, path: '/reports' },
    { title: 'قراردادها', icon: FileText, path: '/contracts' },
    { title: 'تأییدیه‌ها', icon: CheckSquare, path: '/admin' },
    { title: 'درخواست‌های اعتبار', icon: CreditCard, path: '/admin' },
    { title: 'حسابداری', icon: Calculator, path: '/accounting' },
    { title: 'مدیریت کاربران', icon: Users, path: '/admin', adminOnly: true },
];

/**
 * SideNav - Sidebar navigation component
 * Uses shadcn Sidebar with side="right" for RTL layout
 */
export function SideNav() {
    const { user, logout } = useAuthStore();
    const navigate = useNavigate();
    const location = useLocation();

    const isAdmin = user?.role === 'admin';
    const navItems = isAdmin ? adminNavItems : userNavItems;

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    const handleNavigate = (path: string) => {
        navigate(path);
    };

    return (
        <Sidebar
            side="right"
            collapsible="icon"
            className="fixed top-0 right-0 z-50 h-full border-l border-slate-200"
        >
            <SidebarHeader className="border-b border-sidebar-border">
                <div className="flex items-center gap-2 px-2 py-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                        <LayoutDashboard className="h-4 w-4" />
                    </div>
                    <div className="flex flex-col group-data-[collapsible=icon]:hidden">
                        <span className="text-sm font-semibold">سامانه مالی</span>
                        <span className="text-xs text-muted-foreground">شهرداری اصفهان</span>
                    </div>
                </div>
            </SidebarHeader>

            <SidebarContent>
                <SidebarGroup>
                    <SidebarGroupLabel>
                        {isAdmin ? 'پنل مدیریت' : 'پورتال کاربر'}
                    </SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {navItems.map((item) => (
                                <SidebarMenuItem key={item.path + item.title}>
                                    <SidebarMenuButton
                                        isActive={location.pathname === item.path}
                                        onClick={() => handleNavigate(item.path)}
                                        tooltip={item.title}
                                    >
                                        <item.icon className="h-4 w-4" />
                                        <span>{item.title}</span>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            ))}
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
            </SidebarContent>

            <SidebarFooter className="border-t border-sidebar-border">
                <div className="flex items-center justify-between px-2 py-3 group-data-[collapsible=icon]:justify-center">
                    <div className="flex items-center gap-2 group-data-[collapsible=icon]:hidden">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted">
                            <span className="text-sm font-medium">
                                {user?.full_name?.charAt(0) || 'U'}
                            </span>
                        </div>
                        <div className="flex flex-col">
                            <span className="text-sm font-medium">{user?.full_name || 'کاربر'}</span>
                            <span className="text-xs text-muted-foreground">
                                {isAdmin ? 'مدیر' : 'کاربر'}
                            </span>
                        </div>
                    </div>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={handleLogout}
                        className="h-8 w-8"
                        title="خروج"
                    >
                        <LogOut className="h-4 w-4" />
                    </Button>
                </div>
            </SidebarFooter>
        </Sidebar>
    );
}

export default SideNav;
