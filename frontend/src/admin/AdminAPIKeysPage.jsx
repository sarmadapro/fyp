import { useState, useEffect, useCallback } from 'react';
import { Key, Search, Trash2, X, ChevronLeft, ChevronRight } from 'lucide-react';
import toast from 'react-hot-toast';
import { adminListAllKeys, adminRevokeUserKey } from '../api/admin';

function Badge({ active }) {
  return active
    ? <span className="admin-badge badge-success">● Active</span>
    : <span className="admin-badge badge-neutral">○ Revoked</span>;
}

export default function AdminAPIKeysPage() {
  const [keys, setKeys]       = useState([]);
  const [total, setTotal]     = useState(0);
  const [page, setPage]       = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch]   = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [activeOnly, setActiveOnly]   = useState(false);

  const PAGE_SIZE = 30;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminListAllKeys({ search, activeOnly, page, pageSize: PAGE_SIZE });
      setKeys(data.keys);
      setTotal(data.total);
    } catch {
      toast.error('Failed to load API keys');
    } finally {
      setLoading(false);
    }
  }, [search, activeOnly, page]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const t = setTimeout(() => { setSearch(searchInput); setPage(1); }, 350);
    return () => clearTimeout(t);
  }, [searchInput]);

  const handleRevoke = async (key) => {
    if (!confirm(`Revoke key "${key.name}" (${key.key_prefix}…) for ${key.client_email}?`)) return;
    try {
      await adminRevokeUserKey(key.client_id, key.id);
      toast.success('Key revoked');
      load();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const totalCalls = keys.reduce((s, k) => s + k.usage_count, 0);

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Embed Keys</h1>
          <p className="admin-page-desc">{total.toLocaleString()} keys · {totalCalls.toLocaleString()} total API calls</p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="admin-toolbar">
        <div className="admin-search-wrap">
          <Search size={15} className="admin-search-icon" />
          <input
            className="admin-search-input"
            placeholder="Search by email, company or key prefix…"
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
          />
          {searchInput && (
            <button className="admin-search-clear" onClick={() => setSearchInput('')}><X size={13} /></button>
          )}
        </div>
        <label className="admin-checkbox-row" style={{ whiteSpace: 'nowrap' }}>
          <input type="checkbox" checked={activeOnly} onChange={e => { setActiveOnly(e.target.checked); setPage(1); }} />
          <span>Active only</span>
        </label>
      </div>

      <div className="admin-panel" style={{ padding: 0 }}>
        <div className="admin-table-wrap">
          <table className="admin-table admin-table-full">
            <thead>
              <tr>
                <th>Key</th>
                <th>Client</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Calls</th>
                <th>Last Used</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="admin-empty-row">
                  <div className="admin-spinner" style={{ margin: '0 auto' }} />
                </td></tr>
              ) : keys.length === 0 ? (
                <tr><td colSpan={7} className="admin-empty-row">
                  <Key size={28} /><p>No API keys found</p>
                </td></tr>
              ) : keys.map(k => (
                <tr key={k.id} className={`admin-table-row ${!k.is_active ? 'admin-row-muted' : ''}`}>
                  <td>
                    <div className="admin-key-cell">
                      <Key size={13} />
                      <div>
                        <div className="admin-key-name">{k.name}</div>
                        <code className="admin-key-prefix">{k.key_prefix}…</code>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div>
                      <div className="admin-user-company">{k.company_name}</div>
                      <div className="admin-muted admin-user-email-sm">{k.client_email}</div>
                    </div>
                  </td>
                  <td><Badge active={k.is_active} /></td>
                  <td style={{ textAlign: 'right' }}>
                    <span className="admin-calls-badge">{k.usage_count.toLocaleString()}</span>
                  </td>
                  <td className="admin-muted">
                    {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : 'Never'}
                  </td>
                  <td className="admin-muted">
                    {k.created_at ? new Date(k.created_at).toLocaleDateString() : '—'}
                  </td>
                  <td>
                    {k.is_active && (
                      <button
                        className="admin-icon-btn admin-icon-btn-danger"
                        title="Revoke key"
                        onClick={() => handleRevoke(k)}
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

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
