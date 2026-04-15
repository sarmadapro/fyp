import { useState } from 'react';
import { Mic, Square, Loader2, Volume2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import { voiceChat } from '../api/client';

export default function VoicePage() {
  const {
    isRecording,
    audioBlob,
    duration,
    startRecording,
    stopRecording,
    clearRecording,
  } = useAudioRecorder();

  const [processing, setProcessing] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [exchanges, setExchanges] = useState([]);
  const [playingAudio, setPlayingAudio] = useState(false);

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const handleOrbClick = async () => {
    if (processing) return;

    if (isRecording) {
      // Stop recording and process
      stopRecording();
    } else if (audioBlob) {
      // Process the recorded audio
      await processAudio();
    } else {
      // Start recording
      try {
        await startRecording();
      } catch (err) {
        toast.error(err.message);
      }
    }
  };

  // Process audio when blob is available after recording stops
  const processAudio = async () => {
    if (!audioBlob) return;

    setProcessing(true);
    try {
      const result = await voiceChat(audioBlob, conversationId);
      setConversationId(result.conversation_id);

      // Add exchange to history
      setExchanges((prev) => [
        ...prev,
        {
          userText: result.transcription,
          aiText: result.answer,
          audioBase64: result.audio_base64,
        },
      ]);

      // Play audio response
      if (result.audio_base64) {
        playAudioResponse(result.audio_base64);
      }

      clearRecording();
    } catch (err) {
      toast.error(err.message || 'Voice chat failed');
      clearRecording();
    } finally {
      setProcessing(false);
    }
  };

  // Auto-process when recording stops and blob becomes available
  useState(() => {
    if (audioBlob && !isRecording && !processing) {
      processAudio();
    }
  }, [audioBlob, isRecording]);

  const playAudioResponse = (base64Audio) => {
    try {
      const audioBytes = atob(base64Audio);
      const arrayBuffer = new ArrayBuffer(audioBytes.length);
      const view = new Uint8Array(arrayBuffer);
      for (let i = 0; i < audioBytes.length; i++) {
        view[i] = audioBytes.charCodeAt(i);
      }

      const blob = new Blob([arrayBuffer], { type: 'audio/wav' });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);

      setPlayingAudio(true);
      audio.onended = () => {
        setPlayingAudio(false);
        URL.revokeObjectURL(url);
      };
      audio.onerror = () => {
        setPlayingAudio(false);
        URL.revokeObjectURL(url);
      };
      audio.play();
    } catch (err) {
      console.error('Failed to play audio:', err);
      setPlayingAudio(false);
    }
  };

  const getStatusText = () => {
    if (processing) return { title: 'Processing...', subtitle: 'Transcribing, thinking, and speaking' };
    if (isRecording) return { title: 'Listening...', subtitle: 'Tap to stop recording' };
    if (playingAudio) return { title: 'Speaking...', subtitle: 'AI is responding' };
    return { title: 'Tap to Speak', subtitle: 'Ask your document a question' };
  };

  const getOrbClass = () => {
    if (processing) return 'voice-orb processing';
    if (isRecording) return 'voice-orb recording';
    return 'voice-orb';
  };

  const status = getStatusText();

  return (
    <div className="chat-container">
      <div className="voice-container">
        {/* Orb */}
        <div className="voice-orb-container">
          <button
            className={getOrbClass()}
            onClick={handleOrbClick}
            disabled={processing}
          >
            {processing ? (
              <Loader2 className="spinning" />
            ) : isRecording ? (
              <Square />
            ) : playingAudio ? (
              <Volume2 />
            ) : (
              <Mic />
            )}
          </button>
          {isRecording && (
            <>
              <div className="voice-pulse-ring" />
              <div className="voice-pulse-ring" />
              <div className="voice-pulse-ring" />
            </>
          )}
        </div>

        {/* Timer */}
        {isRecording && (
          <div className="voice-timer">{formatTime(duration)}</div>
        )}

        {/* Status */}
        <div className="voice-status">
          <h3>{status.title}</h3>
          <p>{status.subtitle}</p>
        </div>

        {/* Transcript History */}
        {exchanges.length > 0 && (
          <div className="voice-transcript">
            {exchanges.map((exchange, i) => (
              <div key={i}>
                {exchange.userText && (
                  <div className="voice-transcript-item">
                    <div className="label">You said</div>
                    <div className="text">{exchange.userText}</div>
                  </div>
                )}
                <div className="voice-transcript-item">
                  <div className="label">AI Response</div>
                  <div className="text">{exchange.aiText}</div>
                  {exchange.audioBase64 && (
                    <button
                      className="btn btn-secondary"
                      style={{ marginTop: '0.5rem', fontSize: '0.75rem' }}
                      onClick={() => playAudioResponse(exchange.audioBase64)}
                      disabled={playingAudio}
                    >
                      <Volume2 size={12} />
                      Replay
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
