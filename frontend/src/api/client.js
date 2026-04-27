/**
 * API Client for VoiceRAG SaaS Platform.
 * 
 * Handles:
 * - Authentication (register, login, profile)
 * - Portal document management
 * - API key management
 * - Analytics
 * - Chat & Voice (legacy single-user + portal multi-tenant)
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ─── Auth Token Management ─────────────────────────────────────────

let _token = localStorage.getItem('voicerag_token') || null;

export function setToken(token) {
  _token = token;
  if (token) {
    localStorage.setItem('voicerag_token', token);
  } else {
    localStorage.removeItem('voicerag_token');
  }
}

export function getToken() {
  return _token;
}

export function isAuthenticated() {
  return !!_token;
}

export function logout() {
  setToken(null);
  localStorage.removeItem('voicerag_client');
}

// ─── Core Request Helpers ──────────────────────────────────────────

let _isRefreshing = false;
let _refreshPromise = null;

async function _tryRefreshToken() {
  // Only one refresh at a time
  if (_isRefreshing) return _refreshPromise;

  _isRefreshing = true;
  _refreshPromise = fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    credentials: 'include', // sends the HTTP-only refresh cookie
  })
    .then(async (res) => {
      if (!res.ok) throw new Error('Refresh failed');
      const data = await res.json();
      setToken(data.access_token);
      if (data.client) {
        localStorage.setItem('voicerag_client', JSON.stringify(data.client));
      }
      return data.access_token;
    })
    .finally(() => {
      _isRefreshing = false;
      _refreshPromise = null;
    });

  return _refreshPromise;
}

async function request(path, options = {}, _isRetry = false) {
  const url = `${API_BASE}${path}`;
  const headers = {
    ...options.headers,
  };

  // Add auth header if we have a token
  if (_token) {
    headers['Authorization'] = `Bearer ${_token}`;
  }

  // Add JSON content type for non-FormData bodies
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(url, {
    ...options,
    credentials: 'include', // needed so refresh cookie is sent
    headers,
  });

  // If 401 and we haven't retried yet — try to silently refresh the token
  if (response.status === 401 && !_isRetry) {
    try {
      await _tryRefreshToken();
      // Retry the original request once with the new token
      return request(path, options, true);
    } catch {
      // Refresh also failed — user must log in again
      setToken(null);
      localStorage.removeItem('voicerag_client');
      window.dispatchEvent(new CustomEvent('voicerag:unauthorized'));
      const error = await response.json().catch(() => ({ detail: 'Session expired. Please log in again.' }));
      throw new Error(error.detail || 'Session expired');
    }
  }

  if (response.status === 401) {
    // Already retried — clear auth state
    setToken(null);
    localStorage.removeItem('voicerag_client');
    window.dispatchEvent(new CustomEvent('voicerag:unauthorized'));
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response;
}

// ─── Authentication ────────────────────────────────────────────────

export async function register(email, password, companyName, fullName = '') {
  const res = await request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      email,
      password,
      company_name: companyName,
      full_name: fullName,
    }),
  });
  const data = await res.json();
  setToken(data.access_token);
  localStorage.setItem('voicerag_client', JSON.stringify(data.client));
  return data;
}

export async function login(email, password) {
  const res = await request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  setToken(data.access_token);
  localStorage.setItem('voicerag_client', JSON.stringify(data.client));
  return data;
}

export async function getProfile() {
  const res = await request('/auth/me');
  return res.json();
}

export function getSavedClient() {
  try {
    return JSON.parse(localStorage.getItem('voicerag_client'));
  } catch {
    return null;
  }
}

// ─── Portal: Document Management ───────────────────────────────────

export async function portalDocumentStatus() {
  const res = await request('/portal/document/status');
  return res.json();
}

export async function portalUploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await request('/portal/document/upload', {
    method: 'POST',
    body: formData,
  });
  return res.json();
}

export async function portalDeleteDocument() {
  const res = await request('/portal/document/delete', { method: 'DELETE' });
  return res.json();
}

export async function portalChat(question) {
  const res = await request('/portal/chat', {
    method: 'POST',
    body: JSON.stringify({ question }),
  });
  return res.json();
}

// ─── Embed Key ─────────────────────────────────────────────────────

export async function listAPIKeys() {
  const res = await request('/api-keys');
  return res.json();
}

export async function regenerateEmbedKey() {
  const res = await request('/api-keys/regenerate', { method: 'POST' });
  return res.json();
}

export async function revokeAPIKey(keyId) {
  const res = await request(`/api-keys/${keyId}`, { method: 'DELETE' });
  return res.json();
}

// ─── Portal Analytics ──────────────────────────────────────────────

export async function portalAnalyticsSummary() {
  const res = await request('/portal/analytics/summary');
  return res.json();
}

// ─── Legacy: Single-User APIs (backward compat) ────────────────────

export async function getDocumentStatus() {
  const res = await request('/document/status');
  return res.json();
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await request('/document/upload', {
    method: 'POST',
    body: formData,
  });
  return res.json();
}

export async function deleteDocument() {
  const res = await request('/document/delete', { method: 'DELETE' });
  return res.json();
}

export async function chatWithDocument(question, conversationId = null) {
  const res = await request('/chat', {
    method: 'POST',
    body: JSON.stringify({
      question,
      conversation_id: conversationId,
    }),
  });
  return res.json();
}

export function chatStreamURL() {
  return `${API_BASE}/chat/stream`;
}

export async function sendMessageStream(question, conversationId, onChunk) {
  const token = getToken();
  const url = `${API_BASE}/portal/chat/stream`;   // authenticated — always uses client's own index
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ question, conversation_id: conversationId }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Stream failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('data: ')) {
        const json = trimmed.slice(6);
        if (json === '[DONE]') return;
        try {
          const chunk = JSON.parse(json);
          onChunk(chunk);
        } catch {}
      }
    }
  }
}

export async function clearChatHistory(conversationId) {
  const res = await request(`/chat/history/${conversationId}`, { method: 'DELETE' });
  return res.json();
}

export function getWebSocketURL() {
  const wsBase = API_BASE.replace('http', 'ws');
  return `${wsBase}/voice/ws`;
}

// ─── Analytics ──────────────────────────────────────────────────────

export async function getAnalyticsConversations(mode = null, status = null, limit = 100, offset = 0) {
  const params = new URLSearchParams();
  if (mode) params.set('mode', mode);
  if (status) params.set('status', status);
  params.set('limit', limit.toString());
  params.set('offset', offset.toString());
  const res = await request(`/analytics/conversations?${params.toString()}`);
  return res.json();
}

export async function getAnalyticsSummary() {
  const res = await request('/analytics/summary');
  return res.json();
}

export async function clearAnalytics() {
  const res = await request('/analytics/clear', { method: 'DELETE' });
  return res.json();
}

// ─── Export Base URL (for widget code generation) ─────────────────

export function getAPIBase() {
  return API_BASE;
}
