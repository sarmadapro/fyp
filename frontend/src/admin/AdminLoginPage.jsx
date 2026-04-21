import { useState } from 'react';
import { Shield, Mail, Lock, Eye, EyeOff, Loader } from 'lucide-react';
import toast from 'react-hot-toast';
import { adminLogin } from '../api/admin';

export default function AdminLoginPage({ onLoginSuccess }) {
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw]     = useState(false);
  const [loading, setLoading]   = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) { toast.error('Enter email and password'); return; }
    setLoading(true);
    try {
      await adminLogin(email, password);
      toast.success('Welcome back, Admin');
      onLoginSuccess();
    } catch (err) {
      toast.error(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="admin-login-root">
      <div className="admin-login-card">
        {/* Brand */}
        <div className="admin-login-brand">
          <div className="admin-login-icon">
            <Shield size={28} />
          </div>
          <div>
            <h1 className="admin-login-title">Admin Console</h1>
            <p className="admin-login-sub">VoiceRAG Platform Management</p>
          </div>
        </div>

        <div className="admin-login-divider" />

        <form onSubmit={handleSubmit} className="admin-login-form">
          <div className="admin-field">
            <label className="admin-label">Email</label>
            <div className="admin-input-wrap">
              <Mail size={16} className="admin-input-icon" />
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="admin@example.com"
                className="admin-input"
                autoFocus
              />
            </div>
          </div>

          <div className="admin-field">
            <label className="admin-label">Password</label>
            <div className="admin-input-wrap">
              <Lock size={16} className="admin-input-icon" />
              <input
                type={showPw ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                className="admin-input"
              />
              <button type="button" className="admin-input-toggle" onClick={() => setShowPw(!showPw)}>
                {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>

          <button type="submit" className="admin-btn-primary admin-login-btn" disabled={loading}>
            {loading ? <Loader size={16} className="admin-spin" /> : <Shield size={16} />}
            {loading ? 'Authenticating…' : 'Sign In as Admin'}
          </button>
        </form>

        <p className="admin-login-footer">
          Admin access only. Regular users should use the{' '}
          <button className="admin-link" onClick={() => window.location.hash = ''}>
            client portal
          </button>.
        </p>
      </div>
    </div>
  );
}
