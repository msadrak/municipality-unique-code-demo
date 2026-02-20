import React from 'react';
import { ArrowLeft, LayoutDashboard, UserCircle } from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../ui/card';

type RoleSelectionDialogProps = {
  userFullName?: string;
  onSelectManagement: () => void;
  onSelectPortal: () => void;
};

type WorkspaceOption = {
  key: 'management' | 'portal';
  title: string;
  description: string;
  icon: React.ElementType;
  onClick: () => void;
};

export function RoleSelectionDialog({
  userFullName,
  onSelectManagement,
  onSelectPortal,
}: RoleSelectionDialogProps) {
  const options: WorkspaceOption[] = [
    {
      key: 'management',
      title: 'داشبورد مدیریتی',
      description: 'ورود به مرکز فرماندهی: کارتابل تاییدها، نمای گردش کار و آمار سیستم',
      icon: LayoutDashboard,
      onClick: onSelectManagement,
    },
    {
      key: 'portal',
      title: 'پرتال کارمندی',
      description: 'ورود به محیط پرتال کاربری برای ثبت و پیگیری عملیات روزانه',
      icon: UserCircle,
      onClick: onSelectPortal,
    },
  ];

  return (
    <div
      dir="rtl"
      className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-100 via-slate-50 to-blue-50 p-4"
    >
      <Card className="w-full max-w-3xl border-primary/20 shadow-xl">
        <CardHeader className="space-y-3 text-center">
          <CardTitle className="text-xl md:text-2xl">
            خوش آمدید! لطفاً محیط کاربری خود را انتخاب کنید
          </CardTitle>
          <CardDescription className="text-sm md:text-base">
            {userFullName ? `${userFullName}، ` : ''}
            یکی از مسیرهای زیر را انتخاب کنید.
          </CardDescription>
        </CardHeader>

        <CardContent className="grid grid-cols-1 gap-4 pb-6 md:grid-cols-2">
          {options.map((option) => (
            <button
              key={option.key}
              type="button"
              onClick={option.onClick}
              className="group rounded-xl border bg-card p-5 text-right transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-2">
                  <h3 className="text-lg font-semibold">{option.title}</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {option.description}
                  </p>
                </div>
                <div className="shrink-0 rounded-lg bg-primary/10 p-3 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                  <option.icon className="h-6 w-6" />
                </div>
              </div>

              <div className="mt-4 inline-flex items-center text-sm font-medium text-primary">
                ورود به این بخش
                <ArrowLeft className="mr-1 h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
              </div>
            </button>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

export default RoleSelectionDialog;
