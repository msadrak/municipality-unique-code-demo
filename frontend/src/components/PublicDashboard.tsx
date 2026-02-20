import React, { useState } from 'react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Building2, LogIn, Search, TrendingUp, Wallet, FileText, BarChart3 } from 'lucide-react';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from './ui/accordion';
import { formatNumber } from '../lib/utils';

type PublicDashboardProps = {
  onNavigateToLogin: () => void;
};

// Mock aggregate data
const BUDGET_SUMMARY = {
  totalApproved: 150000000000,
  totalAllocated: 135000000000,
  totalSpent: 98000000000,
  totalReserved: 22000000000,
  totalRemaining: 15000000000,
};

const ZONE_BUDGETS = [
  { zone: 'منطقه ۱', allocated: 15000000000, spent: 11000000000, remaining: 4000000000 },
  { zone: 'منطقه ۲', allocated: 18000000000, spent: 13000000000, remaining: 5000000000 },
  { zone: 'منطقه ۵', allocated: 12000000000, spent: 9000000000, remaining: 3000000000 },
  { zone: 'معاونت مالی', allocated: 25000000000, spent: 18000000000, remaining: 7000000000 },
];

const RECENT_CODES = [
  { code: '20-02-015-11020401-001-01-000-A1B2C3-001-1403-001', amount: 5000000, date: '1403/09/20' },
  { code: '20-02-015-11020501-001-01-000-B2C3D4-002-1403-002', amount: 3000000, date: '1403/09/21' },
  { code: '01-01-020-52010101-002-02-001-C3D4E5-004-1403-003', amount: 8000000, date: '1403/09/19' },
  { code: '05-02-010-11030201-001-01-000-D4E5F6-003-1403-004', amount: 2500000, date: '1403/09/18' },
];

const TRANSACTION_STATS = {
  total: 1247,
  approved: 856,
  pending: 198,
  rejected: 43,
  paid: 150,
};

export function PublicDashboard({ onNavigateToLogin }: PublicDashboardProps) {
  const [searchCode, setSearchCode] = useState('');

  const formatBillion = (amount: number) => {
    return (amount / 1000000000).toFixed(1) + ' میلیارد';
  };

  const getUsagePercentage = (spent: number, allocated: number) => {
    return Math.round((spent / allocated) * 100);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b border-border">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-primary p-2 rounded">
                <Building2 className="h-6 w-6 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-lg">داشبورد عمومی سامانه مالی</h1>
                <p className="text-sm text-muted-foreground">شهرداری اصفهان - معاونت مالی و اقتصادی</p>
              </div>
            </div>
            
            <Button onClick={onNavigateToLogin}>
              <LogIn className="h-4 w-4 ml-2" />
              ورود به سامانه
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          {/* Welcome Banner */}
          <Card className="p-6 bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
            <div className="flex items-start gap-4">
              <div className="bg-primary p-3 rounded-lg">
                <BarChart3 className="h-8 w-8 text-primary-foreground" />
              </div>
              <div className="flex-1">
                <h2>سامانه تولید شناسه یکتای مالی</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  این داشبورد اطلاعات عمومی بودجه و تراکنش‌های مالی شهرداری اصفهان را به صورت خلاصه نمایش می‌دهد
                </p>
              </div>
            </div>
          </Card>

          {/* Tabs */}
          <Tabs defaultValue="overview" dir="rtl">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="overview">
                <TrendingUp className="h-4 w-4 ml-2" />
                آمار کلی
              </TabsTrigger>
              <TabsTrigger value="budget">
                <Wallet className="h-4 w-4 ml-2" />
                وضعیت بودجه
              </TabsTrigger>
              <TabsTrigger value="codes">
                <FileText className="h-4 w-4 ml-2" />
                کدهای یکتا
              </TabsTrigger>
            </TabsList>

            {/* Overview Tab */}
            <TabsContent value="overview" className="space-y-6">
              {/* Budget Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="p-4">
                  <p className="text-sm text-muted-foreground">بودجه مصوب</p>
                  <p className="text-2xl mt-2">{formatBillion(BUDGET_SUMMARY.totalApproved)}</p>
                  <p className="text-xs text-muted-foreground mt-1">ریال</p>
                </Card>
                <Card className="p-4">
                  <p className="text-sm text-muted-foreground">بودجه تخصیص یافته</p>
                  <p className="text-2xl mt-2">{formatBillion(BUDGET_SUMMARY.totalAllocated)}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {Math.round((BUDGET_SUMMARY.totalAllocated / BUDGET_SUMMARY.totalApproved) * 100)}٪ مصوب
                  </p>
                </Card>
                <Card className="p-4 bg-blue-50 border-blue-200">
                  <p className="text-sm text-blue-800">هزینه شده</p>
                  <p className="text-2xl mt-2 text-blue-600">{formatBillion(BUDGET_SUMMARY.totalSpent)}</p>
                  <p className="text-xs text-blue-700 mt-1">
                    {Math.round((BUDGET_SUMMARY.totalSpent / BUDGET_SUMMARY.totalAllocated) * 100)}٪ تخصیص
                  </p>
                </Card>
                <Card className="p-4 bg-green-50 border-green-200">
                  <p className="text-sm text-green-800">مانده بودجه</p>
                  <p className="text-2xl mt-2 text-green-600">{formatBillion(BUDGET_SUMMARY.totalRemaining)}</p>
                  <p className="text-xs text-green-700 mt-1">قابل استفاده</p>
                </Card>
              </div>

              {/* Transaction Stats */}
              <Card className="p-6">
                <h3 className="mb-4">آمار تراکنش‌ها</h3>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
                  <div>
                    <p className="text-3xl">{TRANSACTION_STATS.total}</p>
                    <p className="text-sm text-muted-foreground mt-1">کل تراکنش‌ها</p>
                  </div>
                  <div>
                    <p className="text-3xl text-green-600">{TRANSACTION_STATS.approved}</p>
                    <p className="text-sm text-muted-foreground mt-1">تایید شده</p>
                  </div>
                  <div>
                    <p className="text-3xl text-amber-600">{TRANSACTION_STATS.pending}</p>
                    <p className="text-sm text-muted-foreground mt-1">در انتظار</p>
                  </div>
                  <div>
                    <p className="text-3xl text-red-600">{TRANSACTION_STATS.rejected}</p>
                    <p className="text-sm text-muted-foreground mt-1">رد شده</p>
                  </div>
                  <div>
                    <p className="text-3xl text-blue-600">{TRANSACTION_STATS.paid}</p>
                    <p className="text-sm text-muted-foreground mt-1">پرداخت شده</p>
                  </div>
                </div>
              </Card>
            </TabsContent>

            {/* Budget Tab */}
            <TabsContent value="budget" className="space-y-6">
              <Card className="p-6">
                <h3 className="mb-4">وضعیت بودجه مناطق و معاونت‌ها</h3>
                <div className="space-y-4">
                  {ZONE_BUDGETS.map((zone, index) => (
                    <div key={index} className="border-b pb-4 last:border-0">
                      <div className="flex items-center justify-between mb-2">
                        <h4>{zone.zone}</h4>
                        <span className="text-sm text-muted-foreground">
                          {getUsagePercentage(zone.spent, zone.allocated)}٪ مصرف شده
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-3 text-sm">
                        <div>
                          <p className="text-muted-foreground">تخصیص</p>
                          <p className="font-mono-num">{formatNumber(zone.allocated)} ریال</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">هزینه شده</p>
                          <p className="font-mono-num text-blue-600">{formatNumber(zone.spent)} ریال</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">مانده</p>
                          <p className="font-mono-num text-green-600">{formatNumber(zone.remaining)} ریال</p>
                        </div>
                      </div>
                      <div className="mt-2 h-2 bg-muted rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-blue-600"
                          style={{ width: `${getUsagePercentage(zone.spent, zone.allocated)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </TabsContent>

            {/* Codes Tab */}
            <TabsContent value="codes" className="space-y-6">
              {/* Search */}
              <Card className="p-4">
                <div className="relative">
                  <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="جستجوی کد یکتا..."
                    value={searchCode}
                    onChange={(e) => setSearchCode(e.target.value)}
                    className="pr-10"
                    dir="ltr"
                  />
                </div>
              </Card>

              {/* Recent Codes */}
              <Card className="p-6">
                <h3 className="mb-4">کدهای یکتای اخیر</h3>
                <div className="space-y-3">
                  {RECENT_CODES.map((item, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <p className="font-mono text-sm mb-1" dir="ltr">{item.code}</p>
                          <p className="text-sm text-muted-foreground">{item.date}</p>
                        </div>
                        <div className="text-left">
                          <p className="font-mono-num">{formatNumber(item.amount)} ریال</p>
                          <Badge className="bg-green-600 text-white mt-1">تایید شده</Badge>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Code Structure Info */}
              <Card className="p-6">
                <h3 className="mb-4">ساختار کد یکتای ۱۱ بخشی</h3>
                <Accordion type="single" collapsible>
                  <AccordionItem value="structure">
                    <AccordionTrigger>
                      توضیحات ساختار کد یکتا
                    </AccordionTrigger>
                    <AccordionContent>
                      <div className="space-y-3 text-sm">
                        <p className="text-muted-foreground">
                          هر کد یکتا از ۱۱ بخش تشکیل شده که اطلاعات زیر را شامل می‌شود:
                        </p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                          <div className="flex gap-2">
                            <span className="text-muted-foreground">۱.</span>
                            <span>کد منطقه/معاونت</span>
                          </div>
                          <div className="flex gap-2">
                            <span className="text-muted-foreground">۲.</span>
                            <span>کد اداره</span>
                          </div>
                          <div className="flex gap-2">
                            <span className="text-muted-foreground">۳.</span>
                            <span>کد قسمت</span>
                          </div>
                          <div className="flex gap-2">
                            <span className="text-muted-foreground">۴.</span>
                            <span>کد بودجه</span>
                          </div>
                          <div className="flex gap-2">
                            <span className="text-muted-foreground">۵.</span>
                            <span>کد مرکز هزینه</span>
                          </div>
                          <div className="flex gap-2">
                            <span className="text-muted-foreground">۶.</span>
                            <span>کد اقدام مستمر</span>
                          </div>
                          <div className="flex gap-2">
                            <span className="text-muted-foreground">۷.</span>
                            <span>فعالیت خاص</span>
                          </div>
                          <div className="flex gap-2">
                            <span className="text-muted-foreground">۸.</span>
                            <span>هش ذینفع</span>
                          </div>
                          <div className="flex gap-2">
                            <span className="text-muted-foreground">۹.</span>
                            <span>رویداد مالی</span>
                          </div>
                          <div className="flex gap-2">
                            <span className="text-muted-foreground">۱۰.</span>
                            <span>سال مالی</span>
                          </div>
                          <div className="flex gap-2">
                            <span className="text-muted-foreground">۱۱.</span>
                            <span>شماره ترتیب</span>
                          </div>
                        </div>
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Footer Info */}
          <Card className="p-4 bg-muted/30 text-center text-sm text-muted-foreground">
            <p>شهرداری اصفهان - معاونت مالی و اقتصادی</p>
            <p className="mt-1">سامانه تولید شناسه یکتای مالی | نسخه ۱.۰.۰</p>
          </Card>
        </div>
      </main>
    </div>
  );
}
