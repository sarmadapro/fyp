import { useState, useEffect } from 'react';
import {
  MessageSquare, Mic, CheckCircle, XCircle, ChevronDown, ChevronUp,
  Zap, Clock, User, ArrowLeft, AlertTriangle,
} from 'lucide-react';
import { adminGetConversations, adminGetUserStats } from '../api/admin';

// ─── Latency bar ─────────────────────────────────────────────────────────────

function LatencyBar({ label, ms, max, color }) {
  const pct = max > 0 ? Math.min((ms / max) * 100, 100) : 0;
  return (
    <div className="admin-latency-row">
      <span className="admin-latency-label">{label}</span>
      <div className="admin-latency-track">
        <div className="admin-latency-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="admin-latency-val">{ms ? `${Math.round(ms)}ms` : '—'}</span>
    </div>
  );
}

// ─── Individual conversation row ─────────────────────────────────────────────

function ConvRow({ conv }) {
  const [open, setOpen] = useState(false);
  const isVoice  = conv.mode === 'voice';
  const isError  = conv.status === 'error';
  const ModeIcon = isVoice ? Mic : MessageSquare;

  const lat    = conv.latency || {};
  const total  = lat.total_round_trip_ms;
  const sttMs  = lat.stt_transcription_ms;
  const retMs  = lat.retrieval_ms;
  const llmMs  = lat.llm_generation_ms;
  const ttsMs  = lat.tts_first_audio_ms;
  const maxMs  = Math.max(sttMs || 0, retMs || 0, llmMs || 0, ttsMs || 0, 1);

  return (
    <div className={`admin-conv-row ${isError ? 'has-error' : ''}`}>
      <div className="admin-conv-header" onClick={() => setOpen(o => !o)}>
        <div className="admin-conv-left">
          <ModeIcon size={14} className={isVoice ? 'icon-voice' : 'icon-chat'} />
          <span className="admin-conv-query">{conv.user_query || '(empty)'}</span>
        </div>
        <div className="admin-conv-right">
          {total != null && (
            <span className="admin-conv-latency">
              <Zap size={11} /> {Math.round(total)}ms
            </span>
          )}
          <span className={`admin-badge ${isError ? 'badge-danger' : 'badge-success'}`}>
            {isError ? <XCircle size={10} /> : <CheckCircle size={10} />}
            {conv.status}
          </span>
          <span className="admin-conv-time">
            {conv.timestamp ? new Date(conv.timestamp).toLocaleString() : '—'}
          </span>
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>

      {open && (
        <div className="admin-conv-detail">
          <div className="admin-conv-detail-cols">
            <div>
              <div className="admin-detail-label">User Query</div>
              <div className="admin-detail-value">{conv.user_query || '—'}</div>

              {conv.ai_response && (
                <>
                  <div className="admin-detail-label" style={{ marginTop: '0.75rem' }}>AI Response</div>
                  <div className="admin-detail-value admin-muted">{conv.ai_response}</div>
                </>
              )}

              {conv.errors?.length > 0 && (
                <>
                  <div className="admin-detail-label error" style={{ marginTop: '0.75rem' }}>Errors</div>
                  {conv.errors.map((e, i) => (
                    <div key={i} className="admin-error-chip">{e}</div>
                  ))}
                </>
              )}
            </div>

            <div className="admin-conv-latency-block">
              <div className="admin-detail-label">Latency Breakdown</div>
              {sttMs  > 0 && <LatencyBar label="STT"       ms={sttMs}  max={maxMs} color="#6c5ce7" />}
              {retMs  > 0 && <LatencyBar label="Retrieval" ms={retMs}  max={maxMs} color="#00cec9" />}
              {llmMs  > 0 && <LatencyBar label="LLM"       ms={llmMs}  max={maxMs} color="#e17055" />}
              {ttsMs  > 0 && <LatencyBar label="TTS"       ms={ttsMs}  max={maxMs} color="#55efc4" />}
              {total  != null && (
                <div className="admin-latency-total">
                  <Zap size={12} /> Total: {Math.round(total)}ms
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Per-user stats row ───────────────────────────────────────────────────────

function UserStatsRow({ user, onDrillDown }) {
  const errRate = user.total_conversations > 0
    ? ((user.error_count / user.total_conversations) * 100).toFixed(1)
    : '0.0';
  const hasErrors = user.error_count > 0;

  return (
    <tr
      className="admin-user-conv-row"
      onClick={() => onDrillDown(user)}
      title="Click to view conversations"
    >
      <td>
        <div className="admin-user-conv-identity">
          <div className="admin-user-avatar-sm">
            {(user.email || user.client_id || '?')[0].toUpperCase()}
          </div>
          <div>
            <div className="admin-user-conv-email">{user.email || user.client_id}</div>
            {user.company_name && (
              <div className="admin-user-conv-company">{user.company_name}</div>
            )}
          </div>
        </div>
      </td>
      <td className="admin-td-center">{user.total_conversations}</td>
      <td className="admin-td-center">
        <span className="admin-conv-mode-badge chat">{user.chat_count}</span>
        {user.voice_count > 0 && (
          <span className="admin-conv-mode-badge voice" style={{ marginLeft: '0.35rem' }}>{user.voice_count}</span>
        )}
      </td>
      <td className="admin-td-center">
        {hasErrors ? (
          <span className="admin-badge badge-danger" style={{ gap: '0.25rem' }}>
            <AlertTriangle size={10} /> {user.error_count} ({errRate}%)
          </span>
        ) : (
          <span className="admin-badge badge-success"><CheckCircle size={10} /> 0</span>
        )}
      </td>
      <td className="admin-td-center">
        {user.avg_latency_ms > 0 ? (
          <span className="admin-conv-latency"><Zap size={11} /> {Math.round(user.avg_latency_ms)}ms</span>
        ) : '—'}
      </td>
      <td className="admin-td-right admin-muted" style={{ fontSize: '0.85em' }}>
        {user.last_seen ? new Date(user.last_seen).toLocaleString() : '—'}
      </td>
    </tr>
  );
}

// ─── Drill-down view: conversations for one user ──────────────────────────────

function UserDrillDown({ user, onBack }) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode]       = useState('');
  const [status, setStatus]   = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const res = await adminGetConversations({
        clientId: user.client_id,
        mode,
        status,
        limit: 100,
      });
      setData(res);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [mode, status]);

  const convs = data?.conversations || [];

  return (
    <div>
      {/* Header */}
      <div className="admin-page-header" style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button className="admin-btn-secondary admin-btn-sm" onClick={onBack} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <ArrowLeft size={14} /> All Users
          </button>
          <div>
            <h2 className="admin-page-title" style={{ fontSize: '1.15rem', marginBottom: '0.1rem' }}>
              {user.email || user.client_id}
            </h2>
            {user.company_name && (
              <p className="admin-page-desc" style={{ margin: 0 }}>{user.company_name}</p>
            )}
          </div>
        </div>
        <button className="admin-btn-secondary admin-btn-sm" onClick={load}>Refresh</button>
      </div>

      {/* Mini stats */}
      <div className="admin-stats-grid" style={{ marginBottom: '1rem' }}>
        <div className="admin-stat-card">
          <div className="admin-stat-icon-wrap"><MessageSquare size={18} /></div>
          <div className="admin-stat-body">
            <div className="admin-stat-value">{user.total_conversations}</div>
            <div className="admin-stat-label">Total Conversations</div>
          </div>
        </div>
        <div className="admin-stat-card">
          <div className="admin-stat-icon-wrap" style={{ background: 'rgba(108,92,231,0.12)', color: '#6c5ce7' }}>
            <MessageSquare size={18} />
          </div>
          <div className="admin-stat-body">
            <div className="admin-stat-value">{user.chat_count}</div>
            <div className="admin-stat-label">Chat</div>
          </div>
        </div>
        <div className="admin-stat-card">
          <div className="admin-stat-icon-wrap" style={{ background: 'rgba(0,206,201,0.12)', color: '#00cec9' }}>
            <Mic size={18} />
          </div>
          <div className="admin-stat-body">
            <div className="admin-stat-value">{user.voice_count}</div>
            <div className="admin-stat-label">Voice</div>
          </div>
        </div>
        <div className="admin-stat-card">
          <div className="admin-stat-icon-wrap" style={{ background: 'rgba(255,107,107,0.12)', color: '#ff6b6b' }}>
            <XCircle size={18} />
          </div>
          <div className="admin-stat-body">
            <div className="admin-stat-value">{user.error_count}</div>
            <div className="admin-stat-label">Errors</div>
          </div>
        </div>
        {user.avg_latency_ms > 0 && (
          <div className="admin-stat-card">
            <div className="admin-stat-icon-wrap" style={{ background: 'rgba(253,203,110,0.12)', color: '#fdcb6e' }}>
              <Zap size={18} />
            </div>
            <div className="admin-stat-body">
              <div className="admin-stat-value">{Math.round(user.avg_latency_ms)}ms</div>
              <div className="admin-stat-label">Avg Latency</div>
            </div>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="admin-filter-row">
        <div className="admin-filter-group">
          <span>Mode:</span>
          {['', 'chat', 'voice'].map(m => (
            <button key={m} className={`admin-filter-btn ${mode === m ? 'active' : ''}`} onClick={() => setMode(m)}>
              {m || 'All'}
            </button>
          ))}
        </div>
        <div className="admin-filter-group">
          <span>Status:</span>
          {['', 'success', 'error'].map(s => (
            <button key={s} className={`admin-filter-btn ${status === s ? 'active' : ''}`} onClick={() => setStatus(s)}>
              {s || 'All'}
            </button>
          ))}
        </div>
        <span className="admin-filter-count">{convs.length} shown</span>
      </div>

      {/* Conversation list */}
      {loading ? (
        <div className="admin-page-loading"><div className="admin-spinner" /></div>
      ) : convs.length === 0 ? (
        <div className="admin-empty">
          <MessageSquare size={36} />
          <p>No conversations found for this user with the current filters.</p>
        </div>
      ) : (
        <div className="admin-conv-list">
          {convs.map((c, i) => <ConvRow key={c.id || i} conv={c} />)}
        </div>
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function AdminConversationsPage() {
  const [userStats, setUserStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState(null);

  const loadStats = async () => {
    setStatsLoading(true);
    try {
      const res = await adminGetUserStats();
      setUserStats(res);
    } catch { /* ignore */ }
    finally { setStatsLoading(false); }
  };

  useEffect(() => { loadStats(); }, []);

  const users = userStats?.users || [];
  const totalConvs  = users.reduce((s, u) => s + u.total_conversations, 0);
  const totalErrors = users.reduce((s, u) => s + u.error_count, 0);

  // Drill-down into a specific user
  if (selectedUser) {
    return (
      <div className="admin-page">
        <UserDrillDown user={selectedUser} onBack={() => setSelectedUser(null)} />
      </div>
    );
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Conversations</h1>
          <p className="admin-page-desc">Per-user conversation analytics — click any row to drill down</p>
        </div>
        <button className="admin-btn-secondary admin-btn-sm" onClick={loadStats}>Refresh</button>
      </div>

      {/* Summary cards */}
      <div className="admin-stats-grid">
        <div className="admin-stat-card">
          <div className="admin-stat-icon-wrap"><User size={20} /></div>
          <div className="admin-stat-body">
            <div className="admin-stat-value">{users.length}</div>
            <div className="admin-stat-label">Active Users</div>
          </div>
        </div>
        <div className="admin-stat-card">
          <div className="admin-stat-icon-wrap" style={{ background: 'rgba(108,92,231,0.12)', color: '#6c5ce7' }}>
            <MessageSquare size={20} />
          </div>
          <div className="admin-stat-body">
            <div className="admin-stat-value">{totalConvs}</div>
            <div className="admin-stat-label">Total Conversations</div>
          </div>
        </div>
        <div className="admin-stat-card">
          <div className="admin-stat-icon-wrap" style={{ background: 'rgba(255,107,107,0.12)', color: '#ff6b6b' }}>
            <XCircle size={20} />
          </div>
          <div className="admin-stat-body">
            <div className="admin-stat-value">{totalErrors}</div>
            <div className="admin-stat-label">Total Errors</div>
            {totalConvs > 0 && (
              <div className="admin-stat-sub">{((totalErrors / totalConvs) * 100).toFixed(1)}% error rate</div>
            )}
          </div>
        </div>
        <div className="admin-stat-card">
          <div className="admin-stat-icon-wrap" style={{ background: 'rgba(253,203,110,0.12)', color: '#fdcb6e' }}>
            <Clock size={20} />
          </div>
          <div className="admin-stat-body">
            <div className="admin-stat-value">
              {users.length > 0
                ? `${Math.round(users.reduce((s, u) => s + u.avg_latency_ms, 0) / users.filter(u => u.avg_latency_ms > 0).length || 0)}ms`
                : '—'}
            </div>
            <div className="admin-stat-label">Avg Latency</div>
          </div>
        </div>
      </div>

      {/* User table */}
      {statsLoading ? (
        <div className="admin-page-loading"><div className="admin-spinner" /></div>
      ) : users.length === 0 ? (
        <div className="admin-empty">
          <MessageSquare size={40} />
          <p>No conversations recorded yet. Start chatting or using voice to see entries here.</p>
        </div>
      ) : (
        <div className="admin-panel" style={{ marginTop: '0' }}>
          <div className="admin-panel-header">
            <User size={16} />
            <h3>Users ({users.length})</h3>
          </div>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th className="admin-td-center">Conversations</th>
                  <th className="admin-td-center">Chat / Voice</th>
                  <th className="admin-td-center">Errors</th>
                  <th className="admin-td-center">Avg Latency</th>
                  <th className="admin-td-right">Last Active</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u, i) => (
                  <UserStatsRow key={u.client_id || i} user={u} onDrillDown={setSelectedUser} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
