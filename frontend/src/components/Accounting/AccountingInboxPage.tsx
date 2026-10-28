/**
 * Accounting Inbox Page
 *
 * Main page component for accounting staff to view and post transactions.
 * Based on frontend_architecture.md v2 design.
 */
import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import {
    AlertCircle,
    CheckCircle2,
    ChevronLeft,
    ChevronRight,
    Download,
    Eye,
    FileText,
    Inbox,
    Loader2,
    RefreshCw,
    Search,
    Send,
    ShieldAlert,
    X,
} from 'lucide-react';
import { toast } from 'sonner';

import {
    InboxItem, InboxFilters, JournalPreview,
    PostRequest, BatchPostRequest, BatchPostResponse, AccountingStatus
} from '../../types/accounting';
import {
    fetchAccountingInbox, fetchJournalPreview,
    postTransaction, batchPostTransactions, exportTransactions
} from '../../services/accounting';
import { formatRial } from '../../lib/utils';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '../ui/card';
import { Input } from '../ui/input';
import { Skeleton } from '../ui/skeleton';
import { cn } from '../ui/utils';

const STATUS_OPTIONS = [
    { value: 'ALL', label: 'همه' },
    { value: 'READY_TO_POST', label: 'آماده ثبت' },
    { value: 'POSTED', label: 'ثبت شده' },
    { value: 'POST_ERROR', label: 'خطا' },
] as const;

const STATUS_META: Record<string, { label: string; className: string; dotClassName: string }> = {
    READY_TO_POST: {
        label: 'آماده ثبت',
        className: 'border-amber-200 bg-amber-50 text-amber-700',
        dotClassName: 'bg-amber-500',
    },
    POSTED: {
        label: 'ثبت شده',
        className: 'border-emerald-200 bg-emerald-50 text-emerald-700',
        dotClassName: 'bg-emerald-500',
    },
    POST_ERROR: {
        label: 'خطا',
        className: 'border-red-200 bg-red-50 text-red-700',
        dotClassName: 'bg-red-500',
    },
};

const VALIDATION_META: Record<string, { label: string; className: string }> = {
    VALID: { label: 'معتبر', className: 'border-emerald-200 bg-emerald-50 text-emerald-700' },
    WARNING: { label: 'دارای هشدار', className: 'border-amber-200 bg-amber-50 text-amber-700' },
    BLOCKED: { label: 'مسدود', className: 'border-red-200 bg-red-50 text-red-700' },
};

function AccountingInboxSkeleton() {
    return (
        <div className="space-y-5">
            <div className="grid gap-4 md:grid-cols-4">
                {Array.from({ length: 4 }).map((_, index) => (
                    <Skeleton key={index} className="h-28 rounded-xl" />
                ))}
            </div>
            <Skeleton className="h-24 rounded-xl" />
            <Skeleton className="h-[430px] rounded-xl" />
        </div>
    );
}

function formatDate(dateStr: string | null) {
    if (!dateStr) return '---';
    return new Date(dateStr).toLocaleDateString('fa-IR');
}

function getStatusMeta(status: AccountingStatus | null | undefined) {
    return STATUS_META[status || 'READY_TO_POST'] || STATUS_META.READY_TO_POST;
}

function getValidationMeta(status: string | null | undefined) {
    return VALIDATION_META[status || 'VALID'] || VALIDATION_META.VALID;
}

function StatusBadge({ status }: { status: AccountingStatus | null | undefined }) {
    const meta = getStatusMeta(status);

    return (
        <Badge variant="outline" className={cn('gap-2 rounded-full px-3 py-1 font-semibold', meta.className)}>
            <span className={cn('h-2 w-2 rounded-full', meta.dotClassName)} />
            {meta.label}
        </Badge>
    );
}

function ValidationBadge({ status }: { status: string | null | undefined }) {
    const meta = getValidationMeta(status);

    return (
        <Badge variant="outline" className={cn('rounded-full px-3 py-1 font-semibold', meta.className)}>
            {meta.label}
        </Badge>
    );
}

function EmptyState({ onRefresh }: { onRefresh: () => void }) {
    return (
        <Card className="border-dashed border-slate-300 bg-white">
            <CardContent className="flex min-h-[320px] flex-col items-center justify-center gap-4 p-8 text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-50 text-blue-700">
                    <Inbox className="h-8 w-8" />
                </div>
                <div className="space-y-2">
                    <h2 className="text-lg font-bold text-slate-900">تراکنشی برای نمایش وجود ندارد</h2>
                    <p className="max-w-md text-sm leading-7 text-muted-foreground">
                        با فیلترهای فعلی سندی در کارتابل حسابداری پیدا نشد. وضعیت یا عبارت جستجو را تغییر دهید.
                    </p>
                </div>
                <Button variant="outline" className="rounded-lg" onClick={onRefresh}>
                    <RefreshCw className="h-4 w-4" />
                    بروزرسانی کارتابل
                </Button>
            </CardContent>
        </Card>
    );
}

interface ErrorStateProps {
    message: string;
    onRetry: () => void;
}

function ErrorState({ message, onRetry }: ErrorStateProps) {
    return (
        <Card className="border-red-200 bg-red-50/60">
            <CardContent className="flex min-h-[260px] flex-col items-center justify-center gap-4 p-8 text-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-red-100 text-red-700">
                    <AlertCircle className="h-7 w-7" />
                </div>
                <div className="space-y-2">
                    <h2 className="text-lg font-bold text-red-950">خطا در دریافت کارتابل حسابداری</h2>
                    <p className="max-w-lg text-sm leading-7 text-red-700">{message}</p>
                </div>
                <Button variant="destructive" className="rounded-lg" onClick={onRetry}>
                    تلاش مجدد
                </Button>
            </CardContent>
        </Card>
    );
}

// ============ MAIN COMPONENT ============
export function AccountingInboxPage() {
    // State
    const [items, setItems] = useState<InboxItem[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Filters
    const [filters, setFilters] = useState<InboxFilters>({
        status: 'READY_TO_POST',
        limit: 50,
        offset: 0,
    });
    const [searchInput, setSearchInput] = useState('');

    // Selection
    const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

    // Preview drawer
    const [previewId, setPreviewId] = useState<number | null>(null);
    const [preview, setPreview] = useState<JournalPreview | null>(null);
    const [previewLoading, setPreviewLoading] = useState(false);

    // Posting modal
    const [postingItem, setPostingItem] = useState<InboxItem | null>(null);
    const [postingRef, setPostingRef] = useState('');
    const [postingNotes, setPostingNotes] = useState('');
    const [posting, setPosting] = useState(false);

    // Batch posting modal/results
    const [batchDialogOpen, setBatchDialogOpen] = useState(false);
    const [batchPrefix, setBatchPrefix] = useState('GL-');
    const [batchResults, setBatchResults] = useState<BatchPostResponse | null>(null);
    const [exporting, setExporting] = useState(false);

    // Refs for focus management
    const tableRef = useRef<HTMLTableElement>(null);
    const drawerRef = useRef<HTMLDivElement>(null);

    // ============ DATA FETCHING ============
    const loadInbox = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetchAccountingInbox(filters);
            setItems(response.items);
            setTotal(response.total);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'خطا در بارگذاری';
            setError(message);
            toast.error(message);
        } finally {
            setLoading(false);
        }
    }, [filters]);

    useEffect(() => {
        loadInbox();
    }, [loadInbox]);

    // Debounced search
    useEffect(() => {
        const timer = setTimeout(() => {
            setFilters(f => ({ ...f, search: searchInput || undefined, offset: 0 }));
        }, 300);
        return () => clearTimeout(timer);
    }, [searchInput]);

    // ============ PREVIEW ============
    const openPreview = useCallback(async (id: number) => {
        setPreviewId(id);
        setPreview(null);
        setPreviewLoading(true);
        try {
            const data = await fetchJournalPreview(id);
            setPreview(data);
        } catch (err) {
            console.error('Preview error:', err);
            toast.error('دریافت پیش نمایش سند ناموفق بود');
        } finally {
            setPreviewLoading(false);
        }
    }, []);

    const closePreview = useCallback(() => {
        setPreviewId(null);
        setPreview(null);
        tableRef.current?.focus();
    }, []);

    // ============ POSTING ============
    const handlePostClick = useCallback((item: InboxItem) => {
        setPostingItem(item);
        setPostingRef('');
        setPostingNotes('');
    }, []);

    const confirmPost = useCallback(async () => {
        if (!postingItem) return;

        const normalizedRef = postingRef.trim();
        if (!normalizedRef) {
            toast.error('شماره مرجع ثبت الزامی است');
            return;
        }

        setPosting(true);
        try {
            const request: PostRequest = {
                posting_ref: normalizedRef,
                notes: postingNotes.trim() || undefined,
                version: postingItem.version,
            };

            await postTransaction(postingItem.id, request);

            // Refetch inbox
            await loadInbox();

            // Close modal
            setPostingItem(null);
            toast.success('سند حسابداری با موفقیت ثبت شد');

        } catch (err: any) {
            if (err?.error === 'VERSION_MISMATCH') {
                toast.warning('این تراکنش توسط کاربر دیگری تغییر کرده است. کارتابل بروزرسانی شد.');
                await loadInbox();
            } else if (err?.error === 'CONFLICT') {
                toast.error(`قبلا با شماره ${err.existing_ref} ثبت شده است`);
            } else {
                toast.error(err?.message || 'خطا در ثبت سند');
            }
        } finally {
            setPosting(false);
        }
    }, [postingItem, postingRef, postingNotes, loadInbox]);

    // ============ BATCH POST ============
    const handleBatchPost = useCallback(async () => {
        const selectedItems = items.filter(item => selectedIds.has(item.id));
        if (selectedItems.length === 0) return;

        const normalizedPrefix = batchPrefix.trim();
        if (!normalizedPrefix) {
            toast.error('پیشوند شماره مرجع الزامی است');
            return;
        }

        const request: BatchPostRequest = {
            items: selectedItems.map((item, index) => ({
                transaction_id: item.id,
                posting_ref: `${normalizedPrefix}${String(index + 1).padStart(4, '0')}`,
                version: item.version,
            })),
        };

        setPosting(true);
        try {
            const response = await batchPostTransactions(request);
            setBatchResults(response);
            setSelectedIds(new Set());
            setBatchDialogOpen(false);
            await loadInbox();

            if (response.failed > 0) {
                toast.warning(`${response.succeeded} سند ثبت شد و ${response.failed} سند ناموفق بود`);
            } else {
                toast.success(`${response.succeeded} سند با موفقیت ثبت شد`);
            }
        } catch (err) {
            toast.error('خطا در ثبت دسته ای');
        } finally {
            setPosting(false);
        }
    }, [items, selectedIds, batchPrefix, loadInbox]);

    // ============ EXPORT ============
    const handleExport = useCallback(async () => {
        const ids = selectedIds.size > 0
            ? Array.from(selectedIds)
            : items.map(i => i.id);

        if (ids.length === 0) {
            toast.warning('تراکنشی برای خروجی گرفتن وجود ندارد');
            return;
        }

        setExporting(true);
        try {
            await exportTransactions({
                transaction_ids: ids,
                format: 'csv',
                include_journal_lines: true,
            });
            toast.success('فایل خروجی آماده شد');
        } catch (err) {
            toast.error('خطا در خروجی');
        } finally {
            setExporting(false);
        }
    }, [selectedIds, items]);

    // ============ SELECTION ============
    const toggleSelection = useCallback((id: number) => {
        setSelectedIds(prev => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    }, []);

    const toggleSelectAll = useCallback(() => {
        if (selectedIds.size === items.length) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(items.map(i => i.id)));
        }
    }, [items, selectedIds]);

    // ============ KEYBOARD NAVIGATION ============
    const [focusedIndex, setFocusedIndex] = useState(0);

    const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                setFocusedIndex(i => Math.min(i + 1, items.length - 1));
                break;
            case 'ArrowUp':
                e.preventDefault();
                setFocusedIndex(i => Math.max(i - 1, 0));
                break;
            case 'Enter':
                if (items[focusedIndex]) {
                    openPreview(items[focusedIndex].id);
                }
                break;
            case ' ':
                e.preventDefault();
                if (items[focusedIndex]) {
                    toggleSelection(items[focusedIndex].id);
                }
                break;
            case 'F7':
                if (items[focusedIndex]) {
                    handlePostClick(items[focusedIndex]);
                }
                break;
            case 'Escape':
                closePreview();
                break;
        }

        // Alt+key combinations
        if (e.altKey) {
            switch (e.key.toLowerCase()) {
                case 'p':
                    e.preventDefault();
                    if (items[focusedIndex]) {
                        handlePostClick(items[focusedIndex]);
                    }
                    break;
                case 'e':
                    e.preventDefault();
                    handleExport();
                    break;
            }
        }
    }, [items, focusedIndex, openPreview, toggleSelection, handlePostClick, handleExport, closePreview]);

    const selectedItems = useMemo(
        () => items.filter(item => selectedIds.has(item.id)),
        [items, selectedIds],
    );
    const readyCount = useMemo(
        () => items.filter(item => !item.accounting_status || item.accounting_status === 'READY_TO_POST').length,
        [items],
    );
    const errorCount = useMemo(
        () => items.filter(item => item.accounting_status === 'POST_ERROR').length,
        [items],
    );
    const pageAmount = useMemo(
        () => items.reduce((sum, item) => sum + item.amount, 0),
        [items],
    );
    const selectedAmount = useMemo(
        () => selectedItems.reduce((sum, item) => sum + item.amount, 0),
        [selectedItems],
    );
    const rangeStart = total === 0 ? 0 : (filters.offset || 0) + 1;
    const rangeEnd = Math.min((filters.offset || 0) + (filters.limit || 50), total);
    const postingRefInvalid = postingItem !== null && postingRef.trim().length === 0;

    return (
        <div className="w-full space-y-6 text-right" dir="rtl">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div className="space-y-2">
                    <div className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
                        <FileText className="h-3.5 w-3.5" />
                        کارتابل ثبت سند
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-slate-950">صندوق حسابداری</h1>
                        <p className="mt-1 text-sm leading-7 text-muted-foreground">
                            بررسی، پیش نمایش و ثبت اسناد مالی تایید شده در گردش کار
                        </p>
                    </div>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                    <Button
                        variant="outline"
                        className="rounded-lg bg-white"
                        onClick={loadInbox}
                        disabled={loading}
                        aria-label="بارگذاری مجدد"
                    >
                        <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
                        بارگذاری مجدد
                    </Button>
                    <Button
                        variant="outline"
                        className="rounded-lg bg-white"
                        onClick={handleExport}
                        disabled={exporting || items.length === 0}
                    >
                        {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                        خروجی CSV
                    </Button>
                </div>
            </div>

            {loading && items.length === 0 ? (
                <AccountingInboxSkeleton />
            ) : (
                <>
                    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                        <Card className="border-slate-200 bg-white shadow-sm">
                            <CardContent className="flex items-center justify-between gap-4 p-5">
                                <div className="space-y-1">
                                    <p className="text-sm text-muted-foreground">کل نتایج</p>
                                    <p className="text-2xl font-bold text-slate-950">{total.toLocaleString('fa-IR')}</p>
                                </div>
                                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-100 text-slate-700">
                                    <Inbox className="h-5 w-5" />
                                </div>
                            </CardContent>
                        </Card>
                        <Card className="border-amber-200 bg-amber-50/70 shadow-sm">
                            <CardContent className="flex items-center justify-between gap-4 p-5">
                                <div className="space-y-1">
                                    <p className="text-sm text-amber-700/80">آماده ثبت در این صفحه</p>
                                    <p className="text-2xl font-bold text-amber-900">{readyCount.toLocaleString('fa-IR')}</p>
                                </div>
                                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white text-amber-700">
                                    <Send className="h-5 w-5" />
                                </div>
                            </CardContent>
                        </Card>
                        <Card className="border-red-200 bg-red-50/70 shadow-sm">
                            <CardContent className="flex items-center justify-between gap-4 p-5">
                                <div className="space-y-1">
                                    <p className="text-sm text-red-700/80">خطاهای ثبت</p>
                                    <p className="text-2xl font-bold text-red-900">{errorCount.toLocaleString('fa-IR')}</p>
                                </div>
                                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white text-red-700">
                                    <ShieldAlert className="h-5 w-5" />
                                </div>
                            </CardContent>
                        </Card>
                        <Card className="border-blue-200 bg-blue-950 text-white shadow-sm">
                            <CardContent className="space-y-1 p-5">
                                <p className="text-sm text-blue-100">جمع مبلغ صفحه</p>
                                <p className="font-mono-num text-xl font-black">{formatRial(pageAmount)}</p>
                            </CardContent>
                        </Card>
                    </div>

                    <Card className="border-slate-200 bg-white shadow-sm">
                        <CardContent className="p-4 md:p-5">
                            <div className="grid gap-4 lg:grid-cols-[220px_1fr]">
                                <label className="space-y-2">
                                    <span className="text-sm font-semibold text-slate-700">وضعیت سند</span>
                                    <select
                                        value={filters.status || 'ALL'}
                                        onChange={e => setFilters(f => ({
                                            ...f,
                                            status: e.target.value as AccountingStatus | 'ALL',
                                            offset: 0
                                        }))}
                                        className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
                                    >
                                        {STATUS_OPTIONS.map(opt => (
                                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                                        ))}
                                    </select>
                                </label>

                                <label className="space-y-2">
                                    <span className="text-sm font-semibold text-slate-700">جستجوی تراکنش</span>
                                    <div className="relative">
                                        <Search className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                                        <Input
                                            type="text"
                                            placeholder="شناسه، ذینفع یا منطقه را جستجو کنید"
                                            value={searchInput}
                                            onChange={e => setSearchInput(e.target.value)}
                                            className="h-10 rounded-lg border-slate-200 bg-white pr-10 text-right"
                                        />
                                    </div>
                                    <p className="text-xs leading-6 text-muted-foreground">
                                        جستجو با تاخیر کوتاه اعمال می شود تا کارتابل بدون پرش بروزرسانی شود.
                                    </p>
                                </label>
                            </div>
                        </CardContent>
                    </Card>

                    {selectedIds.size > 0 && (
                        <Card className="border-blue-200 bg-blue-950 text-white shadow-sm">
                            <CardContent className="flex flex-col gap-4 p-4 md:flex-row md:items-center md:justify-between">
                                <div className="space-y-1">
                                    <p className="text-sm font-semibold">
                                        {selectedIds.size.toLocaleString('fa-IR')} مورد انتخاب شده
                                    </p>
                                    <p className="font-mono-num text-sm text-blue-100">
                                        جمع انتخاب: {formatRial(selectedAmount)}
                                    </p>
                                </div>
                                <div className="flex flex-wrap items-center gap-2">
                                    <Button
                                        variant="secondary"
                                        className="rounded-lg bg-white text-blue-950 hover:bg-blue-50"
                                        onClick={() => setBatchDialogOpen(true)}
                                        disabled={posting}
                                    >
                                        {posting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                                        ثبت دسته ای
                                    </Button>
                                    <Button
                                        variant="outline"
                                        className="rounded-lg border-white/30 bg-white/10 text-white hover:bg-white hover:text-blue-950"
                                        onClick={handleExport}
                                        disabled={exporting}
                                    >
                                        {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                                        خروجی
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        className="rounded-lg text-white hover:bg-white/10"
                                        onClick={() => setSelectedIds(new Set())}
                                    >
                                        لغو انتخاب
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {error ? (
                        <ErrorState message={error} onRetry={loadInbox} />
                    ) : items.length === 0 ? (
                        <EmptyState onRefresh={loadInbox} />
                    ) : (
                        <Card className="overflow-hidden border-slate-200 bg-white shadow-sm">
                            <CardHeader className="border-b border-slate-100 pb-5">
                                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                                    <div>
                                        <CardTitle className="text-base font-bold text-slate-950">
                                            تراکنش های آماده عملیات
                                        </CardTitle>
                                        <CardDescription className="mt-1 text-sm">
                                            برای پیش نمایش دوبار کلیک کنید یا از کلید Enter روی ردیف فعال استفاده کنید.
                                        </CardDescription>
                                    </div>
                                    {loading && (
                                        <Badge variant="outline" className="gap-2 rounded-full border-blue-200 bg-blue-50 text-blue-700">
                                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                            در حال بروزرسانی
                                        </Badge>
                                    )}
                                </div>
                            </CardHeader>
                            <CardContent className="p-0">
                                <div className="hidden overflow-x-auto lg:block">
                                    <table
                                        ref={tableRef}
                                        role="grid"
                                        className="w-full min-w-[980px] text-sm outline-none"
                                        tabIndex={0}
                                        onKeyDown={handleKeyDown}
                                    >
                                        <thead className="border-b border-slate-200 bg-slate-50 text-slate-500">
                                            <tr>
                                                <th className="w-12 px-4 py-4 text-right">
                                                    <input
                                                        type="checkbox"
                                                        checked={items.length > 0 && selectedIds.size === items.length}
                                                        onChange={toggleSelectAll}
                                                        aria-label="انتخاب همه"
                                                        className="h-4 w-4 rounded border-slate-300 accent-blue-700"
                                                    />
                                                </th>
                                                <th className="px-4 py-4 text-right font-semibold">شناسه</th>
                                                <th className="px-4 py-4 text-right font-semibold">تاریخ تایید</th>
                                                <th className="px-4 py-4 text-right font-semibold">ذینفع</th>
                                                <th className="px-4 py-4 text-right font-semibold">مبلغ</th>
                                                <th className="px-4 py-4 text-right font-semibold">منطقه</th>
                                                <th className="px-4 py-4 text-right font-semibold">اعتبارسنجی</th>
                                                <th className="px-4 py-4 text-right font-semibold">وضعیت</th>
                                                <th className="px-4 py-4 text-center font-semibold">عملیات</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-100">
                                            {items.map((item, index) => (
                                                <tr
                                                    key={item.id}
                                                    className={cn(
                                                        'transition-colors hover:bg-slate-50',
                                                        focusedIndex === index && 'bg-blue-50/70 outline outline-2 outline-inset outline-blue-200',
                                                        selectedIds.has(item.id) && 'bg-blue-50'
                                                    )}
                                                    onClick={() => setFocusedIndex(index)}
                                                    onDoubleClick={() => openPreview(item.id)}
                                                >
                                                    <td className="px-4 py-4">
                                                        <input
                                                            type="checkbox"
                                                            checked={selectedIds.has(item.id)}
                                                            onChange={() => toggleSelection(item.id)}
                                                            aria-label={`انتخاب ${item.unique_code}`}
                                                            className="h-4 w-4 rounded border-slate-300 accent-blue-700"
                                                        />
                                                    </td>
                                                    <td className="px-4 py-4">
                                                        <button
                                                            type="button"
                                                            className="font-mono-num rounded-md bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-900 transition hover:bg-slate-200 focus:outline-none focus:ring-4 focus:ring-blue-100"
                                                            onClick={() => openPreview(item.id)}
                                                        >
                                                            {item.unique_code}
                                                        </button>
                                                    </td>
                                                    <td className="px-4 py-4 text-slate-600">{formatDate(item.approved_at)}</td>
                                                    <td className="px-4 py-4">
                                                        <div className="max-w-[220px] truncate font-semibold text-slate-900" title={item.beneficiary_name}>
                                                            {item.beneficiary_name}
                                                        </div>
                                                    </td>
                                                    <td className="px-4 py-4">
                                                        <span className="font-mono-num whitespace-nowrap text-left text-base font-black text-slate-950">
                                                            {formatRial(item.amount)}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-4 text-slate-600">{item.zone_title}</td>
                                                    <td className="px-4 py-4">
                                                        <ValidationBadge status={item.validation_status} />
                                                    </td>
                                                    <td className="px-4 py-4">
                                                        <StatusBadge status={item.accounting_status} />
                                                    </td>
                                                    <td className="px-4 py-4">
                                                        <div className="flex items-center justify-center gap-2">
                                                            <Button
                                                                variant="outline"
                                                                size="sm"
                                                                className="rounded-lg bg-white"
                                                                onClick={() => openPreview(item.id)}
                                                                title="پیش نمایش"
                                                            >
                                                                <Eye className="h-4 w-4" />
                                                            </Button>
                                                            {(!item.accounting_status || item.accounting_status === 'READY_TO_POST') && (
                                                                <Button
                                                                    size="sm"
                                                                    className="rounded-lg"
                                                                    onClick={() => handlePostClick(item)}
                                                                >
                                                                    ثبت
                                                                </Button>
                                                            )}
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>

                                <div className="space-y-3 p-4 lg:hidden">
                                    {items.map((item, index) => (
                                        <div
                                            key={item.id}
                                            className={cn(
                                                'rounded-xl border border-slate-200 bg-white p-4 shadow-sm',
                                                focusedIndex === index && 'border-blue-300 bg-blue-50/60',
                                                selectedIds.has(item.id) && 'ring-2 ring-blue-200'
                                            )}
                                            onClick={() => setFocusedIndex(index)}
                                        >
                                            <div className="flex items-start justify-between gap-3">
                                                <div className="min-w-0 space-y-1">
                                                    <p className="font-mono-num text-xs font-bold text-blue-700">{item.unique_code}</p>
                                                    <h3 className="truncate font-bold text-slate-950">{item.beneficiary_name}</h3>
                                                    <p className="text-xs text-muted-foreground">{item.zone_title} · {formatDate(item.approved_at)}</p>
                                                </div>
                                                <input
                                                    type="checkbox"
                                                    checked={selectedIds.has(item.id)}
                                                    onChange={() => toggleSelection(item.id)}
                                                    aria-label={`انتخاب ${item.unique_code}`}
                                                    className="mt-1 h-4 w-4 rounded border-slate-300 accent-blue-700"
                                                />
                                            </div>
                                            <div className="mt-4 flex flex-wrap items-center gap-2">
                                                <StatusBadge status={item.accounting_status} />
                                                <ValidationBadge status={item.validation_status} />
                                            </div>
                                            <div className="mt-4 rounded-lg bg-slate-50 p-3">
                                                <p className="text-xs text-muted-foreground">مبلغ</p>
                                                <p className="font-mono-num mt-1 text-lg font-black text-slate-950">{formatRial(item.amount)}</p>
                                            </div>
                                            <div className="mt-4 flex items-center gap-2">
                                                <Button
                                                    variant="outline"
                                                    className="flex-1 rounded-lg bg-white"
                                                    onClick={() => openPreview(item.id)}
                                                >
                                                    <Eye className="h-4 w-4" />
                                                    پیش نمایش
                                                </Button>
                                                {(!item.accounting_status || item.accounting_status === 'READY_TO_POST') && (
                                                    <Button
                                                        className="flex-1 rounded-lg"
                                                        onClick={() => handlePostClick(item)}
                                                    >
                                                        ثبت سند
                                                    </Button>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600 shadow-sm md:flex-row md:items-center md:justify-between">
                        <span>
                            نمایش {rangeStart.toLocaleString('fa-IR')} تا {rangeEnd.toLocaleString('fa-IR')} از {total.toLocaleString('fa-IR')}
                        </span>
                        <div className="flex items-center gap-2">
                            <Button
                                variant="outline"
                                className="rounded-lg bg-white"
                                onClick={() => setFilters(f => ({ ...f, offset: Math.max(0, (f.offset || 0) - (f.limit || 50)) }))}
                                disabled={(filters.offset || 0) === 0}
                            >
                                <ChevronRight className="h-4 w-4" />
                                قبلی
                            </Button>
                            <Button
                                variant="outline"
                                className="rounded-lg bg-white"
                                onClick={() => setFilters(f => ({ ...f, offset: (f.offset || 0) + (f.limit || 50) }))}
                                disabled={(filters.offset || 0) + (filters.limit || 50) >= total}
                            >
                                بعدی
                                <ChevronLeft className="h-4 w-4" />
                            </Button>
                        </div>
                    </div>
                </>
            )}

            {previewId !== null && (
                <div className="fixed inset-0 z-50 flex justify-start bg-slate-950/40 backdrop-blur-sm" onClick={closePreview}>
                    <div
                        ref={drawerRef}
                        className="flex h-full w-full max-w-2xl flex-col overflow-hidden bg-white shadow-2xl"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="drawer-title"
                        onClick={e => e.stopPropagation()}
                    >
                        <header className="flex items-start justify-between gap-4 border-b border-slate-200 p-5">
                            <div className="space-y-1">
                                <h2 id="drawer-title" className="text-lg font-bold text-slate-950">پیش نمایش ثبت حسابداری</h2>
                                <p className="text-sm text-muted-foreground">خطوط سند، وضعیت توازن و هشدارهای اعتبارسنجی</p>
                            </div>
                            <Button variant="ghost" size="icon" className="rounded-lg" onClick={closePreview} aria-label="بستن">
                                <X className="h-4 w-4" />
                            </Button>
                        </header>

                        <div className="flex-1 overflow-y-auto p-5">
                            {previewLoading && (
                                <div className="space-y-4">
                                    <Skeleton className="h-28 rounded-xl" />
                                    <Skeleton className="h-72 rounded-xl" />
                                </div>
                            )}

                            {!previewLoading && !preview && (
                                <div className="flex min-h-[260px] flex-col items-center justify-center gap-3 text-center text-muted-foreground">
                                    <AlertCircle className="h-10 w-10 text-amber-600" />
                                    <p>پیش نمایش سند در دسترس نیست.</p>
                                </div>
                            )}

                            {preview && (
                                <div className="space-y-5">
                                    <div className="grid gap-3 sm:grid-cols-2">
                                        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                                            <p className="text-xs text-muted-foreground">شناسه تراکنش</p>
                                            <p className="font-mono-num mt-1 font-black text-slate-950">{preview.unique_code}</p>
                                        </div>
                                        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                                            <p className="text-xs text-muted-foreground">نسخه snapshot</p>
                                            <p className="mt-1 font-bold text-slate-950">{preview.snapshot_version.toLocaleString('fa-IR')}</p>
                                        </div>
                                        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                                            <p className="text-xs text-muted-foreground">قسمت</p>
                                            <p className="mt-1 font-bold text-slate-950">{preview.section_name || 'نامشخص'}</p>
                                        </div>
                                        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                                            <p className="text-xs text-muted-foreground">سامانه</p>
                                            <p className="mt-1 font-bold text-slate-950">{preview.subsystem_name || 'نامشخص'}</p>
                                        </div>
                                    </div>

                                    {(preview.validation_errors.length > 0 || preview.warnings.length > 0) && (
                                        <div className="space-y-3">
                                            {preview.validation_errors.length > 0 && (
                                                <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
                                                    <p className="mb-2 font-bold">خطاهای اعتبارسنجی</p>
                                                    <ul className="list-inside list-disc space-y-1">
                                                        {preview.validation_errors.map((item, index) => (
                                                            <li key={`${item}-${index}`}>{item}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                            {preview.warnings.length > 0 && (
                                                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                                                    <p className="mb-2 font-bold">هشدارها</p>
                                                    <ul className="list-inside list-disc space-y-1">
                                                        {preview.warnings.map((item, index) => (
                                                            <li key={`${item}-${index}`}>{item}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    <div className="overflow-x-auto rounded-xl border border-slate-200">
                                        <table className="w-full min-w-[680px] text-sm">
                                            <thead className="bg-slate-50 text-slate-500">
                                                <tr>
                                                    <th className="px-4 py-3 text-right font-semibold">#</th>
                                                    <th className="px-4 py-3 text-right font-semibold">کد حساب</th>
                                                    <th className="px-4 py-3 text-right font-semibold">نام حساب</th>
                                                    <th className="px-4 py-3 text-right font-semibold">بدهکار</th>
                                                    <th className="px-4 py-3 text-right font-semibold">بستانکار</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-slate-100">
                                                {preview.lines.map(line => (
                                                    <tr key={line.sequence} className="hover:bg-slate-50">
                                                        <td className="px-4 py-3 text-slate-500">{line.sequence.toLocaleString('fa-IR')}</td>
                                                        <td className="font-mono-num px-4 py-3 text-slate-700">{line.account_code}</td>
                                                        <td className="px-4 py-3 font-semibold text-slate-900">{line.account_name}</td>
                                                        <td className="font-mono-num px-4 py-3 font-bold text-slate-950">
                                                            {line.debit_amount > 0 ? formatRial(line.debit_amount) : '---'}
                                                        </td>
                                                        <td className="font-mono-num px-4 py-3 font-bold text-slate-950">
                                                            {line.credit_amount > 0 ? formatRial(line.credit_amount) : '---'}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                            <tfoot className="border-t border-slate-200 bg-slate-50">
                                                <tr>
                                                    <td colSpan={3} className="px-4 py-4 font-bold text-slate-950">جمع</td>
                                                    <td className="font-mono-num px-4 py-4 font-black text-slate-950">{formatRial(preview.total_debit)}</td>
                                                    <td className="font-mono-num px-4 py-4 font-black text-slate-950">{formatRial(preview.total_credit)}</td>
                                                </tr>
                                            </tfoot>
                                        </table>
                                    </div>

                                    <div className={cn(
                                        'flex items-center justify-between gap-3 rounded-xl border p-4',
                                        preview.is_balanced ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-red-200 bg-red-50 text-red-800'
                                    )}>
                                        <div className="flex items-center gap-2 font-bold">
                                            {preview.is_balanced ? <CheckCircle2 className="h-5 w-5" /> : <AlertCircle className="h-5 w-5" />}
                                            {preview.is_balanced ? 'سند تراز است' : 'سند تراز نیست'}
                                        </div>
                                        <ValidationBadge status={preview.validation_status} />
                                    </div>
                                </div>
                            )}
                        </div>

                        {preview && (preview.validation_status === 'VALID' || preview.validation_status === 'WARNING') && (() => {
                            const item = items.find(i => i.id === previewId);
                            const canPost = item && (!item.accounting_status || item.accounting_status === 'READY_TO_POST');
                            return canPost ? (
                                <footer className="border-t border-slate-200 bg-slate-50 p-5">
                                    <Button
                                        className="w-full rounded-lg"
                                        onClick={() => item && handlePostClick(item)}
                                        disabled={posting}
                                    >
                                        {posting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                                        ثبت سند
                                    </Button>
                                </footer>
                            ) : null;
                        })()}
                    </div>
                </div>
            )}

            {postingItem && (
                <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-sm">
                    <div className="w-full max-w-lg overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="posting-title">
                        <header className="flex items-start justify-between gap-4 border-b border-slate-200 p-5">
                            <div>
                                <h2 id="posting-title" className="text-lg font-bold text-slate-950">تایید ثبت سند</h2>
                                <p className="mt-1 text-sm text-muted-foreground">شماره مرجع ثبت را قبل از ارسال نهایی کنترل کنید.</p>
                            </div>
                            <Button variant="ghost" size="icon" className="rounded-lg" onClick={() => setPostingItem(null)} aria-label="بستن" disabled={posting}>
                                <X className="h-4 w-4" />
                            </Button>
                        </header>

                        <div className="space-y-5 p-5">
                            <div className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-2">
                                <div>
                                    <p className="text-xs text-muted-foreground">شناسه</p>
                                    <p className="font-mono-num mt-1 font-black text-slate-950">{postingItem.unique_code}</p>
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground">مبلغ</p>
                                    <p className="font-mono-num mt-1 font-black text-slate-950">{formatRial(postingItem.amount)}</p>
                                </div>
                                <div className="sm:col-span-2">
                                    <p className="text-xs text-muted-foreground">ذینفع</p>
                                    <p className="mt-1 font-bold text-slate-950">{postingItem.beneficiary_name}</p>
                                </div>
                            </div>

                            <label className="block space-y-2">
                                <span className="text-sm font-semibold text-slate-700">شماره مرجع ثبت</span>
                                <Input
                                    type="text"
                                    value={postingRef}
                                    onChange={e => setPostingRef(e.target.value)}
                                    placeholder="GL-2026-0001"
                                    required
                                    aria-invalid={postingRefInvalid}
                                    className={cn(
                                        'h-10 rounded-lg bg-white text-right',
                                        postingRefInvalid && 'border-red-400 focus-visible:border-red-500 focus-visible:ring-red-100'
                                    )}
                                />
                                {postingRefInvalid ? (
                                    <p className="flex items-center gap-1.5 text-xs text-red-600">
                                        <AlertCircle className="h-3.5 w-3.5" />
                                        وارد کردن شماره مرجع الزامی است.
                                    </p>
                                ) : (
                                    <p className="text-xs leading-6 text-muted-foreground">
                                        این شماره برای تطبیق سند در سیستم مالی استفاده می شود.
                                    </p>
                                )}
                            </label>

                            <label className="block space-y-2">
                                <span className="text-sm font-semibold text-slate-700">یادداشت اختیاری</span>
                                <textarea
                                    value={postingNotes}
                                    onChange={e => setPostingNotes(e.target.value)}
                                    placeholder="توضیحات تکمیلی برای ثبت سند"
                                    className="min-h-24 w-full resize-y rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm leading-7 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                                />
                            </label>
                        </div>

                        <footer className="flex flex-col-reverse gap-2 border-t border-slate-200 bg-slate-50 p-5 sm:flex-row sm:justify-end">
                            <Button variant="outline" className="rounded-lg bg-white" onClick={() => setPostingItem(null)} disabled={posting}>
                                انصراف
                            </Button>
                            <Button
                                onClick={confirmPost}
                                disabled={!postingRef.trim() || posting}
                                className="rounded-lg"
                            >
                                {posting ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                                ثبت کردن
                            </Button>
                        </footer>
                    </div>
                </div>
            )}

            {batchDialogOpen && (
                <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-sm">
                    <div className="w-full max-w-lg overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="batch-title">
                        <header className="flex items-start justify-between gap-4 border-b border-slate-200 p-5">
                            <div>
                                <h2 id="batch-title" className="text-lg font-bold text-slate-950">ثبت دسته ای اسناد</h2>
                                <p className="mt-1 text-sm text-muted-foreground">
                                    برای {selectedIds.size.toLocaleString('fa-IR')} سند انتخاب شده شماره مرجع تولید می شود.
                                </p>
                            </div>
                            <Button variant="ghost" size="icon" className="rounded-lg" onClick={() => setBatchDialogOpen(false)} aria-label="بستن" disabled={posting}>
                                <X className="h-4 w-4" />
                            </Button>
                        </header>
                        <div className="space-y-4 p-5">
                            <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
                                <p className="text-sm font-semibold text-blue-900">جمع مبلغ انتخاب شده</p>
                                <p className="font-mono-num mt-1 text-xl font-black text-blue-950">{formatRial(selectedAmount)}</p>
                            </div>
                            <label className="block space-y-2">
                                <span className="text-sm font-semibold text-slate-700">پیشوند شماره مرجع</span>
                                <Input
                                    value={batchPrefix}
                                    onChange={e => setBatchPrefix(e.target.value)}
                                    placeholder="GL-"
                                    className="h-10 rounded-lg bg-white text-right"
                                    aria-invalid={batchPrefix.trim().length === 0}
                                />
                                <p className="text-xs leading-6 text-muted-foreground">
                                    نمونه خروجی: {batchPrefix || 'GL-'}0001، {batchPrefix || 'GL-'}0002
                                </p>
                            </label>
                        </div>
                        <footer className="flex flex-col-reverse gap-2 border-t border-slate-200 bg-slate-50 p-5 sm:flex-row sm:justify-end">
                            <Button variant="outline" className="rounded-lg bg-white" onClick={() => setBatchDialogOpen(false)} disabled={posting}>
                                انصراف
                            </Button>
                            <Button onClick={handleBatchPost} disabled={posting || batchPrefix.trim().length === 0} className="rounded-lg">
                                {posting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                                ثبت دسته ای
                            </Button>
                        </footer>
                    </div>
                </div>
            )}

            {batchResults && (
                <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-sm">
                    <div className="w-full max-w-lg overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="batch-results-title">
                        <header className="border-b border-slate-200 p-5">
                            <h2 id="batch-results-title" className="text-lg font-bold text-slate-950">نتیجه ثبت دسته ای</h2>
                            <p className="mt-1 text-sm text-muted-foreground">خلاصه عملیات ثبت اسناد انتخاب شده</p>
                        </header>

                        <div className="space-y-5 p-5">
                            <div className="grid grid-cols-2 gap-3">
                                <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center">
                                    <p className="text-sm text-emerald-700">موفق</p>
                                    <p className="mt-1 text-2xl font-black text-emerald-900">{batchResults.succeeded.toLocaleString('fa-IR')}</p>
                                </div>
                                <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-center">
                                    <p className="text-sm text-red-700">ناموفق</p>
                                    <p className="mt-1 text-2xl font-black text-red-900">{batchResults.failed.toLocaleString('fa-IR')}</p>
                                </div>
                            </div>

                            {batchResults.failed > 0 && (
                                <div className="max-h-56 overflow-y-auto rounded-xl border border-red-200 bg-red-50 p-4">
                                    <h4 className="font-bold text-red-950">خطاها</h4>
                                    <ul className="mt-3 space-y-2 text-sm text-red-800">
                                        {batchResults.results
                                            .filter(r => !r.success)
                                            .map(r => (
                                                <li key={r.transaction_id}>
                                                    <span className="font-mono-num font-bold">{r.display_id}</span>: {r.error_message || r.error}
                                                </li>
                                            ))}
                                    </ul>
                                </div>
                            )}
                        </div>

                        <footer className="flex justify-end border-t border-slate-200 bg-slate-50 p-5">
                            <Button onClick={() => setBatchResults(null)} className="rounded-lg">
                                بستن
                            </Button>
                        </footer>
                    </div>
                </div>
            )}

            <div role="status" aria-live="polite" className="sr-only">
                {posting && 'در حال ثبت...'}
                {exporting && 'در حال آماده سازی خروجی...'}
            </div>
        </div>
    );
}

export default AccountingInboxPage;
