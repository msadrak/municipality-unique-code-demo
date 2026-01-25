/**
 * API service for Accounting Posting module
 */
import {
    InboxFilters, InboxResponse, JournalPreview,
    PostRequest, PostResponse, PostError,
    BatchPostRequest, BatchPostResponse,
    ExportRequest
} from '../types/accounting';

const API_BASE = '/api';

/**
 * Fetch accounting inbox with filters
 */
export async function fetchAccountingInbox(filters: InboxFilters): Promise<InboxResponse> {
    const params = new URLSearchParams();

    if (filters.status) params.append('status', filters.status);
    if (filters.zone_id) params.append('zone_id', String(filters.zone_id));
    if (filters.date_from) params.append('date_from', filters.date_from);
    if (filters.date_to) params.append('date_to', filters.date_to);
    if (filters.search) params.append('search', filters.search);
    if (filters.limit) params.append('limit', String(filters.limit));
    if (filters.offset) params.append('offset', String(filters.offset));

    const response = await fetch(`${API_BASE}/accounting/inbox?${params}`, {
        credentials: 'include',
    });

    if (!response.ok) {
        throw new Error(`Failed to fetch inbox: ${response.statusText}`);
    }

    return response.json();
}

/**
 * Fetch journal preview for a transaction
 */
export async function fetchJournalPreview(transactionId: number): Promise<JournalPreview> {
    const response = await fetch(`${API_BASE}/accounting/tx/${transactionId}/journal-preview`, {
        credentials: 'include',
    });

    if (!response.ok) {
        throw new Error(`Failed to fetch journal preview: ${response.statusText}`);
    }

    return response.json();
}

/**
 * Post a single transaction (pessimistic mutation)
 */
export async function postTransaction(
    transactionId: number,
    request: PostRequest
): Promise<PostResponse> {
    const response = await fetch(`${API_BASE}/accounting/tx/${transactionId}/post`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(request),
    });

    if (!response.ok) {
        const error = await response.json();
        throw error as PostError;
    }

    return response.json();
}

/**
 * Batch post multiple transactions
 */
export async function batchPostTransactions(
    request: BatchPostRequest
): Promise<BatchPostResponse> {
    const response = await fetch(`${API_BASE}/accounting/batch-post`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(request),
    });

    if (!response.ok) {
        throw new Error(`Batch post failed: ${response.statusText}`);
    }

    return response.json();
}

/**
 * Export transactions (synchronous download)
 */
export async function exportTransactions(request: ExportRequest): Promise<void> {
    const response = await fetch(`${API_BASE}/accounting/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(request),
    });

    if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`);
    }

    // Download the file
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `accounting-export-${Date.now()}.${request.format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
