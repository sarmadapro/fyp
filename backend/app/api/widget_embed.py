"""
Serves the embeddable chat widget JavaScript.
Add to any website: <script src="https://your-server/widget.js" data-api-key="vrag_xxx"></script>
"""

from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter(tags=["Widget Embed"])


WIDGET_JS = r"""
/* VoiceRAG Embeddable Widget v3 — Real-time Voice + Text Chat */
(function () {
  'use strict';

  if (document.getElementById('vrag-root')) return;

  var script = document.currentScript || document.querySelector('script[data-api-key]');
  if (!script) { console.error('[VoiceRAG] Script tag not found'); return; }

  var API_KEY = script.getAttribute('data-api-key');
  var API_URL = (script.getAttribute('data-api-url') || script.src.replace(/\/widget\.js.*/, '')).replace(/\/$/, '');
  var WS_URL  = API_URL.replace(/^http/, 'ws');
  var SIDE    = script.getAttribute('data-position') || 'right';
  var DARK    = script.getAttribute('data-theme') !== 'light';
  var VAD_URL = API_URL + '/vad/';

  if (!API_KEY) { console.error('[VoiceRAG] data-api-key is required'); return; }

  /* ─── CSS ──────────────────────────────────────────────────────────── */
  var css = '\
#vrag-root,#vrag-root *,#vrag-root *::before,#vrag-root *::after{\
  box-sizing:border-box;margin:0;padding:0;\
}\
#vrag-root{\
  --vp:#6c5ce7;--vp2:#00cec9;\
  --vbg:' + (DARK?'#0e0e18':'#ffffff') + ';\
  --vbg2:' + (DARK?'#16161f':'#f3f3f8') + ';\
  --vbg3:' + (DARK?'#1e1e2c':'#e8e8f2') + ';\
  --vtx:' + (DARK?'#e2e2f0':'#111128') + ';\
  --vtx2:' + (DARK?'#8080a0':'#64648a') + ';\
  --vbd:' + (DARK?'rgba(255,255,255,0.07)':'rgba(0,0,0,0.08)') + ';\
  --vsh:0 24px 80px rgba(0,0,0,' + (DARK?'0.55':'0.18') + '),0 0 0 1px rgba(' + (DARK?'255,255,255,0.06':'0,0,0,0.06') + ');\
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;\
  position:fixed;bottom:24px;' + (SIDE==='left'?'left:24px':'right:24px') + ';\
  z-index:2147483647;\
  display:flex;flex-direction:column;\
  align-items:' + (SIDE==='left'?'flex-start':'flex-end') + ';\
  gap:14px;\
}\
#vrag-btn{\
  width:54px;height:54px;border-radius:50%;\
  background:linear-gradient(135deg,#6c5ce7 0%,#4a3fd4 50%,#00cec9 100%);\
  border:none;cursor:pointer;\
  display:flex;align-items:center;justify-content:center;\
  box-shadow:0 4px 24px rgba(108,92,231,0.5),0 1px 4px rgba(0,0,0,0.3);\
  transition:transform .3s cubic-bezier(.34,1.56,.64,1),box-shadow .3s ease;\
  position:relative;\
}\
#vrag-btn:hover{transform:scale(1.1);box-shadow:0 6px 30px rgba(108,92,231,0.65),0 2px 6px rgba(0,0,0,0.3);}\
#vrag-btn.open{transform:scale(0.95);}\
#vrag-btn-icon{transition:transform .35s cubic-bezier(.34,1.56,.64,1);display:flex;align-items:center;justify-content:center;}\
#vrag-btn.open #vrag-btn-icon{transform:rotate(90deg);}\
#vrag-unread{\
  position:absolute;top:-1px;right:-1px;\
  width:14px;height:14px;border-radius:50%;\
  background:linear-gradient(135deg,#ff4757,#ff6b81);\
  border:2px solid var(--vbg);display:none;\
  box-shadow:0 2px 6px rgba(255,71,87,0.5);\
}\
#vrag-unread.show{display:block;animation:vrag-pop .3s cubic-bezier(.34,1.56,.64,1);}\
@keyframes vrag-pop{from{transform:scale(0)}to{transform:scale(1)}}\
#vrag-win{\
  width:370px;\
  background:var(--vbg);\
  border-radius:20px;\
  border:1px solid var(--vbd);\
  box-shadow:var(--vsh);\
  display:none;flex-direction:column;\
  overflow:hidden;\
  transform-origin:bottom ' + (SIDE==='left'?'left':'right') + ';\
}\
#vrag-win.open{\
  display:flex;\
  animation:vrag-open .3s cubic-bezier(.34,1.56,.64,1);\
}\
@keyframes vrag-open{\
  from{opacity:0;transform:scale(.85) translateY(16px);}\
  to{opacity:1;transform:scale(1) translateY(0);}\
}\
#vrag-head{\
  display:flex;align-items:center;gap:11px;\
  padding:14px 16px;\
  background:linear-gradient(135deg,#3a2fa0 0%,#2b3a9e 45%,#0b6b68 100%);\
  flex-shrink:0;\
  position:relative;overflow:hidden;\
}\
#vrag-head::after{\
  content:"";\
  position:absolute;inset:0;\
  background:radial-gradient(ellipse at 100% 0%,rgba(255,255,255,0.08) 0%,transparent 60%);\
  pointer-events:none;\
}\
#vrag-av{\
  width:38px;height:38px;border-radius:50%;\
  background:rgba(255,255,255,0.15);\
  border:1.5px solid rgba(255,255,255,0.25);\
  display:flex;align-items:center;justify-content:center;\
  font-size:16px;font-weight:700;color:#fff;\
  flex-shrink:0;letter-spacing:-.5px;\
  backdrop-filter:blur(4px);\
}\
#vrag-ht{flex:1;min-width:0;}\
#vrag-nm{font-size:14px;font-weight:600;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;letter-spacing:-.01em;}\
#vrag-st{display:flex;align-items:center;gap:5px;margin-top:3px;}\
#vrag-stl{font-size:11px;color:rgba(255,255,255,0.7);}\
#vrag-sd{\
  width:7px;height:7px;border-radius:50%;background:#51cf66;\
  box-shadow:0 0 0 2px rgba(81,207,102,0.3);\
  animation:vrag-pulse 2s ease-in-out infinite;\
}\
@keyframes vrag-pulse{\
  0%,100%{box-shadow:0 0 0 2px rgba(81,207,102,0.3);}\
  50%{box-shadow:0 0 0 5px rgba(81,207,102,0.1);}\
}\
#vrag-cl{\
  width:30px;height:30px;border-radius:50%;\
  background:rgba(255,255,255,0.12);border:none;\
  color:#fff;cursor:pointer;\
  display:flex;align-items:center;justify-content:center;\
  transition:background .2s;flex-shrink:0;\
}\
#vrag-cl:hover{background:rgba(255,255,255,0.24);}\
#vrag-cl svg{width:12px;height:12px;stroke:#fff;stroke-width:2.5;stroke-linecap:round;}\
#vrag-msgs{\
  flex:1;overflow-y:auto;\
  padding:16px;display:flex;flex-direction:column;gap:10px;\
  min-height:260px;max-height:360px;\
  scrollbar-width:thin;scrollbar-color:var(--vbg3) transparent;\
}\
#vrag-msgs::-webkit-scrollbar{width:4px;}\
#vrag-msgs::-webkit-scrollbar-track{background:transparent;}\
#vrag-msgs::-webkit-scrollbar-thumb{background:var(--vbg3);border-radius:4px;}\
.vb{\
  max-width:82%;padding:10px 14px;border-radius:16px;\
  font-size:13.5px;line-height:1.55;word-wrap:break-word;\
  animation:vrag-in .2s ease-out;\
}\
@keyframes vrag-in{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:translateY(0)}}\
.vb.u{\
  align-self:flex-end;\
  background:linear-gradient(135deg,#6c5ce7,#4a3fd4);\
  color:#fff;border-bottom-right-radius:4px;\
  box-shadow:0 2px 12px rgba(108,92,231,0.3);\
}\
.vb.a{\
  align-self:flex-start;\
  background:var(--vbg2);color:var(--vtx);\
  border:1px solid var(--vbd);border-bottom-left-radius:4px;\
  box-shadow:0 1px 4px rgba(0,0,0,0.08);\
}\
.vb.e{\
  align-self:flex-start;\
  background:rgba(255,71,87,0.08);color:#ff6b6b;\
  border:1px solid rgba(255,71,87,0.18);border-bottom-left-radius:4px;\
  font-size:12.5px;\
}\
.vb.sys{\
  align-self:center;\
  background:transparent;color:var(--vtx2);\
  font-size:11px;padding:4px 10px;\
}\
.vdots{display:inline-flex;gap:4px;align-items:center;height:17px;}\
.vd{\
  width:6px;height:6px;border-radius:50%;background:var(--vtx2);\
  animation:vrag-dot 1.3s ease-in-out infinite;\
}\
.vd:nth-child(2){animation-delay:.15s}.vd:nth-child(3){animation-delay:.3s}\
@keyframes vrag-dot{\
  0%,60%,100%{transform:translateY(0);opacity:.4}\
  30%{transform:translateY(-5px);opacity:1}\
}\
#vrag-foot{\
  display:flex;align-items:flex-end;gap:8px;\
  padding:10px 12px 12px;\
  border-top:1px solid var(--vbd);\
  background:var(--vbg);flex-shrink:0;\
}\
#vrag-in{\
  flex:1;padding:9px 14px;border-radius:22px;\
  border:1.5px solid var(--vbd);\
  background:var(--vbg2);color:var(--vtx);\
  font-size:13.5px;font-family:inherit;\
  resize:none;min-height:40px;max-height:100px;\
  line-height:1.45;transition:border-color .2s,background .2s;\
  outline:none;\
}\
#vrag-in:focus{border-color:rgba(108,92,231,0.6);background:var(--vbg3);}\
#vrag-in::placeholder{color:var(--vtx2);}\
.vrag-icon-btn{\
  width:40px;height:40px;border-radius:50%;border:none;\
  display:flex;align-items:center;justify-content:center;\
  cursor:pointer;transition:all .2s;flex-shrink:0;\
}\
#vrag-mic{\
  background:var(--vbg2);\
  color:var(--vtx2);\
}\
#vrag-mic:hover{background:var(--vbg3);color:var(--vtx);}\
#vrag-mic.voice{\
  background:rgba(108,92,231,0.15);\
  color:var(--vp);\
  animation:vrag-voice-pulse 2s ease-in-out infinite;\
}\
#vrag-mic.speaking{\
  background:rgba(0,206,201,0.15);\
  color:var(--vp2);\
  animation:vrag-voice-pulse 0.8s ease-in-out infinite;\
}\
@keyframes vrag-voice-pulse{\
  0%,100%{box-shadow:0 0 0 0 rgba(108,92,231,0.3);}\
  50%{box-shadow:0 0 0 8px rgba(108,92,231,0);}\
}\
#vrag-go{\
  background:linear-gradient(135deg,#6c5ce7,#4a3fd4);\
  color:#fff;\
  box-shadow:0 2px 10px rgba(108,92,231,0.4);\
}\
#vrag-go:hover:not(:disabled){transform:scale(1.08);box-shadow:0 4px 16px rgba(108,92,231,0.5);}\
#vrag-go:disabled{opacity:.4;cursor:not-allowed;transform:none;}\
#vrag-voice-panel{\
  display:none;flex-direction:column;align-items:center;\
  padding:18px 16px 14px;\
  gap:10px;flex-shrink:0;\
  border-top:1px solid var(--vbd);\
  background:var(--vbg);\
}\
#vrag-voice-panel.show{display:flex;}\
#vrag-wave{\
  display:flex;align-items:center;gap:3px;height:40px;\
}\
.vw{\
  width:3px;border-radius:3px;flex-shrink:0;\
  background:linear-gradient(to top,#6c5ce7,#00cec9);\
  animation:vrag-wave 1s ease-in-out infinite;\
}\
.vw:nth-child(1){height:30%;animation-delay:0s}\
.vw:nth-child(2){height:55%;animation-delay:.08s}\
.vw:nth-child(3){height:85%;animation-delay:.16s}\
.vw:nth-child(4){height:100%;animation-delay:.24s}\
.vw:nth-child(5){height:70%;animation-delay:.12s}\
.vw:nth-child(6){height:45%;animation-delay:.2s}\
.vw:nth-child(7){height:60%;animation-delay:.04s}\
.vw:nth-child(8){height:90%;animation-delay:.28s}\
.vw:nth-child(9){height:40%;animation-delay:.36s}\
@keyframes vrag-wave{\
  0%,100%{transform:scaleY(.35);opacity:.5}\
  50%{transform:scaleY(1);opacity:1}\
}\
#vrag-vstatus{\
  font-size:13px;font-weight:500;color:var(--vtx);\
  text-align:center;min-height:18px;\
}\
#vrag-vhint{\
  font-size:11px;color:var(--vtx2);\
  text-align:center;\
}\
#vrag-langbar{\
  display:flex;align-items:center;gap:6px;\
  font-size:11.5px;color:var(--vtx2);\
}\
#vrag-langsel{\
  background:var(--vbg2);color:var(--vtx);\
  border:1px solid var(--vbd);border-radius:8px;\
  padding:3px 7px;font-size:11.5px;cursor:pointer;\
  outline:none;color-scheme:dark;\
}\
#vrag-langsel:focus{border-color:rgba(108,92,231,0.5);}\
#vrag-pw{\
  text-align:center;padding:5px 0 8px;\
  font-size:10px;color:var(--vtx2);opacity:.45;\
  letter-spacing:.04em;flex-shrink:0;\
}\
@media(max-width:420px){\
  #vrag-win{width:calc(100vw - 20px);border-radius:16px;}\
}\
';

  var st = document.createElement('style');
  st.textContent = css;
  document.head.appendChild(st);

  /* ─── DOM ──────────────────────────────────────────────────────────── */
  var root = document.createElement('div');
  root.id = 'vrag-root';
  root.innerHTML = '\
<div id="vrag-win">\
  <div id="vrag-head">\
    <div id="vrag-av">AI</div>\
    <div id="vrag-ht">\
      <div id="vrag-nm">AI Assistant</div>\
      <div id="vrag-st"><div id="vrag-sd"></div><span id="vrag-stl">Online &middot; Ready to help</span></div>\
    </div>\
    <button id="vrag-cl" title="Close">\
      <svg viewBox="0 0 14 14" fill="none"><line x1="1" y1="1" x2="13" y2="13"/><line x1="13" y1="1" x2="1" y2="13"/></svg>\
    </button>\
  </div>\
  <div id="vrag-msgs">\
    <div class="vb a">Hi! How can I help you today?</div>\
  </div>\
  <div id="vrag-voice-panel">\
    <div id="vrag-wave">\
      <div class="vw"></div><div class="vw"></div><div class="vw"></div>\
      <div class="vw"></div><div class="vw"></div><div class="vw"></div>\
      <div class="vw"></div><div class="vw"></div><div class="vw"></div>\
    </div>\
    <div id="vrag-vstatus">Connecting...</div>\
    <div id="vrag-vhint">Click the mic to stop voice mode</div>\
  </div>\
  <div id="vrag-langbar" style="display:none;justify-content:center;padding:0 14px 10px;gap:6px;align-items:center;">\
    <span style="font-size:11px;color:var(--vtx2);">Language:</span>\
    <select id="vrag-langsel">\
      <option value="auto">Auto-detect</option>\
      <option value="en">English</option>\
      <option value="hi">Hindi / Urdu</option>\
      <option value="ur">Urdu (script)</option>\
    </select>\
  </div>\
  <div id="vrag-foot">\
    <button id="vrag-mic" class="vrag-icon-btn" title="Voice assistant">\
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">\
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>\
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>\
      </svg>\
    </button>\
    <textarea id="vrag-in" rows="1" placeholder="Type a message\u2026" autocomplete="off"></textarea>\
    <button id="vrag-go" class="vrag-icon-btn" title="Send">\
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">\
        <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>\
      </svg>\
    </button>\
  </div>\
  <div id="vrag-pw">Powered by VoiceRAG</div>\
</div>\
<button id="vrag-btn" title="Chat with us">\
  <div id="vrag-unread"></div>\
  <span id="vrag-btn-icon">\
    <svg width="23" height="23" viewBox="0 0 24 24" fill="#fff">\
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>\
    </svg>\
  </span>\
</button>\
';
  document.body.appendChild(root);

  /* ─── Refs ──────────────────────────────────────────────────────────── */
  function g(id) { return document.getElementById(id); }
  var $win = g('vrag-win'), $btn = g('vrag-btn'), $cl = g('vrag-cl');
  var $msgs = g('vrag-msgs'), $in = g('vrag-in'), $go = g('vrag-go');
  var $mic = g('vrag-mic'), $vp = g('vrag-voice-panel'), $unread = g('vrag-unread');
  var $nm = g('vrag-nm'), $av = g('vrag-av'), $vstatus = g('vrag-vstatus');
  var $langbar = g('vrag-langbar'), $langsel = g('vrag-langsel');

  /* ─── State ─────────────────────────────────────────────────────────── */
  var sid = null, busy = false, isOpen = false;

  /* ─── Window toggle ──────────────────────────────────────────────────── */
  function openWin() {
    isOpen = true;
    $win.classList.add('open');
    $btn.classList.add('open');
    $unread.classList.remove('show');
    setTimeout(function() { if (!voiceMode) $in.focus(); }, 60);
  }
  function closeWin() {
    isOpen = false;
    $win.classList.remove('open');
    $btn.classList.remove('open');
  }
  $btn.addEventListener('click', function() { isOpen ? closeWin() : openWin(); });
  $cl.addEventListener('click', closeWin);

  /* ─── Messages ───────────────────────────────────────────────────────── */
  function addMsg(text, cls) {
    var el = document.createElement('div');
    el.className = 'vb ' + cls;
    el.textContent = text;
    $msgs.appendChild(el);
    $msgs.scrollTop = $msgs.scrollHeight;
    return el;
  }
  function showTyping() {
    var el = document.createElement('div');
    el.className = 'vb a'; el.id = 'vt';
    el.innerHTML = '<div class="vdots"><div class="vd"></div><div class="vd"></div><div class="vd"></div></div>';
    $msgs.appendChild(el); $msgs.scrollTop = $msgs.scrollHeight;
  }
  function hideTyping() { var t = g('vt'); if (t) t.parentNode.removeChild(t); }

  /* ─── Auto-grow textarea ─────────────────────────────────────────────── */
  $in.addEventListener('input', function() {
    $in.style.height = 'auto';
    $in.style.height = Math.min($in.scrollHeight, 100) + 'px';
  });

  /* ─── Text send (streaming SSE) ─────────────────────────────────────── */
  function sendText() {
    var text = $in.value.trim();
    if (!text || busy) return;
    $in.value = ''; $in.style.height = 'auto';
    setBusy(true);
    addMsg(text, 'u');
    showTyping();

    fetch(API_URL + '/widget/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
      body: JSON.stringify({ message: text, session_id: sid }),
    })
    .then(function(res) {
      hideTyping();
      if (!res.ok) {
        return res.json().catch(function(){ return {}; }).then(function(e) {
          addMsg(e.detail || 'Something went wrong. Please try again.', 'e');
          setBusy(false); $in.focus();
        });
      }

      // Create a streaming bubble
      var msgEl = addMsg('', 'a');
      var fullText = '';
      var reader = res.body.getReader();
      var decoder = new TextDecoder();
      var buffer = '';

      function read() {
        reader.read().then(function(result) {
          if (result.done) {
            setBusy(false); $in.focus();
            if (!isOpen) $unread.classList.add('show');
            return;
          }
          buffer += decoder.decode(result.value, { stream: true });
          var lines = buffer.split('\n');
          buffer = lines.pop() || '';
          lines.forEach(function(line) {
            var trimmed = line.trim();
            if (!trimmed.startsWith('data: ')) return;
            var json = trimmed.slice(6);
            if (json === '[DONE]') return;
            try {
              var chunk = JSON.parse(json);
              if (chunk.type === 'token') {
                fullText += chunk.content;
                if (msgEl) { msgEl.textContent = fullText; $msgs.scrollTop = $msgs.scrollHeight; }
              } else if (chunk.type === 'done') {
                if (chunk.conversation_id) sid = chunk.conversation_id;
              } else if (chunk.type === 'error') {
                if (msgEl) msgEl.textContent = chunk.message || 'Something went wrong.';
              }
            } catch(e) {}
          });
          read();
        }).catch(function() {
          addMsg('Unable to reach the server. Please try again.', 'e');
          setBusy(false); $in.focus();
        });
      }
      read();
    })
    .catch(function() { hideTyping(); addMsg('Unable to reach the server. Please try again.', 'e'); setBusy(false); $in.focus(); });
  }
  $go.addEventListener('click', sendText);
  $in.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendText(); }
  });

  /* ─── Busy state ─────────────────────────────────────────────────────── */
  function setBusy(b) {
    busy = b;
    $go.disabled = b;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     REAL-TIME VOICE PIPELINE
     Identical to the client portal: Silero VAD + WebSocket streaming PCM
     + sentence-by-sentence TTS playback + barge-in.
     ═══════════════════════════════════════════════════════════════════════ */

  var voiceMode   = false;   // true while voice session is active
  var vadLoading  = false;
  var ws          = null;
  var vad         = null;
  var ttsActive   = false;
  var acceptingAudio = true;

  /* ── AudioContext ── */
  var audioCtx    = null;
  function getAudioCtx() {
    if (!audioCtx || audioCtx.state === 'closed') {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
    }
    if (audioCtx.state === 'suspended') audioCtx.resume();
    return audioCtx;
  }

  /* ── Playback graph: all TTS sources → gain → analyser → speakers ── */
  var playbackGain = null, playbackAnalyser = null;
  function ensurePlaybackGraph() {
    var ctx = getAudioCtx();
    if (playbackGain && playbackAnalyser) return playbackGain;
    var g2 = ctx.createGain(); g2.gain.value = 1;
    var an = ctx.createAnalyser(); an.fftSize = 1024;
    g2.connect(an); g2.connect(ctx.destination);
    playbackGain = g2; playbackAnalyser = an;
    return playbackGain;
  }

  /* ── Audio queue ── */
  var audioQueue  = [], isPlaying = false, activeSource = null, playGen = 0;

  function playNextInQueue() {
    if (!audioQueue.length) {
      isPlaying = false;
      $mic.classList.remove('speaking');
      stopBarge();
      setTimeout(resumeVAD, 500);
      setVStatus('Listening...');
      return;
    }
    isPlaying = true;
    var item = audioQueue.shift(), gen = playGen;
    try {
      var bytes = atob(item.data), arr = new Uint8Array(bytes.length);
      for (var i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
      var ctx = getAudioCtx();
      ctx.decodeAudioData(arr.buffer.slice(0), function(buf) {
        if (gen !== playGen) return;
        var src = ctx.createBufferSource();
        src.buffer = buf;
        src.connect(ensurePlaybackGraph() || ctx.destination);
        activeSource = src;
        src.onended = function() {
          if (gen !== playGen) return;
          if (activeSource === src) activeSource = null;
          playNextInQueue();
        };
        src.start(0);
      }, function() { playNextInQueue(); });
    } catch(e) { playNextInQueue(); }
  }

  function enqueueAudio(data) {
    audioQueue.push({ data: data });
    if (!isPlaying) {
      isPlaying = true;
      ttsActive = true;
      setVStatus('Speaking...');
      $mic.classList.add('speaking');
      if (vad) { try { vad.pause(); } catch(e){} }
      startBarge();
      playNextInQueue();
    }
  }

  function interruptPlayback() {
    stopBarge();
    ttsActive = false;
    playGen++;
    audioQueue = [];
    if (activeSource) {
      try { activeSource.onended = null; activeSource.stop(0); } catch(e){}
      try { activeSource.disconnect(); } catch(e){}
      activeSource = null;
    }
    isPlaying = false;
    acceptingAudio = false;
    $mic.classList.remove('speaking');
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'interrupt' }));
    }
  }

  function resumeVAD() {
    ttsActive = false;
    if (vad && voiceMode) {
      try { vad.start(); } catch(e){}
      setVStatus('Listening...');
      $mic.classList.remove('speaking');
    }
  }

  /* ── Barge-in energy detector ── */
  var monitorStream = null, monitorCtx2 = null, micAnalyser = null;
  var bargeInterval = null, bargeConsec = 0;
  var B_POLL = 40, B_CAL = 5, B_CONSEC = 6, B_RATIO = 2.5, B_ABS = 0.07, B_FLOOR = 0.03;

  function rms(analyser) {
    if (!analyser) return 0;
    var d = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(d);
    var s = 0;
    for (var i = 0; i < d.length; i++) { var c = (d[i]-128)/128; s += c*c; }
    return Math.sqrt(s / d.length);
  }

  function stopBarge() {
    if (bargeInterval) { clearInterval(bargeInterval); bargeInterval = null; }
    bargeConsec = 0;
  }

  function startBarge() {
    stopBarge();
    var calN = 0, calSum = 0, thresh = null;
    bargeInterval = setInterval(function() {
      if (!isPlaying) { stopBarge(); return; }
      var mic = rms(micAnalyser), tts = rms(playbackAnalyser);
      if (tts < 0.01) return;
      if (calN < B_CAL) {
        calSum += mic / tts; calN++;
        if (calN === B_CAL) thresh = Math.max((calSum/calN) * B_RATIO, 1.5);
        return;
      }
      var ratioOk = mic > B_FLOOR && thresh && (mic/tts) > thresh;
      var absOk   = mic > B_ABS;
      if (ratioOk || absOk) {
        bargeConsec++;
        if (bargeConsec >= B_CONSEC) {
          stopBarge();
          interruptPlayback();
          startCapture().catch(function(){});
          setTimeout(resumeVAD, 200);
        }
      } else { bargeConsec = 0; }
    }, B_POLL);
  }

  function startEchoMonitor() {
    if (monitorStream) return Promise.resolve();
    return navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1, sampleRate: 16000 }
    }).then(function(stream) {
      monitorStream = stream;
      var AudioCtx2 = window.AudioContext || window.webkitAudioContext;
      monitorCtx2 = new AudioCtx2();
      var src = monitorCtx2.createMediaStreamSource(stream);
      var an  = monitorCtx2.createAnalyser(); an.fftSize = 1024;
      src.connect(an);
      micAnalyser = an;
      ensurePlaybackGraph();
    }).catch(function(e) { console.warn('[VoiceRAG] echo monitor failed:', e); });
  }

  function stopEchoMonitor() {
    if (monitorStream) { monitorStream.getTracks().forEach(function(t){t.stop();}); monitorStream = null; }
    if (monitorCtx2) { try{monitorCtx2.close();}catch(e){} monitorCtx2 = null; }
    micAnalyser = null; playbackGain = null; playbackAnalyser = null;
  }

  /* ── PCM capture (ScriptProcessor → WAV chunks → WS) ── */
  var capStream = null, capCtx = null, capSrc = null, capProc = null;
  var capBufs = [], capInterval = null;

  function f32ToWav(f32, sr) {
    var nc=1, bps=2, ba=nc*bps, ds=f32.length*bps;
    var buf = new ArrayBuffer(44+ds), v = new DataView(buf);
    var ws2 = function(o,s){for(var i=0;i<s.length;i++) v.setUint8(o+i,s.charCodeAt(i));};
    ws2(0,'RIFF'); v.setUint32(4,36+ds,true); ws2(8,'WAVE');
    ws2(12,'fmt '); v.setUint32(16,16,true); v.setUint16(20,1,true);
    v.setUint16(22,nc,true); v.setUint32(24,sr,true); v.setUint32(28,sr*ba,true);
    v.setUint16(32,ba,true); v.setUint16(34,bps*8,true); ws2(36,'data'); v.setUint32(40,ds,true);
    var off=44;
    for(var i=0;i<f32.length;i++){
      var s2=Math.max(-1,Math.min(1,f32[i]));
      v.setInt16(off,s2<0?s2*0x8000:s2*0x7FFF,true); off+=2;
    }
    return new Blob([buf],{type:'audio/wav'});
  }

  function b64(blob) {
    return new Promise(function(res,rej){
      var r=new FileReader();
      r.onloadend=function(){res(r.result.split(',')[1]||'');};
      r.onerror=function(){rej(new Error('FileReader failed'));};
      r.readAsDataURL(blob);
    });
  }

  function flushPcm(force) {
    var chunks = capBufs;
    if (!chunks.length) return Promise.resolve();
    var total = 0;
    for(var i=0;i<chunks.length;i++) total+=chunks[i].length;
    if (!force && total < 2048) return Promise.resolve();
    var merged = new Float32Array(total), off = 0;
    for(var i=0;i<chunks.length;i++){merged.set(chunks[i],off);off+=chunks[i].length;}
    capBufs = [];
    if (!ws || ws.readyState !== WebSocket.OPEN) return Promise.resolve();
    var sr = capCtx ? capCtx.sampleRate : 16000;
    return b64(f32ToWav(merged, sr)).then(function(data){
      if (ws && ws.readyState === WebSocket.OPEN)
        ws.send(JSON.stringify({type:'audio_chunk',data:data}));
    }).catch(function(e){console.error('[VoiceRAG] flushPcm failed:',e);});
  }

  function startCapture() {
    if (capProc) return Promise.resolve();
    return navigator.mediaDevices.getUserMedia({
      audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true,channelCount:1,sampleRate:16000}
    }).then(function(stream){
      capStream = stream;
      var AC = window.AudioContext || window.webkitAudioContext;
      capCtx = new AC({sampleRate:16000});
      capSrc = capCtx.createMediaStreamSource(stream);
      capProc = capCtx.createScriptProcessor(2048,1,1);
      capProc.onaudioprocess = function(e){
        capBufs.push(new Float32Array(e.inputBuffer.getChannelData(0)));
      };
      capSrc.connect(capProc);
      capProc.connect(capCtx.destination);
      capInterval = setInterval(function(){ flushPcm(false); }, 300);
    });
  }

  function stopCapture(commit) {
    if (capInterval){ clearInterval(capInterval); capInterval=null; }
    var p = commit ? flushPcm(true) : Promise.resolve();
    return p.then(function(){
      if(capProc){try{capProc.disconnect();}catch(e){} capProc.onaudioprocess=null; capProc=null;}
      if(capSrc){try{capSrc.disconnect();}catch(e){} capSrc=null;}
      if(capCtx){try{capCtx.close();}catch(e){} capCtx=null;}
      if(capStream){capStream.getTracks().forEach(function(t){t.stop();}); capStream=null;}
      capBufs=[];
      if(ws && ws.readyState===WebSocket.OPEN)
        ws.send(JSON.stringify({type: commit?'audio_commit':'audio_discard'}));
    });
  }

  /* ── VAD bundle loader ── */
  function loadVAD() {
    return new Promise(function(res,rej){
      if (window.vad && window.vad.MicVAD){ res(window.vad.MicVAD); return; }
      var s = document.createElement('script');
      s.src = VAD_URL + 'vad-bundle.min.js';
      s.onload = function(){
        if (window.vad && window.vad.MicVAD) res(window.vad.MicVAD);
        else rej(new Error('VAD bundle loaded but MicVAD not found'));
      };
      s.onerror = function(){ rej(new Error('Failed to load VAD bundle from ' + VAD_URL)); };
      document.head.appendChild(s);
    });
  }

  /* ── Status display ── */
  function setVStatus(text) { if ($vstatus) $vstatus.textContent = text; }

  /* ── Show language bar when widget is closed (before voice starts) ── */
  function syncLangBar() {
    if ($langbar) $langbar.style.display = voiceMode ? 'none' : 'flex';
  }
  syncLangBar();

  /* ── Start full voice pipeline ── */
  function startVoice() {
    if (vadLoading || voiceMode) return;
    vadLoading = true;
    $vp.classList.add('show');
    $in.style.display = 'none';
    $go.style.display = 'none';
    $mic.classList.add('voice');
    if ($langbar) $langbar.style.display = 'none';
    setVStatus('Connecting...');

    var lang = $langsel ? $langsel.value : 'auto';
    var langParam = (lang && lang !== 'auto') ? '&language=' + encodeURIComponent(lang) : '';
    ws = new WebSocket(WS_URL + '/widget/voice/ws?api_key=' + encodeURIComponent(API_KEY) + langParam);

    ws.onopen = function() {
      console.log('[VoiceRAG] WS connected');
    };

    ws.onmessage = function(e) {
      var msg;
      try { msg = JSON.parse(e.data); } catch(e2){ return; }
      if (msg.type === 'listening') {
        setVStatus('Listening...');
      } else if (msg.type === 'status') {
        setVStatus(msg.message || '...');
      } else if (msg.type === 'transcription') {
        acceptingAudio = true;
        if (msg.conversation_id) sid = msg.conversation_id;
        addMsg(msg.text, 'u');
        setVStatus('Processing...');
        if (!isOpen) $unread.classList.add('show');
      } else if (msg.type === 'partial_transcription') {
        var t = msg.text || '';
        setVStatus('"' + (t.length > 45 ? t.substring(0,45)+'...' : t) + '"');
      } else if (msg.type === 'answer') {
        addMsg(msg.text, 'a');
        if (!isOpen) $unread.classList.add('show');
      } else if (msg.type === 'audio_chunk') {
        if (acceptingAudio) enqueueAudio(msg.data);
      } else if (msg.type === 'error') {
        addMsg(msg.message || 'Voice error. Please try again.', 'e');
      }
    };

    ws.onerror = function() {
      addMsg('Voice connection failed. Please try again.', 'e');
      stopVoice();
    };

    ws.onclose = function() {
      if (voiceMode) stopVoice();
    };

    Promise.all([loadVAD(), startEchoMonitor()])
    .then(function(results) {
      var MicVAD = results[0];
      return MicVAD.new({
        model: 'legacy',
        baseAssetPath: VAD_URL,
        onnxWASMBasePath: VAD_URL,
        additionalAudioConstraints: {
          echoCancellation: true, noiseSuppression: true, autoGainControl: true,
          channelCount: 1, sampleRate: 16000,
        },
        positiveSpeechThreshold: 0.80,
        negativeSpeechThreshold: 0.35,
        redemptionMs: 1200,
        minSpeechMs: 400,
        preSpeechPadMs: 300,
        submitUserSpeechOnPause: true,
        onSpeechStart: function() {
          if (ttsActive) {
            interruptPlayback();
            startCapture().catch(function(){});
            return;
          }
          setVStatus('Hearing you...');
          startCapture().catch(function(e){ console.error('[VoiceRAG] startCapture failed:', e); });
        },
        onSpeechEnd: function(audioFloat32) {
          if (!audioFloat32 || audioFloat32.length < 8000) {
            stopCapture(false).catch(function(){});
            return;
          }
          setVStatus('Processing...');
          stopCapture(true).catch(function(e){ console.error('[VoiceRAG] stopCapture failed:', e); });
        },
      });
    })
    .then(function(v) {
      vad = v;
      voiceMode = true;
      vadLoading = false;
      vad.start();
      setVStatus('Listening...');
      console.log('[VoiceRAG] Voice pipeline ready');
    })
    .catch(function(err) {
      console.error('[VoiceRAG] Voice init failed:', err);
      addMsg('Voice assistant failed to start: ' + (err.message || 'Unknown error'), 'e');
      stopVoice();
    });
  }

  /* ── Stop voice pipeline ── */
  function stopVoice() {
    voiceMode = false;
    vadLoading = false;
    stopBarge();
    interruptPlayback();
    stopCapture(false).catch(function(){});
    stopEchoMonitor();
    if (vad) { try{ vad.destroy(); }catch(e){} vad = null; }
    if (ws) { try{ ws.close(); }catch(e){} ws = null; }
    $vp.classList.remove('show');
    $in.style.display = '';
    $go.style.display = '';
    $mic.classList.remove('voice');
    $mic.classList.remove('speaking');
    setVStatus('Connecting...');
    if ($langbar) $langbar.style.display = 'flex';
    $in.focus();
  }

  $mic.addEventListener('click', function() {
    if (voiceMode || vadLoading) stopVoice(); else startVoice();
  });

  /* ─── Load config ────────────────────────────────────────────────────── */
  fetch(API_URL + '/widget/config', { headers: { 'X-API-Key': API_KEY } })
  .then(function(r) { return r.ok ? r.json() : null; })
  .then(function(cfg) {
    if (!cfg || !cfg.company_name) return;
    $nm.textContent = cfg.company_name + ' Assistant';
    $av.textContent = cfg.company_name.trim().charAt(0).toUpperCase();
    if (!cfg.has_documents) {
      addMsg('No knowledge base is set up yet. The owner needs to upload a document first.', 'sys');
    }
  })
  .catch(function(){});

  console.log('[VoiceRAG] Widget v3 ready');
})();
""".strip()


@router.get("/widget.js")
def serve_widget():
    """Serve the embeddable chat widget JavaScript."""
    return Response(
        content=WIDGET_JS,
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache, no-store"},
    )
