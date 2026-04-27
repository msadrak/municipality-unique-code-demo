import { api } from './api';
import type { AuthResponse, LoginRequest, User } from '../types';

export const authService = {
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'خطا در ورود' }));
      throw new Error(error.detail || 'نام کاربری یا رمز عبور اشتباه است');
    }

    return response.json() as Promise<AuthResponse>;
  },

  async getCurrentUser(): Promise<User> {
    return api.get<User>('/api/auth/me');
  },

  async logout(): Promise<void> {
    try {
      await api.post('/api/auth/logout', {});
    } catch {
      // JWT logout is client-side; ignore server errors.
    }
  },
};

export default authService;
