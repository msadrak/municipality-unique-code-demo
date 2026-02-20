import React from 'react';
import { useNavigate } from 'react-router-dom';
import { PublicDashboard as PublicDashboardComponent } from '../components/PublicDashboard';

/**
 * PublicDashboardPage - Wrapper for PublicDashboard component
 * Integrates with React Router for navigation
 */
export function PublicDashboardPage() {
    const navigate = useNavigate();

    const handleNavigateToLogin = () => {
        navigate('/login');
    };

    return (
        <PublicDashboardComponent onNavigateToLogin={handleNavigateToLogin} />
    );
}

export default PublicDashboardPage;
