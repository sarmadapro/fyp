import { useState, useEffect } from 'react';
import {
  Activity, CheckCircle, XCircle, AlertCircle,
  Server, Cpu, Database, Mic, Volume2, Brain,
  RefreshCw, Users, Key, Zap
} from 'lucide-react';
import { adminGetSystemHealth } from '../api/admin';

const SERVICE_ICONS = {
  'Backend API': Server,
  'LLM':         Brain,
  'STT':         Mic,
  'TTS':         Volume2,
  'Database':    Database,
};

const STATUS_CONFIG = {
  ok:       { color: '#51cf66', bg: 'rgba(81,207,102,0.1)',  icon: CheckCircle,   label: 'Healthy'  },
  degraded: { color: '#ffd43b', bg: 'rgba(255,212,59,0.1)', icon: AlertCircle,   label: 'Degraded' },
  down:     { color: '#ff6b6b', bg: 'rgba(255,107,107,0.1)',icon: XCircle,       label: 'Down'     },
};

function ServiceCard({ service }) {
  const cfg    = STATUS_CONFIG[service.status] || STATUS_CONFIG.degraded;
  const Icon   = SERVICE_ICONS[service.name] || Server;
  const Status = cfg.icon;

  // detail can be a string or a dict from the health endpoint — always stringify
  const detail = service.detail
    ? (typeof service.detail === 'object' ? JSON.stringify(service.detail) : service.detail)
    : '—';

  return (
    <div className="admin-service-card" style={{ borderColor: `${cfg.color}33` }}>
      <div className="admin-service-icon" style={{ background: cfg.bg, color: cfg.color }}>
        <Icon size={22} />
      </div>
      <div className="admin-service-body">
        <div className="admin-service-name">{service.name}</div>
        <div className="admin-service-detail">{detail}</div>
      </div>
      <div className="admin-service-status" style={{ color: cfg.color }}>
        <Status size={16} />
        <span>{cfg.label}</span>
      </div>
    </div>
  );
}

function MetricTile({ icon: Icon, label, value, color }) {
  return (
    <div className="admin-metric-tile">
      <div className="admin-metric-icon" style={{ color: color || 'var(--admin-accent)' }}>
        <Icon size={18} />
      </div>
      <div className="admin-metric-value">{value ?? '—'}</div>
      <div className="admin-metric-label">{label}</div>
    </div>
  );
}

export default function AdminSystemPage() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const res = await adminGetSystemHealth();
      setData(res);
      setLastRefresh(new Date());
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const services = data?.services  || [];
  const platform = data?.platform  || {};

  const allOk     = services.length > 0 && services.every(s => s.status === 'ok');
  const anyDown   = services.some(s => s.status === 'down');
  const overallStatus = anyDown ? 'down' : allOk ? 'ok' : 'degraded';
  const overallCfg    = STATUS_CONFIG[overallStatus];
  const OverallIcon   = overallCfg.icon;

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">System Health</h1>
          <p className="admin-page-desc">
            Live status of all platform services
            {lastRefresh && ` — Last checked: ${lastRefresh.toLocaleTimeString()}`}
          </p>
        </div>
        <button className="admin-btn-secondary admin-btn-sm" onClick={load} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spinning' : ''} />
          Refresh
        </button>
      </div>

      {/* Overall status banner */}
      <div className="admin-overall-status" style={{ background: overallCfg.bg, borderColor: `${overallCfg.color}44` }}>
        <OverallIcon size={20} style={{ color: overallCfg.color }} />
        <div>
          <div className="admin-overall-label" style={{ color: overallCfg.color }}>
            {overallStatus === 'ok' ? 'All Systems Operational' : overallStatus === 'down' ? 'Service Outage Detected' : 'Partial Degradation'}
          </div>
          <div className="admin-overall-sub">
            {services.filter(s => s.status === 'ok').length}/{services.length} services healthy
          </div>
        </div>
      </div>

      {/* Service cards */}
      {loading ? (
        <div className="admin-page-loading"><div className="admin-spinner" /></div>
      ) : (
        <>
          <div className="admin-services-grid">
            {services.map((s, i) => <ServiceCard key={i} service={s} />)}
          </div>

          {/* Platform metrics */}
          <div className="admin-panel" style={{ marginTop: '1.5rem' }}>
            <div className="admin-panel-header">
              <Activity size={16} />
              <h3>Platform Metrics</h3>
            </div>
            <div className="admin-metrics-grid">
              <MetricTile icon={Users} label="Total Users"     value={platform.total_users?.toLocaleString()} />
              <MetricTile icon={Key}   label="API Keys"        value={platform.total_api_keys?.toLocaleString()} />
              <MetricTile icon={Zap}   label="Total API Calls" value={platform.total_api_calls?.toLocaleString()} color="#ffd43b" />
            </div>
          </div>

          {/* Config info */}
          <div className="admin-panel" style={{ marginTop: '1rem' }}>
            <div className="admin-panel-header">
              <Cpu size={16} />
              <h3>Configuration</h3>
            </div>
            <div className="admin-config-grid">
              {[
                { label: 'LLM Provider',    value: platform.llm_provider },
                { label: 'LLM Model',       value: platform.llm_model },
                { label: 'Embedding Model', value: platform.embedding_model },
                { label: 'STT Service',     value: platform.stt_url },
                { label: 'TTS Service',     value: platform.tts_url },
              ].map(({ label, value }) => (
                <div key={label} className="admin-config-row">
                  <span className="admin-config-label">{label}</span>
                  <code className="admin-config-value">{value || '—'}</code>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
