import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider, useAuth } from './context/AuthContext';
import { CartProvider, useCart } from './context/CartContext';
import { Header } from './components/layout/Header';
import { CategoryBar } from './components/layout/CategoryBar';
import { Footer } from './components/layout/Footer';
import { LoginModal } from './components/auth/LoginModal';
import { HomePage } from './pages/HomePage';
import { SearchPage } from './pages/SearchPage';
import { ProductPage } from './pages/ProductPage';
import { CartPage } from './pages/CartPage';
import { ProfilePage } from './pages/ProfilePage';
import { SellerDashboard } from './pages/SellerDashboard';
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
  const [showLogin, setShowLogin] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);

  useEffect(() => {
    marketAPI.getCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    if (token) refreshCart();
  }, [token, refreshCart]);

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
          <Route path="/seller" element={<SellerDashboard />} />
          <Route path="/orders" element={
            <div className="page-content" style={{ paddingTop: 32 }}>
              <div className="empty-state"><h3>Order history coming soon</h3><p>Your past orders will appear here</p></div>
            </div>
          } />
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
        <CartProvider>
          <AppContent />
        </CartProvider>
      </AuthProvider>
    </BrowserRouter>
  </GoogleOAuthProvider>
);

export default App;
