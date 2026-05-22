import { useState, useEffect } from 'react';
import { User, Lock, CheckCircle, AlertCircle, Mail, Calendar, Key } from 'lucide-react';
import toast from 'react-hot-toast';
import { getProfile, updateProfile, changePassword } from '../api/client';

export default function SettingsPage() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  const [fullName, setFullName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);

  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [changingPw, setChangingPw] = useState(false);

  useEffect(() => {
    getProfile()
      .then((data) => {
        setProfile(data);
        setFullName(data.full_name || '');
        setCompanyName(data.company_name || '');
      })
      .catch(() => toast.error('Failed to load profile'))
      .finally(() => setLoading(false));
  }, []);

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    if (!companyName.trim()) return toast.error('Company name is required');
    setSavingProfile(true);
    try {
      const updated = await updateProfile(fullName.trim(), companyName.trim());
      setProfile((prev) => ({ ...prev, ...updated }));
      const saved = JSON.parse(localStorage.getItem('voicerag_client') || '{}');
      localStorage.setItem(
        'voicerag_client',
        JSON.stringify({ ...saved, full_name: updated.full_name, company_name: updated.company_name }),
      );
      toast.success('Profile updated');
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSavingProfile(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (newPw !== confirmPw) return toast.error('New passwords do not match');
    if (newPw.length < 8) return toast.error('Password must be at least 8 characters');
    setChangingPw(true);
    try {
      await changePassword(currentPw, newPw);
      toast.success('Password changed successfully');
      setCurrentPw('');
      setNewPw('');
      setConfirmPw('');
    } catch (err) {
      toast.error(err.message);
    } finally {
      setChangingPw(false);
    }
  };

  const avatarLetter = profile
    ? (profile.company_name || profile.email || '?')[0].toUpperCase()
    : '?';

  const memberSince = profile?.created_at
    ? new Date(profile.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long' })
    : '—';

  return (
    <>
      <div className="page-header">
        <h2>Settings</h2>
        <p>Manage your profile and account security</p>
      </div>

      <div className="page-body">
        {loading ? (
          <div className="settings-loading">
            <div className="spinner spinner-lg" />
          </div>
        ) : (
          <div className="settings-grid">

            {/* ── Profile Card ── */}
            <div className="settings-card">
              <div className="settings-card-header">
                <div className="settings-card-icon">
                  <User size={18} />
                </div>
                <div>
                  <h3>Profile</h3>
                  <p>Your public display information</p>
                </div>
              </div>

              <div className="settings-avatar-row">
                <div className="settings-avatar">{avatarLetter}</div>
                <div>
                  <div className="settings-avatar-name">
                    {profile?.full_name || profile?.company_name || 'Unnamed'}
                  </div>
                  <div className="settings-avatar-email">{profile?.email}</div>
                </div>
              </div>

              <form onSubmit={handleSaveProfile} className="settings-form">
                <div className="form-group">
                  <label>Full Name</label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Your name"
                  />
                </div>
                <div className="form-group">
                  <label>Company / Organisation</label>
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="Your company"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Email</label>
                  <div className="settings-email-row">
                    <input type="email" value={profile?.email || ''} readOnly className="input-readonly" />
                    {profile?.is_email_verified ? (
                      <span className="settings-badge verified">
                        <CheckCircle size={12} /> Verified
                      </span>
                    ) : (
                      <span className="settings-badge unverified">
                        <AlertCircle size={12} /> Unverified
                      </span>
                    )}
                  </div>
                </div>
                <button type="submit" className="btn btn-primary" disabled={savingProfile}>
                  {savingProfile ? <><div className="spinner" /> Saving…</> : 'Save Changes'}
                </button>
              </form>
            </div>

            {/* ── Security Card ── */}
            <div className="settings-card">
              <div className="settings-card-header">
                <div className="settings-card-icon">
                  <Lock size={18} />
                </div>
                <div>
                  <h3>Security</h3>
                  <p>Update your password</p>
                </div>
              </div>

              <form onSubmit={handleChangePassword} className="settings-form">
                <div className="form-group">
                  <label>Current Password</label>
                  <input
                    type="password"
                    value={currentPw}
                    onChange={(e) => setCurrentPw(e.target.value)}
                    placeholder="••••••••"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>New Password</label>
                  <input
                    type="password"
                    value={newPw}
                    onChange={(e) => setNewPw(e.target.value)}
                    placeholder="Min. 8 characters"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Confirm New Password</label>
                  <input
                    type="password"
                    value={confirmPw}
                    onChange={(e) => setConfirmPw(e.target.value)}
                    placeholder="Repeat new password"
                    required
                  />
                </div>
                <button type="submit" className="btn btn-primary" disabled={changingPw}>
                  {changingPw ? <><div className="spinner" /> Changing…</> : 'Change Password'}
                </button>
              </form>
            </div>

            {/* ── Account Info Card ── */}
            <div className="settings-card settings-card-info">
              <div className="settings-card-header">
                <div className="settings-card-icon">
                  <Key size={18} />
                </div>
                <div>
                  <h3>Account Info</h3>
                  <p>Read-only account details</p>
                </div>
              </div>

              <div className="settings-info-list">
                <div className="settings-info-row">
                  <Mail size={14} />
                  <span className="settings-info-label">Email</span>
                  <span className="settings-info-value">{profile?.email}</span>
                </div>
                <div className="settings-info-row">
                  <Calendar size={14} />
                  <span className="settings-info-label">Member since</span>
                  <span className="settings-info-value">{memberSince}</span>
                </div>
                <div className="settings-info-row">
                  <Key size={14} />
                  <span className="settings-info-label">API Keys</span>
                  <span className="settings-info-value">{profile?.api_key_count ?? '—'} active</span>
                </div>
                <div className="settings-info-row">
                  <CheckCircle size={14} />
                  <span className="settings-info-label">Documents</span>
                  <span className="settings-info-value">
                    {profile?.has_documents ? 'Document loaded' : 'No document'}
                  </span>
                </div>
              </div>
            </div>

          </div>
        )}
      </div>
    </>
  );
}
