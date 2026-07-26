import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { adminAPI, verificationAPI, kutumbAPI } from '../api/client';
import {
  LayoutDashboard, Users, Package, IndianRupee, ShieldCheck, CheckCircle2, XCircle,
  Building2, UserCheck, Clock, Heart, AlertTriangle, Ban
} from 'lucide-react';

export const AdminDashboard: React.FC = () => {
  const { user } = useAuth();
  const [tab, setTab] = useState<'overview' | 'verifications' | 'sellers' | 'listings' | 'kutumb'>('overview');
  const [overview, setOverview] = useState<any>(null);
  const [pendingOfficial, setPendingOfficial] = useState<any[]>([]);
  const [pendingLocal, setPendingLocal] = useState<any[]>([]);
  const [sellers, setSellers] = useState<any[]>([]);
  const [listings, setListings] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [reportStatusFilter, setReportStatusFilter] = useState('open');
  const [loading, setLoading] = useState(true);
  const [actingId, setActingId] = useState<string | null>(null);

  const loadAll = async () => {
    setLoading(true);
    const [ov, po, pl, sl, li, rp] = await Promise.allSettled([
      adminAPI.getOverview(),
      verificationAPI.listPendingOfficial(),
      verificationAPI.listPendingLocal(),
      adminAPI.listSellers(),
      adminAPI.listListings(50),
      kutumbAPI.adminListReports(reportStatusFilter || undefined),
    ]);
    if (ov.status === 'fulfilled') setOverview(ov.value);
    if (po.status === 'fulfilled') setPendingOfficial(po.value);
    if (pl.status === 'fulfilled') setPendingLocal(pl.value);
    if (sl.status === 'fulfilled') setSellers(sl.value);
    if (li.status === 'fulfilled') setListings(li.value);
    if (rp.status === 'fulfilled') setReports(rp.value);
    setLoading(false);
  };

  const handleResolveReport = async (reportId: string, action: string) => {
    setActingId(reportId);
    try {
      await kutumbAPI.adminResolveReport(reportId, action);
      await loadAll();
    } catch { /* ignore */ }
    setActingId(null);
  };

  useEffect(() => {
    if (user?.is_admin) loadAll();
    else setLoading(false);
  }, [user, reportStatusFilter]);

  const handleApproveOfficial = async (id: string) => {
    setActingId(id);
    try { await verificationAPI.approveOfficial(id); await loadAll(); } catch { /* ignore */ }
    setActingId(null);
  };
  const handleRejectOfficial = async (id: string) => {
    const reason = prompt('Rejection reason (optional):') || undefined;
    setActingId(id);
    try { await verificationAPI.rejectOfficial(id, reason); await loadAll(); } catch { /* ignore */ }
    setActingId(null);
  };
  const handleApproveLocal = async (id: string) => {
    setActingId(id);
    try { await verificationAPI.approveLocal(id); await loadAll(); } catch { /* ignore */ }
    setActingId(null);
  };
  const handleRejectLocal = async (id: string) => {
    const reason = prompt('Rejection reason (optional):') || undefined;
    setActingId(id);
    try { await verificationAPI.rejectLocal(id, reason); await loadAll(); } catch { /* ignore */ }
    setActingId(null);
  };

  if (!user) {
    return <div className="page-content" style={{ paddingTop: 32 }}><div className="empty-state"><h3>Please login</h3></div></div>;
  }
  if (!user.is_admin) {
    return (
      <div className="page-content" style={{ paddingTop: 32 }}>
        <div className="empty-state">
          <ShieldCheck size={64} />
          <h3>Admin Access Required</h3>
          <p>This dashboard is only available to platform administrators.</p>
        </div>
      </div>
    );
  }
  if (loading) {
    return <div className="page-content" style={{ paddingTop: 16 }}><div className="skeleton" style={{ height: 400 }} /></div>;
  }

  const pendingCount = pendingOfficial.length + pendingLocal.length;

  return (
    <div className="page-content" style={{ paddingTop: 16 }}>
      <h2 style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: 4 }}>Samuday Platform Admin</h2>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: 16 }}>Manage sellers, verifications, listings, and platform revenue</p>

      <div className="dashboard-tabs">
        <button className={`dashboard-tab ${tab === 'overview' ? 'active' : ''}`} onClick={() => setTab('overview')}>
          <LayoutDashboard size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> Overview
        </button>
        <button className={`dashboard-tab ${tab === 'verifications' ? 'active' : ''}`} onClick={() => setTab('verifications')}>
          <ShieldCheck size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> Verifications ({pendingCount})
        </button>
        <button className={`dashboard-tab ${tab === 'sellers' ? 'active' : ''}`} onClick={() => setTab('sellers')}>
          <Users size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> Sellers ({sellers.length})
        </button>
        <button className={`dashboard-tab ${tab === 'listings' ? 'active' : ''}`} onClick={() => setTab('listings')}>
          <Package size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> Listings ({listings.length})
        </button>
        <button className={`dashboard-tab ${tab === 'kutumb' ? 'active' : ''}`} onClick={() => setTab('kutumb')}>
          <Heart size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> Kutumb Safety ({reports.length})
        </button>
      </div>

      {tab === 'overview' && overview && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 20 }}>
            {[
              { label: 'Total Users', value: overview.total_users, color: 'var(--primary)' },
              { label: 'Total Sellers', value: overview.total_sellers, color: 'var(--accent)' },
              { label: 'Active Listings', value: overview.active_listings, color: 'var(--success)' },
              { label: 'Completed Orders', value: overview.completed_orders, color: '#00A8E8' },
            ].map(stat => (
              <div key={stat.label} style={{ background: 'var(--bg-white)', padding: 20, borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', textAlign: 'center' }}>
                <div style={{ fontSize: '2rem', fontWeight: 700, color: stat.color }}>{stat.value}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{stat.label}</div>
              </div>
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 20 }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
                <IndianRupee size={18} color="var(--primary)" /> Platform Revenue
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>GMV (completed orders)</span>
                  <strong>&#8377;{(overview.gmv_paise / 100).toLocaleString('en-IN')}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>Platform Fee Revenue</span>
                  <strong style={{ color: 'var(--success)' }}>&#8377;{(overview.platform_fee_revenue_paise / 100).toLocaleString('en-IN')}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>Delivery Fees Collected (pass-through)</span>
                  <strong>&#8377;{(overview.delivery_fee_collected_paise / 100).toLocaleString('en-IN')}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px dashed var(--border-light)', paddingTop: 10 }}>
                  <span style={{ fontWeight: 600 }}>House Wallet Balance</span>
                  <strong>&#8377;{(overview.platform_house_balance_paise / 100).toLocaleString('en-IN')}</strong>
                </div>
              </div>
            </div>

            <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 20 }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
                <Users size={18} color="var(--accent)" /> Seller Breakdown
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.88rem' }}><Building2 size={14} /> Official Business</span>
                  <strong>{overview.official_sellers}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.88rem' }}><UserCheck size={14} /> Local Marketplace</span>
                  <strong>{overview.local_sellers}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.88rem' }}><Clock size={14} /> Pending Verification</span>
                  <strong style={{ color: overview.pending_verifications > 0 ? 'var(--accent-dark)' : 'inherit' }}>{overview.pending_verifications}</strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === 'verifications' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 20 }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Building2 size={18} /> Official Business Verifications ({pendingOfficial.length})
            </h3>
            {pendingOfficial.length === 0 ? <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>No pending submissions.</p> : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {pendingOfficial.map((p: any) => (
                  <div key={p.id} style={{ border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', padding: 14 }}>
                    <div style={{ fontWeight: 600 }}>{p.business_name}</div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                      GSTIN: {p.gstin} {p.pan && `· PAN: ${p.pan}`} {p.business_phone && `· ${p.business_phone}`}
                    </div>
                    {p.business_address && <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{p.business_address} - {p.pincode}</div>}
                    {p.gst_certificate_url && (
                      <a href={p.gst_certificate_url} target="_blank" rel="noreferrer" style={{ fontSize: '0.8rem', color: 'var(--primary)', display: 'inline-block', marginTop: 6 }}>
                        View GST Certificate
                      </a>
                    )}
                    <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                      <button className="btn btn-primary btn-sm" onClick={() => handleApproveOfficial(p.id)} disabled={actingId === p.id} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <CheckCircle2 size={14} /> Approve
                      </button>
                      <button className="btn btn-outline btn-sm" onClick={() => handleRejectOfficial(p.id)} disabled={actingId === p.id} style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--danger)' }}>
                        <XCircle size={14} /> Reject
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 20 }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
              <UserCheck size={18} /> Identity (KYC) Verifications ({pendingLocal.length})
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: -8, marginBottom: 14 }}>
              Includes local-seller applications and individual identity checks (e.g. Kutumb matrimonial opt-in).
            </p>
            {pendingLocal.length === 0 ? <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>No pending submissions.</p> : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {pendingLocal.map((k: any) => (
                  <div key={k.id} style={{ display: 'flex', alignItems: 'center', gap: 14, border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', padding: 14 }}>
                    <a href={k.document_url} target="_blank" rel="noreferrer">
                      <img src={k.document_url} alt="ID document" style={{ width: 70, height: 70, objectFit: 'cover', borderRadius: 6, border: '1px solid var(--border-light)' }} />
                    </a>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
                        {k.applicant_name}
                        <span style={{ fontSize: '0.68rem', fontWeight: 600, padding: '2px 8px', borderRadius: 10, background: k.applicant_context === 'Local Seller Application' ? 'var(--bg-hover)' : '#EDE7F6', color: k.applicant_context === 'Local Seller Application' ? 'var(--text-primary)' : '#5E35B1' }}>
                          {k.applicant_context}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                        {k.id_type.toUpperCase()} {k.applicant_phone && `· ${k.applicant_phone}`}
                      </div>
                      {k.gstin && (
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          GSTIN: {k.gstin}
                          {k.gst_certificate_url && (
                            <> · <a href={k.gst_certificate_url} target="_blank" rel="noreferrer" style={{ color: 'var(--primary)' }}>View GST Certificate</a></>
                          )}
                        </div>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button className="btn btn-primary btn-sm" onClick={() => handleApproveLocal(k.id)} disabled={actingId === k.id}>Approve</button>
                      <button className="btn btn-outline btn-sm" onClick={() => handleRejectLocal(k.id)} disabled={actingId === k.id} style={{ color: 'var(--danger)' }}>Reject</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'sellers' && (
        <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 20 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {sellers.map((s: any) => (
              <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: 12, border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600 }}>{s.full_name}</div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>{s.email || s.phone_number} · {s.listing_count} listings</div>
                </div>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '3px 8px', borderRadius: 10, background: 'var(--bg-hover)', textTransform: 'capitalize' }}>{s.seller_tier || 'no tier'}</span>
                <span style={{
                  fontSize: '0.75rem', fontWeight: 600, padding: '3px 8px', borderRadius: 10, textTransform: 'capitalize',
                  background: s.seller_verification_status === 'approved' ? 'var(--success-light)' : s.seller_verification_status === 'pending' ? 'var(--warning-light)' : 'var(--bg-hover)',
                  color: s.seller_verification_status === 'approved' ? '#15803d' : s.seller_verification_status === 'pending' ? '#92400e' : 'var(--text-muted)',
                }}>
                  {s.seller_verification_status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'listings' && (
        <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 20 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {listings.map((l: any) => (
              <div key={l.id} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: 12, border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600 }}>{l.title}</div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>by {l.seller_name || 'Unknown'} · &#8377;{(l.price / 100).toLocaleString('en-IN')} · Qty {l.quantity}</div>
                </div>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '3px 8px', borderRadius: 10, background: 'var(--success-light)', color: '#15803d', textTransform: 'capitalize' }}>{l.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'kutumb' && (
        <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Heart size={18} /> Matrimonial Reports
            </h3>
            <select value={reportStatusFilter} onChange={e => setReportStatusFilter(e.target.value)} style={{ maxWidth: 160 }}>
              <option value="">All statuses</option>
              <option value="open">Open</option>
              <option value="reviewing">Reviewing</option>
              <option value="actioned">Actioned</option>
              <option value="dismissed">Dismissed</option>
            </select>
          </div>

          {reports.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>No reports match this filter.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {reports.map((r: any) => (
                <div key={r.id} style={{ border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', padding: 14, background: r.reason_code === 'underage_suspicion' ? '#FFF5F5' : undefined }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                        <span style={{
                          fontSize: '0.72rem', fontWeight: 700, padding: '2px 9px', borderRadius: 10, textTransform: 'capitalize',
                          background: r.reason_code === 'underage_suspicion' ? '#FFEBEE' : 'var(--bg-hover)',
                          color: r.reason_code === 'underage_suspicion' ? '#C62828' : 'var(--text-primary)',
                        }}>
                          {r.reason_code === 'underage_suspicion' && <AlertTriangle size={11} style={{ verticalAlign: -1, marginRight: 3 }} />}
                          {r.reason_code.replace('_', ' ')}
                        </span>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Reported {r.report_count_against_user}x total</span>
                      </div>
                      <div style={{ fontSize: '0.82rem' }}>{r.details || <em style={{ color: 'var(--text-muted)' }}>No details provided</em>}</div>
                      <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: 4 }}>
                        Reported user profile: {r.reported_profile_status || 'no profile'}
                        {r.reported_profile_age_verified !== null && (r.reported_profile_age_verified ? ' · age-verified' : ' · NOT age-verified')}
                        {' · '}{new Date(r.created_at).toLocaleString()}
                      </div>
                    </div>
                    <span style={{ fontSize: '0.72rem', fontWeight: 600, padding: '3px 9px', borderRadius: 10, textTransform: 'capitalize', background: 'var(--bg-hover)' }}>{r.status}</span>
                  </div>
                  {r.status !== 'dismissed' && r.status !== 'actioned' && (
                    <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
                      <button className="btn btn-outline btn-sm" disabled={actingId === r.id} onClick={() => handleResolveReport(r.id, 'dismiss')}>Dismiss</button>
                      <button className="btn btn-primary btn-sm" disabled={actingId === r.id} onClick={() => handleResolveReport(r.id, 'suspend_profile')} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                        <Ban size={13} /> Suspend Profile
                      </button>
                      <button className="btn btn-outline btn-sm" disabled={actingId === r.id} onClick={() => handleResolveReport(r.id, 'remove_profile')} style={{ color: 'var(--danger)' }}>Remove Profile</button>
                    </div>
                  )}
                  {r.status === 'actioned' && r.resolution_action === 'suspend_profile' && (
                    <div style={{ marginTop: 10 }}>
                      <button className="btn btn-outline btn-sm" disabled={actingId === r.id} onClick={() => handleResolveReport(r.id, 'reinstate_profile')} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                        <CheckCircle2 size={13} /> Reinstate Profile
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
