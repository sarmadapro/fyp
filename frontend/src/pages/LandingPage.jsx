import { Mic, Zap, Shield, BarChart3, ArrowRight, MessageCircle, Upload, Code, Globe } from 'lucide-react';

export default function LandingPage({ onNavigate }) {
  return (
    <div className="landing">
      {/* Navigation */}
      <nav className="landing-nav">
        <div className="landing-nav-inner">
          <div className="landing-brand">
            <div className="landing-brand-icon"><Mic size={18} /></div>
            <span>VoiceRAG</span>
          </div>
          <div className="landing-nav-links">
            <button onClick={() => onNavigate('pipeline')} className="landing-nav-link">How It Works</button>
            <button onClick={() => onNavigate('auth')} className="btn btn-primary btn-sm">Get Started</button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="landing-hero">
        <div className="landing-hero-badge">
          <Zap size={14} /> AI-Powered RAG Platform
        </div>
        <h1>Deploy an AI Assistant<br /><span className="gradient-text">Trained on Your Data</span></h1>
        <p className="landing-hero-sub">
          Upload your documents. Get an embeddable chat widget.
          Your customers get instant, accurate answers — powered by your knowledge base.
        </p>
        <div className="landing-hero-actions">
          <button onClick={() => onNavigate('auth')} className="btn btn-primary btn-lg">
            Start Free <ArrowRight size={16} />
          </button>
          <button onClick={() => onNavigate('pipeline')} className="btn btn-secondary btn-lg">
            See How It Works
          </button>
        </div>
        <div className="landing-hero-stats">
          <div className="hero-stat">
            <span className="hero-stat-value">&lt;2s</span>
            <span className="hero-stat-label">Response Time</span>
          </div>
          <div className="hero-stat-divider" />
          <div className="hero-stat">
            <span className="hero-stat-value">RAG</span>
            <span className="hero-stat-label">Powered Retrieval</span>
          </div>
          <div className="hero-stat-divider" />
          <div className="hero-stat">
            <span className="hero-stat-value">1-Click</span>
            <span className="hero-stat-label">Widget Deploy</span>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="landing-section">
        <h2>How It Works</h2>
        <p className="section-sub">Three steps to your own AI assistant</p>
        <div className="landing-steps">
          <div className="landing-step">
            <div className="step-number">1</div>
            <div className="step-icon"><Upload size={24} /></div>
            <h3>Upload Documents</h3>
            <p>Upload PDFs, DOCX, or TXT files. We chunk, embed, and index them in a vector database dedicated to your account.</p>
          </div>
          <div className="step-arrow"><ArrowRight size={20} /></div>
          <div className="landing-step">
            <div className="step-number">2</div>
            <div className="step-icon"><Code size={24} /></div>
            <h3>Get Your Widget</h3>
            <p>We generate a unique API key and embeddable chat widget. Just copy one line of code into your website.</p>
          </div>
          <div className="step-arrow"><ArrowRight size={20} /></div>
          <div className="landing-step">
            <div className="step-number">3</div>
            <div className="step-icon"><Globe size={24} /></div>
            <h3>Go Live</h3>
            <p>Your visitors get instant AI-powered answers from your knowledge base. Track everything in your analytics dashboard.</p>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="landing-section features-section">
        <h2>Why VoiceRAG</h2>
        <p className="section-sub">Built for performance, security, and simplicity</p>
        <div className="landing-features">
          <div className="feature-card">
            <div className="feature-icon"><Zap size={22} /></div>
            <h3>Ultra-Fast Inference</h3>
            <p>Powered by Groq's hardware-accelerated LLM inference. Get answers in milliseconds, not seconds.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon"><Shield size={22} /></div>
            <h3>Isolated Per-Client</h3>
            <p>Every client gets their own vector database. Your data is completely isolated — no cross-contamination.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon"><BarChart3 size={22} /></div>
            <h3>Full Analytics</h3>
            <p>See every conversation, latency breakdown, and error. Know exactly how your assistant is performing.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon"><MessageCircle size={22} /></div>
            <h3>Chat + Voice</h3>
            <p>Text and voice modes. Real-time speech-to-speech powered by Faster-Whisper and Kokoro TTS.</p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="landing-cta">
        <h2>Ready to Deploy Your AI Assistant?</h2>
        <p>Create your account in 30 seconds. No credit card required.</p>
        <button onClick={() => onNavigate('auth')} className="btn btn-primary btn-lg">
          Get Started Free <ArrowRight size={16} />
        </button>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="landing-brand">
          <div className="landing-brand-icon"><Mic size={14} /></div>
          <span>VoiceRAG</span>
        </div>
        <p>© 2024 VoiceRAG. Intelligent document assistants.</p>
      </footer>
    </div>
  );
}
