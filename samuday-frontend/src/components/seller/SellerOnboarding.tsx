import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { authAPI, verificationAPI, marketAPI } from '../../api/client';
import { Building2, UserCheck, Clock, XCircle, Upload } from 'lucide-react';

export const SellerOnboarding: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Official tier form state
  const [businessName, setBusinessName] = useState('');
  const [gstin, setGstin] = useState('');
  const [pan, setPan] = useState('');
  const [businessPhone, setBusinessPhone] = useState('');
  const [businessAddress, setBusinessAddress] = useState('');
  const [pincode, setPincode] = useState('');

  // Local tier form state
  const [idType, setIdType] = useState<'aadhaar' | 'pan' | 'voter_id'>('aadhaar');
  const [docFile, setDocFile] = useState<File | null>(null);
  const [uploadingDoc, setUploadingDoc] = useState(false);

  if (!user) return null;

  const handleChooseTier = async (tier: 'official' | 'local') => {
    setSubmitting(true);
    setError('');
    try {
      await authAPI.updateProfile({ seller_tier: tier });
      await refreshUser();
    } catch (e: any) {
      setError(e.message || 'Failed to select seller tier');
    }
    setSubmitting(false);
  };

  const handleSubmitOfficial = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessName || gstin.length !== 15) {
      setError('Please enter a valid business name and 15-character GSTIN.');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      await verificationAPI.submitOfficialProfile({
        business_name: businessName,
        gstin,
        pan: pan || undefined,
        business_phone: businessPhone || undefined,
        business_address: businessAddress || undefined,
        pincode: pincode || undefined,
      });
      await refreshUser();
    } catch (e: any) {
      setError(e.message || 'Failed to submit business verification');
    }
    setSubmitting(false);
  };

  const handleUploadDoc = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setDocFile(file);
  };

  const handleSubmitLocal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!docFile) {
      setError('Please upload a photo of your ID document.');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      setUploadingDoc(true);
      const uploadRes = await marketAPI.uploadImage(docFile);
      setUploadingDoc(false);
      await verificationAPI.submitLocalKyc({ id_type: idType, document_url: uploadRes.url });
      await refreshUser();
    } catch (e: any) {
      setError(e.message || 'Failed to submit KYC document');
    }
    setSubmitting(false);
    setUploadingDoc(false);
  };

  // --- Screen: no tier chosen yet ---
  if (!user.seller_tier) {
    return (
      <div className="page-content" style={{ paddingTop: 32 }}>
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 28 }}>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: 8 }}>Start Selling on Samuday</h2>
            <p style={{ color: 'var(--text-secondary)' }}>Choose the seller type that fits you best</p>
          </div>
          {error && <div className="alert alert-error" style={{ maxWidth: 500, margin: '0 auto 16px' }}>{error}</div>}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            <div style={{ background: 'var(--bg-white)', border: '1px solid var(--border-card)', borderRadius: 'var(--radius-lg)', padding: 28, boxShadow: 'var(--shadow-card)' }}>
              <Building2 size={36} color="var(--primary)" style={{ marginBottom: 12 }} />
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: 8 }}>Official Business</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: 16, lineHeight: 1.6 }}>
                For registered businesses. Verify with your GSTIN and business details to sell on the main marketplace with full trust badges.
              </p>
              <button className="btn btn-primary btn-block" onClick={() => handleChooseTier('official')} disabled={submitting}>
                Register as Official Business
              </button>
            </div>
            <div style={{ background: 'var(--bg-white)', border: '1px solid var(--border-card)', borderRadius: 'var(--radius-lg)', padding: 28, boxShadow: 'var(--shadow-card)' }}>
              <UserCheck size={36} color="var(--accent)" style={{ marginBottom: 12 }} />
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: 8 }}>Local Marketplace Seller</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: 16, lineHeight: 1.6 }}>
                For small/informal local sellers. Verify your identity with a simple ID document (Aadhaar/PAN/Voter ID) — no business registration required.
              </p>
              <button className="btn btn-accent btn-block" onClick={() => handleChooseTier('local')} disabled={submitting}>
                Register as Local Seller
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // --- Screen: pending review ---
  if (user.seller_verification_status === 'pending') {
    return (
      <div className="page-content" style={{ paddingTop: 32 }}>
        <div style={{ maxWidth: 500, margin: '0 auto', textAlign: 'center', background: 'var(--bg-white)', padding: 40, borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-card)' }}>
          <Clock size={48} color="var(--accent)" style={{ marginBottom: 16 }} />
          <h2 style={{ marginBottom: 8, fontSize: '1.3rem' }}>Verification In Progress</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem' }}>
            Your {user.seller_tier === 'official' ? 'business' : 'identity'} verification is being reviewed by our team.
            You'll be able to publish listings as soon as it's approved.
          </p>
        </div>
      </div>
    );
  }

  // --- Screen: rejected — allow resubmission ---
  const rejected = user.seller_verification_status === 'rejected';

  // --- Screen: verification form (unverified or rejected) ---
  return (
    <div className="page-content" style={{ paddingTop: 32 }}>
      <div style={{ maxWidth: 560, margin: '0 auto' }}>
        {rejected && (
          <div className="alert alert-error" style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <XCircle size={16} /> Your previous submission was rejected. Please review and resubmit.
          </div>
        )}
        {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

        {user.seller_tier === 'official' ? (
          <div style={{ background: 'var(--bg-white)', border: '1px solid var(--border-card)', borderRadius: 'var(--radius-lg)', padding: 28 }}>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Building2 size={20} color="var(--primary)" /> Official Business Verification
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: 20 }}>Reviewed by our team, usually within 1-2 business days.</p>
            <form onSubmit={handleSubmitOfficial} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div className="form-group"><label>Business Name *</label><input value={businessName} onChange={e => setBusinessName(e.target.value)} required /></div>
              <div className="form-group"><label>GSTIN * (15 characters)</label><input value={gstin} onChange={e => setGstin(e.target.value.toUpperCase())} maxLength={15} required /></div>
              <div className="form-group"><label>PAN</label><input value={pan} onChange={e => setPan(e.target.value.toUpperCase())} maxLength={10} /></div>
              <div className="form-group"><label>Business Phone</label><input value={businessPhone} onChange={e => setBusinessPhone(e.target.value)} /></div>
              <div className="form-group"><label>Business Address</label><textarea value={businessAddress} onChange={e => setBusinessAddress(e.target.value)} rows={2} /></div>
              <div className="form-group"><label>Pincode</label><input value={pincode} onChange={e => setPincode(e.target.value)} maxLength={6} /></div>
              <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
                {submitting ? 'Submitting...' : 'Submit for Verification'}
              </button>
            </form>
          </div>
        ) : (
          <div style={{ background: 'var(--bg-white)', border: '1px solid var(--border-card)', borderRadius: 'var(--radius-lg)', padding: 28 }}>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
              <UserCheck size={20} color="var(--accent)" /> Local Seller Identity Verification
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: 20 }}>
              Upload a clear photo of one government ID. Reviewed by our team, usually within 1-2 business days.
            </p>
            <form onSubmit={handleSubmitLocal} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div className="form-group">
                <label>ID Type</label>
                <select value={idType} onChange={e => setIdType(e.target.value as any)}>
                  <option value="aadhaar">Aadhaar Card</option>
                  <option value="pan">PAN Card</option>
                  <option value="voter_id">Voter ID</option>
                </select>
              </div>
              <div className="form-group">
                <label>ID Document Photo</label>
                <input type="file" accept="image/*" onChange={handleUploadDoc} />
                {docFile && <span style={{ fontSize: '0.8rem', color: 'var(--success)', marginTop: 4 }}>Selected: {docFile.name}</span>}
              </div>
              <button type="submit" className="btn btn-accent btn-block" disabled={submitting || uploadingDoc}>
                <Upload size={16} style={{ marginRight: 6, verticalAlign: -3 }} />
                {uploadingDoc ? 'Uploading...' : submitting ? 'Submitting...' : 'Submit for Verification'}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
};
