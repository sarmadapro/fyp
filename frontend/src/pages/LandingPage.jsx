import { Mic, Zap, Shield, BarChart3, ArrowRight, Code, Globe, ChevronDown, Database } from 'lucide-react';

export default function LandingPage({ onNavigate }) {
  return (
    <div className="pro-landing">
      {/* Background Glow */}
      <div className="glow-bg" />

      {/* Navigation */}
      <nav className="pro-landing-nav">
        <div className="pro-nav-container">
          <div className="landing-brand" style={{ cursor: 'pointer' }} onClick={() => window.scrollTo(0, 0)}>
            <div className="landing-brand-icon"><Mic size={18} /></div>
            <span>VoiceRAG</span>
          </div>
          <div className="pro-nav-menu">
            <span className="pro-nav-item">Features <ChevronDown size={14}/></span>
            <span className="pro-nav-item" onClick={() => onNavigate('pipeline')}>How it Works</span>
            <span className="pro-nav-item">Pricing</span>
            <span className="pro-nav-item">Resources <ChevronDown size={14}/></span>
          </div>
          <div className="landing-nav-links">
            <button onClick={() => onNavigate('auth')} className="pro-nav-item" style={{ background: 'none', border:'none' }}>Sign In</button>
            <button onClick={() => onNavigate('auth')} className="pro-btn pro-btn-primary" style={{ padding: '8px 16px', fontSize: '13px' }}>Deploy Now</button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pro-hero">
        <div className="pro-hero-badge">
          <span>New</span> VoiceRAG 2.0 is now available
        </div>
        <h1 className="pro-hero-title">
          Build AI Voice Agents<br/>Trained on Your Data.
        </h1>
        <p className="pro-hero-subtitle">
          Instantly deploy an intelligent, ultra-fast RAG assistant to your website. Forget hallucination—our state-of-the-art Voice-to-Voice LLM pipeline provides accurate answers strictly from your knowledge base.
        </p>
        <div className="pro-hero-actions">
          <button onClick={() => onNavigate('auth')} className="pro-btn pro-btn-primary">
            Start Building Free <ArrowRight size={18} />
          </button>
          <button onClick={() => onNavigate('pipeline')} className="pro-btn pro-btn-secondary">
            See Pipeline Architecture
          </button>
        </div>
        
        {/* Mockup Image */}
        <div className="pro-hero-visual">
          <img src="/hero_dashboard.png" alt="VoiceRAG Dashboard Overview" />
        </div>
      </section>

      {/* Trusted By Segment */}
      <section className="logo-cloud">
        <p>Trusted by forward-thinking teams globally</p>
        <div className="logos">
          <div className="logo-placeholder"><Code size={24}/> Acme Corp</div>
          <div className="logo-placeholder"><Globe size={24}/> GlobalScale</div>
          <div className="logo-placeholder"><Shield size={24}/> SecureTech</div>
          <div className="logo-placeholder"><Zap size={24}/> FlashUI</div>
        </div>
      </section>

      {/* Bento Grid Features */}
      <section className="bento-section">
        <div className="bento-header">
          <h2>Everything you need. Out of the box.</h2>
          <p>A unified conversational platform designed for pristine accuracy and raw performance.</p>
        </div>
        
        <div className="bento-grid">
          {/* Card 1: RAG Accuracy (Large) */}
          <div className="bento-card bento-large" style={{ paddingBottom: '200px' }}>
            <div className="bento-icon"><Database size={24}/></div>
            <h3>Intelligent RAG Retrieval</h3>
            <p style={{ position: 'relative', zIndex: 10 }}>We chunk, embed, and index your documents securely. The AI will strictly reference these vectors, ensuring zero hallucinations and perfect citations.</p>
            <img src="/bento_fast.png" className="bento-image" style={{ width: '130%', right: '-15%', bottom: '-70%', opacity: 0.15, mixBlendMode: 'multiply', pointerEvents: 'none' }} alt="" />
          </div>

          {/* Card 2: Ultra Fast Voice */}
          <div className="bento-card" style={{ paddingBottom: '200px' }}>
            <div className="bento-icon"><Mic size={24}/></div>
            <h3>Real-Time Voice UI</h3>
            <p style={{ position: 'relative', zIndex: 10 }}>Utilizing Kokoro TTS and Faster Whisper, enable instantaneous voice-to-voice communication for your visitors.</p>
            <img src="/bento_voice.png" className="bento-image" style={{ bottom: '-80%', right: '-60%', width: '220%', opacity: 0.15, mixBlendMode: 'multiply', pointerEvents: 'none' }} alt="" />
          </div>

          {/* Card 3: Deep Analytics */}
          <div className="bento-card">
            <div className="bento-icon"><BarChart3 size={24}/></div>
            <h3>Advanced Analytics</h3>
            <p style={{ position: 'relative', zIndex: 10 }}>Gain unbridled visibility into latency, system failures, and user interactions within the dashboard. Track tokens precisely.</p>
          </div>

          {/* Card 4: Widget Integration (Large) */}
          <div className="bento-card bento-large" style={{ paddingBottom: '160px' }}>
            <div className="bento-icon"><Code size={24}/></div>
            <h3>1-Click Widget Deployment</h3>
            <p style={{ position: 'relative', zIndex: 10 }}>Generate isolated API credentials instantly, and copy just one line of JavaScript to deploy the bot floating exactly where you need it on your site.</p>
            <img src="/hero_dashboard.png" className="bento-image" style={{ width: '100%', right: '0%', bottom: '-60%', opacity: 0.15, mixBlendMode: 'multiply', pointerEvents: 'none' }} alt="" />
          </div>
        </div>
      </section>

      {/* Call to Action */}
      <section className="pro-cta">
        <h2>Ready to deploy your agent?</h2>
        <p className="pro-hero-subtitle" style={{ maxWidth: '100%', marginBottom: '32px' }}>
          Join thousands of modern teams delivering magical customer experiences.
        </p>
        <button onClick={() => onNavigate('auth')} className="pro-btn pro-btn-primary" style={{ padding: '16px 32px', fontSize: '16px' }}>
          Get Started For Free <ArrowRight size={18} />
        </button>
      </section>

      {/* Footer */}
      <footer className="pro-footer">
        <div className="landing-brand">
          <div className="landing-brand-icon"><Mic size={14} /></div>
          <span>VoiceRAG</span>
        </div>
        <div>
          <span style={{ marginRight: '24px', cursor: 'pointer' }}>Privacy Policy</span>
          <span style={{ marginRight: '24px', cursor: 'pointer' }}>Terms of Service</span>
          <span>© 2026 VoiceRAG Inc.</span>
        </div>
      </footer>
    </div>
  );
}
