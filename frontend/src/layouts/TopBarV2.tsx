import React from 'react';
import { Bell } from 'lucide-react';

import { useAuthStore } from '../stores/useAuthStore';
import { getRoleDisplayName } from '../components/funding/workflow';

export function TopBarV2() {
  const { user } = useAuthStore();

  return (
    <header className="bg-[var(--vault-bg)]/80 backdrop-blur-xl border-b border-[var(--vault-surface-highest)] px-8 py-5 flex items-center justify-between sticky top-0 z-50">
      <div className="flex flex-col gap-1">
        <h2 className="text-2xl font-black text-[var(--vault-on-surface)] tracking-tight">
          خوش آمدید، {user?.full_name || 'کاربر'}
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-[var(--vault-primary)] font-medium text-sm">{getRoleDisplayName(user?.role)}</span>
          <span className="text-[var(--vault-surface-highest)] text-xs">|</span>
          <span className="text-[var(--vault-on-surface-variant)] text-xs">سامانه هوشمند منابع انسانی</span>
        </div>
      </div>
      <div className="flex items-center gap-6">
        <button className="relative p-2.5 text-[var(--vault-on-surface-variant)] hover:bg-[var(--vault-surface-high)] hover:text-[var(--vault-primary)] rounded-xl transition-all duration-300">
          <Bell className="h-5 w-5" />
          <span className="absolute top-2.5 right-2.5 h-2.5 w-2.5 bg-rose-500 rounded-full border-2 border-[var(--vault-bg)]" />
        </button>
        <div className="flex items-center gap-3 pl-2 border-r border-[var(--vault-surface-highest)] mr-2">
          <div className="h-10 w-10 rounded-2xl bg-[var(--vault-primary)]/10 flex items-center justify-center border border-[var(--vault-primary)]/20 shadow-sm">
            <span className="text-sm font-black text-[var(--vault-primary)]">{user?.full_name?.charAt(0) || 'U'}</span>
          </div>
        </div>
      </div>
    </header>
  );
}

export default TopBarV2;
