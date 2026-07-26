import React, { useState } from 'react';
import { marketAPI, aiAPI } from '../../api/client';
import { Sprout, X, AlertCircle, CheckCircle, ImageIcon, Sparkles, RefreshCw, ZoomIn } from 'lucide-react';

type ImageVariant = { url: string; style: 'studio' | 'lifestyle' };

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  agriCategoryId: string | null;
}

const UNITS = ['kg', 'quintal', 'ton', 'dozen', 'piece'] as const;
const GRADES = [
  { value: 'A', label: 'Grade A (Premium)' },
  { value: 'B', label: 'Grade B (Standard)' },
  { value: 'C', label: 'Grade C (Economy)' },
];
const VARIANT_STYLES: Array<'studio' | 'lifestyle'> = ['studio', 'lifestyle'];

export const PublishAgriModal: React.FC<Props> = ({ isOpen, onClose, onSuccess, agriCategoryId }) => {
  const [title, setTitle] = useState('');
  const [cropType, setCropType] = useState('');
  const [unit, setUnit] = useState<typeof UNITS[number]>('kg');
  const [priceInr, setPriceInr] = useState('');
  const [quantity, setQuantity] = useState('100');
  const [isOrganic, setIsOrganic] = useState(false);
  const [harvestDate, setHarvestDate] = useState('');
  const [grade, setGrade] = useState('A');
  const [description, setDescription] = useState('');

  const [primaryImage, setPrimaryImage] = useState('');
  const [imageVariants, setImageVariants] = useState<ImageVariant[]>([]);
  const [imageGenerating, setImageGenerating] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [regeneratingIndex, setRegeneratingIndex] = useState<number | null>(null);
  const [viewingImage, setViewingImage] = useState<string | null>(null);

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
        setPrimaryImage(res.url);
        setNotice('Photo uploaded.');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to upload image.');
    }
    setUploadingImage(false);
  };

  const handleAiGenerateImages = async () => {
    if (!primaryImage) {
      setError('Please upload a primary photo first.');
      return;
    }
    setImageGenerating(true);
    setError('');
    try {
      const res = await aiAPI.generateImages(primaryImage, title || cropType || 'Farm Produce', 'Agriculture', description);
      const urls: string[] = res.generated_variants || [];
      setImageVariants(urls.map((url, i) => ({ url, style: VARIANT_STYLES[i] || 'studio' })));
      setNotice('AI generated 2 high-quality showcase photos!');
    } catch (e: any) {
      setError(e.message || 'Image generation failed');
    }
    setImageGenerating(false);
  };

  const handleRegenerateVariant = async (index: number) => {
    const variant = imageVariants[index];
    if (!primaryImage || !variant) return;
    setRegeneratingIndex(index);
    setError('');
    try {
      const res = await aiAPI.regenerateImage(primaryImage, title || cropType || 'Farm Produce', variant.style, 'Agriculture', description);
      if (res.url) {
        setImageVariants(prev => prev.map((v, i) => (i === index ? { ...v, url: res.url } : v)));
        setNotice('Regenerated that photo!');
      }
    } catch (e: any) {
      setError(e.message || 'Regeneration failed');
    }
    setRegeneratingIndex(null);
  };

  const handleRemovePrimaryImage = () => setPrimaryImage('');
  const handleRemoveVariant = (index: number) => setImageVariants(prev => prev.filter((_, i) => i !== index));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !priceInr) {
      setError('Please fill in the produce title and price.');
      return;
    }
    if (!agriCategoryId) {
      setError('The "Agriculture" category isn\'t available right now — please try again shortly.');
      return;
    }
    const priceValue = Math.round(parseFloat(priceInr) * 100);
    if (isNaN(priceValue) || priceValue <= 0) {
      setError('Please enter a valid price per unit.');
      return;
    }

    setSubmitting(true);
    setError('');
    try {
      const mediaUrls: string[] = [];
      if (primaryImage) mediaUrls.push(primaryImage);
      imageVariants.forEach(v => { if (v?.url) mediaUrls.push(v.url); });

      await marketAPI.createAgriListing({
        pillar: 'marketplace',
        category_id: agriCategoryId,
        title: title.slice(0, 150),
        description: (description || 'Farm produce listed on Samuday marketplace.').slice(0, 10000),
        price: priceValue,
        unit,
        quantity: parseInt(quantity) || 1,
        crop_type: cropType || undefined,
        is_organic: isOrganic,
        harvest_date: harvestDate || undefined,
        grade,
        media_urls: mediaUrls,
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err.message || 'Failed to publish produce listing';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    setSubmitting(false);
  };

  return (
    <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1100 }}>
      <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: 700, maxHeight: '90vh', overflowY: 'auto', padding: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sprout size={22} color="var(--primary)" /> List Farm Produce
          </h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X size={20} /></button>
        </div>

        {error && <div className="alert alert-error" style={{ marginBottom: 16 }}><AlertCircle size={16} /> {error}</div>}
        {notice && <div className="alert alert-success" style={{ marginBottom: 16 }}><CheckCircle size={16} /> {notice}</div>}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="form-group">
            <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Produce Title *</label>
            <input value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g., Organic Sharbati Wheat - Fresh Harvest" required />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Crop Type</label>
              <input value={cropType} onChange={e => setCropType(e.target.value)} placeholder="e.g., Wheat, Basmati Rice, Cotton" />
            </div>
            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Quality Grade</label>
              <select value={grade} onChange={e => setGrade(e.target.value)}>
                {GRADES.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Price per Unit (₹) *</label>
              <input type="number" value={priceInr} onChange={e => setPriceInr(e.target.value)} placeholder="2200" required min="1" />
            </div>
            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Unit</label>
              <select value={unit} onChange={e => setUnit(e.target.value as typeof UNITS[number])}>
                {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Quantity Available</label>
              <input type="number" value={quantity} onChange={e => setQuantity(e.target.value)} min="1" />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, alignItems: 'end' }}>
            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Harvest Date</label>
              <input type="date" value={harvestDate} onChange={e => setHarvestDate(e.target.value)} />
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600, fontSize: '0.85rem', paddingBottom: 10, cursor: 'pointer' }}>
              <input type="checkbox" checked={isOrganic} onChange={e => setIsOrganic(e.target.checked)} />
              Certified Organic
            </label>
          </div>

          <div className="form-group">
            <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Description & Details</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} rows={4} placeholder="Growing conditions, farm location, freshness, packaging..." />
          </div>

          <div style={{ background: 'var(--bg-body)', padding: 16, borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)' }}>
            <label style={{ fontWeight: 600, fontSize: '0.88rem', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
              <ImageIcon size={16} color="var(--primary)" /> Produce Photo
            </label>
            <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
              <input type="file" accept="image/*" onChange={handleImageUpload} disabled={uploadingImage} style={{ flex: 1 }} />
              <button
                type="button"
                className="btn btn-accent"
                onClick={handleAiGenerateImages}
                disabled={imageGenerating || !primaryImage || uploadingImage}
                style={{ whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: 6 }}
              >
                <Sparkles size={16} /> {imageGenerating ? 'Generating...' : 'AI Generate 2 Variant Photos'}
              </button>
            </div>

            <div style={{ display: 'flex', gap: 14, overflowX: 'auto', paddingTop: 4, paddingBottom: 4 }}>
              {primaryImage && (
                <div style={{ position: 'relative', flexShrink: 0 }}>
                  <img
                    src={primaryImage}
                    alt="Primary"
                    onClick={() => setViewingImage(primaryImage)}
                    style={{ width: 84, height: 84, objectFit: 'cover', borderRadius: 6, border: '2px solid var(--primary)', cursor: 'zoom-in' }}
                  />
                  <span style={{ position: 'absolute', bottom: 4, left: 4, background: 'var(--primary)', color: '#fff', fontSize: '0.65rem', padding: '1px 4px', borderRadius: 3 }}>Main</span>
                  <button
                    type="button"
                    onClick={handleRemovePrimaryImage}
                    title="Remove image"
                    style={{ position: 'absolute', top: -7, right: -7, width: 20, height: 20, borderRadius: '50%', background: 'var(--danger)', color: '#fff', border: '2px solid var(--bg-white)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', padding: 0 }}
                  >
                    <X size={12} />
                  </button>
                </div>
              )}
              {imageVariants.map((variant, i) => (
                <div key={i} style={{ position: 'relative', flexShrink: 0 }}>
                  <img
                    src={variant.url}
                    alt={`AI Variant ${i + 1}`}
                    onClick={() => setViewingImage(variant.url)}
                    style={{ width: 84, height: 84, objectFit: 'cover', borderRadius: 6, border: '1px solid var(--border-card)', cursor: 'zoom-in', opacity: regeneratingIndex === i ? 0.4 : 1, transition: 'opacity 0.2s' }}
                  />
                  <span style={{ position: 'absolute', bottom: 4, left: 4, background: 'var(--accent)', color: '#fff', fontSize: '0.65rem', padding: '1px 4px', borderRadius: 3 }}>
                    AI · {variant.style === 'studio' ? 'Studio' : 'Lifestyle'}
                  </span>
                  <button
                    type="button"
                    onClick={() => setViewingImage(variant.url)}
                    title="View full image"
                    style={{ position: 'absolute', top: -7, left: -7, width: 20, height: 20, borderRadius: '50%', background: 'var(--bg-white)', color: 'var(--text-primary)', border: '1px solid var(--border-card)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', padding: 0 }}
                  >
                    <ZoomIn size={11} />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRemoveVariant(i)}
                    title="Remove image"
                    style={{ position: 'absolute', top: -7, right: -7, width: 20, height: 20, borderRadius: '50%', background: 'var(--danger)', color: '#fff', border: '2px solid var(--bg-white)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', padding: 0 }}
                  >
                    <X size={12} />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRegenerateVariant(i)}
                    disabled={regeneratingIndex !== null || !primaryImage}
                    title="Regenerate this photo"
                    style={{ position: 'absolute', bottom: -7, right: -7, width: 22, height: 22, borderRadius: '50%', background: 'var(--bg-white)', color: 'var(--primary)', border: '1px solid var(--border-card)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: regeneratingIndex !== null ? 'default' : 'pointer', padding: 0 }}
                  >
                    <RefreshCw size={12} className={regeneratingIndex === i ? 'animate-pulse' : ''} />
                  </button>
                </div>
              ))}
            </div>
            {(primaryImage || imageVariants.length > 0) && (
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Click any photo to view it full-size. Use ↻ to regenerate an AI photo, or ✕ to remove one.</span>
            )}
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 12 }}>
            <button type="button" className="btn btn-outline" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Publishing...' : 'Publish Produce Listing'}
            </button>
          </div>
        </form>

        {viewingImage && (
          <div
            onClick={() => setViewingImage(null)}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)', zIndex: 1300, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}
          >
            <button
              type="button"
              onClick={() => setViewingImage(null)}
              style={{ position: 'absolute', top: 20, right: 20, background: 'rgba(255,255,255,0.15)', border: 'none', color: '#fff', borderRadius: '50%', width: 36, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}
            >
              <X size={20} />
            </button>
            <img
              src={viewingImage}
              alt="Full view"
              onClick={e => e.stopPropagation()}
              style={{ maxWidth: '92vw', maxHeight: '92vh', objectFit: 'contain', borderRadius: 8 }}
            />
          </div>
        )}
      </div>
    </div>
  );
};
