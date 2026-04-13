import React, { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Building2, Lock, User, Loader2, UserPlus, LayoutDashboard, Eye, EyeOff } from 'lucide-react';
import { authService } from '../services';

type UserData = {
  id: number;
  username: string;
  fullName: string;
  role: string;
};

type LoginProps = {
  onLogin: (user: UserData) => void;
  onNavigateToPublic: () => void;
  onNavigateToContractorAuth?: () => void;
};

export function Login({ onLogin, onNavigateToPublic, onNavigateToContractorAuth }: LoginProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const user = await authService.login({ username, password });
      onLogin({
        id: user.id,
        username: user.username,
        fullName: user.full_name,
        role: user.role,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'نام کاربری یا رمز عبور اشتباه است');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center relative overflow-hidden bg-slate-50 p-4">
      {/* ── Animated Background Blobs ────────────────────── */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[10%] -right-[5%] w-[500px] h-[500px] rounded-full blur-3xl opacity-50 bg-blue-600/10" />
        <div className="absolute -bottom-[10%] -left-[10%] w-[600px] h-[600px] rounded-full blur-3xl opacity-50 bg-blue-300/20" />
        {/* Geometric dot grid */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: 'radial-gradient(#2563eb 1px, transparent 1px)',
            backgroundSize: '32px 32px',
          }}
        />
      </div>

      {/* ── Main Card ────────────────────────────────────── */}
      <div className="relative z-10 w-full max-w-[440px] glass-card rounded-2xl shadow-2xl overflow-hidden animate-fade-in-up">
        {/* Header Pattern Area */}
        <div className="h-32 w-full bg-gradient-to-br from-blue-600/10 to-blue-500/5 flex items-center justify-center relative overflow-hidden">
          <div
            className="absolute inset-0 opacity-10"
            style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%232563eb' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
            }}
          />
          <div className="relative bg-white p-4 rounded-xl shadow-lg border border-slate-100 mt-8">
            <Building2 className="h-9 w-9 text-blue-600" />
          </div>
        </div>

        {/* Card Content */}
        <div className="px-8 pb-8 pt-10">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-slate-900 mb-2 tracking-tight">
              سامانه مالی شهرداری
            </h1>
            <h2 className="text-slate-500 font-medium text-sm">
              منابع انسانی شهرداری مرکزی
            </h2>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-sm text-center mb-5">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Username */}
            <div className="space-y-2">
              <Label htmlFor="username" className="text-sm font-semibold text-slate-700 mr-1 block">
                نام کاربری
              </Label>
              <div className="relative">
                <User className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400 pointer-events-none" />
                <Input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="h-12 pr-11 pl-4 rounded-lg bg-white/50 border-slate-200 placeholder:text-slate-400 focus:ring-2 focus:ring-blue-600/20 focus:border-blue-600 transition-all duration-200"
                  placeholder="نام کاربری خود را وارد کنید"
                  required
                  autoFocus
                />
              </div>
            </div>

            {/* Password */}
            <div className="space-y-2">
              <Label htmlFor="password" className="text-sm font-semibold text-slate-700 mr-1 block">
                رمز عبور
              </Label>
              <div className="relative group">
                <Lock className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400 pointer-events-none" />
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-12 pr-11 pl-11 rounded-lg bg-white/50 border-slate-200 placeholder:text-slate-400 focus:ring-2 focus:ring-blue-600/20 focus:border-blue-600 transition-all duration-200"
                  placeholder="رمز عبور خود را وارد کنید"
                  required
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute left-0 top-0 h-full w-10 flex items-center justify-center text-slate-400 hover:text-blue-600 transition-colors cursor-pointer"
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow-lg shadow-blue-600/20 hover:shadow-blue-600/40 transition-all duration-300 transform hover:-translate-y-0.5 flex items-center justify-center gap-2 mt-4"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="ml-2 h-5 w-5 animate-spin" />
                  در حال ورود...
                </>
              ) : (
                'ورود به سامانه'
              )}
            </Button>

            {/* Demo Credentials */}
            <div className="bg-slate-50/80 border border-slate-200 p-3 rounded-lg text-xs space-y-1">
              <p className="text-center text-slate-400 font-medium">اطلاعات ورود نمونه:</p>
              <div className="flex justify-center gap-6 text-slate-500">
                <span>کاربر: user / user</span>
                <span>مدیر: admin / admin</span>
              </div>
            </div>
          </form>

          {/* ── Divider ──────────────────────────────── */}
          <div className="mt-8 relative">
            <div aria-hidden="true" className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200" />
            </div>
            <div className="relative flex justify-center">
              <span className="px-3 bg-white/80 text-xs text-slate-400 font-medium backdrop-blur-sm">
                دسترسی سریع
              </span>
            </div>
          </div>

          {/* ── Quick Access Icons ────────────────────── */}
          <div className="flex items-center justify-center gap-8 mt-6">
            <button
              type="button"
              onClick={onNavigateToPublic}
              className="flex flex-col items-center group"
            >
              <div className="w-11 h-11 rounded-full bg-slate-50 flex items-center justify-center text-slate-500 group-hover:text-blue-600 group-hover:bg-blue-50 transition-all duration-300 border border-slate-200">
                <LayoutDashboard className="h-5 w-5" />
              </div>
              <span className="text-[11px] font-medium text-slate-500 group-hover:text-blue-600 mt-2 transition-colors">
                داشبورد عمومی
              </span>
            </button>

            {onNavigateToContractorAuth && (
              <button
                type="button"
                onClick={onNavigateToContractorAuth}
                className="flex flex-col items-center group"
              >
                <div className="w-11 h-11 rounded-full bg-slate-50 flex items-center justify-center text-slate-500 group-hover:text-blue-600 group-hover:bg-blue-50 transition-all duration-300 border border-slate-200">
                  <UserPlus className="h-5 w-5" />
                </div>
                <span className="text-[11px] font-medium text-slate-500 group-hover:text-blue-600 mt-2 transition-colors">
                  احراز هویت پیمانکار
                </span>
              </button>
            )}
          </div>
        </div>

        {/* Bottom gradient bar */}
        <div className="h-1.5 w-full bg-gradient-to-r from-blue-400 via-blue-600 to-blue-500" />
      </div>

      {/* Copyright */}
      <p className="mt-8 text-xs text-slate-400 text-center font-medium relative z-10">
        © ۱۴۰۳ شهرداری اصفهان - تمامی حقوق محفوظ است
      </p>
    </div>
  );
}
