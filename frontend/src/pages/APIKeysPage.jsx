import { useState, useEffect } from 'react';
import { Key, Copy, Code, Globe, RefreshCw, AlertTriangle, CheckCircle2, Eye, EyeOff } from 'lucide-react';
import toast from 'react-hot-toast';
import { listAPIKeys, regenerateEmbedKey, getAPIBase } from '../api/client';

export default function APIKeysPage() {
  const [embedKey, setEmbedKey]       = useState(null);   // KeyResponse (prefix only)
  const [newFullKey, setNewFullKey]    = useState(null);   // shown once after regenerate
  const [loading, setLoading]         = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [showKey, setShowKey]         = useState(false);

  const fetchKey = async () => {
    try {
      const keys = await listAPIKeys();
      setEmbedKey(keys.find(k => k.is_active) || null);
    } catch {
      toast.error('Failed to load embed key');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchKey(); }, []);

  const handleRegenerate = async () => {
    setShowConfirm(false);
    setRegenerating(true);
    try {
      const data = await regenerateEmbedKey();
      setNewFullKey(data.full_key);
      setEmbedKey({ ...data, full_key: undefined });
      setShowKey(true);
      toast.success('New embed key generated');
    } catch (err) {
      toast.error(err.message);
    } finally {
      setRegenerating(false);
    }
  };

  const copy = (text, label = 'Copied!') => {
    navigator.clipboard.writeText(text);
    toast.success(label);
  };

  const displayKey    = newFullKey || (embedKey ? `${embedKey.key_prefix}${'•'.repeat(24)}` : null);
  const copyableKey   = newFullKey || (embedKey?.key_prefix + '...');
  const widgetScript  = newFullKey
    ? `<script src="${getAPIBase()}/widget.js" data-api-key="${newFullKey}" data-api-url="${getAPIBase()}"></script>`
    : embedKey
    ? `<script src="${getAPIBase()}/widget.js" data-api-key="${embedKey.key_prefix}..." data-api-url="${getAPIBase()}"></script>`
    : null;

  return (
    <>
      <div className="page-header">
        <h2>Website Embed Key</h2>
        <p>Your unique key for embedding the AI assistant on your website</p>
      </div>

      <div className="page-body">
        {loading ? (
          <div className="keys-loading"><div className="spinner" /> Loading…</div>
        ) : (
          <>
            {/* One-time reveal banner */}
            {newFullKey && (
              <div className="key-reveal-banner">
                <div className="key-reveal-header">
                  <CheckCircle2 size={20} />
                  <strong>New Embed Key Generated</strong>
                </div>
                <p className="key-reveal-warning">
                  Save this key now — it will not be shown again after you leave this page.
                </p>
              </div>
            )}

            {/* Key Card */}
            <div className="embed-key-card">
              <div className="embed-key-header">
                <Key size={20} />
                <div>
                  <h3>Embed Key</h3>
                  <p>{embedKey ? `Created ${new Date(embedKey.created_at).toLocaleDateString()} · ${embedKey.usage_count.toLocaleString()} requests` : 'No active key'}</p>
                </div>
                <span className={`key-status ${embedKey ? 'active' : 'revoked'}`}>
                  {embedKey ? '● Active' : '○ None'}
                </span>
              </div>

              {embedKey ? (
                <div className="embed-key-value-row">
                  <code className="embed-key-value">
                    {showKey ? (newFullKey || displayKey) : `${embedKey.key_prefix}${'•'.repeat(24)}`}
                  </code>
                  <button className="btn btn-secondary btn-sm btn-icon" onClick={() => setShowKey(s => !s)} title={showKey ? 'Hide' : 'Reveal'}>
                    {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                  <button className="btn btn-secondary btn-sm" onClick={() => copy(copyableKey, 'Key copied!')}>
                    <Copy size={14} /> Copy
                  </button>
                </div>
              ) : (
                <p className="embed-key-empty">No active embed key. Generate one below.</p>
              )}

              {!newFullKey && embedKey && (
                <p className="embed-key-note">
                  <AlertTriangle size={12} />
                  The full key was shown once when first generated. Use Regenerate to get a new one.
                </p>
              )}

              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setShowConfirm(true)}
                disabled={regenerating}
                style={{ marginTop: '12px', alignSelf: 'flex-start' }}
              >
                <RefreshCw size={14} className={regenerating ? 'spin' : ''} />
                {regenerating ? 'Generating…' : embedKey ? 'Regenerate Key' : 'Generate Key'}
              </button>
            </div>

            {/* Embed Code */}
            {embedKey && (
              <div className="widget-embed-card">
                <div className="widget-embed-header">
                  <Globe size={20} />
                  <div>
                    <h3>Embed Code</h3>
                    <p>Add this script tag to your website to deploy the AI chat assistant</p>
                  </div>
                </div>
                <div className="widget-code-box">
                  <code>{widgetScript}</code>
                  <button className="btn btn-secondary btn-sm" onClick={() => copy(widgetScript, 'Embed code copied!')}>
                    <Copy size={14} /> Copy
                  </button>
                </div>
                {!newFullKey && (
                  <p className="widget-note">
                    <AlertTriangle size={12} /> Replace <code>...</code> in the key with your full embed key (shown at generation time). Or regenerate to get a new full key.
                  </p>
                )}
              </div>
            )}

            {/* How it works */}
            <div className="how-it-works">
              <h4><Code size={16} /> How it works</h4>
              <ol>
                <li>Copy the embed code above and paste it into your website's HTML (before <code>&lt;/body&gt;</code>).</li>
                <li>The widget loads automatically and routes all visitor interactions to your isolated AI knowledge base.</li>
                <li>Use <strong>Regenerate Key</strong> if your key is compromised — the old key is revoked instantly.</li>
              </ol>
            </div>
          </>
        )}
      </div>

      {/* Confirm Regenerate Dialog */}
      {showConfirm && (
        <div className="modal-overlay" onClick={() => setShowConfirm(false)}>
          <div className="modal-box" onClick={e => e.stopPropagation()}>
            <div className="modal-icon warning"><AlertTriangle size={24} /></div>
            <h3>{embedKey ? 'Regenerate Embed Key?' : 'Generate Embed Key?'}</h3>
            {embedKey && (
              <p>The current key will be <strong>revoked immediately</strong>. Any website using the old key will stop working until updated.</p>
            )}
            {!embedKey && <p>A new embed key will be generated for your account.</p>}
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowConfirm(false)}>Cancel</button>
              <button className="btn btn-danger" onClick={handleRegenerate}>
                {embedKey ? 'Revoke & Regenerate' : 'Generate'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
