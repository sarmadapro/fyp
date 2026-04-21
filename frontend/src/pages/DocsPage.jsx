import { useState } from 'react';
import {
  Mic, ArrowRight, FileText, MessageCircle, Volume2,
  BarChart3, Code, Key, ChevronRight, Terminal,
  AlertCircle, CheckCircle2, Globe, Cpu, Database
} from 'lucide-react';

const NAV = [
  {
    section: 'Getting Started',
    items: ['Quick Start', 'Authentication', 'Your First Assistant'],
  },
  {
    section: 'Core Features',
    items: ['Document Upload', 'Text Chat', 'Voice Assistant', 'Analytics'],
  },
  {
    section: 'Integration',
    items: ['Embed Widget', 'API Reference', 'API Keys'],
  },
  {
    section: 'Advanced',
    items: ['Multi-Language', 'Pipeline Overview', 'Security & Isolation'],
  },
];

const CONTENT = {

  'Quick Start': (
    <div className="docs-article">
      <div className="docs-badge docs-badge-new">Getting Started</div>
      <h1>Quick Start</h1>
      <p className="docs-lead">Get your AI voice assistant live in under 5 minutes. No infrastructure setup required.</p>

      <div className="docs-steps">
        <div className="docs-step">
          <div className="docs-step-num">1</div>
          <div className="docs-step-body">
            <h3>Create your account</h3>
            <p>Sign up at <strong>app.voicerag.io</strong>. A free account is ready immediately with no credit card required.</p>
          </div>
        </div>
        <div className="docs-step">
          <div className="docs-step-num">2</div>
          <div className="docs-step-body">
            <h3>Upload your document</h3>
            <p>Head to the <strong>Documents</strong> tab and upload a PDF, DOCX, or TXT file. Processing takes 10–30 seconds depending on size.</p>
          </div>
        </div>
        <div className="docs-step">
          <div className="docs-step-num">3</div>
          <div className="docs-step-body">
            <h3>Test in the portal</h3>
            <p>Use the <strong>Chat</strong> or <strong>Voice</strong> tab to immediately query your assistant. Answers are grounded strictly in your uploaded document.</p>
          </div>
        </div>
        <div className="docs-step">
          <div className="docs-step-num">4</div>
          <div className="docs-step-body">
            <h3>Deploy to your website</h3>
            <p>Go to <strong>API Keys</strong>, generate an embed key, and paste the one-liner script tag into your website's HTML.</p>
          </div>
        </div>
      </div>

      <div className="docs-callout docs-callout-info">
        <AlertCircle size={16} />
        <span>Only one document can be active at a time on the free plan. Upload a new file to replace the current one.</span>
      </div>

      <h2>What's next?</h2>
      <div className="docs-next-links">
        <a className="docs-next-card">
          <FileText size={18} />
          <div>
            <strong>Document Upload</strong>
            <span>Supported formats, size limits, and processing details</span>
          </div>
          <ChevronRight size={16} />
        </a>
        <a className="docs-next-card">
          <Code size={18} />
          <div>
            <strong>Embed Widget</strong>
            <span>Deploy your assistant to any website in one line</span>
          </div>
          <ChevronRight size={16} />
        </a>
      </div>
    </div>
  ),

  'Authentication': (
    <div className="docs-article">
      <div className="docs-badge">Getting Started</div>
      <h1>Authentication</h1>
      <p className="docs-lead">VoiceRAG uses JWT bearer tokens for portal sessions and scoped API keys for widget embeds.</p>

      <h2>Portal Authentication</h2>
      <p>When you log in via the portal, a JWT access token is stored in <code>localStorage</code> under the key <code>voicerag_token</code>. This token is sent with every API request as an <code>Authorization: Bearer</code> header.</p>

      <div className="docs-code-block">
        <div className="docs-code-header"><Terminal size={13} /> HTTP Request</div>
        <pre><code>{`GET /api/portal/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...`}</code></pre>
      </div>

      <h2>Embed API Keys</h2>
      <p>The embed widget uses a separate, scoped API key that allows only the <code>/api/widget/chat</code> and <code>/api/widget/voice</code> endpoints. Keys can be created, listed, and revoked from the <strong>API Keys</strong> tab.</p>

      <div className="docs-callout docs-callout-warning">
        <AlertCircle size={16} />
        <span>API keys are shown only once at creation. Store them securely — they cannot be recovered after the initial reveal.</span>
      </div>

      <h2>Token Expiry</h2>
      <p>Portal JWTs expire after 7 days. The frontend automatically redirects to the login screen when a 401 response is received. Embed API keys do not expire unless manually revoked.</p>
    </div>
  ),

  'Your First Assistant': (
    <div className="docs-article">
      <div className="docs-badge">Getting Started</div>
      <h1>Your First Assistant</h1>
      <p className="docs-lead">A walkthrough of creating, testing, and deploying a complete AI voice assistant from scratch.</p>

      <h2>1. Choose your source document</h2>
      <p>Pick a document that represents a single knowledge domain — e.g., a product manual, an FAQ document, or a company policy PDF. VoiceRAG works best with focused, well-structured content.</p>

      <div className="docs-callout docs-callout-success">
        <CheckCircle2 size={16} />
        <span><strong>Tip:</strong> Documents with clear headings and numbered lists tend to produce the most accurate retrievals.</span>
      </div>

      <h2>2. Upload and verify indexing</h2>
      <p>After uploading, the status indicator in the sidebar turns green when indexing is complete. This typically takes 15–45 seconds. The pipeline automatically:</p>
      <ul className="docs-list">
        <li>Extracts text from your file</li>
        <li>Splits it into overlapping chunks</li>
        <li>Embeds chunks into your private FAISS index</li>
      </ul>

      <h2>3. Test with Chat first</h2>
      <p>Use the <strong>Chat</strong> tab to send a few queries before enabling voice. This lets you verify that the AI is referencing your document correctly without the overhead of the voice pipeline.</p>

      <h2>4. Enable Voice</h2>
      <p>Switch to the <strong>Voice</strong> tab. Click the orb to start recording. Speak your query naturally — the assistant will respond in under 5 seconds.</p>

      <h2>5. Deploy your widget</h2>
      <p>Once you're satisfied with accuracy, generate an embed key and add the script tag to your site:</p>
      <div className="docs-code-block">
        <div className="docs-code-header"><Terminal size={13} /> HTML</div>
        <pre><code>{`<script
  src="https://voicerag.io/widget.js"
  data-key="vr_live_xxxxxxxxxxxx"
  data-mode="voice"
  data-position="bottom-right">
</script>`}</code></pre>
      </div>
    </div>
  ),

  'Document Upload': (
    <div className="docs-article">
      <div className="docs-badge docs-badge-blue">Core Features</div>
      <h1>Document Upload</h1>
      <p className="docs-lead">Your document is the knowledge source for the AI. Upload, replace, and manage it from the Documents tab.</p>

      <h2>Supported Formats</h2>
      <div className="docs-format-grid">
        <div className="docs-format-card">
          <FileText size={20} />
          <strong>PDF</strong>
          <span>Text-selectable PDFs. Scanned documents are not supported yet.</span>
        </div>
        <div className="docs-format-card">
          <FileText size={20} />
          <strong>DOCX</strong>
          <span>Microsoft Word documents. Tables and embedded images are extracted as text.</span>
        </div>
        <div className="docs-format-card">
          <FileText size={20} />
          <strong>TXT</strong>
          <span>Plain text files with UTF-8 encoding. No formatting required.</span>
        </div>
      </div>

      <h2>Size Limits</h2>
      <table className="docs-table">
        <thead><tr><th>Plan</th><th>Max File Size</th><th>Max Pages</th></tr></thead>
        <tbody>
          <tr><td>Starter (Free)</td><td>10 MB</td><td>50 pages</td></tr>
          <tr><td>Pro</td><td>50 MB</td><td>200 pages</td></tr>
          <tr><td>Enterprise</td><td>Unlimited</td><td>Unlimited</td></tr>
        </tbody>
      </table>

      <h2>Processing Pipeline</h2>
      <p>Once uploaded, the document goes through:</p>
      <ol className="docs-list">
        <li><strong>Text extraction</strong> — PyMuPDF (PDF) or python-docx (DOCX) extracts raw text</li>
        <li><strong>Chunking</strong> — LangChain's recursive splitter divides text into 512-token chunks with 64-token overlap</li>
        <li><strong>Embedding</strong> — Each chunk is encoded using <code>all-MiniLM-L6-v2</code> (384 dimensions)</li>
        <li><strong>Indexing</strong> — Vectors are stored in your private FAISS Flat-L2 index</li>
      </ol>

      <div className="docs-callout docs-callout-info">
        <AlertCircle size={16} />
        <span>Uploading a new document replaces the current one. The old index is permanently deleted.</span>
      </div>
    </div>
  ),

  'Text Chat': (
    <div className="docs-article">
      <div className="docs-badge docs-badge-blue">Core Features</div>
      <h1>Text Chat</h1>
      <p className="docs-lead">The Chat interface lets you query your document knowledge base via a streaming text interface.</p>

      <h2>How it works</h2>
      <ol className="docs-list">
        <li>Your message is embedded using the same model as your documents</li>
        <li>Top-5 most relevant chunks are retrieved from your FAISS index</li>
        <li>Retrieved context + your query are sent to Llama 3.3 70B on Groq</li>
        <li>The response streams back token-by-token in real time</li>
      </ol>

      <h2>Chat API endpoint</h2>
      <div className="docs-code-block">
        <div className="docs-code-header"><Terminal size={13} /> HTTP</div>
        <pre><code>{`POST /api/portal/chat
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "What is the return policy?"
}

// Response (streaming)
data: {"token": "Based"}
data: {"token": " on"}
data: {"token": " the"}
...`}</code></pre>
      </div>

      <h2>Hallucination prevention</h2>
      <p>The system prompt explicitly instructs the LLM to answer <em>only</em> from the retrieved context chunks. If the answer is not found in your document, the assistant will say so rather than fabricating information.</p>
    </div>
  ),

  'Voice Assistant': (
    <div className="docs-article">
      <div className="docs-badge docs-badge-blue">Core Features</div>
      <h1>Voice Assistant</h1>
      <p className="docs-lead">The full voice-to-voice pipeline: speech recognition → RAG retrieval → LLM generation → speech synthesis.</p>

      <h2>Pipeline stages & latency</h2>
      <table className="docs-table">
        <thead><tr><th>Stage</th><th>Technology</th><th>Typical Latency</th></tr></thead>
        <tbody>
          <tr><td>Speech-to-Text</td><td>Faster-Whisper large-v3</td><td>0.3 – 0.8s</td></tr>
          <tr><td>RAG Retrieval</td><td>FAISS ANN search</td><td>&lt; 50ms</td></tr>
          <tr><td>LLM Generation</td><td>Groq Llama 3.3 70B</td><td>0.2 – 0.5s</td></tr>
          <tr><td>Text-to-Speech</td><td>Kokoro TTS (82M params)</td><td>0.8 – 1.5s</td></tr>
          <tr><td><strong>Total round-trip</strong></td><td></td><td><strong>2 – 5s</strong></td></tr>
        </tbody>
      </table>

      <h2>WebSocket protocol</h2>
      <p>Voice sessions use a persistent WebSocket connection at <code>/api/voice/ws</code>. Audio is streamed as base64-encoded PCM frames. The server responds with synthesised audio chunks as they are generated.</p>

      <h2>Language detection</h2>
      <p>VoiceRAG supports automatic language detection or manual selection. Whisper detects the spoken language; the TTS engine synthesises the response in the same language. Supported languages include English, Hindi, Urdu, French, Spanish, German, and more.</p>

      <div className="docs-callout docs-callout-info">
        <AlertCircle size={16} />
        <span>Voice is only available on Pro and Enterprise plans. Starter accounts can use text chat.</span>
      </div>
    </div>
  ),

  'Analytics': (
    <div className="docs-article">
      <div className="docs-badge docs-badge-blue">Core Features</div>
      <h1>Analytics</h1>
      <p className="docs-lead">Monitor every query — latency per stage, error rates, session history, and token usage.</p>

      <h2>Dashboard metrics</h2>
      <div className="docs-metrics-grid">
        <div className="docs-metric-card"><BarChart3 size={18} /><strong>Total Queries</strong><span>Chat + voice combined</span></div>
        <div className="docs-metric-card"><BarChart3 size={18} /><strong>Avg Latency</strong><span>End-to-end response time</span></div>
        <div className="docs-metric-card"><BarChart3 size={18} /><strong>Error Rate</strong><span>Failed or timeout queries</span></div>
        <div className="docs-metric-card"><BarChart3 size={18} /><strong>Tokens Used</strong><span>LLM input + output tokens</span></div>
      </div>

      <h2>Per-stage latency breakdown</h2>
      <p>Every query logs individual timings for STT, retrieval, LLM generation, and TTS. View these in the <strong>Conversation Details</strong> drawer by clicking any session row in the Analytics tab.</p>

      <h2>Data retention</h2>
      <p>Analytics data is retained for <strong>30 days</strong> on Starter, <strong>90 days</strong> on Pro, and <strong>unlimited</strong> on Enterprise plans.</p>
    </div>
  ),

  'Embed Widget': (
    <div className="docs-article">
      <div className="docs-badge docs-badge-purple">Integration</div>
      <h1>Embed Widget</h1>
      <p className="docs-lead">One script tag. That's all it takes to deploy your AI assistant on any website.</p>

      <h2>Basic embed</h2>
      <div className="docs-code-block">
        <div className="docs-code-header"><Terminal size={13} /> HTML</div>
        <pre><code>{`<script
  src="https://voicerag.io/widget.js"
  data-key="vr_live_xxxxxxxxxxxx">
</script>`}</code></pre>
      </div>

      <h2>Configuration options</h2>
      <table className="docs-table">
        <thead><tr><th>Attribute</th><th>Values</th><th>Default</th></tr></thead>
        <tbody>
          <tr><td><code>data-key</code></td><td>Your API key</td><td><em>required</em></td></tr>
          <tr><td><code>data-mode</code></td><td><code>"chat"</code> | <code>"voice"</code> | <code>"both"</code></td><td><code>"both"</code></td></tr>
          <tr><td><code>data-position</code></td><td><code>"bottom-right"</code> | <code>"bottom-left"</code></td><td><code>"bottom-right"</code></td></tr>
          <tr><td><code>data-lang</code></td><td>ISO language code (e.g. <code>"en"</code>, <code>"hi"</code>)</td><td><code>"auto"</code></td></tr>
          <tr><td><code>data-theme</code></td><td><code>"light"</code> | <code>"dark"</code></td><td><code>"light"</code></td></tr>
        </tbody>
      </table>

      <h2>Full example</h2>
      <div className="docs-code-block">
        <div className="docs-code-header"><Terminal size={13} /> HTML</div>
        <pre><code>{`<script
  src="https://voicerag.io/widget.js"
  data-key="vr_live_xxxxxxxxxxxx"
  data-mode="voice"
  data-position="bottom-right"
  data-lang="en"
  data-theme="dark">
</script>`}</code></pre>
      </div>

      <div className="docs-callout docs-callout-success">
        <CheckCircle2 size={16} />
        <span>The widget is fully responsive and works on mobile, tablet, and desktop browsers. No additional CSS is required.</span>
      </div>

      <h2>Security</h2>
      <p>Embed API keys are scoped to widget endpoints only. Even if a key is exposed in client-side HTML, it cannot access analytics, upload new documents, or manage account settings.</p>
    </div>
  ),

  'API Reference': (
    <div className="docs-article">
      <div className="docs-badge docs-badge-purple">Integration</div>
      <h1>API Reference</h1>
      <p className="docs-lead">All endpoints, request formats, and response schemas.</p>

      <h2>Base URL</h2>
      <div className="docs-code-block">
        <div className="docs-code-header"><Globe size={13} /> Base URL</div>
        <pre><code>https://voicerag.io/api</code></pre>
      </div>

      <h2>Portal endpoints (JWT)</h2>

      <div className="docs-endpoint">
        <div className="docs-endpoint-badge post">POST</div>
        <code>/auth/register</code>
        <span>Create a new client account</span>
      </div>
      <div className="docs-endpoint">
        <div className="docs-endpoint-badge post">POST</div>
        <code>/auth/login</code>
        <span>Obtain a JWT access token</span>
      </div>
      <div className="docs-endpoint">
        <div className="docs-endpoint-badge post">POST</div>
        <code>/portal/upload</code>
        <span>Upload a document for indexing</span>
      </div>
      <div className="docs-endpoint">
        <div className="docs-endpoint-badge post">POST</div>
        <code>/portal/chat</code>
        <span>Send a text query (streaming response)</span>
      </div>
      <div className="docs-endpoint">
        <div className="docs-endpoint-badge get">GET</div>
        <code>/portal/analytics</code>
        <span>Retrieve session analytics</span>
      </div>
      <div className="docs-endpoint">
        <div className="docs-endpoint-badge get">GET</div>
        <code>/portal/api-keys</code>
        <span>List all embed API keys</span>
      </div>
      <div className="docs-endpoint">
        <div className="docs-endpoint-badge post">POST</div>
        <code>/portal/api-keys</code>
        <span>Generate a new embed API key</span>
      </div>

      <h2>Widget endpoints (API key)</h2>
      <div className="docs-endpoint">
        <div className="docs-endpoint-badge post">POST</div>
        <code>/widget/chat</code>
        <span>Text query via embed widget</span>
      </div>
      <div className="docs-endpoint">
        <div className="docs-endpoint-badge ws">WS</div>
        <code>/widget/voice</code>
        <span>Voice session via WebSocket</span>
      </div>
    </div>
  ),

  'API Keys': (
    <div className="docs-article">
      <div className="docs-badge docs-badge-purple">Integration</div>
      <h1>API Keys</h1>
      <p className="docs-lead">Create and manage scoped embed keys from the API Keys tab in the portal.</p>

      <h2>Creating a key</h2>
      <ol className="docs-list">
        <li>Navigate to <strong>API Keys</strong> in the portal sidebar</li>
        <li>Enter a descriptive name (e.g. "Production Website")</li>
        <li>Click <strong>Generate Key</strong></li>
        <li>Copy the key immediately — it is shown only once</li>
      </ol>

      <div className="docs-callout docs-callout-warning">
        <AlertCircle size={16} />
        <span>Keys cannot be recovered after the initial reveal. If lost, revoke the old key and generate a new one.</span>
      </div>

      <h2>Key format</h2>
      <div className="docs-code-block">
        <div className="docs-code-header"><Key size={13} /> Key format</div>
        <pre><code>vr_live_xxxxxxxxxxxxxxxxxxxxxxxx</code></pre>
      </div>

      <h2>Revoking a key</h2>
      <p>In the API Keys tab, click the <strong>Revoke</strong> button next to any active key. Revoked keys immediately stop working for all embed widgets that use them.</p>

      <h2>Key scope</h2>
      <p>Embed API keys grant access to <code>/widget/chat</code> and <code>/widget/voice</code> only. They cannot be used to upload documents, access analytics, or manage account settings.</p>
    </div>
  ),

  'Multi-Language': (
    <div className="docs-article">
      <div className="docs-badge docs-badge-gray">Advanced</div>
      <h1>Multi-Language Voice</h1>
      <p className="docs-lead">VoiceRAG supports 10+ languages for both speech recognition and synthesis.</p>

      <h2>Supported languages</h2>
      <table className="docs-table">
        <thead><tr><th>Language</th><th>Code</th><th>STT</th><th>TTS</th></tr></thead>
        <tbody>
          {[
            ['English', 'en', '✓', '✓'],
            ['Hindi', 'hi', '✓', '✓'],
            ['Urdu', 'ur', '✓', '✓'],
            ['French', 'fr', '✓', '✓'],
            ['Spanish', 'es', '✓', '✓'],
            ['German', 'de', '✓', '✓'],
            ['Arabic', 'ar', '✓', '✓'],
            ['Portuguese', 'pt', '✓', '✓'],
            ['Japanese', 'ja', '✓', '–'],
            ['Chinese', 'zh', '✓', '–'],
          ].map(([lang, code, stt, tts]) => (
            <tr key={code}><td>{lang}</td><td><code>{code}</code></td><td>{stt}</td><td>{tts}</td></tr>
          ))}
        </tbody>
      </table>

      <h2>Language selection</h2>
      <p>In the Voice tab, use the language selector to choose a specific language or leave it on <strong>Auto</strong> to let Whisper detect automatically. Auto-detection is accurate for most languages with at least 5 seconds of speech.</p>

      <h2>Widget language setting</h2>
      <div className="docs-code-block">
        <div className="docs-code-header"><Terminal size={13} /> HTML</div>
        <pre><code>{`<script
  src="https://voicerag.io/widget.js"
  data-key="vr_live_xxxx"
  data-lang="hi">   <!-- Force Hindi -->
</script>`}</code></pre>
      </div>
    </div>
  ),

  'Pipeline Overview': (
    <div className="docs-article">
      <div className="docs-badge docs-badge-gray">Advanced</div>
      <h1>Pipeline Overview</h1>
      <p className="docs-lead">A technical summary of each stage in the VoiceRAG processing pipeline.</p>

      <div className="docs-pipeline-stages">
        {[
          { num: '01', icon: <FileText size={18} />, title: 'Document Ingestion', desc: 'PyMuPDF / python-docx extract text. LangChain splits into 512-token chunks with 64-token overlap.' },
          { num: '02', icon: <Database size={18} />, title: 'Embedding & Indexing', desc: 'all-MiniLM-L6-v2 encodes each chunk into 384-dimension vectors stored in a per-client FAISS Flat-L2 index.' },
          { num: '03', icon: <Cpu size={18} />, title: 'Semantic Retrieval', desc: 'Query is embedded and ANN-searched against the FAISS index. Top-5 chunks are retrieved and ranked by cosine similarity.' },
          { num: '04', icon: <MessageCircle size={18} />, title: 'LLM Generation', desc: 'Groq Llama 3.3 70B generates a grounded response from retrieved context in under 500ms on Groq LPU hardware.' },
          { num: '05', icon: <Volume2 size={18} />, title: 'Voice Synthesis (optional)', desc: 'Faster-Whisper large-v3 handles STT. Kokoro TTS (82M params) synthesises the response. Full round-trip under 5 seconds.' },
        ].map((s) => (
          <div key={s.num} className="docs-pipeline-stage">
            <div className="docs-pipeline-num">{s.num}</div>
            <div className="docs-pipeline-icon">{s.icon}</div>
            <div>
              <strong>{s.title}</strong>
              <p>{s.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  ),

  'Security & Isolation': (
    <div className="docs-article">
      <div className="docs-badge docs-badge-gray">Advanced</div>
      <h1>Security &amp; Isolation</h1>
      <p className="docs-lead">How VoiceRAG keeps your data private and prevents cross-tenant exposure.</p>

      <h2>Per-client vector stores</h2>
      <p>Every account has its own dedicated FAISS index stored under a unique client UUID directory. Retrieval queries are always scoped to the authenticated client's index — there is no shared or pooled vector store.</p>

      <h2>API key scoping</h2>
      <p>Portal JWTs and embed API keys are separate credential types with different permission scopes. Embed keys cannot read analytics, upload documents, or access any admin endpoint.</p>

      <h2>Admin isolation</h2>
      <p>The admin panel (accessible via <code>/#admin</code> with admin credentials) has read access to usage aggregates but cannot read the content of any client's documents or conversation history.</p>

      <div className="docs-callout docs-callout-success">
        <CheckCircle2 size={16} />
        <span>All API communication is HTTPS. Passwords are hashed with bcrypt before storage. No plaintext credentials are ever logged.</span>
      </div>

      <h2>Data deletion</h2>
      <p>Uploading a new document permanently deletes the previous document's chunks and FAISS index from disk. Deleted data cannot be recovered. Account deletion purges all associated data within 24 hours.</p>
    </div>
  ),
};

const ALL_ITEMS = NAV.flatMap((s) => s.items);

export default function DocsPage({ onNavigate }) {
  const [active, setActive] = useState('Quick Start');
  const content = CONTENT[active] || CONTENT['Quick Start'];

  return (
    <div className="pro-landing" style={{ minHeight: '100vh' }}>

      {/* ── Navigation ── */}
      <nav className="pro-landing-nav">
        <div className="pro-nav-container">
          <div className="landing-brand" onClick={() => onNavigate('landing')} style={{ cursor: 'pointer' }}>
            <div className="landing-brand-icon"><Mic size={18} /></div>
            <span>VoiceRAG</span>
          </div>
          <div className="pro-nav-menu">
            <span className="pro-nav-item" onClick={() => onNavigate('landing')}>Features</span>
            <span className="pro-nav-item" onClick={() => onNavigate('pipeline')}>Pipeline</span>
            <span className="pro-nav-item" onClick={() => onNavigate('pricing')}>Pricing</span>
            <span className="pro-nav-item" style={{ color: 'var(--accent-secondary)' }}>Docs</span>
          </div>
          <div className="pro-nav-actions">
            <button onClick={() => onNavigate('auth')} className="pro-nav-signin">Sign In</button>
            <button onClick={() => onNavigate('auth')} className="pro-btn pro-btn-primary pro-btn-sm">Get Started Free</button>
          </div>
        </div>
      </nav>

      {/* ── Docs Layout ── */}
      <div className="docs-layout">

        {/* Sidebar */}
        <aside className="docs-sidebar">
          <div className="docs-sidebar-inner">
            {NAV.map((sec) => (
              <div key={sec.section} className="docs-nav-section">
                <div className="docs-nav-section-title">{sec.section}</div>
                {sec.items.map((item) => (
                  <button
                    key={item}
                    className={`docs-nav-item${active === item ? ' active' : ''}`}
                    onClick={() => setActive(item)}
                  >
                    {item}
                  </button>
                ))}
              </div>
            ))}
          </div>
        </aside>

        {/* Content */}
        <main className="docs-content">
          {content}

          {/* Prev / Next navigation */}
          <div className="docs-pagination">
            {ALL_ITEMS.indexOf(active) > 0 && (
              <button
                className="docs-page-btn docs-page-prev"
                onClick={() => setActive(ALL_ITEMS[ALL_ITEMS.indexOf(active) - 1])}
              >
                ← {ALL_ITEMS[ALL_ITEMS.indexOf(active) - 1]}
              </button>
            )}
            {ALL_ITEMS.indexOf(active) < ALL_ITEMS.length - 1 && (
              <button
                className="docs-page-btn docs-page-next"
                onClick={() => setActive(ALL_ITEMS[ALL_ITEMS.indexOf(active) + 1])}
              >
                {ALL_ITEMS[ALL_ITEMS.indexOf(active) + 1]} →
              </button>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
