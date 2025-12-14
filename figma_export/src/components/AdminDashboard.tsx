import React, { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Building2, LogOut, Search, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { TransactionReviewPanel } from './TransactionReviewPanel';
import { fetchAdminTransactions, FigmaTransaction } from '../services/adapters';

type User = {
  id: number;
  username: string;
  fullName: string;
  role: 'user' | 'admin';
};

type Transaction = {
  id: number;
  uniqueCode: string;
  status: 'draft' | 'pending' | 'approved' | 'rejected' | 'paid';
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
};

const STATUS_CONFIG = {
  draft: { label: 'پیش‌نویس', color: 'bg-gray-500' },
  pending: { label: 'در انتظار تایید', color: 'bg-amber-500' },
  approved: { label: 'تایید شده', color: 'bg-green-600' },
  rejected: { label: 'رد شده', color: 'bg-red-600' },
  paid: { label: 'پرداخت شده', color: 'bg-blue-600' },
};

export function AdminDashboard({ user, onLogout, onNavigateToPublic }: AdminDashboardProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Load transactions from API
  useEffect(() => {
    const loadTransactions = async () => {
      setLoading(true);
      setError(null);

      try {
        const result = await fetchAdminTransactions({
          status: statusFilter !== 'all' ? statusFilter : undefined,
          search: searchTerm || undefined,
          page: currentPage
        });
        // Map to component format
        const mapped: Transaction[] = result.transactions.map(t => ({
          id: t.id,
          uniqueCode: t.uniqueCode,
          status: t.status,
          amount: t.amount,
          beneficiaryName: t.beneficiaryName,
          createdAt: t.createdAt,
          zoneName: t.zoneName,
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

  const handleApprove = (txId: number) => {
    setTransactions(prev =>
      prev.map(tx => tx.id === txId ? { ...tx, status: 'approved' as const } : tx)
    );
    setSelectedTransaction(null);
  };

  const handleReject = (txId: number, reason: string) => {
    setTransactions(prev =>
      prev.map(tx => tx.id === txId ? { ...tx, status: 'rejected' as const, rejectionReason: reason } : tx)
    );
    setSelectedTransaction(null);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('fa-IR').format(amount);
  };

  const stats = {
    total: transactions.length,
    pending: transactions.filter(t => t.status === 'pending').length,
    approved: transactions.filter(t => t.status === 'approved').length,
    rejected: transactions.filter(t => t.status === 'rejected').length,
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
                <p className="text-sm">{user.fullName}</p>
                <p className="text-xs text-muted-foreground">مدیر سیستم</p>
              </div>
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
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="p-4">
              <p className="text-sm text-muted-foreground">کل تراکنش‌ها</p>
              <p className="text-3xl mt-2">{stats.total}</p>
            </Card>
            <Card className="p-4 bg-amber-50 border-amber-200">
              <p className="text-sm text-amber-800">در انتظار تایید</p>
              <p className="text-3xl mt-2 text-amber-600">{stats.pending}</p>
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
                  <SelectItem value="pending">در انتظار تایید</SelectItem>
                  <SelectItem value="approved">تایید شده</SelectItem>
                  <SelectItem value="rejected">رد شده</SelectItem>
                  <SelectItem value="paid">پرداخت شده</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </Card>

          {/* Transactions Table - NO INLINE EDITING */}
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-right">کد یکتا</TableHead>
                  <TableHead className="text-right">وضعیت</TableHead>
                  <TableHead className="text-right">مبلغ (ریال)</TableHead>
                  <TableHead className="text-right">ردیف بودجه</TableHead>
                  <TableHead className="text-right">ذینفع</TableHead>
                  <TableHead className="text-right">ایجادکننده</TableHead>
                  <TableHead className="text-right">تاریخ</TableHead>
                  <TableHead className="text-right">عملیات</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedTransactions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
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
                        <Badge className={`${STATUS_CONFIG[tx.status].color} text-white`}>
                          {STATUS_CONFIG[tx.status].label}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono">{formatCurrency(tx.amount)}</TableCell>
                      <TableCell className="font-mono text-sm">{tx.budgetCode}</TableCell>
                      <TableCell className="max-w-[150px] truncate">{tx.beneficiaryName || '-'}</TableCell>
                      <TableCell>{tx.createdBy || '-'}</TableCell>
                      <TableCell className="text-sm">{tx.createdAt?.split(' - ')[0] || '-'}</TableCell>
                      <TableCell>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e: React.MouseEvent) => {
                            e.stopPropagation();
                            setSelectedTransaction(tx);
                          }}
                        >
                          بررسی
                        </Button>
                      </TableCell>
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

      {/* Side Panel for Review - NEVER INLINE EDITING */}
      {selectedTransaction && (
        <TransactionReviewPanel
          transaction={selectedTransaction}
          onClose={() => setSelectedTransaction(null)}
          onApprove={handleApprove}
          onReject={handleReject}
        />
      )}
    </div>
  );
}
