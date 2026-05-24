import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Home,
  LogOut,
} from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

import { useAuthStore } from '../stores/useAuthStore';
import { useUIStore } from '../stores/useUIStore';
import {
  getRoleDisplayName,
} from '../components/funding/workflow';
import {
  resolveSidebarFooterItems,
  resolveSidebarSections,
  type SidebarNavItem,
} from '../config/navigation';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../components/ui/tooltip';
import { cn } from '../components/ui/utils';

export function SideNavV2() {
  const { user, logout } = useAuthStore();
  const { isSidebarExpanded, toggleSidebar } = useUIStore();
  const navigate = useNavigate();
  const location = useLocation();
  const currentRole = user?.role;
  const sections = React.useMemo(() => resolveSidebarSections(currentRole), [currentRole]);
  const footerItems = React.useMemo(() => resolveSidebarFooterItems(currentRole), [currentRole]);

  const [openMenus, setOpenMenus] = React.useState<string[]>([]);

  const isActive = (path?: string) => {
    if (!path) return false;
    const [targetPath, targetSearch] = path.split('?');
    const samePath = location.pathname === targetPath || location.pathname.startsWith(`${targetPath}/`);
    if (!samePath) return false;
    return targetSearch
      ? new URLSearchParams(location.search).toString() === new URLSearchParams(targetSearch).toString()
      : true;
  };

  const isChildActive = (item: SidebarNavItem) =>
    item.children?.some((child) => isActive(child.path)) ?? false;

  React.useEffect(() => {
    const menuIds = sections.flatMap((section) =>
      section.items.filter((item) => (item.children?.length ?? 0) > 0).map((item) => item.id),
    );
    const activeSubmenus = sections
      .flatMap((section) => section.items)
      .filter((item) => item.children && isChildActive(item))
      .map((item) => item.id);
    const defaultSubmenus = sections
      .flatMap((section) => section.items)
      .filter((item) => item.defaultOpen && (item.children?.length ?? 0) > 0)
      .map((item) => item.id);

    setOpenMenus((prev) => {
      const retainedMenus = prev.filter((menuId) => menuIds.includes(menuId));
      return Array.from(new Set([...retainedMenus, ...defaultSubmenus, ...activeSubmenus]));
    });
  }, [location.pathname, location.search, sections]);

  const toggleMenu = (menuId: string) => {
    setOpenMenus((prev) =>
      prev.includes(menuId) ? prev.filter((id) => id !== menuId) : [...prev, menuId]
    );
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          'sticky top-0 h-screen overflow-y-auto shrink-0 flex flex-col justify-between border-l border-[var(--vault-surface-highest)] bg-[var(--vault-bg)] p-6 text-[var(--vault-on-surface)] transition-all duration-300 ease-in-out',
          isSidebarExpanded ? 'w-72' : 'w-20 p-4',
        )}
      >
        <div className="flex flex-col gap-8">
          <div className="flex items-center justify-between">
            <div
              className={cn(
                'flex items-center gap-4 overflow-hidden px-2 transition-all duration-300',
                !isSidebarExpanded && 'w-0 px-0 opacity-0',
              )}
            >
              <div className="glass-vault flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-3xl bg-[var(--vault-primary)]/10 text-[var(--vault-primary)] shadow-[0_0_15px_rgba(137,206,255,0.1)]">
                <Home className="h-6 w-6" />
              </div>
              <div className="flex flex-col whitespace-nowrap">
                <h1 className="text-base font-bold leading-tight text-[var(--vault-on-surface)]">
                  سیستم جامع ERP
                </h1>
                <p className="text-sm text-[var(--vault-on-surface-variant)]">شهرداری مرکزی</p>
              </div>
            </div>

            <button
              onClick={() => toggleSidebar()}
              className={cn(
                'flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--vault-surface-high)] text-[var(--vault-on-surface-variant)] transition-all hover:bg-[var(--vault-surface-highest)] hover:text-[var(--vault-primary)]',
                !isSidebarExpanded && 'mx-auto',
              )}
            >
              {isSidebarExpanded ? <ChevronRight className="h-5 w-5" /> : <ChevronLeft className="h-5 w-5" />}
            </button>
          </div>

          <nav className="flex flex-col gap-8">
            {sections.map((section) => (
              <div key={section.id} className="flex flex-col gap-3">
                {section.title && isSidebarExpanded ? (
                  <div className="whitespace-nowrap px-4 pb-2 pt-2 text-xs font-bold text-gray-400 border-b border-[var(--vault-surface-highest)] mb-2">
                    {section.title}
                  </div>
                ) : null}

                {section.items.map((item) => {
                  const hasChildren = item.children && item.children.length > 0;
                  const active = item.path ? isActive(item.path) : isChildActive(item);
                  const isOpen = openMenus.includes(item.id);

                  const buttonContent = (
                    <div className="flex flex-col gap-1">
                      <button
                        onClick={() => {
                          if (hasChildren && isSidebarExpanded) {
                            toggleMenu(item.id);
                          } else if (item.path) {
                            navigate(item.path);
                          }
                        }}
                        className={cn(
                          'flex w-full items-center gap-3 rounded-2xl py-3.5 transition-all duration-300',
                          isSidebarExpanded ? 'px-4 text-right' : 'justify-center px-0',
                          active && (!hasChildren || !isSidebarExpanded)
                            ? 'bg-[var(--vault-primary)]/10 font-bold text-[var(--vault-primary)] shadow-[0_0_20px_rgba(37,99,235,0.05)]'
                            : 'text-[var(--vault-on-surface-variant)] hover:bg-[var(--vault-surface-highest)] hover:text-[var(--vault-primary)]',
                        )}
                      >
                        <item.icon className="h-5 w-5 flex-shrink-0" />
                        {isSidebarExpanded && (
                          <div className="flex flex-1 items-center justify-between overflow-hidden">
                            <span className="whitespace-nowrap text-sm font-medium">{item.title}</span>
                            {hasChildren && (
                              <ChevronDown
                                className={cn(
                                  'h-4 w-4 transition-transform duration-300',
                                  isOpen && 'rotate-180'
                                )}
                              />
                            )}
                          </div>
                        )}
                      </button>

                      {hasChildren && isSidebarExpanded && (
                        <AnimatePresence>
                          {isOpen && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              transition={{ duration: 0.3, ease: 'easeInOut' }}
                              className="overflow-hidden"
                            >
                              <div className="mr-9 mt-1 flex flex-col gap-1 border-r border-[var(--vault-surface-highest)] pr-4">
                                {item.children?.map((child) => {
                                  const childActive = isActive(child.path);
                                  return (
                                    <button
                                      key={child.id}
                                      onClick={() => navigate(child.path)}
                                      className={cn(
                                        'rounded-xl py-2.5 text-right text-xs transition-all duration-200',
                                        childActive
                                          ? 'font-bold text-[var(--vault-primary)]'
                                          : 'text-[var(--vault-on-surface-variant)] hover:text-[var(--vault-primary)]'
                                      )}
                                    >
                                      {child.title}
                                    </button>
                                  );
                                })}
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      )}
                    </div>
                  );

                  if (!isSidebarExpanded) {
                    return (
                      <Tooltip key={item.id}>
                        <TooltipTrigger asChild>{buttonContent}</TooltipTrigger>
                        <TooltipContent side="left" className="font-medium">
                          {item.title}
                        </TooltipContent>
                      </Tooltip>
                    );
                  }

                  return <React.Fragment key={item.id}>{buttonContent}</React.Fragment>;
                })}
              </div>
            ))}
          </nav>
        </div>

        <div
          className={cn(
            'mt-8 flex flex-col gap-5 border-t border-[var(--vault-surface-highest)] pt-8 transition-all duration-300',
            !isSidebarExpanded && 'items-center px-0',
          )}
        >
          <div
            className={cn(
              'flex items-center gap-3 overflow-hidden px-2 transition-all',
              !isSidebarExpanded && 'px-0',
            )}
          >
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-[var(--vault-surface-highest)] text-[var(--vault-primary)] shadow-sm">
              <span className="text-sm font-bold">{user?.full_name?.charAt(0) || 'U'}</span>
            </div>
            {isSidebarExpanded ? (
              <div className="flex flex-col whitespace-nowrap">
                <span className="text-sm font-bold text-[var(--vault-on-surface)]">{user?.full_name || 'کاربر'}</span>
                <span className="text-xs text-[var(--vault-on-surface-variant)]">{getRoleDisplayName(currentRole)}</span>
              </div>
            ) : null}
          </div>

          {footerItems.map((item) => (
            <Tooltip key={item.id} delayDuration={0} disableHoverableContent={isSidebarExpanded}>
              <TooltipTrigger asChild>
                <button
                  onClick={() => navigate(item.path)}
                  className={cn(
                    'flex items-center gap-3 py-2 text-[var(--vault-on-surface-variant)] transition-colors hover:text-[var(--vault-primary)]',
                    isSidebarExpanded ? 'px-4' : 'justify-center px-0',
                  )}
                >
                  <item.icon className="h-5 w-5 flex-shrink-0" />
                  {isSidebarExpanded ? <span className="text-sm">{item.title}</span> : null}
                </button>
              </TooltipTrigger>
              {!isSidebarExpanded ? <TooltipContent side="left">{item.title}</TooltipContent> : null}
            </Tooltip>
          ))}

          <Tooltip delayDuration={0} disableHoverableContent={isSidebarExpanded}>
            <TooltipTrigger asChild>
              <button
                onClick={handleLogout}
                className={cn(
                  'flex items-center gap-3 py-2 text-rose-400/80 transition-all hover:scale-[1.02] hover:text-rose-400',
                  isSidebarExpanded ? 'px-4' : 'justify-center px-0',
                )}
              >
                <LogOut className="h-5 w-5 flex-shrink-0" />
                {isSidebarExpanded ? <span className="text-sm">خروج</span> : null}
              </button>
            </TooltipTrigger>
            {!isSidebarExpanded ? <TooltipContent side="left">خروج</TooltipContent> : null}
          </Tooltip>
        </div>
      </aside>
    </TooltipProvider>
  );
}

export default SideNavV2;
