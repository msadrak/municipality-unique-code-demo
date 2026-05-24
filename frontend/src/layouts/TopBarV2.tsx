import React, { useEffect, useState } from 'react';
import { Bell } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import { getRoleDisplayName } from '../components/funding/workflow';
import { Button } from '../components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { fetchUnreadNotifications, markNotificationRead, NotificationItem } from '../services/notifications';
import { useAuthStore } from '../stores/useAuthStore';

export function TopBarV2() {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    let active = true;

    const loadNotifications = async () => {
      try {
        const items = await fetchUnreadNotifications();
        if (active) {
          setNotifications(items);
        }
      } catch (error) {
        if (active) {
          console.error(error);
        }
      }
    };

    void loadNotifications();
    const intervalId = window.setInterval(() => {
      void loadNotifications();
    }, 30000);

    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, []);

  const handleReadNotification = async (notification: NotificationItem) => {
    try {
      await markNotificationRead(notification.id);
      setNotifications((current) => current.filter((item) => item.id !== notification.id));
      setIsOpen(false);
      if ((user?.role || '').toUpperCase() === 'REGION_USER') {
        navigate('/attendance/inbox');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'خواندن اعلان ناموفق بود.';
      toast.error(message);
    }
  };

  let moduleTitle = 'داشبورد یکپارچه مدیریت شهری (ERP)';
  const path = location.pathname;
  if (path.startsWith('/civil') || path.startsWith('/contracts') || path.startsWith('/reports') || path.startsWith('/accounting') || path.startsWith('/portal')) {
    moduleTitle = 'سیستم مدیریت پروژه‌های عمرانی';
  } else if (path.startsWith('/hr') || path.startsWith('/attendance') || path.startsWith('/security') || path.startsWith('/region') || path.startsWith('/contractor')) {
    moduleTitle = 'سیستم مدیریت منابع انسانی';
  } else if (path.startsWith('/admin')) {
    moduleTitle = 'پنل مدیریت سیستم';
  }

  return (
    <header className="sticky top-0 z-50 flex items-center justify-between border-b border-[var(--vault-surface-highest)] bg-[var(--vault-bg)]/80 px-8 py-5 backdrop-blur-xl">
      <div className="flex flex-col gap-1">
        <h2 className="text-2xl font-black tracking-tight text-[var(--vault-on-surface)]">
          {moduleTitle}
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-[var(--vault-primary)]">{getRoleDisplayName(user?.role)}</span>
          {user?.region_name ? (
            <>
              <span className="text-xs text-[var(--vault-surface-highest)]">|</span>
              <span className="text-xs text-[var(--vault-on-surface-variant)]">{user.region_name}</span>
            </>
          ) : null}
        </div>
      </div>
      <div className="flex items-center gap-6">
        <Popover open={isOpen} onOpenChange={setIsOpen}>
          <PopoverTrigger asChild>
            <button className="relative rounded-xl p-2.5 text-[var(--vault-on-surface-variant)] transition-all duration-300 hover:bg-[var(--vault-surface-high)] hover:text-[var(--vault-primary)]">
              <Bell className="h-5 w-5" />
              {notifications.length > 0 ? (
                <span className="absolute -right-1 -top-1 flex min-h-5 min-w-5 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white">
                  {notifications.length}
                </span>
              ) : null}
            </button>
          </PopoverTrigger>
          <PopoverContent align="end" className="w-96 border-[var(--vault-surface-highest)] bg-[var(--vault-surface-low)] p-0 text-right">
            <div className="border-b border-[var(--vault-surface-highest)] px-4 py-3">
              <div className="text-sm font-bold text-[var(--vault-on-surface)]">اعلان‌های خوانده‌نشده</div>
              <div className="mt-1 text-xs text-[var(--vault-on-surface-variant)]">
                آخرین بازخوردها و تغییرات برای حساب شما
              </div>
            </div>
            <div className="max-h-96 overflow-auto">
              {notifications.length === 0 ? (
                <div className="px-4 py-8 text-center text-sm text-[var(--vault-on-surface-variant)]">
                  اعلان خوانده‌نشده‌ای ندارید.
                </div>
              ) : (
                notifications.map((notification) => (
                  <div key={notification.id} className="border-b border-[var(--vault-surface-highest)]/70 px-4 py-4 last:border-b-0">
                    <div className="text-sm leading-7 text-[var(--vault-on-surface)]">{notification.message}</div>
                    <div className="mt-2 flex items-center justify-between gap-3">
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-[var(--vault-surface-highest)] bg-transparent"
                        onClick={() => void handleReadNotification(notification)}
                      >
                        خواندم
                      </Button>
                      <span className="text-xs text-[var(--vault-on-surface-variant)]">
                        {new Date(notification.created_at).toLocaleString('fa-IR')}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </PopoverContent>
        </Popover>
        <div className="mr-2 flex items-center gap-3 border-r border-[var(--vault-surface-highest)] pl-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-[var(--vault-primary)]/20 bg-[var(--vault-primary)]/10 shadow-sm">
            <span className="text-sm font-black text-[var(--vault-primary)]">
              {(user?.full_name || user?.username || 'U').charAt(0)}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}

export default TopBarV2;
