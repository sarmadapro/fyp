import { useState, useEffect } from 'react';
import { TrendingUp, Users, Key, Activity, Award } from 'lucide-react';
import { adminGetAnalytics, adminGetStats } from '../api/admin';

function MiniBar({ value, max, color = 'purple' }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="admin-minibar-wrap">
      <div
        className={`admin-minibar admin-minibar-${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export default function AdminAnalyticsPage() {
  const [analytics, setAnalytics] = useState(null);
  const [stats, setStats]         = useState(null);
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    Promise.all([adminGetAnalytics(), adminGetStats()])
      .then(([a, s]) => { setAnalytics(a); setStats(s); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="admin-page-loading">
      <div className="admin-spinner" />
      <span>Loading analytics…</span>
    </div>
  );

  const growth   = analytics?.user_growth || [];
  const topClients = analytics?.top_clients || [];
  const dist     = analytics?.key_activity_distribution || {};
  const maxGrowth = Math.max(...growth.map(g => g.new_users), 1);
  const maxCalls  = Math.max(...topClients.map(c => c.total_calls), 1);

  const distTotal = (dist.unused || 0) + (dist.low_1_100 || 0) + (dist.mid_101_1000 || 0) + (dist['high_1000+'] || 0);

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Analytics</h1>
          <p className="admin-page-desc">Platform-wide usage insights</p>
        </div>
      </div>

      <div className="admin-analytics-grid">
        {/* User growth */}
        <div className="admin-panel admin-analytics-panel">
          <div className="admin-panel-header">
            <TrendingUp size={16} />
            <h3>User Growth (Last 6 Months)</h3>
          </div>
          <div className="admin-growth-chart">
            {growth.map((g, i) => (
              <div key={i} className="admin-growth-row">
                <span className="admin-growth-label">{g.month}</span>
                <MiniBar value={g.new_users} max={maxGrowth} color="purple" />
                <span className="admin-growth-val">{g.new_users}</span>
              </div>
            ))}
          </div>
          <div className="admin-growth-total">
            Total: {growth.reduce((s, g) => s + g.new_users, 0)} new users in 6 months
          </div>
        </div>

        {/* API Key Activity Distribution */}
        <div className="admin-panel admin-analytics-panel">
          <div className="admin-panel-header">
            <Key size={16} />
            <h3>API Key Activity Distribution</h3>
          </div>
          <div className="admin-dist-list">
            {[
              { label: 'Unused (0 calls)',       val: dist.unused,       color: 'neutral' },
              { label: 'Low (1–100 calls)',       val: dist.low_1_100,    color: 'cyan'   },
              { label: 'Medium (101–1000)',       val: dist.mid_101_1000, color: 'purple' },
              { label: 'High (1000+ calls)',      val: dist['high_1000+'],color: 'success' },
            ].map(row => (
              <div key={row.label} className="admin-dist-row">
                <span className="admin-dist-label">{row.label}</span>
                <MiniBar value={row.val || 0} max={distTotal || 1} color={row.color} />
                <span className="admin-dist-val">{row.val || 0}</span>
              </div>
            ))}
          </div>
          <div className="admin-dist-total">
            {distTotal} total keys
          </div>
        </div>

        {/* Top clients */}
        <div className="admin-panel admin-analytics-panel-wide">
          <div className="admin-panel-header">
            <Award size={16} />
            <h3>Top 10 Clients by API Usage</h3>
          </div>
          <div className="admin-table-wrap">
            <table className="admin-table admin-table-full">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Company</th>
                  <th>Email</th>
                  <th>Keys</th>
                  <th>Usage</th>
                  <th style={{ width: '200px' }}>Share</th>
                </tr>
              </thead>
              <tbody>
                {topClients.map((c, i) => (
                  <tr key={c.id} className="admin-table-row">
                    <td className="admin-muted admin-rank">#{i + 1}</td>
                    <td>
                      <div className="admin-user-cell">
                        <div className="admin-user-avatar-sm">{(c.company_name || c.email)[0].toUpperCase()}</div>
                        {c.company_name}
                      </div>
                    </td>
                    <td className="admin-muted">{c.email}</td>
                    <td className="admin-muted">{c.key_count}</td>
                    <td>
                      <span className="admin-calls-badge">{c.total_calls.toLocaleString()}</span>
                    </td>
                    <td>
                      <MiniBar value={c.total_calls} max={maxCalls} color="purple" />
                    </td>
                  </tr>
                ))}
                {!topClients.length && (
                  <tr><td colSpan={6} className="admin-empty-row">No usage data yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Summary cards */}
        <div className="admin-panel admin-analytics-panel">
          <div className="admin-panel-header">
            <Activity size={16} />
            <h3>Platform Summary</h3>
          </div>
          <div className="admin-summary-list">
            {[
              { label: 'Total Users',        val: stats?.users?.total?.toLocaleString() },
              { label: 'Active Users',        val: stats?.users?.active?.toLocaleString() },
              { label: 'Email Verified',      val: stats?.users?.verified?.toLocaleString() },
              { label: 'With Documents',      val: stats?.users?.with_documents?.toLocaleString() },
              { label: 'Total API Keys',      val: stats?.api_keys?.total?.toLocaleString() },
              { label: 'Active API Keys',     val: stats?.api_keys?.active?.toLocaleString() },
              { label: 'Lifetime API Calls',  val: stats?.usage?.total_api_calls?.toLocaleString() },
              { label: 'New Users (7d)',       val: stats?.users?.new_7d?.toLocaleString() },
              { label: 'New Users (30d)',      val: stats?.users?.new_30d?.toLocaleString() },
            ].map(row => (
              <div key={row.label} className="admin-summary-row">
                <span className="admin-summary-label">{row.label}</span>
                <span className="admin-summary-val">{row.val ?? '—'}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
