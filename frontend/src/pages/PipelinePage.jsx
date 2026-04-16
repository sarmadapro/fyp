import {
  ArrowRight, ArrowLeft, Mic, FileText, Database, Cpu, MessageCircle,
  Volume2, Search, Zap, Shield, CheckCircle2
} from 'lucide-react';

export default function PipelinePage({ onNavigate }) {
  return (
    <div className="landing">
      <nav className="landing-nav">
        <div className="landing-nav-inner">
          <div className="landing-brand" onClick={() => onNavigate('landing')} style={{ cursor: 'pointer' }}>
            <div className="landing-brand-icon"><Mic size={18} /></div>
            <span>VoiceRAG</span>
          </div>
          <div className="landing-nav-links">
            <button onClick={() => onNavigate('landing')} className="landing-nav-link">
              <ArrowLeft size={14} /> Home
            </button>
            <button onClick={() => onNavigate('auth')} className="btn btn-primary btn-sm">Get Started</button>
          </div>
        </div>
      </nav>

      <section className="pipeline-hero">
        <h1>Our <span className="gradient-text">Pipeline Architecture</span></h1>
        <p className="landing-hero-sub">
          A fully orchestrated RAG pipeline — from document ingestion to real-time AI responses.
          Here's how every piece fits together.
        </p>
      </section>

      {/* Pipeline Stages */}
      <section className="landing-section">
        <div className="pipeline-stages">

          {/* Stage 1: Ingestion */}
          <div className="pipeline-stage">
            <div className="pipeline-stage-header">
              <div className="pipeline-stage-number">01</div>
              <div className="pipeline-stage-icon"><FileText size={24} /></div>
              <h3>Document Ingestion</h3>
            </div>
            <p>Upload PDF, DOCX, or TXT files. We extract text using PyMuPDF and python-docx, then split into optimally-sized chunks using recursive character splitting with intelligent overlap.</p>
            <div className="pipeline-tech-tags">
              <span className="tech-tag">PyMuPDF</span>
              <span className="tech-tag">python-docx</span>
              <span className="tech-tag">LangChain Splitter</span>
            </div>
          </div>

          <div className="pipeline-connector"><ArrowRight size={16} /></div>

          {/* Stage 2: Embedding */}
          <div className="pipeline-stage">
            <div className="pipeline-stage-header">
              <div className="pipeline-stage-number">02</div>
              <div className="pipeline-stage-icon"><Database size={24} /></div>
              <h3>Vector Embedding & Indexing</h3>
            </div>
            <p>Each chunk is transformed into a high-dimensional vector using sentence transformers. These vectors are stored in a FAISS index — one per client, completely isolated.</p>
            <div className="pipeline-tech-tags">
              <span className="tech-tag">Sentence-Transformers</span>
              <span className="tech-tag">FAISS</span>
              <span className="tech-tag">Per-Client Isolation</span>
            </div>
          </div>

          <div className="pipeline-connector"><ArrowRight size={16} /></div>

          {/* Stage 3: Retrieval */}
          <div className="pipeline-stage">
            <div className="pipeline-stage-header">
              <div className="pipeline-stage-number">03</div>
              <div className="pipeline-stage-icon"><Search size={24} /></div>
              <h3>Semantic Retrieval</h3>
            </div>
            <p>When a query arrives, we embed it and perform approximate nearest-neighbor search on the client's FAISS index. The top-k most relevant chunks are retrieved as context for the LLM.</p>
            <div className="pipeline-tech-tags">
              <span className="tech-tag">ANN Search</span>
              <span className="tech-tag">Top-K Retrieval</span>
              <span className="tech-tag">Score Ranking</span>
            </div>
          </div>

          <div className="pipeline-connector"><ArrowRight size={16} /></div>

          {/* Stage 4: Generation */}
          <div className="pipeline-stage">
            <div className="pipeline-stage-header">
              <div className="pipeline-stage-number">04</div>
              <div className="pipeline-stage-icon"><Cpu size={24} /></div>
              <h3>LLM Generation</h3>
            </div>
            <p>Retrieved chunks are injected into a carefully crafted prompt. The Groq-hosted Llama 3.3 70B generates a context-grounded response in under 500ms thanks to Groq's hardware acceleration.</p>
            <div className="pipeline-tech-tags">
              <span className="tech-tag">Llama 3.3 70B</span>
              <span className="tech-tag">Groq Hardware</span>
              <span className="tech-tag">&lt;500ms Inference</span>
            </div>
          </div>

          <div className="pipeline-connector"><ArrowRight size={16} /></div>

          {/* Stage 5: Voice (Optional) */}
          <div className="pipeline-stage">
            <div className="pipeline-stage-header">
              <div className="pipeline-stage-number">05</div>
              <div className="pipeline-stage-icon"><Volume2 size={24} /></div>
              <h3>Voice Pipeline (Optional)</h3>
            </div>
            <p>For voice mode: Faster-Whisper large-v3 transcribes speech in real-time. The RAG response is synthesized into natural speech by Kokoro TTS (82M params). Full round-trip under 5 seconds.</p>
            <div className="pipeline-tech-tags">
              <span className="tech-tag">Faster-Whisper</span>
              <span className="tech-tag">Kokoro TTS</span>
              <span className="tech-tag">WebSocket Streaming</span>
            </div>
          </div>
        </div>
      </section>

      {/* Differentiators */}
      <section className="landing-section features-section">
        <h2>What Makes Us Different</h2>
        <p className="section-sub">Purpose-built for speed, isolation, and observability</p>
        <div className="landing-features">
          <div className="feature-card">
            <div className="feature-icon"><Zap size={22} /></div>
            <h3>Hardware-Accelerated LLM</h3>
            <p>While competitors rely on generic GPU clouds, we use Groq's purpose-built LPU hardware for 10x faster inference.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon"><Shield size={22} /></div>
            <h3>True Multi-Tenancy</h3>
            <p>Per-client FAISS indices with API key isolation. No shared contexts, no data leakage — ever.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon"><CheckCircle2 size={22} /></div>
            <h3>Full Observability</h3>
            <p>Per-stage latency tracking (STT → Retrieval → LLM → TTS), error logs, and session analytics built in from day one.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon"><MessageCircle size={22} /></div>
            <h3>1-Line Integration</h3>
            <p>One script tag. That's all it takes. Our embeddable widget handles the entire chat experience.</p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="landing-cta">
        <h2>See It In Action</h2>
        <p>Create your account and deploy your first AI assistant in minutes.</p>
        <button onClick={() => onNavigate('auth')} className="btn btn-primary btn-lg">
          Start Building <ArrowRight size={16} />
        </button>
      </section>

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
