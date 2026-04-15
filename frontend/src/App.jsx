import { useState, useEffect } from 'react';
import { Upload, MessageCircle, Mic, FileText } from 'lucide-react';
import { Toaster } from 'react-hot-toast';
import UploadPage from './pages/UploadPage';
import ChatPage from './pages/ChatPage';
import VoicePage from './pages/VoicePage';
import { getDocumentStatus } from './api/client';

const PAGES = {
  upload: { label: 'Upload', icon: Upload, component: UploadPage },
  chat: { label: 'Chat', icon: MessageCircle, component: ChatPage },
  voice: { label: 'Voice', icon: Mic, component: VoicePage },
};

export default function App() {
  const [activePage, setActivePage] = useState('upload');
  const [docStatus, setDocStatus] = useState(null);

  const fetchDocStatus = async () => {
    try {
      const status = await getDocumentStatus();
      setDocStatus(status);
    } catch {
      // Backend not running
    }
  };

  useEffect(() => {
    fetchDocStatus();
    const interval = setInterval(fetchDocStatus, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, []);

  // Refresh doc status when switching pages
  useEffect(() => {
    fetchDocStatus();
  }, [activePage]);

  const ActiveComponent = PAGES[activePage].component;

  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'var(--bg-tertiary)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-subtle)',
            fontFamily: 'var(--font-family)',
            fontSize: 'var(--font-size-sm)',
          },
        }}
      />

      <div className="app-layout">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-brand">
            <div className="sidebar-brand-icon">
              <Mic size={18} />
            </div>
            <h1>VoiceRAG</h1>
          </div>

          <nav className="sidebar-nav">
            {Object.entries(PAGES).map(([key, page]) => {
              const Icon = page.icon;
              return (
                <button
                  key={key}
                  className={`nav-item ${activePage === key ? 'active' : ''}`}
                  onClick={() => setActivePage(key)}
                >
                  <Icon />
                  {page.label}
                </button>
              );
            })}
          </nav>

          {/* Document Status */}
          <div className="doc-status">
            <div className="doc-status-label">Current Document</div>
            {docStatus?.has_document ? (
              <>
                <div className="doc-status-name">
                  <FileText size={14} style={{ display: 'inline', marginRight: '0.25rem', verticalAlign: 'middle' }} />
                  {docStatus.document_name}
                </div>
                <div className="doc-status-meta">
                  {docStatus.chunk_count} chunks • Ready
                </div>
              </>
            ) : (
              <div className="doc-status-empty">No document uploaded</div>
            )}
          </div>
        </aside>

        {/* Main Content */}
        <main className="main-content">
          <ActiveComponent />
        </main>
      </div>
    </>
  );
}
