import { useState, useRef, useCallback, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE = API_BASE.replace(/^http/, 'ws');

/**
 * Real-time conversational voice hook powered by Silero VAD.
 *
 * Uses the Silero VAD neural network (via @ricky0123/vad-web) to detect
 * real human speech vs. background noise. Only confirmed speech segments
 * are recorded and sent to the backend for processing.
 *
 * Flow:
 *   1. Silero VAD listens to the mic continuously
 *   2. onSpeechStart → UI shows "Hearing you..."
 *   3. onSpeechEnd → stop recording, send accumulated audio to backend
 *   4. Backend: STT → RAG → TTS (sentence-by-sentence)
 *   5. Frontend plays TTS audio chunks from a sequential queue
 *   6. After playback finishes → VAD resumes listening automatically
 */
export function useVoiceConversation() {
  // Connection state
  const [isConnected, setIsConnected] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isUserTalking, setIsUserTalking] = useState(false);
  const [status, setStatus] = useState('idle');
  const [statusMessage, setStatusMessage] = useState('');
  const [error, setError] = useState(null);

  // Conversation state
  const [conversationId, setConversationId] = useState(null);
  const [exchanges, setExchanges] = useState([]);
  const [currentTranscription, setCurrentTranscription] = useState('');
  const [currentAnswer, setCurrentAnswer] = useState('');

  // Refs
  const wsRef = useRef(null);
  const vadRef = useRef(null);
  const audioQueueRef = useRef([]);
  const isPlayingRef = useRef(false);
  const isProcessingRef = useRef(false);
  // Currently playing TTS source — kept so barge-in can stop it instantly.
  const activeSourceRef = useRef(null);
  // Incremented on every interrupt. Any async decode/onended callback from a
  // prior generation is dropped on the floor so stale chunks don't resurrect
  // playback after the user has barged in.
  const playbackGenerationRef = useRef(0);
  // Gate for inbound audio_chunk messages. After barge-in, we drop any chunks
  // that the backend had already put on the wire before it saw our interrupt.
  // Reopened on the next turn's `transcription` event (or `answer`).
  const acceptingAudioRef = useRef(true);
  // ── Echo-aware barge-in gating ──
  // Long-lived mic stream + AnalyserNode used ONLY for polling mic energy
  // while VAD is paused during TTS. A separate polling interval replaces the
  // VAD for barge-in detection so speaker echo can never reach onSpeechStart.
  const monitorStreamRef = useRef(null);
  const monitorContextRef = useRef(null);
  const micAnalyserRef = useRef(null);
  // AnalyserNode in the TTS playback graph. Every playing BufferSource routes
  // through playbackGainRef so this analyser sees all assistant audio.
  const playbackGainRef = useRef(null);
  const playbackAnalyserRef = useRef(null);
  // setInterval handle for the barge-in energy polling loop.
  const bargeInDetectorRef = useRef(null);
  // Consecutive samples above threshold — avoids single-spike false triggers.
  const bargeInConsecutiveRef = useRef(0);
  // Software gate: true from 'transcription' until resumeVAD() is called.
  // Guards onSpeechStart independently of vad.pause() timing — if the VAD
  // worker has queued frames that fire after pause() is called, this ref
  // catches them before any processing begins.
  const ttsActiveRef = useRef(false);
  // AudioContext for reliable playback
  const audioContextRef = useRef(null);
  // Refs that mirror state (to avoid stale closures in WS/VAD callbacks)
  const currentTranscriptionRef = useRef('');
  const currentAnswerRef = useRef('');
  // Track whether we're connected to avoid race conditions
  const isConnectedRef = useRef(false);
  // Per-utterance PCM capture refs (for low-latency WAV chunking)
  const captureStreamRef = useRef(null);
  const captureContextRef = useRef(null);
  const captureSourceRef = useRef(null);
  const captureProcessorRef = useRef(null);
  const captureIntervalRef = useRef(null);
  const captureBuffersRef = useRef([]);

  // ── Get or create AudioContext ──
  const getAudioContext = useCallback(() => {
    if (!audioContextRef.current || audioContextRef.current.state === 'closed') {
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 24000, // Match Kokoro TTS output sample rate
      });
    }
    // Resume if suspended (browser autoplay policy)
    if (audioContextRef.current.state === 'suspended') {
      audioContextRef.current.resume();
    }
    return audioContextRef.current;
  }, []);

  // ── Playback analyser: all TTS sources route through this node ──
  const ensurePlaybackAnalyser = useCallback(() => {
    const ctx = getAudioContext();
    if (playbackGainRef.current && playbackAnalyserRef.current) {
      return playbackGainRef.current;
    }
    const gain = ctx.createGain();
    gain.gain.value = 1.0;
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 1024;
    analyser.smoothingTimeConstant = 0.25;
    // Fan out: gain → analyser (for measurement) and gain → destination (to speakers).
    gain.connect(analyser);
    gain.connect(ctx.destination);
    playbackGainRef.current = gain;
    playbackAnalyserRef.current = analyser;
    return gain;
  }, [getAudioContext]);

  // ── Mic monitoring stream (separate from VAD + capture pipelines) ──
  const startEchoMonitor = useCallback(async () => {
    if (monitorStreamRef.current) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
          sampleRate: 16000,
        },
      });
      monitorStreamRef.current = stream;

      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const ctx = new AudioCtx();
      monitorContextRef.current = ctx;

      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 1024;
      analyser.smoothingTimeConstant = 0.25;
      source.connect(analyser);
      micAnalyserRef.current = analyser;
      // Make sure the playback analyser exists too so confirmBargeInByEnergy
      // has both sides to compare.
      ensurePlaybackAnalyser();
      console.log('[EchoMonitor] Initialized (mic + playback analysers live)');
    } catch (err) {
      console.warn('[EchoMonitor] Failed to initialize:', err);
    }
  }, [ensurePlaybackAnalyser]);

  const stopEchoMonitor = useCallback(() => {
    if (monitorStreamRef.current) {
      try {
        monitorStreamRef.current.getTracks().forEach((t) => t.stop());
      } catch {
        // ignore
      }
      monitorStreamRef.current = null;
    }
    if (monitorContextRef.current) {
      try {
        monitorContextRef.current.close();
      } catch {
        // ignore
      }
      monitorContextRef.current = null;
    }
    micAnalyserRef.current = null;
    playbackGainRef.current = null;
    playbackAnalyserRef.current = null;
  }, []);

  // ── RMS helpers + echo gate ──
  const rmsFromAnalyser = (analyser) => {
    if (!analyser) return 0;
    const data = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(data);
    let sum = 0;
    for (let i = 0; i < data.length; i++) {
      const centered = (data[i] - 128) / 128;
      sum += centered * centered;
    }
    return Math.sqrt(sum / data.length);
  };

  // ── Barge-in energy detector ──
  // Polls mic vs TTS playback RMS at POLL_MS intervals while TTS is active
  // (VAD is paused during this period so echo can't reach onSpeechStart).
  // When mic energy consistently exceeds playback by RATIO, it's a real
  // human interruption — we trigger barge-in directly.
  const BARGE_POLL_MS = 40;
  const BARGE_CALIBRATION_SAMPLES = 5;   // first 200ms (5 × 40ms) — measure echo
  const BARGE_CONSECUTIVE = 6;           // 6 × 40ms = 240ms sustained speech
  const BARGE_RATIO_MULT = 2.5;          // threshold = baseline_echo × 2.5
  const BARGE_ABS_THRESHOLD = 0.07;      // absolute mic floor (room-independent)
  const BARGE_FLOOR = 0.03;              // ignore near-silence on mic

  const stopBargeInDetector = useCallback(() => {
    if (bargeInDetectorRef.current) {
      clearInterval(bargeInDetectorRef.current);
      bargeInDetectorRef.current = null;
    }
    bargeInConsecutiveRef.current = 0;
  }, []);

  // Forward-declared — defined after interruptPlayback + resumeVAD.
  const startBargeInDetectorRef = useRef(null);

  // ── Resume VAD Safely ──
  const resumeVAD = useCallback(() => {
    // Clear the software TTS gate — from this point on, onSpeechStart is
    // allowed to process detections again.
    ttsActiveRef.current = false;
    if (vadRef.current && isConnectedRef.current) {
      try {
        vadRef.current.start();
        console.log('[VAD] Resumed listening');
      } catch {
        // Already started — this is fine
      }
      setIsListening(true);
      setStatus('listening');
      setStatusMessage('');
    }
  }, []);

  // ── Utterance Audio Chunk Streaming (PCM -> WAV) ──
  const blobToBase64 = useCallback((blob) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const result = reader.result;
        if (!result || typeof result !== 'string') {
          reject(new Error('Failed to encode audio chunk'));
          return;
        }
        const base64 = result.split(',')[1] || '';
        resolve(base64);
      };
      reader.onerror = () => reject(new Error('FileReader failed'));
      reader.readAsDataURL(blob);
    });
  }, []);

  const float32ToWavBlob = useCallback((float32Array, sampleRate = 16000) => {
    const numChannels = 1;
    const bytesPerSample = 2;
    const blockAlign = numChannels * bytesPerSample;
    const dataSize = float32Array.length * bytesPerSample;
    const headerSize = 44;
    const buffer = new ArrayBuffer(headerSize + dataSize);
    const view = new DataView(buffer);

    const writeString = (offset, str) => {
      for (let i = 0; i < str.length; i++) {
        view.setUint8(offset + i, str.charCodeAt(i));
      }
    };

    writeString(0, 'RIFF');
    view.setUint32(4, headerSize + dataSize - 8, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * blockAlign, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bytesPerSample * 8, true);
    writeString(36, 'data');
    view.setUint32(40, dataSize, true);

    let offset = headerSize;
    for (let i = 0; i < float32Array.length; i++) {
      let s = Math.max(-1, Math.min(1, float32Array[i]));
      s = s < 0 ? s * 0x8000 : s * 0x7FFF;
      view.setInt16(offset, s, true);
      offset += 2;
    }

    return new Blob([buffer], { type: 'audio/wav' });
  }, []);

  const flushPcmBuffers = useCallback(async (force = false) => {
    const chunks = captureBuffersRef.current;
    if (!chunks.length) {
      return;
    }

    let total = 0;
    for (const chunk of chunks) {
      total += chunk.length;
    }

    // Avoid ultra-tiny partial payloads unless we're forcing a final flush.
    if (!force && total < 2048) {
      return;
    }

    const merged = new Float32Array(total);
    let offset = 0;
    for (const chunk of chunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }
    captureBuffersRef.current = [];

    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    try {
      const sampleRate = captureContextRef.current?.sampleRate || 16000;
      const wavBlob = float32ToWavBlob(merged, sampleRate);
      const base64 = await blobToBase64(wavBlob);
      wsRef.current.send(JSON.stringify({
        type: 'audio_chunk',
        data: base64,
      }));
    } catch (err) {
      console.error('[Stream] Failed to flush WAV chunk:', err);
    }
  }, [blobToBase64, float32ToWavBlob]);

  const startSpeechChunkStreaming = useCallback(async () => {
    if (captureProcessorRef.current) {
      return;
    }

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: 1,
        sampleRate: 16000,
      },
    });
    captureStreamRef.current = stream;

    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    const ctx = new AudioCtx({ sampleRate: 16000 });
    captureContextRef.current = ctx;

    const source = ctx.createMediaStreamSource(stream);
    captureSourceRef.current = source;

    const processor = ctx.createScriptProcessor(2048, 1, 1);
    captureProcessorRef.current = processor;

    processor.onaudioprocess = (event) => {
      const input = event.inputBuffer.getChannelData(0);
      captureBuffersRef.current.push(new Float32Array(input));
    };

    source.connect(processor);
    processor.connect(ctx.destination);

    captureIntervalRef.current = window.setInterval(() => {
      flushPcmBuffers(false);
    }, 300);
  }, [flushPcmBuffers]);

  const stopSpeechChunkStreaming = useCallback(async (commit = true) => {
    if (captureIntervalRef.current) {
      window.clearInterval(captureIntervalRef.current);
      captureIntervalRef.current = null;
    }

    if (commit) {
      await flushPcmBuffers(true);
    } else {
      captureBuffersRef.current = [];
    }

    if (captureProcessorRef.current) {
      try {
        captureProcessorRef.current.disconnect();
      } catch (err) {
        console.debug('[Stream] captureProcessor disconnect issue:', err);
      }
      captureProcessorRef.current.onaudioprocess = null;
      captureProcessorRef.current = null;
    }

    if (captureSourceRef.current) {
      try {
        captureSourceRef.current.disconnect();
      } catch (err) {
        console.debug('[Stream] captureSource disconnect issue:', err);
      }
      captureSourceRef.current = null;
    }

    if (captureContextRef.current) {
      try {
        await captureContextRef.current.close();
      } catch (err) {
        console.debug('[Stream] captureContext close issue:', err);
      }
      captureContextRef.current = null;
    }

    if (captureStreamRef.current) {
      captureStreamRef.current.getTracks().forEach((track) => track.stop());
      captureStreamRef.current = null;
    }
    captureBuffersRef.current = [];

    if (commit && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'audio_commit' }));
    } else if (!commit && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'audio_discard' }));
    }
  }, [flushPcmBuffers]);

  // ── Barge-in: stop current TTS playback + tell backend to cancel ──
  const interruptPlayback = useCallback(() => {
    stopBargeInDetector();
    // User is taking control — clear TTS gate so VAD can listen again
    // (after the grace period in the barge-in detector).
    ttsActiveRef.current = false;
    // Bump generation so any in-flight decode/onended from previous chunks
    // doesn't accidentally start the next queued chunk.
    playbackGenerationRef.current += 1;

    audioQueueRef.current = [];

    if (activeSourceRef.current) {
      try {
        activeSourceRef.current.onended = null;
        activeSourceRef.current.stop(0);
      } catch (err) {
        // Stop can throw if the source hasn't started or already ended — safe to ignore.
        console.debug('[Audio] Interrupt stop() threw:', err);
      }
      try {
        activeSourceRef.current.disconnect();
      } catch {
        // ignore
      }
      activeSourceRef.current = null;
    }

    isPlayingRef.current = false;
    setIsSpeaking(false);
    // Drop any audio_chunk messages that were in flight before the backend
    // saw the interrupt. Reopened when the next turn's transcription arrives.
    acceptingAudioRef.current = false;

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'interrupt' }));
      console.log('[Audio] Barge-in: sent interrupt to backend');
    }
  }, [stopBargeInDetector]);

  // ── Barge-in energy detector (polling loop, adaptive) ──
  // Phase 1 — Calibration (first BARGE_CALIBRATION_SAMPLES ticks):
  //   Measure the actual echo ratio (mic/tts) for this room/device.
  //   Rooms vary widely: some attenuate echo to 5%, others to 40%.
  //   Fixed thresholds fail at both extremes.
  // Phase 2 — Detection:
  //   Require mic > adaptiveThreshold AND either:
  //     (a) ratio-based: mic > (calibrated_echo × BARGE_RATIO_MULT), OR
  //     (b) absolute:    mic > BARGE_ABS_THRESHOLD (user speaking loudly)
  //   Confirmed after BARGE_CONSECUTIVE passes (~240ms) with no resets.
  const startBargeInDetector = useCallback(() => {
    stopBargeInDetector();
    bargeInConsecutiveRef.current = 0;

    let calibCount = 0;
    let calibRatioSum = 0;
    let dynamicThreshold = null; // set after calibration

    bargeInDetectorRef.current = setInterval(() => {
      if (!isPlayingRef.current) {
        stopBargeInDetector();
        return;
      }
      const mic = rmsFromAnalyser(micAnalyserRef.current);
      const tts = rmsFromAnalyser(playbackAnalyserRef.current);

      // Skip until TTS is actually audible (avoid calibrating on silence
      // at the very start of the first chunk's decode/buffer fill).
      if (tts < 0.01) return;

      // ── Phase 1: Calibration ──
      if (calibCount < BARGE_CALIBRATION_SAMPLES) {
        calibRatioSum += mic / tts;
        calibCount++;
        if (calibCount === BARGE_CALIBRATION_SAMPLES) {
          const baseRatio = calibRatioSum / calibCount;
          // Threshold = 2.5× above measured echo baseline, but never below 1.5.
          dynamicThreshold = Math.max(baseRatio * BARGE_RATIO_MULT, 1.5);
          console.log(`[BargeIn] Calibrated: echoBase=${baseRatio.toFixed(3)} → threshold=${dynamicThreshold.toFixed(3)}`);
        }
        return;
      }

      // ── Phase 2: Detection ──
      const ratioPass  = mic > BARGE_FLOOR && tts > 0 && (mic / tts) > dynamicThreshold;
      const absPass    = mic > BARGE_ABS_THRESHOLD;

      if (ratioPass || absPass) {
        bargeInConsecutiveRef.current++;
        console.log(
          `[BargeIn] Candidate: mic=${mic.toFixed(3)} tts=${tts.toFixed(3)} ` +
          `ratio=${tts > 0 ? (mic/tts).toFixed(2) : '∞'} ` +
          `(${bargeInConsecutiveRef.current}/${BARGE_CONSECUTIVE})`
        );
        if (bargeInConsecutiveRef.current >= BARGE_CONSECUTIVE) {
          console.log('[BargeIn] Confirmed — real speech detected, interrupting TTS');
          stopBargeInDetector();
          interruptPlayback();
          isProcessingRef.current = false;
          setIsProcessing(false);
          // Capture starts immediately — don't lose the leading edge of the
          // user's utterance while we wait for the grace timer.
          startSpeechChunkStreaming().catch((err) => {
            console.error('[BargeIn] Failed to start chunk streaming:', err);
          });
          // Grace period before re-enabling VAD: the interrupted TTS chunk
          // leaves room echo for ~150-200ms. ttsActiveRef was already cleared
          // by interruptPlayback(), so resumeVAD() will allow onSpeechStart.
          setTimeout(resumeVAD, 200);
        }
      } else {
        bargeInConsecutiveRef.current = 0;
      }
    }, BARGE_POLL_MS);
  }, [stopBargeInDetector, interruptPlayback, resumeVAD, startSpeechChunkStreaming]);

  // Keep the forward-declared ref in sync so enqueueAudio (defined earlier)
  // can reach startBargeInDetector without a circular dependency.
  startBargeInDetectorRef.current = startBargeInDetector;

  // ── Audio Playback Queue (using AudioContext for reliability) ──
  const playNextInQueue = useCallback(() => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      setIsSpeaking(false);
      stopBargeInDetector();
      // Short grace period: lets speaker echo die off before VAD listens again.
      // Without this, the tail of the last TTS chunk can trigger onSpeechStart.
      setTimeout(() => {
        resumeVAD();
      }, 500);
      return;
    }

    isPlayingRef.current = true;
    const { audioData, index, total } = audioQueueRef.current.shift();
    // Capture the generation at dequeue time. If an interrupt happens while
    // decodeAudioData is still in flight, we bail out instead of starting.
    const generation = playbackGenerationRef.current;

    try {
      const binaryStr = atob(audioData);
      const bytes = new Uint8Array(binaryStr.length);
      for (let i = 0; i < binaryStr.length; i++) {
        bytes[i] = binaryStr.charCodeAt(i);
      }

      const ctx = getAudioContext();

      // Decode the WAV bytes into an AudioBuffer
      ctx.decodeAudioData(
        bytes.buffer.slice(0), // Need a copy because decodeAudioData detaches the buffer
        (audioBuffer) => {
          if (generation !== playbackGenerationRef.current) {
            // An interrupt superseded this chunk while it was decoding.
            return;
          }
          const source = ctx.createBufferSource();
          source.buffer = audioBuffer;
          // Route through the playback gain/analyser so the echo gate can
          // measure TTS level in real time. Falls back to direct destination
          // if the analyser graph couldn't be built.
          const playbackNode = ensurePlaybackAnalyser();
          source.connect(playbackNode || ctx.destination);
          activeSourceRef.current = source;
          source.onended = () => {
            // Ignore onended from a source that was stopped by an interrupt.
            if (generation !== playbackGenerationRef.current) {
              return;
            }
            if (activeSourceRef.current === source) {
              activeSourceRef.current = null;
            }
            console.log(`[Audio] Chunk ${index}/${total} finished (${audioBuffer.duration.toFixed(1)}s)`);
            playNextInQueue();
          };
          source.start(0);
          console.log(`[Audio] Playing chunk ${index}/${total}`);
        },
        (decodeErr) => {
          console.error(`[Audio] decodeAudioData failed for chunk ${index}/${total}:`, decodeErr);
          // Try fallback with Audio element
          playWithAudioElement(audioData, index, total);
        }
      );
    } catch (err) {
      console.error('[Audio] Error in playback pipeline:', err);
      // Try fallback
      playWithAudioElement(audioData, index, total);
    }
  }, [getAudioContext, resumeVAD]);

  // ── Fallback: Play with Audio element ──
  const playWithAudioElement = useCallback((audioData, index, total) => {
    try {
      const binaryStr = atob(audioData);
      const bytes = new Uint8Array(binaryStr.length);
      for (let i = 0; i < binaryStr.length; i++) {
        bytes[i] = binaryStr.charCodeAt(i);
      }

      const blob = new Blob([bytes], { type: 'audio/wav' });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);

      audio.onended = () => {
        URL.revokeObjectURL(url);
        console.log(`[Audio Fallback] Chunk ${index}/${total} finished`);
        playNextInQueue();
      };

      audio.onerror = (e) => {
        URL.revokeObjectURL(url);
        console.error(`[Audio Fallback] Chunk ${index}/${total} error:`, e);
        // Skip this chunk and continue with next
        playNextInQueue();
      };

      audio.play().catch((e) => {
        URL.revokeObjectURL(url);
        console.error(`[Audio Fallback] Play rejected for ${index}/${total}:`, e);
        playNextInQueue();
      });
    } catch (err) {
      console.error('[Audio Fallback] Total failure:', err);
      // Give up on this chunk, continue
      playNextInQueue();
    }
  }, [playNextInQueue]);

  const enqueueAudio = useCallback((audioData, index, total) => {
    console.log(`[Audio] Enqueuing chunk ${index}/${total} (${(audioData.length * 0.75 / 1024).toFixed(0)}KB)`);
    audioQueueRef.current.push({ audioData, index, total });

    if (!isPlayingRef.current) {
      isPlayingRef.current = true;
      setIsSpeaking(true);
      setStatus('speaking');
      // Pause VAD so TTS echo never reaches onSpeechStart.
      // The barge-in energy detector handles real interruptions.
      if (vadRef.current) {
        try { vadRef.current.pause(); } catch { /* already paused */ }
      }
      if (startBargeInDetectorRef.current) {
        startBargeInDetectorRef.current();
      }
      playNextInQueue();
    }
  }, [playNextInQueue]);

  // ── Handle Speech End from VAD ──
  const handleSpeechEnd = useCallback(async (audioFloat32) => {
    setIsUserTalking(false);

    // NOTE: we no longer bail out when isPlayingRef is true — barge-in is
    // handled in onSpeechStart (stops playback + fires `interrupt`). By the
    // time onSpeechEnd fires, playback is already torn down.
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.log('[VAD] WebSocket not open, ignoring');
      await stopSpeechChunkStreaming(false);
      return;
    }

    // Check minimum speech length (~0.5 seconds at 16kHz)
    if (audioFloat32.length < 8000) {
      console.log(`[VAD] Speech too short (${(audioFloat32.length / 16000).toFixed(2)}s), ignoring`);
      await stopSpeechChunkStreaming(false);
      return;
    }

    const durationSecs = (audioFloat32.length / 16000).toFixed(1);
    console.log(`[VAD] ━━━ Speech captured: ${durationSecs}s (${audioFloat32.length} samples) ━━━`);

    // DO NOT pause VAD here. We need it to keep listening during the entire
    // processing + TTS playback so the user can barge in. Barge-in is handled
    // in onSpeechStart by invoking interruptPlayback().

    isProcessingRef.current = true;
    setIsProcessing(true);
    setStatus('processing');
    setStatusMessage('Finalizing speech...');

    try {
      await stopSpeechChunkStreaming(true);
    } catch (err) {
      console.error('[VAD] Failed to finalize streamed utterance:', err);
      isProcessingRef.current = false;
      setIsProcessing(false);
      resumeVAD();
    }
  }, [resumeVAD, stopSpeechChunkStreaming]);

  // ── Load VAD bundle via script tag (avoids CJS/ESM issues with Vite) ──
  const ensureOnnxRuntimeGlobal = useCallback(async () => {
    if (window.ort?.InferenceSession) {
      return;
    }

    const ortModule = await import('onnxruntime-web');
    const ort = ortModule?.default || ortModule;

    if (!ort?.InferenceSession) {
      throw new Error('Failed to load ONNX Runtime for VAD');
    }

    window.ort = ort;
  }, []);

  const loadVADBundle = useCallback(() => {
    return new Promise((resolve, reject) => {
      // Already loaded?
      if (window.vad && window.vad.MicVAD) {
        resolve(window.vad.MicVAD);
        return;
      }

      const script = document.createElement('script');
      script.src = '/vad-bundle.min.js';
      script.onload = () => {
        if (window.vad && window.vad.MicVAD) {
          resolve(window.vad.MicVAD);
        } else {
          reject(new Error('VAD bundle loaded but MicVAD not found'));
        }
      };
      script.onerror = () => reject(new Error('Failed to load VAD bundle'));
      document.head.appendChild(script);
    });
  }, []);

  // ── Initialize Silero VAD ──
  const startVAD = useCallback(async () => {
    await ensureOnnxRuntimeGlobal();
    const MicVAD = await loadVADBundle();

    const vad = await MicVAD.new({
      model: "legacy",
      // Point to files served from /public (served at root in both dev and prod)
      baseAssetPath: "/",
      onnxWASMBasePath: "/",
      // Apply WebRTC AEC to the VAD's internal mic stream so TTS playback
      // is cancelled before Silero ever sees the audio frames.
      additionalAudioConstraints: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: 1,
        sampleRate: 16000,
      },
      // Silero VAD thresholds — tuned for natural conversation
      positiveSpeechThreshold: 0.80,  // High confidence to start speech (filters noise)
      negativeSpeechThreshold: 0.35,  // Lower threshold to end speech
      redemptionMs: 1200,             // 1.2s of silence before ending utterance (faster, more natural)
      minSpeechMs: 400,               // Minimum 0.4s of speech to count
      preSpeechPadMs: 300,            // Capture 0.3s before speech starts
      submitUserSpeechOnPause: true,  // Submit audio even if VAD is paused mid-speech

      onSpeechStart: () => {
        console.log('[VAD] Speech started');

        // Primary gate: ttsActiveRef is set at 'transcription' (before any
        // audio plays) and cleared only in resumeVAD(). This catches VAD
        // worker frames that were queued before pause() took full effect,
        // as well as any race at the first chunk boundary.
        // Secondary gate: isPlayingRef catches the case where ttsActiveRef
        // was somehow not set (e.g. TTS with no prior transcription event).
        if (ttsActiveRef.current || isPlayingRef.current) {
          console.log('[VAD] onSpeechStart suppressed (TTS active)');
          return;
        }

        // Mid-RAG barge-in: cancel the processing turn.
        if (isProcessingRef.current) {
          console.log('[VAD] Barge-in during processing — cancelling previous turn');
          interruptPlayback();
          isProcessingRef.current = false;
          setIsProcessing(false);
        }

        setIsUserTalking(true);
        setIsListening(true);
        setStatus('listening');
        setStatusMessage('Listening...');
        setError(null);
        startSpeechChunkStreaming().catch((err) => {
          console.error('[Stream] Failed to start chunk streaming:', err);
        });
      },

      onSpeechEnd: (audio) => {
        console.log('[VAD] Speech ended');
        handleSpeechEnd(audio);
      },

      onVADMisfire: () => {
        // Speech was too short — VAD discarded it
        console.log('[VAD] Misfire (too short, ignored)');
        setIsUserTalking(false);
        stopSpeechChunkStreaming(false).catch(() => {});
      },
    });

    vadRef.current = vad;
    vad.start();

    setIsListening(true);
    setStatus('listening');
    console.log('[VAD] Silero VAD initialized and listening');
  }, [
    handleSpeechEnd,
    loadVADBundle,
    ensureOnnxRuntimeGlobal,
    startSpeechChunkStreaming,
    stopSpeechChunkStreaming,
    interruptPlayback,
  ]);

  const stopVAD = useCallback(async () => {
    await stopSpeechChunkStreaming(false).catch(() => {});

    if (vadRef.current) {
      try {
        await vadRef.current.pause();
        await vadRef.current.destroy();
      } catch {
        // Ignore cleanup errors
      }
      vadRef.current = null;
    }
    setIsListening(false);
    setIsUserTalking(false);
  }, [stopSpeechChunkStreaming]);

  // ── WebSocket Connection ──
  const connect = useCallback(async (language = null) => {
    if (wsRef.current) return;

    setError(null);

    // Pre-initialize AudioContext on user gesture (required by browsers)
    getAudioContext();

    const token = localStorage.getItem('voicerag_token');
    if (!token) {
      setError('Please log in to use the voice assistant.');
      return;
    }
    const langParam = language && language !== 'auto' ? `&language=${encodeURIComponent(language)}` : '';
    const ws = new WebSocket(
      `${WS_BASE}/voice/conversation?token=${encodeURIComponent(token)}${langParam}`
    );
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        
        // Only log non-audio messages in detail (audio is too noisy)
        if (msg.type !== 'audio_chunk') {
          console.log(`[WS] ← ${msg.type}`, msg.text ? `"${msg.text.substring(0, 60)}..."` : msg.message || '');
        } else {
          console.log(`[WS] ← audio_chunk ${msg.index}/${msg.total}`);
        }

        switch (msg.type) {
          case 'listening':
            // Backend is ready for next turn
            isProcessingRef.current = false;
            setIsProcessing(false);
            if (!isPlayingRef.current && audioQueueRef.current.length === 0) {
              // Resume VAD if not playing audio
              resumeVAD();
            }
            break;

          case 'status':
            setStatusMessage(msg.message || '');
            break;

          case 'transcription':
            // A fresh turn's STT has landed — audio chunks from here on are
            // legitimate, so reopen the inbound-audio gate.
            acceptingAudioRef.current = true;
            currentTranscriptionRef.current = msg.text || '';
            setCurrentTranscription(msg.text || '');
            setStatusMessage('Got it! Thinking...');
            // Arm the software TTS gate. onSpeechStart will suppress any
            // VAD detections from here until resumeVAD() is called.
            ttsActiveRef.current = true;
            // Pre-emptively pause VAD here, before any TTS arrives.
            // Waiting until the first audio_chunk to pause is too late:
            // decodeAudioData is async, so audio can hit the speakers while
            // VAD's internal frame queue still has unprocessed samples —
            // those frames contain echo and trigger a false onSpeechStart.
            // Pausing now gives VAD time to fully drain before any playback.
            if (vadRef.current) {
              try { vadRef.current.pause(); } catch { /* already paused */ }
            }
            break;

          case 'partial_transcription':
            currentTranscriptionRef.current = msg.text || '';
            setCurrentTranscription(msg.text || '');
            setStatusMessage('Listening...');
            break;

          case 'answer':
            currentAnswerRef.current = msg.text || '';
            setCurrentAnswer(msg.text || '');
            if (msg.conversation_id) {
              setConversationId(msg.conversation_id);
            }
            break;

          case 'audio_chunk':
            if (!acceptingAudioRef.current) {
              console.log(`[Audio] Dropped stale audio_chunk ${msg.index}/${msg.total} (post-barge-in)`);
              break;
            }
            // Belt-and-suspenders: pause VAD synchronously before decode
            // begins. The transcription handler already did this, but in
            // the barge-in path the VAD was just resumed and may have
            // queued audio frames that haven't been processed yet. A second
            // synchronous pause here costs nothing and closes that window.
            if (vadRef.current && !isPlayingRef.current) {
              try { vadRef.current.pause(); } catch { /* already paused */ }
            }
            enqueueAudio(msg.data, msg.index, msg.total);
            break;

          case 'speaking_done':
            console.log('[WS] ✓ Speaking done — finalizing exchange');
            // AI finished generating audio — finalize the exchange
            if (currentTranscriptionRef.current || currentAnswerRef.current) {
              setExchanges(prev => [
                ...prev,
                {
                  userText: currentTranscriptionRef.current || '',
                  aiText: currentAnswerRef.current || '',
                },
              ]);
            }
            currentTranscriptionRef.current = '';
            currentAnswerRef.current = '';
            setCurrentTranscription('');
            setCurrentAnswer('');

            // Mark processing as done
            isProcessingRef.current = false;
            setIsProcessing(false);

            // If no audio was queued at all, resume VAD immediately
            if (!isPlayingRef.current && audioQueueRef.current.length === 0) {
              setIsSpeaking(false);
              resumeVAD();
            }
            // Otherwise, VAD resume happens when audio queue empties in playNextInQueue
            break;

          case 'error':
            console.error('[WS] ⚠ Error from server:', msg.message);
            setError(msg.message || 'Something went wrong');
            setStatusMessage(msg.message || 'Something went wrong');
            isProcessingRef.current = false;
            setIsProcessing(false);
            // Only resume VAD if TTS isn't still playing. If audio is in
            // the queue (e.g. a backend error mid-stream), let the queue
            // drain naturally — resumeVAD fires in playNextInQueue.
            if (!isPlayingRef.current && audioQueueRef.current.length === 0) {
              resumeVAD();
            }
            break;

          case 'done':
            break;
        }
      } catch (err) {
        console.error('[WS] Failed to parse message:', err);
      }
    };

    ws.onclose = (event) => {
      console.log(`[WS] Closed (code=${event.code}, reason=${event.reason})`);
      isConnectedRef.current = false;
      setIsConnected(false);
      setStatus('idle');
      wsRef.current = null;
      stopVAD();
    };

    ws.onerror = (err) => {
      console.error('[WS] WebSocket error:', err);
      setError('Connection to backend lost. Try reconnecting.');
    };

    // Wait for connection
    await new Promise((resolve, reject) => {
      ws.addEventListener('open', resolve, { once: true });
      ws.addEventListener('error', () => {
        reject(new Error('Could not connect to voice backend. Is the server running?'));
      }, { once: true });
    });

    isConnectedRef.current = true;
    setIsConnected(true);
    console.log('[WS] ✓ Voice WebSocket connected');

    // Spin up the echo monitor before VAD so the analysers are live the first
    // time the user speaks (and the first time TTS plays back).
    await startEchoMonitor();

    // Start Silero VAD
    try {
      await startVAD();
    } catch (err) {
      const message = err?.message || 'Failed to initialize voice activity detection';
      console.error('[VAD] Failed to initialize:', err);
      setError(message);
      setStatus('idle');
      setStatusMessage(message);
      ws.close();
      throw new Error(message);
    }
  }, [startVAD, stopVAD, enqueueAudio, getAudioContext, resumeVAD, startEchoMonitor]);

  const disconnect = useCallback(() => {
    isConnectedRef.current = false;

    // Send end session
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'end_session' }));
      wsRef.current.close();
    }
    wsRef.current = null;

    stopVAD();
    stopEchoMonitor();
    stopBargeInDetector();

    // Close AudioContext
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }

    // Clear audio queue
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    isProcessingRef.current = false;

    setIsConnected(false);
    setIsSpeaking(false);
    setIsProcessing(false);
    setIsUserTalking(false);
    setStatus('idle');
    setStatusMessage('');
    setCurrentTranscription('');
    setCurrentAnswer('');
    setError(null);
  }, [stopVAD, stopEchoMonitor, stopBargeInDetector]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    // State
    isConnected,
    isListening,
    isSpeaking,
    isProcessing,
    isUserTalking,
    status,
    statusMessage,
    error,
    conversationId,
    exchanges,
    currentTranscription,
    currentAnswer,

    // Actions
    connect,
    disconnect,
    setExchanges,
  };
}
