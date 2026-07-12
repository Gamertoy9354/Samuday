import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { kutumbAPI, marketAPI, verificationAPI, authAPI } from '../api/client';
import {
  Users, Heart, Shield, Building2, Plus, Ban, Flag,
  BadgeCheck, Lock, AlertTriangle, Mail, MailCheck, MailX, LogOut, PauseCircle,
  PlayCircle, Search, Send, Inbox, ShieldAlert
} from 'lucide-react';

type Tab = 'family' | 'community' | 'matrimonial' | 'safety';
type MatrimonialSubTab = 'profile' | 'discover' | 'interests';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FamilyMember {
  id: string;
  family_id: string;
  user_id?: string | null;
  relationship_type: string;
  display_name: string;
  visible_phone: boolean;
  visible_kyc: boolean;
  status: 'accepted' | 'pending' | 'declined';
  added_by_user_id?: string | null;
  created_at: string;
}

interface Family {
  id: string;
  name: string;
  head_id: string;
  members: FamilyMember[];
  created_at: string;
}

interface CommunityGroup {
  id: string;
  name: string;
  group_type: string;
  description: string;
  location_geohash: string;
  created_by?: string | null;
  created_at: string;
  member_count: number;
  is_member: boolean;
}

interface MatrimonialProfile {
  id: string;
  user_id: string;
  gender: string;
  age: number;
  religion: string;
  caste?: string | null;
  occupation: string;
  education: string;
  about?: string | null;
  photo_url?: string | null;
  status: 'active' | 'paused' | 'suspended' | 'removed';
  age_verified: boolean;
  family_verified_badge: boolean;
  show_verified_family_badge: boolean;
  opt_in_confirmed: boolean;
  my_interest_status?: string | null;
  created_at: string;
}

interface MatrimonialInterest {
  id: string;
  from_user_id: string;
  to_user_id: string;
  status: 'pending' | 'accepted' | 'declined' | 'withdrawn';
  created_at: string;
  responded_at?: string | null;
  counterpart_profile?: MatrimonialProfile | null;
}

interface UserBlock {
  id: string;
  user_id: string;
  blocked_user_id: string;
  created_at: string;
}

const REPORT_REASONS: Array<{ value: string; label: string }> = [
  { value: 'harassment', label: 'Harassment' },
  { value: 'fake_profile', label: 'Fake profile' },
  { value: 'inappropriate_content', label: 'Inappropriate content' },
  { value: 'underage_suspicion', label: 'Underage suspicion' },
  { value: 'other', label: 'Other' },
];

const STATUS_CHIP: Record<string, { bg: string; color: string; label: string }> = {
  accepted: { bg: '#E8F5E9', color: '#2E7D32', label: 'Accepted' },
  pending: { bg: '#FFF3E0', color: '#E65100', label: 'Pending' },
  declined: { bg: '#FFEBEE', color: '#C62828', label: 'Declined' },
};

// ---------------------------------------------------------------------------
// Shared bits
// ---------------------------------------------------------------------------

const Card: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 20, ...style }}>
    {children}
  </div>
);

const ReportInline: React.FC<{ onSubmit: (reasonCode: string, details: string) => void; onCancel: () => void }> = ({ onSubmit, onCancel }) => {
  const [reasonCode, setReasonCode] = useState('harassment');
  const [details, setDetails] = useState('');
  return (
    <div style={{ background: 'var(--bg-body)', borderRadius: 8, padding: 14, marginTop: 10 }}>
      <div className="form-group" style={{ marginBottom: 8 }}>
        <label style={{ fontSize: '0.8rem' }}>Reason</label>
        <select value={reasonCode} onChange={e => setReasonCode(e.target.value)}>
          {REPORT_REASONS.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
        </select>
      </div>
      <div className="form-group" style={{ marginBottom: 10 }}>
        <label style={{ fontSize: '0.8rem' }}>Details (optional)</label>
        <textarea value={details} onChange={e => setDetails(e.target.value)} rows={2} placeholder="Anything that will help our review" />
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn btn-primary btn-sm" onClick={() => onSubmit(reasonCode, details)}>Submit Report</button>
        <button className="btn btn-outline btn-sm" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Page shell
// ---------------------------------------------------------------------------

export const KutumbPage: React.FC = () => {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>('family');

  if (!user) {
    return (
      <div className="page-content" style={{ paddingTop: 32 }}>
        <div className="empty-state"><h3>Please login to access Kutumb Network</h3></div>
      </div>
    );
  }

  return (
    <div className="page-content" style={{ paddingTop: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16 }}>
        <div style={{ width: 48, height: 48, borderRadius: 12, background: 'linear-gradient(135deg, #7C4DFF, #B388FF)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <Users size={26} color="white" />
        </div>
        <div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: 2 }}>Kutumb Network</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Family registration, local community groups &amp; a separate, opt-in matrimonial layer</p>
        </div>
      </div>

      <div className="dashboard-tabs">
        <button className={`dashboard-tab ${tab === 'family' ? 'active' : ''}`} onClick={() => setTab('family')}>
          <Users size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> My Family
        </button>
        <button className={`dashboard-tab ${tab === 'community' ? 'active' : ''}`} onClick={() => setTab('community')}>
          <Building2 size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> Community Groups
        </button>
        <button className={`dashboard-tab ${tab === 'matrimonial' ? 'active' : ''}`} onClick={() => setTab('matrimonial')}>
          <Heart size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> Matrimonial (18+)
        </button>
        <button className={`dashboard-tab ${tab === 'safety' ? 'active' : ''}`} onClick={() => setTab('safety')}>
          <Shield size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> Blocking &amp; Safety
        </button>
      </div>

      <div style={{ marginTop: 16 }}>
        {tab === 'family' && <FamilyTab userId={user.id} />}
        {tab === 'community' && <CommunityTab />}
        {tab === 'matrimonial' && <MatrimonialTab />}
        {tab === 'safety' && <SafetyTab />}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Family tab
// ---------------------------------------------------------------------------

const FamilyTab: React.FC<{ userId: string }> = ({ userId }) => {
  const [family, setFamily] = useState<Family | null>(null);
  const [invites, setInvites] = useState<FamilyMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [newFamilyName, setNewFamilyName] = useState('');
  const [creating, setCreating] = useState(false);

  const [memberName, setMemberName] = useState('');
  const [memberRelation, setMemberRelation] = useState('child');
  const [memberUserId, setMemberUserId] = useState('');
  const [visiblePhone, setVisiblePhone] = useState(false);
  const [visibleKyc, setVisibleKyc] = useState(false);
  const [addingMember, setAddingMember] = useState(false);
  const [editingVisibilityFor, setEditingVisibilityFor] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    const [famRes, invRes] = await Promise.allSettled([kutumbAPI.getMyFamily(), kutumbAPI.getFamilyInvites()]);
    setFamily(famRes.status === 'fulfilled' ? famRes.value : null);
    setInvites(invRes.status === 'fulfilled' ? invRes.value : []);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleCreateFamily = async () => {
    if (!newFamilyName.trim()) return;
    setCreating(true);
    setError('');
    try {
      const f = await kutumbAPI.createFamily(newFamilyName.trim());
      setFamily(f);
      setNewFamilyName('');
    } catch (e: any) {
      setError(e.message || 'Failed to create family');
    }
    setCreating(false);
  };

  const handleAddMember = async () => {
    if (!family || !memberName.trim()) return;
    setAddingMember(true);
    setError('');
    try {
      await kutumbAPI.addFamilyMember(family.id, {
        user_id: memberUserId.trim() || undefined,
        relationship_type: memberRelation,
        display_name: memberName.trim(),
        visible_phone: visiblePhone,
        visible_kyc: visibleKyc,
      });
      setMemberName(''); setMemberUserId(''); setVisiblePhone(false); setVisibleKyc(false);
      setNotice(memberUserId.trim() ? 'Member added — they must accept the link from their own account before it is confirmed.' : 'Member added.');
      await load();
    } catch (e: any) {
      setError(e.message || 'Failed to add member');
    }
    setAddingMember(false);
  };

  const handleRespondInvite = async (memberId: string, accept: boolean) => {
    try {
      await kutumbAPI.respondFamilyInvite(memberId, accept);
      setNotice(accept ? 'You accepted the family link.' : 'You declined the family link.');
      await load();
    } catch (e: any) {
      setError(e.message || 'Failed to respond to invite');
    }
  };

  const handleVisibilityChange = async (memberId: string, field: 'visible_phone' | 'visible_kyc', value: boolean) => {
    try {
      await kutumbAPI.updateMemberVisibility(memberId, { [field]: value });
      await load();
    } catch (e: any) {
      setError(e.message || 'Failed to update visibility');
    }
  };

  if (loading) return <div className="skeleton" style={{ height: 180 }} />;

  const isHead = family?.head_id === userId;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 720 }}>
      {error && <div className="alert alert-error">{error}</div>}
      {notice && <div className="alert alert-success">{notice}</div>}

      {invites.length > 0 && (
        <Card style={{ borderColor: '#FFCC80', background: '#FFF8E1' }}>
          <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 8, color: '#E65100' }}>
            <Mail size={16} /> Family Invites Awaiting Your Response
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {invites.map(inv => (
              <div key={inv.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'white', padding: '10px 14px', borderRadius: 8 }}>
                <div style={{ fontSize: '0.85rem' }}>
                  Someone added you as their <strong>{inv.relationship_type}</strong> ({inv.display_name})
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button className="btn btn-primary btn-sm" onClick={() => handleRespondInvite(inv.id, true)} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <MailCheck size={13} /> Accept
                  </button>
                  <button className="btn btn-outline btn-sm" onClick={() => handleRespondInvite(inv.id, false)} style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--danger)' }}>
                    <MailX size={13} /> Decline
                  </button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {!family ? (
        <Card style={{ maxWidth: 480 }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: 6 }}>Register your family</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: 16 }}>
            Create a family unit for local community directories and mutual-aid networking. This is completely
            separate from the matrimonial layer &mdash; registering here never creates or exposes a matrimonial profile for anyone.
          </p>
          <div className="form-group">
            <label>Family Name</label>
            <input value={newFamilyName} onChange={e => setNewFamilyName(e.target.value)} placeholder="e.g. Sharma Family" />
          </div>
          <button className="btn btn-primary" disabled={creating || !newFamilyName.trim()} onClick={handleCreateFamily}>
            {creating ? 'Creating...' : 'Create Family'}
          </button>
        </Card>
      ) : (
        <>
          <Card>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: 4 }}>{family.name}</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 16 }}>
              {isHead ? 'You are the primary contact for this family.' : 'You are linked to this family.'}
            </p>

            {family.members.length === 0 ? (
              <div className="empty-state" style={{ padding: '20px 0' }}>No members added yet.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {family.members.map(m => {
                  const chip = STATUS_CHIP[m.status];
                  const isMe = m.user_id === userId && m.status === 'accepted';
                  const headOwnsPlaceholder = isHead && !m.user_id;
                  const canManage = isMe || headOwnsPlaceholder;
                  return (
                    <div key={m.id} style={{ background: 'var(--bg-body)', padding: '10px 14px', borderRadius: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{m.display_name} {isMe && <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(you)</span>}</div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>{m.relationship_type}{!m.user_id && ' · no account linked'}</div>
                        </div>
                        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                          <span style={{ fontSize: '0.7rem', background: chip.bg, color: chip.color, padding: '2px 8px', borderRadius: 10, fontWeight: 600 }}>{chip.label}</span>
                          {m.visible_phone && <span style={{ fontSize: '0.7rem', background: '#E8F5E9', color: '#2E7D32', padding: '2px 8px', borderRadius: 10 }}>Phone visible</span>}
                          {m.visible_kyc && <span style={{ fontSize: '0.7rem', background: '#E8F5E9', color: '#2E7D32', padding: '2px 8px', borderRadius: 10 }}>KYC visible</span>}
                          {!m.visible_phone && !m.visible_kyc && <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}><Lock size={11} /> Private</span>}
                          {canManage && (
                            <button className="btn btn-outline btn-sm" onClick={() => setEditingVisibilityFor(editingVisibilityFor === m.id ? null : m.id)}>
                              Manage
                            </button>
                          )}
                        </div>
                      </div>
                      {editingVisibilityFor === m.id && (
                        <div style={{ display: 'flex', gap: 18, marginTop: 10, paddingTop: 10, borderTop: '1px dashed var(--border-light)' }}>
                          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.82rem' }}>
                            <input type="checkbox" checked={m.visible_phone} onChange={e => handleVisibilityChange(m.id, 'visible_phone', e.target.checked)} /> Show phone in directory
                          </label>
                          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.82rem' }}>
                            <input type="checkbox" checked={m.visible_kyc} onChange={e => handleVisibilityChange(m.id, 'visible_kyc', e.target.checked)} /> Show KYC verified badge
                          </label>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </Card>

          {isHead && (
            <Card>
              <h4 style={{ fontSize: '0.92rem', fontWeight: 700, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                <Plus size={16} /> Add a Family Member
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="form-group">
                  <label>Display Name</label>
                  <input value={memberName} onChange={e => setMemberName(e.target.value)} placeholder="e.g. Priya Sharma" />
                </div>
                <div className="form-group">
                  <label>Relationship</label>
                  <select value={memberRelation} onChange={e => setMemberRelation(e.target.value)}>
                    <option value="spouse">Spouse</option>
                    <option value="child">Child</option>
                    <option value="parent">Parent</option>
                    <option value="sibling">Sibling</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label>Linked App User ID (optional)</label>
                <input value={memberUserId} onChange={e => setMemberUserId(e.target.value)} placeholder="Leave blank if they don't have their own account" />
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 10 }}>
                If you link an account, that person will see this as a pending invite on their own Kutumb Network page and must accept
                it themselves &mdash; you can't set their visibility for them. Visibility toggles below only take effect immediately for
                account-less members.
              </p>
              <div style={{ display: 'flex', gap: 18, marginBottom: 14 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.85rem' }}>
                  <input type="checkbox" checked={visiblePhone} onChange={e => setVisiblePhone(e.target.checked)} /> Show phone in directory
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.85rem' }}>
                  <input type="checkbox" checked={visibleKyc} onChange={e => setVisibleKyc(e.target.checked)} /> Show KYC verified badge
                </label>
              </div>
              <button className="btn btn-primary" disabled={addingMember || !memberName.trim()} onClick={handleAddMember}>
                {addingMember ? 'Adding...' : 'Add Member'}
              </button>
            </Card>
          )}
        </>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Community tab
// ---------------------------------------------------------------------------

const CommunityTab: React.FC = () => {
  const [view, setView] = useState<'discover' | 'mine'>('discover');
  const [groups, setGroups] = useState<CommunityGroup[]>([]);
  const [myGroups, setMyGroups] = useState<CommunityGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [groupType, setGroupType] = useState('neighborhood');
  const [description, setDescription] = useState('');
  const [geohash, setGeohash] = useState('');
  const [creating, setCreating] = useState(false);
  const [actingId, setActingId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    const [gRes, mRes] = await Promise.allSettled([kutumbAPI.getGroups(), kutumbAPI.getMyGroups()]);
    setGroups(gRes.status === 'fulfilled' ? gRes.value : []);
    setMyGroups(mRes.status === 'fulfilled' ? mRes.value : []);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!name.trim() || !description.trim() || !geohash.trim()) return;
    setCreating(true);
    setError('');
    try {
      await kutumbAPI.createGroup({ name: name.trim(), group_type: groupType, description: description.trim(), location_geohash: geohash.trim() });
      setName(''); setDescription(''); setGeohash('');
      setShowForm(false);
      await load();
    } catch (e: any) {
      setError(e.message || 'Failed to create group');
    }
    setCreating(false);
  };

  const handleJoin = async (groupId: string) => {
    setActingId(groupId);
    try { await kutumbAPI.joinGroup(groupId); await load(); } catch (e: any) { setError(e.message || 'Failed to join'); }
    setActingId(null);
  };

  const handleLeave = async (groupId: string) => {
    setActingId(groupId);
    try { await kutumbAPI.leaveGroup(groupId); await load(); } catch (e: any) { setError(e.message || 'Failed to leave'); }
    setActingId(null);
  };

  const list = view === 'discover' ? groups : myGroups;

  return (
    <div style={{ maxWidth: 720 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 10 }}>
        <div className="dashboard-tabs" style={{ marginBottom: 0 }}>
          <button className={`dashboard-tab ${view === 'discover' ? 'active' : ''}`} onClick={() => setView('discover')}>Discover</button>
          <button className={`dashboard-tab ${view === 'mine' ? 'active' : ''}`} onClick={() => setView('mine')}>My Groups ({myGroups.length})</button>
        </div>
        <button className="btn btn-outline btn-sm" onClick={() => setShowForm(v => !v)}>
          <Plus size={14} style={{ marginRight: 4, verticalAlign: -2 }} /> New Group
        </button>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: 12 }}>{error}</div>}

      {showForm && (
        <Card style={{ marginBottom: 16 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label>Group Name</label>
              <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Green Valley Society" />
            </div>
            <div className="form-group">
              <label>Type</label>
              <select value={groupType} onChange={e => setGroupType(e.target.value)}>
                <option value="neighborhood">Neighborhood</option>
                <option value="society">Housing Society</option>
                <option value="temple">Temple / Religious</option>
                <option value="alumni">Alumni</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>
          <div className="form-group">
            <label>Description</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} rows={3} placeholder="What's this group for?" />
          </div>
          <div className="form-group">
            <label>Location Geohash</label>
            <input value={geohash} onChange={e => setGeohash(e.target.value)} placeholder="e.g. tdr1y" />
          </div>
          <button className="btn btn-primary" disabled={creating} onClick={handleCreate}>{creating ? 'Creating...' : 'Create Group'}</button>
        </Card>
      )}

      {loading ? (
        <div className="skeleton" style={{ height: 140 }} />
      ) : list.length === 0 ? (
        <div className="empty-state">{view === 'discover' ? 'No community groups yet — be the first to create one.' : "You haven't joined any groups yet."}</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {list.map(g => (
            <Card key={g.id} style={{ padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <h4 style={{ fontSize: '0.95rem', fontWeight: 700 }}>{g.name}</h4>
                    <span style={{ fontSize: '0.72rem', background: 'var(--bg-body)', padding: '2px 8px', borderRadius: 10, textTransform: 'capitalize' }}>{g.group_type}</span>
                  </div>
                  <p style={{ fontSize: '0.83rem', color: 'var(--text-muted)', marginBottom: 6 }}>{g.description}</p>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{g.member_count} member{g.member_count !== 1 ? 's' : ''}</span>
                </div>
                {g.is_member ? (
                  <button className="btn btn-outline btn-sm" disabled={actingId === g.id} onClick={() => handleLeave(g.id)} style={{ display: 'flex', alignItems: 'center', gap: 4, whiteSpace: 'nowrap' }}>
                    <LogOut size={13} /> Leave
                  </button>
                ) : (
                  <button className="btn btn-primary btn-sm" disabled={actingId === g.id} onClick={() => handleJoin(g.id)} style={{ whiteSpace: 'nowrap' }}>
                    Join
                  </button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Matrimonial tab
// ---------------------------------------------------------------------------

const MatrimonialTab: React.FC = () => {
  const [subTab, setSubTab] = useState<MatrimonialSubTab>('profile');
  const [myProfile, setMyProfile] = useState<MatrimonialProfile | null>(null);
  const [profileLoaded, setProfileLoaded] = useState(false);
  const [notice, setNotice] = useState('');

  const loadProfile = async () => {
    try {
      setMyProfile(await kutumbAPI.getMyMatrimonialProfile());
    } catch {
      setMyProfile(null);
    }
    setProfileLoaded(true);
  };

  useEffect(() => { loadProfile(); }, []);

  const canBrowse = !!myProfile && (myProfile.status === 'active' || myProfile.status === 'paused');

  return (
    <div style={{ maxWidth: 800 }}>
      <div style={{ background: '#FDF2FF', border: '1px solid #F0C9FF', borderRadius: 'var(--radius-md)', padding: '14px 18px', marginBottom: 16, display: 'flex', gap: 12, alignItems: 'flex-start' }}>
        <AlertTriangle size={18} color="#8E24AA" style={{ marginTop: 2, flexShrink: 0 }} />
        <div style={{ fontSize: '0.82rem', color: '#4A148C' }}>
          <strong>Adults only, fully separate &amp; opt-in.</strong> Age is verified server-side from your KYC-approved
          identity, never from a form field. This is never linked to your family registration unless you explicitly
          choose to show a verified-family badge.
        </div>
      </div>

      {notice && <div className="alert alert-success" style={{ marginBottom: 14 }}>{notice}</div>}

      <div className="dashboard-tabs">
        <button className={`dashboard-tab ${subTab === 'profile' ? 'active' : ''}`} onClick={() => setSubTab('profile')}>My Profile</button>
        <button className={`dashboard-tab ${subTab === 'discover' ? 'active' : ''}`} onClick={() => canBrowse && setSubTab('discover')} disabled={!canBrowse} style={{ opacity: canBrowse ? 1 : 0.5 }}>Discover</button>
        <button className={`dashboard-tab ${subTab === 'interests' ? 'active' : ''}`} onClick={() => canBrowse && setSubTab('interests')} disabled={!canBrowse} style={{ opacity: canBrowse ? 1 : 0.5 }}>Interests</button>
      </div>

      <div style={{ marginTop: 16 }}>
        {subTab === 'profile' && profileLoaded && (
          <MatrimonialProfilePanel
            profile={myProfile}
            onChanged={async (msg) => { setNotice(msg); await loadProfile(); }}
          />
        )}
        {subTab === 'discover' && canBrowse && <MatrimonialDiscoverPanel onNotice={setNotice} />}
        {subTab === 'interests' && canBrowse && <MatrimonialInterestsPanel onNotice={setNotice} />}
      </div>
    </div>
  );
};

const MatrimonialProfilePanel: React.FC<{ profile: MatrimonialProfile | null; onChanged: (msg: string) => void }> = ({ profile, onChanged }) => {
  const { refreshUser } = useAuth();
  const [showOptIn, setShowOptIn] = useState(false);
  const [error, setError] = useState('');
  const [needsKyc, setNeedsKyc] = useState(false);
  const [needsDob, setNeedsDob] = useState(false);
  const [dobInput, setDobInput] = useState('');
  const [savingDob, setSavingDob] = useState(false);

  const [gender, setGender] = useState('female');
  const [religion, setReligion] = useState('');
  const [caste, setCaste] = useState('');
  const [occupation, setOccupation] = useState('');
  const [education, setEducation] = useState('');
  const [about, setAbout] = useState('');
  const [photoUrl, setPhotoUrl] = useState('');
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [showBadge, setShowBadge] = useState(false);
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [editing, setEditing] = useState(false);
  const [editReligion, setEditReligion] = useState('');
  const [editCaste, setEditCaste] = useState('');
  const [editOccupation, setEditOccupation] = useState('');
  const [editEducation, setEditEducation] = useState('');
  const [editAbout, setEditAbout] = useState('');
  const [editPhotoUrl, setEditPhotoUrl] = useState('');
  const [editShowBadge, setEditShowBadge] = useState(false);
  const [saving, setSaving] = useState(false);

  // Inline quick-KYC submission, surfaced only when opt-in fails due to missing verification.
  const [kycIdType, setKycIdType] = useState('aadhaar');
  const [kycFile, setKycFile] = useState<File | null>(null);
  const [kycSubmitting, setKycSubmitting] = useState(false);
  const [kycSubmitted, setKycSubmitted] = useState(false);

  const handlePhotoUpload = async (file: File, setter: (url: string) => void) => {
    setUploadingPhoto(true);
    try {
      const res = await marketAPI.uploadImage(file);
      setter(res.url);
    } catch { /* graceful degradation */ }
    setUploadingPhoto(false);
  };

  const handleOptIn = async () => {
    setError(''); setNeedsKyc(false); setNeedsDob(false);
    if (!consent) { setError('Please confirm you are 18+ and agree to the matrimonial consent statement.'); return; }
    if (!religion.trim() || !occupation.trim() || !education.trim()) { setError('Please fill in all required fields.'); return; }
    setSubmitting(true);
    try {
      await kutumbAPI.optInMatrimonial({
        gender, religion: religion.trim(), caste: caste.trim() || undefined,
        occupation: occupation.trim(), education: education.trim(), about: about.trim() || undefined,
        photo_url: photoUrl || undefined, show_verified_family_badge: showBadge, consent_confirmed: true,
      });
      setShowOptIn(false);
      onChanged('Your matrimonial profile is live.');
    } catch (e: any) {
      const msg = e.message || 'Failed to create matrimonial profile';
      setError(msg);
      if (/date of birth/i.test(msg)) setNeedsDob(true);
      else if (/kyc|identity/i.test(msg)) setNeedsKyc(true);
    }
    setSubmitting(false);
  };

  const handleSaveDob = async () => {
    if (!dobInput) { setError('Please choose your date of birth.'); return; }
    setSavingDob(true);
    setError('');
    try {
      await authAPI.updateProfile({ date_of_birth: dobInput });
      await refreshUser();
      setNeedsDob(false);
      await handleOptIn();
    } catch (e: any) {
      setError(e.message || 'Failed to save date of birth');
    }
    setSavingDob(false);
  };

  const handleKycSubmit = async () => {
    if (!kycFile) { setError('Please choose a document photo to upload.'); return; }
    setKycSubmitting(true);
    setError('');
    try {
      const uploaded = await marketAPI.uploadImage(kycFile);
      await verificationAPI.submitLocalKyc({ id_type: kycIdType, document_url: uploaded.url });
      setKycSubmitted(true);
    } catch (e: any) {
      setError(e.message || 'Failed to submit identity verification');
    }
    setKycSubmitting(false);
  };

  const startEdit = () => {
    if (!profile) return;
    setEditReligion(profile.religion); setEditCaste(profile.caste || ''); setEditOccupation(profile.occupation);
    setEditEducation(profile.education); setEditAbout(profile.about || ''); setEditPhotoUrl(profile.photo_url || '');
    setEditShowBadge(profile.show_verified_family_badge);
    setEditing(true);
  };

  const handleSaveEdit = async () => {
    setSaving(true); setError('');
    try {
      await kutumbAPI.updateMatrimonialProfile({
        religion: editReligion.trim(), caste: editCaste.trim() || null, occupation: editOccupation.trim(),
        education: editEducation.trim(), about: editAbout.trim() || null, photo_url: editPhotoUrl || null,
        show_verified_family_badge: editShowBadge,
      });
      setEditing(false);
      onChanged('Profile updated.');
    } catch (e: any) {
      setError(e.message || 'Failed to update profile');
    }
    setSaving(false);
  };

  const handleToggleStatus = async () => {
    if (!profile) return;
    try {
      await kutumbAPI.updateMatrimonialProfile({ status: profile.status === 'active' ? 'paused' : 'active' });
      onChanged(profile.status === 'active' ? 'Profile paused — hidden from discovery until reactivated.' : 'Profile reactivated.');
    } catch (e: any) {
      setError(e.message || 'Failed to update status');
    }
  };

  const handleOptOut = async () => {
    if (!window.confirm('Opt out of the matrimonial layer? Your profile will be immediately removed from discovery and all pending interests withdrawn.')) return;
    try {
      await kutumbAPI.optOutMatrimonial();
      onChanged('You have opted out of the matrimonial layer.');
    } catch (e: any) {
      setError(e.message || 'Failed to opt out');
    }
  };

  if (profile) {
    return (
      <Card>
        {error && <div className="alert alert-error" style={{ marginBottom: 12 }}>{error}</div>}
        {profile.status === 'suspended' && (
          <div className="alert alert-error" style={{ marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
            <ShieldAlert size={16} /> Your profile is suspended pending moderation review and can't be edited or browsed right now.
          </div>
        )}
        {profile.status === 'paused' && (
          <div className="alert alert-success" style={{ marginBottom: 14, background: '#FFF3E0', color: '#E65100' }}>
            Your profile is paused — hidden from discovery until you reactivate it.
          </div>
        )}

        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
          {profile.photo_url && (
            <img src={profile.photo_url} alt="" style={{ width: 80, height: 80, borderRadius: 12, objectFit: 'cover', flexShrink: 0 }} />
          )}
          <div style={{ flex: 1 }}>
            <h4 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              {profile.age} yrs, {profile.gender}
              {profile.family_verified_badge && (
                <span style={{ fontSize: '0.7rem', background: '#E3F2FD', color: '#1565C0', padding: '2px 8px', borderRadius: 10, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                  <BadgeCheck size={12} /> Verified Family
                </span>
              )}
              <span style={{ fontSize: '0.7rem', background: profile.status === 'active' ? '#E8F5E9' : '#F5F5F5', color: profile.status === 'active' ? '#2E7D32' : 'var(--text-muted)', padding: '2px 8px', borderRadius: 10, textTransform: 'capitalize' }}>{profile.status}</span>
            </h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 6 }}>
              {profile.religion}{profile.caste ? ` · ${profile.caste}` : ''} &middot; {profile.occupation} &middot; {profile.education}
            </p>
            {profile.about && <p style={{ fontSize: '0.85rem', marginBottom: 6 }}>{profile.about}</p>}
          </div>
        </div>

        {!editing ? (
          profile.status !== 'suspended' && (
            <div style={{ display: 'flex', gap: 10, marginTop: 16, flexWrap: 'wrap' }}>
              <button className="btn btn-outline btn-sm" onClick={startEdit}>Edit Profile</button>
              <button className="btn btn-outline btn-sm" onClick={handleToggleStatus} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                {profile.status === 'active' ? <><PauseCircle size={13} /> Pause</> : <><PlayCircle size={13} /> Reactivate</>}
              </button>
              <button className="btn btn-outline btn-sm" onClick={handleOptOut} style={{ color: 'var(--danger)' }}>Opt Out Entirely</button>
            </div>
          )
        ) : (
          <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border-light)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-group"><label>Religion</label><input value={editReligion} onChange={e => setEditReligion(e.target.value)} /></div>
              <div className="form-group"><label>Caste (optional)</label><input value={editCaste} onChange={e => setEditCaste(e.target.value)} /></div>
              <div className="form-group"><label>Occupation</label><input value={editOccupation} onChange={e => setEditOccupation(e.target.value)} /></div>
              <div className="form-group"><label>Education</label><input value={editEducation} onChange={e => setEditEducation(e.target.value)} /></div>
            </div>
            <div className="form-group"><label>About</label><textarea value={editAbout} onChange={e => setEditAbout(e.target.value)} rows={3} /></div>
            <div className="form-group">
              <label>Photo (only shown to mutually accepted matches)</label>
              {editPhotoUrl && <img src={editPhotoUrl} alt="" style={{ width: 60, height: 60, borderRadius: 8, objectFit: 'cover', marginBottom: 6 }} />}
              <input type="file" accept="image/*" onChange={e => e.target.files?.[0] && handlePhotoUpload(e.target.files[0], setEditPhotoUrl)} />
              {uploadingPhoto && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Uploading...</span>}
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem', margin: '8px 0 14px' }}>
              <input type="checkbox" checked={editShowBadge} onChange={e => setEditShowBadge(e.target.checked)} /> Show verified-family badge
            </label>
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn btn-primary" disabled={saving} onClick={handleSaveEdit}>{saving ? 'Saving...' : 'Save Changes'}</button>
              <button className="btn btn-outline" onClick={() => setEditing(false)}>Cancel</button>
            </div>
          </div>
        )}
      </Card>
    );
  }

  return (
    <Card>
      {!showOptIn ? (
        <>
          <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: 6 }}>Create your matrimonial profile</h4>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: 14 }}>
            For adults (18+) only, by explicit opt-in. Requires your date of birth on file and an approved identity (KYC) verification.
          </p>
          <button className="btn btn-primary" onClick={() => setShowOptIn(true)}>
            <Heart size={14} style={{ marginRight: 6, verticalAlign: -2 }} /> Start Matrimonial Opt-In
          </button>
        </>
      ) : (
        <>
          <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: 12 }}>Matrimonial Opt-In</h4>
          {error && <div className="alert alert-error" style={{ marginBottom: 12 }}>{error}</div>}

          {needsDob && (
            <div style={{ background: '#FFF3E0', borderRadius: 8, padding: 14, marginBottom: 16 }}>
              <h5 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: 8 }}>Add your date of birth</h5>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 10 }}>
                Your age is verified from your profile's date of birth, not from a field in this form. Set it once here
                (or on your Profile page) and we'll continue automatically.
              </p>
              <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end', flexWrap: 'wrap' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label style={{ fontSize: '0.78rem' }}>Date of Birth</label>
                  <input type="date" value={dobInput} onChange={e => setDobInput(e.target.value)} />
                </div>
                <button className="btn btn-primary btn-sm" disabled={savingDob} onClick={handleSaveDob}>{savingDob ? 'Saving...' : 'Save & Continue'}</button>
              </div>
            </div>
          )}

          {needsKyc && !kycSubmitted && (
            <div style={{ background: '#FFF3E0', borderRadius: 8, padding: 14, marginBottom: 16 }}>
              <h5 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: 8 }}>Quick identity verification</h5>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 10 }}>
                We need a verified ID on file before you can opt in. Upload one now — an admin will review it, then you can opt in again.
                Also make sure your date of birth is set on your Profile page.
              </p>
              <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end', flexWrap: 'wrap' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label style={{ fontSize: '0.78rem' }}>ID Type</label>
                  <select value={kycIdType} onChange={e => setKycIdType(e.target.value)}>
                    <option value="aadhaar">Aadhaar</option>
                    <option value="pan">PAN</option>
                    <option value="voter_id">Voter ID</option>
                  </select>
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label style={{ fontSize: '0.78rem' }}>Document Photo</label>
                  <input type="file" accept="image/*" onChange={e => setKycFile(e.target.files?.[0] || null)} />
                </div>
                <button className="btn btn-primary btn-sm" disabled={kycSubmitting} onClick={handleKycSubmit}>{kycSubmitting ? 'Submitting...' : 'Submit for Review'}</button>
              </div>
            </div>
          )}
          {kycSubmitted && (
            <div className="alert alert-success" style={{ marginBottom: 16 }}>
              Submitted for review. Once an admin approves it (and your date of birth is set on your profile), come back and opt in again.
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label>Gender</label>
              <select value={gender} onChange={e => setGender(e.target.value)}>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div className="form-group">
              <label>Religion</label>
              <input value={religion} onChange={e => setReligion(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Caste (optional)</label>
              <input value={caste} onChange={e => setCaste(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Occupation</label>
              <input value={occupation} onChange={e => setOccupation(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Education</label>
              <input value={education} onChange={e => setEducation(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Photo (optional, shown only to mutual matches)</label>
              <input type="file" accept="image/*" onChange={e => e.target.files?.[0] && handlePhotoUpload(e.target.files[0], setPhotoUrl)} />
              {uploadingPhoto && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Uploading...</span>}
            </div>
          </div>
          <div className="form-group">
            <label>About (optional)</label>
            <textarea value={about} onChange={e => setAbout(e.target.value)} rows={3} placeholder="A short note about yourself" />
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem', margin: '6px 0 10px' }}>
            <input type="checkbox" checked={showBadge} onChange={e => setShowBadge(e.target.checked)} /> Show verified-family badge if my family is registered &amp; KYC-verified
          </label>
          <label style={{ display: 'flex', alignItems: 'flex-start', gap: 8, fontSize: '0.82rem', margin: '10px 0 16px' }}>
            <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} style={{ marginTop: 3 }} />
            <span>I confirm I am 18 years of age or older and I explicitly consent to creating a matrimonial profile, separate from any family registration.</span>
          </label>
          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn btn-primary" disabled={submitting} onClick={handleOptIn}>{submitting ? 'Submitting...' : 'Confirm Opt-In'}</button>
            <button className="btn btn-outline" onClick={() => setShowOptIn(false)}>Cancel</button>
          </div>
        </>
      )}
    </Card>
  );
};

const MatrimonialDiscoverPanel: React.FC<{ onNotice: (msg: string) => void }> = ({ onNotice }) => {
  const [filterGender, setFilterGender] = useState('');
  const [filterReligion, setFilterReligion] = useState('');
  const [filterOccupation, setFilterOccupation] = useState('');
  const [minAge, setMinAge] = useState('');
  const [maxAge, setMaxAge] = useState('');
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [results, setResults] = useState<MatrimonialProfile[]>([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [reportingFor, setReportingFor] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const handleSearch = async () => {
    setSearching(true);
    try {
      const res = await kutumbAPI.searchMatrimonial({
        gender: filterGender || undefined, religion: filterReligion || undefined,
        occupation: filterOccupation || undefined, verified_only: verifiedOnly || undefined,
        min_age: minAge || undefined, max_age: maxAge || undefined,
      });
      setResults(res);
      setSearched(true);
    } catch { /* graceful degradation */ }
    setSearching(false);
  };

  useEffect(() => { handleSearch(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSendInterest = async (userId: string) => {
    setBusyId(userId);
    try {
      await kutumbAPI.sendInterest(userId);
      setResults(prev => prev.map(p => p.user_id === userId ? { ...p, my_interest_status: 'sent_pending' } : p));
      onNotice('Interest sent.');
    } catch (e: any) {
      onNotice(e.message || 'Failed to send interest');
    }
    setBusyId(null);
  };

  const handleRespond = async (userId: string, action: 'accept' | 'decline') => {
    // Search results don't carry the interest id directly; fetch it from the received list.
    setBusyId(userId);
    try {
      const received: any[] = await kutumbAPI.getMyInterests('received');
      const match = received.find(r => r.from_user_id === userId && r.status === 'pending');
      if (match) {
        await kutumbAPI.respondInterest(match.id, action);
        setResults(prev => prev.map(p => p.user_id === userId ? { ...p, my_interest_status: action === 'accept' ? 'matched' : 'declined' } : p));
        onNotice(action === 'accept' ? "It's a match! You can now see each other's full profile." : 'Declined.');
      }
    } catch (e: any) {
      onNotice(e.message || 'Failed to respond');
    }
    setBusyId(null);
  };

  const handleBlock = async (userId: string) => {
    if (!window.confirm('Block this profile? They will immediately be unable to see or contact you.')) return;
    try {
      await kutumbAPI.blockUser(userId);
      setResults(prev => prev.filter(p => p.user_id !== userId));
      onNotice('Profile blocked.');
    } catch (e: any) {
      onNotice(e.message || 'Failed to block');
    }
  };

  const handleReport = async (userId: string, reasonCode: string, details: string) => {
    try {
      await kutumbAPI.submitReport(userId, reasonCode, details || undefined);
      setReportingFor(null);
      onNotice('Report submitted for moderation review. Thank you.');
    } catch (e: any) {
      onNotice(e.message || 'Failed to submit report');
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 14 }}>
        <select value={filterGender} onChange={e => setFilterGender(e.target.value)} style={{ maxWidth: 130 }}>
          <option value="">Any Gender</option>
          <option value="male">Male</option>
          <option value="female">Female</option>
          <option value="other">Other</option>
        </select>
        <input placeholder="Religion" value={filterReligion} onChange={e => setFilterReligion(e.target.value)} style={{ maxWidth: 130 }} />
        <input placeholder="Occupation" value={filterOccupation} onChange={e => setFilterOccupation(e.target.value)} style={{ maxWidth: 130 }} />
        <input placeholder="Min age" type="number" value={minAge} onChange={e => setMinAge(e.target.value)} style={{ maxWidth: 90 }} />
        <input placeholder="Max age" type="number" value={maxAge} onChange={e => setMaxAge(e.target.value)} style={{ maxWidth: 90 }} />
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.85rem' }}>
          <input type="checkbox" checked={verifiedOnly} onChange={e => setVerifiedOnly(e.target.checked)} /> Verified family only
        </label>
        <button className="btn btn-primary btn-sm" onClick={handleSearch} disabled={searching} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Search size={13} /> {searching ? 'Searching...' : 'Search'}
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {searched && results.length === 0 ? (
          <div className="empty-state">No results &mdash; try adjusting your filters.</div>
        ) : results.map(p => (
          <Card key={p.id} style={{ padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
              <div style={{ display: 'flex', gap: 12, flex: 1 }}>
                {p.photo_url && <img src={p.photo_url} alt="" style={{ width: 56, height: 56, borderRadius: 10, objectFit: 'cover', flexShrink: 0 }} />}
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    {p.age} yrs, {p.gender}
                    {p.family_verified_badge && (
                      <span style={{ fontSize: '0.68rem', background: '#E3F2FD', color: '#1565C0', padding: '2px 7px', borderRadius: 10, display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                        <BadgeCheck size={11} /> Verified Family
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {p.religion}{p.caste ? ` · ${p.caste}` : ''} &middot; {p.occupation} &middot; {p.education}
                  </div>
                  {p.about && <div style={{ fontSize: '0.8rem', marginTop: 4 }}>{p.about}</div>}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                <button className="btn btn-outline btn-sm" onClick={() => setReportingFor(reportingFor === p.user_id ? null : p.user_id)} title="Report"><Flag size={13} /></button>
                <button className="btn btn-outline btn-sm" onClick={() => handleBlock(p.user_id)} title="Block"><Ban size={13} /></button>
              </div>
            </div>

            <div style={{ marginTop: 10 }}>
              {p.my_interest_status === 'matched' && <span style={{ fontSize: '0.75rem', background: '#E8F5E9', color: '#2E7D32', padding: '3px 10px', borderRadius: 10, fontWeight: 600 }}>&#10003; Matched</span>}
              {p.my_interest_status === 'sent_pending' && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Interest sent, awaiting response</span>}
              {p.my_interest_status === 'declined' && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Not available</span>}
              {p.my_interest_status === 'received_pending' && (
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span style={{ fontSize: '0.78rem' }}>They're interested in you</span>
                  <button className="btn btn-primary btn-sm" disabled={busyId === p.user_id} onClick={() => handleRespond(p.user_id, 'accept')}>Accept</button>
                  <button className="btn btn-outline btn-sm" disabled={busyId === p.user_id} onClick={() => handleRespond(p.user_id, 'decline')}>Decline</button>
                </div>
              )}
              {(!p.my_interest_status || p.my_interest_status === 'none') && (
                <button className="btn btn-primary btn-sm" disabled={busyId === p.user_id} onClick={() => handleSendInterest(p.user_id)} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Send size={13} /> Send Interest
                </button>
              )}
            </div>

            {reportingFor === p.user_id && (
              <ReportInline onCancel={() => setReportingFor(null)} onSubmit={(reason, details) => handleReport(p.user_id, reason, details)} />
            )}
          </Card>
        ))}
      </div>
    </div>
  );
};

const MatrimonialInterestsPanel: React.FC<{ onNotice: (msg: string) => void }> = ({ onNotice }) => {
  const [direction, setDirection] = useState<'received' | 'sent'>('received');
  const [interests, setInterests] = useState<MatrimonialInterest[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = async (dir: 'received' | 'sent') => {
    setLoading(true);
    try {
      setInterests(await kutumbAPI.getMyInterests(dir));
    } catch {
      setInterests([]);
    }
    setLoading(false);
  };

  useEffect(() => { load(direction); }, [direction]);

  const handleAction = async (id: string, action: 'accept' | 'decline' | 'withdraw') => {
    setBusyId(id);
    try {
      await kutumbAPI.respondInterest(id, action);
      onNotice(action === 'accept' ? "It's a match!" : action === 'decline' ? 'Declined.' : 'Withdrawn.');
      await load(direction);
    } catch (e: any) {
      onNotice(e.message || 'Failed to update interest');
    }
    setBusyId(null);
  };

  return (
    <div>
      <div className="dashboard-tabs" style={{ marginBottom: 14 }}>
        <button className={`dashboard-tab ${direction === 'received' ? 'active' : ''}`} onClick={() => setDirection('received')}>
          <Inbox size={14} style={{ marginRight: 6, verticalAlign: -2 }} /> Received
        </button>
        <button className={`dashboard-tab ${direction === 'sent' ? 'active' : ''}`} onClick={() => setDirection('sent')}>
          <Send size={14} style={{ marginRight: 6, verticalAlign: -2 }} /> Sent
        </button>
      </div>

      {loading ? (
        <div className="skeleton" style={{ height: 100 }} />
      ) : interests.length === 0 ? (
        <div className="empty-state">No {direction} interests yet.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {interests.map(it => (
            <Card key={it.id} style={{ padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                <div>
                  {it.counterpart_profile ? (
                    <>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                        {it.counterpart_profile.age} yrs, {it.counterpart_profile.gender}
                        {it.counterpart_profile.family_verified_badge && (
                          <span style={{ fontSize: '0.68rem', background: '#E3F2FD', color: '#1565C0', padding: '2px 7px', borderRadius: 10, marginLeft: 8 }}>
                            <BadgeCheck size={10} style={{ verticalAlign: -1 }} /> Verified Family
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        {it.counterpart_profile.religion}{it.counterpart_profile.caste ? ` · ${it.counterpart_profile.caste}` : ''} &middot; {it.counterpart_profile.occupation}
                      </div>
                      {it.status === 'accepted' && it.counterpart_profile.about && (
                        <div style={{ fontSize: '0.8rem', marginTop: 4 }}>{it.counterpart_profile.about}</div>
                      )}
                    </>
                  ) : (
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Profile no longer available</span>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span style={{
                    fontSize: '0.72rem', padding: '3px 9px', borderRadius: 10, textTransform: 'capitalize',
                    background: it.status === 'accepted' ? '#E8F5E9' : it.status === 'pending' ? '#FFF3E0' : '#F5F5F5',
                    color: it.status === 'accepted' ? '#2E7D32' : it.status === 'pending' ? '#E65100' : 'var(--text-muted)',
                  }}>{it.status}</span>
                  {direction === 'received' && it.status === 'pending' && (
                    <>
                      <button className="btn btn-primary btn-sm" disabled={busyId === it.id} onClick={() => handleAction(it.id, 'accept')}>Accept</button>
                      <button className="btn btn-outline btn-sm" disabled={busyId === it.id} onClick={() => handleAction(it.id, 'decline')}>Decline</button>
                    </>
                  )}
                  {direction === 'sent' && it.status === 'pending' && (
                    <button className="btn btn-outline btn-sm" disabled={busyId === it.id} onClick={() => handleAction(it.id, 'withdraw')}>Withdraw</button>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Safety tab
// ---------------------------------------------------------------------------

const SafetyTab: React.FC = () => {
  const [blocks, setBlocks] = useState<UserBlock[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    kutumbAPI.getMyBlocks().then(setBlocks).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleUnblock = async (blockedUserId: string) => {
    setBusyId(blockedUserId);
    try {
      await kutumbAPI.unblockUser(blockedUserId);
      await load();
    } catch { /* ignore */ }
    setBusyId(null);
  };

  return (
    <div style={{ maxWidth: 600 }}>
      <Card>
        <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Shield size={16} /> Users You've Blocked
        </h4>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 14 }}>
          A block is immediate and mutual &mdash; blocked profiles can't see or contact you either, anywhere in Kutumb Network.
        </p>
        {loading ? (
          <div className="skeleton" style={{ height: 60 }} />
        ) : blocks.length === 0 ? (
          <div className="empty-state">You haven't blocked anyone.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {blocks.map(b => (
              <div key={b.id} style={{ background: 'var(--bg-body)', padding: '10px 14px', borderRadius: 8, fontSize: '0.82rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Ban size={14} color="#C62828" /> Blocked user &middot; {new Date(b.created_at).toLocaleDateString()}
                </span>
                <button className="btn btn-outline btn-sm" disabled={busyId === b.blocked_user_id} onClick={() => handleUnblock(b.blocked_user_id)}>
                  Unblock
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};
