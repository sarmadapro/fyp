import { useState } from 'react';
import { Mic, ArrowLeft, Eye, EyeOff, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { register, login } from '../api/client';

export default function AuthPage({ onNavigate, onAuthSuccess }) {
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [fullName, setFullName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [generatedKey, setGeneratedKey] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (mode === 'register') {
        const data = await register(email, password, companyName, fullName);
        setGeneratedKey(data.client?.api_key || null);
        toast.success('Account created successfully!');
        if (!data.client?.api_key) {
          onAuthSuccess(data);
        }
      } else {
        const data = await login(email, password);
        toast.success('Welcome back!');
        onAuthSuccess(data);
      }
    } catch (err) {
      toast.error(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  // Show API key screen after registration
  if (generatedKey) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <div className="auth-brand">
            <div className="landing-brand-icon"><Mic size={18} /></div>
            <span>VoiceRAG</span>
          </div>
          <div className="auth-key-reveal">
            <h2>🎉 Account Created!</h2>
            <p className="auth-key-warning">
              Your API key has been generated. Save it now — it won't be shown again.
            </p>
            <div className="auth-key-box">
              <code>{generatedKey}</code>
            </div>
            <button
              className="btn btn-secondary"
              onClick={() => {
                navigator.clipboard.writeText(generatedKey);
                toast.success('API key copied!');
              }}
            >
              Copy to Clipboard
            </button>
            <button
              className="btn btn-primary"
              style={{ marginTop: '12px' }}
              onClick={() => onAuthSuccess({ access_token: localStorage.getItem('voicerag_token') })}
            >
              Go to Dashboard →
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <button className="auth-back" onClick={() => onNavigate('landing')}>
          <ArrowLeft size={16} /> Back
        </button>

        <div className="auth-brand">
          <div className="landing-brand-icon"><Mic size={18} /></div>
          <span>VoiceRAG</span>
        </div>

        <h2>{mode === 'login' ? 'Welcome Back' : 'Create Account'}</h2>
        <p className="auth-sub">
          {mode === 'login'
            ? 'Sign in to your portal'
            : 'Start deploying your AI assistant'}
        </p>

        <form onSubmit={handleSubmit} className="auth-form">
          {mode === 'register' && (
            <>
              <div className="form-group">
                <label>Company Name</label>
                <input
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="Acme Inc."
                  required
                  autoComplete="organization"
                />
              </div>
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="John Doe"
                  autoComplete="name"
                />
              </div>
            </>
          )}

          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <div className="password-input">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min 6 characters"
                required
                minLength={6}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button type="submit" className="btn btn-primary auth-submit" disabled={loading}>
            {loading ? (
              <><Loader2 size={16} className="spinning" /> Processing...</>
            ) : (
              mode === 'login' ? 'Sign In' : 'Create Account'
            )}
          </button>
        </form>

        <div className="auth-switch">
          {mode === 'login' ? (
            <p>Don't have an account? <button onClick={() => setMode('register')}>Sign up</button></p>
          ) : (
            <p>Already have an account? <button onClick={() => setMode('login')}>Sign in</button></p>
          )}
        </div>
      </div>
    </div>
  );
}
