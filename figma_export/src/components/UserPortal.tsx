import React, { useState } from 'react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Building2, LogOut, FileText, List } from 'lucide-react';
import { TransactionWizard } from './TransactionWizard';
import { MyTransactionsList } from './MyTransactionsList';

type User = {
  id: number;
  username: string;
  fullName: string;
  role: 'user' | 'admin';
};

type UserPortalProps = {
  user: User;
  onLogout: () => void;
  onNavigateToPublic: () => void;
};

type View = 'wizard' | 'my-transactions';

export function UserPortal({ user, onLogout, onNavigateToPublic }: UserPortalProps) {
  const [currentView, setCurrentView] = useState<View>('wizard');

  return (
    <div className="min-h-screen bg-background">
      {/* Header - Government Identity */}
      <header className="bg-card border-b border-border">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-primary p-2 rounded">
                <Building2 className="h-6 w-6 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-lg">پرتال کاربری</h1>
                <p className="text-sm text-muted-foreground">شهرداری اصفهان - معاونت مالی</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="text-left">
                <p className="text-sm">{user.fullName}</p>
                <p className="text-xs text-muted-foreground">کاربر مالی</p>
              </div>
              <Button variant="outline" size="sm" onClick={onLogout}>
                <LogOut className="h-4 w-4 ml-2" />
                خروج
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs - One Decision: What to View */}
      <div className="bg-card border-b border-border">
        <div className="container mx-auto px-4">
          <div className="flex gap-1">
            <button
              onClick={() => setCurrentView('wizard')}
              className={`px-6 py-3 border-b-2 transition-colors ${
                currentView === 'wizard'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <FileText className="h-4 w-4 inline-block ml-2" />
              ایجاد تراکنش جدید
            </button>
            <button
              onClick={() => setCurrentView('my-transactions')}
              className={`px-6 py-3 border-b-2 transition-colors ${
                currentView === 'my-transactions'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <List className="h-4 w-4 inline-block ml-2" />
              تراکنش‌های من
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {currentView === 'wizard' && <TransactionWizard userId={user.id} />}
        {currentView === 'my-transactions' && <MyTransactionsList userId={user.id} />}
      </main>
    </div>
  );
}
