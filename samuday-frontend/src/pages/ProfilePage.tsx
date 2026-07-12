import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useWallet } from '../context/WalletContext';
import { authAPI } from '../api/client';
import { User, Mail, Phone, Globe, Shield, Wallet, Plus, MapPin, Users, ChevronRight, Copy, Check } from 'lucide-react';
import { AddMoneyModal } from '../components/wallet/AddMoneyModal';
import { AddressPicker } from '../components/checkout/AddressPicker';

export const ProfilePage: React.FC = () => {
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();
  const { balancePaise, refreshBalance } = useWallet();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(user?.full_name || '');
  const [bio, setBio] = useState('');
  const [gender, setGender] = useState('');
  const [dob, setDob] = useState('');
  const [altPhone, setAltPhone] = useState('');
  const [language, setLanguage] = useState('en');
  const [saving, setSaving] = useState(false);
  const [showAddMoney, setShowAddMoney] = useState(false);
  const [avatarError, setAvatarError] = useState(false);
  const [idCopied, setIdCopied] = useState(false);

  const copyAccountId = () => {
    navigator.clipboard.writeText(user!.id).then(() => {
      setIdCopied(true);
      setTimeout(() => setIdCopied(false), 1500);
    });
  };

  useEffect(() => {
    if (user) refreshBalance();
  }, [user]);

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
      await authAPI.updateProfile({
        full_name: name,
        profile_bio: bio || undefined,
        gender: gender || undefined,
        date_of_birth: dob || undefined,
        alternate_phone: altPhone || undefined,
        preferred_language: language,
      });
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
            {user.avatar_url && !avatarError ? (
              <img
                src={user.avatar_url}
                alt=""
                referrerPolicy="no-referrer"
                onError={() => setAvatarError(true)}
                style={{ width: 80, height: 80, borderRadius: '50%', border: '3px solid rgba(255,255,255,0.3)', objectFit: 'cover' }}
              />
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

          {/* Wallet */}
          <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border-light)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <Wallet size={22} color="var(--primary)" />
              <div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Wallet Balance</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>&#8377;{(balancePaise / 100).toLocaleString('en-IN')}</div>
              </div>
            </div>
            <button className="btn btn-primary btn-sm" onClick={() => setShowAddMoney(true)} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Plus size={14} /> Add Money
            </button>
          </div>

          {/* Details */}
          <div style={{ padding: 24 }}>
            {!editing ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}><Mail size={18} color="var(--text-muted)" /> <span>{user.email || 'No email'}</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}><Phone size={18} color="var(--text-muted)" /> <span>{user.phone_number || 'No phone'}</span></div>
                {user.alternate_phone && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}><Phone size={18} color="var(--text-muted)" /> <span>Alternate: {user.alternate_phone}</span></div>
                )}
                {user.profile_bio && (
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}><User size={18} color="var(--text-muted)" style={{ marginTop: 2 }} /> <span>{user.profile_bio}</span></div>
                )}
                {user.gender && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}><User size={18} color="var(--text-muted)" /> <span>Gender: {user.gender}</span></div>
                )}
                {user.date_of_birth && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}><User size={18} color="var(--text-muted)" /> <span>Date of Birth: {user.date_of_birth}</span></div>
                )}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}><Globe size={18} color="var(--text-muted)" /> <span>Language: {user.preferred_language.toUpperCase()}</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}><Shield size={18} color="var(--text-muted)" /> <span>Status: {user.status}</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <User size={18} color="var(--text-muted)" />
                  <span style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    Account ID: <code style={{ background: 'var(--bg-body)', padding: '2px 8px', borderRadius: 4, fontSize: '0.78rem' }}>{user.id}</code>
                    <button
                      type="button"
                      onClick={copyAccountId}
                      title="Copy account ID"
                      style={{ background: 'none', border: '1px solid var(--border-card)', borderRadius: 4, padding: '3px 8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.75rem', color: idCopied ? 'var(--success)' : 'var(--text-muted)' }}
                    >
                      {idCopied ? <Check size={12} /> : <Copy size={12} />} {idCopied ? 'Copied' : 'Copy'}
                    </button>
                  </span>
                </div>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: -8 }}>
                  Share this ID with a family member so they can link your account under Kutumb Network &rarr; My Family.
                </p>
                <button className="btn btn-outline" onClick={() => {
                  setEditing(true);
                  setName(user.full_name);
                  setBio(user.profile_bio || '');
                  setGender(user.gender || '');
                  setDob(user.date_of_birth || '');
                  setAltPhone(user.alternate_phone || '');
                  setLanguage(user.preferred_language || 'en');
                }}>
                  Edit Profile
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div className="form-group"><label>Full Name</label><input value={name} onChange={e => setName(e.target.value)} /></div>
                <div className="form-group"><label>Bio</label><textarea value={bio} onChange={e => setBio(e.target.value)} rows={3} placeholder="Tell us about yourself..." /></div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div className="form-group">
                    <label>Gender</label>
                    <select value={gender} onChange={e => setGender(e.target.value)}>
                      <option value="">Prefer not to say</option>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                  <div className="form-group"><label>Date of Birth</label><input type="date" value={dob} onChange={e => setDob(e.target.value)} /></div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div className="form-group"><label>Alternate Phone</label><input value={altPhone} onChange={e => setAltPhone(e.target.value)} placeholder="+91XXXXXXXXXX" /></div>
                  <div className="form-group">
                    <label>Preferred Language</label>
                    <select value={language} onChange={e => setLanguage(e.target.value)}>
                      <option value="en">English</option>
                      <option value="hi">हिंदी (Hindi)</option>
                      <option value="gu">ગુજરાતી (Gujarati)</option>
                    </select>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-primary" onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
                  <button className="btn btn-outline" onClick={() => setEditing(false)}>Cancel</button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Kutumb Network */}
        <div
          onClick={() => navigate('/kutumb')}
          style={{ background: 'linear-gradient(135deg, #7C4DFF, #B388FF)', borderRadius: 'var(--radius-md)', padding: '18px 22px', marginTop: 16, display: 'flex', alignItems: 'center', gap: 14, color: 'white', cursor: 'pointer' }}
        >
          <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(255,255,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <Users size={20} />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>Kutumb Network</div>
            <div style={{ fontSize: '0.8rem', opacity: 0.9 }}>Family registration, community groups &amp; matrimonial (18+)</div>
          </div>
          <ChevronRight size={18} />
        </div>

        {/* Saved Addresses */}
        <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 24, marginTop: 16 }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
            <MapPin size={18} color="var(--primary)" /> Saved Delivery Addresses
          </h3>
          <AddressPicker selectedAddressId={null} onSelect={() => {}} />
        </div>
      </div>

      <AddMoneyModal isOpen={showAddMoney} onClose={() => setShowAddMoney(false)} onSuccess={refreshBalance} />
    </div>
  );
};
