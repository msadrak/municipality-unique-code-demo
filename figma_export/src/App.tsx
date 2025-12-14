import React, { useState } from 'react';
import { Login } from './components/Login';
import { UserPortal } from './components/UserPortal';
import { AdminDashboard } from './components/AdminDashboard';
import { PublicDashboard } from './components/PublicDashboard';

type User = {
  id: number;
  username: string;
  fullName: string;
  role: 'user' | 'admin';
};

type Page = 'login' | 'user-portal' | 'admin-dashboard' | 'public-dashboard';

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>('login');
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  const handleLogin = (user: User) => {
    setCurrentUser(user);
    if (user.role === 'admin') {
      setCurrentPage('admin-dashboard');
    } else {
      setCurrentPage('user-portal');
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
    setCurrentPage('login');
  };

  const navigateTo = (page: Page) => {
    setCurrentPage(page);
  };

  return (
    <div dir="rtl" className="min-h-screen">
      {currentPage === 'login' && (
        <Login onLogin={handleLogin} onNavigateToPublic={() => navigateTo('public-dashboard')} />
      )}
      
      {currentPage === 'user-portal' && currentUser && (
        <UserPortal user={currentUser} onLogout={handleLogout} onNavigateToPublic={() => navigateTo('public-dashboard')} />
      )}
      
      {currentPage === 'admin-dashboard' && currentUser && (
        <AdminDashboard user={currentUser} onLogout={handleLogout} onNavigateToPublic={() => navigateTo('public-dashboard')} />
      )}
      
      {currentPage === 'public-dashboard' && (
        <PublicDashboard onNavigateToLogin={() => navigateTo('login')} />
      )}
    </div>
  );
}
