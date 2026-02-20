import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import {
  ArrowRight,
  FileText,
  Plus,
  CheckCircle,
  CreditCard,
  Loader2,
  Send,
  AlertTriangle,
  Banknote,
} from 'lucide-react';
import {
  fetchContract,
  fetchStatements,
  createStatement,
  submitStatement,
  approveStatement,
  payStatement,
  transitionContractStatus,
  type ContractResponse,
  type StatementListItem,
  type StatementCreateRequest,
} from '../services/contracts';
import { toast } from 'sonner';
import { formatNumber } from '../lib/utils';

// ============================================================
// Helpers
// ============================================================

const getContractStatusConfig = (status?: string) => {
  switch (status?.toUpperCase()) {
    case 'DRAFT':
      return { label: 'پیش‌نویس', className: 'bg-slate-100 text-slate-700' };
    case 'PENDING_APPROVAL':
      return { label: 'در انتظار تایید', className: 'bg-amber-100 text-amber-700' };
    case 'APPROVED':
      return { label: 'تایید شده', className: 'bg-green-100 text-green-700' };
    case 'IN_PROGRESS':
      return { label: 'در حال اجرا', className: 'bg-blue-100 text-blue-700' };
    case 'REJECTED':
      return { label: 'رد شده', className: 'bg-red-100 text-red-700' };
    case 'COMPLETED':
      return { label: 'تکمیل شده', className: 'bg-emerald-100 text-emerald-700' };
    case 'CLOSED':
      return { label: 'بسته شده', className: 'bg-gray-100 text-gray-600' };
    default:
      return { label: status || 'نامشخص', className: 'bg-slate-100 text-slate-700' };
  }
};

const getStatementStatusConfig = (status?: string) => {
  switch (status?.toUpperCase()) {
    case 'DRAFT':
      return { label: 'پیش‌نویس', className: 'bg-slate-100 text-slate-600', icon: FileText };
    case 'SUBMITTED':
      return { label: 'ارسال شده', className: 'bg-blue-100 text-blue-700', icon: Send };
    case 'APPROVED':
      return { label: 'تایید شده', className: 'bg-amber-100 text-amber-700', icon: CheckCircle };
    case 'PAID':
      return { label: 'پرداخت شده', className: 'bg-green-100 text-green-700', icon: Banknote };
    default:
      return { label: status || '—', className: 'bg-slate-100 text-slate-600', icon: FileText };
  }
};

function getProgressColor(percent: number): string {
  if (percent > 95) return 'bg-red-500';
  if (percent > 80) return 'bg-amber-500';
  return 'bg-emerald-500';
}

function getProgressTrackColor(percent: number): string {
  if (percent > 95) return 'bg-red-100';
  if (percent > 80) return 'bg-amber-100';
  return 'bg-emerald-100';
}


// ============================================================
// Financial Progress Bar Component
// ============================================================

function FinancialProgressBar({
  paid,
  total,
}: {
  paid: number;
  total: number;
}) {
  const percent = total > 0 ? Math.min((paid / total) * 100, 100) : 0;
  const barColor = getProgressColor(percent);
  const trackColor = getProgressTrackColor(percent);

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <CreditCard className="h-5 w-5 text-muted-foreground" />
          <h3 className="font-semibold text-sm">پیشرفت مالی</h3>
        </div>
        <span className="text-sm font-medium text-muted-foreground">
          {percent.toFixed(1)}% تکمیل شده
        </span>
      </div>
      <div className={`relative h-4 w-full overflow-hidden rounded-full ${trackColor}`}>
        <div
          className={`h-full rounded-full transition-all duration-500 ease-out ${barColor}`}
          style={{ width: `${percent}%` }}
        />
      </div>
      <div className="flex items-center justify-between mt-3 text-sm">
        <div>
          <span className="text-muted-foreground">پرداخت شده: </span>
          <span className="font-mono-num font-semibold" dir="ltr">
            {formatNumber(paid)}
          </span>
          <span className="text-muted-foreground"> ریال</span>
        </div>
        <div>
          <span className="text-muted-foreground">مبلغ کل: </span>
          <span className="font-mono-num font-semibold" dir="ltr">
            {formatNumber(total)}
          </span>
          <span className="text-muted-foreground"> ریال</span>
        </div>
      </div>
    </Card>
  );
}


// ============================================================
// Add Statement Dialog
// ============================================================

function AddStatementDialog({
  open,
  onOpenChange,
  contractId,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  contractId: number;
  onCreated: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    description: '',
    gross_amount: '',
    deductions: '0',
    period_start: '',
    period_end: '',
  });

  const resetForm = () => {
    setForm({ description: '', gross_amount: '', deductions: '0', period_start: '', period_end: '' });
  };

  const handleSubmit = async () => {
    const gross = parseInt(form.gross_amount, 10);
    const deductions = parseInt(form.deductions || '0', 10);

    if (!form.description.trim()) {
      toast.error('شرح صورت وضعیت الزامی است');
      return;
    }
    if (isNaN(gross) || gross <= 0) {
      toast.error('مبلغ ناخالص باید عددی مثبت باشد');
      return;
    }
    if (isNaN(deductions) || deductions < 0) {
      toast.error('کسورات نمی‌تواند منفی باشد');
      return;
    }

    const payload: StatementCreateRequest = {
      gross_amount: gross,
      deductions,
      description: form.description.trim(),
    };
    if (form.period_start) payload.period_start = form.period_start;
    if (form.period_end) payload.period_end = form.period_end;

    setLoading(true);
    try {
      await createStatement(contractId, payload);
      toast.success('صورت وضعیت با موفقیت ایجاد شد');
      resetForm();
      onOpenChange(false);
      onCreated();
    } catch (err: any) {
      toast.error(err?.message || 'خطا در ایجاد صورت وضعیت');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) resetForm(); onOpenChange(o); }}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-right">ایجاد صورت وضعیت جدید</DialogTitle>
          <DialogDescription className="text-right">
            اطلاعات صورت وضعیت را وارد کنید. مبلغ خالص به صورت خودکار محاسبه می‌شود.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="stmt-desc">شرح صورت وضعیت *</Label>
            <Textarea
              id="stmt-desc"
              placeholder="مثلاً: صورت وضعیت مرحله اول - آسفالت معابر"
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              rows={2}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="stmt-gross">مبلغ ناخالص (ریال) *</Label>
              <Input
                id="stmt-gross"
                type="number"
                min={1}
                placeholder="0"
                dir="ltr"
                className="font-mono"
                value={form.gross_amount}
                onChange={(e) => setForm((f) => ({ ...f, gross_amount: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="stmt-ded">کسورات (ریال)</Label>
              <Input
                id="stmt-ded"
                type="number"
                min={0}
                placeholder="0"
                dir="ltr"
                className="font-mono"
                value={form.deductions}
                onChange={(e) => setForm((f) => ({ ...f, deductions: e.target.value }))}
              />
            </div>
          </div>
          {form.gross_amount && (
            <Card className="p-3 bg-blue-50/60 border-blue-200">
              <div className="flex items-center justify-between text-sm">
                <span className="text-blue-800">مبلغ خالص (محاسبه شده):</span>
                <span className="font-mono-num font-bold text-blue-900" dir="ltr">
                  {formatNumber(
                    Math.max(0, (parseInt(form.gross_amount, 10) || 0) - (parseInt(form.deductions || '0', 10) || 0))
                  )}{' '}
                  ریال
                </span>
              </div>
            </Card>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="stmt-start">تاریخ شروع دوره</Label>
              <Input
                id="stmt-start"
                type="date"
                dir="ltr"
                value={form.period_start}
                onChange={(e) => setForm((f) => ({ ...f, period_start: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="stmt-end">تاریخ پایان دوره</Label>
              <Input
                id="stmt-end"
                type="date"
                dir="ltr"
                value={form.period_end}
                onChange={(e) => setForm((f) => ({ ...f, period_end: e.target.value }))}
              />
            </div>
          </div>
        </div>
        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={() => { resetForm(); onOpenChange(false); }}>
            انصراف
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading && <Loader2 className="h-4 w-4 animate-spin ml-2" />}
            ایجاد صورت وضعیت
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


// ============================================================
// Confirm Action Dialog (Approve / Pay / Submit)
// ============================================================

function ConfirmActionDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  variant = 'default',
  icon: Icon,
  loading,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel: string;
  variant?: 'default' | 'destructive';
  icon?: React.ElementType;
  loading: boolean;
  onConfirm: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-right flex items-center gap-2">
            {Icon && <Icon className="h-5 w-5" />}
            {title}
          </DialogTitle>
          <DialogDescription className="text-right">{description}</DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            انصراف
          </Button>
          <Button variant={variant} onClick={onConfirm} disabled={loading}>
            {loading && <Loader2 className="h-4 w-4 animate-spin ml-2" />}
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


// ============================================================
// Statements Table Component
// ============================================================

function StatementsSection({
  contractId,
  contractStatus,
  statements,
  loading,
  onRefresh,
}: {
  contractId: number;
  contractStatus: string;
  statements: StatementListItem[];
  loading: boolean;
  onRefresh: () => void;
}) {
  const [addDialogOpen, setAddDialogOpen] = useState(false);

  // Action state
  const [actionDialog, setActionDialog] = useState<{
    type: 'submit' | 'approve' | 'pay';
    statementId: number;
    statementNumber: string;
  } | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const canCreateStatement = ['APPROVED', 'IN_PROGRESS'].includes(
    contractStatus?.toUpperCase() ?? '',
  );

  const handleAction = async () => {
    if (!actionDialog) return;
    setActionLoading(true);
    try {
      if (actionDialog.type === 'submit') {
        await submitStatement(actionDialog.statementId);
        toast.success(`صورت وضعیت ${actionDialog.statementNumber} ارسال شد`);
      } else if (actionDialog.type === 'approve') {
        await approveStatement(actionDialog.statementId);
        toast.success(`صورت وضعیت ${actionDialog.statementNumber} تایید شد`);
      } else if (actionDialog.type === 'pay') {
        await payStatement(actionDialog.statementId);
        toast.success(`پرداخت صورت وضعیت ${actionDialog.statementNumber} انجام شد`);
      }
      setActionDialog(null);
      onRefresh();
    } catch (err: any) {
      toast.error(err?.message || 'خطا در انجام عملیات');
    } finally {
      setActionLoading(false);
    }
  };

  const actionConfigs = {
    submit: {
      title: 'ارسال صورت وضعیت',
      description: 'آیا از ارسال این صورت وضعیت برای بررسی مطمئن هستید؟',
      confirmLabel: 'ارسال',
      variant: 'default' as const,
      icon: Send,
    },
    approve: {
      title: 'تایید صورت وضعیت',
      description: 'با تایید این صورت وضعیت، امکان پرداخت فعال می‌شود. آیا مطمئن هستید؟',
      confirmLabel: 'تایید',
      variant: 'default' as const,
      icon: CheckCircle,
    },
    pay: {
      title: 'پرداخت صورت وضعیت',
      description:
        'با پرداخت، مبلغ از بودجه رزرو شده به هزینه تبدیل می‌شود. این عملیات غیرقابل بازگشت است.',
      confirmLabel: 'تایید پرداخت',
      variant: 'default' as const,
      icon: Banknote,
    },
  };

  return (
    <>
      <Card className="overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-muted-foreground" />
            <h3 className="font-semibold">صورت وضعیت‌ها</h3>
            <Badge variant="secondary" className="text-xs">
              {statements.length}
            </Badge>
          </div>
          {canCreateStatement && (
            <Button size="sm" onClick={() => setAddDialogOpen(true)}>
              <Plus className="h-4 w-4 ml-1" />
              صورت وضعیت جدید
            </Button>
          )}
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-right">شماره</TableHead>
              <TableHead className="text-right">دوره</TableHead>
              <TableHead className="text-right">مبلغ ناخالص</TableHead>
              <TableHead className="text-right">مبلغ خالص</TableHead>
              <TableHead className="text-right">وضعیت</TableHead>
              <TableHead className="text-right">عملیات</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center">
                  <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2 text-muted-foreground" />
                  <span className="text-muted-foreground text-sm">بارگیری...</span>
                </TableCell>
              </TableRow>
            ) : statements.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center">
                  <FileText className="h-8 w-8 mx-auto mb-2 text-muted-foreground/40" />
                  <p className="text-muted-foreground text-sm">
                    هنوز صورت وضعیتی ثبت نشده است
                  </p>
                </TableCell>
              </TableRow>
            ) : (
              statements.map((stmt) => {
                const statusCfg = getStatementStatusConfig(stmt.status);
                const StatusIcon = statusCfg.icon;
                const stmtStatus = stmt.status?.toUpperCase();
                return (
                  <TableRow key={stmt.id}>
                    <TableCell className="font-mono text-sm" dir="ltr">
                      {stmt.statement_number}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {stmt.created_at || '—'}
                    </TableCell>
                    <TableCell className="font-mono text-sm" dir="ltr">
                      {/* We only have net_amount in the list view; show net */}
                      —
                    </TableCell>
                    <TableCell className="font-mono-num text-sm" dir="ltr">
                      {formatNumber(stmt.net_amount)} ریال
                    </TableCell>
                    <TableCell>
                      <Badge className={`${statusCfg.className} gap-1`}>
                        <StatusIcon className="h-3 w-3" />
                        {statusCfg.label}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        {stmtStatus === 'DRAFT' && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs h-7"
                            onClick={() =>
                              setActionDialog({
                                type: 'submit',
                                statementId: stmt.id,
                                statementNumber: stmt.statement_number,
                              })
                            }
                          >
                            <Send className="h-3 w-3 ml-1" />
                            ارسال
                          </Button>
                        )}
                        {stmtStatus === 'SUBMITTED' && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs h-7 border-blue-300 text-blue-700 hover:bg-blue-50"
                            onClick={() =>
                              setActionDialog({
                                type: 'approve',
                                statementId: stmt.id,
                                statementNumber: stmt.statement_number,
                              })
                            }
                          >
                            <CheckCircle className="h-3 w-3 ml-1" />
                            تایید
                          </Button>
                        )}
                        {stmtStatus === 'APPROVED' && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs h-7 border-amber-300 text-amber-700 hover:bg-amber-50"
                            onClick={() =>
                              setActionDialog({
                                type: 'pay',
                                statementId: stmt.id,
                                statementNumber: stmt.statement_number,
                              })
                            }
                          >
                            <Banknote className="h-3 w-3 ml-1" />
                            پرداخت
                          </Button>
                        )}
                        {stmtStatus === 'PAID' && (
                          <span className="text-xs text-green-600 flex items-center gap-1">
                            <CheckCircle className="h-3.5 w-3.5" />
                            تسویه شده
                          </span>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </Card>

      {/* Add Statement Dialog */}
      <AddStatementDialog
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        contractId={contractId}
        onCreated={onRefresh}
      />

      {/* Confirm Action Dialog */}
      {actionDialog && (
        <ConfirmActionDialog
          open={true}
          onOpenChange={(o) => { if (!o) setActionDialog(null); }}
          loading={actionLoading}
          onConfirm={handleAction}
          {...actionConfigs[actionDialog.type]}
        />
      )}
    </>
  );
}


// ============================================================
// Main Page Component
// ============================================================

export function ContractDetails() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [contract, setContract] = useState<ContractResponse | null>(null);
  const [statements, setStatements] = useState<StatementListItem[]>([]);
  const [loadingContract, setLoadingContract] = useState(true);
  const [loadingStatements, setLoadingStatements] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [contractActionDialog, setContractActionDialog] = useState<'approve' | 'reject' | null>(null);
  const [contractActionLoading, setContractActionLoading] = useState(false);

  const contractId = parseInt(id || '0', 10);

  const loadContract = useCallback(async () => {
    if (!contractId) return;
    setLoadingContract(true);
    try {
      const data = await fetchContract(contractId);
      setContract(data);
      setError(null);
    } catch (err: any) {
      setError(err?.message || 'خطا در بارگیری اطلاعات قرارداد');
    } finally {
      setLoadingContract(false);
    }
  }, [contractId]);

  const loadStatements = useCallback(async () => {
    if (!contractId) return;
    setLoadingStatements(true);
    try {
      const data = await fetchStatements(contractId);
      setStatements(data.items ?? []);
    } catch {
      // Statements may not exist yet - not a critical error
      setStatements([]);
    } finally {
      setLoadingStatements(false);
    }
  }, [contractId]);

  const refreshAll = useCallback(() => {
    loadContract();
    loadStatements();
  }, [loadContract, loadStatements]);

  const handleContractTransition = useCallback(async () => {
    if (!contractActionDialog || !contractId) return;
    setContractActionLoading(true);
    try {
      const updatedContract = await transitionContractStatus(contractId, contractActionDialog);
      setContract(updatedContract);
      toast.success(
        contractActionDialog === 'approve'
          ? 'Contract approved successfully'
          : 'Contract rejected successfully',
      );
      setContractActionDialog(null);
      await Promise.all([loadContract(), loadStatements()]);
    } catch (err: any) {
      toast.error(err?.message || 'Failed to update contract status');
    } finally {
      setContractActionLoading(false);
    }
  }, [contractActionDialog, contractId, loadContract, loadStatements]);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  // Loading state
  if (loadingContract) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3 text-primary" />
          <p className="text-muted-foreground">بارگیری اطلاعات قرارداد...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !contract) {
    return (
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 max-w-5xl">
        <Card className="p-8 text-center">
          <AlertTriangle className="h-10 w-10 mx-auto mb-3 text-amber-500" />
          <h2 className="text-lg font-semibold mb-2">خطا</h2>
          <p className="text-muted-foreground mb-4">{error || 'قرارداد یافت نشد'}</p>
          <Button variant="outline" onClick={() => navigate('/contracts')}>
            <ArrowRight className="h-4 w-4 ml-2" />
            بازگشت به فهرست قراردادها
          </Button>
        </Card>
      </div>
    );
  }

  const statusCfg = getContractStatusConfig(contract.status);
  const paidAmount = contract.paid_amount ?? 0;
  const totalAmount = contract.total_amount ?? 0;
  const isPendingApproval = contract.status?.toUpperCase() === 'PENDING_APPROVAL';
  const contractActionConfigs = {
    approve: {
      title: 'Approve Contract',
      description:
        'Are you sure you want to approve this contract? Funds are already blocked.',
      confirmLabel: 'Approve Contract',
      variant: 'default' as const,
      icon: CheckCircle,
    },
    reject: {
      title: 'Reject Contract',
      description:
        'Are you sure you want to reject this contract? The reserved funds will be released.',
      confirmLabel: 'Reject Contract',
      variant: 'destructive' as const,
      icon: AlertTriangle,
    },
  };

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6 max-w-5xl">
      {/* Back Button */}
      <Button
        variant="ghost"
        size="sm"
        className="text-muted-foreground -mr-2"
        onClick={() => navigate('/contracts')}
      >
        <ArrowRight className="h-4 w-4 ml-1" />
        بازگشت به فهرست
      </Button>

      {/* Header Card */}
      <Card className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1 min-w-0 flex-1">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-xl font-bold tracking-tight">{contract.title}</h1>
              <Badge className={statusCfg.className}>{statusCfg.label}</Badge>
            </div>
            <div className="flex items-center gap-4 text-sm text-muted-foreground flex-wrap mt-2">
              <span className="font-mono" dir="ltr">
                {contract.contract_number}
              </span>
              {contract.contractor_name && (
                <>
                  <span className="text-muted-foreground/40">|</span>
                  <span>پیمانکار: {contract.contractor_name}</span>
                </>
              )}
              {contract.created_at && (
                <>
                  <span className="text-muted-foreground/40">|</span>
                  <span>تاریخ: {contract.created_at}</span>
                </>
              )}
            </div>
          </div>
          <div className="text-left shrink-0">
            <p className="text-xs text-muted-foreground mb-1">مبلغ کل قرارداد</p>
            <p className="text-lg font-bold font-mono-num" dir="ltr">
              {formatNumber(totalAmount)} <span className="text-sm font-normal">ریال</span>
            </p>
          </div>
        </div>
      </Card>

      {/* Manager Actions */}
      {isPendingApproval && (
        <Card className="p-5 border-amber-200 bg-amber-50/40">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-1">
              <h2 className="text-sm font-semibold">Manager Actions</h2>
              <p className="text-sm text-muted-foreground">
                This contract is waiting for manager approval.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                className="bg-emerald-600 text-white hover:bg-emerald-700"
                onClick={() => setContractActionDialog('approve')}
                disabled={contractActionLoading}
              >
                <CheckCircle className="h-4 w-4" />
                Approve
              </Button>
              <Button
                variant="destructive"
                onClick={() => setContractActionDialog('reject')}
                disabled={contractActionLoading}
              >
                <AlertTriangle className="h-4 w-4" />
                Reject
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Financial Progress Bar */}
      <FinancialProgressBar paid={paidAmount} total={totalAmount} />

      {/* Contract Info Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="p-3 text-center">
          <p className="text-xs text-muted-foreground mb-1">مبلغ پرداختی</p>
          <p className="font-mono-num font-bold text-sm" dir="ltr">
            {formatNumber(paidAmount)}
          </p>
        </Card>
        <Card className="p-3 text-center">
          <p className="text-xs text-muted-foreground mb-1">مانده قرارداد</p>
          <p className="font-mono-num font-bold text-sm" dir="ltr">
            {formatNumber(totalAmount - paidAmount)}
          </p>
        </Card>
        <Card className="p-3 text-center">
          <p className="text-xs text-muted-foreground mb-1">تعداد صورت وضعیت</p>
          <p className="font-bold text-sm">{statements.length}</p>
        </Card>
        <Card className="p-3 text-center">
          <p className="text-xs text-muted-foreground mb-1">وضعیت</p>
          <Badge className={`${statusCfg.className} text-xs`}>{statusCfg.label}</Badge>
        </Card>
      </div>

      {/* Statements Section */}
      <StatementsSection
        contractId={contractId}
        contractStatus={contract.status}
        statements={statements}
        loading={loadingStatements}
        onRefresh={refreshAll}
      />

      {contractActionDialog && (
        <ConfirmActionDialog
          open={true}
          onOpenChange={(o) => { if (!o) setContractActionDialog(null); }}
          loading={contractActionLoading}
          onConfirm={handleContractTransition}
          {...contractActionConfigs[contractActionDialog]}
        />
      )}
    </div>
  );
}

export default ContractDetails;
