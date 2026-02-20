import React, { useEffect, useState, useCallback } from 'react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Building2, LogOut, FileText, List, Loader2, AlertCircle, RefreshCw, ArrowRight, ShieldCheck } from 'lucide-react';
import { TransactionWizard } from './TransactionWizard';
import { MyTransactionsList } from './MyTransactionsList';
import { DashboardActivityCard } from './DashboardActivityCard';
import { CreditRequestManager } from './CreditRequestManager';
import { useTransactionStore } from '../stores/useTransactionStore';
import { AllowedActivity } from '../types/dashboard';

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

// Views: activity-selection (Grid), wizard (in-progress transaction), my-transactions, credit-requests
type View = 'activity-selection' | 'wizard' | 'my-transactions' | 'credit-requests';

export function UserPortal({ user, onLogout, onNavigateToPublic }: UserPortalProps) {
  const [currentView, setCurrentView] = useState<View>('activity-selection');

  // Atomic Zustand selectors
  const dashboardData = useTransactionStore((s) => s.dashboardData);
  const isLoading = useTransactionStore((s) => s.isLoading);
  const error = useTransactionStore((s) => s.error);
  const selectedActivity = useTransactionStore((s) => s.selectedActivity);
  const fetchDashboardInit = useTransactionStore((s) => s.fetchDashboardInit);
  const startWizard = useTransactionStore((s) => s.startWizard);
  const closeWizard = useTransactionStore((s) => s.closeWizard);

  // Derive values from dashboardData
  const userContext = dashboardData?.user_context;
  const subsystem = dashboardData?.subsystem;
  const activities = dashboardData?.allowed_activities ?? [];
  const hasSubsystem = dashboardData?.has_subsystem ?? false;
  const message = dashboardData?.message;

  // Fetch dashboard data on mount
  useEffect(() => {
    fetchDashboardInit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle activity selection - THIS IS STEP 1
  const handleActivityClick = useCallback((activity: AllowedActivity) => {
    startWizard(activity);
    setCurrentView('wizard'); // Switch to wizard view
  }, [startWizard]);

  // Handle back to activity selection
  const handleBackToActivities = useCallback(() => {
    closeWizard();
    setCurrentView('activity-selection');
  }, [closeWizard]);

  // Handle retry
  const handleRetry = useCallback(() => {
    fetchDashboardInit();
  }, [fetchDashboardInit]);

  // LOADING STATE
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-lg text-muted-foreground">در حال بارگذاری...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header - Government Identity */}
      <header className="bg-card border-b border-border">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-primary p-2 rounded">
                <Building2 className="h-6 w-6 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-lg">پرتال کاربری</h1>
                <p className="text-sm text-muted-foreground">
                  {userContext?.section_title
                    ? `${userContext.zone_title ?? ''} - ${userContext.section_title}`
                    : 'شهرداری اصفهان - معاونت مالی'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="text-left">
                <p className="text-sm">{user.fullName}</p>
                <p className="text-xs text-muted-foreground">
                  {subsystem?.title ?? 'کاربر مالی'}
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={onLogout}>
                <LogOut className="h-4 w-4 ml-2" />
                خروج
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs - Two Main Actions */}
      <div className="bg-card border-b border-border">
        <div className="container mx-auto px-4">
          <div className="flex gap-1">
            {/* Tab 1: New Transaction (Activity Grid = Step 1) */}
            <button
              onClick={() => {
                closeWizard();
                setCurrentView('activity-selection');
              }}
              className={`px-6 py-3 border-b-2 transition-colors ${currentView === 'activity-selection' || currentView === 'wizard'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
            >
              <FileText className="h-4 w-4 inline-block ml-2" />
              تراکنش جدید
            </button>

            {/* Tab 2: My Transactions */}
            <button
              onClick={() => setCurrentView('my-transactions')}
              className={`px-6 py-3 border-b-2 transition-colors ${currentView === 'my-transactions'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
            >
              <List className="h-4 w-4 inline-block ml-2" />
              تراکنش‌های من
            </button>

            {/* Tab 3: Credit Requests (Stage 1 Gateway) */}
            <button
              onClick={() => setCurrentView('credit-requests')}
              className={`px-6 py-3 border-b-2 transition-colors ${currentView === 'credit-requests'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
            >
              <ShieldCheck className="h-4 w-4 inline-block ml-2" />
              تامین اعتبار
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {/* Activity Selection View (Step 1 - Choose Activity) */}
        {currentView === 'activity-selection' && (
          <div>
            {/* Error State */}
            {error && (
              <Card className="border-destructive/50">
                <CardContent className="flex flex-col items-center py-8">
                  <AlertCircle className="h-12 w-12 text-destructive mb-4" />
                  <p className="text-destructive font-medium mb-2">خطا در بارگذاری</p>
                  <p className="text-sm text-muted-foreground mb-4">{error}</p>
                  <Button onClick={handleRetry} variant="outline">
                    <RefreshCw className="h-4 w-4 ml-2" />
                    تلاش مجدد
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* No Section Assigned */}
            {!error && !hasSubsystem && message && (
              <Card>
                <CardContent className="flex flex-col items-center py-12">
                  <Building2 className="h-16 w-16 text-muted-foreground/50 mb-4" />
                  <p className="text-lg text-muted-foreground">{message}</p>
                  <p className="text-sm text-muted-foreground mt-2">
                    لطفاً با مدیر سیستم تماس بگیرید
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Activities Grid - This IS Step 1 */}
            {!error && hasSubsystem && (
              <div>
                {/* Section Header - Emphasize this is Step 1 */}
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="secondary" className="text-xs">
                        مرحله ۱
                      </Badge>
                      <h2 className="text-xl font-semibold">انتخاب نوع فعالیت</h2>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {subsystem
                        ? `یکی از فعالیت‌های ${subsystem.title} را انتخاب کنید`
                        : 'یکی از فعالیت‌های زیر را انتخاب کنید'}
                    </p>
                  </div>
                  <Badge variant="outline" className="text-sm">
                    {activities.length} فعالیت
                  </Badge>
                </div>

                {/* Activities Grid */}
                {activities.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {activities.map((activity) => (
                      <DashboardActivityCard
                        key={activity.id}
                        activity={activity}
                        onClick={() => handleActivityClick(activity)}
                      />
                    ))}
                  </div>
                ) : (
                  <Card>
                    <CardContent className="flex flex-col items-center py-12">
                      <FileText className="h-12 w-12 text-muted-foreground/50 mb-4" />
                      <p className="text-lg text-muted-foreground mb-2">
                        فعالیتی برای قسمت شما تعریف نشده است
                      </p>
                      <p className="text-sm text-muted-foreground">
                        لطفاً با مدیر سیستم تماس بگیرید تا فعالیت‌های مجاز را تنظیم کند
                      </p>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}

            {/* Initial empty state */}
            {!error && !hasSubsystem && !message && (
              <Card>
                <CardContent className="flex flex-col items-center py-12">
                  <Loader2 className="h-12 w-12 text-muted-foreground/50 mb-4 animate-spin" />
                  <p className="text-lg text-muted-foreground">در انتظار دریافت اطلاعات...</p>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* Wizard View (Steps 2+) */}
        {currentView === 'wizard' && (
          <div>
            {/* Back Button with Activity Name */}
            <div className="mb-6 flex items-center gap-3">
              <Button variant="ghost" size="sm" onClick={handleBackToActivities} className="gap-2">
                <ArrowRight className="h-4 w-4" />
                بازگشت به انتخاب فعالیت
              </Button>
              {selectedActivity && (
                <>
                  <span className="text-muted-foreground">|</span>
                  <Badge variant="secondary" className="gap-1">
                    <FileText className="h-3 w-3" />
                    {selectedActivity.title}
                  </Badge>
                </>
              )}
            </div>

            {/* TransactionWizard - Starts at Step 2+ because Step 1 is already done */}
            <TransactionWizard userId={user.id} />
          </div>
        )}

        {/* My Transactions View */}
        {currentView === 'my-transactions' && <MyTransactionsList userId={user.id} />}

        {/* Credit Requests View (Stage 1 Gateway) */}
        {currentView === 'credit-requests' && (
          <CreditRequestManager
            userId={user.id}
            userZoneId={userContext?.zone_id ?? undefined}
            userDeptId={undefined}
            userSectionId={userContext?.section_id ?? undefined}
            userZoneCode={userContext?.zone_code ?? undefined}
          />
        )}
      </main>
    </div>
  );
}
