import { useState } from 'react';
import { Mic, ArrowLeft, Eye, EyeOff, Loader2, Database, Zap, Shield } from 'lucide-react';
import toast from 'react-hot-toast';
import { register, login } from '../api/client';

export default function AuthPage({ onNavigate, onAuthSuccess }) {
  const [mode, setMode]               = useState('login');
  const [email, setEmail]             = useState('');
  const [password, setPassword]       = useState('');
  const [companyName, setCompanyName] = useState('');
  const [fullName, setFullName]       = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading]         = useState(false);
  const [generatedKey, setGeneratedKey] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (mode === 'register') {
        const data = await register(email, password, companyName, fullName);
        setGeneratedKey(data.client?.api_key || null);
        toast.success('Account created successfully!');
        if (!data.client?.api_key) onAuthSuccess(data);
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

  // API key reveal screen after registration
  if (generatedKey) {
    return (
      <div className="auth-split">
        <div className="auth-split-left">
          <div className="auth-left-brand">
            <div className="auth-left-brand-icon"><Mic size={16} /></div>
            <span className="auth-left-brand-name">VoiceRAG</span>
          </div>
          <h2 className="auth-left-headline">Your AI assistant<br />is ready to deploy.</h2>
          <p className="auth-left-sub">Save your API key securely. You'll need it to authenticate your widget on any website.</p>
          <div className="auth-left-features">
            <div className="auth-left-feature">
              <div className="auth-feat-icon"><Database size={16} /></div>
              <div className="auth-feat-text">
                <h4>Upload documents now</h4>
                <p>Head to the portal and upload your PDFs or DOCX files to power your assistant.</p>
              </div>
            </div>
            <div className="auth-left-feature">
              <div className="auth-feat-icon"><Zap size={16} /></div>
              <div className="auth-feat-text">
                <h4>Deploy in one line</h4>
                <p>Copy your embed script and paste it into any website to go live instantly.</p>
              </div>
            </div>
            <div className="auth-left-feature">
              <div className="auth-feat-icon"><Shield size={16} /></div>
              <div className="auth-feat-text">
                <h4>Your data stays isolated</h4>
                <p>Per client vector stores ensure your content never mixes with other tenants.</p>
              </div>
            </div>
          </div>
        </div>

        <div className="auth-split-right">
          <div className="auth-split-card">
            <div className="auth-key-reveal">
              <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Account Created!</h2>
              <p className="auth-key-warning" style={{ marginBottom: 20 }}>
                Your API key has been generated. Save it now it won't be shown again after you navigate away.
              </p>
              <div className="auth-key-box">
                <code>{generatedKey}</code>
              </div>
              <button
                className="btn btn-secondary"
                style={{ width: '100%', marginBottom: 10 }}
                onClick={() => {
                  navigator.clipboard.writeText(generatedKey);
                  toast.success('API key copied!');
                }}
              >
                Copy to Clipboard
              </button>
              <button
                className="btn btn-primary"
                style={{ width: '100%' }}
                onClick={() => onAuthSuccess({ access_token: localStorage.getItem('voicerag_token') })}
              >
                Go to Dashboard →
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-split">
      {/* ── Left Brand Panel ── */}
      <div className="auth-split-left">
        <div className="auth-left-brand">
          <div className="auth-left-brand-icon"><Mic size={16} /></div>
          <span className="auth-left-brand-name">VoiceRAG</span>
        </div>
        <h2 className="auth-left-headline">
          {mode === 'login'
            ? 'Welcome back to\nyour AI platform.'
            : 'Start building your\nAI voice agent.'}
        </h2>
        <p className="auth-left-sub">
          {mode === 'login'
            ? 'Sign in to access your dashboard, analytics, and deployed voice assistants.'
            : 'Create an account and deploy an AI assistant trained on your data — in minutes.'}
        </p>
        <div className="auth-left-features">
          <div className="auth-left-feature">
            <div className="auth-feat-icon"><Database size={16} /></div>
            <div className="auth-feat-text">
              <h4>Zero-hallucination RAG</h4>
              <p>Every answer is grounded strictly in your uploaded documents via FAISS vector search.</p>
            </div>
          </div>
          <div className="auth-left-feature">
            <div className="auth-feat-icon"><Zap size={16} /></div>
            <div className="auth-feat-text">
              <h4>Sub 5s voice round trips</h4>
              <p>Faster Whisper STT + Groq LLM + Kokoro TTS delivering natural conversation speeds.</p>
            </div>
          </div>
          <div className="auth-left-feature">
            <div className="auth-feat-icon"><Shield size={16} /></div>
            <div className="auth-feat-text">
              <h4>Full data isolation</h4>
              <p>Per client indices and API key scoping ensure your content stays yours, always.</p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Right Form Panel ── */}
      <div className="auth-split-right">
        <div className="auth-split-card">
          <button className="auth-back" onClick={() => onNavigate('landing')}>
            <ArrowLeft size={14} /> Back to home
          </button>

          <div className="auth-brand">
            <div className="landing-brand-icon"><Mic size={16} /></div>
            <span>VoiceRAG</span>
          </div>

          <h2>{mode === 'login' ? 'Sign In' : 'Create Account'}</h2>
          <p className="auth-sub">
            {mode === 'login'
              ? 'Sign in to your portal to continue'
              : 'Deploy your first AI assistant in minutes'}
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
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <button type="submit" className="btn btn-primary auth-submit" disabled={loading}>
              {loading ? (
                <><Loader2 size={15} className="spinning" /> Processing...</>
              ) : (
                mode === 'login' ? 'Sign In' : 'Create Account'
              )}
            </button>
          </form>

          <div className="auth-switch">
            {mode === 'login' ? (
              <p>Don't have an account? <button onClick={() => setMode('register')}>Sign up free</button></p>
            ) : (
              <p>Already have an account? <button onClick={() => setMode('login')}>Sign in</button></p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
