import React, { createContext, useContext, useMemo } from 'react';

import { useAuthStore } from '../stores/useAuthStore';

type AuthContextValue = {
  token: string | null;
  userRole: string | null;
  regionName: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  restoreSession: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((state) => state.token);
  const user = useAuthStore((state) => state.user);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isLoading = useAuthStore((state) => state.isLoading);
  const login = useAuthStore((state) => state.login);
  const logout = useAuthStore((state) => state.logout);
  const restoreSession = useAuthStore((state) => state.restoreSession);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      userRole: user?.role ?? null,
      regionName: user?.region_name ?? null,
      isAuthenticated,
      isLoading,
      login,
      logout,
      restoreSession,
    }),
    [token, user?.role, user?.region_name, isAuthenticated, isLoading, login, logout, restoreSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
