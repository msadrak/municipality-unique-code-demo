/**
 * CreditRequestGateSelector — used inside the TransactionWizard.
 *
 * Shows a list of available (APPROVED + unused) credit requests for the
 * current user's org context. The user must select one before proceeding.
 *
 * If none available, shows a prompt to create one first.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Loader2, AlertCircle, CheckCircle2, Plus, ShieldCheck, RefreshCw } from 'lucide-react';
import { listCreditRequests } from '../services/creditRequestService';
import type { CreditRequestListItem } from '../types/creditRequest';
import { formatRial } from '../lib/utils';

interface CreditRequestGateSelectorProps {
  zoneId?: number;
  departmentId?: number;
  sectionId?: number;
  budgetCode?: string;
  onSelect: (cr: CreditRequestListItem) => void;
  onCreateNew: () => void;
  selectedCRId?: number;
}

export function CreditRequestGateSelector({
  zoneId,
  departmentId,
  sectionId,
  budgetCode,
  onSelect,
  onCreateNew,
  selectedCRId,
}: CreditRequestGateSelectorProps) {
  const [items, setItems] = useState<CreditRequestListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAvailable = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listCreditRequests({
        available_only: true,
        mine_only: true,
        zone_id: zoneId,
        budget_code: budgetCode,
        limit: 50,
      });
      setItems(data.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'خطا در بارگذاری');
    } finally {
      setLoading(false);
    }
  }, [zoneId, budgetCode]);

  useEffect(() => {
    fetchAvailable();
  }, [fetchAvailable]);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <ShieldCheck className="h-5 w-5 text-primary" />
        <h3 className="text-lg font-semibold">انتخاب درخواست تامین اعتبار</h3>
      </div>
      <p className="text-sm text-muted-foreground">
        برای ایجاد تراکنش، ابتدا باید یک درخواست تامین اعتبار تایید شده انتخاب کنید.
      </p>

      {error && (
        <div className="bg-red-50 border border-red-200 p-3 rounded text-sm text-red-700 flex items-center gap-2">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : items.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center py-8">
            <AlertCircle className="h-10 w-10 text-amber-500 mb-3" />
            <p className="font-medium mb-1">درخواست تامین اعتبار تایید شده‌ای یافت نشد</p>
            <p className="text-sm text-muted-foreground mb-4">
              {budgetCode
                ? `برای کد بودجه ${budgetCode} درخواست تایید شده‌ای وجود ندارد.`
                : 'ابتدا یک درخواست تامین اعتبار ایجاد و تایید بگیرید.'}
            </p>
            <div className="flex gap-2">
              <Button size="sm" onClick={onCreateNew}>
                <Plus className="h-4 w-4 ml-1" />
                ایجاد درخواست جدید
              </Button>
              <Button size="sm" variant="outline" onClick={fetchAvailable}>
                <RefreshCw className="h-4 w-4 ml-1" />
                بروزرسانی
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {items.map((item) => {
            const isSelected = selectedCRId === item.id;
            return (
              <Card
                key={item.id}
                className={`cursor-pointer transition-colors ${
                  isSelected
                    ? 'border-primary ring-2 ring-primary/20'
                    : 'hover:border-primary/30'
                }`}
                onClick={() => onSelect(item)}
              >
                <CardContent className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-3">
                    {isSelected ? (
                      <CheckCircle2 className="h-5 w-5 text-primary" />
                    ) : (
                      <div className="h-5 w-5 rounded-full border-2 border-muted-foreground/30" />
                    )}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-medium">
                          {item.credit_request_code}
                        </span>
                        <Badge className="bg-green-100 text-green-700 text-xs">تایید شده</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground truncate max-w-sm">
                        {item.description}
                      </p>
                    </div>
                  </div>
                  <div className="text-left">
                    <p className="text-sm font-medium">{formatRial(item.amount_approved)}</p>
                    <p className="text-xs text-muted-foreground">
                      کد بودجه: {item.budget_code}
                    </p>
                  </div>
                </CardContent>
              </Card>
            );
          })}

          <div className="pt-2 flex justify-center">
            <Button variant="outline" size="sm" onClick={onCreateNew}>
              <Plus className="h-4 w-4 ml-1" />
              ایجاد درخواست جدید
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
