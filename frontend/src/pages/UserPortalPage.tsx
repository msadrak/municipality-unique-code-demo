import React from 'react';
import { useNavigate } from 'react-router-dom';
import { UserPortal as UserPortalComponent } from '../components/UserPortal';
import { useAuthStore } from '../stores/useAuthStore';

/**
 * UserPortalPage - Wrapper for UserPortal component
 * Provides user data from auth store and handles navigation
 */
export function UserPortalPage() {
    const navigate = useNavigate();
    const { user, logout } = useAuthStore();

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    const handleNavigateToPublic = () => {
        navigate('/public');
    };

    // Create user object in format expected by UserPortal
    const portalUser = user ? {
        id: user.id,
        username: user.username,
        fullName: user.full_name,
        role: user.role as 'user' | 'admin',
    } : {
        id: 0,
        username: '',
        fullName: '',
        role: 'user' as const,
    };

    return (
        <UserPortalComponent
            user={portalUser}
            onLogout={handleLogout}
            onNavigateToPublic={handleNavigateToPublic}
        />
    );
}

export default UserPortalPage;
