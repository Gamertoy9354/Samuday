import React, { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import type { CredentialResponse } from '@react-oauth/google';
import { authAPI } from '../../api/client';
import { useAuth } from '../../context/AuthContext';

interface LoginModalProps {
  onClose: () => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({ onClose }) => {
  const { login } = useAuth();
  const [tab, setTab] = useState<'google' | 'phone'>('google');
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [name, setName] = useState('');
  const [step, setStep] = useState<'phone' | 'otp' | 'register'>('phone');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [mockOtp, setMockOtp] = useState('');

  const handleGoogleSuccess = async (response: CredentialResponse) => {
    if (!response.credential) return;
    setLoading(true);
    setError('');
    try {
      const data = await authAPI.googleLogin(response.credential);
      await login(data.access_token);
      onClose();
    } catch (e: any) {
      setError(e.message || 'Google login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRequestOTP = async () => {
    if (!phone || phone.length < 10) { setError('Enter a valid phone number'); return; }
    setLoading(true);
    setError('');
    try {
      const formatted = phone.startsWith('+') ? phone : `+91${phone}`;
      const res = await authAPI.requestOTP(formatted);
      if (res.mock_otp) setMockOtp(res.mock_otp);
      setStep('otp');
    } catch (e: any) {
      setError(e.message || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async () => {
    if (otp.length !== 6) { setError('Enter 6-digit OTP'); return; }
    setLoading(true);
    setError('');
    try {
      const formatted = phone.startsWith('+') ? phone : `+91${phone}`;
      const data = await authAPI.verifyOTP(formatted, otp);
      await login(data.access_token);
      onClose();
    } catch (e: any) {
      const detail = e.message;
      if (detail?.includes('REGISTRATION_REQUIRED') || detail?.includes('registration')) {
        setStep('register');
        setError('');
      } else {
        setError(detail || 'Invalid OTP');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!name || name.length < 2) { setError('Enter your full name'); return; }
    setLoading(true);
    setError('');
    try {
      const formatted = phone.startsWith('+') ? phone : `+91${phone}`;
      // Re-request OTP for registration verification
      const otpRes = await authAPI.requestOTP(formatted).catch(() => null);
      const otpCode = otpRes?.mock_otp || otp;
      const data = await authAPI.register(formatted, otpCode, name, 'en');
      await login(data.access_token);
      onClose();
    } catch (e: any) {
      setError(e.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-content animate-fade-in">
        <div className="modal-header">
          <h2>Login / Sign Up</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          {/* Tabs */}
          <div className="auth-tabs">
            <button className={`auth-tab ${tab === 'google' ? 'active' : ''}`} onClick={() => { setTab('google'); setError(''); }}>
              Google
            </button>
            <button className={`auth-tab ${tab === 'phone' ? 'active' : ''}`} onClick={() => { setTab('phone'); setError(''); }}>
              Phone
            </button>
          </div>

          {error && <div className="alert alert-error">{error}</div>}

          {tab === 'google' && (
            <div>
              <p style={{ textAlign: 'center', color: 'var(--text-secondary)', marginBottom: 16, fontSize: '0.9rem' }}>
                Sign in with your Google account for a seamless experience
              </p>
              <div className="google-btn-wrapper">
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={() => setError('Google Sign-In failed. Please try again.')}
                  size="large"
                  width="320"
                  text="signin_with"
                  shape="rectangular"
                />
              </div>
              <div className="auth-divider">OR</div>
              <button className="btn btn-outline btn-block" onClick={() => setTab('phone')}>
                Login with Phone Number
              </button>
            </div>
          )}

          {tab === 'phone' && step === 'phone' && (
            <div>
              <div className="form-group" style={{ marginBottom: 16 }}>
                <label>Phone Number</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    value="+91"
                    readOnly
                    style={{ width: 60, textAlign: 'center', background: 'var(--bg-hover)', padding: '10px 8px', border: '1px solid var(--border-input)', borderRadius: 'var(--radius-sm)', fontSize: '0.92rem' }}
                  />
                  <input
                    type="tel"
                    placeholder="Enter 10-digit mobile number"
                    value={phone.replace(/^\+91/, '')}
                    onChange={e => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                    maxLength={10}
                    autoFocus
                  />
                </div>
              </div>
              <button className="btn btn-primary btn-block" onClick={handleRequestOTP} disabled={loading}>
                {loading ? 'Sending...' : 'Get OTP'}
              </button>
            </div>
          )}

          {tab === 'phone' && step === 'otp' && (
            <div>
              {mockOtp && (
                <div className="alert alert-info">
                  Demo OTP: <strong>{mockOtp}</strong>
                </div>
              )}
              <div className="form-group" style={{ marginBottom: 16 }}>
                <label>Enter OTP sent to +91{phone.replace(/^\+91/, '')}</label>
                <input
                  type="text"
                  placeholder="Enter 6-digit OTP"
                  value={otp}
                  onChange={e => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  maxLength={6}
                  autoFocus
                />
              </div>
              <button className="btn btn-primary btn-block" onClick={handleVerifyOTP} disabled={loading}>
                {loading ? 'Verifying...' : 'Verify OTP'}
              </button>
              <button className="btn btn-outline btn-block" style={{ marginTop: 8 }} onClick={() => { setStep('phone'); setOtp(''); }}>
                Change Number
              </button>
            </div>
          )}

          {tab === 'phone' && step === 'register' && (
            <div>
              <p style={{ color: 'var(--text-secondary)', marginBottom: 12, fontSize: '0.9rem' }}>
                New user! Complete your registration:
              </p>
              <div className="form-group" style={{ marginBottom: 16 }}>
                <label>Full Name</label>
                <input
                  type="text"
                  placeholder="Enter your full name"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  autoFocus
                />
              </div>
              <button className="btn btn-primary btn-block" onClick={handleRegister} disabled={loading}>
                {loading ? 'Creating Account...' : 'Create Account'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
