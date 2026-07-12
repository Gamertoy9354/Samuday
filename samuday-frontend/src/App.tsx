import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider, useAuth } from './context/AuthContext';
import { CartProvider, useCart } from './context/CartContext';
import { WalletProvider, useWallet } from './context/WalletContext';
import { Header } from './components/layout/Header';
import { CategoryBar } from './components/layout/CategoryBar';
import { Footer } from './components/layout/Footer';
import { LoginModal } from './components/auth/LoginModal';
import { HomePage } from './pages/HomePage';
import { SearchPage } from './pages/SearchPage';
import { ProductPage } from './pages/ProductPage';
import { CartPage } from './pages/CartPage';
import { OrdersPage } from './pages/OrdersPage';
import { ProfilePage } from './pages/ProfilePage';
import { KutumbPage } from './pages/KutumbPage';
import { SellerDashboard } from './pages/SellerDashboard';
import { AdminDashboard } from './pages/AdminDashboard';
import { SellerPage } from './pages/SellerPage';
import { SaleEventPage } from './pages/SaleEventPage';
import { AdPage } from './pages/AdPage';
import { marketAPI } from './api/client';

// Google Client ID - leave empty for dev mode (login will still work with phone OTP)
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

import { AICopilotWidget } from './components/ai/AICopilotWidget';

interface Category {
  id: string;
  name: string;
}

const AppContent: React.FC = () => {
  const { token } = useAuth();
  const { refreshCart } = useCart();
  const { refreshBalance } = useWallet();
  const [showLogin, setShowLogin] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);

  useEffect(() => {
    marketAPI.getCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    if (token) {
      refreshCart();
      refreshBalance();
    }
  }, [token, refreshCart, refreshBalance]);

  // Surface expired sessions instead of leaving the user stuck on cryptic
  // "Could not validate credentials" errors from background API calls.
  useEffect(() => {
    const onSessionExpired = () => setShowLogin(true);
    window.addEventListener('samuday:session-expired', onSessionExpired);
    return () => window.removeEventListener('samuday:session-expired', onSessionExpired);
  }, []);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header onOpenLogin={() => setShowLogin(true)} />
      <CategoryBar categories={categories} />
      
      <main style={{ flex: 1 }}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/product/:id" element={<ProductPage />} />
          <Route path="/cart" element={<CartPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/kutumb" element={<KutumbPage />} />
          <Route path="/seller" element={<SellerDashboard />} />
          <Route path="/sellers/:sellerId" element={<SellerPage />} />
          <Route path="/sale/:saleId" element={<SaleEventPage />} />
          <Route path="/ad/:adId" element={<AdPage />} />
          <Route path="/orders" element={<OrdersPage />} />
          <Route path="/admin" element={<AdminDashboard />} />
        </Routes>
      </main>

      <Footer />
      <AICopilotWidget />

      {showLogin && <LoginModal onClose={() => setShowLogin(false)} />}
    </div>
  );
};

const App: React.FC = () => (
  <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
    <BrowserRouter>
      <AuthProvider>
        <WalletProvider>
          <CartProvider>
            <AppContent />
          </CartProvider>
        </WalletProvider>
      </AuthProvider>
    </BrowserRouter>
  </GoogleOAuthProvider>
);

export default App;
