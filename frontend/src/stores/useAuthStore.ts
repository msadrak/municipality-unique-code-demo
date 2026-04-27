import { create } from 'zustand';

import { clearAuthSession, persistAuthSession, readStoredAccessToken, readStoredUser } from '../lib/auth-storage';
import { authService } from '../services/auth';
import type { User } from '../types';

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  restoreSession: () => Promise<void>;
  clearError: () => void;
}

function clearLocalState(set: (partial: Partial<AuthState>) => void) {
  clearAuthSession();
  set({
    token: null,
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
  });
}

export const useAuthStore = create<AuthState>((set) => ({
  token: readStoredAccessToken(),
  user: readStoredUser(),
  isAuthenticated: Boolean(readStoredAccessToken() && readStoredUser()),
  isLoading: true,
  error: null,

  login: async (username: string, password: string) => {
    set({ isLoading: true, error: null });

    try {
      const response = await authService.login({ username, password });
      persistAuthSession(response.access_token, response.user);
      set({
        token: response.access_token,
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
      return true;
    } catch (error) {
      clearLocalState(set);
      set({
        error: error instanceof Error ? error.message : 'خطا در ورود',
      });
      return false;
    }
  },

  logout: async () => {
    clearLocalState(set);
    await authService.logout();
  },

  restoreSession: async () => {
    const storedToken = readStoredAccessToken();
    const storedUser = readStoredUser();

    if (!storedToken || !storedUser) {
      clearLocalState(set);
      return;
    }

    set({
      token: storedToken,
      user: storedUser,
      isAuthenticated: true,
      isLoading: true,
      error: null,
    });

    try {
      const freshUser = await authService.getCurrentUser();
      persistAuthSession(storedToken, freshUser);
      set({
        token: storedToken,
        user: freshUser,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch {
      clearLocalState(set);
    }
  },

  clearError: () => set({ error: null }),
}));

export const selectUser = (state: AuthState) => state.user;
export const selectIsAuthenticated = (state: AuthState) => state.isAuthenticated;
export const selectIsLoading = (state: AuthState) => state.isLoading;

export default useAuthStore;
