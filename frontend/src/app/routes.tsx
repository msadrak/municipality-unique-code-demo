import React from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';

// Layouts
import { AuthLayout, AppShell } from '../layouts';

// Route Guards
import { RequireAuth } from '../components/RequireAuth';
import { ForbiddenPage } from '../components/ForbiddenPage';

// Page wrappers - integrate existing components with React Router
import {
    LoginPage,
    PublicDashboardPage,
    UserPortalPage,
    AdminDashboardPage,
    AccountingPage,
    ContractsList,
    ContractDetails,
    NewContract,
    ReportsPage,
} from '../pages';

/**
 * Application routes configuration
 * Phase 1: Maps existing page components to URL routes via page wrappers
 */
export const router = createBrowserRouter([
    // Public routes (AuthLayout - no sidebar)
    {
        element: <AuthLayout />,
        children: [
            {
                path: '/login',
                element: <LoginPage />,
            },
            {
                path: '/public',
                element: <PublicDashboardPage />,
            },
        ],
    },

    // Protected routes (AppShell - with sidebar)
    {
        element: (
            <RequireAuth>
                <AppShell />
            </RequireAuth>
        ),
        children: [
            // User portal
            {
                path: '/portal',
                element: <UserPortalPage />,
            },

            // Admin dashboard
            {
                path: '/admin',
                element: <AdminDashboardPage />,
            },

            // Accounting inbox
            {
                path: '/accounting',
                element: <AccountingPage />,
            },
            // Contracts dashboard
            {
                path: '/contracts',
                element: <ContractsList />,
            },
            // New contract wizard (MUST come before :id to avoid matching "new" as an ID)
            {
                path: '/contracts/new',
                element: <NewContract />,
            },
            // Contract detail / execution hub
            {
                path: '/contracts/:id',
                element: <ContractDetails />,
            },

            // Executive reports dashboard
            {
                path: '/reports',
                element: <ReportsPage />,
            },
        ],
    },

    // 403 Forbidden page
    {
        path: '/forbidden',
        element: <ForbiddenPage />,
    },

    // Catch-all redirect to login
    {
        path: '*',
        element: <Navigate to="/login" replace />,
    },
]);

export default router;
