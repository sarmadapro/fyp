import { useState, useEffect, useCallback } from 'react';
import {
  Upload, MessageCircle, Mic, FileText, BarChart3, Key,
  LogOut, LayoutDashboard
} from 'lucide-react';
import { Toaster } from 'react-hot-toast';

// Public Pages
import LandingPage from './pages/LandingPage';
import PipelinePage from './pages/PipelinePage';
import AuthPage from './pages/AuthPage';

// Portal Pages
import UploadPage from './pages/UploadPage';
import ChatPage from './pages/ChatPage';
import VoicePage from './pages/VoicePage';
import AnalyticsPage from './pages/AnalyticsPage';
import APIKeysPage from './pages/APIKeysPage';

import {
  isAuthenticated, logout, getSavedClient,
  portalDocumentStatus,
} from './api/client';

const PORTAL_PAGES = {
  upload: { label: 'Documents', icon: Upload, component: UploadPage },
  chat: { label: 'Chat', icon: MessageCircle, component: ChatPage },
  voice: { label: 'Voice', icon: Mic, component: VoicePage },
  apikeys: { label: 'API Keys', icon: Key, component: APIKeysPage },
  analytics: { label: 'Analytics', icon: BarChart3, component: AnalyticsPage },
};

export default function App() {
  const [currentView, setCurrentView] = useState(
    isAuthenticated() ? 'portal' : 'landing'
  );
  const [activePortalPage, setActivePortalPage] = useState('upload');
  const [docStatus, setDocStatus] = useState(null);
  const [client, setClient] = useState(getSavedClient());

  // Listen for 401 events
  useEffect(() => {
    const handler = () => {
      setCurrentView('auth');
      setClient(null);
    };
    window.addEventListener('voicerag:unauthorized', handler);
    return () => window.removeEventListener('voicerag:unauthorized', handler);
  }, []);

  // Fetch doc status for portal
  const fetchDocStatus = useCallback(async () => {
    if (currentView !== 'portal') return;
    try {
      const status = await portalDocumentStatus();
      setDocStatus(status);
    } catch {
      // Not critical
    }
  }, [currentView]);

  useEffect(() => {
    fetchDocStatus();
    const interval = setInterval(fetchDocStatus, 15000);
    return () => clearInterval(interval);
  }, [fetchDocStatus]);

  useEffect(() => { fetchDocStatus(); }, [activePortalPage]);

  const handleNavigate = (view) => {
    setCurrentView(view);
  };

  const handleAuthSuccess = () => {
    setClient(getSavedClient());
    setCurrentView('portal');
    fetchDocStatus();
  };

  const handleLogout = () => {
    logout();
    setClient(null);
    setDocStatus(null);
    setCurrentView('landing');
  };

  // ─── Public Views ─────────────────────────────────────────────────

  if (currentView === 'landing') {
    return (
      <>
        <Toaster position="top-right" toastOptions={{ style: toastStyle }} />
        <LandingPage onNavigate={handleNavigate} />
      </>
    );
  }

  if (currentView === 'pipeline') {
    return (
      <>
        <Toaster position="top-right" toastOptions={{ style: toastStyle }} />
        <PipelinePage onNavigate={handleNavigate} />
      </>
    );
  }

  if (currentView === 'auth') {
    return (
      <>
        <Toaster position="top-right" toastOptions={{ style: toastStyle }} />
        <AuthPage onNavigate={handleNavigate} onAuthSuccess={handleAuthSuccess} />
      </>
    );
  }

  // ─── Portal (Authenticated) ───────────────────────────────────────

  const ActiveComponent = PORTAL_PAGES[activePortalPage].component;

  return (
    <>
      <Toaster position="top-right" toastOptions={{ style: toastStyle }} />

      <div className="app-layout">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-brand" title="VoiceRAG">
            <div className="sidebar-brand-icon">
              <Mic size={18} />
            </div>
          </div>

          <nav className="sidebar-nav">
            {Object.entries(PORTAL_PAGES).map(([key, page]) => {
              const Icon = page.icon;
              return (
                <button
                  key={key}
                  className={`nav-item ${activePortalPage === key ? 'active' : ''}`}
                  onClick={() => setActivePortalPage(key)}
                  title={page.label}
                >
                  <Icon />
                </button>
              );
            })}
          </nav>

          {/* Client Info */}
          {client && (
            <div className="sidebar-client" title={client.email} style={{ marginTop: 'auto', marginBottom: '1rem', display: 'flex', justifyContent: 'center' }}>
              <div className="client-avatar" style={{ margin: 0 }}>
                {(client.company_name || client.email || '?')[0].toUpperCase()}
              </div>
            </div>
          )}

          {/* Document Status Collapsed */}
          <div className="doc-status-icon" title={docStatus?.has_document ? `Ready: ${docStatus.document_name}` : "No document"} style={{ display: 'flex', justifyContent: 'center', marginBottom: '1rem', color: docStatus?.has_document ? 'var(--accent-primary)' : 'var(--text-tertiary)' }}>
             <FileText size={20} />
          </div>

          {/* Logout */}
          <button className="sidebar-logout" onClick={handleLogout} title="Sign Out" style={{ display: 'flex', justifyContent: 'center', padding: '0.75rem', width: '44px', borderRadius: '50%', background: 'transparent' }}>
            <LogOut size={16} />
          </button>
        </aside>

        {/* Main Content */}
        <main className="main-content">
          <ActiveComponent />
        </main>
      </div>
    </>
  );
}

const toastStyle = {
  background: 'var(--bg-tertiary)',
  color: 'var(--text-primary)',
  border: '1px solid var(--border-subtle)',
  fontFamily: 'var(--font-family)',
  fontSize: 'var(--font-size-sm)',
};
