"""
Serves the embeddable chat widget JavaScript file.
Clients add <script src="http://server/widget.js" data-api-key="vrag_xxx"></script>
"""

from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter(tags=["Widget Embed"])


WIDGET_JS = """
(function() {
  'use strict';

  // Find the script tag to get config
  const scriptTag = document.currentScript || document.querySelector('script[data-api-key]');
  if (!scriptTag) { console.error('VoiceRAG: Script tag not found'); return; }

  const API_KEY = scriptTag.getAttribute('data-api-key');
  const API_URL = scriptTag.getAttribute('data-api-url') || scriptTag.src.replace(/\\/widget\\.js.*/, '');
  const POSITION = scriptTag.getAttribute('data-position') || 'right';
  const THEME = scriptTag.getAttribute('data-theme') || 'dark';

  if (!API_KEY) { console.error('VoiceRAG: data-api-key attribute is required'); return; }

  // Inject styles
  const style = document.createElement('style');
  style.textContent = `
    #vrag-widget-container * { box-sizing: border-box; margin: 0; padding: 0; }
    #vrag-widget-container {
      --vrag-primary: #6c5ce7;
      --vrag-primary-hover: #5a4bd1;
      --vrag-bg: ${THEME === 'light' ? '#ffffff' : '#1a1a2e'};
      --vrag-bg-secondary: ${THEME === 'light' ? '#f5f5f8' : '#16213e'};
      --vrag-text: ${THEME === 'light' ? '#1a1a2e' : '#e8e8f0'};
      --vrag-text-secondary: ${THEME === 'light' ? '#666' : '#a0a0b8'};
      --vrag-border: ${THEME === 'light' ? '#e0e0e8' : 'rgba(255,255,255,0.08)'};
      --vrag-shadow: 0 8px 32px rgba(0,0,0,0.3);
      --vrag-radius: 16px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
      position: fixed;
      bottom: 20px;
      ${POSITION === 'left' ? 'left: 20px' : 'right: 20px'};
      z-index: 999999;
    }

    #vrag-toggle {
      width: 56px; height: 56px;
      border-radius: 50%;
      background: linear-gradient(135deg, #6c5ce7, #00cec9);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 20px rgba(108, 92, 231, 0.4);
      transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    #vrag-toggle:hover { transform: scale(1.1); box-shadow: 0 6px 28px rgba(108, 92, 231, 0.5); }
    #vrag-toggle svg { width: 24px; height: 24px; fill: white; }

    #vrag-chat-window {
      display: none;
      position: absolute;
      bottom: 70px;
      ${POSITION === 'left' ? 'left: 0' : 'right: 0'};
      width: 380px;
      max-height: 520px;
      background: var(--vrag-bg);
      border-radius: var(--vrag-radius);
      border: 1px solid var(--vrag-border);
      box-shadow: var(--vrag-shadow);
      flex-direction: column;
      overflow: hidden;
      animation: vragSlideUp 0.3s ease-out;
    }
    #vrag-chat-window.open { display: flex; }

    @keyframes vragSlideUp {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .vrag-header {
      padding: 16px 20px;
      background: linear-gradient(135deg, #6c5ce7, #00cec9);
      color: white;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .vrag-header-title { font-size: 15px; font-weight: 600; }
    .vrag-header-sub { font-size: 11px; opacity: 0.8; margin-top: 2px; }
    .vrag-close-btn {
      background: rgba(255,255,255,0.2);
      border: none;
      color: white;
      width: 28px; height: 28px;
      border-radius: 50%;
      cursor: pointer;
      font-size: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s;
    }
    .vrag-close-btn:hover { background: rgba(255,255,255,0.3); }

    .vrag-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      min-height: 300px;
      max-height: 360px;
    }

    .vrag-msg {
      max-width: 85%;
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 13px;
      line-height: 1.5;
      word-wrap: break-word;
      animation: vragMsgIn 0.2s ease-out;
    }
    @keyframes vragMsgIn {
      from { opacity: 0; transform: translateY(5px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .vrag-msg.user {
      align-self: flex-end;
      background: var(--vrag-primary);
      color: white;
      border-bottom-right-radius: 4px;
    }
    .vrag-msg.ai {
      align-self: flex-start;
      background: var(--vrag-bg-secondary);
      color: var(--vrag-text);
      border: 1px solid var(--vrag-border);
      border-bottom-left-radius: 4px;
    }

    .vrag-msg.typing .vrag-dots { display: inline-flex; gap: 4px; }
    .vrag-msg.typing .vrag-dot {
      width: 6px; height: 6px;
      background: var(--vrag-text-secondary);
      border-radius: 50%;
      animation: vragBounce 1.4s ease-in-out infinite;
    }
    .vrag-msg.typing .vrag-dot:nth-child(2) { animation-delay: 0.2s; }
    .vrag-msg.typing .vrag-dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes vragBounce {
      0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
      40% { transform: scale(1); opacity: 1; }
    }

    .vrag-input-area {
      padding: 12px 16px;
      border-top: 1px solid var(--vrag-border);
      display: flex;
      gap: 8px;
      background: var(--vrag-bg);
    }
    .vrag-input {
      flex: 1;
      padding: 10px 14px;
      border-radius: 10px;
      border: 1px solid var(--vrag-border);
      background: var(--vrag-bg-secondary);
      color: var(--vrag-text);
      font-size: 13px;
      font-family: inherit;
      outline: none;
      transition: border-color 0.2s;
    }
    .vrag-input:focus { border-color: var(--vrag-primary); }
    .vrag-input::placeholder { color: var(--vrag-text-secondary); }

    .vrag-send {
      width: 38px; height: 38px;
      border-radius: 10px;
      background: var(--vrag-primary);
      color: white;
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s;
      flex-shrink: 0;
    }
    .vrag-send:hover { background: var(--vrag-primary-hover); }
    .vrag-send:disabled { opacity: 0.5; cursor: not-allowed; }
    .vrag-send svg { width: 16px; height: 16px; }

    .vrag-powered {
      text-align: center;
      padding: 6px;
      font-size: 10px;
      color: var(--vrag-text-secondary);
      opacity: 0.6;
    }

    @media (max-width: 440px) {
      #vrag-chat-window { width: calc(100vw - 40px); }
    }
  `;
  document.head.appendChild(style);

  // Build DOM
  const container = document.createElement('div');
  container.id = 'vrag-widget-container';

  container.innerHTML = `
    <div id="vrag-chat-window">
      <div class="vrag-header">
        <div>
          <div class="vrag-header-title">AI Assistant</div>
          <div class="vrag-header-sub">Powered by VoiceRAG</div>
        </div>
        <button class="vrag-close-btn" id="vrag-close">&times;</button>
      </div>
      <div class="vrag-messages" id="vrag-messages">
        <div class="vrag-msg ai">Hi! How can I help you today?</div>
      </div>
      <div class="vrag-input-area">
        <input class="vrag-input" id="vrag-input" placeholder="Type a message..." autocomplete="off" />
        <button class="vrag-send" id="vrag-send">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="m22 2-7 20-4-9-9-4z"/><path d="m22 2-11 11"/>
          </svg>
        </button>
      </div>
      <div class="vrag-powered">Powered by VoiceRAG</div>
    </div>
    <button id="vrag-toggle">
      <svg viewBox="0 0 24 24"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
    </button>
  `;

  document.body.appendChild(container);

  // State
  let sessionId = null;
  let isOpen = false;

  const toggle = document.getElementById('vrag-toggle');
  const chatWindow = document.getElementById('vrag-chat-window');
  const closeBtn = document.getElementById('vrag-close');
  const messagesEl = document.getElementById('vrag-messages');
  const input = document.getElementById('vrag-input');
  const sendBtn = document.getElementById('vrag-send');

  // Toggle chat
  function toggleChat() {
    isOpen = !isOpen;
    chatWindow.classList.toggle('open', isOpen);
    if (isOpen) input.focus();
  }
  toggle.addEventListener('click', toggleChat);
  closeBtn.addEventListener('click', toggleChat);

  // Add message to UI
  function addMessage(text, type) {
    const msg = document.createElement('div');
    msg.className = 'vrag-msg ' + type;
    msg.textContent = text;
    messagesEl.appendChild(msg);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return msg;
  }

  function showTyping() {
    const msg = document.createElement('div');
    msg.className = 'vrag-msg ai typing';
    msg.id = 'vrag-typing';
    msg.innerHTML = '<div class="vrag-dots"><div class="vrag-dot"></div><div class="vrag-dot"></div><div class="vrag-dot"></div></div>';
    messagesEl.appendChild(msg);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function hideTyping() {
    const el = document.getElementById('vrag-typing');
    if (el) el.remove();
  }

  // Send message
  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    addMessage(text, 'user');
    sendBtn.disabled = true;
    showTyping();

    try {
      const res = await fetch(API_URL + '/widget/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': API_KEY,
        },
        body: JSON.stringify({
          message: text,
          session_id: sessionId,
        }),
      });

      hideTyping();

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        addMessage(err.detail || 'Something went wrong. Please try again.', 'ai');
        return;
      }

      const data = await res.json();
      sessionId = data.session_id;
      addMessage(data.answer, 'ai');
    } catch (e) {
      hideTyping();
      addMessage('Connection error. Please check your internet.', 'ai');
    } finally {
      sendBtn.disabled = false;
    }
  }

  sendBtn.addEventListener('click', sendMessage);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Fetch config to customize header
  (async function() {
    try {
      const res = await fetch(API_URL + '/widget/config', {
        headers: { 'X-API-Key': API_KEY },
      });
      if (res.ok) {
        const cfg = await res.json();
        if (cfg.company_name) {
          container.querySelector('.vrag-header-title').textContent = cfg.company_name + ' Assistant';
        }
      }
    } catch(e) {}
  })();

  console.log('VoiceRAG Widget loaded successfully');
})();
""".strip()


@router.get("/widget.js")
def serve_widget():
    """Serve the embeddable chat widget JavaScript."""
    return Response(
        content=WIDGET_JS,
        media_type="application/javascript",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        },
    )
