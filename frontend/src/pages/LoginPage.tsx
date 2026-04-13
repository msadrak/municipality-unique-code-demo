import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Login as LoginComponent } from '../components/Login';
import { RoleSelectionDialog } from '../components/auth/RoleSelectionDialog';
import { getDefaultHomePath } from '../components/funding/workflow';
import { useAuthStore } from '../stores/useAuthStore';

const MANAGEMENT_HOME = '/admin';

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
    if (!from || from === '/login' || from === '/public' || from === '/portal') {
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

    navigate(from || getDefaultHomePath(user.role), { replace: true });
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

      const role = (state.user.role || '').toUpperCase();
      const target = from || getDefaultHomePath(state.user.role);

      if (role === 'OPERATOR' && (!from || from === '/portal' || from === '/admin')) {
        navigate('/attendance/inbox', { replace: true });
      } else if (role === 'SECURITY_DIRECTOR' && (!from || from === '/portal' || from === '/admin')) {
        navigate('/security/aggregation', { replace: true });
      } else {
        navigate(target, { replace: true });
      }
    });
  };

  const handleNavigateToPublic = () => {
    navigate('/public');
  };

  const handleNavigateToContractorAuth = () => {
    navigate('/contractor-auth');
  };

  const handleSelectManagement = () => {
    setShowRoleSelection(false);
    navigate(managementTarget, { replace: true });
  };

  const handleSelectPortal = () => {
    setShowRoleSelection(false);
    navigate('/portal', { replace: true });
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
      onNavigateToContractorAuth={handleNavigateToContractorAuth}
    />
  );
}

export default LoginPage;
