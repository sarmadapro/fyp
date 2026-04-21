import { useState, useEffect } from 'react';
import './admin.css';
import { isAdminAuthenticated } from '../api/admin';
import AdminLoginPage from './AdminLoginPage';
import AdminLayout from './AdminLayout';
import AdminDashboard from './AdminDashboard';
import AdminUsersPage from './AdminUsersPage';
import AdminAPIKeysPage from './AdminAPIKeysPage';
import AdminAnalyticsPage from './AdminAnalyticsPage';

const PAGES = {
  dashboard: AdminDashboard,
  users:     AdminUsersPage,
  'api-keys': AdminAPIKeysPage,
  analytics: AdminAnalyticsPage,
};

export default function AdminApp({ onExitAdmin }) {
  const [authed, setAuthed]   = useState(isAdminAuthenticated());
  const [page, setPage]       = useState('dashboard');

  // Listen for 401/403 events
  useEffect(() => {
    const handler = () => setAuthed(false);
    window.addEventListener('admin:unauthorized', handler);
    return () => window.removeEventListener('admin:unauthorized', handler);
  }, []);

  if (!authed) {
    return <AdminLoginPage onLoginSuccess={() => setAuthed(true)} />;
  }

  const ActivePage = PAGES[page] || AdminDashboard;

  return (
    <AdminLayout page={page} onNavigate={setPage} onLogout={() => setAuthed(false)}>
      <ActivePage onNavigate={setPage} />
    </AdminLayout>
  );
}
