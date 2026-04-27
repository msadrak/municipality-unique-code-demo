// Base API client with credentials support
import { readStoredAccessToken } from '../lib/auth-storage';

const API_BASE_URL = '';  // Same origin, use relative URLs

// Custom error class for 403 Forbidden responses
export class ForbiddenError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'ForbiddenError';
    }
}

interface RequestOptions extends RequestInit {
    params?: Record<string, string | number | undefined>;
}

function formatValidationMessage(detail: unknown): string | null {
    if (typeof detail === 'string') {
        return detail;
    }

    if (Array.isArray(detail)) {
        const fieldLabels: Record<string, string> = {
            letter_date: 'تاریخ نامه',
            receiver_title: 'گیرنده',
            sender_title: 'فرستنده',
            subject: 'موضوع',
            body_text: 'متن نامه',
            cc_list: 'رونوشت',
            attachment_count: 'تعداد پیوست',
            amount: 'مبلغ',
            request_type: 'نوع درخواست',
            action: 'عملیات',
            comment: 'توضیح',
        };

        const messages = detail
            .map((item) => {
                if (!item || typeof item !== 'object') return null;
                const candidate = item as Record<string, unknown>;
                const rawLoc = Array.isArray(candidate.loc) ? candidate.loc : [];
                const fieldKey = rawLoc.find(
                    (part) => typeof part === 'string' && part !== 'body',
                ) as string | undefined;
                const fieldLabel = fieldKey ? fieldLabels[fieldKey] || fieldKey : null;
                const rawMessage = candidate.msg || candidate.message || candidate.type;
                if (!rawMessage) return null;
                return fieldLabel ? `${fieldLabel}: ${String(rawMessage)}` : String(rawMessage);
            })
            .filter(Boolean);

        return messages.length ? messages.join(' | ') : null;
    }

    if (detail && typeof detail === 'object') {
        const candidate = detail as Record<string, unknown>;
        if (typeof candidate.detail === 'string') {
            return candidate.detail;
        }
        try {
            return JSON.stringify(candidate);
        } catch {
            return null;
        }
    }

    return null;
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { params, ...init } = options;

    // Build URL with query params
    let url = `${API_BASE_URL}${endpoint}`;
    if (params) {
        const searchParams = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined) {
                searchParams.append(key, String(value));
            }
        });
        const queryString = searchParams.toString();
        if (queryString) {
            url += `?${queryString}`;
        }
    }

    const isFormData = typeof FormData !== 'undefined' && init.body instanceof FormData;
    const headers = new Headers(init.headers ?? {});
    if (!isFormData && !headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json');
    }

    const accessToken = readStoredAccessToken();
    if (accessToken && !headers.has('Authorization')) {
        headers.set('Authorization', `Bearer ${accessToken}`);
    }

    const response = await fetch(url, {
        ...init,
        headers,
    });

    if (!response.ok) {
        // Handle 401 Unauthorized - session expired
        if (response.status === 401) {
            // Clear auth state and redirect to login
            // Import dynamically to avoid circular dependency
            const { useAuthStore } = await import('../stores/useAuthStore');
            useAuthStore.getState().logout();
            window.location.href = '/login';
            throw new Error('جلسه شما منقضی شده است. لطفا مجددا وارد شوید.');
        }

        // Handle 403 Forbidden
        if (response.status === 403) {
            const error = await response.json().catch(() => ({ detail: 'دسترسی غیرمجاز' }));
            throw new ForbiddenError(
                formatValidationMessage(error.detail) || 'شما دسترسی به این بخش را ندارید',
            );
        }

        const error = await response.json().catch(() => ({ detail: 'خطای سرور' }));
        throw new Error(
            formatValidationMessage(error.detail) ||
            formatValidationMessage(error) ||
            `HTTP error ${response.status}`,
        );
    }

    // Handle empty responses
    const text = await response.text();
    if (!text) return {} as T;

    return JSON.parse(text);
}

export const api = {
    get: <T>(endpoint: string, params?: Record<string, string | number | undefined>) =>
        request<T>(endpoint, { method: 'GET', params }),

    post: <T>(endpoint: string, data?: unknown) =>
        request<T>(endpoint, {
            method: 'POST',
            body: data ? JSON.stringify(data) : undefined,
        }),

    postForm: <T>(endpoint: string, data: FormData) =>
        request<T>(endpoint, {
            method: 'POST',
            body: data,
        }),

    put: <T>(endpoint: string, data?: unknown) =>
        request<T>(endpoint, {
            method: 'PUT',
            body: data ? JSON.stringify(data) : undefined,
        }),

    patch: <T>(endpoint: string, data?: unknown, params?: Record<string, string | number | undefined>) =>
        request<T>(endpoint, {
            method: 'PATCH',
            params,
            body: data ? JSON.stringify(data) : undefined,
        }),

    delete: <T>(endpoint: string) =>
        request<T>(endpoint, { method: 'DELETE' }),
};

export default api;
