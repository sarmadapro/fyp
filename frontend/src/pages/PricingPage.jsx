import { ArrowRight, Check, Mic, Zap, Shield, Headphones, Building2, X } from 'lucide-react';

const TIERS = [
  {
    name: 'Starter',
    price: 'Free',
    period: '',
    badge: null,
    description: 'Perfect for exploring VoiceRAG and building your first AI assistant.',
    cta: 'Get Started Free',
    ctaStyle: 'secondary',
    features: [
      { text: '500 queries / month', included: true },
      { text: '1 document (up to 50 pages)', included: true },
      { text: 'Text chat interface', included: true },
      { text: 'Basic analytics dashboard', included: true },
      { text: 'Embeddable widget (1 site)', included: true },
      { text: 'Community support', included: true },
      { text: 'Voice assistant', included: false },
      { text: 'Advanced analytics', included: false },
      { text: 'Priority support', included: false },
      { text: 'Custom branding', included: false },
    ],
  },
  {
    name: 'Pro',
    price: '$29',
    period: '/ month',
    badge: 'Most Popular',
    description: 'For teams deploying AI voice agents to real customers at scale.',
    cta: 'Start Pro Trial',
    ctaStyle: 'primary',
    features: [
      { text: 'Unlimited queries', included: true },
      { text: '10 documents (up to 200 pages each)', included: true },
      { text: 'Text chat + Voice assistant', included: true },
      { text: 'Full analytics with latency breakdown', included: true },
      { text: 'Embeddable widget (unlimited sites)', included: true },
      { text: 'Email support', included: true },
      { text: 'Multi-language voice (10+ langs)', included: true },
      { text: 'Custom assistant branding', included: true },
      { text: 'Priority support', included: false },
      { text: 'SLA guarantee', included: false },
    ],
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    badge: null,
    description: 'Tailored infrastructure for large organisations with strict requirements.',
    cta: 'Contact Sales',
    ctaStyle: 'secondary',
    features: [
      { text: 'Unlimited queries', included: true },
      { text: 'Unlimited documents', included: true },
      { text: 'Text chat + Voice assistant', included: true },
      { text: 'Custom analytics & reporting', included: true },
      { text: 'White label widget', included: true },
      { text: 'Dedicated support engineer', included: true },
      { text: 'Multi language voice (10+ langs)', included: true },
      { text: 'Custom branding & domain', included: true },
      { text: 'Priority support + SLA', included: true },
      { text: 'Custom LLM / on-prem deployment', included: true },
    ],
  },
];

const FAQS = [
  {
    q: 'Can I switch plans later?',
    a: 'Yes. You can upgrade or downgrade at any time from your dashboard. Changes take effect immediately and are prorated to your billing cycle.',
  },
  {
    q: 'What counts as a "query"?',
    a: 'Each message sent to the AI assistant via text or voice counts as one query. Follow-up messages in the same conversation each count separately.',
  },
  {
    q: 'What file types can I upload?',
    a: 'We support PDF, DOCX, and TXT files. For best results, use PDFs with selectable text (not scanned images). Scanned-PDF OCR is on our roadmap.',
  },
  {
    q: 'Is my data private and isolated?',
    a: 'Absolutely. Every account gets a separate FAISS vector index. Your documents are never shared with or accessible by any other tenant.',
  },
  {
    q: 'How does the embed widget work?',
    a: 'Paste a single <script> tag into your website\'s HTML. The widget appears as a floating chat/voice button. No backend setup is needed on your side.',
  },
  {
    q: 'Do you offer a free trial on Pro?',
    a: 'Yes — the Pro plan includes a 14-day free trial with no credit card required. Full access to all Pro features from day one.',
  },
];

export default function PricingPage({ onNavigate }) {
  return (
    <div className="pro-landing">
      <div className="glow-bg" />

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
            <span className="pro-nav-item" style={{ color: 'var(--accent-secondary)' }}>Pricing</span>
            <span className="pro-nav-item" onClick={() => onNavigate('docs')}>Docs</span>
          </div>
          <div className="pro-nav-actions">
            <button onClick={() => onNavigate('auth')} className="pro-nav-signin">Sign In</button>
            <button onClick={() => onNavigate('auth')} className="pro-btn pro-btn-primary pro-btn-sm">Get Started Free</button>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="pro-hero" style={{ paddingBottom: '60px' }}>
        <div className="pro-hero-eyebrow">Transparent Pricing</div>
        <div className="pro-hero-badge">
          <span>Free</span> 14-day Pro trial no credit card required
        </div>
        <h1 className="pro-hero-title">
          Simple pricing.<br />
          <span className="hero-gradient-text">No surprises.</span>
        </h1>
        <p className="pro-hero-subtitle">
          Start free and scale when you're ready. Every plan includes your own isolated knowledge base and the same production grade RAG pipeline.
        </p>
      </section>

      {/* ── Pricing Cards ── */}
      <section className="pricing-section">
        <div className="pricing-grid">
          {TIERS.map((tier) => (
            <div
              key={tier.name}
              className={`pricing-card${tier.badge ? ' pricing-card-featured' : ''}`}
            >
              {tier.badge && (
                <div className="pricing-badge">{tier.badge}</div>
              )}
              <div className="pricing-tier-name">{tier.name}</div>
              <div className="pricing-price-row">
                <span className="pricing-price">{tier.price}</span>
                {tier.period && <span className="pricing-period">{tier.period}</span>}
              </div>
              <p className="pricing-desc">{tier.description}</p>

              <button
                className={`pricing-cta pro-btn ${tier.ctaStyle === 'primary' ? 'pro-btn-primary' : 'pricing-cta-secondary'}`}
                onClick={() => onNavigate('auth')}
              >
                {tier.cta} {tier.ctaStyle === 'primary' && <ArrowRight size={16} />}
              </button>

              <div className="pricing-divider" />

              <ul className="pricing-features">
                {tier.features.map((f, i) => (
                  <li key={i} className={`pricing-feature${f.included ? '' : ' pricing-feature-off'}`}>
                    {f.included
                      ? <Check size={15} className="pricing-check" />
                      : <X size={15} className="pricing-x" />
                    }
                    {f.text}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* ── All-plan Perks ── */}
      <section className="perks-section">
        <div className="section-container">
          <h2 className="perks-title">Every plan includes</h2>
          <div className="perks-grid">
            <div className="perk-item">
              <div className="perk-icon"><Shield size={20} /></div>
              <div className="perk-text">
                <strong>Per client data isolation</strong>
                <span>Separate FAISS index per account zero cross tenant exposure.</span>
              </div>
            </div>
            <div className="perk-item">
              <div className="perk-icon"><Zap size={20} /></div>
              <div className="perk-text">
                <strong>Groq LPU inference</strong>
                <span>Sub-500ms LLM generation on Groq's purpose built hardware.</span>
              </div>
            </div>
            <div className="perk-item">
              <div className="perk-icon"><Headphones size={20} /></div>
              <div className="perk-text">
                <strong>Embed widget included</strong>
                <span>One script tag deploys your AI assistant to any website instantly.</span>
              </div>
            </div>
            <div className="perk-item">
              <div className="perk-icon"><Building2 size={20} /></div>
              <div className="perk-text">
                <strong>99.9% uptime SLA</strong>
                <span>Production grade infrastructure with continuous monitoring.</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── FAQ ── */}
      <section className="faq-section">
        <div className="section-container">
          <div className="section-eyebrow">FAQ</div>
          <h2 className="faq-title">Frequently asked questions</h2>
          <div className="faq-grid">
            {FAQS.map((item, i) => (
              <div key={i} className="faq-item">
                <h3 className="faq-q">{item.q}</h3>
                <p className="faq-a">{item.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="pro-cta">
        <div className="pro-cta-inner">
          <h2>Start building for free today.</h2>
          <p>No credit card required. Upgrade when your usage grows.</p>
          <div className="pro-cta-actions">
            <button onClick={() => onNavigate('auth')} className="pro-btn pro-btn-primary pro-btn-lg">
              Create Free Account <ArrowRight size={18} />
            </button>
            <button onClick={() => onNavigate('docs')} className="pro-btn pro-btn-secondary">
              Read the Docs
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
                Intelligent AI voice agents trained on your data. Deploy in minutes, answer accurately always.
              </p>
            </div>
            <div className="footer-links-col">
              <div className="footer-col-title">Product</div>
              <div className="footer-col-links">
                <span className="footer-col-link" onClick={() => onNavigate('landing')}>Features</span>
                <span className="footer-col-link" onClick={() => onNavigate('pipeline')}>Pipeline Architecture</span>
                <span className="footer-col-link" onClick={() => onNavigate('pricing')}>Pricing</span>
                <span className="footer-col-link">Analytics</span>
              </div>
            </div>
            <div className="footer-links-col">
              <div className="footer-col-title">Developers</div>
              <div className="footer-col-links">
                <span className="footer-col-link" onClick={() => onNavigate('docs')}>Documentation</span>
                <span className="footer-col-link">API Reference</span>
                <span className="footer-col-link">Embed Guide</span>
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
            <span>© 2026 VoiceRAG Inc. All rights reserved.</span>
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
