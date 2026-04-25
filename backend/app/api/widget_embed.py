"""
Serves the embeddable chat widget JavaScript.
Add to any website: <script src="https://your-server/widget.js" data-api-key="vrag_xxx"></script>

Permission bug fix: mic is requested ONCE at voice-start and the same
MediaStream is passed to the VAD constructor (stream option) and to the
ScriptProcessor capture node.  No repeated getUserMedia prompts.
"""

import json as _json
from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter(tags=["Widget Embed"])

# ─── Widget JSX ────────────────────────────────────────────────────────────────
# Stored as a raw Python string so backslashes are literal (needed for JS
# escape sequences such as \n inside string literals in the generated code).
# json.dumps() below turns this into a safe JS string literal.

_WIDGET_JSX = r"""
const { useState, useRef, useEffect, useCallback } = React;

// ── Config (injected by loader) ───────────────────────────────────────────────
const API_KEY = window.__VRAG_API_KEY;
const API_URL = window.__VRAG_API_URL;
const WS_URL  = window.__VRAG_WS_URL;
const VAD_URL = window.__VRAG_VAD_URL;

// ── SSE streaming chat ────────────────────────────────────────────────────────
async function streamChat(message, sessionId, onToken, onDone, onError) {
  try {
    const res = await fetch(API_URL + '/widget/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
      body: JSON.stringify({ message, session_id: sessionId || null }),
    });
    if (!res.ok) {
      const e = await res.json().catch(() => ({}));
      onError(e.detail || 'Something went wrong.'); return;
    }
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = '', newSid = sessionId;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split('\n'); buf = lines.pop() || '';
      for (const line of lines) {
        const t = line.trim();
        if (!t.startsWith('data: ')) continue;
        const j = t.slice(6);
        if (j === '[DONE]') continue;
        try {
          const c = JSON.parse(j);
          if (c.type === 'token' && c.content) onToken(c.content);
          else if (c.type === 'done' && c.conversation_id) newSid = c.conversation_id;
          else if (c.type === 'error') onError(c.message || 'Error');
        } catch(_) {}
      }
    }
    onDone(newSid);
  } catch(e) { onError('Unable to reach the server.'); }
}

// ── Icons ─────────────────────────────────────────────────────────────────────
const IconChat = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  </svg>
);
const IconClose = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);
const IconSend = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13"/>
    <polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>
);
const IconMic = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
    <line x1="12" y1="19" x2="12" y2="23"/>
    <line x1="8" y1="23" x2="16" y2="23"/>
  </svg>
);
const IconArrowLeft = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="19" y1="12" x2="5" y2="12"/>
    <polyline points="12 19 5 12 12 5"/>
  </svg>
);

const AIAvatar = () => (
  <div style={{ width:26, height:26, borderRadius:'50%', background:'#0a0a0a', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0, marginBottom:2 }}>
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3"/>
      <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
    </svg>
  </div>
);

const TypingDots = () => (
  <div style={{ display:'flex', gap:4, alignItems:'center', padding:'4px 0' }}>
    {[0,1,2].map(i => (
      <span key={i} style={{ width:5, height:5, borderRadius:'50%', background:'#bbb', display:'inline-block',
        animation:`vr-dot-blink 1.2s ease-in-out ${i*0.2}s infinite` }}/>
    ))}
  </div>
);

const WaveformBars = ({ active }) => {
  const heights = [0.4,0.7,1,0.6,0.9,0.5,0.8,0.3,0.7,1,0.5,0.6,0.4,0.8,0.3];
  return (
    <div style={{ display:'flex', alignItems:'center', gap:3, height:48 }}>
      {heights.map((h, i) => (
        <div key={i} style={{
          width:3, borderRadius:4, background:'#0a0a0a', transformOrigin:'center',
          height: active ? `${h*100}%` : '20%',
          animation: active ? `vr-bar-bounce ${0.6+(i%4)*0.15}s ease-in-out ${i*0.06}s infinite` : 'none',
          transition:'height 0.4s ease',
          opacity: active ? 1 : 0.2,
        }}/>
      ))}
    </div>
  );
};

const PulseRing = ({ listening, onClick }) => (
  <div onClick={onClick} style={{ position:'relative', display:'flex', alignItems:'center', justifyContent:'center', cursor:'pointer' }}>
    {listening && [0,1].map(i => (
      <div key={i} style={{ position:'absolute', width:72, height:72, borderRadius:'50%',
        border:'1px solid #0a0a0a', animation:`vr-ripple 2s ease-out ${i*0.7}s infinite`,
        pointerEvents:'none' }}/>
    ))}
    <div style={{ width:72, height:72, borderRadius:'50%',
      background: listening ? '#0a0a0a' : '#f0f0f0',
      display:'flex', alignItems:'center', justifyContent:'center',
      transition:'background 0.3s', color: listening ? '#fff' : '#0a0a0a',
      border:'1.5px solid #0a0a0a' }}>
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" y1="19" x2="12" y2="23"/>
        <line x1="8" y1="23" x2="16" y2="23"/>
      </svg>
    </div>
  </div>
);

// ── Audio helpers ─────────────────────────────────────────────────────────────
function f32ToWav(f32, sr) {
  const nc=1,bps=2,ba=nc*bps,ds=f32.length*bps;
  const buf=new ArrayBuffer(44+ds),v=new DataView(buf);
  const ws=(o,s)=>{for(let i=0;i<s.length;i++)v.setUint8(o+i,s.charCodeAt(i));};
  ws(0,'RIFF');v.setUint32(4,36+ds,true);ws(8,'WAVE');
  ws(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);
  v.setUint16(22,nc,true);v.setUint32(24,sr,true);v.setUint32(28,sr*ba,true);
  v.setUint16(32,ba,true);v.setUint16(34,bps*8,true);ws(36,'data');v.setUint32(40,ds,true);
  let off=44;
  for(let i=0;i<f32.length;i++){const s=Math.max(-1,Math.min(1,f32[i]));v.setInt16(off,s<0?s*0x8000:s*0x7FFF,true);off+=2;}
  return new Blob([buf],{type:'audio/wav'});
}
function b64(blob){
  return new Promise((res,rej)=>{const r=new FileReader();r.onloadend=()=>res(r.result.split(',')[1]||'');r.onerror=()=>rej(new Error('fr'));r.readAsDataURL(blob);});
}
function loadVAD(){
  return new Promise((res,rej)=>{
    if(window.vad&&window.vad.MicVAD){res(window.vad.MicVAD);return;}
    const s=document.createElement('script');
    s.src=VAD_URL+'vad-bundle.min.js';
    s.onload=()=>window.vad&&window.vad.MicVAD?res(window.vad.MicVAD):rej(new Error('VAD not found'));
    s.onerror=()=>rej(new Error('VAD load failed'));
    document.head.appendChild(s);
  });
}

// ── Main component ────────────────────────────────────────────────────────────
function VoiceRAGWidget() {
  const [open, setOpen]               = useState(false);
  const [closing, setClosing]         = useState(false);
  const [mode, setMode]               = useState('chat');
  const [messages, setMessages]       = useState([{id:0, role:'ai', text:'Hi there. How can I help you today?'}]);
  const [input, setInput]             = useState('');
  const [typing, setTyping]           = useState(false);
  const [assistantName, setAssistantName] = useState('AI Assistant');

  // Voice UI state
  const [voiceStatus, setVoiceStatus] = useState('Tap to speak');
  const [isListening, setIsListening] = useState(false);
  const [waveActive, setWaveActive]   = useState(false);

  const inputRef       = useRef(null);
  const messagesEndRef = useRef(null);
  const sessionRef     = useRef(null);

  // ── All voice pipeline state lives in a single ref so mutations
  //    never trigger re-renders ────────────────────────────────────────────
  const vr = useRef({
    running: false,
    ws: null, vad: null,
    micStream: null,          // ← SINGLE getUserMedia result, shared everywhere
    audioCtx: null, playGain: null,
    queue: [], playing: false, activeSrc: null, playGen: 0, ttsActive: false,
    acceptAudio: true,
    capCtx: null, capSrc: null, capProc: null, capBufs: [], capTimer: null,
  }).current;

  // ── Scroll + focus effects ────────────────────────────────────────────────
  useEffect(() => { if(open && mode==='chat') setTimeout(()=>inputRef.current?.focus(),300); }, [open,mode]);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({behavior:'smooth'}); }, [messages,typing]);

  // ── Load company name from config ─────────────────────────────────────────
  useEffect(() => {
    fetch(API_URL + '/widget/config', { headers: { 'X-API-Key': API_KEY } })
      .then(r => r.ok ? r.json() : null)
      .then(cfg => { if(cfg?.company_name) setAssistantName(cfg.company_name + ' Assistant'); })
      .catch(() => {});
  }, []);

  // ── Close animation ───────────────────────────────────────────────────────
  const handleClose = () => {
    setClosing(true);
    setTimeout(() => { setOpen(false); setClosing(false); }, 260);
  };

  // ── Chat ──────────────────────────────────────────────────────────────────
  const sendMessage = useCallback(async () => {
    const txt = input.trim();
    if (!txt) return;
    setInput('');
    setMessages(m => [...m, {id:Date.now(), role:'user', text:txt}]);
    const msgId = Date.now()+1;
    setMessages(m => [...m, {id:msgId, role:'ai', text:''}]);
    setTyping(true);
    let reply = '';
    await streamChat(
      txt, sessionRef.current,
      token => { reply += token; setMessages(m => m.map(x => x.id===msgId ? {...x,text:reply} : x)); },
      newSid => { sessionRef.current=newSid; setTyping(false); },
      err  => { setTyping(false); setMessages(m => m.map(x => x.id===msgId ? {...x,text:'⚠ '+err} : x)); }
    );
  }, [input]);

  const handleKey = e => { if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage();} };

  // ── Audio playback ────────────────────────────────────────────────────────
  function getAudioCtx() {
    if (!vr.audioCtx || vr.audioCtx.state==='closed') {
      const AC = window.AudioContext || window.webkitAudioContext;
      vr.audioCtx = new AC({sampleRate:24000});
      const g = vr.audioCtx.createGain(); g.gain.value=1;
      g.connect(vr.audioCtx.destination);
      vr.playGain = g;
    }
    if (vr.audioCtx.state==='suspended') vr.audioCtx.resume();
    return vr.audioCtx;
  }

  function playNext() {
    if (!vr.queue.length) {
      vr.playing=false; vr.ttsActive=false;
      setWaveActive(false); setIsListening(true); setVoiceStatus('Listening…');
      if(vr.vad) try{vr.vad.start();}catch(_){}
      return;
    }
    vr.playing=true;
    const data=vr.queue.shift(), gen=vr.playGen;
    try {
      const bytes=atob(data), arr=new Uint8Array(bytes.length);
      for(let i=0;i<bytes.length;i++) arr[i]=bytes.charCodeAt(i);
      const ctx=getAudioCtx();
      ctx.decodeAudioData(arr.buffer.slice(0), buf=>{
        if(gen!==vr.playGen) return;
        const src=ctx.createBufferSource();
        src.buffer=buf; src.connect(vr.playGain||ctx.destination);
        vr.activeSrc=src;
        src.onended=()=>{ if(gen===vr.playGen) playNext(); };
        src.start(0);
      }, ()=>playNext());
    } catch(_) { playNext(); }
  }

  function enqueueAudio(data) {
    vr.queue.push(data);
    if (!vr.playing) {
      vr.ttsActive=true; vr.playing=true;
      setWaveActive(true); setIsListening(false); setVoiceStatus('Speaking…');
      if(vr.vad) try{vr.vad.pause();}catch(_){}
      playNext();
    }
  }

  function interruptPlayback() {
    vr.playGen++; vr.queue=[]; vr.playing=false; vr.ttsActive=false; vr.acceptAudio=false;
    if(vr.activeSrc){try{vr.activeSrc.onended=null;vr.activeSrc.stop(0);}catch(_){} vr.activeSrc=null;}
    if(vr.ws&&vr.ws.readyState===WebSocket.OPEN) vr.ws.send(JSON.stringify({type:'interrupt'}));
    setWaveActive(false);
  }

  // ── PCM capture — reuses vr.micStream, NO new getUserMedia ───────────────
  function startCapture() {
    if (vr.capProc || !vr.micStream) return;
    const AC = window.AudioContext || window.webkitAudioContext;
    vr.capCtx = new AC({sampleRate:16000});
    vr.capSrc = vr.capCtx.createMediaStreamSource(vr.micStream); // reuse stream
    vr.capProc = vr.capCtx.createScriptProcessor(2048,1,1);
    vr.capProc.onaudioprocess = e => { vr.capBufs.push(new Float32Array(e.inputBuffer.getChannelData(0))); };
    vr.capSrc.connect(vr.capProc); vr.capProc.connect(vr.capCtx.destination);
    vr.capTimer = setInterval(()=>flushPcm(false), 300);
  }

  function stopCapture(commit) {
    if(vr.capTimer){clearInterval(vr.capTimer);vr.capTimer=null;}
    const p = commit ? flushPcm(true) : Promise.resolve();
    return p.then(()=>{
      if(vr.capProc){try{vr.capProc.disconnect();}catch(_){} vr.capProc.onaudioprocess=null; vr.capProc=null;}
      if(vr.capSrc){try{vr.capSrc.disconnect();}catch(_){} vr.capSrc=null;}
      if(vr.capCtx){try{vr.capCtx.close();}catch(_){} vr.capCtx=null;}
      vr.capBufs=[];
      if(vr.ws&&vr.ws.readyState===WebSocket.OPEN)
        vr.ws.send(JSON.stringify({type:commit?'audio_commit':'audio_discard'}));
    });
  }

  function flushPcm(force) {
    const chunks=vr.capBufs;
    if(!chunks.length) return Promise.resolve();
    let total=0; for(const c of chunks) total+=c.length;
    if(!force&&total<2048) return Promise.resolve();
    let merged=new Float32Array(total),off=0;
    for(const c of chunks){merged.set(c,off);off+=c.length;}
    vr.capBufs=[];
    if(!vr.ws||vr.ws.readyState!==WebSocket.OPEN) return Promise.resolve();
    const sr=vr.capCtx?vr.capCtx.sampleRate:16000;
    return b64(f32ToWav(merged,sr)).then(data=>{
      if(vr.ws&&vr.ws.readyState===WebSocket.OPEN)
        vr.ws.send(JSON.stringify({type:'audio_chunk',data}));
    });
  }

  // ── Start voice ───────────────────────────────────────────────────────────
  const startVoice = useCallback(async () => {
    if (vr.running) return;
    vr.running = true;
    setVoiceStatus('Requesting mic…');

    // ════════════════════════════════════════════════════════════════════════
    // ONE getUserMedia call. The resulting stream is reused for:
    //   1. VAD (passed via the `stream` option — no internal getUserMedia)
    //   2. ScriptProcessor capture (createMediaStreamSource reuses the stream)
    // This eliminates the repeated browser permission prompts.
    // ════════════════════════════════════════════════════════════════════════
    try {
      vr.micStream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation:true, noiseSuppression:true, autoGainControl:true, channelCount:1, sampleRate:16000 }
      });
    } catch(e) {
      setVoiceStatus('Mic denied — check browser permissions.');
      vr.running = false;
      return;
    }

    // ── WebSocket ────────────────────────────────────────────────────────
    setVoiceStatus('Connecting…');
    vr.ws = new WebSocket(`${WS_URL}/widget/voice/ws?api_key=${encodeURIComponent(API_KEY)}`);

    vr.ws.onmessage = e => {
      let msg; try { msg=JSON.parse(e.data); } catch(_){return;}
      switch(msg.type) {
        case 'listening':
          vr.acceptAudio=true;
          setIsListening(true); setWaveActive(false); setVoiceStatus('Listening…');
          break;
        case 'status': setVoiceStatus(msg.message||'…'); break;
        case 'partial_transcription': {
          const t=msg.text||'';
          setVoiceStatus('“'+(t.length>40?t.slice(0,40)+'…':t)+'”');
          break;
        }
        case 'transcription':
          if(msg.conversation_id) sessionRef.current=msg.conversation_id;
          setMessages(m=>[...m,{id:Date.now(),role:'user',text:msg.text}]);
          setWaveActive(false); setVoiceStatus('Thinking…');
          break;
        case 'answer':
          setMessages(m=>{
            const last=m[m.length-1];
            if(last&&last.role==='ai'&&last._voice) return [...m.slice(0,-1),{...last,text:msg.text}];
            return [...m,{id:Date.now(),role:'ai',text:msg.text,_voice:true}];
          });
          break;
        case 'audio_chunk':
          if(vr.acceptAudio) enqueueAudio(msg.data);
          break;
        case 'error':
          setMessages(m=>[...m,{id:Date.now(),role:'ai',text:'⚠ '+(msg.message||'Voice error.')}]);
          setVoiceStatus('Error — try again');
          break;
      }
    };
    vr.ws.onerror = () => { setVoiceStatus('Connection failed.'); stopVoice(); };
    vr.ws.onclose = () => { if(vr.running) stopVoice(); };

    // ── Load VAD ─────────────────────────────────────────────────────────
    setVoiceStatus('Loading voice AI…');
    try {
      const MicVAD = await loadVAD();
      vr.vad = await MicVAD.new({
        stream: vr.micStream,       // ← pass existing stream, VAD skips getUserMedia
        model: 'legacy',
        baseAssetPath: VAD_URL,
        onnxWASMBasePath: VAD_URL,
        positiveSpeechThreshold: 0.80,
        negativeSpeechThreshold: 0.35,
        redemptionMs: 1200,
        minSpeechMs: 400,
        preSpeechPadMs: 300,
        submitUserSpeechOnPause: true,
        onSpeechStart: () => {
          if(vr.ttsActive) interruptPlayback();
          setIsListening(true); setWaveActive(true); setVoiceStatus('Hearing you…');
          startCapture();
        },
        onSpeechEnd: audio => {
          if(!audio||audio.length<8000){stopCapture(false);return;}
          setWaveActive(false); setVoiceStatus('Processing…');
          stopCapture(true).catch(e=>console.error('[VoiceRAG]',e));
        },
      });
      vr.vad.start();
      setIsListening(true); setVoiceStatus('Listening…');
    } catch(e) {
      console.error('[VoiceRAG] VAD init failed:', e);
      setMessages(m=>[...m,{id:Date.now(),role:'ai',text:'⚠ Voice AI failed to load. Try again.'}]);
      stopVoice();
    }
  }, []);

  // ── Stop voice ────────────────────────────────────────────────────────────
  const stopVoice = useCallback(() => {
    vr.running = false;
    interruptPlayback();
    stopCapture(false);
    if(vr.vad){try{vr.vad.destroy();}catch(_){} vr.vad=null;}
    if(vr.ws){try{vr.ws.close();}catch(_){} vr.ws=null;}
    if(vr.micStream){vr.micStream.getTracks().forEach(t=>t.stop()); vr.micStream=null;}
    if(vr.audioCtx){try{vr.audioCtx.close();}catch(_){} vr.audioCtx=null;}
    setIsListening(false); setWaveActive(false); setVoiceStatus('Tap to speak');
  }, []);

  const toggleVoice = () => {
    if (mode==='voice') { stopVoice(); setMode('chat'); }
    else { setMode('voice'); startVoice(); }
  };

  useEffect(() => () => stopVoice(), []);

  // ── Render ────────────────────────────────────────────────────────────────
  const side = window.__VRAG_SIDE || 'right';
  const panelStyle = side==='left'
    ? {position:'absolute', bottom:68, left:0}
    : {position:'absolute', bottom:68, right:0};

  return (
    <div style={{ position:'relative' }}>

      {/* Panel */}
      {open && (
        <div style={{
          ...panelStyle,
          width:380, height:'min(560px, calc(100vh - 96px))',
          background:'#fff', borderRadius:20,
          border:'1px solid #e2e2e2',
          boxShadow:'0 8px 40px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.06)',
          display:'flex', flexDirection:'column', overflow:'hidden',
          animation: closing
            ? 'vr-fadeDown 0.26s ease forwards'
            : 'vr-fadeUp 0.28s cubic-bezier(0.34,1.26,0.64,1) forwards',
        }}>

          {/* Header */}
          <div style={{ padding:'18px 20px 16px', borderBottom:'1px solid #f0f0f0', display:'flex', alignItems:'center', justifyContent:'space-between', flexShrink:0 }}>
            <div style={{ display:'flex', alignItems:'center', gap:10 }}>
              {mode==='voice' && (
                <button onClick={toggleVoice} style={{ background:'none', border:'none', cursor:'pointer', color:'#888', padding:'0 4px 0 0', display:'flex', alignItems:'center' }}>
                  <IconArrowLeft />
                </button>
              )}
              <div>
                <div style={{ fontWeight:600, fontSize:14, color:'#0a0a0a', letterSpacing:'-0.2px' }}>
                  {mode==='voice' ? 'Voice Assistant' : assistantName}
                </div>
                <div style={{ fontSize:11, color:'#aaa', marginTop:1 }}>Powered by VoiceRAG</div>
              </div>
            </div>
            <div style={{ display:'flex', alignItems:'center', gap:6 }}>
              <div style={{ width:6, height:6, borderRadius:'50%', background:'#22c55e' }}/>
              <button onClick={handleClose}
                style={{ width:28, height:28, borderRadius:'50%', background:'#f5f5f5', border:'none', cursor:'pointer', display:'flex', alignItems:'center', justifyContent:'center', color:'#666' }}
                onMouseEnter={e=>e.currentTarget.style.background='#ebebeb'}
                onMouseLeave={e=>e.currentTarget.style.background='#f5f5f5'}>
                <IconClose />
              </button>
            </div>
          </div>

          {/* Body */}
          {mode==='chat' ? (
            <>
              <div style={{ flex:1, overflowY:'auto', padding:'20px 20px 8px', display:'flex', flexDirection:'column', gap:16 }}>
                {messages.map(msg => (
                  <div key={msg.id} style={{ display:'flex', flexDirection:msg.role==='user'?'row-reverse':'row', alignItems:'flex-end', gap:8 }}>
                    {msg.role==='ai' && <AIAvatar />}
                    <div style={{
                      maxWidth:'72%',
                      padding: msg.role==='user' ? '9px 14px' : '0',
                      background: msg.role==='user' ? '#0a0a0a' : 'transparent',
                      borderRadius: msg.role==='user' ? '16px 16px 4px 16px' : 0,
                      color: msg.role==='user' ? '#fff' : '#1a1a1a',
                      fontSize:13.5, lineHeight:1.55, fontWeight:400, letterSpacing:'-0.1px',
                    }}>{msg.text}</div>
                  </div>
                ))}
                {typing && (
                  <div style={{ display:'flex', alignItems:'flex-end', gap:8 }}>
                    <AIAvatar /><TypingDots />
                  </div>
                )}
                <div ref={messagesEndRef}/>
              </div>

              <div style={{ padding:'12px 16px 14px', borderTop:'1px solid #f0f0f0', flexShrink:0 }}>
                <div style={{ display:'flex', alignItems:'center', gap:8, background:'#f8f8f8', borderRadius:14, padding:'8px 8px 8px 14px', border:'1px solid #ececec' }}>
                  <input ref={inputRef} value={input} onChange={e=>setInput(e.target.value)} onKeyDown={handleKey}
                    placeholder="Message…"
                    style={{ flex:1, border:'none', background:'transparent', fontSize:13.5, color:'#0a0a0a', outline:'none', fontFamily:"'DM Sans', sans-serif", letterSpacing:'-0.1px' }}
                  />
                  <button onClick={toggleVoice}
                    style={{ width:32, height:32, borderRadius:9, border:'none', background:'transparent', cursor:'pointer', display:'flex', alignItems:'center', justifyContent:'center', color:'#999' }}
                    onMouseEnter={e=>{e.currentTarget.style.color='#0a0a0a';e.currentTarget.style.background='#efefef';}}
                    onMouseLeave={e=>{e.currentTarget.style.color='#999';e.currentTarget.style.background='transparent';}}>
                    <IconMic />
                  </button>
                  <button onClick={sendMessage}
                    style={{ width:32, height:32, borderRadius:9, border:'none', background:input.trim()?'#0a0a0a':'#e8e8e8', cursor:input.trim()?'pointer':'default', display:'flex', alignItems:'center', justifyContent:'center', color:input.trim()?'#fff':'#bbb', transition:'background 0.2s, color 0.2s', flexShrink:0 }}>
                    <IconSend />
                  </button>
                </div>
                <div style={{ textAlign:'center', marginTop:8, fontSize:10.5, color:'#ccc', letterSpacing:'0.2px' }}>Powered by VoiceRAG</div>
              </div>
            </>
          ) : (
            <div style={{ flex:1, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:32, padding:'32px 24px' }}>
              <div style={{ fontSize:13, color:'#999', letterSpacing:'0.3px' }}>{voiceStatus}</div>
              <div style={{ height:48, display:'flex', alignItems:'center', opacity:waveActive?1:0.3, transition:'opacity 0.4s' }}>
                <WaveformBars active={waveActive} />
              </div>
              <PulseRing listening={isListening} onClick={()=>{ if(vr.ttsActive) interruptPlayback(); }} />
              <div style={{ fontSize:11, color:'#ccc', letterSpacing:'0.2px', marginTop:'auto' }}>Powered by VoiceRAG</div>
            </div>
          )}
        </div>
      )}

      {/* Launcher button */}
      <button onClick={()=>open?handleClose():setOpen(true)}
        style={{ width:52, height:52, borderRadius:'50%', background:'#0a0a0a', border:'none', cursor:'pointer', display:'flex', alignItems:'center', justifyContent:'center', color:'#fff', boxShadow:'0 4px 20px rgba(0,0,0,0.22)', transition:'transform 0.2s ease, box-shadow 0.2s ease', animation:'vr-launcher-pop 0.5s cubic-bezier(0.34,1.26,0.64,1) 0.3s both' }}
        onMouseEnter={e=>{e.currentTarget.style.transform='scale(1.07)';e.currentTarget.style.boxShadow='0 6px 28px rgba(0,0,0,0.28)';}}
        onMouseLeave={e=>{e.currentTarget.style.transform='scale(1)';e.currentTarget.style.boxShadow='0 4px 20px rgba(0,0,0,0.22)';}}>
        <div style={{ transition:'transform 0.25s ease', transform:open?'rotate(90deg)':'rotate(0deg)' }}>
          {open ? <IconClose /> : <IconChat />}
        </div>
      </button>

    </div>
  );
}

ReactDOM.createRoot(document.getElementById('voicerag-root')).render(
  React.createElement(VoiceRAGWidget)
);
""".strip()


# ─── Loader JS ─────────────────────────────────────────────────────────────────
# Dynamically injects fonts, CSS, mount div, React + Babel from CDN, then
# Babel-transforms the JSX above and executes it.

_CSS = r"""
@keyframes vr-fadeUp{from{opacity:0;transform:translateY(12px) scale(0.97)}to{opacity:1;transform:translateY(0) scale(1)}}
@keyframes vr-fadeDown{from{opacity:1;transform:translateY(0) scale(1)}to{opacity:0;transform:translateY(12px) scale(0.97)}}
@keyframes vr-bar-bounce{0%,100%{transform:scaleY(0.3)}50%{transform:scaleY(1)}}
@keyframes vr-dot-blink{0%,80%,100%{opacity:0.2;transform:scale(0.8)}40%{opacity:1;transform:scale(1)}}
@keyframes vr-ripple{0%{transform:scale(0.9);opacity:0.6}100%{transform:scale(2.2);opacity:0}}
@keyframes vr-launcher-pop{0%{transform:scale(0.8);opacity:0}60%{transform:scale(1.08)}100%{transform:scale(1);opacity:1}}
#voicerag-root{position:fixed;bottom:28px;right:28px;z-index:9999;font-family:'DM Sans',sans-serif;}
#voicerag-root[data-side=left]{right:auto;left:28px;}
#voicerag-root *{box-sizing:border-box;}
#voicerag-root input::placeholder{color:#bbb;}
#voicerag-root ::-webkit-scrollbar{width:4px;}
#voicerag-root ::-webkit-scrollbar-track{background:transparent;}
#voicerag-root ::-webkit-scrollbar-thumb{background:#e0e0e0;border-radius:4px;}
"""


def _make_widget_js() -> str:
    jsx_json = _json.dumps(_WIDGET_JSX)   # safely escapes all special chars
    css_json = _json.dumps(_CSS)

    return (
        r"""/* VoiceRAG Widget v4 */
(function () {
  'use strict';
  if (document.getElementById('voicerag-root')) return;

  var script = document.currentScript || document.querySelector('script[data-api-key]');
  if (!script) { console.error('[VoiceRAG] Script tag with data-api-key not found'); return; }

  var API_KEY = script.getAttribute('data-api-key');
  if (!API_KEY) { console.error('[VoiceRAG] data-api-key is required'); return; }

  var API_URL = (script.getAttribute('data-api-url') || script.src.replace(/\/widget\.js.*/, '')).replace(/\/$/, '');
  var WS_URL  = API_URL.replace(/^http/, 'ws');
  var SIDE    = script.getAttribute('data-position') || 'right';
  var VAD_URL = API_URL + '/vad/';

  window.__VRAG_API_KEY = API_KEY;
  window.__VRAG_API_URL = API_URL;
  window.__VRAG_WS_URL  = WS_URL;
  window.__VRAG_VAD_URL = VAD_URL;
  window.__VRAG_SIDE    = SIDE;

  // Google Fonts
  var fl = document.createElement('link');
  fl.rel = 'stylesheet';
  fl.href = 'https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap';
  document.head.appendChild(fl);

  // CSS
  var st = document.createElement('style');
  st.textContent = """
        + css_json
        + r""";
  document.head.appendChild(st);

  // Mount div
  var root = document.createElement('div');
  root.id = 'voicerag-root';
  if (SIDE === 'left') root.setAttribute('data-side', 'left');
  document.body.appendChild(root);

  // Script loader
  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      if (document.querySelector('script[src="' + src + '"]')) { resolve(); return; }
      var s = document.createElement('script');
      s.src = src; s.async = true;
      s.onload = resolve;
      s.onerror = function () { reject(new Error('Failed: ' + src)); };
      document.head.appendChild(s);
    });
  }

  var JSX_CODE = """
        + jsx_json
        + r""";

  loadScript('https://unpkg.com/react@18.3.1/umd/react.production.min.js')
    .then(function () { return loadScript('https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js'); })
    .then(function () { return loadScript('https://unpkg.com/@babel/standalone@7.29.0/babel.min.js'); })
    .then(function () {
      try {
        var compiled = Babel.transform(JSX_CODE, { presets: ['react'] }).code;
        // eslint-disable-next-line no-new-func
        (new Function(compiled))();
      } catch (e) { console.error('[VoiceRAG] Widget compile error:', e); }
    })
    .catch(function (e) { console.error('[VoiceRAG] Dependency load failed:', e); });
})();
"""
    )


WIDGET_JS = _make_widget_js()


@router.get("/widget.js")
def serve_widget():
    """Serve the embeddable chat widget JavaScript."""
    return Response(
        content=WIDGET_JS,
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache, no-store"},
    )
