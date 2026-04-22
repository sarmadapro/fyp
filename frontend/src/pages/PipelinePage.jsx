import {
  ArrowRight, ArrowLeft, Mic, FileText, Database, Cpu,
  Volume2, Search, Zap, Shield, CheckCircle2, MessageCircle
} from 'lucide-react';

export default function PipelinePage({ onNavigate }) {
  return (
    <div className="pro-landing">

      {/* ── Navigation ── */}
      <nav className="pro-landing-nav">
        <div className="pro-nav-container">
          <div className="landing-brand" onClick={() => onNavigate('landing')} style={{ cursor: 'pointer' }}>
            <div className="landing-brand-icon"><Mic size={18} /></div>
            <span>VoiceRAG</span>
          </div>
          <div className="pro-nav-menu">
            <span className="pro-nav-item" onClick={() => onNavigate('landing')}>Features</span>
            <span className="pro-nav-item" style={{ color: 'var(--accent-secondary)' }}>Pipeline</span>
            <span className="pro-nav-item" onClick={() => onNavigate('pricing')}>Pricing</span>
            <span className="pro-nav-item" onClick={() => onNavigate('docs')}>Docs</span>
          </div>
          <div className="pro-nav-actions">
            <button onClick={() => onNavigate('landing')} className="pro-nav-signin">
              <ArrowLeft size={14} style={{ display: 'inline', marginRight: 4 }} />Back
            </button>
            <button onClick={() => onNavigate('auth')} className="pro-btn pro-btn-primary pro-btn-sm">
              Get Started
            </button>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="pro-hero" style={{ paddingBottom: '60px' }}>
        <div className="pro-hero-eyebrow">Technical Deep Dive</div>
        <div className="pro-hero-badge">
          <span>Open</span> Architecture Built for transparency and performance
        </div>
        <h1 className="pro-hero-title">
          Our <span className="hero-gradient-text">Pipeline Architecture</span>
        </h1>
        <p className="pro-hero-subtitle">
          A fully orchestrated RAG pipeline from document ingestion to real time AI voice responses. Here's exactly how every piece fits together under the hood.
        </p>
      </section>

      {/* ── Pipeline Stages ── */}
      <section style={{ padding: '0 0 80px', position: 'relative', zIndex: 2 }}>
        <div className="pipeline-v2-wrap">

          {/* Stage 1 */}
          <div className="pipeline-stage-v2">
            <div className="pipeline-stage-header">
              <div className="pipeline-stage-number">01</div>
              <div className="pipeline-stage-icon"><FileText size={22} /></div>
              <h3>Document Ingestion</h3>
            </div>
            <p>Upload PDF, DOCX, or TXT files. We extract text using PyMuPDF and python docx, then split into optimally sized chunks using recursive character splitting with intelligent overlap for maximum context retention.</p>
            <div className="pipeline-tech-tags">
              <span className="tech-tag">PyMuPDF</span>
              <span className="tech-tag">python docx</span>
              <span className="tech-tag">LangChain Splitter</span>
              <span className="tech-tag">Recursive Chunking</span>
            </div>
          </div>

          <div className="pipeline-connector-v2"><ArrowRight size={16} /></div>

          {/* Stage 2 */}
          <div className="pipeline-stage-v2">
            <div className="pipeline-stage-header">
              <div className="pipeline-stage-number">02</div>
              <div className="pipeline-stage-icon"><Database size={22} /></div>
              <h3>Vector Embedding &amp; Indexing</h3>
            </div>
            <p>Each chunk is transformed into a high dimensional vector using sentence transformers. These vectors are stored in a FAISS index one per client, completely isolated enabling instant retrieval with no cross-tenant exposure.</p>
            <div className="pipeline-tech-tags">
              <span className="tech-tag">Sentence-Transformers</span>
              <span className="tech-tag">FAISS</span>
              <span className="tech-tag">Per Client Isolation</span>
              <span className="tech-tag">384-dim Embeddings</span>
            </div>
          </div>

          <div className="pipeline-connector-v2"><ArrowRight size={16} /></div>

          {/* Stage 3 */}
          <div className="pipeline-stage-v2">
            <div className="pipeline-stage-header">
              <div className="pipeline-stage-number">03</div>
              <div className="pipeline-stage-icon"><Search size={22} /></div>
              <h3>Semantic Retrieval</h3>
            </div>
            <p>When a query arrives, we embed it and perform approximate nearest-neighbor search on the client's FAISS index. The top k most semantically relevant chunks are retrieved and ranked by similarity score as context for the LLM.</p>
            <div className="pipeline-tech-tags">
              <span className="tech-tag">ANN Search</span>
              <span className="tech-tag">Top K Retrieval</span>
              <span className="tech-tag">Score Ranking</span>
              <span className="tech-tag">Cosine Similarity</span>
            </div>
          </div>

          <div className="pipeline-connector-v2"><ArrowRight size={16} /></div>

          {/* Stage 4 */}
          <div className="pipeline-stage-v2">
            <div className="pipeline-stage-header">
              <div className="pipeline-stage-number">04</div>
              <div className="pipeline-stage-icon"><Cpu size={22} /></div>
              <h3>LLM Generation</h3>
            </div>
            <p>Retrieved chunks are injected into a carefully crafted prompt. The Groq-hosted Llama 3.3 70B generates a context-grounded response in under 500ms thanks to Groq's purpose-built LPU hardware acceleration — 10× faster than standard GPU inference.</p>
            <div className="pipeline-tech-tags">
              <span className="tech-tag">Llama 3.3 70B</span>
              <span className="tech-tag">Groq LPU</span>
              <span className="tech-tag">&lt;500ms Inference</span>
              <span className="tech-tag">Grounded Prompting</span>
            </div>
          </div>

          <div className="pipeline-connector-v2"><ArrowRight size={16} /></div>

          {/* Stage 5 */}
          <div className="pipeline-stage-v2">
            <div className="pipeline-stage-header">
              <div className="pipeline-stage-number">05</div>
              <div className="pipeline-stage-icon"><Volume2 size={22} /></div>
              <h3>Voice Pipeline (Optional)</h3>
            </div>
            <p>For voice mode: Faster Whisper large-v3 transcribes speech in real-time with high accuracy. The RAG response is then synthesized into natural sounding speech by Kokoro TTS (82M parameter model). Full round trip completes in under 5 seconds via WebSocket streaming.</p>
            <div className="pipeline-tech-tags">
              <span className="tech-tag">Faster Whisper v3</span>
              <span className="tech-tag">Kokoro TTS</span>
              <span className="tech-tag">WebSocket Streaming</span>
              <span className="tech-tag">10+ Languages</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── Differentiators ── */}
      <section style={{ padding: '80px 0', background: 'white', borderTop: '1px solid rgba(0,0,0,0.06)', borderBottom: '1px solid rgba(0,0,0,0.06)', position: 'relative', zIndex: 2 }}>
        <div className="section-container" style={{ textAlign: 'center' }}>
          <div className="section-eyebrow">What Sets Us Apart</div>
          <h2 style={{ fontSize: 36, fontWeight: 700, marginBottom: 12, letterSpacing: '-0.03em' }}>
            Purpose built for speed, isolation &amp; observability
          </h2>
          <p style={{ color: '#71717A', fontSize: 17, marginBottom: 52, maxWidth: 500, margin: '0 auto 52px' }}>
            Every design decision in this pipeline was made to maximize reliability and minimize latency.
          </p>
          <div className="pipeline-diff-grid">
            <div className="pipeline-diff-card">
              <div className="feature-icon"><Zap size={20} /></div>
              <h3>Hardware-Accelerated LLM</h3>
              <p>While competitors rely on generic GPU clouds, we use Groq's purpose built LPU hardware for 10× faster inference and consistent sub 500ms generation.</p>
            </div>
            <div className="pipeline-diff-card">
              <div className="feature-icon"><Shield size={20} /></div>
              <h3>True Multi Tenancy</h3>
              <p>Per client FAISS indices with API key isolation. No shared contexts, no data leakage between tenants enforced at the storage and retrieval layers.</p>
            </div>
            <div className="pipeline-diff-card">
              <div className="feature-icon"><CheckCircle2 size={20} /></div>
              <h3>Full Stage Observability</h3>
              <p>Per-stage latency tracking (STT → Retrieval → LLM → TTS), detailed error logs, and session analytics built into every single query.</p>
            </div>
            <div className="pipeline-diff-card">
              <div className="feature-icon"><MessageCircle size={20} /></div>
              <h3>1 Line Widget Integration</h3>
              <p>One script tag deploys the entire voice + chat experience on any website. No backend required on the customer side just a single API key.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="pro-cta">
        <div className="pro-cta-inner">
          <h2>See It In Action</h2>
          <p>Create your account and deploy your first AI assistant in minutes no infrastructure setup required.</p>
          <div className="pro-cta-actions">
            <button onClick={() => onNavigate('auth')} className="pro-btn pro-btn-primary pro-btn-lg">
              Start Building Free <ArrowRight size={18} />
            </button>
            <button onClick={() => onNavigate('landing')} className="pro-btn pro-btn-secondary">
              Back to Home
            </button>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="pro-footer-full">
        <div className="footer-inner">
          <div className="footer-top">
            <div className="footer-brand-col">
              <div className="landing-brand footer-brand" style={{ cursor: 'pointer' }} onClick={() => onNavigate('landing')}>
                <div className="landing-brand-icon"><Mic size={14} /></div>
                <span>VoiceRAG</span>
              </div>
              <p className="footer-brand-desc">
                Intelligent AI voice agents trained on your data. Deploy in minutes, answer accurately — always.
              </p>
            </div>
            <div className="footer-links-col">
              <div className="footer-col-title">Product</div>
              <div className="footer-col-links">
                <span className="footer-col-link" onClick={() => onNavigate('landing')}>Features</span>
                <span className="footer-col-link">Pipeline Architecture</span>
                <span className="footer-col-link">Analytics</span>
                <span className="footer-col-link">Widget Embed</span>
              </div>
            </div>
            <div className="footer-links-col">
              <div className="footer-col-title">Developers</div>
              <div className="footer-col-links">
                <span className="footer-col-link">API Reference</span>
                <span className="footer-col-link">Embed Docs</span>
                <span className="footer-col-link">Webhooks</span>
                <span className="footer-col-link">SDKs</span>
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
