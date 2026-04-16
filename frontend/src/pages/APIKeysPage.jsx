import { useState, useEffect } from 'react';
import {
  Key, Plus, Copy, Trash2, Code, CheckCircle2, AlertTriangle,
  RefreshCw, Eye, EyeOff, Globe
} from 'lucide-react';
import toast from 'react-hot-toast';
import { listAPIKeys, createAPIKey, revokeAPIKey, getAPIBase } from '../api/client';

export default function APIKeysPage() {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newKeyName, setNewKeyName] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState(null);

  const fetchKeys = async () => {
    try {
      const data = await listAPIKeys();
      setKeys(data);
    } catch (err) {
      toast.error('Failed to load API keys');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchKeys(); }, []);

  const handleCreate = async () => {
    try {
      const data = await createAPIKey(newKeyName || 'Default Key');
      setNewlyCreatedKey(data.full_key);
      setNewKeyName('');
      setShowCreate(false);
      fetchKeys();
      toast.success('API key created!');
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleRevoke = async (keyId, prefix) => {
    if (!confirm(`Revoke key ${prefix}...? This cannot be undone.`)) return;
    try {
      await revokeAPIKey(keyId);
      fetchKeys();
      toast.success('API key revoked');
    } catch (err) {
      toast.error(err.message);
    }
  };

  const activeKey = keys.find(k => k.is_active);
  const widgetCode = activeKey
    ? `<script src="${getAPIBase()}/widget.js" data-api-key="${activeKey.key_prefix}..." data-api-url="${getAPIBase()}"></script>`
    : null;

  const actualWidgetCode = newlyCreatedKey
    ? `<script src="${getAPIBase()}/widget.js" data-api-key="${newlyCreatedKey}" data-api-url="${getAPIBase()}"></script>`
    : null;

  return (
    <>
      <div className="page-header">
        <h2>API Keys & Widget</h2>
        <p>Manage API keys and get your embeddable chat widget code</p>
      </div>

      <div className="page-body">
        {/* Newly Created Key Alert */}
        {newlyCreatedKey && (
          <div className="key-reveal-banner">
            <div className="key-reveal-header">
              <CheckCircle2 size={20} />
              <strong>New API Key Created</strong>
            </div>
            <p className="key-reveal-warning">
              Save this key now — it won't be shown again.
            </p>
            <div className="key-reveal-box">
              <code>{newlyCreatedKey}</code>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  navigator.clipboard.writeText(newlyCreatedKey);
                  toast.success('Key copied!');
                }}
              >
                <Copy size={14} /> Copy
              </button>
            </div>

            {/* Widget Code */}
            <div className="widget-code-section">
              <h4><Code size={16} /> Your Widget Code</h4>
              <p>Add this single line to your website's HTML to deploy the chat assistant:</p>
              <div className="widget-code-box">
                <code>{actualWidgetCode}</code>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    navigator.clipboard.writeText(actualWidgetCode);
                    toast.success('Widget code copied!');
                  }}
                >
                  <Copy size={14} /> Copy
                </button>
              </div>
            </div>

            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setNewlyCreatedKey(null)}
              style={{ marginTop: '12px' }}
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Widget Code (for existing keys) */}
        {!newlyCreatedKey && activeKey && (
          <div className="widget-embed-card">
            <div className="widget-embed-header">
              <Globe size={20} />
              <div>
                <h3>Embeddable Widget</h3>
                <p>Add this script tag to your website to deploy the AI chat assistant</p>
              </div>
            </div>
            <div className="widget-code-box">
              <code>{widgetCode}</code>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  navigator.clipboard.writeText(widgetCode);
                  toast.success('Widget code copied!');
                }}
              >
                <Copy size={14} /> Copy
              </button>
            </div>
            <p className="widget-note">
              <AlertTriangle size={12} /> Replace the key prefix with your full API key.
              You can find it in your key creation confirmation.
            </p>
          </div>
        )}

        {/* Keys List */}
        <div className="keys-header">
          <h3><Key size={18} /> Your API Keys</h3>
          <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(!showCreate)}>
            <Plus size={14} /> New Key
          </button>
        </div>

        {showCreate && (
          <div className="key-create-form">
            <input
              type="text"
              placeholder="Key name (e.g. Production, Staging)"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              className="key-name-input"
            />
            <button className="btn btn-primary btn-sm" onClick={handleCreate}>Create</button>
            <button className="btn btn-secondary btn-sm" onClick={() => setShowCreate(false)}>Cancel</button>
          </div>
        )}

        <div className="keys-list">
          {loading ? (
            <div className="keys-loading"><div className="spinner" /> Loading...</div>
          ) : keys.length === 0 ? (
            <div className="keys-empty">
              <Key size={32} />
              <p>No API keys yet. Create one to get started.</p>
            </div>
          ) : (
            keys.map((key) => (
              <div key={key.id} className={`key-row ${!key.is_active ? 'revoked' : ''}`}>
                <div className="key-row-left">
                  <Key size={16} />
                  <div>
                    <div className="key-name">{key.name}</div>
                    <div className="key-prefix">{key.key_prefix}...</div>
                  </div>
                </div>
                <div className="key-row-right">
                  <span className={`key-status ${key.is_active ? 'active' : 'revoked'}`}>
                    {key.is_active ? '● Active' : '○ Revoked'}
                  </span>
                  <span className="key-usage">{key.usage_count} uses</span>
                  <span className="key-date">
                    {new Date(key.created_at).toLocaleDateString()}
                  </span>
                  {key.is_active && (
                    <button
                      className="btn btn-danger btn-sm btn-icon"
                      onClick={() => handleRevoke(key.id, key.key_prefix)}
                      title="Revoke key"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </>
  );
}
