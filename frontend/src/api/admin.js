/**
 * Admin API client.
 * Uses a separate localStorage key so admin sessions are isolated
 * from regular client sessions.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'voicerag_admin_token';

// ─── Token Management ──────────────────────────────────────────────────────

let _adminToken = localStorage.getItem(TOKEN_KEY) || null;

export function setAdminToken(token) {
  _adminToken = token;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function getAdminToken() { return _adminToken; }
export function isAdminAuthenticated() { return !!_adminToken; }

export function adminLogout() {
  setAdminToken(null);
  localStorage.removeItem('voicerag_admin_info');
}

export function getSavedAdmin() {
  try { return JSON.parse(localStorage.getItem('voicerag_admin_info')); }
  catch { return null; }
}

// ─── Core Request ──────────────────────────────────────────────────────────

async function adminRequest(path, options = {}) {
  const headers = { ...options.headers };
  if (_adminToken) headers['Authorization'] = `Bearer ${_adminToken}`;
  if (options.body && !(options.body instanceof FormData))
    headers['Content-Type'] = 'application/json';

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 || res.status === 403) {
    setAdminToken(null);
    window.dispatchEvent(new CustomEvent('admin:unauthorized'));
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res;
}

// ─── Auth ──────────────────────────────────────────────────────────────────

export async function adminLogin(email, password) {
  const res = await adminRequest('/admin/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  setAdminToken(data.access_token);
  localStorage.setItem('voicerag_admin_info', JSON.stringify(data.admin));
  return data;
}

// ─── Stats & Analytics ─────────────────────────────────────────────────────

export async function adminGetStats() {
  const res = await adminRequest('/admin/stats');
  return res.json();
}

export async function adminGetAnalytics() {
  const res = await adminRequest('/admin/analytics');
  return res.json();
}

// ─── Users ─────────────────────────────────────────────────────────────────

export async function adminListUsers({ search = '', status = 'all', page = 1, pageSize = 20, sortBy = 'created_at' } = {}) {
  const p = new URLSearchParams({
    search, status_filter: status, page, page_size: pageSize, sort_by: sortBy,
  });
  const res = await adminRequest(`/admin/users?${p}`);
  return res.json();
}

export async function adminGetUser(id) {
  const res = await adminRequest(`/admin/users/${id}`);
  return res.json();
}

export async function adminCreateUser(data) {
  const res = await adminRequest('/admin/users', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function adminSetUserStatus(id, isActive) {
  const res = await adminRequest(`/admin/users/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ is_active: isActive }),
  });
  return res.json();
}

export async function adminVerifyUser(id) {
  const res = await adminRequest(`/admin/users/${id}/verify`, { method: 'PATCH' });
  return res.json();
}

export async function adminToggleAdmin(id) {
  const res = await adminRequest(`/admin/users/${id}/make-admin`, { method: 'PATCH' });
  return res.json();
}

export async function adminDeleteUser(id) {
  const res = await adminRequest(`/admin/users/${id}`, { method: 'DELETE' });
  return res.json();
}

export async function adminRevokeUserSessions(id) {
  const res = await adminRequest(`/admin/users/${id}/revoke-sessions`, { method: 'POST' });
  return res.json();
}

// ─── API Keys ──────────────────────────────────────────────────────────────

export async function adminListUserKeys(userId) {
  const res = await adminRequest(`/admin/users/${userId}/api-keys`);
  return res.json();
}

export async function adminRevokeUserKey(userId, keyId) {
  const res = await adminRequest(`/admin/users/${userId}/api-keys/${keyId}`, { method: 'DELETE' });
  return res.json();
}

export async function adminListAllKeys({ search = '', activeOnly = false, page = 1, pageSize = 30 } = {}) {
  const p = new URLSearchParams({ search, active_only: activeOnly, page, page_size: pageSize });
  const res = await adminRequest(`/admin/api-keys?${p}`);
  return res.json();
}
