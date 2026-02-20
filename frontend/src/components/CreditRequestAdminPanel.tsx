/**
 * CreditRequestAdminPanel — admin view for reviewing and approving/rejecting
 * SUBMITTED credit requests.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import {
  Loader2, AlertCircle, CheckCircle2, XCircle, RefreshCw, ShieldCheck,
} from 'lucide-react';
import {
  listCreditRequests,
  getCreditRequest,
  approveCreditRequest,
  rejectCreditRequest,
  getCreditRequestLogs,
} from '../services/creditRequestService';
import type {
  CreditRequest,
  CreditRequestListItem,
  CreditRequestLogEntry,
} from '../types/creditRequest';
import { CR_STATUS_CONFIG } from '../types/creditRequest';
import { formatRial } from '../lib/utils';

export function CreditRequestAdminPanel() {
  const [items, setItems] = useState<CreditRequestListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCR, setSelectedCR] = useState<CreditRequest | null>(null);
  const [logs, setLogs] = useState<CreditRequestLogEntry[]>([]);
  const [actionLoading, setActionLoading] = useState(false);

  // Reject modal state
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  // Filter: show SUBMITTED by default (pending review)
  const [statusFilter, setStatusFilter] = useState<string>('SUBMITTED');

  const fetchList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listCreditRequests({
        status: statusFilter || undefined,
        limit: 50,
      });
      setItems(data.items);
      setTotal(data.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'خطا');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  const fetchDetail = useCallback(async (id: number) => {
    setLoading(true);
    try {
      const [cr, logData] = await Promise.all([
        getCreditRequest(id),
        getCreditRequestLogs(id),
      ]);
      setSelectedCR(cr);
      setLogs(logData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'خطا');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  const handleApprove = async () => {
    if (!selectedCR) return;
    setActionLoading(true);
    setError(null);
    try {
      await approveCreditRequest(selectedCR.id);
      await fetchDetail(selectedCR.id);
      fetchList();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'خطا');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!selectedCR || !rejectReason) return;
    setActionLoading(true);
    setError(null);
    try {
      await rejectCreditRequest(selectedCR.id, { reason: rejectReason });
      setShowRejectForm(false);
      setRejectReason('');
      await fetchDetail(selectedCR.id);
      fetchList();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'خطا');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-primary" />
          <h2 className="text-xl font-semibold">بررسی درخواست‌های تامین اعتبار</h2>
          <Badge variant="outline">{total}</Badge>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="text-sm border rounded px-2 py-1"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="SUBMITTED">در انتظار بررسی</option>
            <option value="APPROVED">تایید شده</option>
            <option value="REJECTED">رد شده</option>
            <option value="">همه</option>
          </select>
          <Button variant="outline" size="sm" onClick={fetchList} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 p-3 rounded text-sm text-red-700 flex items-center gap-2">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* List */}
        <div className="space-y-2">
          {loading && items.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : items.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                درخواستی با فیلتر انتخابی یافت نشد
              </CardContent>
            </Card>
          ) : (
            items.map((item) => {
              const isActive = selectedCR?.id === item.id;
              const config = CR_STATUS_CONFIG[item.status] || CR_STATUS_CONFIG.DRAFT;
              return (
                <Card
                  key={item.id}
                  className={`cursor-pointer transition-colors ${isActive ? 'border-primary ring-1 ring-primary/20' : 'hover:border-primary/30'}`}
                  onClick={() => fetchDetail(item.id)}
                >
                  <CardContent className="py-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-mono text-sm">{item.credit_request_code}</span>
                          <Badge className={config.bgClass + ' text-xs'}>{config.label}</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground truncate max-w-xs">{item.description}</p>
                        <p className="text-xs text-muted-foreground">
                          {item.created_by_name} • {item.created_at}
                        </p>
                      </div>
                      <p className="text-sm font-medium">{formatRial(item.amount_requested)}</p>
                    </div>
                  </CardContent>
                </Card>
              );
            })
          )}
        </div>

        {/* Detail Panel */}
        <div>
          {selectedCR ? (
            <Card className="sticky top-4">
              <CardContent className="pt-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-mono font-semibold">{selectedCR.credit_request_code}</h3>
                  <Badge className={CR_STATUS_CONFIG[selectedCR.status]?.bgClass}>
                    {CR_STATUS_CONFIG[selectedCR.status]?.label}
                  </Badge>
                </div>

                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div><span className="text-muted-foreground">منطقه:</span> {selectedCR.zone_title}</div>
                  <div><span className="text-muted-foreground">کد بودجه:</span> <span dir="ltr">{selectedCR.budget_code}</span></div>
                  <div><span className="text-muted-foreground">مبلغ:</span> {formatRial(selectedCR.amount_requested)}</div>
                  <div><span className="text-muted-foreground">ایجادکننده:</span> {selectedCR.created_by_name}</div>
                </div>

                <div className="text-sm bg-muted/50 p-3 rounded">
                  <span className="font-medium">شرح: </span>{selectedCR.description}
                </div>

                {/* Actions for SUBMITTED only */}
                {selectedCR.status === 'SUBMITTED' && (
                  <div className="space-y-2 pt-2 border-t">
                    {!showRejectForm ? (
                      <div className="flex gap-2">
                        <Button
                          className="flex-1 bg-green-600 hover:bg-green-700"
                          onClick={handleApprove}
                          disabled={actionLoading}
                        >
                          {actionLoading ? <Loader2 className="h-4 w-4 animate-spin ml-1" /> : <CheckCircle2 className="h-4 w-4 ml-1" />}
                          تایید
                        </Button>
                        <Button
                          variant="destructive"
                          className="flex-1"
                          onClick={() => setShowRejectForm(true)}
                          disabled={actionLoading}
                        >
                          <XCircle className="h-4 w-4 ml-1" />
                          رد
                        </Button>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <Input
                          placeholder="دلیل رد..."
                          value={rejectReason}
                          onChange={(e) => setRejectReason(e.target.value)}
                        />
                        <div className="flex gap-2">
                          <Button
                            variant="destructive"
                            className="flex-1"
                            onClick={handleReject}
                            disabled={actionLoading || !rejectReason}
                          >
                            {actionLoading ? <Loader2 className="h-4 w-4 animate-spin ml-1" /> : null}
                            تایید رد
                          </Button>
                          <Button variant="outline" onClick={() => { setShowRejectForm(false); setRejectReason(''); }}>
                            انصراف
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {selectedCR.rejection_reason && (
                  <div className="bg-red-50 border border-red-200 p-2 rounded text-sm text-red-700">
                    <strong>دلیل رد:</strong> {selectedCR.rejection_reason}
                  </div>
                )}

                {/* Logs */}
                {logs.length > 0 && (
                  <div className="pt-2 border-t">
                    <h4 className="text-xs font-semibold mb-2 text-muted-foreground">تاریخچه</h4>
                    {logs.map((log) => (
                      <div key={log.id} className="text-xs flex items-center gap-2 mb-1">
                        <span className="text-muted-foreground">{log.created_at}</span>
                        <span>{log.actor_name}: {log.action}</span>
                        {log.comment && <span className="text-muted-foreground">({log.comment})</span>}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                یک درخواست را از لیست انتخاب کنید
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
