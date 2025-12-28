import React, { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Card } from './ui/card';
import { Building2, Lock, User, Loader2 } from 'lucide-react';
import { authService } from '../services';

type UserData = {
  id: number;
  username: string;
  fullName: string;
  role: 'user' | 'admin';
};

type LoginProps = {
  onLogin: (user: UserData) => void;
  onNavigateToPublic: () => void;
};

export function Login({ onLogin, onNavigateToPublic }: LoginProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Header - Government Identity */}
        <div className="text-center space-y-3">
          <div className="flex justify-center">
            <div className="bg-primary p-4 rounded-lg">
              <Building2 className="h-12 w-12 text-primary-foreground" />
            </div>
          </div>
          <div className="space-y-1">
            <h1 className="text-2xl">سامانه مالی شهرداری اصفهان</h1>
            <p className="text-muted-foreground">معاونت مالی و اقتصادی</p>
          </div>
        </div>

        {/* Login Card - Single Decision Point */}
        <Card className="p-6">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <h2 className="text-center">ورود به سامانه</h2>
              <p className="text-sm text-muted-foreground text-center">
                اطلاعات ورود خود را وارد نمایید
              </p>
            </div>

            {error && (
              <div className="bg-destructive/10 border border-destructive/20 text-destructive p-3 rounded text-sm text-center">
                {error}
              </div>
            )}

            <div className="space-y-4">
              {/* Username Field */}
              <div className="space-y-2">
                <Label htmlFor="username">نام کاربری</Label>
                <div className="relative">
                  <User className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="pr-10"
                    placeholder="نام کاربری"
                    required
                    autoFocus
                  />
                </div>
              </div>

              {/* Password Field */}
              <div className="space-y-2">
                <Label htmlFor="password">رمز عبور</Label>
                <div className="relative">
                  <Lock className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pr-10"
                    placeholder="رمز عبور"
                    required
                    autoComplete="current-password"
                  />
                </div>
              </div>
            </div>

            {/* Primary Action - Visually Dominant */}
            <Button type="submit" className="w-full h-11" disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="ml-2 h-4 w-4 animate-spin" />
                  در حال ورود...
                </>
              ) : (
                'ورود به سامانه'
              )}
            </Button>

            {/* Demo Credentials */}
            <div className="bg-muted/50 p-3 rounded text-xs space-y-1">
              <p className="text-center text-muted-foreground">اطلاعات ورود نمونه:</p>
              <div className="flex justify-center gap-6">
                <span>کاربر: user / user</span>
                <span>مدیر: admin / admin</span>
              </div>
            </div>
          </form>
        </Card>

        {/* Secondary Action - Public Dashboard */}
        <div className="text-center">
          <Button variant="ghost" onClick={onNavigateToPublic} className="text-sm">
            مشاهده داشبورد عمومی
          </Button>
        </div>

        {/* Footer */}
        <div className="text-center text-xs text-muted-foreground pt-4">
          <p>شهرداری اصفهان - معاونت مالی و اقتصادی</p>
          <p>سامانه تولید شناسه یکتا | نسخه ۱.۰.۰</p>
        </div>
      </div>
    </div>
  );
}
