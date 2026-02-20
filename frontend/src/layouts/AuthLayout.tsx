import React from 'react';
import { Outlet } from 'react-router-dom';

/**
 * AuthLayout - Layout for unauthenticated pages (login, public dashboard)
 * Simple centered layout without sidebar
 */
export function AuthLayout() {
    return (
        <div dir="rtl" className="min-h-screen">
            <Outlet />
        </div>
    );
}

export default AuthLayout;
