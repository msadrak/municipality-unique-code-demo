import React, { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from './ui/sheet';
import {
    Building2,
    LogOut,
    Search,
    ChevronLeft,
    ChevronRight,
    Loader2,
    CheckCircle2,
    Eye,
    Download,
    FileText,
    User,
    Calendar,
    Clock,
    Wallet,
    Hash,
    ShieldCheck
} from 'lucide-react';

type User = {
    id: number;
    username: string;
    fullName: string;
    role: string;
};

// Transaction History Entry
type HistoryEntry = {
    id: number;
    action: 'SUBMIT' | 'APPROVE' | 'REJECT' | 'RESUBMIT';
    actorName: string;
    actorLevel: number;
    timestamp: string;
    comment?: string;
};

// Approved Transaction with full details
type ApprovedTransaction = {
    id: number;
    uniqueCode: string;
    amount: number;
    budgetCode?: string;
    budgetDescription?: string;
    beneficiaryName?: string;
    createdBy?: string;
    createdAt?: string;
    approvedAt?: string;
    zoneName?: string;
    sectionName?: string;
    officeName?: string;
    costCenterName?: string;
    financialEventName?: string;
    description?: string;
    fiscalYear?: string;
    // History log
    history: HistoryEntry[];
};

type AccountantLedgerProps = {
    user: User;
    onLogout: () => void;
    onNavigateToPublic: () => void;
};

// Mock data for demonstration
const MOCK_TRANSACTIONS: ApprovedTransaction[] = [
    {
        id: 1,
        uniqueCode: '20-EXP-11020401-611-0001',
        amount: 150000000,
        budgetCode: '11020401',
        budgetDescription: 'حقوق و دستمزد - پرسنل اداری',
        beneficiaryName: 'محمد احمدی',
        createdBy: 'کاربر سطح ۱',
        createdAt: '1403/09/15 - 10:30',
        approvedAt: '1403/09/18 - 14:22',
        zoneName: 'منطقه ۳',
        sectionName: 'امور مالی',
        officeName: 'اداره حسابداری',
        costCenterName: 'مرکز هزینه ۱۰۱',
        financialEventName: 'تامین اعتبار',
        description: 'پرداخت حقوق آذرماه',
        fiscalYear: '1403',
        history: [
            { id: 1, action: 'SUBMIT', actorName: 'کاربر سطح ۱', actorLevel: 0, timestamp: '1403/09/15 - 10:30' },
            { id: 2, action: 'APPROVE', actorName: 'مسئول قسمت', actorLevel: 1, timestamp: '1403/09/16 - 09:15', comment: 'تایید شد' },
            { id: 3, action: 'APPROVE', actorName: 'رئیس اداره', actorLevel: 2, timestamp: '1403/09/17 - 11:30' },
            { id: 4, action: 'APPROVE', actorName: 'مدیر حوزه', actorLevel: 3, timestamp: '1403/09/17 - 16:45' },
            { id: 5, action: 'APPROVE', actorName: 'ذی‌حساب', actorLevel: 4, timestamp: '1403/09/18 - 14:22', comment: 'تایید نهایی' },
        ]
    },
    {
        id: 2,
        uniqueCode: '20-CON-22030501-612-0002',
        amount: 85000000,
        budgetCode: '22030501',
        budgetDescription: 'قراردادهای خدماتی',
        beneficiaryName: 'شرکت خدمات فنی البرز',
        createdBy: 'کاربر قراردادها',
        createdAt: '1403/09/12 - 08:45',
        approvedAt: '1403/09/16 - 10:10',
        zoneName: 'منطقه ۵',
        sectionName: 'امور قراردادها',
        officeName: 'اداره تدارکات',
        costCenterName: 'مرکز هزینه ۲۰۵',
        financialEventName: 'پیش‌پرداخت',
        description: 'پیش‌پرداخت قرارداد نگهداری تاسیسات',
        fiscalYear: '1403',
        history: [
            { id: 1, action: 'SUBMIT', actorName: 'کاربر قراردادها', actorLevel: 0, timestamp: '1403/09/12 - 08:45' },
            { id: 2, action: 'APPROVE', actorName: 'مسئول قسمت', actorLevel: 1, timestamp: '1403/09/13 - 10:00' },
            { id: 3, action: 'APPROVE', actorName: 'رئیس اداره', actorLevel: 2, timestamp: '1403/09/14 - 14:20' },
            { id: 4, action: 'APPROVE', actorName: 'مدیر حوزه', actorLevel: 3, timestamp: '1403/09/15 - 09:30' },
            { id: 5, action: 'APPROVE', actorName: 'ذی‌حساب', actorLevel: 4, timestamp: '1403/09/16 - 10:10' },
        ]
    },
    {
        id: 3,
        uniqueCode: '20-PET-33040601-613-0003',
        amount: 25000000,
        budgetCode: '33040601',
        budgetDescription: 'تنخواه‌گردان',
        beneficiaryName: 'علی رضایی',
        createdBy: 'کاربر تنخواه',
        createdAt: '1403/09/10 - 14:00',
        approvedAt: '1403/09/14 - 11:55',
        zoneName: 'منطقه ۱',
        sectionName: 'امور اداری',
        officeName: 'اداره پشتیبانی',
        costCenterName: 'مرکز هزینه ۳۰۱',
        financialEventName: 'تامین اعتبار',
        description: 'تنخواه خرید ملزومات اداری',
        fiscalYear: '1403',
        history: [
            { id: 1, action: 'SUBMIT', actorName: 'کاربر تنخواه', actorLevel: 0, timestamp: '1403/09/10 - 14:00' },
            { id: 2, action: 'APPROVE', actorName: 'مسئول قسمت', actorLevel: 1, timestamp: '1403/09/11 - 08:30' },
            { id: 3, action: 'APPROVE', actorName: 'رئیس اداره', actorLevel: 2, timestamp: '1403/09/12 - 11:15' },
            { id: 4, action: 'APPROVE', actorName: 'مدیر حوزه', actorLevel: 3, timestamp: '1403/09/13 - 15:40' },
            { id: 5, action: 'APPROVE', actorName: 'ذی‌حساب', actorLevel: 4, timestamp: '1403/09/14 - 11:55' },
        ]
    },
];

// Level labels
const LEVEL_LABELS: Record<number, string> = {
    0: 'کاربر',
    1: 'قسمت',
    2: 'اداره',
    3: 'حوزه',
    4: 'ذی‌حساب',
};

// ==========================================
// Validation Badge - 4 Green Checks
// ==========================================
function ValidationBadge() {
    return (
        <div className="flex items-center gap-0.5 bg-green-50 border border-green-200 rounded-full px-2 py-1">
            {[1, 2, 3, 4].map((level) => (
                <div key={level} className="flex flex-col items-center" title={LEVEL_LABELS[level]}>
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                </div>
            ))}
            <span className="text-[10px] text-green-700 font-medium mr-1">تایید کامل</span>
        </div>
    );
}

// ==========================================
// Transaction History Timeline
// ==========================================
function HistoryTimeline({ history }: { history: HistoryEntry[] }) {
    const getActionLabel = (action: HistoryEntry['action']) => {
        switch (action) {
            case 'SUBMIT': return 'ثبت درخواست';
            case 'APPROVE': return 'تایید';
            case 'REJECT': return 'رد';
            case 'RESUBMIT': return 'ارسال مجدد';
        }
    };

    const getActionColor = (action: HistoryEntry['action']) => {
        switch (action) {
            case 'SUBMIT': return 'bg-blue-500';
            case 'APPROVE': return 'bg-green-500';
            case 'REJECT': return 'bg-red-500';
            case 'RESUBMIT': return 'bg-amber-500';
        }
    };

    return (
        <div className="space-y-3">
            {history.map((entry, index) => (
                <div key={entry.id} className="flex gap-3">
                    {/* Timeline line */}
                    <div className="flex flex-col items-center">
                        <div className={`w-3 h-3 rounded-full ${getActionColor(entry.action)}`} />
                        {index < history.length - 1 && (
                            <div className="w-0.5 h-full bg-gray-200 min-h-[30px]" />
                        )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 pb-3">
                        <div className="flex items-center gap-2">
                            <span className="font-medium text-sm">{getActionLabel(entry.action)}</span>
                            <Badge variant="outline" className="text-[10px] h-5">
                                {entry.actorLevel === 0 ? 'کاربر' : `سطح ${entry.actorLevel}`}
                            </Badge>
                        </div>
                        <div className="text-sm text-muted-foreground mt-0.5">
                            <span className="font-medium">{entry.actorName}</span>
                            <span className="mx-2">•</span>
                            <span dir="ltr">{entry.timestamp}</span>
                        </div>
                        {entry.comment && (
                            <p className="text-sm text-muted-foreground mt-1 bg-muted/50 p-2 rounded">
                                {entry.comment}
                            </p>
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
}

// ==========================================
// Details Sheet (Drawer)
// ==========================================
type DetailsSheetProps = {
    transaction: ApprovedTransaction | null;
    isOpen: boolean;
    onClose: () => void;
};

function DetailsSheet({ transaction, isOpen, onClose }: DetailsSheetProps) {
    if (!transaction) return null;

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat('fa-IR').format(amount);
    };

    return (
        <Sheet open={isOpen} onOpenChange={onClose}>
            <SheetContent side="left" className="w-full sm:max-w-lg overflow-y-auto">
                <SheetHeader>
                    <SheetTitle className="flex items-center gap-2">
                        <ShieldCheck className="h-5 w-5 text-green-600" />
                        جزئیات تراکنش تایید شده
                    </SheetTitle>
                    <SheetDescription>
                        اطلاعات کامل و زنجیره تاییدات
                    </SheetDescription>
                </SheetHeader>

                <div className="mt-6 space-y-6">
                    {/* Unique Code */}
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-2">
                            <Hash className="h-4 w-4 text-green-600" />
                            <span className="text-sm text-green-800 font-medium">کد یکتای حسابداری</span>
                        </div>
                        <p className="font-mono text-lg font-bold text-green-900" dir="ltr">
                            {transaction.uniqueCode}
                        </p>
                        <ValidationBadge />
                    </div>

                    {/* Financial Details */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="bg-muted/50 rounded-lg p-3">
                            <div className="flex items-center gap-2 mb-1">
                                <Wallet className="h-4 w-4 text-muted-foreground" />
                                <span className="text-xs text-muted-foreground">مبلغ</span>
                            </div>
                            <p className="font-mono font-bold">{formatCurrency(transaction.amount)} ریال</p>
                        </div>
                        <div className="bg-muted/50 rounded-lg p-3">
                            <div className="flex items-center gap-2 mb-1">
                                <FileText className="h-4 w-4 text-muted-foreground" />
                                <span className="text-xs text-muted-foreground">کد بودجه</span>
                            </div>
                            <p className="font-mono font-medium" dir="ltr">{transaction.budgetCode}</p>
                        </div>
                    </div>

                    {/* Details Grid */}
                    <div className="space-y-3 text-sm">
                        <div className="flex justify-between border-b pb-2">
                            <span className="text-muted-foreground">شرح ردیف بودجه</span>
                            <span className="font-medium">{transaction.budgetDescription}</span>
                        </div>
                        <div className="flex justify-between border-b pb-2">
                            <span className="text-muted-foreground">ذینفع</span>
                            <span className="font-medium">{transaction.beneficiaryName}</span>
                        </div>
                        <div className="flex justify-between border-b pb-2">
                            <span className="text-muted-foreground">منطقه</span>
                            <span className="font-medium">{transaction.zoneName}</span>
                        </div>
                        <div className="flex justify-between border-b pb-2">
                            <span className="text-muted-foreground">اداره / قسمت</span>
                            <span className="font-medium">{transaction.officeName} / {transaction.sectionName}</span>
                        </div>
                        <div className="flex justify-between border-b pb-2">
                            <span className="text-muted-foreground">مرکز هزینه</span>
                            <span className="font-medium">{transaction.costCenterName}</span>
                        </div>
                        <div className="flex justify-between border-b pb-2">
                            <span className="text-muted-foreground">رویداد مالی</span>
                            <span className="font-medium">{transaction.financialEventName}</span>
                        </div>
                        <div className="flex justify-between border-b pb-2">
                            <span className="text-muted-foreground">شرح</span>
                            <span className="font-medium">{transaction.description}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">سال مالی</span>
                            <span className="font-medium">{transaction.fiscalYear}</span>
                        </div>
                    </div>

                    {/* Approval History */}
                    <div className="border-t pt-4">
                        <h3 className="font-semibold mb-4 flex items-center gap-2">
                            <Clock className="h-4 w-4" />
                            زنجیره تاییدات
                        </h3>
                        <HistoryTimeline history={transaction.history} />
                    </div>
                </div>
            </SheetContent>
        </Sheet>
    );
}

// ==========================================
// Main AccountantLedger Component
// ==========================================
export function AccountantLedger({ user, onLogout, onNavigateToPublic }: AccountantLedgerProps) {
    const [transactions, setTransactions] = useState<ApprovedTransaction[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedTransaction, setSelectedTransaction] = useState<ApprovedTransaction | null>(null);
    const [detailsOpen, setDetailsOpen] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [exportingId, setExportingId] = useState<number | null>(null);
    const itemsPerPage = 15; // Higher density

    // Load transactions (mock)
    useEffect(() => {
        const loadTransactions = async () => {
            setLoading(true);
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 500));
            setTransactions(MOCK_TRANSACTIONS);
            setLoading(false);
        };
        loadTransactions();
    }, []);

    const filteredTransactions = transactions.filter(tx => {
        const searchLower = searchTerm.toLowerCase();
        return (
            tx.uniqueCode.toLowerCase().includes(searchLower) ||
            tx.budgetCode?.toLowerCase().includes(searchLower) ||
            tx.beneficiaryName?.toLowerCase().includes(searchLower) ||
            tx.budgetDescription?.toLowerCase().includes(searchLower)
        );
    });

    const totalPages = Math.ceil(filteredTransactions.length / itemsPerPage);
    const paginatedTransactions = filteredTransactions.slice(
        (currentPage - 1) * itemsPerPage,
        currentPage * itemsPerPage
    );

    const handleViewDetails = (tx: ApprovedTransaction) => {
        setSelectedTransaction(tx);
        setDetailsOpen(true);
    };

    const handleExport = async (txId: number) => {
        setExportingId(txId);
        // Mock export delay
        await new Promise(resolve => setTimeout(resolve, 1500));
        alert(`✅ تراکنش ${txId} با موفقیت به سیستم حسابداری صادر شد.`);
        setExportingId(null);
    };

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat('fa-IR').format(amount);
    };

    const stats = {
        total: transactions.length,
        totalAmount: transactions.reduce((sum, t) => sum + t.amount, 0),
    };

    return (
        <div className="min-h-screen bg-background">
            {/* Header */}
            <header className="bg-green-900 text-white">
                <div className="container mx-auto px-4 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="bg-green-700 p-2 rounded">
                                <Building2 className="h-6 w-6" />
                            </div>
                            <div>
                                <h1 className="text-lg font-bold">دفتر حسابداری</h1>
                                <p className="text-sm text-green-200">تراکنش‌های تایید شده - آماده ثبت سند</p>
                            </div>
                        </div>

                        <div className="flex items-center gap-4">
                            <div className="text-left">
                                <p className="text-sm font-medium">{user.fullName}</p>
                                <Badge className="bg-green-700 text-green-100 text-[10px]">
                                    حسابدار
                                </Badge>
                            </div>
                            <Button variant="outline" size="sm" onClick={onLogout} className="border-green-600 text-white hover:bg-green-800">
                                <LogOut className="h-4 w-4 ml-2" />
                                خروج
                            </Button>
                        </div>
                    </div>
                </div>
            </header>

            <main className="container mx-auto px-4 py-6">
                <div className="space-y-4">
                    {/* Stats - Compact */}
                    <div className="grid grid-cols-2 gap-4">
                        <Card className="p-4 bg-green-50 border-green-200">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-green-800">تراکنش‌های آماده</p>
                                    <p className="text-3xl font-bold text-green-700 mt-1">{stats.total}</p>
                                </div>
                                <ShieldCheck className="h-10 w-10 text-green-600 opacity-50" />
                            </div>
                        </Card>
                        <Card className="p-4 bg-green-50 border-green-200">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-green-800">مجموع مبالغ</p>
                                    <p className="text-2xl font-bold text-green-700 mt-1 font-mono">
                                        {formatCurrency(stats.totalAmount)} <span className="text-sm font-normal">ریال</span>
                                    </p>
                                </div>
                                <Wallet className="h-10 w-10 text-green-600 opacity-50" />
                            </div>
                        </Card>
                    </div>

                    {/* Search Bar - Compact */}
                    <Card className="p-3">
                        <div className="relative">
                            <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="جستجو بر اساس کد یکتا، کد بودجه یا ذینفع..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="pr-10 h-9"
                            />
                        </div>
                    </Card>

                    {/* High-Density Data Table */}
                    <Card className="overflow-hidden">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-green-50">
                                    <TableHead className="text-right text-xs font-bold text-green-900">کد یکتا</TableHead>
                                    <TableHead className="text-right text-xs font-bold text-green-900">وضعیت تایید</TableHead>
                                    <TableHead className="text-right text-xs font-bold text-green-900">مبلغ (ریال)</TableHead>
                                    <TableHead className="text-right text-xs font-bold text-green-900">کد بودجه</TableHead>
                                    <TableHead className="text-right text-xs font-bold text-green-900">ذینفع</TableHead>
                                    <TableHead className="text-right text-xs font-bold text-green-900">تاریخ تایید</TableHead>
                                    <TableHead className="text-right text-xs font-bold text-green-900">عملیات</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    <TableRow>
                                        <TableCell colSpan={7} className="text-center py-8">
                                            <div className="flex justify-center">
                                                <Loader2 className="h-6 w-6 animate-spin text-green-600" />
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
                                        <TableRow key={tx.id} className="hover:bg-green-50/50">
                                            <TableCell className="font-mono text-xs py-2" dir="ltr">
                                                {tx.uniqueCode}
                                            </TableCell>
                                            <TableCell className="py-2">
                                                <ValidationBadge />
                                            </TableCell>
                                            <TableCell className="font-mono text-sm py-2">
                                                {formatCurrency(tx.amount)}
                                            </TableCell>
                                            <TableCell className="font-mono text-xs py-2" dir="ltr">
                                                {tx.budgetCode}
                                            </TableCell>
                                            <TableCell className="text-sm py-2 max-w-[120px] truncate">
                                                {tx.beneficiaryName}
                                            </TableCell>
                                            <TableCell className="text-xs py-2" dir="ltr">
                                                {tx.approvedAt?.split(' - ')[0]}
                                            </TableCell>
                                            <TableCell className="py-2">
                                                <div className="flex gap-1">
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        className="h-7 px-2 text-xs"
                                                        onClick={() => handleViewDetails(tx)}
                                                    >
                                                        <Eye className="h-3 w-3 ml-1" />
                                                        جزئیات
                                                    </Button>
                                                    <Button
                                                        variant="default"
                                                        size="sm"
                                                        className="h-7 px-2 text-xs bg-green-600 hover:bg-green-700"
                                                        onClick={() => handleExport(tx.id)}
                                                        disabled={exportingId === tx.id}
                                                    >
                                                        {exportingId === tx.id ? (
                                                            <Loader2 className="h-3 w-3 animate-spin ml-1" />
                                                        ) : (
                                                            <Download className="h-3 w-3 ml-1" />
                                                        )}
                                                        صادرات
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <div className="flex items-center justify-between p-3 border-t bg-muted/30">
                                <p className="text-xs text-muted-foreground">
                                    صفحه {currentPage} از {totalPages} ({filteredTransactions.length} مورد)
                                </p>
                                <div className="flex gap-1">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        className="h-7 w-7 p-0"
                                        onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                                        disabled={currentPage === 1}
                                    >
                                        <ChevronRight className="h-4 w-4" />
                                    </Button>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        className="h-7 w-7 p-0"
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

            {/* Details Sheet */}
            <DetailsSheet
                transaction={selectedTransaction}
                isOpen={detailsOpen}
                onClose={() => {
                    setDetailsOpen(false);
                    setSelectedTransaction(null);
                }}
            />
        </div>
    );
}
