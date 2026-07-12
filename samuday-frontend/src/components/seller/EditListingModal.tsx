import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { marketAPI } from '../../api/client';
import { X, Plus, Trash2, ExternalLink, Save } from 'lucide-react';

interface Props {
  listingId: string | null;
  onClose: () => void;
  onSaved: () => void;
}

export const EditListingModal: React.FC<Props> = ({ listingId, onClose, onSaved }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priceInr, setPriceInr] = useState('');
  const [quantity, setQuantity] = useState('');
  const [offers, setOffers] = useState<string[]>([]);
  const [newOffer, setNewOffer] = useState('');
  const [returnPolicy, setReturnPolicy] = useState('');

  useEffect(() => {
    if (!listingId) return;
    setLoading(true);
    setError('');
    marketAPI.getListing(listingId).then(l => {
      setTitle(l.title);
      setDescription(l.description || '');
      setPriceInr((l.price / 100).toString());
      setQuantity(String(l.quantity));
      setOffers(l.available_offers || []);
      setReturnPolicy(l.return_policy || '');
    }).catch(() => setError('Failed to load listing')).finally(() => setLoading(false));
  }, [listingId]);

  if (!listingId) return null;

  const applyBold = () => setDescription(prev => prev + '**bold text**');
  const applyBullet = () => setDescription(prev => (prev ? prev + '\n' : '') + '- ');
  const applyHeading = () => setDescription(prev => (prev ? prev + '\n' : '') + '### Heading\n');

  const addOffer = () => {
    if (!newOffer.trim()) return;
    setOffers(prev => [...prev, newOffer.trim()]);
    setNewOffer('');
  };
  const removeOffer = (i: number) => setOffers(prev => prev.filter((_, idx) => idx !== i));

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const priceValue = Math.round(parseFloat(priceInr) * 100);
      const quantityValue = parseInt(quantity);
      await marketAPI.updateListing(listingId, {
        title,
        description,
        price: isNaN(priceValue) ? undefined : priceValue,
        quantity: isNaN(quantityValue) ? undefined : quantityValue,
        available_offers: offers,
        return_policy: returnPolicy || null,
      });
      onSaved();
      onClose();
    } catch (e: any) {
      setError(e.message || 'Failed to save changes');
    }
    setSaving(false);
  };

  return (
    <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1100 }}>
      <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: 700, maxHeight: '90vh', overflowY: 'auto', padding: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Edit Listing</h3>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <button type="button" className="btn btn-outline btn-sm" onClick={() => navigate(`/product/${listingId}`)} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <ExternalLink size={14} /> View Listing
            </button>
            <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X size={20} /></button>
          </div>
        </div>

        {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

        {loading ? (
          <div className="skeleton" style={{ height: 200 }} />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Product Title</label>
              <input value={title} onChange={e => setTitle(e.target.value)} />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Price (₹)</label>
                <input type="number" value={priceInr} onChange={e => setPriceInr(e.target.value)} min="1" />
              </div>
              <div className="form-group">
                <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Stock Quantity</label>
                <input type="number" value={quantity} onChange={e => setQuantity(e.target.value)} min="0" />
              </div>
            </div>

            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Description</label>
              <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
                <button type="button" className="btn btn-outline btn-sm" onClick={applyHeading}>Heading</button>
                <button type="button" className="btn btn-outline btn-sm" onClick={applyBold}>Bold</button>
                <button type="button" className="btn btn-outline btn-sm" onClick={applyBullet}>Bullet</button>
              </div>
              <textarea value={description} onChange={e => setDescription(e.target.value)} rows={7} placeholder="### Heading&#10;**Bold text**&#10;- Bullet point" />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Supports ### headings, **bold**, and - bullet points — shown formatted on the product page.</span>
            </div>

            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Available Offers</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 8 }}>
                {offers.map((o, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--bg-body)', padding: '6px 10px', borderRadius: 6 }}>
                    <span style={{ flex: 1, fontSize: '0.85rem' }}>{o}</span>
                    <button type="button" onClick={() => removeOffer(i)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--danger)' }}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  value={newOffer}
                  onChange={e => setNewOffer(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addOffer(); } }}
                  placeholder="e.g. Bank Offer: 10% off on SBI Credit Cards"
                  style={{ flex: 1 }}
                />
                <button type="button" className="btn btn-outline btn-sm" onClick={addOffer} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Plus size={14} /> Add
                </button>
              </div>
            </div>

            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Return Policy</label>
              <textarea value={returnPolicy} onChange={e => setReturnPolicy(e.target.value)} rows={3} placeholder="e.g. 7-day easy returns if item is unused and in original packaging." />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 8 }}>
              <button type="button" className="btn btn-outline" onClick={onClose}>Cancel</button>
              <button type="button" className="btn btn-primary" onClick={handleSave} disabled={saving} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Save size={16} /> {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
