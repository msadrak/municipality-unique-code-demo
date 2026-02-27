import React from 'react';
import { Outlet } from 'react-router-dom';
import { SideNav } from './SideNav';
import { TopBar } from './TopBar';

/**
 * AppShell — Main layout matching Stitch design
 * Right sidebar (dark) + main content area with top header
 * Uses flex layout: sidebar on right (RTL), content fills remaining space
 */
export function AppShell() {
    return (
        <div dir="rtl" className="flex min-h-screen bg-slate-50">
            {/* Dark sidebar on the right (RTL start) */}
            <SideNav />
            {/* Main content area */}
            <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
                <TopBar />
                {/* Scrollable content */}
                <div className="flex-1 overflow-auto p-6 lg:p-10">
                    <Outlet />
                </div>
            </main>
        </div>
    );
}

export default AppShell;
