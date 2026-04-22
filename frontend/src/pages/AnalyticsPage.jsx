import { useState, useEffect, useCallback } from 'react';
import {
  BarChart3, MessageCircle, Mic, AlertTriangle, Clock,
  RefreshCw, Filter, ChevronDown, ChevronRight, Zap,
  Activity, XCircle, CheckCircle2, Trash2
} from 'lucide-react';
import toast from 'react-hot-toast';
import { getAnalyticsConversations, getAnalyticsSummary, clearAnalytics } from '../api/client';

function formatMs(ms) {
  if (ms === null || ms === undefined) return '—';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function formatTimestamp(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

function LatencyBar({ label, value, maxValue, color }) {
  const pct = maxValue > 0 && value != null ? Math.min((value / maxValue) * 100, 100) : 0;
  return (
    <div className="latency-bar-row">
      <span className="latency-bar-label">{label}</span>
      <div className="latency-bar-track">
        <div
          className="latency-bar-fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="latency-bar-value">{formatMs(value)}</span>
    </div>
  );
}

function ConversationRow({ entry }) {
  const [expanded, setExpanded] = useState(false);
  const hasErrors = entry.errors && entry.errors.length > 0;
  const lat = entry.latency || {};

  const maxLat = Math.max(
    lat.stt_transcription_ms || 0,
    lat.retrieval_ms || 0,
    lat.llm_generation_ms || 0,
    lat.tts_first_audio_ms || 0,
    1
  );

  return (
    <div className={`analytics-row ${hasErrors ? 'has-error' : ''}`}>
      <div className="analytics-row-header" onClick={() => setExpanded(!expanded)}>
        <div className="analytics-row-left">
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          <span className={`mode-badge ${entry.mode}`}>
            {entry.mode === 'voice' ? <Mic size={12} /> : <MessageCircle size={12} />}
            {entry.mode}
          </span>
          <span className="analytics-query">{entry.user_query || '—'}</span>
        </div>
        <div className="analytics-row-right">
          {hasErrors && (
            <span className="error-indicator">
              <AlertTriangle size={13} />
            </span>
          )}
          <span className={`status-badge ${entry.status}`}>
            {entry.status === 'success' ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
            {entry.status}
          </span>
          <span className="analytics-latency-badge">
            <Clock size={12} />
            {formatMs(lat.total_round_trip_ms)}
          </span>
          <span className="analytics-time">{formatTimestamp(entry.timestamp)}</span>
        </div>
      </div>

      {expanded && (
        <div className="analytics-row-detail">
          <div className="detail-columns">
            {/* Left: Query & Response */}
            <div className="detail-text">
              <div className="detail-section">
                <div className="detail-section-label">User Query</div>
                <div className="detail-section-content">{entry.user_query || '—'}</div>
              </div>
              <div className="detail-section">
                <div className="detail-section-label">AI Response</div>
                <div className="detail-section-content ai-response-text">
                  {entry.ai_response
                    ? (entry.ai_response.length > 300
                      ? entry.ai_response.slice(0, 300) + '…'
                      : entry.ai_response)
                    : '—'}
                </div>
              </div>
              {hasErrors && (
                <div className="detail-section">
                  <div className="detail-section-label error-label">
                    <AlertTriangle size={13} /> Errors
                  </div>
                  <div className="detail-errors">
                    {entry.errors.map((err, i) => (
                      <div key={i} className="error-item">{err}</div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Right: Latency Breakdown */}
            <div className="detail-latency">
              <div className="detail-section-label">Pipeline Latency</div>
              <div className="latency-breakdown">
                {entry.mode === 'voice' && (
                  <LatencyBar
                    label="STT"
                    value={lat.stt_transcription_ms}
                    maxValue={maxLat}
                    color="var(--accent-warning)"
                  />
                )}
                <LatencyBar
                  label="Retrieval"
                  value={lat.retrieval_ms}
                  maxValue={maxLat}
                  color="var(--accent-secondary)"
                />
                <LatencyBar
                  label="LLM"
                  value={lat.llm_generation_ms}
                  maxValue={maxLat}
                  color="var(--accent-primary)"
                />
                {entry.mode === 'voice' && (
                  <LatencyBar
                    label="TTS (1st)"
                    value={lat.tts_first_audio_ms}
                    maxValue={maxLat}
                    color="var(--accent-success)"
                  />
                )}
                <div className="latency-total">
                  <Zap size={13} />
                  Total: {formatMs(lat.total_round_trip_ms)}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


export default function AnalyticsPage() {
  const [summary, setSummary] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [modeFilter, setModeFilter] = useState(null);
  const [statusFilter, setStatusFilter] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [sumRes, convRes] = await Promise.all([
        getAnalyticsSummary(),
        getAnalyticsConversations(modeFilter, statusFilter),
      ]);
      setSummary(sumRes);
      setConversations(convRes.entries || []);
      setTotal(convRes.total || 0);
    } catch (err) {
      console.error('Analytics fetch failed:', err);
    } finally {
      setLoading(false);
    }
  }, [modeFilter, statusFilter]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 8000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleClear = async () => {
    if (!confirm('Clear all analytics data? This cannot be undone.')) return;
    try {
      await clearAnalytics();
      toast.success('Analytics data cleared');
      fetchData();
    } catch (err) {
      toast.error('Failed to clear analytics');
    }
  };

  const stats = summary || {};

  return (
    <>
      <div className="page-header analytics-page-header">
        <div className="analytics-header-top">
          <div>
            <h2>Analytics</h2>
            <p>Monitor conversations, latency, and errors across all interactions</p>
          </div>
          <div className="analytics-header-actions">
            <button className="btn btn-secondary btn-sm" onClick={fetchData} disabled={loading}>
              <RefreshCw size={14} className={loading ? 'spinning' : ''} />
              Refresh
            </button>
            <button className="btn btn-danger btn-sm" onClick={handleClear} disabled={loading}>
              <Trash2 size={14} />
              Clear
            </button>
          </div>
        </div>
      </div>

      <div className="page-body">
        {/* Summary Cards */}
        <div className="analytics-cards">
          <div className="analytics-card">
            <div className="analytics-card-icon total">
              <Activity size={20} />
            </div>
            <div className="analytics-card-body">
              <div className="analytics-card-value">{stats.total_conversations ?? 0}</div>
              <div className="analytics-card-label">Total Interactions</div>
            </div>
          </div>

          <div className="analytics-card">
            <div className="analytics-card-icon chat">
              <MessageCircle size={20} />
            </div>
            <div className="analytics-card-body">
              <div className="analytics-card-value">{stats.chat_count ?? 0}</div>
              <div className="analytics-card-label">Chat Sessions</div>
            </div>
          </div>

          <div className="analytics-card">
            <div className="analytics-card-icon voice">
              <Mic size={20} />
            </div>
            <div className="analytics-card-body">
              <div className="analytics-card-value">{stats.voice_count ?? 0}</div>
              <div className="analytics-card-label">Voice Sessions</div>
            </div>
          </div>

          <div className="analytics-card">
            <div className="analytics-card-icon errors">
              <AlertTriangle size={20} />
            </div>
            <div className="analytics-card-body">
              <div className="analytics-card-value">{stats.error_count ?? 0}</div>
              <div className="analytics-card-label">Errors</div>
            </div>
          </div>
        </div>

        {/* Latency Summary */}
        <div className="analytics-latency-summary">
          <h3><Clock size={16} /> Average Latency</h3>
          <div className="latency-summary-grid">
            <div className="latency-stat">
              <span className="latency-stat-value">{formatMs(stats.avg_stt_ms)}</span>
              <span className="latency-stat-label">Speech to Text</span>
            </div>
            <div className="latency-stat">
              <span className="latency-stat-value">{formatMs(stats.avg_retrieval_ms)}</span>
              <span className="latency-stat-label">Vector Retrieval</span>
            </div>
            <div className="latency-stat">
              <span className="latency-stat-value">{formatMs(stats.avg_llm_ms)}</span>
              <span className="latency-stat-label">LLM Generation</span>
            </div>
            <div className="latency-stat">
              <span className="latency-stat-value">{formatMs(stats.avg_tts_ms)}</span>
              <span className="latency-stat-label">Text to Speech</span>
            </div>
            <div className="latency-stat total">
              <span className="latency-stat-value">{formatMs(stats.avg_latency_ms)}</span>
              <span className="latency-stat-label">Total Round Trip</span>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="analytics-filters">
          <div className="filter-group">
            <Filter size={14} />
            <span>Filter:</span>
            <button
              className={`filter-btn ${modeFilter === null ? 'active' : ''}`}
              onClick={() => setModeFilter(null)}
            >All</button>
            <button
              className={`filter-btn ${modeFilter === 'chat' ? 'active' : ''}`}
              onClick={() => setModeFilter('chat')}
            ><MessageCircle size={12} /> Chat</button>
            <button
              className={`filter-btn ${modeFilter === 'voice' ? 'active' : ''}`}
              onClick={() => setModeFilter('voice')}
            ><Mic size={12} /> Voice</button>
          </div>
          <div className="filter-group">
            <button
              className={`filter-btn ${statusFilter === null ? 'active' : ''}`}
              onClick={() => setStatusFilter(null)}
            >All Status</button>
            <button
              className={`filter-btn ${statusFilter === 'success' ? 'active' : ''}`}
              onClick={() => setStatusFilter('success')}
            ><CheckCircle2 size={12} /> Success</button>
            <button
              className={`filter-btn ${statusFilter === 'error' ? 'active' : ''}`}
              onClick={() => setStatusFilter('error')}
            ><XCircle size={12} /> Errors</button>
          </div>
          <span className="filter-count">{total} results</span>
        </div>

        {/* Conversation List */}
        <div className="analytics-list">
          {loading && conversations.length === 0 ? (
            <div className="analytics-empty">
              <div className="spinner" />
              <p>Loading analytics...</p>
            </div>
          ) : conversations.length === 0 ? (
            <div className="analytics-empty">
              <BarChart3 size={40} />
              <h3>No data yet</h3>
              <p>Start a chat or voice conversation to see analytics here.</p>
            </div>
          ) : (
            conversations.map((entry) => (
              <ConversationRow key={entry.id} entry={entry} />
            ))
          )}
        </div>
      </div>
    </>
  );
}
