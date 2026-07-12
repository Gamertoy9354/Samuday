import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { cartAPI, orderAPI, shippingAPI } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { useWallet } from '../context/WalletContext';
import { ShoppingBag, Wallet, AlertCircle, Truck, Home } from 'lucide-react';
import { FALLBACK_IMAGE } from '../utils/placeholder';
import { AddMoneyModal } from '../components/wallet/AddMoneyModal';
import { AddressPicker } from '../components/checkout/AddressPicker';

interface CartItem {
  id: string; listing_id: string; quantity: number;
  listing_title?: string; listing_price?: number; listing_image?: string;
}

interface CartSummary {
  items: CartItem[]; total_items: number; subtotal_paise: number;
}

// Matches the backend's default PLATFORM_FEE_RATE — for display only; the
// server always computes and charges the authoritative amount at order time.
const PLATFORM_FEE_RATE = 0.05;

export const CartPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { refreshCart } = useCart();
  const { balancePaise, refreshBalance } = useWallet();
  const [cart, setCart] = useState<CartSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [placing, setPlacing] = useState(false);
  const [placeError, setPlaceError] = useState('');
  const [showAddMoney, setShowAddMoney] = useState(false);

  const [fulfillmentType, setFulfillmentType] = useState<'self_pickup' | 'courier'>('self_pickup');
  const [selectedAddress, setSelectedAddress] = useState<{ id: string; pincode: string } | null>(null);
  const [deliveryFeePaise, setDeliveryFeePaise] = useState(0);
  const [deliveryEstimating, setDeliveryEstimating] = useState(false);
  const [deliverySimulated, setDeliverySimulated] = useState(false);
  const [deliveryError, setDeliveryError] = useState('');

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
    if (user) {
      loadCart();
      refreshBalance();
    } else {
      setLoading(false);
    }
  }, [user]);

  // Estimate total delivery fee by summing a rate quote per cart item (each
  // item may have a different seller/dispatch origin, so each is quoted separately).
  useEffect(() => {
    const estimate = async () => {
      if (fulfillmentType !== 'courier' || !selectedAddress || !cart || cart.items.length === 0) {
        setDeliveryFeePaise(0);
        return;
      }
      setDeliveryEstimating(true);
      setDeliveryError('');
      try {
        let total = 0;
        let anySimulated = false;
        for (const item of cart.items) {
          const rate = await shippingAPI.getRate(item.listing_id, item.quantity, selectedAddress.pincode);
          total += rate.delivery_fee_paise;
          if (rate.is_simulated) anySimulated = true;
        }
        setDeliveryFeePaise(total);
        setDeliverySimulated(anySimulated);
      } catch (e: any) {
        setDeliveryError(e.message || 'Could not estimate delivery for one or more items — the seller may not have set up dispatch info yet.');
        setDeliveryFeePaise(0);
      }
      setDeliveryEstimating(false);
    };
    estimate();
  }, [fulfillmentType, selectedAddress, cart]);

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

  const handlePlaceOrder = async () => {
    if (!cart || cart.items.length === 0) return;
    if (fulfillmentType === 'courier' && !selectedAddress) {
      setPlaceError('Please select or add a delivery address first.');
      return;
    }
    setPlacing(true);
    setPlaceError('');
    const failures: string[] = [];
    for (const item of cart.items) {
      try {
        await orderAPI.createOrder({
          listing_id: item.listing_id,
          quantity: item.quantity,
          fulfillment_type: fulfillmentType,
          delivery_address_id: fulfillmentType === 'courier' ? selectedAddress?.id : undefined,
        });
        await cartAPI.removeItem(item.id);
      } catch (err: any) {
        failures.push(`${item.listing_title || 'Item'}: ${err.message || 'failed'}`);
      }
    }
    await loadCart();
    await refreshCart();
    await refreshBalance();
    setPlacing(false);
    if (failures.length === 0) {
      navigate('/orders');
    } else {
      setPlaceError(`Some items could not be ordered — ${failures.join('; ')}`);
    }
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

  const productTotal = cart.subtotal_paise / 100;
  const platformFee = Math.round(cart.subtotal_paise * PLATFORM_FEE_RATE) / 100;
  const deliveryFee = deliveryFeePaise / 100;
  const grandTotal = productTotal + platformFee + deliveryFee;
  const insufficientFunds = balancePaise < Math.round(grandTotal * 100);
  const canPlaceOrder = fulfillmentType === 'self_pickup' || (!!selectedAddress && !deliveryEstimating && !deliveryError);

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
                src={item.listing_image || FALLBACK_IMAGE}
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

          {/* Fulfillment Method */}
          <div style={{ padding: '18px 22px', borderTop: '1px solid var(--border-light)' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: 12 }}>Delivery Method</h3>
            <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
              <button
                onClick={() => setFulfillmentType('self_pickup')}
                className={`btn ${fulfillmentType === 'self_pickup' ? 'btn-primary' : 'btn-outline'} btn-sm`}
                style={{ display: 'flex', alignItems: 'center', gap: 6 }}
              >
                <Home size={14} /> Self Pickup
              </button>
              <button
                onClick={() => setFulfillmentType('courier')}
                className={`btn ${fulfillmentType === 'courier' ? 'btn-primary' : 'btn-outline'} btn-sm`}
                style={{ display: 'flex', alignItems: 'center', gap: 6 }}
              >
                <Truck size={14} /> Courier Delivery
              </button>
            </div>

            {fulfillmentType === 'courier' && (
              <AddressPicker
                selectedAddressId={selectedAddress?.id || null}
                onSelect={(addr) => setSelectedAddress(addr ? { id: addr.id, pincode: addr.pincode } : null)}
              />
            )}
            {deliveryError && <div className="alert alert-error" style={{ marginTop: 10 }}>{deliveryError}</div>}
          </div>
        </div>

        {/* Price Summary */}
        <div className="price-summary">
          <div className="price-summary-header">Price Details</div>
          <div className="price-summary-row">
            <span>Price ({cart.total_items} items)</span>
            <span>&#8377;{productTotal.toLocaleString('en-IN')}</span>
          </div>
          <div className="price-summary-row">
            <span>Platform Fee</span>
            <span>&#8377;{platformFee.toLocaleString('en-IN')}</span>
          </div>
          <div className="price-summary-row">
            <span>Delivery Charges</span>
            <span style={{ color: fulfillmentType === 'self_pickup' ? 'var(--text-discount)' : 'inherit' }}>
              {fulfillmentType === 'self_pickup' ? 'FREE (Self Pickup)' : deliveryEstimating ? 'Calculating...' : `₹${deliveryFee.toLocaleString('en-IN')}`}
            </span>
          </div>
          <div className="price-summary-total">
            <span>Total Amount</span>
            <span>&#8377;{grandTotal.toLocaleString('en-IN')}</span>
          </div>
          {fulfillmentType === 'courier' && deliverySimulated && deliveryFeePaise > 0 && (
            <p style={{ padding: '0 22px 10px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Delivery fee is an estimate — no courier account is connected yet for one or more sellers.
            </p>
          )}

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '4px 22px 0', padding: '10px 12px', background: 'var(--bg-body)', borderRadius: 6, fontSize: '0.85rem' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><Wallet size={16} /> Wallet Balance</span>
            <strong>&#8377;{(balancePaise / 100).toLocaleString('en-IN')}</strong>
          </div>

          {insufficientFunds && (
            <div className="alert alert-error" style={{ margin: '12px 22px 0', display: 'flex', flexDirection: 'column', gap: 8 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><AlertCircle size={16} /> Insufficient wallet balance</span>
              <button className="btn btn-primary btn-sm" onClick={() => setShowAddMoney(true)}>Add Money</button>
            </div>
          )}

          {placeError && <div className="alert alert-error" style={{ margin: '12px 22px 0' }}>{placeError}</div>}

          <div style={{ padding: '16px 22px' }}>
            <button
              className="btn btn-primary btn-lg btn-block"
              onClick={handlePlaceOrder}
              disabled={placing || insufficientFunds || !canPlaceOrder}
            >
              {placing ? 'Placing Order...' : 'PLACE ORDER'}
            </button>
          </div>
        </div>
      </div>

      <AddMoneyModal
        isOpen={showAddMoney}
        onClose={() => setShowAddMoney(false)}
        onSuccess={refreshBalance}
        suggestedAmountInr={Math.ceil((Math.round(grandTotal * 100) - balancePaise) / 100 / 100) * 100 || 500}
      />
    </div>
  );
};
