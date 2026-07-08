import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { marketAPI } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { Star, ShoppingCart, Zap, Shield, Truck, RotateCcw, Tag } from 'lucide-react';

interface Listing {
  id: string; title: string; description: string; price: number; seller_id: string;
  quantity: number; unit?: string; status: string; listing_type: string;
  media: Array<{ id: string; media_url: string }>; category_id?: string; created_at: string;
}

function pseudoRating(id: string) {
  let hash = 0;
  for (let i = 0; i < id.length; i++) { hash = ((hash << 5) - hash) + id.charCodeAt(i); hash |= 0; }
  return { rating: Math.min(3.5 + (Math.abs(hash) % 15) / 10, 4.9), reviews: 100 + (Math.abs(hash) % 9900) };
}

export const ProductPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { addToCart } = useCart();
  const [product, setProduct] = useState<Listing | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState(0);
  const [addedToCart, setAddedToCart] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    marketAPI.getListing(id).then(setProduct).catch(() => navigate('/')).finally(() => setLoading(false));
  }, [id, navigate]);

  if (loading) {
    return (
      <div className="page-content" style={{ paddingTop: 16 }}>
        <div className="product-detail">
          <div className="skeleton" style={{ height: 400 }} />
          <div><div className="skeleton" style={{ height: 24, marginBottom: 12 }} /><div className="skeleton" style={{ height: 200 }} /></div>
        </div>
      </div>
    );
  }

  if (!product) return <div className="page-content"><div className="empty-state"><h3>Product not found</h3></div></div>;

  const displayPrice = product.price / 100;
  const discount = Math.floor(10 + Math.random() * 40);
  const originalPrice = Math.round(displayPrice / (1 - discount / 100));
  const { rating, reviews } = pseudoRating(product.id);
  const images = product.media.length > 0 ? product.media.map(m => m.media_url) : ['https://via.placeholder.com/500x500?text=Product'];

  const handleAddToCart = async () => {
    if (!user) return;
    const success = await addToCart(product.id);
    if (success) setAddedToCart(true);
  };

  return (
    <div className="page-content" style={{ paddingTop: 16 }}>
      {/* Breadcrumbs */}
      <div className="breadcrumbs">
        <a onClick={() => navigate('/')}>Home</a>
        <span>/</span>
        <a onClick={() => navigate('/search')}>Products</a>
        <span>/</span>
        <span>{product.title.slice(0, 40)}...</span>
      </div>

      <div className="product-detail">
        {/* Gallery */}
        <div className="product-gallery">
          <div className="product-gallery-main">
            <img src={images[selectedImage]} alt={product.title} />
          </div>
          {images.length > 1 && (
            <div className="product-gallery-thumbs">
              {images.map((img, i) => (
                <div
                  key={i}
                  className={`product-gallery-thumb ${selectedImage === i ? 'active' : ''}`}
                  onClick={() => setSelectedImage(i)}
                >
                  <img src={img} alt="" />
                </div>
              ))}
            </div>
          )}
          <div className="product-actions" style={{ marginTop: 16 }}>
            <button className="btn btn-cart btn-lg" onClick={handleAddToCart} disabled={addedToCart}>
              <ShoppingCart size={20} />
              {addedToCart ? 'ADDED TO CART' : 'ADD TO CART'}
            </button>
            <button className="btn btn-buy btn-lg" onClick={() => { handleAddToCart(); navigate('/cart'); }}>
              <Zap size={20} />
              BUY NOW
            </button>
          </div>
        </div>

        {/* Info */}
        <div className="product-info">
          <h1>{product.title}</h1>

          <div className="product-card-rating">
            <span className="rating-badge" style={{ fontSize: '0.85rem', padding: '3px 10px' }}>
              {rating.toFixed(1)} <Star size={12} fill="white" />
            </span>
            <span className="rating-count" style={{ fontSize: '0.9rem' }}>
              {reviews.toLocaleString()} Ratings & {Math.floor(reviews * 0.3).toLocaleString()} Reviews
            </span>
          </div>

          <div className="product-info-price">
            <span className="price-current" style={{ fontSize: '2rem' }}>&#8377;{displayPrice.toLocaleString('en-IN')}</span>
            <span className="price-original" style={{ fontSize: '1.1rem' }}>&#8377;{originalPrice.toLocaleString('en-IN')}</span>
            <span className="price-discount" style={{ fontSize: '1.1rem' }}>{discount}% off</span>
          </div>

          {/* Offers */}
          <div style={{ background: 'var(--bg-body)', borderRadius: 'var(--radius-md)', padding: 16 }}>
            <div style={{ fontWeight: 600, marginBottom: 8, fontSize: '0.95rem' }}>Available Offers</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}><Tag size={14} className="text-success" style={{ color: 'var(--success)', flexShrink: 0 }} /> <span><strong>Bank Offer:</strong> 10% off on SBI Credit Cards, up to ₹1,500 on orders of ₹5,000+</span></div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}><Tag size={14} className="text-success" style={{ color: 'var(--success)', flexShrink: 0 }} /> <span><strong>Special Price:</strong> Get extra {Math.floor(discount/2)}% off (price inclusive)</span></div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}><Tag size={14} className="text-success" style={{ color: 'var(--success)', flexShrink: 0 }} /> <span><strong>Partner Offer:</strong> Sign up for Samuday Pay & get ₹100 cashback</span></div>
            </div>
          </div>

          {/* Delivery */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 12, border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)' }}>
              <Truck size={20} color="var(--text-muted)" />
              <div><div style={{ fontWeight: 600, fontSize: '0.85rem' }}>Free Delivery</div><div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Orders above ₹499</div></div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 12, border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)' }}>
              <RotateCcw size={20} color="var(--text-muted)" />
              <div><div style={{ fontWeight: 600, fontSize: '0.85rem' }}>7-Day Returns</div><div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Easy return policy</div></div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 12, border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)' }}>
              <Shield size={20} color="var(--text-muted)" />
              <div><div style={{ fontWeight: 600, fontSize: '0.85rem' }}>Secure Payment</div><div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>100% protected</div></div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 12, border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)' }}>
              <Shield size={20} color="var(--text-muted)" />
              <div><div style={{ fontWeight: 600, fontSize: '0.85rem' }}>Genuine Products</div><div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Community verified</div></div>
            </div>
          </div>

          {/* Description */}
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 8 }}>Product Description</h3>
            <p className="product-info-desc">{product.description}</p>
          </div>

          {/* Specs */}
          <div style={{ border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
            <div style={{ padding: '10px 16px', fontWeight: 600, fontSize: '0.95rem', background: 'var(--bg-body)' }}>Specifications</div>
            <div style={{ padding: 16, display: 'grid', gridTemplateColumns: '140px 1fr', gap: '8px 16px', fontSize: '0.85rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Listing Type</span>
              <span style={{ textTransform: 'capitalize' }}>{product.listing_type}</span>
              <span style={{ color: 'var(--text-muted)' }}>Available Qty</span>
              <span>{product.quantity} {product.unit || 'units'}</span>
              <span style={{ color: 'var(--text-muted)' }}>Status</span>
              <span style={{ textTransform: 'capitalize' }}>{product.status}</span>
              <span style={{ color: 'var(--text-muted)' }}>Listed On</span>
              <span>{new Date(product.created_at).toLocaleDateString('en-IN')}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
