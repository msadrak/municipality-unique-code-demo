import React, { useState, useEffect } from 'react';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Search, FileText, Calendar, DollarSign, Loader2 } from 'lucide-react';
import { fetchMyTransactions, FigmaTransaction } from '../services/adapters';

type Transaction = {
  id: number;
  uniqueCode: string;
  status: 'draft' | 'pending' | 'approved' | 'rejected' | 'paid';
  amount: number;
  budgetCode?: string;
  budgetDescription?: string;
  beneficiaryName?: string;
  createdAt?: string;
  rejectionReason?: string;
};

type MyTransactionsListProps = {
  userId: number;
};

const STATUS_CONFIG = {
  draft: { label: 'پیش‌نویس', color: 'bg-gray-500' },
  pending: { label: 'در انتظار تایید', color: 'bg-amber-500' },
  approved: { label: 'تایید شده', color: 'bg-green-600' },
  rejected: { label: 'رد شده', color: 'bg-red-600' },
  paid: { label: 'پرداخت شده', color: 'bg-blue-600' },
};

export function MyTransactionsList({ userId }: MyTransactionsListProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load transactions on mount
  useEffect(() => {
    const loadTransactions = async () => {
      setLoading(true);
      setError(null);

      try {
        const data = await fetchMyTransactions();
        // Map API response to component format
        const mapped: Transaction[] = data.map(t => ({
          id: t.id,
          uniqueCode: t.uniqueCode,
          status: t.status,
          amount: t.amount,
          beneficiaryName: t.beneficiaryName,
          createdAt: t.createdAt,
          rejectionReason: t.rejectionReason,
        }));
        setTransactions(mapped);
      } catch (err) {
        console.error('Failed to load transactions:', err);
        setError('خطا در بارگیری تراکنش‌ها');
      } finally {
        setLoading(false);
      }
    };

    loadTransactions();
  }, [userId]);

  const filteredTransactions = transactions.filter(tx => {
    const matchesSearch =
      tx.uniqueCode.includes(searchTerm) ||
      tx.budgetDescription?.includes(searchTerm) ||
      tx.beneficiaryName?.includes(searchTerm);

    const matchesStatus = statusFilter === 'all' || tx.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('fa-IR').format(amount) + ' ریال';
  };

  return (
    <div className="space-y-6">
      <div>
        <h2>تراکنش‌های من</h2>
        <p className="text-sm text-muted-foreground mt-1">
          مشاهده و پیگیری تراکنش‌های ثبت شده
        </p>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="جستجو بر اساس کد، ردیف بودجه یا ذینفع..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pr-10"
            />
          </div>

          {/* Status Filter */}
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger>
              <SelectValue placeholder="فیلتر بر اساس وضعیت" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه وضعیت‌ها</SelectItem>
              <SelectItem value="draft">پیش‌نویس</SelectItem>
              <SelectItem value="pending">در انتظار تایید</SelectItem>
              <SelectItem value="approved">تایید شده</SelectItem>
              <SelectItem value="rejected">رد شده</SelectItem>
              <SelectItem value="paid">پرداخت شده</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>

      {/* Transactions List */}
      <div className="space-y-3">
        {loading ? (
          <Card className="p-8 text-center">
            <Loader2 className="h-12 w-12 mx-auto mb-3 animate-spin text-muted-foreground" />
            <p className="text-muted-foreground">در حال بارگیری تراکنش‌ها...</p>
          </Card>
        ) : error ? (
          <Card className="p-8 text-center text-red-600">
            <p>{error}</p>
          </Card>
        ) : filteredTransactions.length === 0 ? (
          <Card className="p-8 text-center text-muted-foreground">
            <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>تراکنشی یافت نشد</p>
          </Card>
        ) : (
          filteredTransactions.map(tx => (
            <Card key={tx.id} className="p-4 hover:shadow-md transition-shadow">
              <div className="space-y-3">
                {/* Header */}
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-mono text-sm" dir="ltr">{tx.uniqueCode}</p>
                      <Badge className={`${STATUS_CONFIG[tx.status].color} text-white`}>
                        {STATUS_CONFIG[tx.status].label}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {tx.budgetDescription}
                    </p>
                  </div>
                  <div className="text-left">
                    <p className="font-mono">{formatCurrency(tx.amount)}</p>
                    <p className="text-xs text-muted-foreground mt-1">{tx.createdAt || '-'}</p>
                  </div>
                </div>

                {/* Details */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm pt-3 border-t">
                  {tx.budgetCode && (
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <span className="text-muted-foreground">بودجه:</span>
                      <span className="font-mono">{tx.budgetCode}</span>
                    </div>
                  )}
                  {tx.beneficiaryName && (
                    <div className="flex items-center gap-2">
                      <DollarSign className="h-4 w-4 text-muted-foreground" />
                      <span className="text-muted-foreground">ذینفع:</span>
                      <span>{tx.beneficiaryName}</span>
                    </div>
                  )}
                  {tx.createdAt && (
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4 text-muted-foreground" />
                      <span className="text-muted-foreground">تاریخ:</span>
                      <span>{tx.createdAt.split(' - ')[0]}</span>
                    </div>
                  )}
                </div>

                {/* Rejection Reason */}
                {tx.status === 'rejected' && tx.rejectionReason && (
                  <div className="bg-destructive/10 border border-destructive/20 p-3 rounded text-sm">
                    <p className="text-destructive">
                      <span className="font-medium">دلیل رد:</span> {tx.rejectionReason}
                    </p>
                  </div>
                )}
              </div>
            </Card>
          ))
        )}
      </div>

      {/* Summary */}
      <Card className="p-4 bg-muted/30">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center text-sm">
          <div>
            <p className="text-muted-foreground">کل تراکنش‌ها</p>
            <p className="text-xl mt-1">{transactions.length}</p>
          </div>
          <div>
            <p className="text-muted-foreground">در انتظار</p>
            <p className="text-xl mt-1 text-amber-600">
              {transactions.filter(t => t.status === 'pending').length}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground">تایید شده</p>
            <p className="text-xl mt-1 text-green-600">
              {transactions.filter(t => t.status === 'approved').length}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground">رد شده</p>
            <p className="text-xl mt-1 text-red-600">
              {transactions.filter(t => t.status === 'rejected').length}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground">پرداخت شده</p>
            <p className="text-xl mt-1 text-blue-600">
              {transactions.filter(t => t.status === 'paid').length}
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
