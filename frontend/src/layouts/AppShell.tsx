import React from 'react';
import { Outlet } from 'react-router-dom';
import { SidebarProvider, SidebarInset } from '../components/ui/sidebar';
import { SideNav } from './SideNav';
import { TopBar } from './TopBar';

/**
 * AppShell - Main application layout with sidebar and topbar
 * Wraps authenticated pages with consistent navigation
 */
export function AppShell() {
    return (
        <div dir="rtl" className="min-h-screen">
            <SidebarProvider defaultOpen={true}>
                <SideNav />
                <SidebarInset className="transition-[margin] duration-200 ease-linear peer-data-[state=expanded]:mr-64 peer-data-[state=collapsed]:mr-12">
                    <TopBar />
                    <main className="flex-1 overflow-auto">
                        <Outlet />
                    </main>
                </SidebarInset>
            </SidebarProvider>
        </div>
    );
}

export default AppShell;
