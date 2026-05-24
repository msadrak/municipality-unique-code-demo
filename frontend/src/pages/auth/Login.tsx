import React, { useEffect, useState } from 'react';
import { ArrowLeft, Building2, KeyRound, Landmark, Loader2, HardHat, Users, Shield, UserCog } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';

import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { getDefaultHomePath } from '../../components/funding/workflow';
import { useAuthStore } from '../../stores/useAuthStore';

const QUICK_HINTS = [
  { title: 'مدیر عمران (Civil)', value: 'civil_manager@test.com / password123', icon: HardHat },
  { title: 'مدیر مالی (Finance)', value: 'finance_manager@test.com / password123', icon: Landmark },
  { title: 'شهردار (Mayor/Council)', value: 'mayor@test.com / password123', icon: Building2 },
  { title: 'امور قراردادها', value: 'contracts_officer@test.com / password123', icon: Users },
  { title: 'کمیسیون تحویل', value: 'delivery_commission@test.com / password123', icon: Users },
  { title: 'مدیریت کل/Admin', value: 'admin@test.com / password123', icon: Shield },
];

export function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isLoading, isAuthenticated, user, error, clearError } = useAuthStore();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;

  useEffect(() => {
    if (!isAuthenticated || !user) {
      return;
    }

    navigate(from || getDefaultHomePath(user.role), { replace: true });
  }, [from, isAuthenticated, navigate, user]);

  useEffect(() => {
    clearError();
  }, [clearError]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await login(username.trim(), password);
  };

  return (
    <div dir="rtl" className="relative min-h-screen overflow-hidden bg-[#f8fafc] text-slate-900 font-sans">
      {/* Dynamic Background Elements */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(0,128,153,0.05),transparent_40%),radial-gradient(circle_at_bottom_right,rgba(0,128,153,0.08),transparent_40%)]" />
      <div className="absolute inset-0 opacity-[0.03] [background-image:radial-gradient(#008099_1px,transparent_1px)] [background-size:24px_24px]" />

      <div className="relative mx-auto flex min-h-screen w-full max-w-6xl items-center justify-center px-4 py-12">
        <div className="grid w-full gap-0 overflow-hidden rounded-[2.5rem] border border-white/60 bg-white/40 shadow-[0_32px_120px_-20px_rgba(0,0,0,0.08)] backdrop-blur-2xl lg:grid-cols-2">
          
          {/* Information Section - Light Architectural Feel */}
          <section className="relative hidden flex-col justify-between border-l border-slate-100 bg-gradient-to-br from-[#f0f9fa] via-white to-[#e6f4f6] p-12 lg:flex">
            <div className="relative space-y-8">
              <div className="inline-flex items-center gap-3 rounded-2xl bg-white px-4 py-2.5 shadow-sm">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#008099]/10 text-[#008099]">
                  <Building2 className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs font-bold tracking-wider text-slate-400 uppercase">Municipality ERP</p>
                  <p className="text-sm font-black text-slate-800">پلتفرم یکپارچه مدیریت شهری</p>
                </div>
              </div>

              <div className="space-y-4">
                <h1 className="text-4xl font-black leading-[1.35] text-slate-900 lg:text-5xl">
                  سامانه جامع مدیریت منابع شهرداری (ERP)
                </h1>
                <p className="max-w-md text-base leading-relaxed text-slate-500">
                  دسترسی یکپارچه به داشبوردهای مالی، مدیریت پروژههای عمرانی، منابع انسانی و املاک در یک بستر شفاف و امن.
                </p>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {QUICK_HINTS.map((hint) => {
                const Icon = hint.icon;
                return (
                <div key={hint.title} className="group rounded-2xl border border-white bg-white/60 p-4 transition-all hover:bg-white hover:shadow-md text-right">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="text-[11px] font-bold text-[#008099] uppercase opacity-70">{hint.title}</p>
                    <Icon className="h-4 w-4 text-[#008099]" />
                  </div>
                  <p className="font-mono text-[11px] text-slate-600 text-left" dir="ltr">{hint.value}</p>
                </div>
                );
              })}
            </div>

            {/* Decorative element */}
            <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-[#008099]/5 blur-3xl" />
          </section>

          {/* Login Form Section */}
          <section className="flex flex-col justify-center bg-white p-8 lg:p-16">
            <div className="mx-auto w-full max-w-sm space-y-8">
              <div className="space-y-2 text-right">
                <div className="mb-6 flex justify-end lg:hidden">
                   <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#008099] text-white shadow-lg shadow-[#008099]/20">
                    <Landmark className="h-6 w-6" />
                  </div>
                </div>
                <h2 className="text-3xl font-black tracking-tight text-slate-900">ورود به پنل کاربری</h2>
                <p className="text-sm font-medium text-slate-400 italic">Security verified • JWT Authentication</p>
              </div>

              {error ? (
                <div className="flex items-center gap-3 rounded-2xl border border-rose-100 bg-rose-50/50 p-4 text-right text-sm text-rose-600 animate-in fade-in slide-in-from-top-2">
                  <div className="h-2 w-2 rounded-full bg-rose-500" />
                  <p className="flex-1">{error}</p>
                </div>
              ) : null}

              <form className="space-y-6" onSubmit={handleSubmit}>
                <div className="space-y-5">
                  <div className="space-y-2 text-right">
                    <label className="text-xs font-bold uppercase tracking-widest text-slate-400 pr-1">نام کاربری</label>
                    <div className="relative group">
                      <Input
                        value={username}
                        onChange={(event) => setUsername(event.target.value)}
                        placeholder="ایمیل یا نام کاربری"
                        className="h-14 rounded-2xl border-slate-100 bg-slate-50/50 pr-5 text-right transition-all focus:bg-white focus:ring-[#008099]/20"
                        autoFocus
                      />
                    </div>
                  </div>

                  <div className="space-y-2 text-right">
                    <label className="text-xs font-bold uppercase tracking-widest text-slate-400 pr-1">رمز عبور</label>
                    <div className="relative group">
                      <KeyRound className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-300 transition-colors group-focus-within:text-[#008099]" />
                      <Input
                        type="password"
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                        placeholder="••••••••"
                        className="h-14 rounded-2xl border-slate-100 bg-slate-50/50 pl-12 pr-5 text-right transition-all focus:bg-white focus:ring-[#008099]/20"
                      />
                    </div>
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={isLoading}
                  className="relative h-14 w-full overflow-hidden rounded-2xl bg-[#008099] text-base font-bold text-white shadow-lg shadow-[#008099]/25 transition-all hover:scale-[1.01] hover:bg-[#006b80] active:scale-[0.98] disabled:opacity-70"
                >
                  {isLoading ? (
                    <div className="flex items-center justify-center gap-2">
                      <Loader2 className="h-5 w-5 animate-spin" />
                      <span>در حال بررسی...</span>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center gap-2">
                      <ArrowLeft className="h-5 w-5" />
                      <span>ورود به سامانه</span>
                    </div>
                  )}
                </Button>
              </form>

              <div className="relative py-4">
                <div className="absolute inset-0 flex items-center" aria-hidden="true">
                  <div className="w-full border-t border-slate-100"></div>
                </div>
                <div className="relative flex justify-center text-xs font-bold uppercase tracking-widest">
                  <span className="bg-white px-4 text-slate-300">دسترسی نمایشی</span>
                </div>
              </div>

              <div className="space-y-2 text-right">
                <p className="text-xs font-bold tracking-wide text-slate-400">اعتبارهای ورود آزمایشی:</p>
                <div className="space-y-2 rounded-2xl border border-slate-100 bg-slate-50/70 p-4 text-xs text-slate-500">
                  {QUICK_HINTS.map((hint, i) => (
                    <p key={i} className="flex justify-between items-center gap-4">
                      <span className="whitespace-nowrap">{hint.title}:</span>
                      <span className="font-mono text-left text-[10px] sm:text-xs" dir="ltr">{hint.value}</span>
                    </p>
                  ))}
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

export default Login;
