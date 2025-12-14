// Authentication service

import { api } from './api';
import type { User, AuthResponse, LoginRequest } from '../types';

interface LoginResponse {
    status: string;
    message: string;
    user: {
        id: number;
        username: string;
        full_name: string;
        role: 'user' | 'admin';
    };
}

export const authService = {
    /**
     * Login with username and password
     */
    async login(credentials: LoginRequest): Promise<User> {
        // FastAPI expects JSON, not form data
        const response = await fetch('/auth/login', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(credentials),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'خطا در ورود' }));
            throw new Error(error.detail || 'نام کاربری یا رمز عبور اشتباه است');
        }

        const data: LoginResponse = await response.json();

        // Extract user from response
        return {
            id: data.user.id,
            username: data.user.username,
            full_name: data.user.full_name,
            role: data.user.role,
        };
    },

    /**
     * Logout current user
     */
    async logout(): Promise<void> {
        await api.post('/auth/logout');
    },

    /**
     * Get current authenticated user
     */
    async getCurrentUser(): Promise<AuthResponse> {
        return api.get<AuthResponse>('/auth/me');
    },

    /**
     * Check if user is authenticated
     */
    async isAuthenticated(): Promise<boolean> {
        try {
            const response = await this.getCurrentUser();
            return response.authenticated;
        } catch {
            return false;
        }
    },

    /**
     * Register first admin user (only works if no users exist)
     */
    async registerAdmin(data: { full_name: string; username: string; password: string }): Promise<User> {
        return api.post<User>('/auth/register-admin', data);
    },

    /**
     * Check if this is first user (no users in system)
     */
    async checkFirstUser(): Promise<{ first_user: boolean }> {
        return api.get<{ first_user: boolean }>('/auth/check-first-user');
    },
};

export default authService;
