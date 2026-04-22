import {
  Mic, Zap, Shield, BarChart3, ArrowRight, Code, Globe,
  Database, FileText, Cpu, Lock, Activity, Puzzle,
  Languages, Building2
} from 'lucide-react';

export default function LandingPage({ onNavigate }) {
  return (
    <div className="pro-landing">
      <div className="glow-bg" />

      {/* ── Navigation ── */}
      <nav className="pro-landing-nav">
        <div className="pro-nav-container">
          <div className="landing-brand" style={{ cursor: 'pointer' }} onClick={() => window.scrollTo(0, 0)}>
            <div className="landing-brand-icon"><Mic size={18} /></div>
            <span>VoiceRAG</span>
          </div>
          <div className="pro-nav-menu">
            <span className="pro-nav-item">Features</span>
            <span className="pro-nav-item" onClick={() => onNavigate('pipeline')}>Pipeline</span>
            <span className="pro-nav-item" onClick={() => onNavigate('pricing')}>Pricing</span>
            <span className="pro-nav-item" onClick={() => onNavigate('docs')}>Docs</span>
          </div>
          <div className="pro-nav-actions">
            <button onClick={() => onNavigate('auth')} className="pro-nav-signin">Sign In</button>
            <button onClick={() => onNavigate('auth')} className="pro-btn pro-btn-primary pro-btn-sm">
              Get Started Free
            </button>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="pro-hero">
        <div className="pro-hero-eyebrow">AI Powered Voice Intelligence Platform</div>
        <div className="pro-hero-badge">
          <span>New</span> VoiceRAG 2.0 Ultra-low latency voice pipeline is live
        </div>
        <h1 className="pro-hero-title">
          Deploy AI Voice Agents<br />
          Trained on <span className="hero-gradient-text">Your Data.</span>
        </h1>
        <p className="pro-hero-subtitle">
          Instantly embed an intelligent voice assistant on your website. Our state of the art RAG pipeline ensures every answer is grounded strictly in your documents zero hallucinations, full accuracy.
        </p>
        <div className="pro-hero-actions">
          <button onClick={() => onNavigate('auth')} className="pro-btn pro-btn-primary">
            Start Building Free <ArrowRight size={17} />
          </button>
          <button onClick={() => onNavigate('pipeline')} className="pro-btn pro-btn-secondary">
            Explore the Pipeline
          </button>
        </div>

        {/* Browser-frame mock dashboard */}
        <div className="hero-visual-wrap">
          <div className="hero-browser">
            <div className="hero-browser-bar">
              <div className="hero-browser-dots">
                <span className="dot dot-red" />
                <span className="dot dot-yellow" />
                <span className="dot dot-green" />
              </div>
              <div className="hero-browser-address">app.voicerag.io/dashboard</div>
            </div>
            <div className="hero-browser-body">
              <div className="hero-mock-layout">
                {/* Sidebar icons */}
                <div className="hero-mock-sidebar">
                  <div className="hms-icon hms-active" />
                  <div className="hms-icon" />
                  <div className="hms-icon" />
                  <div className="hms-icon" />
                  <div className="hms-icon" />
                </div>
                {/* Main area */}
                <div className="hero-mock-main">
                  <div className="hero-mock-stats-row">
                    <div className="hero-mock-card">
                      <div className="hmc-label">Total Queries</div>
                      <div className="hmc-value">1,247</div>
                      <span className="hmc-badge up">↑ 12%</span>
                    </div>
                    <div className="hero-mock-card">
                      <div className="hmc-label">Avg Latency</div>
                      <div className="hmc-value">3.2s</div>
                      <span className="hmc-badge up">↑ Fast</span>
                    </div>
                    <div className="hero-mock-card">
                      <div className="hmc-label">Accuracy</div>
                      <div className="hmc-value">99.8%</div>
                      <span className="hmc-badge up">↑ High</span>
                    </div>
                  </div>
                  <div className="hero-mock-voice-area">
                    <div className="hero-mock-orb">
                      <div className="hmo-ring" />
                      <div className="hmo-core" />
                    </div>
                    <div className="hero-mock-transcript">
                      <div className="hmt-line hmt-user">What is our return policy?</div>
                      <div className="hmt-line hmt-ai">Based on your uploaded policy document, returns are accepted within 30 days of purchase...</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Stats Belt ── */}
      <section className="stats-belt">
        <div className="stats-belt-inner">
          <div className="stat-item">
            <div className="stat-number">&lt;&nbsp;5s</div>
            <div className="stat-label">Full voice round trip</div>
          </div>
          <div className="stat-divider" />
          <div className="stat-item">
            <div className="stat-number">100%</div>
            <div className="stat-label">Document-grounded answers</div>
          </div>
          <div className="stat-divider" />
          <div className="stat-item">
            <div className="stat-number">10+</div>
            <div className="stat-label">Languages supported</div>
          </div>
          <div className="stat-divider" />
          <div className="stat-item">
            <div className="stat-number">1 line</div>
            <div className="stat-label">To deploy on any website</div>
          </div>
        </div>
      </section>

      {/* ── Trusted By ── */}
      <section className="logo-cloud">
        <p>Trusted by forward thinking teams globally</p>
        <div className="logos">
          <div className="logo-placeholder"><Code size={18} /> Acme Corp</div>
          <div className="logo-placeholder"><Globe size={18} /> GlobalScale</div>
          <div className="logo-placeholder"><Shield size={18} /> SecureTech</div>
          <div className="logo-placeholder"><Zap size={18} /> FlashUI</div>
          <div className="logo-placeholder"><Building2 size={18} /> Enterprise Co</div>
        </div>
      </section>

      {/* ── Features Bento Grid ── */}
      <section className="bento-section">
        <div className="bento-header">
          <div className="section-eyebrow">Platform Features</div>
          <h2>Everything you need. Out of the box.</h2>
          <p>A unified conversational platform designed for pristine accuracy and raw performance.</p>
        </div>
        <div className="bento-grid">
          {/* Large card — RAG */}
          <div className="bento-card bento-large">
            <div className="bento-icon"><Database size={22} /></div>
            <h3>Intelligent RAG Retrieval</h3>
            <p>Chunk, embed, and index your documents with per-client FAISS indices. Every answer strictly references your uploaded content zero hallucinations guaranteed.</p>
            <div className="bento-tag-row">
              <span className="bento-tech-tag">FAISS Indexing</span>
              <span className="bento-tech-tag">Semantic Search</span>
              <span className="bento-tech-tag">Per Client Isolation</span>
            </div>
          </div>

          {/* Small — Voice */}
          <div className="bento-card">
            <div className="bento-icon"><Mic size={22} /></div>
            <h3>Real Time Voice UI</h3>
            <p>Full voice to voice pipeline using Faster Whisper STT and Kokoro TTS. Sub-5-second round-trips for truly natural conversations.</p>
            <div className="bento-tag-row">
              <span className="bento-tech-tag">Whisper STT</span>
              <span className="bento-tech-tag">Kokoro TTS</span>
            </div>
          </div>

          {/* Small — Analytics */}
          <div className="bento-card">
            <div className="bento-icon"><BarChart3 size={22} /></div>
            <h3>Advanced Analytics</h3>
            <p>Per-stage latency breakdowns, error tracking, session histories, and token usage all visible in your live dashboard.</p>
            <div className="bento-tag-row">
              <span className="bento-tech-tag">Real time Metrics</span>
              <span className="bento-tech-tag">Error Logs</span>
            </div>
          </div>

          {/* Large card — Widget */}
          <div className="bento-card bento-large">
            <div className="bento-icon"><Code size={22} /></div>
            <h3>1 Click Widget Deployment</h3>
            <p>Generate isolated API credentials instantly. Copy one line of JavaScript and your AI assistant is live on your site floating exactly where visitors need it.</p>
            <div className="bento-code-preview">
              <code>{`<script src="voicerag.io/widget.js" data-key="YOUR_KEY"></script>`}</code>
            </div>
          </div>
        </div>
      </section>

      {/* ── How It Works ── */}
      <section className="landing-how-it-works">
        <div className="section-container">
          <div className="section-eyebrow">Simple Setup</div>
          <h2 className="how-title">Deploy in minutes, not weeks.</h2>
          <p className="how-subtitle">Three steps from sign-up to a live AI assistant on your website.</p>
          <div className="how-steps">
            <div className="how-step">
              <div className="how-step-num">01</div>
              <div className="how-step-icon"><FileText size={22} /></div>
              <h3>Upload Your Documents</h3>
              <p>Drop your PDFs, DOCX, or TXT files. We parse, chunk, and embed them into a secure, isolated vector store just for your account.</p>
            </div>
            <div className="how-step-connector"><ArrowRight size={20} /></div>
            <div className="how-step">
              <div className="how-step-num">02</div>
              <div className="how-step-icon"><Cpu size={22} /></div>
              <h3>Configure Your Assistant</h3>
              <p>Your AI is ready immediately. Test it via text chat or voice in the portal. Accurate answers from your docs no setup beyond uploading.</p>
            </div>
            <div className="how-step-connector"><ArrowRight size={20} /></div>
            <div className="how-step">
              <div className="how-step-num">03</div>
              <div className="how-step-icon"><Code size={22} /></div>
              <h3>Deploy with One Line</h3>
              <p>Generate your embed key, copy one script tag, and paste it into your website. Your voice agent is live and ready for visitors instantly.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Why VoiceRAG ── */}
      <section className="ent-features">
        <div className="section-container">
          <div className="section-eyebrow">Why VoiceRAG</div>
          <h2>Built for production from day one.</h2>
          <p className="ent-subtitle">Purpose-built for speed, isolation, and full observability at every layer of the stack.</p>
          <div className="ent-grid">
            <div className="ent-card">
              <div className="ent-card-icon"><Zap size={20} /></div>
              <h3>Hardware Accelerated LLM</h3>
              <p>Groq's LPU hardware delivers 10× faster inference than standard GPU clouds keeping LLM responses under 500ms consistently.</p>
            </div>
            <div className="ent-card">
              <div className="ent-card-icon"><Shield size={20} /></div>
              <h3>True Multi Tenancy</h3>
              <p>Per client FAISS indices with API key isolation. No shared contexts, no cross-tenant data leakage enforced at every layer.</p>
            </div>
            <div className="ent-card">
              <div className="ent-card-icon"><Activity size={20} /></div>
              <h3>Full Observability</h3>
              <p>Per stage latency (STT → Retrieval → LLM → TTS), error logs, and session analytics baked in from day one.</p>
            </div>
            <div className="ent-card">
              <div className="ent-card-icon"><Puzzle size={20} /></div>
              <h3>1 Line Integration</h3>
              <p>One script tag. That's all it takes. Our widget handles the entire chat and voice experience for your visitors.</p>
            </div>
            <div className="ent-card">
              <div className="ent-card-icon"><Languages size={20} /></div>
              <h3>Multi Language Voice</h3>
              <p>Auto-detect or manually select from 10+ languages including English, Hindi, Urdu, and more for global reach.</p>
            </div>
            <div className="ent-card">
              <div className="ent-card-icon"><Lock size={20} /></div>
              <h3>Enterprise Security</h3>
              <p>Per-client data isolation, API key scoping, and admin oversight controls built into every account from the start.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="pro-cta">
        <div className="pro-cta-inner">
          <h2>Ready to deploy your AI agent?</h2>
          <p>Join teams delivering accurate, grounded AI experiences with zero hallucinations and instant deployment.</p>
          <div className="pro-cta-actions">
            <button onClick={() => onNavigate('auth')} className="pro-btn pro-btn-primary pro-btn-lg">
              Get Started Free <ArrowRight size={18} />
            </button>
            <button onClick={() => onNavigate('pipeline')} className="pro-btn pro-btn-secondary">
              Explore the Pipeline
            </button>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="pro-footer-full">
        <div className="footer-inner">
          <div className="footer-top">
            <div className="footer-brand-col">
              <div className="landing-brand footer-brand" style={{ cursor: 'pointer' }}>
                <div className="landing-brand-icon"><Mic size={14} /></div>
                <span>VoiceRAG</span>
              </div>
              <p className="footer-brand-desc">
                Intelligent AI voice agents trained on your data. Deploy in minutes, answer accurately always.
              </p>
            </div>
            <div className="footer-links-col">
              <div className="footer-col-title">Product</div>
              <div className="footer-col-links">
                <span className="footer-col-link">Features</span>
                <span className="footer-col-link" onClick={() => onNavigate('pipeline')}>Pipeline Architecture</span>
                <span className="footer-col-link" onClick={() => onNavigate('pricing')}>Pricing</span>
                <span className="footer-col-link">Widget Embed</span>
              </div>
            </div>
            <div className="footer-links-col">
              <div className="footer-col-title">Developers</div>
              <div className="footer-col-links">
                <span className="footer-col-link" onClick={() => onNavigate('docs')}>Documentation</span>
                <span className="footer-col-link" onClick={() => onNavigate('docs')}>API Reference</span>
                <span className="footer-col-link" onClick={() => onNavigate('docs')}>Embed Guide</span>
                <span className="footer-col-link">Webhooks</span>
              </div>
            </div>
            <div className="footer-links-col">
              <div className="footer-col-title">Company</div>
              <div className="footer-col-links">
                <span className="footer-col-link">About</span>
                <span className="footer-col-link">Blog</span>
                <span className="footer-col-link">Privacy Policy</span>
                <span className="footer-col-link">Terms of Service</span>
              </div>
            </div>
          </div>
          <div className="footer-bottom">
            <span>© 2026 VocalizeWeb Inc. All rights reserved.</span>
            <div className="footer-bottom-links">
              <span>Privacy</span>
              <span>Terms</span>
              <span>Status</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
