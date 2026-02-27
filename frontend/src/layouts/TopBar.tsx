import React from 'react';
import { useAuthStore } from '../stores/useAuthStore';
import { useNavigate } from 'react-router-dom';
import { Bell } from 'lucide-react';

/**
 * TopBar — Matches Stitch header design
 * White background with border-bottom, welcome text on right, notification + avatar on left
 */
export function TopBar() {
    const { user } = useAuthStore();

    return (
        <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
            <div className="flex flex-col">
                <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
                    خوش آمدید، {user?.full_name || 'کاربر'}
                </h2>
                <div className="flex items-center gap-2 mt-1">
                    <span className="text-slate-500 text-sm">
                        {user?.role === 'admin' ? 'مدیر سیستم' : 'کارشناس مالی'}
                    </span>
                    <span className="text-slate-300 mx-1">|</span>
                    <span className="text-slate-400 text-xs">آخرین ورود: امروز</span>
                </div>
            </div>
            <div className="flex items-center gap-4">
                {/* Notification Bell */}
                <button className="relative p-2 text-slate-500 hover:bg-slate-100 rounded-full transition-colors">
                    <Bell className="h-5 w-5" />
                    <span className="absolute top-2 right-2 h-2.5 w-2.5 bg-red-500 rounded-full border-2 border-white" />
                </button>
                {/* User Avatar */}
                <div className="h-10 w-10 rounded-full bg-slate-200 flex items-center justify-center border border-slate-300">
                    <span className="text-sm font-medium text-slate-600">
                        {user?.full_name?.charAt(0) || 'U'}
                    </span>
                </div>
            </div>
        </header>
    );
}

export default TopBar;
