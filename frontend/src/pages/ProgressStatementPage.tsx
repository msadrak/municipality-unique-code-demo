import React from 'react';
import { ProgressStatementWizard } from '../components/ProgressStatementWizard';

/**
 * ProgressStatementPage — page wrapper for the wizard.
 * Renders inside AppShell with light-gray bg.
 */
export default function ProgressStatementPage() {
    return (
        <div className="min-h-screen bg-slate-50 py-8 px-4" dir="rtl">
            <ProgressStatementWizard />
        </div>
    );
}
