import React, { useEffect, useState } from 'react';
import { marketAPI } from '../../api/client';
import { MapPin, Plus, Navigation, Trash2, Check } from 'lucide-react';

interface Address {
  id: string;
  label: string;
  recipient_name: string;
  phone: string;
  address_line1: string;
  address_line2?: string;
  city: string;
  state: string;
  pincode: string;
  is_default: boolean;
}

interface Props {
  selectedAddressId: string | null;
  onSelect: (address: Address | null) => void;
}

const emptyForm = {
  label: 'Home', recipient_name: '', phone: '', address_line1: '', address_line2: '',
  city: '', state: '', pincode: '', latitude: undefined as number | undefined, longitude: undefined as number | undefined,
};

export const AddressPicker: React.FC<Props> = ({ selectedAddressId, onSelect }) => {
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const data = await marketAPI.getAddresses();
      setAddresses(data);
      if (!selectedAddressId) {
        const def = data.find((a: Address) => a.is_default) || data[0];
        if (def) onSelect(def);
      }
    } catch {
      setAddresses([]);
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleUseMyLocation = () => {
    if (!navigator.geolocation) {
      setError('Your browser does not support location detection. Please enter your address manually.');
      return;
    }
    setLocating(true);
    setError('');
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const result = await marketAPI.reverseGeocode(pos.coords.latitude, pos.coords.longitude);
          setForm(f => ({
            ...f,
            address_line1: result.address_line1 || f.address_line1,
            city: result.city || f.city,
            state: result.state || f.state,
            pincode: result.pincode || f.pincode,
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
          }));
        } catch {
          setError('Could not resolve your location to an address. Please fill it in manually.');
        }
        setLocating(false);
      },
      () => {
        setError('Location access denied. You can still type your address manually below.');
        setLocating(false);
      },
      { timeout: 10000 }
    );
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const saved = await marketAPI.createAddress(form);
      setAddresses(prev => [saved, ...prev]);
      onSelect(saved);
      setShowForm(false);
      setForm(emptyForm);
    } catch (e: any) {
      setError(e.message || 'Failed to save address');
    }
    setSaving(false);
  };

  const handleDelete = async (id: string) => {
    try {
      await marketAPI.deleteAddress(id);
      setAddresses(prev => prev.filter(a => a.id !== id));
      if (selectedAddressId === id) onSelect(null);
    } catch { /* ignore */ }
  };

  if (loading) return <div className="skeleton" style={{ height: 80 }} />;

  return (
    <div>
      {error && <div className="alert alert-error" style={{ marginBottom: 10 }}>{error}</div>}

      {addresses.length > 0 && !showForm && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
          {addresses.map(addr => (
            <div
              key={addr.id}
              onClick={() => onSelect(addr)}
              style={{
                display: 'flex', alignItems: 'flex-start', gap: 10, padding: 12,
                border: `1.5px solid ${selectedAddressId === addr.id ? 'var(--primary)' : 'var(--border-light)'}`,
                borderRadius: 'var(--radius-sm)', cursor: 'pointer',
                background: selectedAddressId === addr.id ? 'var(--primary-light)' : 'var(--bg-white)',
              }}
            >
              <MapPin size={18} color={selectedAddressId === addr.id ? 'var(--primary)' : 'var(--text-muted)'} style={{ marginTop: 2, flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: '0.88rem', display: 'flex', alignItems: 'center', gap: 6 }}>
                  {addr.label} {selectedAddressId === addr.id && <Check size={14} color="var(--primary)" />}
                </div>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                  {addr.recipient_name}, {addr.address_line1}{addr.address_line2 ? `, ${addr.address_line2}` : ''}, {addr.city}, {addr.state} - {addr.pincode}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{addr.phone}</div>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); handleDelete(addr.id); }}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--danger)', padding: 4 }}
                title="Delete address"
              >
                <Trash2 size={15} />
              </button>
            </div>
          ))}
        </div>
      )}

      {!showForm ? (
        <button className="btn btn-outline btn-sm" onClick={() => setShowForm(true)} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Plus size={14} /> Add New Address
        </button>
      ) : (
        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: 14, background: 'var(--bg-hover)', borderRadius: 'var(--radius-sm)' }}>
          <button type="button" className="btn btn-outline btn-sm" onClick={handleUseMyLocation} disabled={locating} style={{ display: 'flex', alignItems: 'center', gap: 6, alignSelf: 'flex-start' }}>
            <Navigation size={14} /> {locating ? 'Detecting location...' : 'Use My Current Location'}
          </button>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <div className="form-group"><label>Full Name</label><input value={form.recipient_name} onChange={e => setForm({ ...form, recipient_name: e.target.value })} required /></div>
            <div className="form-group"><label>Phone</label><input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} required /></div>
          </div>
          <div className="form-group"><label>Address Line 1</label><input value={form.address_line1} onChange={e => setForm({ ...form, address_line1: e.target.value })} required /></div>
          <div className="form-group"><label>Address Line 2 (optional)</label><input value={form.address_line2} onChange={e => setForm({ ...form, address_line2: e.target.value })} /></div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
            <div className="form-group"><label>City</label><input value={form.city} onChange={e => setForm({ ...form, city: e.target.value })} required /></div>
            <div className="form-group"><label>State</label><input value={form.state} onChange={e => setForm({ ...form, state: e.target.value })} required /></div>
            <div className="form-group"><label>Pincode</label><input value={form.pincode} onChange={e => setForm({ ...form, pincode: e.target.value })} maxLength={6} required /></div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="submit" className="btn btn-primary btn-sm" disabled={saving}>{saving ? 'Saving...' : 'Save Address'}</button>
            <button type="button" className="btn btn-outline btn-sm" onClick={() => { setShowForm(false); setError(''); }}>Cancel</button>
          </div>
        </form>
      )}
    </div>
  );
};
