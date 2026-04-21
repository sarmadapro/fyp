import { useState, useEffect } from 'react';
import {
  Users, Key, Activity, TrendingUp, UserCheck, UserX,
  FileText, Shield, ArrowUpRight, Clock, Star
} from 'lucide-react';
import { adminGetStats } from '../api/admin';

function StatCard({ icon: Icon, label, value, sub, trend }) {
  return (
    <div className="admin-stat-card">
      <div className="admin-stat-icon-wrap">
        <Icon size={20} />
      </div>
      <div className="admin-stat-body">
        <div className="admin-stat-value">{value ?? '—'}</div>
        <div className="admin-stat-label">{label}</div>
        {sub && <div className="admin-stat-sub">{sub}</div>}
      </div>
      {trend !== undefined && (
        <div className={`admin-stat-trend ${trend >= 0 ? 'up' : 'down'}`}>
          <ArrowUpRight size={12} />
          {Math.abs(trend)}
        </div>
      )}
    </div>
  );
}

function Badge({ type }) {
  const map = {
    active:   { label: 'Active',    cls: 'badge-success' },
    inactive: { label: 'Inactive',  cls: 'badge-danger'  },
    verified: { label: 'Verified',  cls: 'badge-cyan'    },
    unverified: { label: 'Unverified', cls: 'badge-warning' },
  };
  const b = map[type] || { label: type, cls: 'badge-neutral' };
  return <span className={`admin-badge ${b.cls}`}>{b.label}</span>;
}

export default function AdminDashboard({ onNavigate }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminGetStats()
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="admin-page-loading">
      <div className="admin-spinner" />
      <span>Loading platform stats…</span>
    </div>
  );

  const u = stats?.users || {};
  const k = stats?.api_keys || {};
  const usage = stats?.usage || {};

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Dashboard</h1>
          <p className="admin-page-desc">Platform overview and live metrics</p>
        </div>
        <button className="admin-btn-secondary admin-btn-sm" onClick={() => window.location.reload()}>
          Refresh
        </button>
      </div>

      {/* Primary KPI row */}
      <div className="admin-stats-grid">
        <StatCard icon={Users}     label="Total Users"     value={u.total}    sub={`${u.new_7d} new this week`} />
        <StatCard icon={UserCheck} label="Active Users"    value={u.active}   sub={`${u.inactive} inactive`} />
        <StatCard icon={Key}       label="Active Embed Keys" value={k.active} sub={`${k.revoked} revoked`} />
        <StatCard icon={Activity}  label="Total API Calls" value={usage.total_api_calls?.toLocaleString()} sub="all time" />
      </div>

      {/* Secondary row */}
      <div className="admin-stats-grid admin-stats-grid-4">
        <StatCard icon={UserX}    label="Unverified Email" value={u.unverified} />
        <StatCard icon={FileText} label="With Documents"   value={u.with_documents} />
        <StatCard icon={Shield}   label="Admin Accounts"   value={u.admins} />
        <StatCard icon={TrendingUp} label="New Users (30d)" value={u.new_30d} />
      </div>

      {/* Bottom panels */}
      <div className="admin-panels">
        {/* Top users */}
        <div className="admin-panel">
          <div className="admin-panel-header">
            <Star size={16} />
            <h3>Top Users by API Usage</h3>
            <button className="admin-link admin-panel-more" onClick={() => onNavigate('users')}>
              View all →
            </button>
          </div>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Email</th>
                  <th style={{ textAlign: 'right' }}>API Calls</th>
                </tr>
              </thead>
              <tbody>
                {(stats?.top_users || []).map((u, i) => (
                  <tr key={u.id}>
                    <td>
                      <div className="admin-user-cell">
                        <div className="admin-user-avatar-sm">{(u.company_name || u.email)[0].toUpperCase()}</div>
                        {u.company_name}
                      </div>
                    </td>
                    <td className="admin-muted">{u.email}</td>
                    <td style={{ textAlign: 'right' }}>
                      <span className="admin-calls-badge">{u.calls.toLocaleString()}</span>
                    </td>
                  </tr>
                ))}
                {!stats?.top_users?.length && (
                  <tr><td colSpan={3} className="admin-empty-row">No usage data yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent registrations */}
        <div className="admin-panel">
          <div className="admin-panel-header">
            <Clock size={16} />
            <h3>Recent Registrations</h3>
            <button className="admin-link admin-panel-more" onClick={() => onNavigate('users')}>
              View all →
            </button>
          </div>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Status</th>
                  <th>Joined</th>
                </tr>
              </thead>
              <tbody>
                {(stats?.recent_users || []).map(u => (
                  <tr key={u.id}>
                    <td>
                      <div className="admin-user-cell">
                        <div className="admin-user-avatar-sm">{(u.company_name || u.email)[0].toUpperCase()}</div>
                        <div>
                          <div className="admin-user-company">{u.company_name}</div>
                          <div className="admin-muted admin-user-email-sm">{u.email}</div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <Badge type={u.is_active ? 'active' : 'inactive'} />
                      {!u.is_email_verified && <Badge type="unverified" />}
                    </td>
                    <td className="admin-muted">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                    </td>
                  </tr>
                ))}
                {!stats?.recent_users?.length && (
                  <tr><td colSpan={3} className="admin-empty-row">No users yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
