import React from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';

// Layouts
import { AuthLayout, AppShell } from '../layouts';

// Route Guards
import { RequireAuth } from '../components/RequireAuth';
import { ForbiddenPage } from '../components/ForbiddenPage';
import { OfficialLetterForm } from '../components/funding/OfficialLetterForm';
import { OfficialLetterViewer } from '../components/funding/OfficialLetterViewer';
import { MyFundingRequestsV2 } from '../components/funding/MyFundingRequestsV2';
import { FundingManagerInboxV2 } from '../components/funding/FundingManagerInboxV2';
import {
    canAccessCivilModule,
    canAccessAttendanceAggregationDashboard,
    canAccessAttendanceModule,
    canAccessHrModule,
    canSeeFundingArchive,
} from '../components/funding/workflow';
import { useAuthStore } from '../stores/useAuthStore';

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
    ContractorRegistration,
    ProgressStatementPage,
} from '../pages';
import RegionalAttendanceUpload from '../pages/attendance/RegionalAttendanceUpload';
import ContractorStatementUpload from '../pages/attendance/ContractorStatementUpload';
import AttendanceInbox from '../pages/attendance/AttendanceInbox';
import AttendanceDetail from '../pages/attendance/AttendanceDetail';
import ReconciliationDashboard from '../pages/attendance/ReconciliationDashboard';
import LetterArchive from '../pages/funding/LetterArchive';
import SecurityAggregationDashboard from '../pages/SecurityAggregationDashboard';

/**
 * Application routes configuration
 * Phase 1: Maps existing page components to URL routes via page wrappers
 */
function DomainRoute({
    children,
    allow,
}: {
    children: React.ReactNode;
    allow: (role?: string | null) => boolean;
}) {
    const role = useAuthStore((state) => state.user?.role);

    if (!allow(role)) {
        return <Navigate to="/forbidden" replace />;
    }

    return <>{children}</>;
}

export const router = createBrowserRouter(
    [
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
                {
                    path: '/contractor-auth',
                    element: <ContractorRegistration />,
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
                    element: (
                        <DomainRoute allow={canAccessCivilModule}>
                            <UserPortalPage />
                        </DomainRoute>
                    ),
                },

                // Admin dashboard
                {
                    path: '/admin',
                    element: <AdminDashboardPage />,
                },

                // Accounting inbox
                {
                    path: '/accounting',
                    element: (
                        <DomainRoute allow={canAccessCivilModule}>
                            <AccountingPage />
                        </DomainRoute>
                    ),
                },
                // Contracts dashboard
                {
                    path: '/contracts',
                    element: (
                        <DomainRoute allow={canAccessCivilModule}>
                            <ContractsList />
                        </DomainRoute>
                    ),
                },
                // New contract wizard (MUST come before :id to avoid matching "new" as an ID)
                {
                    path: '/contracts/new',
                    element: (
                        <DomainRoute allow={canAccessCivilModule}>
                            <NewContract />
                        </DomainRoute>
                    ),
                },
                // Contract detail / execution hub
                {
                    path: '/contracts/:id',
                    element: (
                        <DomainRoute allow={canAccessCivilModule}>
                            <ContractDetails />
                        </DomainRoute>
                    ),
                },

                // Executive reports dashboard
                {
                    path: '/reports',
                    element: (
                        <DomainRoute allow={canAccessCivilModule}>
                            <ReportsPage />
                        </DomainRoute>
                    ),
                },

                // Progress Statement wizard (requires contractId in URL)
                {
                    path: '/contracts/:contractId/progress-statements/new',
                    element: (
                        <DomainRoute allow={canAccessCivilModule}>
                            <ProgressStatementPage />
                        </DomainRoute>
                    ),
                },
                // HR funding workflow
                {
                    path: '/hr/funding/new',
                    element: (
                        <DomainRoute allow={canAccessHrModule}>
                            <OfficialLetterForm />
                        </DomainRoute>
                    ),
                },
                {
                    path: '/hr/funding/my-requests',
                    element: (
                        <DomainRoute allow={canAccessHrModule}>
                            <MyFundingRequestsV2 />
                        </DomainRoute>
                    ),
                },
                {
                    path: '/hr/funding/inbox',
                    element: (
                        <DomainRoute allow={canAccessHrModule}>
                            <FundingManagerInboxV2 />
                        </DomainRoute>
                    ),
                },
                {
                    path: '/hr/funding/archive',
                    element: (
                        <DomainRoute allow={canSeeFundingArchive}>
                            <LetterArchive />
                        </DomainRoute>
                    ),
                },
                {
                    path: '/hr/funding/letters/:id',
                    element: (
                        <DomainRoute allow={canAccessHrModule}>
                            <OfficialLetterViewer />
                        </DomainRoute>
                    ),
                },
                {
                    path: '/region/attendance/upload',
                    element: (
                        <DomainRoute allow={canAccessAttendanceModule}>
                            <RegionalAttendanceUpload />
                        </DomainRoute>
                    ),
                },
                {
                    path: '/contractor/statement/upload',
                    element: (
                        <DomainRoute allow={canAccessAttendanceModule}>
                            <ContractorStatementUpload />
                        </DomainRoute>
                    ),
                },
                {
                    path: '/attendance/inbox',
                    element: (
                        <DomainRoute allow={canAccessAttendanceModule}>
                            <AttendanceInbox />
                        </DomainRoute>
                    ),
                },
                {
                    path: '/attendance/:id',
                    element: (
                        <DomainRoute allow={canAccessAttendanceModule}>
                            <AttendanceDetail />
                        </DomainRoute>
                    ),
                },
                {
                    path: '/security/reconciliation',
                    element: (
                        <DomainRoute allow={canAccessAttendanceAggregationDashboard}>
                            <ReconciliationDashboard />
                        </DomainRoute>
                    ),
                },
                {
                    path: '/security/aggregation',
                    element: (
                        <DomainRoute allow={canAccessAttendanceAggregationDashboard}>
                            <SecurityAggregationDashboard />
                        </DomainRoute>
                    ),
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
    ],
    {
        future: {
            v7_relativeSplatPath: true,
            v7_fetcherPersist: true,
            v7_normalizeFormMethod: true,
            v7_partialHydration: true,
            v7_skipActionErrorRevalidation: true,
        },
    },
);

export default router;
