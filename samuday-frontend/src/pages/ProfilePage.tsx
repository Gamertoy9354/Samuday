import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../api/client';
import { User, Mail, Phone, Globe, Shield } from 'lucide-react';

export const ProfilePage: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(user?.full_name || '');
  const [bio, setBio] = useState('');
  const [saving, setSaving] = useState(false);

  if (!user) {
    return (
      <div className="page-content" style={{ paddingTop: 32 }}>
        <div className="empty-state"><h3>Please login to view your profile</h3></div>
      </div>
    );
  }

  const handleSave = async () => {
    setSaving(true);
    try {
      await authAPI.updateProfile({ full_name: name, profile_bio: bio || undefined });
      await refreshUser();
      setEditing(false);
    } catch { /* ignore */ }
    setSaving(false);
  };

  return (
    <div className="page-content" style={{ paddingTop: 16 }}>
      <div style={{ maxWidth: 700, margin: '0 auto' }}>
        <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', overflow: 'hidden' }}>
          {/* Header */}
          <div style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-dark))', padding: '32px 24px', color: 'white', display: 'flex', alignItems: 'center', gap: 20 }}>
            {user.avatar_url ? (
              <img src={user.avatar_url} alt="" style={{ width: 80, height: 80, borderRadius: '50%', border: '3px solid rgba(255,255,255,0.3)' }} />
            ) : (
              <div style={{ width: 80, height: 80, borderRadius: '50%', background: 'rgba(255,255,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <User size={36} />
              </div>
            )}
            <div>
              <h2 style={{ fontSize: '1.3rem', fontWeight: 700 }}>{user.full_name}</h2>
              <p style={{ opacity: 0.8, fontSize: '0.9rem' }}>{user.email || user.phone_number || 'No contact info'}</p>
              {user.is_seller && <span style={{ background: 'var(--accent)', color: 'var(--text-primary)', padding: '2px 10px', borderRadius: 12, fontSize: '0.75rem', fontWeight: 600, marginTop: 4, display: 'inline-block' }}>Seller</span>}
            </div>
          </div>

          {/* Details */}
          <div style={{ padding: 24 }}>
            {!editing ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}><Mail size={18} color="var(--text-muted)" /> <span>{user.email || 'No email'}</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}><Phone size={18} color="var(--text-muted)" /> <span>{user.phone_number || 'No phone'}</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}><Globe size={18} color="var(--text-muted)" /> <span>Language: {user.preferred_language.toUpperCase()}</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}><Shield size={18} color="var(--text-muted)" /> <span>Status: {user.status}</span></div>
                <button className="btn btn-outline" onClick={() => { setEditing(true); setName(user.full_name); }}>
                  Edit Profile
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div className="form-group"><label>Full Name</label><input value={name} onChange={e => setName(e.target.value)} /></div>
                <div className="form-group"><label>Bio</label><textarea value={bio} onChange={e => setBio(e.target.value)} rows={3} placeholder="Tell us about yourself..." /></div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-primary" onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
                  <button className="btn btn-outline" onClick={() => setEditing(false)}>Cancel</button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
