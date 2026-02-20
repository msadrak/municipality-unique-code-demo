/**
 * CreditRequestManager - Full CRUD + lifecycle UI for Stage 1 Gateway
 *
 * Views:
 *   - list: shows user's credit requests with status badges
 *   - create: form to create a new DRAFT CR
 *   - detail: full detail of a CR with action buttons (submit/cancel)
 *
 * Admin actions (approve/reject) are in CreditRequestAdminPanel.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { Label } from './ui/label';
import {
  Plus, ArrowRight, Send, XCircle, Loader2, AlertCircle,
  CheckCircle2, Clock, FileText, RefreshCw,
} from 'lucide-react';
import {
  createCreditRequest,
  listCreditRequests,
  getCreditRequest,
  submitCreditRequest,
  cancelCreditRequest,
  getCreditRequestLogs,
} from '../services/creditRequestService';
import type {
  CreditRequest,
  CreditRequestListItem,
  CreditRequestCreateData,
  CreditRequestLogEntry,
  CreditRequestStatus,
} from '../types/creditRequest';
import { CR_STATUS_CONFIG } from '../types/creditRequest';
import { formatRial } from '../lib/utils';

// ============================================================
// Props
// ============================================================

type CRView = 'list' | 'create' | 'detail';

interface CreditRequestManagerProps {
  userId: number;
  userZoneId?: number;
  userDeptId?: number;
  userSectionId?: number;
  userZoneCode?: string;
}

// ============================================================
// Status Badge component
// ============================================================

function CRStatusBadge({ status }: { status: CreditRequestStatus }) {
  const config = CR_STATUS_CONFIG[status] || CR_STATUS_CONFIG.DRAFT;
  return <Badge className={config.bgClass}>{config.label}</Badge>;
}

// ============================================================
// Main Component
// ============================================================

export function CreditRequestManager({
  userId,
  userZoneId,
  userDeptId,
  userSectionId,
}: CreditRequestManagerProps) {
  const [view, setView] = useState<CRView>('list');
  const [items, setItems] = useState<CreditRequestListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCR, setSelectedCR] = useState<CreditRequest | null>(null);
  const [logs, setLogs] = useState<CreditRequestLogEntry[]>([]);
  const [actionLoading, setActionLoading] = useState(false);

  // Create form state
  const [formBudgetCode, setFormBudgetCode] = useState('');
  const [formAmount, setFormAmount] = useState('');
  const [formDescription, setFormDescription] = useState('');

  // ============================================================
  // Data fetching
  // ============================================================

  const fetchList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listCreditRequests({ mine_only: true, limit: 50 });
      setItems(data.items);
      setTotal(data.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'خطا در بارگذاری');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchDetail = useCallback(async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const [cr, logData] = await Promise.all([
        getCreditRequest(id),
        getCreditRequestLogs(id),
      ]);
      setSelectedCR(cr);
      setLogs(logData);
      setView('detail');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'خطا در بارگذاری');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  // ============================================================
  // Actions
  // ============================================================

  const handleCreate = async () => {
    if (!formBudgetCode || !formAmount || !formDescription) {
      setError('لطفاً تمام فیلدهای الزامی را پر کنید');
      return;
    }
    setActionLoading(true);
    setError(null);
    try {
      const data: CreditRequestCreateData = {
        zone_id: userZoneId!,
        department_id: userDeptId,
        section_id: userSectionId,
        budget_code: formBudgetCode,
        amount_requested: parseFloat(formAmount),
        description: formDescription,
      };
      const cr = await createCreditRequest(data);
      // Reset form and go to detail
      setFormBudgetCode('');
      setFormAmount('');
      setFormDescription('');
      await fetchDetail(cr.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'خطا در ایجاد');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!selectedCR) return;
    setActionLoading(true);
    setError(null);
    try {
      await submitCreditRequest(selectedCR.id);
      await fetchDetail(selectedCR.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'خطا در ارسال');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!selectedCR) return;
    setActionLoading(true);
    setError(null);
    try {
      await cancelCreditRequest(selectedCR.id);
      await fetchDetail(selectedCR.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'خطا در لغو');
    } finally {
      setActionLoading(false);
    }
  };

  // ============================================================
  // Render: List view
  // ============================================================

  if (view === 'list') {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">درخواست‌های تامین اعتبار</h2>
            <p className="text-sm text-muted-foreground">
              {total} درخواست ثبت شده
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={fetchList} disabled={loading}>
              <RefreshCw className={`h-4 w-4 ml-1 ${loading ? 'animate-spin' : ''}`} />
              بروزرسانی
            </Button>
            <Button size="sm" onClick={() => setView('create')}>
              <Plus className="h-4 w-4 ml-1" />
              درخواست جدید
            </Button>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 p-3 rounded text-sm text-red-700 flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}

        {loading && items.length === 0 ? (
          <Card>
            <CardContent className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </CardContent>
          </Card>
        ) : items.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center py-12">
              <FileText className="h-12 w-12 text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground mb-2">هنوز درخواست تامین اعتباری ثبت نشده</p>
              <Button size="sm" onClick={() => setView('create')}>
                <Plus className="h-4 w-4 ml-1" />
                ایجاد اولین درخواست
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {items.map((item) => (
              <Card
                key={item.id}
                className="cursor-pointer hover:border-primary/30 transition-colors"
                onClick={() => fetchDetail(item.id)}
              >
                <CardContent className="flex items-center justify-between py-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-sm font-medium">
                        {item.credit_request_code}
                      </span>
                      <CRStatusBadge status={item.status} />
                      {item.used_transaction_id && (
                        <Badge variant="outline" className="text-xs">مصرف شده</Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground truncate max-w-md">
                      {item.description}
                    </p>
                  </div>
                  <div className="text-left">
                    <p className="text-sm font-medium">{formatRial(item.amount_approved || item.amount_requested)}</p>
                    <p className="text-xs text-muted-foreground">
                      کد بودجه: {item.budget_code}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ============================================================
  // Render: Create view
  // ============================================================

  if (view === 'create') {
    return (
      <div className="space-y-4 max-w-xl mx-auto">
        <div className="flex items-center gap-3 mb-4">
          <Button variant="ghost" size="sm" onClick={() => { setView('list'); setError(null); }}>
            <ArrowRight className="h-4 w-4 ml-1" />
            بازگشت
          </Button>
          <h2 className="text-xl font-semibold">ایجاد درخواست تامین اعتبار</h2>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 p-3 rounded text-sm text-red-700 flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}

        <Card>
          <CardContent className="space-y-4 pt-6">
            <div>
              <Label>کد بودجه *</Label>
              <Input
                value={formBudgetCode}
                onChange={(e) => setFormBudgetCode(e.target.value)}
                placeholder="مثلاً 11020401"
                dir="ltr"
              />
            </div>
            <div>
              <Label>مبلغ درخواستی (ریال) *</Label>
              <Input
                type="number"
                value={formAmount}
                onChange={(e) => setFormAmount(e.target.value)}
                placeholder="مثلاً 250000000"
                dir="ltr"
                min="1"
              />
            </div>
            <div>
              <Label>شرح درخواست *</Label>
              <Input
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                placeholder="توضیح مختصر درباره هدف تامین اعتبار"
              />
            </div>
            <div className="bg-muted/50 p-3 rounded text-sm text-muted-foreground">
              منطقه و قسمت به صورت خودکار از پروفایل شما تنظیم می‌شود.
            </div>
            <Button
              className="w-full"
              onClick={handleCreate}
              disabled={actionLoading || !formBudgetCode || !formAmount || !formDescription}
            >
              {actionLoading ? (
                <Loader2 className="h-4 w-4 animate-spin ml-1" />
              ) : (
                <Plus className="h-4 w-4 ml-1" />
              )}
              ایجاد پیش‌نویس
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ============================================================
  // Render: Detail view
  // ============================================================

  if (view === 'detail' && selectedCR) {
    const st = selectedCR.status;
    const canSubmit = st === 'DRAFT';
    const canCancel = st === 'DRAFT' || st === 'SUBMITTED';
    const isTerminal = st === 'APPROVED' || st === 'REJECTED' || st === 'CANCELLED';

    return (
      <div className="space-y-4 max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-4">
          <Button variant="ghost" size="sm" onClick={() => { setView('list'); setError(null); fetchList(); }}>
            <ArrowRight className="h-4 w-4 ml-1" />
            بازگشت به لیست
          </Button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 p-3 rounded text-sm text-red-700 flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}

        {/* Header */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-mono font-semibold">{selectedCR.credit_request_code}</h2>
                <p className="text-sm text-muted-foreground">{selectedCR.description}</p>
              </div>
              <CRStatusBadge status={selectedCR.status} />
            </div>

            {/* Info Grid */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">منطقه:</span>{' '}
                {selectedCR.zone_title || '-'}
              </div>
              <div>
                <span className="text-muted-foreground">کد بودجه:</span>{' '}
                <span dir="ltr">{selectedCR.budget_code}</span>
              </div>
              <div>
                <span className="text-muted-foreground">مبلغ درخواستی:</span>{' '}
                {formatRial(selectedCR.amount_requested)}
              </div>
              <div>
                <span className="text-muted-foreground">مبلغ تایید شده:</span>{' '}
                {selectedCR.amount_approved ? formatRial(selectedCR.amount_approved) : '-'}
              </div>
              <div>
                <span className="text-muted-foreground">سال مالی:</span>{' '}
                {selectedCR.fiscal_year}
              </div>
              <div>
                <span className="text-muted-foreground">ایجادکننده:</span>{' '}
                {selectedCR.created_by_name || '-'}
              </div>
              {selectedCR.reviewed_by_name && (
                <div>
                  <span className="text-muted-foreground">بررسی‌کننده:</span>{' '}
                  {selectedCR.reviewed_by_name}
                </div>
              )}
              {selectedCR.rejection_reason && (
                <div className="col-span-2 bg-red-50 border border-red-200 p-2 rounded text-red-700">
                  <span className="font-medium">دلیل رد:</span> {selectedCR.rejection_reason}
                </div>
              )}
              {selectedCR.used_transaction_id && (
                <div className="col-span-2 bg-blue-50 border border-blue-200 p-2 rounded text-blue-700">
                  این درخواست توسط تراکنش شماره {selectedCR.used_transaction_id} مصرف شده است.
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Action buttons */}
        {!isTerminal && (
          <div className="flex gap-2">
            {canSubmit && (
              <Button onClick={handleSubmit} disabled={actionLoading} className="flex-1">
                {actionLoading ? <Loader2 className="h-4 w-4 animate-spin ml-1" /> : <Send className="h-4 w-4 ml-1" />}
                ارسال برای تایید
              </Button>
            )}
            {canCancel && (
              <Button variant="outline" onClick={handleCancel} disabled={actionLoading} className="flex-1">
                {actionLoading ? <Loader2 className="h-4 w-4 animate-spin ml-1" /> : <XCircle className="h-4 w-4 ml-1" />}
                لغو درخواست
              </Button>
            )}
          </div>
        )}

        {/* Audit log */}
        {logs.length > 0 && (
          <Card>
            <CardContent className="pt-6">
              <h3 className="text-sm font-semibold mb-3">تاریخچه</h3>
              <div className="space-y-2">
                {logs.map((log) => (
                  <div key={log.id} className="flex items-start gap-2 text-sm border-b pb-2 last:border-b-0">
                    <div className="mt-0.5">
                      {log.action === 'APPROVE' && <CheckCircle2 className="h-4 w-4 text-green-600" />}
                      {log.action === 'REJECT' && <XCircle className="h-4 w-4 text-red-600" />}
                      {log.action === 'SUBMIT' && <Send className="h-4 w-4 text-amber-600" />}
                      {log.action === 'CANCEL' && <XCircle className="h-4 w-4 text-gray-500" />}
                      {log.action === 'CREATE' && <Plus className="h-4 w-4 text-blue-600" />}
                    </div>
                    <div className="flex-1">
                      <span className="font-medium">{log.actor_name || 'سیستم'}</span>
                      {' — '}
                      <span>{log.new_status}</span>
                      {log.comment && (
                        <p className="text-muted-foreground text-xs mt-1">{log.comment}</p>
                      )}
                    </div>
                    <span className="text-xs text-muted-foreground whitespace-nowrap">{log.created_at}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    );
  }

  return null;
}
