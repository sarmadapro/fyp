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
 *   2. onSpeechStart → begin recording audio
 *   3. onSpeechEnd → stop recording, send accumulated audio to backend
 *   4. Backend: STT → RAG → TTS (sentence-by-sentence)
 *   5. Frontend plays TTS audio chunks from a queue
 *   6. After playback finishes → VAD resumes listening
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
  // Refs that mirror state (to avoid stale closures in WS/VAD callbacks)
  const currentTranscriptionRef = useRef('');
  const currentAnswerRef = useRef('');

  // ── Audio Playback Queue ──
  const playNextInQueue = useCallback(() => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      setIsSpeaking(false);
      setStatus('listening');
      setStatusMessage('');

      // Resume VAD listening after playback finishes
      if (vadRef.current) {
        try {
          vadRef.current.start();
        } catch (e) {
          // Already started
        }
      }
      return;
    }

    isPlayingRef.current = true;
    const { audioData } = audioQueueRef.current.shift();

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
        playNextInQueue();
      };

      audio.onerror = () => {
        URL.revokeObjectURL(url);
        playNextInQueue();
      };

      audio.play().catch(() => {
        URL.revokeObjectURL(url);
        playNextInQueue();
      });
    } catch (err) {
      console.error('Failed to play audio chunk:', err);
      playNextInQueue();
    }
  }, []);

  const enqueueAudio = useCallback((audioData, index, total) => {
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

    // Don't process if already processing or if too short
    if (isProcessingRef.current) return;
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    // Check minimum speech length (~0.5 seconds at 16kHz)
    if (audioFloat32.length < 8000) {
      console.log('Speech too short, ignoring.');
      return;
    }

    console.log(`Speech detected: ${(audioFloat32.length / 16000).toFixed(1)}s of audio`);

    // Pause VAD while processing
    if (vadRef.current) {
      vadRef.current.pause();
    }

    isProcessingRef.current = true;
    setIsProcessing(true);
    setStatus('processing');
    setStatusMessage('Processing...');

    // Convert float32 PCM to WAV blob
    const wavBlob = float32ToWavBlob(audioFloat32, 16000);

    // Read as base64 and send to backend
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = reader.result.split(',')[1];
      if (base64 && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'audio_chunk',
          data: base64,
        }));
        // Immediately tell backend this is a complete utterance
        wsRef.current.send(JSON.stringify({
          type: 'silence_detected',
        }));
      }
    };
    reader.readAsDataURL(wavBlob);
  }, [float32ToWavBlob]);

  // ── Initialize Silero VAD ──
  const startVAD = useCallback(async () => {
    // Dynamic import to avoid SSR issues
    const { MicVAD } = await import('@ricky0123/vad-web');

    const vad = await MicVAD.new({
      model: "legacy",
      // Silero VAD thresholds
      positiveSpeechThreshold: 0.80,  // High confidence to start speech (filters noise)
      negativeSpeechThreshold: 0.35,  // Lower threshold to end speech
      redemptionMs: 2000,             // 2s of non-speech before ending segment
      minSpeechMs: 500,               // Minimum 0.5s of speech to count
      preSpeechPadMs: 300,            // Capture 0.3s before speech starts
      submitUserSpeechOnPause: true,  // Submit audio even if VAD is paused mid-speech

      onSpeechStart: () => {
        console.log('VAD: Speech started');
        setIsUserTalking(true);
        setIsListening(true);
        setStatus('listening');
        setStatusMessage('Listening...');
      },

      onSpeechEnd: (audio) => {
        console.log('VAD: Speech ended');
        handleSpeechEnd(audio);
      },

      onVADMisfire: () => {
        // Speech was too short — VAD discarded it
        console.log('VAD: Misfire (too short)');
        setIsUserTalking(false);
      },
    });

    vadRef.current = vad;
    vad.start();

    setIsListening(true);
    setStatus('listening');
    console.log('Silero VAD initialized and listening');
  }, [handleSpeechEnd]);

  const stopVAD = useCallback(async () => {
    if (vadRef.current) {
      await vadRef.current.pause();
      await vadRef.current.destroy();
      vadRef.current = null;
    }
    setIsListening(false);
    setIsUserTalking(false);
  }, []);

  // ── WebSocket Connection ──
  const connect = useCallback(async () => {
    if (wsRef.current) return;

    const ws = new WebSocket(`${WS_BASE}/voice/conversation`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        switch (msg.type) {
          case 'listening':
            // Backend is ready for next turn
            isProcessingRef.current = false;
            setIsProcessing(false);
            if (!isPlayingRef.current && audioQueueRef.current.length === 0) {
              // Resume VAD if not playing audio
              if (vadRef.current) {
                try {
                  vadRef.current.start();
                } catch (e) {
                  // Already started
                }
              }
              setStatus('listening');
              setStatusMessage('');
            }
            break;

          case 'status':
            setStatusMessage(msg.message || '');
            break;

          case 'transcription':
            currentTranscriptionRef.current = msg.text || '';
            setCurrentTranscription(msg.text || '');
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
            // AI finished generating audio — finalize the exchange
            setExchanges(prev => [
              ...prev,
              {
                userText: currentTranscriptionRef.current || '',
                aiText: currentAnswerRef.current || '',
              },
            ]);
            currentTranscriptionRef.current = '';
            currentAnswerRef.current = '';
            setCurrentTranscription('');
            setCurrentAnswer('');
            // VAD resume will happen when audio queue empties in playNextInQueue
            break;

          case 'error':
            console.error('Voice error:', msg.message);
            setStatusMessage(msg.message || 'Something went wrong');
            isProcessingRef.current = false;
            setIsProcessing(false);
            // Resume VAD
            if (vadRef.current) {
              try {
                vadRef.current.start();
              } catch (e) {
                // Already started
              }
            }
            setStatus('listening');
            break;

          case 'done':
            break;
        }
      } catch (err) {
        console.error('Failed to parse WS message:', err);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      setStatus('idle');
      wsRef.current = null;
      stopVAD();
      console.log('Voice WebSocket closed');
    };

    ws.onerror = (err) => {
      console.error('Voice WebSocket error:', err);
    };

    // Wait for connection
    await new Promise((resolve, reject) => {
      ws.addEventListener('open', resolve, { once: true });
      ws.addEventListener('error', reject, { once: true });
    });

    setIsConnected(true);
    console.log('Voice WebSocket connected');

    // Start Silero VAD
    await startVAD();
  }, [startVAD, stopVAD, enqueueAudio]);

  const disconnect = useCallback(() => {
    // Send end session
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'end_session' }));
      wsRef.current.close();
    }
    wsRef.current = null;

    stopVAD();

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
