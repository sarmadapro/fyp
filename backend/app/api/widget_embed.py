"""
Serves the embeddable chat widget JavaScript file.
Clients add <script src="http://server/widget.js" data-api-key="vrag_xxx"></script>
"""

from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter(tags=["Widget Embed"])


WIDGET_JS = r"""
(function () {
  'use strict';

  /* ── Bootstrap ─────────────────────────────────────────────── */
  if (document.getElementById('vrag-root')) return; // prevent double-init

  const script  = document.currentScript || document.querySelector('script[data-api-key]');
  if (!script)  { console.error('[VoiceRAG] Script tag not found'); return; }

  const API_KEY  = script.getAttribute('data-api-key');
  const API_URL  = (script.getAttribute('data-api-url') || script.src.replace(/\/widget\.js.*/, '')).replace(/\/$/, '');
  const SIDE     = script.getAttribute('data-position') || 'right';
  const DARK     = script.getAttribute('data-theme') !== 'light';

  if (!API_KEY) { console.error('[VoiceRAG] data-api-key attribute is required'); return; }

  /* ── CSS ────────────────────────────────────────────────────── */
  const css = `
    #vrag-root *, #vrag-root *::before, #vrag-root *::after {
      box-sizing: border-box; margin: 0; padding: 0; border: none; outline: none;
    }
    #vrag-root {
      --p:  #6c5ce7;
      --p2: #00cec9;
      --pg: linear-gradient(135deg,#6c5ce7 0%,#5a4bd1 50%,#00cec9 100%);
      --bg:  ${DARK ? '#111118' : '#ffffff'};
      --bg2: ${DARK ? '#1c1c28' : '#f4f4f8'};
      --bg3: ${DARK ? '#252535' : '#ebebf2'};
      --tx:  ${DARK ? '#e4e4f0' : '#111120'};
      --tx2: ${DARK ? '#8888a8' : '#666678'};
      --bd:  ${DARK ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.09)'};
      --sh:  0 20px 60px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.05);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
      position: fixed;
      bottom: 24px;
      ${SIDE === 'left' ? 'left:24px' : 'right:24px'};
      z-index: 2147483647;
      display: flex;
      flex-direction: column;
      align-items: ${SIDE === 'left' ? 'flex-start' : 'flex-end'};
      gap: 14px;
    }

    /* ─── Toggle ───────────────────────────────────────────────── */
    #vrag-btn {
      width: 52px; height: 52px; border-radius: 50%;
      background: var(--pg);
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      box-shadow: 0 4px 20px rgba(108,92,231,0.5);
      transition: transform .25s cubic-bezier(.34,1.56,.64,1), box-shadow .25s ease;
      position: relative;
      background-color: transparent;
    }
    #vrag-btn:hover { transform: scale(1.1); box-shadow: 0 6px 28px rgba(108,92,231,0.6); }
    #vrag-btn-icon { transition: transform .3s ease; }
    #vrag-btn.open #vrag-btn-icon { transform: rotate(90deg); }
    #vrag-dot {
      position: absolute; top: 0; right: 0;
      width: 12px; height: 12px; border-radius: 50%;
      background: #ff4757; border: 2px solid var(--bg);
      display: none;
    }
    #vrag-dot.on { display: block; animation: vrag-pop .3s cubic-bezier(.34,1.56,.64,1); }
    @keyframes vrag-pop { from{transform:scale(0)} to{transform:scale(1)} }

    /* ─── Window ────────────────────────────────────────────────── */
    #vrag-win {
      width: 365px;
      background: var(--bg);
      border-radius: 20px;
      border: 1px solid var(--bd);
      box-shadow: var(--sh);
      display: none; flex-direction: column;
      overflow: hidden;
      transform-origin: bottom ${SIDE === 'left' ? 'left' : 'right'};
    }
    #vrag-win.open {
      display: flex;
      animation: vrag-open .3s cubic-bezier(.34,1.56,.64,1);
    }
    @keyframes vrag-open {
      from { opacity:0; transform:scale(.88) translateY(16px); }
      to   { opacity:1; transform:scale(1)   translateY(0); }
    }

    /* ─── Header ────────────────────────────────────────────────── */
    #vrag-head {
      padding: 14px 16px;
      background: var(--pg);
      display: flex; align-items: center; gap: 10px;
      flex-shrink: 0;
    }
    #vrag-avatar {
      width: 36px; height: 36px; border-radius: 50%;
      background: rgba(255,255,255,0.18);
      display: flex; align-items: center; justify-content: center;
      font-size: 17px; flex-shrink: 0; color: #fff;
      font-weight: 600; letter-spacing: -0.5px;
    }
    #vrag-head-text { flex: 1; min-width: 0; }
    #vrag-name {
      font-size: 14px; font-weight: 600; color: #fff;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    #vrag-status {
      font-size: 11px; color: rgba(255,255,255,0.75);
      display: flex; align-items: center; gap: 5px; margin-top: 2px;
    }
    #vrag-status-dot {
      width: 6px; height: 6px; border-radius: 50%;
      background: #51cf66;
      box-shadow: 0 0 6px rgba(81,207,102,0.9);
    }
    #vrag-x {
      width: 28px; height: 28px; border-radius: 50%;
      background: rgba(255,255,255,0.16);
      cursor: pointer; color: #fff;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0; transition: background .2s;
      font-size: 15px; line-height: 1; background-color: transparent;
    }
    #vrag-x:hover { background: rgba(255,255,255,0.28); }

    /* ─── Messages ──────────────────────────────────────────────── */
    #vrag-msgs {
      flex: 1; overflow-y: auto;
      padding: 16px; display: flex; flex-direction: column; gap: 10px;
      min-height: 280px; max-height: 360px;
      scrollbar-width: thin; scrollbar-color: var(--bg3) transparent;
    }
    #vrag-msgs::-webkit-scrollbar { width: 4px; }
    #vrag-msgs::-webkit-scrollbar-thumb { background: var(--bg3); border-radius: 4px; }

    .vb {
      max-width: 83%;
      padding: 9px 13px; border-radius: 16px;
      font-size: 13px; line-height: 1.55; word-wrap: break-word;
      animation: vrag-msg .2s ease-out;
    }
    @keyframes vrag-msg {
      from { opacity:0; transform:translateY(6px); }
      to   { opacity:1; transform:translateY(0); }
    }
    .vb.u { align-self:flex-end; background:var(--pg); color:#fff; border-bottom-right-radius:4px; }
    .vb.a { align-self:flex-start; background:var(--bg2); color:var(--tx); border:1px solid var(--bd); border-bottom-left-radius:4px; }
    .vb.e { align-self:flex-start; background:rgba(255,71,87,0.1); color:#ff6b6b; border:1px solid rgba(255,71,87,0.2); border-bottom-left-radius:4px; font-size:12px; }

    /* typing dots */
    .vdots { display:inline-flex; gap:4px; align-items:center; height:16px; }
    .vd {
      width:6px; height:6px; border-radius:50%; background:var(--tx2);
      animation:vrag-dot 1.3s ease-in-out infinite;
    }
    .vd:nth-child(2){animation-delay:.15s} .vd:nth-child(3){animation-delay:.3s}
    @keyframes vrag-dot {
      0%,60%,100%{transform:translateY(0);opacity:.4}
      30%{transform:translateY(-5px);opacity:1}
    }

    /* ─── Input ─────────────────────────────────────────────────── */
    #vrag-foot {
      padding: 10px 12px 12px;
      border-top: 1px solid var(--bd);
      display: flex; align-items: flex-end; gap: 8px;
      background: var(--bg); flex-shrink: 0;
    }
    #vrag-in {
      flex: 1;
      padding: 9px 14px;
      border-radius: 22px;
      border: 1px solid var(--bd);
      background: var(--bg2);
      color: var(--tx);
      font-size: 13px; font-family: inherit;
      resize: none; min-height: 38px; max-height: 96px;
      line-height: 1.45; transition: border-color .2s;
      background-color: var(--bg2);
    }
    #vrag-in:focus { border-color: var(--p); }
    #vrag-in::placeholder { color: var(--tx2); }
    #vrag-go {
      width: 38px; height: 38px; border-radius: 50%; flex-shrink: 0;
      background: var(--pg);
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      box-shadow: 0 2px 10px rgba(108,92,231,0.4);
      transition: transform .2s, opacity .2s;
      background-color: transparent;
    }
    #vrag-go:hover:not([disabled]) { transform: scale(1.1); }
    #vrag-go[disabled] { opacity: .4; cursor: not-allowed; }
    #vrag-go svg { width:15px; height:15px; }

    /* ─── Powered by ────────────────────────────────────────────── */
    #vrag-pw {
      text-align: center; padding: 5px 0 8px;
      font-size: 10px; color: var(--tx2); opacity: .45;
      letter-spacing: .03em; flex-shrink: 0;
    }

    @media (max-width: 420px) {
      #vrag-win { width: calc(100vw - 20px); border-radius: 16px; }
    }
  `;

  const sEl = document.createElement('style');
  sEl.textContent = css;
  document.head.appendChild(sEl);

  /* ── DOM ──────────────────────────────────────────────────────── */
  const root = document.createElement('div');
  root.id = 'vrag-root';
  root.innerHTML = `
    <div id="vrag-win">
      <div id="vrag-head">
        <div id="vrag-avatar">AI</div>
        <div id="vrag-head-text">
          <div id="vrag-name">AI Assistant</div>
          <div id="vrag-status">
            <div id="vrag-status-dot"></div>
            <span>Online · Ready to help</span>
          </div>
        </div>
        <button id="vrag-x" title="Close">&#x2715;</button>
      </div>
      <div id="vrag-msgs">
        <div class="vb a">Hi! How can I help you today?</div>
      </div>
      <div id="vrag-foot">
        <textarea id="vrag-in" rows="1" placeholder="Type a message…" autocomplete="off"></textarea>
        <button id="vrag-go" title="Send">
          <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
      <div id="vrag-pw">Powered by VoiceRAG</div>
    </div>
    <button id="vrag-btn" title="Chat with us">
      <div id="vrag-dot"></div>
      <span id="vrag-btn-icon">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="#fff">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
      </span>
    </button>
  `;
  document.body.appendChild(root);

  /* ── Refs ─────────────────────────────────────────────────────── */
  const $win  = document.getElementById('vrag-win');
  const $btn  = document.getElementById('vrag-btn');
  const $x    = document.getElementById('vrag-x');
  const $msgs = document.getElementById('vrag-msgs');
  const $in   = document.getElementById('vrag-in');
  const $go   = document.getElementById('vrag-go');
  const $dot  = document.getElementById('vrag-dot');
  const $name = document.getElementById('vrag-name');
  const $av   = document.getElementById('vrag-avatar');

  /* ── State ────────────────────────────────────────────────────── */
  let sid   = null;   // session id
  let busy  = false;
  let open  = false;

  /* ── Open / Close ─────────────────────────────────────────────── */
  function openWin() {
    open = true;
    $win.classList.add('open');
    $btn.classList.add('open');
    $dot.classList.remove('on');
    setTimeout(() => $in.focus(), 60);
  }
  function closeWin() {
    open = false;
    $win.classList.remove('open');
    $btn.classList.remove('open');
  }
  $btn.addEventListener('click', () => open ? closeWin() : openWin());
  $x.addEventListener('click', closeWin);

  /* ── Messages ─────────────────────────────────────────────────── */
  function addMsg(text, cls) {
    const el = document.createElement('div');
    el.className = 'vb ' + cls;
    el.textContent = text;
    $msgs.appendChild(el);
    $msgs.scrollTop = $msgs.scrollHeight;
  }

  function showTyping() {
    const el = document.createElement('div');
    el.className = 'vb a'; el.id = 'vrag-tp';
    el.innerHTML = '<div class="vdots"><div class="vd"></div><div class="vd"></div><div class="vd"></div></div>';
    $msgs.appendChild(el);
    $msgs.scrollTop = $msgs.scrollHeight;
  }
  function hideTyping() { document.getElementById('vrag-tp')?.remove(); }

  /* Auto-grow textarea */
  $in.addEventListener('input', () => {
    $in.style.height = 'auto';
    $in.style.height = Math.min($in.scrollHeight, 96) + 'px';
  });

  /* ── Send ─────────────────────────────────────────────────────── */
  async function send() {
    const text = $in.value.trim();
    if (!text || busy) return;

    $in.value = ''; $in.style.height = 'auto';
    busy = true; $go.setAttribute('disabled', '');

    addMsg(text, 'u');
    showTyping();

    try {
      const res = await fetch(API_URL + '/widget/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
        body: JSON.stringify({ message: text, session_id: sid }),
      });

      hideTyping();

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        addMsg(err.detail || 'Something went wrong. Please try again.', 'e');
      } else {
        const data = await res.json();
        sid = data.session_id;
        addMsg(data.answer, 'a');
        if (!open) $dot.classList.add('on');
      }
    } catch (_) {
      hideTyping();
      addMsg('Unable to reach the server. Please try again.', 'e');
    } finally {
      busy = false; $go.removeAttribute('disabled'); $in.focus();
    }
  }

  $go.addEventListener('click', send);
  $in.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });

  /* ── Config ───────────────────────────────────────────────────── */
  (async () => {
    try {
      const res = await fetch(API_URL + '/widget/config', {
        headers: { 'X-API-Key': API_KEY },
      });
      if (!res.ok) return;
      const cfg = await res.json();
      if (cfg.company_name) {
        const first = cfg.company_name.trim()[0].toUpperCase();
        $name.textContent = cfg.company_name + ' Assistant';
        $av.textContent = first;
      }
    } catch (_) {}
  })();

  console.log('[VoiceRAG] Widget ready');
})();
""".strip()


@router.get("/widget.js")
def serve_widget():
    """Serve the embeddable chat widget JavaScript."""
    return Response(
        content=WIDGET_JS,
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )
