import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Login as LoginComponent } from '../components/Login';
import { RoleSelectionDialog } from '../components/auth/RoleSelectionDialog';
import { useAuthStore } from '../stores/useAuthStore';

const MANAGEMENT_HOME = '/admin';
const PORTAL_HOME = '/portal';

/** Roles that are allowed to see the workspace-selection dialog */
const ADMIN_ROLES = new Set([
  'ADMIN_L1', 'ADMIN_L2', 'ADMIN_L3', 'ADMIN_L4',
  'MANAGER', 'admin', 'ADMIN',
]);

const isHighLevelRole = (role?: string): boolean =>
  ADMIN_ROLES.has((role || '').trim()) ||
  ADMIN_ROLES.has((role || '').trim().toUpperCase());

/**
 * LoginPage - Wrapper for Login component that integrates with React Router.
 * Handles role-based navigation after successful login.
 */
export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, user } = useAuthStore();
  const [showRoleSelection, setShowRoleSelection] = useState(false);

  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;

  const managementTarget = useMemo(() => {
    if (!from || from === '/login' || from === '/public' || from === PORTAL_HOME) {
      return MANAGEMENT_HOME;
    }
    return from;
  }, [from]);

  useEffect(() => {
    if (!isAuthenticated || !user) {
      setShowRoleSelection(false);
      return;
    }

    if (isHighLevelRole(user.role)) {
      setShowRoleSelection(true);
      return;
    }

    navigate(from || PORTAL_HOME, { replace: true });
  }, [isAuthenticated, user, navigate, from]);

  const handleLogin = () => {
    // Login component submits credentials directly and sets cookie session.
    useAuthStore.getState().restoreSession().then(() => {
      const state = useAuthStore.getState();
      if (!state.user) {
        return;
      }

      if (isHighLevelRole(state.user.role)) {
        setShowRoleSelection(true);
        return;
      }

      navigate(from || PORTAL_HOME, { replace: true });
    });
  };

  const handleNavigateToPublic = () => {
    navigate('/public');
  };

  const handleSelectManagement = () => {
    setShowRoleSelection(false);
    navigate(managementTarget, { replace: true });
  };

  const handleSelectPortal = () => {
    setShowRoleSelection(false);
    navigate(PORTAL_HOME, { replace: true });
  };

  if (showRoleSelection && user) {
    return (
      <RoleSelectionDialog
        userFullName={user.full_name}
        onSelectManagement={handleSelectManagement}
        onSelectPortal={handleSelectPortal}
      />
    );
  }

  return (
    <LoginComponent
      onLogin={handleLogin}
      onNavigateToPublic={handleNavigateToPublic}
    />
  );
}

export default LoginPage;
