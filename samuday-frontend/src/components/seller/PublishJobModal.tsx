import React, { useState } from 'react';
import { marketAPI } from '../../api/client';
import { Briefcase, X, AlertCircle, CheckCircle, ImageIcon } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  jobsCategoryId: string | null;
}

const JOB_TYPES = ['full-time', 'part-time', 'contract', 'internship', 'gig'] as const;
const SALARY_PERIODS = ['monthly', 'yearly', 'hourly'] as const;

export const PublishJobModal: React.FC<Props> = ({ isOpen, onClose, onSuccess, jobsCategoryId }) => {
  const [title, setTitle] = useState('');
  const [jobType, setJobType] = useState<typeof JOB_TYPES[number]>('full-time');
  const [salaryMin, setSalaryMin] = useState('');
  const [salaryMax, setSalaryMax] = useState('');
  const [salaryPeriod, setSalaryPeriod] = useState<typeof SALARY_PERIODS[number]>('monthly');
  const [experienceRequired, setExperienceRequired] = useState('');
  const [openings, setOpenings] = useState('1');
  const [applicationDeadline, setApplicationDeadline] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [description, setDescription] = useState('');
  const [image, setImage] = useState('');
  const [uploadingImage, setUploadingImage] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  if (!isOpen) return null;

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingImage(true);
    setError('');
    try {
      const res = await marketAPI.uploadImage(file);
      if (res.url) {
        setImage(res.url);
        setNotice('Photo uploaded.');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to upload image.');
    }
    setUploadingImage(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !description) {
      setError('Please fill in the job title and description.');
      return;
    }
    if (!jobsCategoryId) {
      setError('The "Jobs" category isn\'t available right now — please try again shortly.');
      return;
    }
    const min = salaryMin ? Math.round(parseFloat(salaryMin) * 100) : undefined;
    const max = salaryMax ? Math.round(parseFloat(salaryMax) * 100) : undefined;
    if (min !== undefined && max !== undefined && min > max) {
      setError('Minimum salary cannot be greater than maximum salary.');
      return;
    }

    setSubmitting(true);
    setError('');
    try {
      await marketAPI.createJobListing({
        pillar: 'marketplace',
        category_id: jobsCategoryId,
        title: title.slice(0, 150),
        description: description.slice(0, 10000),
        job_type: jobType,
        salary_min: min,
        salary_max: max,
        salary_period: salaryPeriod,
        experience_required: experienceRequired || undefined,
        quantity: parseInt(openings) || 1,
        application_deadline: applicationDeadline ? new Date(applicationDeadline).toISOString() : undefined,
        contact_email: contactEmail || undefined,
        media_urls: image ? [image] : [],
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err.message || 'Failed to publish job listing';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    setSubmitting(false);
  };

  return (
    <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1100 }}>
      <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: 640, maxHeight: '90vh', overflowY: 'auto', padding: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Briefcase size={22} color="var(--primary)" /> Post a Job
          </h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X size={20} /></button>
        </div>

        {error && <div className="alert alert-error" style={{ marginBottom: 16 }}><AlertCircle size={16} /> {error}</div>}
        {notice && <div className="alert alert-success" style={{ marginBottom: 16 }}><CheckCircle size={16} /> {notice}</div>}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="form-group">
            <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Job Title *</label>
            <input value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g., Retail Store Sales Assistant" required />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Job Type *</label>
              <select value={jobType} onChange={e => setJobType(e.target.value as typeof JOB_TYPES[number])} required>
                {JOB_TYPES.map(t => <option key={t} value={t}>{t.replace('-', ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Openings</label>
              <input type="number" value={openings} onChange={e => setOpenings(e.target.value)} min="1" />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Salary Min (₹)</label>
              <input type="number" value={salaryMin} onChange={e => setSalaryMin(e.target.value)} placeholder="15000" min="0" />
            </div>
            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Salary Max (₹)</label>
              <input type="number" value={salaryMax} onChange={e => setSalaryMax(e.target.value)} placeholder="25000" min="0" />
            </div>
            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Per</label>
              <select value={salaryPeriod} onChange={e => setSalaryPeriod(e.target.value as typeof SALARY_PERIODS[number])}>
                {SALARY_PERIODS.map(p => <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
              </select>
            </div>
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: -8 }}>Leave salary blank if you'd rather discuss pay with applicants directly.</span>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Experience Required</label>
              <input value={experienceRequired} onChange={e => setExperienceRequired(e.target.value)} placeholder="e.g., 1-3 years, Freshers welcome" />
            </div>
            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Application Deadline</label>
              <input type="date" value={applicationDeadline} onChange={e => setApplicationDeadline(e.target.value)} />
            </div>
          </div>

          <div className="form-group">
            <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Contact Email (optional)</label>
            <input type="email" value={contactEmail} onChange={e => setContactEmail(e.target.value)} placeholder="hr@yourbusiness.com" />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Applicants can also be reviewed from your Seller Dashboard.</span>
          </div>

          <div className="form-group">
            <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Job Description & Requirements *</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} rows={5} placeholder="Role responsibilities, required skills, work timings, location..." required />
          </div>

          <div className="form-group">
            <label style={{ fontWeight: 600, fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: 6 }}>
              <ImageIcon size={14} /> Photo (optional — office, team, or logo)
            </label>
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <input type="file" accept="image/*" onChange={handleImageUpload} disabled={uploadingImage} />
              {image && <img src={image} alt="" style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: 6 }} />}
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 12 }}>
            <button type="button" className="btn btn-outline" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Publishing...' : 'Post Job Listing'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
