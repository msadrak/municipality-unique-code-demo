import React, { useState, useEffect, useCallback } from 'react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from './ui/dialog';
import { Textarea } from './ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import {
  Building2, LogOut, Search, ChevronLeft, ChevronRight, Loader2,
  CheckCircle2, Clock, XCircle, Circle, ShieldCheck,
  Inbox, LayoutDashboard, BarChart3, FileText, ScrollText,
} from 'lucide-react';
import { TransactionReviewPanel } from './TransactionReviewPanel';
import { CreditRequestAdminPanel } from './CreditRequestAdminPanel';
import { WorkflowVisualizer } from './admin/WorkflowVisualizer';
import { fetchAdminTransactions, approveTransaction, rejectTransaction } from '../services/adapters';
import { api } from '../services/api';
import { formatRial, formatNumber } from '../lib/utils';

// ==========================================
// Types
// ==========================================

type User = {
  id: number;
  username: string;
  fullName: string;
  role: string;
  admin_level?: number;
};

type TransactionStatus =
  | 'DRAFT'
  | 'PENDING_L1'
  | 'PENDING_L2'
  | 'PENDING_L3'
  | 'PENDING_L4'
  | 'APPROVED'
  | 'REJECTED'
  | 'BOOKED';

type InboxItem = {
  id: number;
  entity_type: 'TRANSACTION' | 'CONTRACT';
  unique_code?: string;
  contract_number?: string;
  title?: string;
  status: string;
  current_approval_level?: number;
  amount?: number;
  total_amount?: number;
  beneficiary_name?: string;
  contractor_name?: string;
  zone_title?: string;
  dept_title?: string;
  budget_code?: string;
  budget_description?: string;
  created_by_name?: string;
  created_at?: string;
  description?: string;
  rejection_reason?: string;
};

type StatsData = {
  transactions: {
    total: number;
    pending_l1: number;
    pending_l2: number;
    pending_l3: number;
    pending_l4: number;
    approved: number;
    rejected: number;
    booked: number;
    my_pending: number;
  };
  contracts: {
    total: number;
    draft: number;
    pending_approval: number;
    approved: number;
    in_progress: number;
    completed: number;
    closed: number;
  };
  admin_level: number;
};

type OverviewData = {
  transactions: InboxItem[];
  contracts: InboxItem[];
};

type AdminDashboardProps = {
  user: User;
  onLogout: () => void;
  onNavigateToPublic: () => void;
  onNavigateToAccounting?: () => void;
};

// ==========================================
// Status Helpers
// ==========================================

const STATUS_TO_LEVEL: Record<string, number> = {
  DRAFT: 0,
  PENDING_L1: 1,
  PENDING_L2: 2,
  PENDING_L3: 3,
  PENDING_L4: 4,
  APPROVED: 5,
  BOOKED: 6,
  REJECTED: 0,
};

const APPROVAL_STEPS = [
  { level: 1, label: 'قسمت', status: 'PENDING_L1' as const },
  { level: 2, label: 'اداره', status: 'PENDING_L2' as const },
  { level: 3, label: 'حوزه', status: 'PENDING_L3' as const },
  { level: 4, label: 'ذی‌حساب', status: 'PENDING_L4' as const },
];

function formatCurrency(amount: number) {
  return formatNumber(amount);
}

// ==========================================
// RejectionModal
// ==========================================

function RejectionModal({
  isOpen,
  entityCode,
  onClose,
  onConfirm,
}: {
  isOpen: boolean;
  entityCode: string;
  onClose: () => void;
  onConfirm: (reason: string) => void;
}) {
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleConfirm = async () => {
    if (!reason.trim()) return;
    setIsSubmitting(true);
    try {
      await onConfirm(reason);
      setReason('');
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setReason('');
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-right">رد درخواست</DialogTitle>
          <DialogDescription className="text-right">
            درخواست با کد{' '}
            <span className="font-mono text-primary" dir="ltr">
              {entityCode}
            </span>{' '}
            رد خواهد شد.
          </DialogDescription>
        </DialogHeader>
        <div className="py-4">
          <Textarea
            placeholder="دلیل رد را بنویسید... (الزامی)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="min-h-[120px] text-right"
            dir="rtl"
          />
        </div>
        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={handleClose} disabled={isSubmitting}>
            انصراف
          </Button>
          <Button
            variant="destructive"
            onClick={handleConfirm}
            disabled={!reason.trim() || isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin ml-2" />
                در حال ارسال...
              </>
            ) : (
              'تایید رد درخواست'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ==========================================
// StatsCards — Section 3
// ==========================================

function StatsCards({ stats, adminLevel }: { stats: StatsData | null; adminLevel: number }) {
  if (!stats) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  const tx = stats.transactions;
  const cx = stats.contracts;

  return (
    <div className="space-y-6">
      {/* Transaction Stats */}
      <div>
        <h3 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
          <ScrollText className="h-4 w-4" />
          تراکنش‌ها
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
          <Card className="p-3">
            <p className="text-xs text-muted-foreground">کل</p>
            <p className="text-2xl mt-1">{tx.total}</p>
          </Card>
          <Card className="p-3 bg-amber-50 border-amber-200">
            <p className="text-xs text-amber-800">در انتظار من</p>
            <p className="text-2xl mt-1 text-amber-600">{tx.my_pending}</p>
          </Card>
          <Card className="p-3">
            <p className="text-xs text-muted-foreground">سطح ۱</p>
            <p className="text-xl mt-1 text-amber-500">{tx.pending_l1}</p>
          </Card>
          <Card className="p-3">
            <p className="text-xs text-muted-foreground">سطح ۲</p>
            <p className="text-xl mt-1 text-amber-500">{tx.pending_l2}</p>
          </Card>
          <Card className="p-3">
            <p className="text-xs text-muted-foreground">سطح ۳</p>
            <p className="text-xl mt-1 text-orange-500">{tx.pending_l3}</p>
          </Card>
          <Card className="p-3">
            <p className="text-xs text-muted-foreground">سطح ۴</p>
            <p className="text-xl mt-1 text-orange-600">{tx.pending_l4}</p>
          </Card>
          <Card className="p-3 bg-green-50 border-green-200">
            <p className="text-xs text-green-800">تایید شده</p>
            <p className="text-2xl mt-1 text-green-600">{tx.approved}</p>
          </Card>
          <Card className="p-3 bg-red-50 border-red-200">
            <p className="text-xs text-red-800">رد شده</p>
            <p className="text-2xl mt-1 text-red-600">{tx.rejected}</p>
          </Card>
        </div>
      </div>

      {/* Contract Stats */}
      <div>
        <h3 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
          <FileText className="h-4 w-4" />
          قراردادها
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <Card className="p-3">
            <p className="text-xs text-muted-foreground">کل</p>
            <p className="text-2xl mt-1">{cx.total}</p>
          </Card>
          <Card className="p-3">
            <p className="text-xs text-muted-foreground">پیش‌نویس</p>
            <p className="text-xl mt-1 text-gray-500">{cx.draft}</p>
          </Card>
          <Card className="p-3 bg-amber-50 border-amber-200">
            <p className="text-xs text-amber-800">در انتظار تایید</p>
            <p className="text-xl mt-1 text-amber-600">{cx.pending_approval}</p>
          </Card>
          <Card className="p-3 bg-blue-50 border-blue-200">
            <p className="text-xs text-blue-800">در حال اجرا</p>
            <p className="text-xl mt-1 text-blue-600">{cx.in_progress}</p>
          </Card>
          <Card className="p-3 bg-green-50 border-green-200">
            <p className="text-xs text-green-800">تکمیل شده</p>
            <p className="text-xl mt-1 text-green-600">{cx.completed}</p>
          </Card>
          <Card className="p-3">
            <p className="text-xs text-muted-foreground">بسته شده</p>
            <p className="text-xl mt-1">{cx.closed}</p>
          </Card>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// InboxTable — Section 1
// ==========================================

function InboxTable({
  items,
  loading,
  adminLevel,
  onApprove,
  onRejectClick,
  onRowClick,
}: {
  items: InboxItem[];
  loading: boolean;
  adminLevel: number;
  onApprove: (id: number) => void;
  onRejectClick: (item: InboxItem) => void;
  onRowClick: (item: InboxItem) => void;
}) {
  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <Inbox className="h-10 w-10 mx-auto mb-3 opacity-40" />
        <p>کارتابل شما خالی است</p>
        <p className="text-xs mt-1">هیچ موردی در انتظار تایید شما نیست</p>
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="text-right w-[80px]">نوع</TableHead>
          <TableHead className="text-right">شناسه</TableHead>
          <TableHead className="text-right">وضعیت گردش کار</TableHead>
          <TableHead className="text-right">مبلغ (ریال)</TableHead>
          <TableHead className="text-right">ذینفع / پیمانکار</TableHead>
          <TableHead className="text-right">ایجادکننده</TableHead>
          <TableHead className="text-right">تاریخ</TableHead>
          <TableHead className="text-right w-[180px]">اقدام</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item) => {
          const isTx = item.entity_type === 'TRANSACTION';
          const code = isTx ? item.unique_code : item.contract_number;
          const amount = isTx ? item.amount : item.total_amount;
          const name = isTx ? item.beneficiary_name : item.contractor_name;
          const currentLevel = STATUS_TO_LEVEL[item.status] ?? 0;
          const canAct = isTx && adminLevel === currentLevel && item.status !== 'REJECTED' && item.status !== 'APPROVED';

          return (
            <TableRow
              key={`${item.entity_type}-${item.id}`}
              className="cursor-pointer hover:bg-muted/50"
              onClick={() => onRowClick(item)}
            >
              <TableCell>
                <Badge variant={isTx ? 'default' : 'secondary'} className="text-[10px]">
                  {isTx ? 'تراکنش' : 'قرارداد'}
                </Badge>
              </TableCell>
              <TableCell className="font-mono text-sm" dir="ltr">
                {code || '---'}
              </TableCell>
              <TableCell>
                <WorkflowVisualizer
                  status={item.status}
                  entityType={item.entity_type}
                  compact
                />
              </TableCell>
              <TableCell className="font-mono-num">
                {amount ? formatRial(amount) : '-'}
              </TableCell>
              <TableCell className="max-w-[150px] truncate">{name || '-'}</TableCell>
              <TableCell>{item.created_by_name || '-'}</TableCell>
              <TableCell className="text-sm">{item.created_at?.split(' - ')[0] || '-'}</TableCell>
              <TableCell>
                {canAct && (
                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      className="h-7 px-2 bg-green-600 hover:bg-green-700"
                      onClick={(e) => {
                        e.stopPropagation();
                        onApprove(item.id);
                      }}
                    >
                      تایید
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      className="h-7 px-2"
                      onClick={(e) => {
                        e.stopPropagation();
                        onRejectClick(item);
                      }}
                    >
                      رد
                    </Button>
                  </div>
                )}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

// ==========================================
// OverviewPanel — Section 2
// ==========================================

function OverviewPanel({
  overview,
  loading,
}: {
  overview: OverviewData | null;
  loading: boolean;
}) {
  if (loading || !overview) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  const allItems = [
    ...overview.transactions,
    ...overview.contracts,
  ];

  if (allItems.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <LayoutDashboard className="h-10 w-10 mx-auto mb-3 opacity-40" />
        <p>هیچ مورد فعالی وجود ندارد</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {allItems.map((item) => {
        const isTx = item.entity_type === 'TRANSACTION';
        const code = isTx ? item.unique_code : item.contract_number;
        const amount = isTx ? item.amount : item.total_amount;

        return (
          <Card
            key={`${item.entity_type}-${item.id}`}
            className="p-4 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant={isTx ? 'default' : 'secondary'} className="text-[10px]">
                    {isTx ? 'تراکنش' : 'قرارداد'}
                  </Badge>
                  <span className="font-mono text-sm" dir="ltr">
                    {code || '---'}
                  </span>
                  {item.title && (
                    <span className="text-sm text-muted-foreground truncate">
                      {item.title}
                    </span>
                  )}
                </div>
                <WorkflowVisualizer
                  status={item.status}
                  entityType={item.entity_type}
                />
              </div>
              <div className="text-left flex-shrink-0">
                <p className="font-mono-num text-sm">
                  {amount ? formatRial(amount) : '-'}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {isTx ? item.beneficiary_name : item.contractor_name}
                </p>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}

// ==========================================
// Main AdminDashboard Component
// ==========================================

type AdminMainTab = 'inbox' | 'overview' | 'stats' | 'credit-requests';

export function AdminDashboard({
  user,
  onLogout,
  onNavigateToPublic,
  onNavigateToAccounting,
}: AdminDashboardProps) {
  const [activeTab, setActiveTab] = useState<AdminMainTab>('inbox');
  const [loading, setLoading] = useState(false);

  // Inbox state
  const [inboxItems, setInboxItems] = useState<InboxItem[]>([]);
  const [inboxLoading, setInboxLoading] = useState(true);

  // Overview state
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(true);

  // Stats state
  const [stats, setStats] = useState<StatsData | null>(null);

  // Review panel
  const [selectedTransaction, setSelectedTransaction] = useState<any>(null);

  // Rejection modal
  const [rejectionModalOpen, setRejectionModalOpen] = useState(false);
  const [itemToReject, setItemToReject] = useState<InboxItem | null>(null);

  const [error, setError] = useState<string | null>(null);
  const adminLevel = user.admin_level || 0;

  const getRoleLabel = () => {
    if (user.role === 'inspector') return 'ناظر / بازرسی';
    if (user.role === 'admin' || (user.role || '').startsWith('ADMIN_L')) {
      switch (user.admin_level) {
        case 5: return 'طراح و راهبر سیستم';
        case 4: return 'ذی‌حساب (تایید نهایی)';
        case 3: return 'مدیر حوزه / منطقه';
        case 2: return 'رئیس اداره';
        case 1: return 'مسئول قسمت';
        default: return 'مدیر سیستم';
      }
    }
    return 'کاربر';
  };

  // --- Data Loaders ---

  const loadInbox = useCallback(async () => {
    setInboxLoading(true);
    try {
      const data = await api.get<{
        items: InboxItem[];
        total_transactions: number;
        total_contracts: number;
      }>('/admin/inbox');
      setInboxItems(data.items || []);
    } catch (err) {
      console.error('Failed to load inbox:', err);
      setError('خطا در بارگیری کارتابل');
    } finally {
      setInboxLoading(false);
    }
  }, []);

  const loadOverview = useCallback(async () => {
    setOverviewLoading(true);
    try {
      const data = await api.get<{
        transactions: InboxItem[];
        contracts: InboxItem[];
      }>('/admin/overview');
      setOverview({
        transactions: data.transactions || [],
        contracts: data.contracts || [],
      });
    } catch (err) {
      console.error('Failed to load overview:', err);
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const data = await api.get<StatsData>('/admin/stats');
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadInbox();
    loadStats();
  }, [loadInbox, loadStats]);

  // Load overview when tab is activated
  useEffect(() => {
    if (activeTab === 'overview' && !overview) {
      loadOverview();
    }
  }, [activeTab, overview, loadOverview]);

  // --- Actions ---

  const handleApprove = async (txId: number) => {
    try {
      setLoading(true);
      await approveTransaction(txId);
      await Promise.all([loadInbox(), loadStats()]);
      setSelectedTransaction(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'خطا در تایید');
    } finally {
      setLoading(false);
    }
  };

  const handleRejectClick = (item: InboxItem) => {
    setItemToReject(item);
    setRejectionModalOpen(true);
  };

  const handleRejectConfirm = async (reason: string) => {
    if (!itemToReject) return;
    try {
      setLoading(true);
      await rejectTransaction(itemToReject.id, reason);
      await Promise.all([loadInbox(), loadStats()]);
      setSelectedTransaction(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'خطا در رد');
    } finally {
      setLoading(false);
      setItemToReject(null);
    }
  };

  const handleRowClick = (item: InboxItem) => {
    if (item.entity_type === 'TRANSACTION') {
      setSelectedTransaction({
        id: item.id,
        uniqueCode: item.unique_code,
        status: item.status,
        currentApprovalLevel: item.current_approval_level,
        amount: item.amount,
        budgetCode: item.budget_code,
        budgetDescription: item.budget_description,
        beneficiaryName: item.beneficiary_name,
        createdBy: item.created_by_name,
        createdAt: item.created_at,
        zoneName: item.zone_title,
        rejectionReason: item.rejection_reason,
      });
    }
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
                <h1 className="text-lg font-semibold">مرکز فرماندهی مدیریت</h1>
                <p className="text-sm text-muted-foreground">شهرداری اصفهان - معاونت مالی</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="text-left">
                <p className="text-sm font-medium">{user.fullName}</p>
                <div className="flex items-center gap-1 justify-end">
                  <Badge
                    variant="outline"
                    className="text-[10px] h-5 px-1 bg-primary/5 border-primary/20"
                  >
                    {getRoleLabel()}
                  </Badge>
                </div>
              </div>
              {onNavigateToAccounting && (
                <Button variant="outline" size="sm" onClick={onNavigateToAccounting}>
                  <BarChart3 className="h-4 w-4 ml-1" />
                  صندوق حسابداری
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={onLogout}>
                <LogOut className="h-4 w-4 ml-2" />
                خروج
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div className="container mx-auto px-4 pt-4">
          <div className="bg-red-50 border border-red-200 rounded-md p-3 flex items-center justify-between">
            <p className="text-sm text-red-700">{error}</p>
            <Button variant="ghost" size="sm" onClick={() => setError(null)}>
              <XCircle className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Quick Stats Bar */}
      {stats && (
        <div className="bg-card border-b">
          <div className="container mx-auto px-4 py-2">
            <div className="flex items-center gap-6 text-sm">
              <span className="text-muted-foreground">خلاصه:</span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-2 h-2 rounded-full bg-amber-400" />
                در انتظار من:
                <strong className="text-amber-600">{stats.transactions.my_pending}</strong>
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-2 h-2 rounded-full bg-amber-300" />
                L1: {stats.transactions.pending_l1}
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-2 h-2 rounded-full bg-amber-400" />
                L2: {stats.transactions.pending_l2}
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-2 h-2 rounded-full bg-orange-400" />
                L3: {stats.transactions.pending_l3}
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-2 h-2 rounded-full bg-orange-500" />
                L4: {stats.transactions.pending_l4}
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-2 h-2 rounded-full bg-green-500" />
                تایید شده: {stats.transactions.approved}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Main Tabs */}
      <main className="container mx-auto px-4 py-6">
        <Tabs
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as AdminMainTab)}
          dir="rtl"
        >
          <TabsList className="mb-6">
            <TabsTrigger value="inbox" className="gap-1.5">
              <Inbox className="h-4 w-4" />
              کارتابل من
              {stats && stats.transactions.my_pending > 0 && (
                <Badge className="h-5 px-1.5 text-[10px] bg-amber-500 text-white">
                  {stats.transactions.my_pending}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="overview" className="gap-1.5">
              <LayoutDashboard className="h-4 w-4" />
              نمای کلی سیستم
            </TabsTrigger>
            <TabsTrigger value="stats" className="gap-1.5">
              <BarChart3 className="h-4 w-4" />
              آمار
            </TabsTrigger>
            <TabsTrigger value="credit-requests" className="gap-1.5">
              <ShieldCheck className="h-4 w-4" />
              تامین اعتبار
            </TabsTrigger>
          </TabsList>

          {/* Tab 1: Inbox (Cartable) */}
          <TabsContent value="inbox">
            <Card>
              <div className="p-4 border-b">
                <h2 className="text-base font-medium flex items-center gap-2">
                  <Inbox className="h-5 w-5 text-primary" />
                  موارد در انتظار تایید شما
                </h2>
                <p className="text-xs text-muted-foreground mt-1">
                  {adminLevel > 0
                    ? `سطح ${adminLevel} - فقط مواردی که نیاز به تایید سطح شما دارند نمایش داده می‌شوند`
                    : 'تمام موارد در انتظار نمایش داده می‌شوند'}
                </p>
              </div>
              <InboxTable
                items={inboxItems}
                loading={inboxLoading}
                adminLevel={adminLevel}
                onApprove={handleApprove}
                onRejectClick={handleRejectClick}
                onRowClick={handleRowClick}
              />
            </Card>
          </TabsContent>

          {/* Tab 2: System Overview */}
          <TabsContent value="overview">
            <Card className="p-4">
              <h2 className="text-base font-medium flex items-center gap-2 mb-4">
                <LayoutDashboard className="h-5 w-5 text-primary" />
                نمای کلی — کجا گیر کرده؟
              </h2>
              <p className="text-xs text-muted-foreground mb-4">
                تراکنش‌ها و قراردادهای فعال به همراه وضعیت فعلی آن‌ها در گردش کار
              </p>
              <OverviewPanel overview={overview} loading={overviewLoading} />
            </Card>
          </TabsContent>

          {/* Tab 3: Stats */}
          <TabsContent value="stats">
            <StatsCards stats={stats} adminLevel={adminLevel} />
          </TabsContent>

          {/* Tab 4: Credit Requests */}
          <TabsContent value="credit-requests">
            <CreditRequestAdminPanel />
          </TabsContent>
        </Tabs>
      </main>

      {/* Side Panel for Review */}
      {selectedTransaction && (
        <TransactionReviewPanel
          transaction={selectedTransaction}
          onClose={() => setSelectedTransaction(null)}
          onApprove={(id) => handleApprove(id)}
          onReject={(id, reason) => {
            loadInbox();
            loadStats();
          }}
        />
      )}

      {/* Rejection Modal */}
      <RejectionModal
        isOpen={rejectionModalOpen}
        entityCode={
          itemToReject
            ? itemToReject.unique_code || itemToReject.contract_number || ''
            : ''
        }
        onClose={() => {
          setRejectionModalOpen(false);
          setItemToReject(null);
        }}
        onConfirm={handleRejectConfirm}
      />
    </div>
  );
}
