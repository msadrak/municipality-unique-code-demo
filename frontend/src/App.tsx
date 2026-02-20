import React, { useEffect } from 'react';
import { RouterProvider } from 'react-router-dom';
import { router } from './app/routes';
import { useAuthStore } from './stores/useAuthStore';
import './components/Accounting/AccountingInbox.css';

/**
 * App - Root application component
 * Initializes auth session restore and provides router
 */
export default function App() {
  const { restoreSession } = useAuthStore();

  // Restore session on app mount
  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  return <RouterProvider router={router} />;
}
