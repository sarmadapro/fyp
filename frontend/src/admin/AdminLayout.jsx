import {
  LayoutDashboard, Users, Key, BarChart3,
  Shield, LogOut, ChevronRight, Mic
} from 'lucide-react';
import { adminLogout, getSavedAdmin } from '../api/admin';

const NAV = [
  { key: 'dashboard',  label: 'Dashboard',  icon: LayoutDashboard },
  { key: 'users',      label: 'Users',       icon: Users },
  { key: 'api-keys',   label: 'Embed Keys',  icon: Key },
  { key: 'analytics',  label: 'Analytics',   icon: BarChart3 },
];

export default function AdminLayout({ page, onNavigate, onLogout, children }) {
  const admin = getSavedAdmin();

  const handleLogout = () => {
    adminLogout();
    onLogout();
  };

  return (
    <div className="admin-layout">
      {/* Sidebar */}
      <aside className="admin-sidebar">
        <div className="admin-sidebar-brand">
          <div className="admin-brand-icon">
            <Mic size={16} />
          </div>
          <div className="admin-brand-text">
            <span className="admin-brand-name">VoiceRAG</span>
            <span className="admin-brand-badge">Admin</span>
          </div>
        </div>

        <nav className="admin-nav">
          {NAV.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              className={`admin-nav-item ${page === key ? 'active' : ''}`}
              onClick={() => onNavigate(key)}
            >
              <Icon size={18} />
              <span>{label}</span>
              {page === key && <ChevronRight size={14} className="admin-nav-arrow" />}
            </button>
          ))}
        </nav>

        <div className="admin-sidebar-footer">
          <div className="admin-sidebar-user">
            <div className="admin-user-avatar">
              <Shield size={14} />
            </div>
            <div className="admin-user-info">
              <span className="admin-user-name">{admin?.company_name || 'Admin'}</span>
              <span className="admin-user-email">{admin?.email || ''}</span>
            </div>
          </div>
          <button className="admin-logout-btn" onClick={handleLogout} title="Sign out">
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="admin-main">
        {children}
      </main>
    </div>
  );
}
