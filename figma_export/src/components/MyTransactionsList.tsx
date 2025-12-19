import React, { useState, useEffect, useMemo } from 'react';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Search, FileText, Calendar, DollarSign, Loader2, ChevronDown, ChevronUp, ArrowUpDown, ArrowUp, ArrowDown, Folder } from 'lucide-react';
import { fetchMyTransactions, FigmaTransaction } from '../services/adapters';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible';

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

type SortField = 'date' | 'amount' | 'status';
type SortDirection = 'asc' | 'desc';

type GroupedTransactions = {
  budgetCode: string;
  budgetDescription: string;
  transactions: Transaction[];
  totalAmount: number;
};

const STATUS_CONFIG = {
  draft: { label: 'پیش‌نویس', color: 'bg-gray-500', order: 0 },
  pending: { label: 'در انتظار تایید', color: 'bg-amber-500', order: 1 },
  approved: { label: 'تایید شده', color: 'bg-green-600', order: 2 },
  rejected: { label: 'رد شده', color: 'bg-red-600', order: 3 },
  paid: { label: 'پرداخت شده', color: 'bg-blue-600', order: 4 },
};

export function MyTransactionsList({ userId }: MyTransactionsListProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Date filter state
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Sorting state
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  // Grouping state
  const [groupByBudget, setGroupByBudget] = useState(true);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

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

  // Filter transactions
  const filteredTransactions = useMemo(() => {
    return transactions.filter(tx => {
      // Search filter
      const matchesSearch =
        tx.uniqueCode.toLowerCase().includes(searchTerm.toLowerCase()) ||
        tx.budgetDescription?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        tx.beneficiaryName?.toLowerCase().includes(searchTerm.toLowerCase());

      // Status filter
      const matchesStatus = statusFilter === 'all' || tx.status === statusFilter;

      // Date filter (simple string comparison for Persian dates)
      let matchesDateFrom = true;
      let matchesDateTo = true;
      if (dateFrom && tx.createdAt) {
        matchesDateFrom = tx.createdAt >= dateFrom;
      }
      if (dateTo && tx.createdAt) {
        matchesDateTo = tx.createdAt <= dateTo;
      }

      return matchesSearch && matchesStatus && matchesDateFrom && matchesDateTo;
    });
  }, [transactions, searchTerm, statusFilter, dateFrom, dateTo]);

  // Sort transactions
  const sortedTransactions = useMemo(() => {
    const sorted = [...filteredTransactions].sort((a, b) => {
      let comparison = 0;

      switch (sortField) {
        case 'date':
          comparison = (a.createdAt || '').localeCompare(b.createdAt || '');
          break;
        case 'amount':
          comparison = a.amount - b.amount;
          break;
        case 'status':
          comparison = STATUS_CONFIG[a.status].order - STATUS_CONFIG[b.status].order;
          break;
      }

      return sortDirection === 'desc' ? -comparison : comparison;
    });

    return sorted;
  }, [filteredTransactions, sortField, sortDirection]);

  // Group transactions by budget code
  const groupedTransactions = useMemo(() => {
    if (!groupByBudget) {
      return null;
    }

    const groups = new Map<string, GroupedTransactions>();

    for (const tx of sortedTransactions) {
      const key = tx.budgetCode || 'بدون کد بودجه';

      if (!groups.has(key)) {
        groups.set(key, {
          budgetCode: key,
          budgetDescription: tx.budgetDescription || 'بدون شرح',
          transactions: [],
          totalAmount: 0,
        });
      }

      const group = groups.get(key)!;
      group.transactions.push(tx);
      group.totalAmount += tx.amount;
    }

    return Array.from(groups.values());
  }, [sortedTransactions, groupByBudget]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('fa-IR').format(amount) + ' ریال';
  };

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const toggleGroupCollapse = (budgetCode: string) => {
    setCollapsedGroups(prev => {
      const next = new Set(prev);
      if (next.has(budgetCode)) {
        next.delete(budgetCode);
      } else {
        next.add(budgetCode);
      }
      return next;
    });
  };

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) return <ArrowUpDown className="h-3 w-3" />;
    return sortDirection === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />;
  };

  const renderTransactionCard = (tx: Transaction) => (
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
            {tx.beneficiaryName && (
              <p className="text-sm text-muted-foreground">
                {tx.beneficiaryName}
              </p>
            )}
          </div>
          <div className="text-left">
            <p className="font-mono">{formatCurrency(tx.amount)}</p>
            <p className="text-xs text-muted-foreground mt-1">{tx.createdAt || '-'}</p>
          </div>
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
  );

  return (
    <div className="space-y-6">
      <style>{`
        .custom-scroll-container::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scroll-container::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scroll-container::-webkit-scrollbar-thumb {
          background-color: transparent;
          border-radius: 20px;
        }
        .custom-scroll-container:hover::-webkit-scrollbar-thumb {
          background-color: #94a3b8;
        }
      `}</style>
      <div>
        <h2>تراکنش‌های من</h2>
        <p className="text-sm text-muted-foreground mt-1">
          مشاهده و پیگیری تراکنش‌های ثبت شده
        </p>
      </div>

      {/* Filters */}
      <Card className="p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="جستجو..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pr-10"
            />
          </div>

          {/* Status Filter */}
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger>
              <SelectValue placeholder="وضعیت" />
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

          {/* Date From */}
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">از تاریخ</Label>
            <Input
              type="text"
              placeholder="۱۴۰۳/۰۱/۰۱"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </div>

          {/* Date To */}
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">تا تاریخ</Label>
            <Input
              type="text"
              placeholder="۱۴۰۳/۱۲/۲۹"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </div>
        </div>

        {/* Sorting and Grouping Controls */}
        <div className="flex flex-wrap items-center gap-3 pt-3 border-t">
          <span className="text-sm text-muted-foreground">مرتب‌سازی:</span>

          <Button
            variant={sortField === 'date' ? 'default' : 'outline'}
            size="sm"
            onClick={() => toggleSort('date')}
          >
            تاریخ {sortField === 'date' && getSortIcon('date')}
          </Button>

          <Button
            variant={sortField === 'amount' ? 'default' : 'outline'}
            size="sm"
            onClick={() => toggleSort('amount')}
          >
            مبلغ {sortField === 'amount' && getSortIcon('amount')}
          </Button>

          <Button
            variant={sortField === 'status' ? 'default' : 'outline'}
            size="sm"
            onClick={() => toggleSort('status')}
          >
            وضعیت {sortField === 'status' && getSortIcon('status')}
          </Button>

          <div className="h-6 w-px bg-border mx-2" />

          <Button
            variant={groupByBudget ? 'default' : 'outline'}
            size="sm"
            onClick={() => setGroupByBudget(!groupByBudget)}
          >
            <Folder className="h-4 w-4 ml-1" />
            گروه‌بندی بر اساس بودجه
          </Button>
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
        ) : sortedTransactions.length === 0 ? (
          <Card className="p-8 text-center text-muted-foreground">
            <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>تراکنشی یافت نشد</p>
          </Card>
        ) : groupByBudget && groupedTransactions ? (
          // Grouped View
          groupedTransactions.map(group => (
            <Collapsible
              key={group.budgetCode}
              open={!collapsedGroups.has(group.budgetCode)}
              onOpenChange={() => toggleGroupCollapse(group.budgetCode)}
            >
              <Card className="overflow-hidden">
                <CollapsibleTrigger asChild>
                  <div className="p-4 bg-accent/50 cursor-pointer hover:bg-accent transition-colors flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Folder className="h-5 w-5 text-primary" />
                      <div>
                        <p className="font-mono text-sm">{group.budgetCode}</p>
                        <p className="text-sm text-muted-foreground">{group.budgetDescription}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-left">
                        <p className="text-xs text-muted-foreground">{group.transactions.length} تراکنش</p>
                        <p className="font-mono text-sm">{formatCurrency(group.totalAmount)}</p>
                      </div>
                      {collapsedGroups.has(group.budgetCode) ? (
                        <ChevronDown className="h-5 w-5 text-muted-foreground" />
                      ) : (
                        <ChevronUp className="h-5 w-5 text-muted-foreground" />
                      )}
                    </div>
                  </div>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div
                    className="p-4 space-y-3 border-t overflow-y-auto custom-scroll-container"
                    style={{
                      maxHeight: '320px',
                      scrollbarWidth: 'thin',
                      scrollbarColor: '#94a3b8 transparent'
                    }}
                  >
                    <div className="space-y-3">
                      {group.transactions.map(tx => renderTransactionCard(tx))}
                    </div>
                  </div>
                </CollapsibleContent>
              </Card>
            </Collapsible>
          ))
        ) : (
          // Flat View
          <div
            className="rounded-lg overflow-y-auto custom-scroll-container"
            style={{
              maxHeight: '320px',
              scrollbarWidth: 'thin',
              scrollbarColor: '#94a3b8 transparent'
            }}
          >
            <div className="space-y-3 p-1">
              {sortedTransactions.map(tx => renderTransactionCard(tx))}
            </div>
          </div>
        )}
      </div>

      {/* Summary */}
      <Card className="p-4 bg-muted/30">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center text-sm">
          <div>
            <p className="text-muted-foreground">نمایش شده</p>
            <p className="text-xl mt-1">{sortedTransactions.length} از {transactions.length}</p>
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

export default MyTransactionsList;
