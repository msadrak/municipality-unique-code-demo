// Base API client with credentials support

const API_BASE_URL = '';  // Same origin, use relative URLs

interface RequestOptions extends RequestInit {
    params?: Record<string, string | number | undefined>;
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

    const response = await fetch(url, {
        ...init,
        credentials: 'include',  // Important for session cookies
        headers: {
            'Content-Type': 'application/json',
            ...init.headers,
        },
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'خطای سرور' }));
        throw new Error(error.detail || `HTTP error ${response.status}`);
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

    put: <T>(endpoint: string, data?: unknown) =>
        request<T>(endpoint, {
            method: 'PUT',
            body: data ? JSON.stringify(data) : undefined,
        }),

    delete: <T>(endpoint: string) =>
        request<T>(endpoint, { method: 'DELETE' }),
};

export default api;
