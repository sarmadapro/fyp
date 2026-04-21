import { useState, useEffect, useCallback } from 'react';
import {
  Search, Plus, UserCheck, UserX, Trash2, Key, Shield, ShieldOff,
  MailCheck, LogOut, ChevronLeft, ChevronRight, FileText, X, Loader,
  Eye, Users
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  adminListUsers, adminGetUser, adminSetUserStatus, adminVerifyUser,
  adminToggleAdmin, adminDeleteUser, adminRevokeUserSessions,
  adminRevokeUserKey, adminCreateUser,
} from '../api/admin';

// ─── Helpers ──────────────────────────────────────────────────────────────

function Badge({ type, label }) {
  const map = {
    active:   'badge-success',
    inactive: 'badge-danger',
    verified: 'badge-cyan',
    unverified: 'badge-warning',
    admin:    'badge-purple',
    revoked:  'badge-neutral',
  };
  return <span className={`admin-badge ${map[type] || 'badge-neutral'}`}>{label || type}</span>;
}

function Confirm({ message, onConfirm, onCancel }) {
  return (
    <div className="admin-confirm-overlay" onClick={onCancel}>
      <div className="admin-confirm-box" onClick={e => e.stopPropagation()}>
        <p>{message}</p>
        <div className="admin-confirm-actions">
          <button className="admin-btn-secondary admin-btn-sm" onClick={onCancel}>Cancel</button>
          <button className="admin-btn-danger admin-btn-sm" onClick={onConfirm}>Confirm</button>
        </div>
      </div>
    </div>
  );
}

// ─── User Detail Drawer ───────────────────────────────────────────────────

function UserDetailDrawer({ userId, onClose, onUserUpdated }) {
  const [user, setUser]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [confirm, setConfirm] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    adminGetUser(userId).then(setUser).finally(() => setLoading(false));
  }, [userId]);

  useEffect(() => { load(); }, [load]);

  const action = async (fn, successMsg) => {
    try {
      await fn();
      toast.success(successMsg);
      load();
      onUserUpdated?.();
    } catch (err) {
      toast.error(err.message);
    }
  };

  if (loading || !user) return (
    <div className="admin-drawer">
      <div className="admin-drawer-header">
        <h3>User Detail</h3>
        <button className="admin-icon-btn" onClick={onClose}><X size={18} /></button>
      </div>
      <div className="admin-drawer-loading"><div className="admin-spinner" /></div>
    </div>
  );

  return (
    <div className="admin-drawer">
      {confirm && (
        <Confirm
          message={confirm.message}
          onConfirm={() => { confirm.fn(); setConfirm(null); }}
          onCancel={() => setConfirm(null)}
        />
      )}

      <div className="admin-drawer-header">
        <h3>User Detail</h3>
        <button className="admin-icon-btn" onClick={onClose}><X size={18} /></button>
      </div>

      <div className="admin-drawer-body">
        {/* Profile */}
        <div className="admin-drawer-section">
          <div className="admin-profile-hero">
            <div className="admin-profile-avatar">
              {(user.company_name || user.email)[0].toUpperCase()}
            </div>
            <div>
              <div className="admin-profile-company">{user.company_name}</div>
              <div className="admin-profile-name">{user.full_name || '—'}</div>
              <div className="admin-profile-email">{user.email}</div>
              <div className="admin-profile-badges">
                <Badge type={user.is_active ? 'active' : 'inactive'}
                       label={user.is_active ? 'Active' : 'Inactive'} />
                <Badge type={user.is_email_verified ? 'verified' : 'unverified'}
                       label={user.is_email_verified ? 'Email Verified' : 'Unverified'} />
                {user.is_admin && <Badge type="admin" label="Admin" />}
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="admin-drawer-section">
          <h4 className="admin-drawer-section-title">Usage Stats</h4>
          <div className="admin-detail-grid">
            <div className="admin-detail-item">
              <span className="admin-detail-label">Embed Key</span>
              <span className="admin-detail-val">{user.active_key_count > 0 ? '● Active' : '○ None'}</span>
            </div>
            <div className="admin-detail-item">
              <span className="admin-detail-label">Total API Calls</span>
              <span className="admin-detail-val">{user.total_api_calls?.toLocaleString()}</span>
            </div>
            <div className="admin-detail-item">
              <span className="admin-detail-label">Active Sessions</span>
              <span className="admin-detail-val">{user.active_sessions}</span>
            </div>
            <div className="admin-detail-item">
              <span className="admin-detail-label">Document</span>
              <span className="admin-detail-val">
                {user.has_document
                  ? <><FileText size={12} style={{marginRight:4}}/>{user.document_name}</>
                  : 'None'}
              </span>
            </div>
            <div className="admin-detail-item">
              <span className="admin-detail-label">Joined</span>
              <span className="admin-detail-val">
                {user.created_at ? new Date(user.created_at).toLocaleString() : '—'}
              </span>
            </div>
            <div className="admin-detail-item">
              <span className="admin-detail-label">Last API Call</span>
              <span className="admin-detail-val">
                {user.last_api_call_at ? new Date(user.last_api_call_at).toLocaleString() : 'Never'}
              </span>
            </div>
          </div>
        </div>

        {/* Embed Key */}
        <div className="admin-drawer-section">
          <h4 className="admin-drawer-section-title">Website Embed Key</h4>
          <div className="admin-keys-list">
            {(user.api_keys || []).filter(k => k.is_active).map(k => (
              <div key={k.id} className="admin-key-row">
                <div className="admin-key-info">
                  <Key size={13} />
                  <div>
                    <div className="admin-key-name">Embed Key</div>
                    <div className="admin-key-prefix">{k.key_prefix}…</div>
                  </div>
                </div>
                <div className="admin-key-meta">
                  <Badge type="active" label="● Active" />
                  <span className="admin-muted">{k.usage_count} calls</span>
                  <button
                    className="admin-icon-btn admin-icon-btn-danger"
                    title="Revoke embed key"
                    onClick={() => setConfirm({
                      message: `Revoke embed key (${k.key_prefix}…) for ${user.email}? Their widget will stop working.`,
                      fn: () => action(
                        () => adminRevokeUserKey(user.id, k.id),
                        'Embed key revoked'
                      ),
                    })}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            ))}
            {!user.api_keys?.filter(k => k.is_active).length && (
              <p className="admin-muted">No active embed key.</p>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="admin-drawer-section">
          <h4 className="admin-drawer-section-title">Actions</h4>
          <div className="admin-action-grid">
            {!user.is_email_verified && (
              <button
                className="admin-action-btn"
                onClick={() => action(() => adminVerifyUser(user.id), 'Email verified')}
              >
                <MailCheck size={15} /> Force Verify Email
              </button>
            )}
            <button
              className="admin-action-btn"
              onClick={() => setConfirm({
                message: `${user.is_active ? 'Deactivate' : 'Activate'} ${user.email}?`,
                fn: () => action(
                  () => adminSetUserStatus(user.id, !user.is_active),
                  user.is_active ? 'User deactivated' : 'User activated'
                ),
              })}
            >
              {user.is_active ? <UserX size={15} /> : <UserCheck size={15} />}
              {user.is_active ? 'Deactivate Account' : 'Activate Account'}
            </button>
            <button
              className="admin-action-btn"
              onClick={() => setConfirm({
                message: `Revoke all active sessions for ${user.email}?`,
                fn: () => action(() => adminRevokeUserSessions(user.id), 'Sessions revoked'),
              })}
            >
              <LogOut size={15} /> Revoke All Sessions
            </button>
            <button
              className="admin-action-btn"
              onClick={() => setConfirm({
                message: `${user.is_admin ? 'Remove' : 'Grant'} admin access for ${user.email}?`,
                fn: () => action(() => adminToggleAdmin(user.id),
                  user.is_admin ? 'Admin revoked' : 'Admin granted'),
              })}
            >
              {user.is_admin ? <ShieldOff size={15} /> : <Shield size={15} />}
              {user.is_admin ? 'Revoke Admin' : 'Grant Admin'}
            </button>
            <button
              className="admin-action-btn admin-action-btn-danger"
              onClick={() => setConfirm({
                message: `PERMANENTLY delete ${user.email} and all their data? This cannot be undone.`,
                fn: () => action(
                  () => adminDeleteUser(user.id),
                  'User deleted'
                ).then(onClose),
              })}
            >
              <Trash2 size={15} /> Delete Account
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Create User Modal ────────────────────────────────────────────────────

function CreateUserModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ email: '', password: '', company_name: '', full_name: '', is_admin: false });
  const [loading, setLoading] = useState(false);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.email || !form.password || !form.company_name) {
      toast.error('Fill in all required fields'); return;
    }
    setLoading(true);
    try {
      const data = await adminCreateUser(form);
      toast.success(`User created. API Key: ${data.api_key}`);
      onCreated?.();
      onClose();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" onClick={e => e.stopPropagation()}>
        <div className="admin-modal-header">
          <h3>Create User</h3>
          <button className="admin-icon-btn" onClick={onClose}><X size={18} /></button>
        </div>
        <form onSubmit={handleSubmit} className="admin-modal-body">
          <div className="admin-field">
            <label className="admin-label">Email *</label>
            <input className="admin-input" style={{paddingLeft:'var(--space-4)'}} type="email" value={form.email}
              onChange={e => set('email', e.target.value)} placeholder="user@company.com" />
          </div>
          <div className="admin-field">
            <label className="admin-label">Company Name *</label>
            <input className="admin-input" style={{paddingLeft:'var(--space-4)'}} value={form.company_name}
              onChange={e => set('company_name', e.target.value)} placeholder="Acme Corp" />
          </div>
          <div className="admin-field">
            <label className="admin-label">Full Name</label>
            <input className="admin-input" style={{paddingLeft:'var(--space-4)'}} value={form.full_name}
              onChange={e => set('full_name', e.target.value)} placeholder="Jane Doe" />
          </div>
          <div className="admin-field">
            <label className="admin-label">Password *</label>
            <input className="admin-input" style={{paddingLeft:'var(--space-4)'}} type="password" value={form.password}
              onChange={e => set('password', e.target.value)} placeholder="Min 8 chars" />
          </div>
          <label className="admin-checkbox-row">
            <input type="checkbox" checked={form.is_admin}
              onChange={e => set('is_admin', e.target.checked)} />
            <span>Grant admin access</span>
          </label>
          <div className="admin-modal-footer">
            <button type="button" className="admin-btn-secondary admin-btn-sm" onClick={onClose}>Cancel</button>
            <button type="submit" className="admin-btn-primary admin-btn-sm" disabled={loading}>
              {loading ? <Loader size={14} className="admin-spin" /> : <Plus size={14} />}
              Create User
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────

export default function AdminUsersPage() {
  const [users, setUsers]         = useState([]);
  const [total, setTotal]         = useState(0);
  const [page, setPage]           = useState(1);
  const [loading, setLoading]     = useState(true);
  const [search, setSearch]       = useState('');
  const [statusFilter, setStatus] = useState('all');
  const [selectedId, setSelectedId] = useState(null);
  const [showCreate, setShowCreate] = useState(false);

  const PAGE_SIZE = 20;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminListUsers({ search, status: statusFilter, page, pageSize: PAGE_SIZE });
      setUsers(data.users);
      setTotal(data.total);
    } catch (err) {
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, page]);

  useEffect(() => { load(); }, [load]);

  // Debounce search
  const [searchInput, setSearchInput] = useState('');
  useEffect(() => {
    const t = setTimeout(() => { setSearch(searchInput); setPage(1); }, 350);
    return () => clearTimeout(t);
  }, [searchInput]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="admin-page">
      {selectedId && (
        <div className="admin-drawer-overlay" onClick={() => setSelectedId(null)}>
          <div onClick={e => e.stopPropagation()} style={{ height: '100%' }}>
            <UserDetailDrawer
              userId={selectedId}
              onClose={() => setSelectedId(null)}
              onUserUpdated={load}
            />
          </div>
        </div>
      )}

      {showCreate && (
        <CreateUserModal onClose={() => setShowCreate(false)} onCreated={load} />
      )}

      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Users</h1>
          <p className="admin-page-desc">{total.toLocaleString()} total users</p>
        </div>
        <button className="admin-btn-primary admin-btn-sm" onClick={() => setShowCreate(true)}>
          <Plus size={14} /> Create User
        </button>
      </div>

      {/* Toolbar */}
      <div className="admin-toolbar">
        <div className="admin-search-wrap">
          <Search size={15} className="admin-search-icon" />
          <input
            className="admin-search-input"
            placeholder="Search by email, company, name…"
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
          />
          {searchInput && (
            <button className="admin-search-clear" onClick={() => setSearchInput('')}><X size={13} /></button>
          )}
        </div>
        <div className="admin-filter-tabs">
          {['all', 'active', 'inactive', 'unverified'].map(f => (
            <button
              key={f}
              className={`admin-filter-tab ${statusFilter === f ? 'active' : ''}`}
              onClick={() => { setStatus(f); setPage(1); }}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="admin-panel" style={{ padding: 0 }}>
        <div className="admin-table-wrap">
          <table className="admin-table admin-table-full">
            <thead>
              <tr>
                <th>User</th>
                <th>Status</th>
                <th>API Keys</th>
                <th>Total Calls</th>
                <th>Joined</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="admin-empty-row">
                  <div className="admin-spinner" style={{ margin: '0 auto' }} />
                </td></tr>
              ) : users.length === 0 ? (
                <tr><td colSpan={6} className="admin-empty-row">
                  <Users size={28} />
                  <p>No users found</p>
                </td></tr>
              ) : users.map(u => (
                <tr key={u.id} className="admin-table-row">
                  <td>
                    <div className="admin-user-cell">
                      <div className="admin-user-avatar-sm">{(u.company_name || u.email)[0].toUpperCase()}</div>
                      <div>
                        <div className="admin-user-company">
                          {u.company_name}
                          {u.is_admin && <Shield size={11} className="admin-admin-icon" title="Admin" />}
                        </div>
                        <div className="admin-muted admin-user-email-sm">{u.email}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div className="admin-badges-cell">
                      <Badge type={u.is_active ? 'active' : 'inactive'}
                             label={u.is_active ? '● Active' : '○ Inactive'} />
                      {!u.is_email_verified && <Badge type="unverified" label="Unverified" />}
                    </div>
                  </td>
                  <td>
                    <span className="admin-muted">{u.active_key_count}/{u.api_key_count}</span>
                  </td>
                  <td>
                    <span className="admin-calls-badge">{u.total_api_calls?.toLocaleString()}</span>
                  </td>
                  <td className="admin-muted">
                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                  </td>
                  <td>
                    <div className="admin-row-actions">
                      <button
                        className="admin-icon-btn"
                        title="View detail"
                        onClick={() => setSelectedId(u.id)}
                      >
                        <Eye size={15} />
                      </button>
                      <button
                        className={`admin-icon-btn ${u.is_active ? 'admin-icon-btn-warning' : 'admin-icon-btn-success'}`}
                        title={u.is_active ? 'Deactivate' : 'Activate'}
                        onClick={async () => {
                          try {
                            await adminSetUserStatus(u.id, !u.is_active);
                            toast.success(u.is_active ? 'User deactivated' : 'User activated');
                            load();
                          } catch (err) { toast.error(err.message); }
                        }}
                      >
                        {u.is_active ? <UserX size={15} /> : <UserCheck size={15} />}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="admin-pagination">
            <button className="admin-page-btn" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
              <ChevronLeft size={15} />
            </button>
            <span className="admin-page-info">Page {page} of {totalPages}</span>
            <button className="admin-page-btn" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
              <ChevronRight size={15} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
