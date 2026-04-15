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
  // AudioContext for reliable playback
  const audioContextRef = useRef(null);
  // Refs that mirror state (to avoid stale closures in WS/VAD callbacks)
  const currentTranscriptionRef = useRef('');
  const currentAnswerRef = useRef('');
  // Track whether we're connected to avoid race conditions
  const isConnectedRef = useRef(false);

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

  // ── Resume VAD Safely ──
  const resumeVAD = useCallback(() => {
    if (vadRef.current && isConnectedRef.current) {
      try {
        vadRef.current.start();
        console.log('[VAD] Resumed listening');
      } catch (e) {
        // Already started — this is fine
      }
      setIsListening(true);
      setStatus('listening');
      setStatusMessage('');
    }
  }, []);

  // ── Audio Playback Queue (using AudioContext for reliability) ──
  const playNextInQueue = useCallback(() => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      setIsSpeaking(false);

      // Resume VAD listening after playback finishes
      resumeVAD();
      return;
    }

    isPlayingRef.current = true;
    const { audioData, index, total } = audioQueueRef.current.shift();

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
          const source = ctx.createBufferSource();
          source.buffer = audioBuffer;
          source.connect(ctx.destination);
          source.onended = () => {
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
      setIsSpeaking(true);
      setStatus('speaking');
      playNextInQueue();
    }
  }, [playNextInQueue]);

  // ── Convert Float32 PCM to WAV Blob ──
  const float32ToWavBlob = useCallback((float32Array, sampleRate = 16000) => {
    const numChannels = 1;
    const bytesPerSample = 2; // 16-bit PCM
    const blockAlign = numChannels * bytesPerSample;
    const dataSize = float32Array.length * bytesPerSample;
    const headerSize = 44;
    const buffer = new ArrayBuffer(headerSize + dataSize);
    const view = new DataView(buffer);

    // WAV header
    const writeString = (offset, str) => {
      for (let i = 0; i < str.length; i++) {
        view.setUint8(offset + i, str.charCodeAt(i));
      }
    };

    writeString(0, 'RIFF');
    view.setUint32(4, headerSize + dataSize - 8, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true); // Subchunk1Size
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * blockAlign, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bytesPerSample * 8, true);
    writeString(36, 'data');
    view.setUint32(40, dataSize, true);

    // Convert float32 samples to int16
    const offset = headerSize;
    for (let i = 0; i < float32Array.length; i++) {
      let s = Math.max(-1, Math.min(1, float32Array[i]));
      s = s < 0 ? s * 0x8000 : s * 0x7FFF;
      view.setInt16(offset + i * 2, s, true);
    }

    return new Blob([buffer], { type: 'audio/wav' });
  }, []);

  // ── Handle Speech End from VAD ──
  const handleSpeechEnd = useCallback((audioFloat32) => {
    setIsUserTalking(false);

    // Don't process if already processing or playing
    if (isProcessingRef.current) {
      console.log('[VAD] Already processing, ignoring this utterance');
      return;
    }
    if (isPlayingRef.current) {
      console.log('[VAD] Still playing audio, ignoring this utterance');
      return;
    }
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.log('[VAD] WebSocket not open, ignoring');
      return;
    }

    // Check minimum speech length (~0.5 seconds at 16kHz)
    if (audioFloat32.length < 8000) {
      console.log(`[VAD] Speech too short (${(audioFloat32.length / 16000).toFixed(2)}s), ignoring`);
      return;
    }

    const durationSecs = (audioFloat32.length / 16000).toFixed(1);
    console.log(`[VAD] ━━━ Speech captured: ${durationSecs}s (${audioFloat32.length} samples) ━━━`);

    // Pause VAD while processing
    if (vadRef.current) {
      vadRef.current.pause();
    }

    isProcessingRef.current = true;
    setIsProcessing(true);
    setStatus('processing');
    setStatusMessage('Processing your speech...');

    // Convert float32 PCM to WAV blob
    const wavBlob = float32ToWavBlob(audioFloat32, 16000);

    // Read as base64, but use readAsArrayBuffer for reliability
    const reader = new FileReader();
    reader.onloadend = () => {
      if (!reader.result) {
        console.error('[VAD] FileReader returned null');
        isProcessingRef.current = false;
        setIsProcessing(false);
        resumeVAD();
        return;
      }

      // Convert ArrayBuffer to base64
      const uint8 = new Uint8Array(reader.result);
      let binaryStr = '';
      // Process in chunks to avoid call stack overflow for large arrays
      const chunkSize = 8192;
      for (let i = 0; i < uint8.length; i += chunkSize) {
        const slice = uint8.subarray(i, Math.min(i + chunkSize, uint8.length));
        binaryStr += String.fromCharCode.apply(null, slice);
      }
      const base64 = btoa(binaryStr);

      if (base64 && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        console.log(`[VAD] Sending audio: ${(base64.length * 0.75 / 1024).toFixed(0)}KB WAV`);
        wsRef.current.send(JSON.stringify({
          type: 'audio_complete',
          data: base64,
        }));
      } else {
        console.error('[VAD] Cannot send: WS closed or empty data');
        isProcessingRef.current = false;
        setIsProcessing(false);
        resumeVAD();
      }
    };
    reader.onerror = (err) => {
      console.error('[VAD] FileReader error:', err);
      isProcessingRef.current = false;
      setIsProcessing(false);
      resumeVAD();
    };
    // Use readAsArrayBuffer instead of readAsDataURL for reliability
    reader.readAsArrayBuffer(wavBlob);
  }, [float32ToWavBlob, resumeVAD]);

  // ── Load VAD bundle via script tag (avoids CJS/ESM issues with Vite) ──
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
    const MicVAD = await loadVADBundle();

    const vad = await MicVAD.new({
      model: "legacy",
      // Point to files served from /public (served at root in both dev and prod)
      baseAssetPath: "/",
      onnxWASMBasePath: "/",
      // Silero VAD thresholds — tuned for natural conversation
      positiveSpeechThreshold: 0.80,  // High confidence to start speech (filters noise)
      negativeSpeechThreshold: 0.35,  // Lower threshold to end speech
      redemptionMs: 1200,             // 1.2s of silence before ending utterance (faster, more natural)
      minSpeechMs: 400,               // Minimum 0.4s of speech to count
      preSpeechPadMs: 300,            // Capture 0.3s before speech starts
      submitUserSpeechOnPause: true,  // Submit audio even if VAD is paused mid-speech

      onSpeechStart: () => {
        console.log('[VAD] 🎤 Speech started');
        setIsUserTalking(true);
        setIsListening(true);
        setStatus('listening');
        setStatusMessage('Listening...');
        setError(null);
      },

      onSpeechEnd: (audio) => {
        console.log('[VAD] 🔇 Speech ended');
        handleSpeechEnd(audio);
      },

      onVADMisfire: () => {
        // Speech was too short — VAD discarded it
        console.log('[VAD] Misfire (too short, ignored)');
        setIsUserTalking(false);
      },
    });

    vadRef.current = vad;
    vad.start();

    setIsListening(true);
    setStatus('listening');
    console.log('[VAD] ✓ Silero VAD initialized and listening');
  }, [handleSpeechEnd, loadVADBundle]);

  const stopVAD = useCallback(async () => {
    if (vadRef.current) {
      try {
        await vadRef.current.pause();
        await vadRef.current.destroy();
      } catch (e) {
        // Ignore cleanup errors
      }
      vadRef.current = null;
    }
    setIsListening(false);
    setIsUserTalking(false);
  }, []);

  // ── WebSocket Connection ──
  const connect = useCallback(async () => {
    if (wsRef.current) return;

    setError(null);

    // Pre-initialize AudioContext on user gesture (required by browsers)
    getAudioContext();

    const ws = new WebSocket(`${WS_BASE}/voice/conversation`);
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
            currentTranscriptionRef.current = msg.text || '';
            setCurrentTranscription(msg.text || '');
            setStatusMessage('Got it! Thinking...');
            break;

          case 'answer':
            currentAnswerRef.current = msg.text || '';
            setCurrentAnswer(msg.text || '');
            if (msg.conversation_id) {
              setConversationId(msg.conversation_id);
            }
            break;

          case 'audio_chunk':
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
            // Resume VAD so user can try again
            resumeVAD();
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

    // Start Silero VAD
    await startVAD();
  }, [startVAD, stopVAD, enqueueAudio, getAudioContext, resumeVAD]);

  const disconnect = useCallback(() => {
    isConnectedRef.current = false;

    // Send end session
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'end_session' }));
      wsRef.current.close();
    }
    wsRef.current = null;

    stopVAD();

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
  }, [stopVAD]);

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
