import React from 'react';
import { Outlet } from 'react-router-dom';
import { SideNavV2 } from './SideNavV2';
import { TopBarV2 } from './TopBarV2';

/**
 * AppShell — Main layout matching Stitch design
 * Right sidebar (dark) + main content area with top header
 * Uses flex layout: sidebar on right (RTL), content fills remaining space
 */
export function AppShell() {
    return (
        <div dir="rtl" className="flex min-h-screen bg-background">
            {/* Dark sidebar on the right (RTL start) */}
            <SideNavV2 />
            {/* Main content area */}
            <main className="flex-1 flex flex-col min-h-screen min-w-0">
                <TopBarV2 />
                {/* Scrollable content */}
                <div className="p-6 lg:p-10">
                    <Outlet />
                </div>
            </main>
        </div>
    );
}

export default AppShell;
