import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { cartAPI } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { ShoppingBag } from 'lucide-react';

interface CartItem {
  id: string; listing_id: string; quantity: number;
  listing_title?: string; listing_price?: number; listing_image?: string;
}

interface CartSummary {
  items: CartItem[]; total_items: number; subtotal_paise: number;
}

export const CartPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { refreshCart } = useCart();
  const [cart, setCart] = useState<CartSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const loadCart = async () => {
    try {
      const data = await cartAPI.getCart();
      setCart(data);
    } catch {
      setCart(null);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (user) loadCart();
    else setLoading(false);
  }, [user]);

  const handleUpdateQty = async (itemId: string, qty: number) => {
    try {
      await cartAPI.updateItem(itemId, qty);
      await loadCart();
      await refreshCart();
    } catch { /* ignore */ }
  };

  const handleRemove = async (itemId: string) => {
    try {
      await cartAPI.removeItem(itemId);
      await loadCart();
      await refreshCart();
    } catch { /* ignore */ }
  };

  if (!user) {
    return (
      <div className="page-content" style={{ paddingTop: 32 }}>
        <div className="empty-state">
          <ShoppingBag size={64} />
          <h3>Please login to view your cart</h3>
          <p>Sign in to add items and checkout</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="page-content" style={{ paddingTop: 16 }}>
        <div className="skeleton" style={{ height: 400 }} />
      </div>
    );
  }

  if (!cart || cart.items.length === 0) {
    return (
      <div className="page-content" style={{ paddingTop: 32 }}>
        <div className="empty-state">
          <ShoppingBag size={64} />
          <h3>Your cart is empty</h3>
          <p>Add items to your cart and they will appear here</p>
          <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate('/')}>
            Continue Shopping
          </button>
        </div>
      </div>
    );
  }

  const subtotal = cart.subtotal_paise / 100;
  const delivery = subtotal > 499 ? 0 : 4000;
  const discount = Math.round(subtotal * 0.1);
  const total = subtotal - discount + delivery / 100;

  return (
    <div className="page-content" style={{ paddingTop: 16 }}>
      <div className="cart-layout">
        {/* Items */}
        <div className="cart-items-panel">
          <div className="cart-header">
            My Cart ({cart.total_items} items)
          </div>
          {cart.items.map(item => (
            <div key={item.id} className="cart-item">
              <img
                className="cart-item-image"
                src={item.listing_image || 'https://via.placeholder.com/100x100?text=Item'}
                alt={item.listing_title || 'Item'}
                onClick={() => navigate(`/product/${item.listing_id}`)}
                style={{ cursor: 'pointer' }}
              />
              <div className="cart-item-details">
                <h3 onClick={() => navigate(`/product/${item.listing_id}`)} style={{ cursor: 'pointer' }}>
                  {item.listing_title || 'Product'}
                </h3>
                <div className="product-card-price">
                  <span className="price-current">&#8377;{((item.listing_price || 0) / 100).toLocaleString('en-IN')}</span>
                  <span className="price-discount">10% off</span>
                </div>
                <div className="cart-item-qty">
                  <button onClick={() => item.quantity > 1 && handleUpdateQty(item.id, item.quantity - 1)}>-</button>
                  <span>{item.quantity}</span>
                  <button onClick={() => handleUpdateQty(item.id, item.quantity + 1)}>+</button>
                </div>
                <button className="cart-item-remove" onClick={() => handleRemove(item.id)}>
                  REMOVE
                </button>
              </div>
              <div style={{ fontWeight: 600, fontSize: '1rem' }}>
                &#8377;{(((item.listing_price || 0) * item.quantity) / 100).toLocaleString('en-IN')}
              </div>
            </div>
          ))}
          <div style={{ padding: '16px 20px', display: 'flex', justifyContent: 'flex-end' }}>
            <button className="btn btn-primary btn-lg" onClick={() => alert('Order placed successfully! (Simulated)')}>
              PLACE ORDER
            </button>
          </div>
        </div>

        {/* Price Summary */}
        <div className="price-summary">
          <div className="price-summary-header">Price Details</div>
          <div className="price-summary-row">
            <span>Price ({cart.total_items} items)</span>
            <span>&#8377;{subtotal.toLocaleString('en-IN')}</span>
          </div>
          <div className="price-summary-row">
            <span>Discount</span>
            <span style={{ color: 'var(--text-discount)' }}>-&#8377;{discount.toLocaleString('en-IN')}</span>
          </div>
          <div className="price-summary-row">
            <span>Delivery Charges</span>
            <span style={{ color: delivery === 0 ? 'var(--text-discount)' : 'inherit' }}>
              {delivery === 0 ? 'FREE' : `₹${(delivery / 100).toLocaleString('en-IN')}`}
            </span>
          </div>
          <div className="price-summary-total">
            <span>Total Amount</span>
            <span>&#8377;{total.toLocaleString('en-IN')}</span>
          </div>
          <div className="price-summary-savings">
            You will save &#8377;{discount.toLocaleString('en-IN')} on this order
          </div>
        </div>
      </div>
    </div>
  );
};
