import { useState } from 'react';
import { Mic, MicOff, Loader2, Volume2, PhoneOff, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { useVoiceConversation } from '../hooks/useVoiceConversation';

export default function VoicePage() {
  const {
    isConnected,
    isListening,
    isSpeaking,
    isProcessing,
    isUserTalking,
    status,
    statusMessage,
    error,
    exchanges,
    currentTranscription,
    currentAnswer,
    connect,
    disconnect,
  } = useVoiceConversation();

  const handleToggleConversation = async () => {
    if (isConnected) {
      disconnect();
    } else {
      try {
        await connect();
        toast.success('Voice conversation started!');
      } catch (err) {
        toast.error(err.message || 'Failed to start voice conversation');
      }
    }
  };

  const getOrbClass = () => {
    if (isProcessing) return 'voice-orb processing';
    if (isSpeaking) return 'voice-orb speaking';
    if (isUserTalking) return 'voice-orb recording';
    if (isListening) return 'voice-orb listening-idle';
    return 'voice-orb';
  };

  const getStatusInfo = () => {
    if (!isConnected) {
      return { title: 'Start Conversation', subtitle: 'Tap the orb to begin' };
    }
    if (isProcessing) {
      return { title: 'Thinking...', subtitle: statusMessage || 'Processing your question' };
    }
    if (isSpeaking) {
      return { title: 'Speaking...', subtitle: 'AI is responding' };
    }
    if (isUserTalking) {
      return { title: 'Hearing you...', subtitle: 'Keep talking, I\'ll respond when you pause' };
    }
    if (isListening) {
      return { title: 'Ready', subtitle: 'Speak whenever you\'re ready' };
    }
    return { title: 'Connected', subtitle: 'Getting ready...' };
  };

  const statusInfo = getStatusInfo();

  return (
    <div className="chat-container">
      <div className="voice-container">
        {/* Main Orb */}
        <div className="voice-orb-container">
          <button
            className={getOrbClass()}
            onClick={handleToggleConversation}
          >
            {isProcessing ? (
              <Loader2 className="spinning" />
            ) : isSpeaking ? (
              <Volume2 />
            ) : isConnected ? (
              <Mic />
            ) : (
              <Mic />
            )}
          </button>

          {/* Pulse rings only when user is actively speaking (VAD confirmed) */}
          {isUserTalking && (
            <>
              <div className="voice-pulse-ring" />
              <div className="voice-pulse-ring" />
              <div className="voice-pulse-ring" />
            </>
          )}

          {/* Speaking wave animation */}
          {isSpeaking && (
            <>
              <div className="voice-pulse-ring speaking-ring" />
              <div className="voice-pulse-ring speaking-ring" />
            </>
          )}
        </div>

        {/* Status */}
        <div className="voice-status">
          <h3>{statusInfo.title}</h3>
          <p>{statusInfo.subtitle}</p>
        </div>

        {/* Error display */}
        {error && (
          <div className="voice-error">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* End call button when connected */}
        {isConnected && (
          <button
            className="btn btn-danger voice-end-btn"
            onClick={disconnect}
          >
            <PhoneOff size={16} />
            End Conversation
          </button>
        )}

        {/* Live transcription */}
        {(currentTranscription || currentAnswer) && (
          <div className="voice-live">
            {currentTranscription && (
              <div className="voice-live-item user">
                <span className="voice-live-label">You</span>
                <span className="voice-live-text">{currentTranscription}</span>
              </div>
            )}
            {currentAnswer && (
              <div className="voice-live-item ai">
                <span className="voice-live-label">AI</span>
                <span className="voice-live-text">{currentAnswer}</span>
              </div>
            )}
          </div>
        )}

        {/* Conversation History */}
        {exchanges.length > 0 && (
          <div className="voice-transcript">
            {exchanges.map((exchange, i) => (
              <div key={i}>
                {exchange.userText && (
                  <div className="voice-transcript-item user-item">
                    <div className="label">You</div>
                    <div className="text">{exchange.userText}</div>
                  </div>
                )}
                <div className="voice-transcript-item ai-item">
                  <div className="label">AI</div>
                  <div className="text">{exchange.aiText}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
