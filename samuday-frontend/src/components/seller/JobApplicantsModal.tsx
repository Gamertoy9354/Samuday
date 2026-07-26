import React, { useEffect, useState } from 'react';
import { marketAPI } from '../../api/client';
import { X, Users, Phone, MessageSquare } from 'lucide-react';

interface Props {
  listingId: string | null;
  listingTitle: string;
  onClose: () => void;
}

export const JobApplicantsModal: React.FC<Props> = ({ listingId, listingTitle, onClose }) => {
  const [applicants, setApplicants] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!listingId) return;
    setLoading(true);
    setError('');
    marketAPI.getJobApplications(listingId)
      .then(setApplicants)
      .catch((e: any) => setError(e.message || 'Failed to load applicants'))
      .finally(() => setLoading(false));
  }, [listingId]);

  if (!listingId) return null;

  return (
    <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1150 }}>
      <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: 560, maxHeight: '85vh', overflowY: 'auto', padding: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Users size={20} color="var(--primary)" /> Applicants for "{listingTitle}"
          </h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X size={20} /></button>
        </div>

        {loading && <div className="skeleton" style={{ height: 80 }} />}
        {error && <div className="alert alert-error">{error}</div>}

        {!loading && !error && applicants.length === 0 && (
          <div className="empty-state">
            <Users size={40} />
            <h3>No applicants yet</h3>
            <p>People who apply to this job will show up here.</p>
          </div>
        )}

        {!loading && applicants.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {applicants.map((a: any) => (
              <div key={a.id} style={{ border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', padding: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: a.message ? 8 : 0 }}>
                  <span style={{ fontWeight: 600, fontSize: '0.92rem' }}>{a.applicant_name || 'Applicant'}</span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{new Date(a.applied_at).toLocaleDateString('en-IN')}</span>
                </div>
                {a.applicant_phone && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: a.message ? 6 : 0 }}>
                    <Phone size={13} /> {a.applicant_phone}
                  </div>
                )}
                {a.message && (
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 6, fontSize: '0.85rem', color: 'var(--text-primary)', background: 'var(--bg-body)', borderRadius: 6, padding: 10 }}>
                    <MessageSquare size={13} style={{ marginTop: 2, flexShrink: 0 }} /> <span>{a.message}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
