/**
 * Accounting Inbox Page
 * 
 * Main page component for accounting staff to view and post transactions.
 * Based on frontend_architecture.md v2 design.
 */
import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
    InboxItem, InboxFilters, JournalPreview,
    PostRequest, BatchPostRequest, BatchPostResponse, AccountingStatus
} from '../../types/accounting';
import {
    fetchAccountingInbox, fetchJournalPreview,
    postTransaction, batchPostTransactions, exportTransactions
} from '../../services/accounting';
import { formatRial } from '../../lib/utils';

// ============ CONSTANTS ============
const STATUS_OPTIONS = [
    { value: 'ALL', label: 'همه' },
    { value: 'READY_TO_POST', label: 'آماده ثبت' },
    { value: 'POSTED', label: 'ثبت شده' },
    { value: 'POST_ERROR', label: 'خطا' },
];

const STATUS_BADGE_CLASSES: Record<string, string> = {
    READY_TO_POST: 'badge-ready',
    POSTED: 'badge-posted',
    POST_ERROR: 'badge-error',
};

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

    // Batch results
    const [batchResults, setBatchResults] = useState<BatchPostResponse | null>(null);

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
            setError(err instanceof Error ? err.message : 'خطا در بارگذاری');
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
        setPreviewLoading(true);
        try {
            const data = await fetchJournalPreview(id);
            setPreview(data);
        } catch (err) {
            console.error('Preview error:', err);
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

        setPosting(true);
        try {
            const request: PostRequest = {
                posting_ref: postingRef,
                notes: postingNotes || undefined,
                version: postingItem.version,
            };

            await postTransaction(postingItem.id, request);

            // Refetch inbox
            await loadInbox();

            // Close modal
            setPostingItem(null);

        } catch (err: any) {
            if (err?.error === 'VERSION_MISMATCH') {
                alert('این تراکنش توسط کاربر دیگری تغییر کرده. صفحه را رفرش کنید.');
                await loadInbox();
            } else if (err?.error === 'CONFLICT') {
                alert(`قبلاً با شماره ${err.existing_ref} ثبت شده`);
            } else {
                alert(err?.message || 'خطا در ثبت');
            }
        } finally {
            setPosting(false);
        }
    }, [postingItem, postingRef, postingNotes, loadInbox]);

    // ============ BATCH POST ============
    const handleBatchPost = useCallback(async () => {
        const selectedItems = items.filter(item => selectedIds.has(item.id));
        if (selectedItems.length === 0) return;

        const prefix = prompt('پیشوند شماره مرجع را وارد کنید:', 'GL-');
        if (!prefix) return;

        const request: BatchPostRequest = {
            items: selectedItems.map((item, index) => ({
                transaction_id: item.id,
                posting_ref: `${prefix}${String(index + 1).padStart(4, '0')}`,
                version: item.version,
            })),
        };

        setPosting(true);
        try {
            const response = await batchPostTransactions(request);
            setBatchResults(response);
            setSelectedIds(new Set());
            await loadInbox();
        } catch (err) {
            alert('خطا در ثبت دسته‌ای');
        } finally {
            setPosting(false);
        }
    }, [items, selectedIds, loadInbox]);

    // ============ EXPORT ============
    const handleExport = useCallback(async () => {
        const ids = selectedIds.size > 0
            ? Array.from(selectedIds)
            : items.map(i => i.id);

        try {
            await exportTransactions({
                transaction_ids: ids,
                format: 'csv',
                include_journal_lines: true,
            });
        } catch (err) {
            alert('خطا در خروجی');
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

    // ============ RENDER ============
    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '-';
        return new Date(dateStr).toLocaleDateString('fa-IR');
    };

    return (
        <div className="accounting-inbox-page" dir="rtl">
            {/* Header */}
            <header className="inbox-header">
                <h1>صندوق حسابداری</h1>
                <button
                    onClick={loadInbox}
                    disabled={loading}
                    className="btn-refresh"
                    aria-label="بارگذاری مجدد"
                >
                    {loading ? '...' : '🔄'} بارگذاری مجدد
                </button>
            </header>

            {/* Filters */}
            <div className="filters-bar">
                <select
                    value={filters.status || 'ALL'}
                    onChange={e => setFilters(f => ({
                        ...f,
                        status: e.target.value as AccountingStatus | 'ALL',
                        offset: 0
                    }))}
                >
                    {STATUS_OPTIONS.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                </select>

                <input
                    type="text"
                    placeholder="جستجو..."
                    value={searchInput}
                    onChange={e => setSearchInput(e.target.value)}
                    className="search-input"
                />
            </div>

            {/* Batch Action Toolbar */}
            {selectedIds.size > 0 && (
                <div className="batch-toolbar">
                    <span>{selectedIds.size} مورد انتخاب شده</span>
                    <button onClick={handleBatchPost} disabled={posting}>
                        ثبت دسته‌ای
                    </button>
                    <button onClick={handleExport}>
                        خروجی
                    </button>
                    <button onClick={() => setSelectedIds(new Set())}>
                        لغو انتخاب
                    </button>
                </div>
            )}

            {/* Error State */}
            {error && (
                <div className="error-state">
                    <p>{error}</p>
                    <button onClick={loadInbox}>تلاش مجدد</button>
                </div>
            )}

            {/* Loading State */}
            {loading && items.length === 0 && (
                <div className="loading-state">در حال بارگذاری...</div>
            )}

            {/* Empty State */}
            {!loading && items.length === 0 && !error && (
                <div className="empty-state">
                    <p>هیچ تراکنشی یافت نشد</p>
                </div>
            )}

            {/* Table */}
            {items.length > 0 && (
                <table
                    ref={tableRef}
                    role="grid"
                    className="inbox-table"
                    tabIndex={0}
                    onKeyDown={handleKeyDown}
                >
                    <thead>
                        <tr>
                            <th>
                                <input
                                    type="checkbox"
                                    checked={selectedIds.size === items.length}
                                    onChange={toggleSelectAll}
                                    aria-label="انتخاب همه"
                                />
                            </th>
                            <th>شناسه</th>
                            <th>تاریخ تایید</th>
                            <th>ذینفع</th>
                            <th>مبلغ</th>
                            <th>منطقه</th>
                            <th>وضعیت</th>
                            <th>عملیات</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items.map((item, index) => (
                            <tr
                                key={item.id}
                                className={`
                  ${focusedIndex === index ? 'focused' : ''}
                  ${selectedIds.has(item.id) ? 'selected' : ''}
                `}
                                onClick={() => setFocusedIndex(index)}
                                onDoubleClick={() => openPreview(item.id)}
                            >
                                <td>
                                    <input
                                        type="checkbox"
                                        checked={selectedIds.has(item.id)}
                                        onChange={() => toggleSelection(item.id)}
                                        aria-label={`انتخاب ${item.unique_code}`}
                                    />
                                </td>
                                <td>{item.unique_code}</td>
                                <td>{formatDate(item.approved_at)}</td>
                                <td>{item.beneficiary_name}</td>
                                <td className="amount">{formatRial(item.amount)}</td>
                                <td>{item.zone_title}</td>
                                <td>
                                    <span className={`badge ${STATUS_BADGE_CLASSES[item.accounting_status || 'READY_TO_POST']}`}>
                                        {STATUS_OPTIONS.find(o => o.value === (item.accounting_status || 'READY_TO_POST'))?.label}
                                    </span>
                                </td>
                                <td className="actions">
                                    <button onClick={() => openPreview(item.id)} title="پیش‌نمایش">
                                        👁
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}

            {/* Pagination */}
            <div className="pagination">
                <span>نمایش {(filters.offset || 0) + 1} تا {Math.min((filters.offset || 0) + (filters.limit || 50), total)} از {total}</span>
                <button
                    onClick={() => setFilters(f => ({ ...f, offset: Math.max(0, (f.offset || 0) - (f.limit || 50)) }))}
                    disabled={(filters.offset || 0) === 0}
                >
                    قبلی
                </button>
                <button
                    onClick={() => setFilters(f => ({ ...f, offset: (f.offset || 0) + (f.limit || 50) }))}
                    disabled={(filters.offset || 0) + (filters.limit || 50) >= total}
                >
                    بعدی
                </button>
            </div>

            {/* Preview Drawer */}
            {previewId !== null && (
                <div className="preview-drawer-overlay" onClick={closePreview}>
                    <div
                        ref={drawerRef}
                        className="preview-drawer"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="drawer-title"
                        onClick={e => e.stopPropagation()}
                    >
                        <header>
                            <h2 id="drawer-title">پیش‌نمایش ثبت حسابداری</h2>
                            <button onClick={closePreview} aria-label="بستن">✕</button>
                        </header>

                        {previewLoading && <div className="loading">در حال بارگذاری...</div>}

                        {preview && (
                            <div className="preview-content">
                                <div className="preview-header">
                                    <p><strong>شناسه:</strong> {preview.unique_code}</p>
                                    <p><strong>نسخه:</strong> {preview.snapshot_version}</p>
                                    <p><strong>وضعیت:</strong> {preview.validation_status}</p>
                                    <p><strong>قسمت:</strong> {preview.section_name || 'نامشخص'}</p>
                                    <p><strong>سامانه:</strong> {preview.subsystem_name || 'نامشخص'}</p>
                                </div>

                                <table className="journal-lines-table">
                                    <thead>
                                        <tr>
                                            <th>#</th>
                                            <th>کد حساب</th>
                                            <th>نام حساب</th>
                                            <th>بدهکار</th>
                                            <th>بستانکار</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {preview.lines.map(line => (
                                            <tr key={line.sequence}>
                                                <td>{line.sequence}</td>
                                                <td>{line.account_code}</td>
                                                <td>{line.account_name}</td>
                                                <td className="amount">{line.debit_amount > 0 ? formatRial(line.debit_amount) : '-'}</td>
                                                <td className="amount">{line.credit_amount > 0 ? formatRial(line.credit_amount) : '-'}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                    <tfoot>
                                        <tr>
                                            <td colSpan={3}><strong>جمع</strong></td>
                                            <td className="amount">{formatRial(preview.total_debit)}</td>
                                            <td className="amount">{formatRial(preview.total_credit)}</td>
                                        </tr>
                                    </tfoot>
                                </table>

                                <div className="balance-check">
                                    {preview.is_balanced ? (
                                        <span className="balanced">✓ توازن</span>
                                    ) : (
                                        <span className="unbalanced">✗ عدم توازن</span>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Drawer Footer with Post Button */}
                        {preview && (preview.validation_status === 'VALID' || preview.validation_status === 'WARNING') && (() => {
                            const item = items.find(i => i.id === previewId);
                            const canPost = item && (!item.accounting_status || item.accounting_status === 'READY_TO_POST');
                            return canPost ? (
                                <footer className="drawer-footer">
                                    <button
                                        className="btn-post-from-drawer"
                                        onClick={() => item && handlePostClick(item)}
                                    >
                                        ثبت سند
                                    </button>
                                </footer>
                            ) : null;
                        })()}
                    </div>
                </div>
            )}

            {/* Posting Modal */}
            {postingItem && (
                <div className="modal-overlay">
                    <div className="posting-modal" role="dialog" aria-modal="true">
                        <header>
                            <h2>تایید ثبت سند</h2>
                            <button onClick={() => setPostingItem(null)} aria-label="بستن">✕</button>
                        </header>

                        <div className="modal-content">
                            <p><strong>شناسه:</strong> {postingItem.unique_code}</p>
                            <p><strong>ذینفع:</strong> {postingItem.beneficiary_name}</p>
                            <p><strong>مبلغ:</strong> {formatRial(postingItem.amount)}</p>

                            <label>
                                شماره مرجع ثبت:
                                <input
                                    type="text"
                                    value={postingRef}
                                    onChange={e => setPostingRef(e.target.value)}
                                    placeholder="GL-2024-0001"
                                    required
                                />
                            </label>

                            <label>
                                یادداشت (اختیاری):
                                <textarea
                                    value={postingNotes}
                                    onChange={e => setPostingNotes(e.target.value)}
                                    placeholder="توضیحات..."
                                />
                            </label>
                        </div>

                        <footer>
                            <button onClick={() => setPostingItem(null)}>انصراف</button>
                            <button
                                onClick={confirmPost}
                                disabled={!postingRef || posting}
                                className="btn-primary"
                            >
                                {posting ? 'در حال ثبت...' : 'ثبت کردن'}
                            </button>
                        </footer>
                    </div>
                </div>
            )}

            {/* Batch Results Modal */}
            {batchResults && (
                <div className="modal-overlay">
                    <div className="batch-results-modal" role="dialog" aria-modal="true">
                        <header>
                            <h2>نتیجه ثبت دسته‌ای</h2>
                        </header>

                        <div className="modal-content">
                            <div className="summary">
                                <span className="success">✅ {batchResults.succeeded} موفق</span>
                                <span className="failed">❌ {batchResults.failed} ناموفق</span>
                            </div>

                            {batchResults.failed > 0 && (
                                <div className="failure-list">
                                    <h4>خطاها:</h4>
                                    <ul>
                                        {batchResults.results
                                            .filter(r => !r.success)
                                            .map(r => (
                                                <li key={r.transaction_id}>
                                                    {r.display_id}: {r.error_message || r.error}
                                                </li>
                                            ))}
                                    </ul>
                                </div>
                            )}
                        </div>

                        <footer>
                            <button onClick={() => setBatchResults(null)} className="btn-primary">
                                بستن
                            </button>
                        </footer>
                    </div>
                </div>
            )}

            {/* Keyboard Help (hidden, for screen readers) */}
            <div role="status" aria-live="polite" className="sr-only">
                {posting && 'در حال ثبت...'}
            </div>
        </div>
    );
}

export default AccountingInboxPage;
