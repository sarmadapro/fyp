import { useState, useRef, useEffect } from 'react';
import { Send, MessageCircle, FileText, Image, Globe, Mic, Sparkles, X } from 'lucide-react';
import { sendMessageStream } from '../api/client';

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [streamingMessage, setStreamingMessage] = useState('');
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessage]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || loading) return;

    // Add user message
    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    setInput('');
    setLoading(true);
    setStreamingMessage('');

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    try {
      let fullAnswer = '';
      let sources = [];
      let newConversationId = conversationId;

      await sendMessageStream(
        question,
        conversationId,
        (chunk) => {
          // Handle different chunk types
          if (chunk.type === 'token') {
            fullAnswer += chunk.content;
            setStreamingMessage(fullAnswer);
          } else if (chunk.type === 'context') {
            // Could show "Found X relevant chunks" status
            console.log(`Found ${chunk.chunks} relevant chunks`);
          } else if (chunk.type === 'done') {
            newConversationId = chunk.conversation_id;
            sources = chunk.sources || [];
          } else if (chunk.type === 'error') {
            fullAnswer = chunk.message;
            setStreamingMessage(fullAnswer);
          }
        }
      );

      // Add complete message
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: fullAnswer, sources },
      ]);
      setConversationId(newConversationId);
      setStreamingMessage('');
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${err.message}. Please check that the backend is running and a document is uploaded.`,
        },
      ]);
      setStreamingMessage('');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTextareaInput = (e) => {
    setInput(e.target.value);
    // Auto-resize
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
  };

  return (
    <div className="chat-container">
      {/* Premium Header */}
      <div className="chat-header">
        <div className="chat-header-left"><Sparkles size={18} /></div>
        <h2>New Chat</h2>
        <div className="chat-header-right"><X size={18} /></div>
      </div>
      
      {/* Messages Area */}
      <div className="chat-messages">
        {messages.length === 0 && !streamingMessage ? (
          <div className="chat-empty">
            <MessageCircle />
            <h3>Start a Conversation</h3>
            <p>
              Ask questions about your uploaded document. The AI will answer
              based on the document content.
            </p>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                <div className="message-avatar">
                  {msg.role === 'assistant' ? <img src="https://api.dicebear.com/7.x/bottts/svg?seed=AI" alt="AI" /> : <img src="https://api.dicebear.com/7.x/notionists/svg?seed=User" alt="You" />}
                </div>
                <div className="message-content">
                  {msg.content}
                </div>
              </div>
            ))}

            {/* Streaming message */}
            {streamingMessage && (
              <div className="message assistant">
                <div className="message-avatar">AI</div>
                <div className="message-content">
                  {streamingMessage}
                  <span className="streaming-cursor">▊</span>
                </div>
              </div>
            )}

            {/* Loading indicator (before streaming starts) */}
            {loading && !streamingMessage && (
              <div className="message assistant">
                <div className="message-avatar">AI</div>
                <div className="message-content" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <div className="spinner" />
                  <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                    Thinking...
                  </span>
                </div>
              </div>
            )}
          </>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="chat-input-container">
        <div className="chat-action-chips">
          <button className="action-chip"><FileText size={14}/> Chat Files</button>
          <button className="action-chip"><Image size={14}/> Images</button>
          <button className="action-chip"><Globe size={14}/> Translate</button>
          <button className="action-chip"><Mic size={14}/> Audio Chat</button>
        </div>
        <div className="chat-input-wrapper">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={handleTextareaInput}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your document..."
            disabled={loading}
          />
          <button
            className="btn btn-primary btn-icon"
            onClick={handleSend}
            disabled={!input.trim() || loading}
            title="Send message"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
