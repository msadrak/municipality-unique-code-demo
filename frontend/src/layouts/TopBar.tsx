import React from 'react';
import { useAuthStore } from '../stores/useAuthStore';
import { useNavigate } from 'react-router-dom';
import { LogOut, Menu, ChevronLeft } from 'lucide-react';
import { SidebarTrigger } from '../components/ui/sidebar';
import { Button } from '../components/ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '../components/ui/avatar';
import { Separator } from '../components/ui/separator';

/**
 * TopBar - Top navigation bar with sidebar trigger and user menu
 */
export function TopBar() {
    const { user, logout } = useAuthStore();
    const navigate = useNavigate();

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    const getInitials = (name: string) => {
        if (!name) return 'U';
        const parts = name.trim().split(' ');
        if (parts.length >= 2) {
            return parts[0].charAt(0) + parts[1].charAt(0);
        }
        return name.charAt(0);
    };

    const isAdmin = user?.role === 'admin';

    return (
        <header className="flex h-14 shrink-0 items-center gap-2 border-b bg-background px-4">
            {/* Sidebar Toggle */}
            <SidebarTrigger className="-ms-2" />
            <Separator orientation="vertical" className="h-6 mx-2" />

            {/* Breadcrumb placeholder - minimal for Phase 1 */}
            <nav className="flex items-center gap-1 text-sm text-muted-foreground">
                <span>داشبورد</span>
            </nav>

            {/* Spacer */}
            <div className="flex-1" />

            {/* User Menu */}
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                        <Avatar className="h-9 w-9">
                            <AvatarFallback className="bg-primary text-primary-foreground">
                                {getInitials(user?.full_name || '')}
                            </AvatarFallback>
                        </Avatar>
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                    <DropdownMenuLabel className="font-normal">
                        <div className="flex flex-col space-y-1">
                            <p className="text-sm font-medium leading-none">{user?.full_name || 'کاربر'}</p>
                            <p className="text-xs leading-none text-muted-foreground">
                                {isAdmin ? 'مدیر سیستم' : 'کاربر'}
                            </p>
                        </div>
                    </DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={handleLogout} className="text-destructive cursor-pointer">
                        <LogOut className="ml-2 h-4 w-4" />
                        خروج از سامانه
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
        </header>
    );
}

export default TopBar;
