import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AdminDashboard as AdminDashboardComponent } from '../components/AdminDashboard';
import { useAuthStore } from '../stores/useAuthStore';

/**
 * AdminDashboardPage - Wrapper for AdminDashboard component
 * Provides user data from auth store and handles navigation
 */
export function AdminDashboardPage() {
    const navigate = useNavigate();
    const { user, logout } = useAuthStore();

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    const handleNavigateToPublic = () => {
        navigate('/public');
    };

    const handleNavigateToAccounting = () => {
        navigate('/accounting');
    };

    // Create user object in format expected by AdminDashboard
    const adminUser = user ? {
        id: user.id,
        username: user.username,
        fullName: user.full_name,
        role: user.role,
        admin_level: (user as any).admin_level,
    } : {
        id: 0,
        username: '',
        fullName: '',
        role: 'admin',
    };

    return (
        <AdminDashboardComponent
            user={adminUser}
            onLogout={handleLogout}
            onNavigateToPublic={handleNavigateToPublic}
            onNavigateToAccounting={handleNavigateToAccounting}
        />
    );
}

export default AdminDashboardPage;
