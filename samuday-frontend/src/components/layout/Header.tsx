import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useCart } from '../../context/CartContext';
import { Search, ShoppingCart, User, ChevronDown, Package, Store, LogOut, LayoutDashboard } from 'lucide-react';

interface HeaderProps {
  onOpenLogin: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenLogin }) => {
  const { user, logout } = useAuth();
  const { cartCount } = useCart();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  return (
    <header className="header">
      <div className="header-inner">
        {/* Logo */}
        <a className="header-logo" onClick={() => navigate('/')}>
          <span className="header-logo-text">Samuday</span>
          <span className="header-logo-tagline">Community Marketplace</span>
        </a>

        {/* Search */}
        <form className="search-container" onSubmit={handleSearch}>
          <div className="search-input-wrapper">
            <input
              className="search-input"
              type="text"
              placeholder="Search for products, brands and more..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
            <button type="submit" className="search-btn">
              <Search size={20} />
            </button>
          </div>
        </form>

        {/* Actions */}
        <div className="header-actions">
          {/* Account */}
          {user ? (
            <div style={{ position: 'relative' }} ref={dropdownRef}>
              <button className="header-action-btn" onClick={() => setShowDropdown(!showDropdown)}>
                {user.avatar_url ? (
                  <img src={user.avatar_url} alt="" style={{ width: 24, height: 24, borderRadius: '50%' }} />
                ) : (
                  <User size={20} />
                )}
                <span>{user.full_name.split(' ')[0]}</span>
                <ChevronDown size={14} />
              </button>

              {showDropdown && (
                <div className="account-dropdown animate-fade-in">
                  <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-light)' }}>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{user.full_name}</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{user.email || user.phone_number}</div>
                  </div>
                  <div className="account-dropdown-item" onClick={() => { navigate('/profile'); setShowDropdown(false); }}>
                    <User size={16} /> My Profile
                  </div>
                  <div className="account-dropdown-item" onClick={() => { navigate('/orders'); setShowDropdown(false); }}>
                    <Package size={16} /> My Orders
                  </div>
                  {user.is_seller && (
                    <div className="account-dropdown-item" onClick={() => { navigate('/seller'); setShowDropdown(false); }}>
                      <LayoutDashboard size={16} /> Seller Dashboard
                    </div>
                  )}
                  <div className="account-dropdown-item" onClick={() => { navigate('/seller'); setShowDropdown(false); }}>
                    <Store size={16} /> Become a Seller
                  </div>
                  <div className="account-dropdown-divider" />
                  <div className="account-dropdown-item" onClick={() => { logout(); setShowDropdown(false); navigate('/'); }}>
                    <LogOut size={16} /> Logout
                  </div>
                </div>
              )}
            </div>
          ) : (
            <button className="btn btn-primary btn-sm" onClick={onOpenLogin} style={{ borderRadius: '2px' }}>
              Login
            </button>
          )}

          {/* Cart */}
          <button className="header-action-btn" onClick={() => navigate('/cart')}>
            <ShoppingCart size={22} />
            {cartCount > 0 && <span className="cart-badge">{cartCount}</span>}
            <span>Cart</span>
          </button>
        </div>
      </div>
    </header>
  );
};
