import React from 'react';
import { AccountingInboxPage as AccountingInboxComponent } from '../components/Accounting';

/**
 * AccountingPage - Wrapper for AccountingInboxPage component
 * No additional props needed as it manages its own state
 */
export function AccountingPage() {
    return <AccountingInboxComponent />;
}

export default AccountingPage;
