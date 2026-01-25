import React, { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from './ui/dialog';
import { Textarea } from './ui/textarea';
import { Building2, LogOut, Search, ChevronLeft, ChevronRight, Loader2, CheckCircle2, Clock, XCircle, Circle } from 'lucide-react';
import { TransactionReviewPanel } from './TransactionReviewPanel';
import { fetchAdminTransactions, approveTransaction, rejectTransaction } from '../services/adapters';

type User = {
  id: number;
  username: string;
  fullName: string;
  role: string;
  admin_level?: number;
};

// Updated Transaction type with approval workflow statuses
type TransactionStatus =
  | 'PENDING_L1'
  | 'PENDING_L2'
  | 'PENDING_L3'
  | 'PENDING_L4'
  | 'APPROVED'
  | 'REJECTED';

type Transaction = {
  id: number;
  uniqueCode: string;
  status: TransactionStatus;
  currentApprovalLevel: number; // 1=Section, 2=Office, 3=Zone, 4=Finance
  amount: number;
  budgetCode?: string;
  budgetDescription?: string;
  beneficiaryName?: string;
  createdBy?: string;
  createdAt?: string;
  zoneName?: string;
  departmentName?: string;
  sectionName?: string;
  financialEventName?: string;
  rejectionReason?: string;
};

type AdminDashboardProps = {
  user: User;
  onLogout: () => void;
  onNavigateToPublic: () => void;
  onNavigateToAccounting?: () => void;
};

// Map status to approval level
const STATUS_TO_LEVEL: Record<TransactionStatus, number> = {
  'PENDING_L1': 1,
  'PENDING_L2': 2,
  'PENDING_L3': 3,
  'PENDING_L4': 4,
  'APPROVED': 5,
  'REJECTED': 0,
};

// Approval steps configuration
const APPROVAL_STEPS = [
  { level: 1, label: 'قسمت', status: 'PENDING_L1' as const },
  { level: 2, label: 'اداره', status: 'PENDING_L2' as const },
  { level: 3, label: 'حوزه', status: 'PENDING_L3' as const },
  { level: 4, label: 'ذی‌حساب', status: 'PENDING_L4' as const },
];

// ==========================================
// ApprovalStepsCell Component
// ==========================================
type ApprovalStepsCellProps = {
  status: TransactionStatus;
  adminLevel: number;
  onApprove: () => void;
  onRejectClick: () => void;
};

function ApprovalStepsCell({ status, adminLevel, onApprove, onRejectClick }: ApprovalStepsCellProps) {
  const currentLevel = STATUS_TO_LEVEL[status] || 1;
  const isRejected = status === 'REJECTED';
  const isApproved = status === 'APPROVED';

  const getStepIcon = (stepLevel: number) => {
    if (isRejected) {
      return <XCircle className="h-5 w-5 text-red-500" />;
    }
    if (isApproved || stepLevel < currentLevel) {
      return <CheckCircle2 className="h-5 w-5 text-green-500" />;
    }
    if (stepLevel === currentLevel) {
      return <Clock className="h-5 w-5 text-amber-500 animate-pulse" />;
    }
    return <Circle className="h-5 w-5 text-gray-300" />;
  };

  // Admin can act if their level matches current approval level
  const canAct = adminLevel === currentLevel && !isRejected && !isApproved;

  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-1">
        {APPROVAL_STEPS.map((step, index) => (
          <React.Fragment key={step.level}>
            <div
              className="flex flex-col items-center"
              title={step.label}
            >
              {getStepIcon(step.level)}
              <span className="text-[9px] text-muted-foreground mt-0.5">{step.label}</span>
            </div>
            {index < APPROVAL_STEPS.length - 1 && (
              <div className={`w-3 h-0.5 ${step.level < currentLevel || isApproved ? 'bg-green-500' : 'bg-gray-200'
                }`} />
            )}
          </React.Fragment>
        ))}
      </div>
      {canAct && (
        <div className="flex gap-1 mr-3 border-r pr-3">
          <Button
            size="sm"
            variant="default"
            className="h-7 px-2 bg-green-600 hover:bg-green-700"
            onClick={(e) => { e.stopPropagation(); onApprove(); }}
          >
            تایید
          </Button>
          <Button
            size="sm"
            variant="destructive"
            className="h-7 px-2"
            onClick={(e) => { e.stopPropagation(); onRejectClick(); }}
          >
            رد
          </Button>
        </div>
      )}
    </div>
  );
}

// ==========================================
// RejectionModal Component
// ==========================================
type RejectionModalProps = {
  isOpen: boolean;
  transactionCode: string;
  onClose: () => void;
  onConfirm: (reason: string) => void;
};

function RejectionModal({ isOpen, transactionCode, onClose, onConfirm }: RejectionModalProps) {
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
            درخواست با کد <span className="font-mono text-primary" dir="ltr">{transactionCode}</span> رد خواهد شد.
            <br />
            لطفاً دلیل رد را وارد کنید تا به کاربر اطلاع داده شود.
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
// Main AdminDashboard Component
// ==========================================
export function AdminDashboard({ user, onLogout, onNavigateToPublic, onNavigateToAccounting }: AdminDashboardProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Rejection modal state
  const [rejectionModalOpen, setRejectionModalOpen] = useState(false);
  const [transactionToReject, setTransactionToReject] = useState<Transaction | null>(null);

  // Get admin level from user
  const adminLevel = user.admin_level || 0;

  // Improved Header Role Display (5-Level Hierarchy)
  const getRoleLabel = () => {
    if (user.role === 'inspector') return 'ناظر / بازرسی';
    if (user.role === 'admin') {
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

  // Load transactions from API - extracted as reusable function
  const loadTransactions = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await fetchAdminTransactions({
        status: statusFilter !== 'all' ? statusFilter : undefined,
        search: searchTerm || undefined,
        page: currentPage
      });

      // Map to component format with defensive checks
      const mapped: Transaction[] = (result.transactions || []).map((t: any) => {
        // Convert old status format to new if needed
        let status: TransactionStatus = t.status || 'PENDING_L1';
        if (status === 'pending' as any) status = 'PENDING_L1';
        if (status === 'approved' as any) status = 'APPROVED';
        if (status === 'rejected' as any) status = 'REJECTED';

        return {
          id: t.id,
          uniqueCode: t.uniqueCode || '---',
          status,
          currentApprovalLevel: t.currentApprovalLevel || STATUS_TO_LEVEL[status] || 1,
          amount: t.amount || 0,
          budgetCode: t.budgetCode || '',
          budgetDescription: t.budgetDescription || '',
          beneficiaryName: t.beneficiaryName || '',
          createdBy: t.createdBy || '',
          createdAt: t.createdAt || '',
          zoneName: t.zoneName || '',
          rejectionReason: t.rejectionReason,
        };
      });
      setTransactions(mapped);
    } catch (err) {
      console.error('Failed to load transactions:', err);
      setError('خطا در بارگیری تراکنش‌ها');
    } finally {
      setLoading(false);
    }
  };

  // Load transactions on mount and when filters change
  useEffect(() => {
    loadTransactions();
  }, [statusFilter, currentPage]);

  const filteredTransactions = transactions.filter(tx => {
    const matchesSearch =
      tx.uniqueCode.includes(searchTerm) ||
      tx.budgetDescription?.includes(searchTerm) ||
      tx.beneficiaryName?.includes(searchTerm) ||
      tx.createdBy?.includes(searchTerm);

    return matchesSearch;
  });

  const totalPages = Math.ceil(filteredTransactions.length / itemsPerPage);
  const paginatedTransactions = filteredTransactions.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  // Handle approve - call API and reload transactions
  const handleApprove = async (txId: number) => {
    try {
      setLoading(true);
      const result = await approveTransaction(txId);
      console.log('Approve result:', result);
      // Reload transactions to get fresh data from server
      await loadTransactions();
      // Close the review panel if open
      setSelectedTransaction(null);
    } catch (err) {
      console.error('Approve failed:', err);
      setError(err instanceof Error ? err.message : 'خطا در تایید تراکنش');
      setLoading(false);
    }
  };

  // Handle reject - open modal
  const handleRejectClick = (tx: Transaction) => {
    setTransactionToReject(tx);
    setRejectionModalOpen(true);
  };

  // Handle reject confirmation - call API and reload transactions
  const handleRejectConfirm = async (reason: string) => {
    if (!transactionToReject) return;

    try {
      setLoading(true);
      const result = await rejectTransaction(transactionToReject.id, reason);
      console.log('Reject result:', result);
      // Reload transactions to get fresh data from server
      await loadTransactions();
      // Close the review panel if open
      setSelectedTransaction(null);
    } catch (err) {
      console.error('Reject failed:', err);
      setError(err instanceof Error ? err.message : 'خطا در رد تراکنش');
      setLoading(false);
    }

    setTransactionToReject(null);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('fa-IR').format(amount);
  };

  // Updated stats for new statuses
  const stats = {
    total: transactions.length,
    pendingSection: transactions.filter(t => t.status === 'PENDING_L1').length,
    pendingOffice: transactions.filter(t => t.status === 'PENDING_L2').length,
    pendingZone: transactions.filter(t => t.status === 'PENDING_L3').length,
    pendingFinance: transactions.filter(t => t.status === 'PENDING_L4').length,
    approved: transactions.filter(t => t.status === 'APPROVED').length,
    rejected: transactions.filter(t => t.status === 'REJECTED').length,
    // Total pending at my level
    myPending: transactions.filter(t => STATUS_TO_LEVEL[t.status] === adminLevel).length,
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
                <h1 className="text-lg">داشبورد مدیریت</h1>
                <p className="text-sm text-muted-foreground">شهرداری اصفهان - معاونت مالی</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="text-left">
                <p className="text-sm font-medium">{user.fullName}</p>
                <div className="flex items-center gap-1 justify-end">
                  <Badge variant="outline" className="text-[10px] h-5 px-1 bg-primary/5 border-primary/20">
                    {getRoleLabel()}
                  </Badge>
                </div>
              </div>
              {onNavigateToAccounting && (
                <Button variant="outline" size="sm" onClick={onNavigateToAccounting}>
                  📊 صندوق حسابداری
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

      <main className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          {/* Stats Cards - Updated for approval workflow */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <Card className="p-4">
              <p className="text-sm text-muted-foreground">کل تراکنش‌ها</p>
              <p className="text-3xl mt-2">{stats.total}</p>
            </Card>
            <Card className="p-4 bg-amber-50 border-amber-200">
              <p className="text-sm text-amber-800">در انتظار من</p>
              <p className="text-3xl mt-2 text-amber-600">{stats.myPending}</p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-muted-foreground">قسمت</p>
              <p className="text-2xl mt-2 text-amber-500">{stats.pendingSection}</p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-muted-foreground">اداره</p>
              <p className="text-2xl mt-2 text-amber-500">{stats.pendingOffice}</p>
            </Card>
            <Card className="p-4 bg-green-50 border-green-200">
              <p className="text-sm text-green-800">تایید شده</p>
              <p className="text-3xl mt-2 text-green-600">{stats.approved}</p>
            </Card>
            <Card className="p-4 bg-red-50 border-red-200">
              <p className="text-sm text-red-800">رد شده</p>
              <p className="text-3xl mt-2 text-red-600">{stats.rejected}</p>
            </Card>
          </div>

          {/* Filters */}
          <Card className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="relative">
                <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="جستجو بر اساس کد، ردیف، ذینفع یا ایجادکننده..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pr-10"
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="فیلتر وضعیت" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">همه وضعیت‌ها</SelectItem>
                  <SelectItem value="PENDING_L1">در انتظار قسمت</SelectItem>
                  <SelectItem value="PENDING_L2">در انتظار اداره</SelectItem>
                  <SelectItem value="PENDING_L3">در انتظار حوزه</SelectItem>
                  <SelectItem value="PENDING_L4">در انتظار ذی‌حساب</SelectItem>
                  <SelectItem value="APPROVED">تایید شده</SelectItem>
                  <SelectItem value="REJECTED">رد شده</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </Card>

          {/* Transactions Table with Progressive Approval */}
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-right">کد یکتا</TableHead>
                  <TableHead className="text-right">مراحل تایید</TableHead>
                  <TableHead className="text-right">مبلغ (ریال)</TableHead>
                  <TableHead className="text-right">ردیف بودجه</TableHead>
                  <TableHead className="text-right">ذینفع</TableHead>
                  <TableHead className="text-right">ایجادکننده</TableHead>
                  <TableHead className="text-right">تاریخ</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8">
                      <div className="flex justify-center">
                        <Loader2 className="h-6 w-6 animate-spin text-primary" />
                      </div>
                    </TableCell>
                  </TableRow>
                ) : paginatedTransactions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                      تراکنشی یافت نشد
                    </TableCell>
                  </TableRow>
                ) : (
                  paginatedTransactions.map(tx => (
                    <TableRow
                      key={tx.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => setSelectedTransaction(tx)}
                    >
                      <TableCell className="font-mono text-sm" dir="ltr">{tx.uniqueCode}</TableCell>
                      <TableCell>
                        <ApprovalStepsCell
                          status={tx.status}
                          adminLevel={adminLevel}
                          onApprove={() => handleApprove(tx.id)}
                          onRejectClick={() => handleRejectClick(tx)}
                        />
                      </TableCell>
                      <TableCell className="font-mono">{formatCurrency(tx.amount)}</TableCell>
                      <TableCell className="font-mono text-sm">{tx.budgetCode}</TableCell>
                      <TableCell className="max-w-[150px] truncate">{tx.beneficiaryName || '-'}</TableCell>
                      <TableCell>{tx.createdBy || '-'}</TableCell>
                      <TableCell className="text-sm">{tx.createdAt?.split(' - ')[0] || '-'}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between p-4 border-t">
                <p className="text-sm text-muted-foreground">
                  صفحه {currentPage} از {totalPages}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    disabled={currentPage === totalPages}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </Card>
        </div>
      </main>

      {/* Side Panel for Review */}
      {selectedTransaction && (
        <TransactionReviewPanel
          transaction={selectedTransaction as any}
          onClose={() => setSelectedTransaction(null)}
          onApprove={(id) => handleApprove(id)}
          onReject={(id, reason) => {
            setTransactions(prev => prev.filter(t => t.id !== id));
          }}
        />
      )}

      {/* Rejection Modal */}
      <RejectionModal
        isOpen={rejectionModalOpen}
        transactionCode={transactionToReject?.uniqueCode || ''}
        onClose={() => {
          setRejectionModalOpen(false);
          setTransactionToReject(null);
        }}
        onConfirm={handleRejectConfirm}
      />
    </div>
  );
}
