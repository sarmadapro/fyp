/**
 * API client for the Voice RAG backend.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Generic fetch wrapper with error handling.
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }

  return response;
}

// ─── Health ────────────────────────────────────────────────────────
export async function checkHealth() {
  const res = await request('/health');
  return res.json();
}

// ─── Documents ─────────────────────────────────────────────────────
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

// ─── Chat ──────────────────────────────────────────────────────────
export async function sendMessage(question, conversationId = null) {
  const res = await request('/chat', {
    method: 'POST',
    body: JSON.stringify({
      question,
      conversation_id: conversationId,
    }),
  });
  return res.json();
}

export async function clearChatHistory(conversationId) {
  const res = await request(`/chat/history/${conversationId}`, { method: 'DELETE' });
  return res.json();
}

// ─── Voice ─────────────────────────────────────────────────────────
export async function voiceChat(audioBlob, conversationId = null) {
  const formData = new FormData();
  formData.append('file', audioBlob, 'recording.webm');
  
  const url = `${API_BASE}/voice/chat${conversationId ? `?conversation_id=${conversationId}` : ''}`;
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Voice chat failed: ${response.status}`);
  }

  return response.json();
}
