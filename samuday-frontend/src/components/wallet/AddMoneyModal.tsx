import React, { useState } from 'react';
import { walletAPI } from '../../api/client';
import { Wallet, X, CheckCircle, AlertCircle } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  suggestedAmountInr?: number;
}

const PRESET_AMOUNTS_INR = [500, 1000, 2000, 5000];

export const AddMoneyModal: React.FC<Props> = ({ isOpen, onClose, onSuccess, suggestedAmountInr }) => {
  const [amountInr, setAmountInr] = useState<number>(suggestedAmountInr || 1000);
  const [customAmount, setCustomAmount] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const effectiveAmountInr = customAmount ? parseFloat(customAmount) : amountInr;

  const handleAddMoney = async () => {
    if (!effectiveAmountInr || effectiveAmountInr <= 0) {
      setError('Please enter a valid amount');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const amountPaise = Math.round(effectiveAmountInr * 100);
      // Simulated payment gateway: checkout returns a signed order, which the
      // (mock) gateway would normally confirm client-side before this callback.
      const checkout = await walletAPI.checkout(amountPaise);
      const paymentId = `pay_mock_${Date.now()}`;
      await walletAPI.verifyCallback(checkout.gateway_order_id, paymentId, checkout.signature);
      setSuccess(true);
      onSuccess();
      setTimeout(() => {
        setSuccess(false);
        onClose();
      }, 1200);
    } catch (err: any) {
      setError(err.message || 'Failed to add money. Please try again.');
    }
    setSubmitting(false);
  };

  return (
    <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1200 }}>
      <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: 420, padding: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontSize: '1.15rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Wallet size={20} color="var(--primary)" /> Add Money to Wallet
          </h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X size={20} /></button>
        </div>

        {error && <div className="alert alert-error" style={{ marginBottom: 12 }}><AlertCircle size={16} /> {error}</div>}
        {success ? (
          <div className="alert alert-success" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircle size={18} /> Money added successfully!
          </div>
        ) : (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 12 }}>
              {PRESET_AMOUNTS_INR.map(amt => (
                <button
                  key={amt}
                  type="button"
                  onClick={() => { setAmountInr(amt); setCustomAmount(''); }}
                  className={`btn ${!customAmount && amountInr === amt ? 'btn-primary' : 'btn-outline'} btn-sm`}
                >
                  &#8377;{amt.toLocaleString('en-IN')}
                </button>
              ))}
            </div>
            <div className="form-group">
              <label>Or enter a custom amount (₹)</label>
              <input
                type="number"
                min="1"
                value={customAmount}
                onChange={e => setCustomAmount(e.target.value)}
                placeholder="e.g. 1500"
              />
            </div>
            <button className="btn btn-primary btn-block" style={{ marginTop: 16 }} onClick={handleAddMoney} disabled={submitting}>
              {submitting ? 'Processing payment...' : `Add ₹${(effectiveAmountInr || 0).toLocaleString('en-IN')}`}
            </button>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 10, textAlign: 'center' }}>
              Simulated sandbox payment — no real charge is made.
            </p>
          </>
        )}
      </div>
    </div>
  );
};
