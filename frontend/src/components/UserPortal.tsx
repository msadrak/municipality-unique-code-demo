import React, { useEffect, useState, useCallback } from 'react';
import {
  FileText,
  List,
  Loader2,
  ShieldCheck,
  CreditCard,
  Wallet,
  Building,
  Trees,
  Theater,
} from 'lucide-react';
import { TransactionWizard } from './TransactionWizard';
import { MyTransactionsList } from './MyTransactionsList';
import { CreditRequestManager } from './CreditRequestManager';
import { useTransactionStore } from '../stores/useTransactionStore';

type User = {
  id: number;
  username: string;
  fullName: string;
  role: 'user' | 'admin';
};

type UserPortalProps = {
  user: User;
  onLogout: () => void;
  onNavigateToPublic: () => void;
};

type View = 'wizard' | 'my-transactions' | 'credit-requests';

export function UserPortal({ user, onLogout, onNavigateToPublic }: UserPortalProps) {
  const [currentView, setCurrentView] = useState<View>('wizard');
  const [wizardKey, setWizardKey] = useState(0);

  const dashboardData = useTransactionStore((s) => s.dashboardData);
  const isLoading = useTransactionStore((s) => s.isLoading);
  const fetchDashboardInit = useTransactionStore((s) => s.fetchDashboardInit);
  const closeWizard = useTransactionStore((s) => s.closeWizard);

  const userContext = dashboardData?.user_context;
  const subsystem = dashboardData?.subsystem;

  useEffect(() => {
    fetchDashboardInit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleNewTransaction = useCallback(() => {
    closeWizard();
    setWizardKey(k => k + 1);
    setCurrentView('wizard');
  }, [closeWizard]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="text-center">
          <div className="bg-blue-50 p-5 rounded-full inline-block mb-4">
            <Loader2 className="h-10 w-10 animate-spin text-blue-600" />
          </div>
          <p className="text-lg text-slate-500 font-medium">در حال بارگذاری...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* ── Hero Credit Banner ─────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-l from-blue-600 to-blue-500 shadow-lg text-white p-8">
        {/* Decorative background */}
        <div
          className="absolute inset-0 opacity-10 pointer-events-none"
          style={{
            backgroundImage:
              'radial-gradient(circle at 10% 20%, rgba(255,255,255,0.4) 0%, transparent 20%), radial-gradient(circle at 90% 80%, rgba(255,255,255,0.4) 0%, transparent 20%)',
          }}
        />
        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
          <div>
            <p className="text-blue-100 font-medium mb-1">اعتبار در دسترس</p>
            <h3 className="text-4xl font-bold tracking-tight mb-2">
              ۴,۲۵۰,۰۰۰,۰۰۰{' '}
              <span className="text-lg font-normal text-blue-200">ریال</span>
            </h3>
            <p className="text-sm text-blue-100 opacity-90">آخرین بروزرسانی: ۱۰ دقیقه پیش</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setCurrentView('credit-requests')}
              className="bg-white/20 hover:bg-white/30 text-white backdrop-blur-sm px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
            >
              <CreditCard className="h-4 w-4" />
              درخواست اعتبار
            </button>
            <button
              onClick={handleNewTransaction}
              className="bg-white text-blue-600 hover:bg-blue-50 px-4 py-2 rounded-lg text-sm font-medium shadow-sm transition-colors"
            >
              گزارش مالی
            </button>
          </div>
        </div>
      </div>

      {/* ── Activities Section ─────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-bold text-slate-800">فعالیت‌ها</h3>
          <button className="text-sm text-blue-600 hover:underline font-medium">مشاهده همه</button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: Civil Works */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200 hover:shadow-md transition-shadow group cursor-pointer">
            <div className="flex items-start justify-between mb-4">
              <div className="bg-blue-50 p-3 rounded-lg text-blue-600 group-hover:scale-110 transition-transform">
                <Building className="h-6 w-6" />
              </div>
            </div>
            <h4 className="text-lg font-bold text-slate-900 mb-2">عمرانی</h4>
            <p className="text-slate-500 text-sm leading-relaxed mb-4">
              پروژه‌های عمرانی و ساختمانی، نظارت بر پیشرفت فیزیکی.
            </p>
            <div className="w-full bg-slate-100 rounded-full h-2">
              <div className="bg-blue-600 h-2 rounded-full" style={{ width: '75%' }} />
            </div>
            <div className="flex justify-between mt-2 text-xs text-slate-500">
              <span>پیشرفت</span>
              <span>۷۵٪</span>
            </div>
          </div>

          {/* Card 2: Services */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200 hover:shadow-md transition-shadow group cursor-pointer">
            <div className="flex items-start justify-between mb-4">
              <div className="bg-green-50 p-3 rounded-lg text-green-600 group-hover:scale-110 transition-transform">
                <Trees className="h-6 w-6" />
              </div>
            </div>
            <h4 className="text-lg font-bold text-slate-900 mb-2">خدماتی</h4>
            <p className="text-slate-500 text-sm leading-relaxed mb-4">
              خدمات شهری و نگهداری فضای سبز، مدیریت پسماند.
            </p>
            <div className="w-full bg-slate-100 rounded-full h-2">
              <div className="bg-green-600 h-2 rounded-full" style={{ width: '45%' }} />
            </div>
            <div className="flex justify-between mt-2 text-xs text-slate-500">
              <span>پیشرفت</span>
              <span>۴۵٪</span>
            </div>
          </div>

          {/* Card 3: Cultural */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200 hover:shadow-md transition-shadow group cursor-pointer">
            <div className="flex items-start justify-between mb-4">
              <div className="bg-purple-50 p-3 rounded-lg text-purple-600 group-hover:scale-110 transition-transform">
                <Theater className="h-6 w-6" />
              </div>
            </div>
            <h4 className="text-lg font-bold text-slate-900 mb-2">فرهنگی</h4>
            <p className="text-slate-500 text-sm leading-relaxed mb-4">
              برنامه‌های فرهنگی و اجتماعی، رویدادهای محلی.
            </p>
            <div className="w-full bg-slate-100 rounded-full h-2">
              <div className="bg-purple-600 h-2 rounded-full" style={{ width: '90%' }} />
            </div>
            <div className="flex justify-between mt-2 text-xs text-slate-500">
              <span>پیشرفت</span>
              <span>۹۰٪</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── Tab Navigation ─────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-1.5 inline-flex gap-1">
        <button
          onClick={handleNewTransaction}
          className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-2 ${currentView === 'wizard'
              ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
        >
          <FileText className="h-4 w-4" />
          تراکنش جدید
        </button>

        <button
          onClick={() => setCurrentView('my-transactions')}
          className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-2 ${currentView === 'my-transactions'
              ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
        >
          <List className="h-4 w-4" />
          تراکنش‌های من
        </button>

        <button
          onClick={() => setCurrentView('credit-requests')}
          className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-2 ${currentView === 'credit-requests'
              ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
        >
          <ShieldCheck className="h-4 w-4" />
          تامین اعتبار
        </button>
      </div>

      {/* ── Main Content ────────────────────────────────────── */}
      <div>
        {currentView === 'wizard' && (
          <TransactionWizard key={wizardKey} userId={user.id} />
        )}

        {currentView === 'my-transactions' && <MyTransactionsList userId={user.id} />}

        {currentView === 'credit-requests' && (
          <CreditRequestManager
            userId={user.id}
            userZoneId={userContext?.zone_id ?? undefined}
            userDeptId={undefined}
            userSectionId={userContext?.section_id ?? undefined}
            userZoneCode={userContext?.zone_code ?? undefined}
          />
        )}
      </div>
    </div>
  );
}
