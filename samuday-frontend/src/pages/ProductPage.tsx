import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { marketAPI } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { Star, ShoppingCart, Zap, Shield, Truck, RotateCcw, Tag, Store, ChevronRight, Briefcase, Send, CheckCircle, Sprout } from 'lucide-react';
import { FALLBACK_IMAGE } from '../utils/placeholder';
import { renderFormattedText } from '../utils/textFormat';

interface JobDetails {
  job_type: string; salary_min?: number | null; salary_max?: number | null; salary_period?: string | null;
  experience_required?: string | null; openings: number; application_deadline?: string | null; contact_email?: string | null;
}

interface AgriDetails {
  crop_type?: string | null; is_organic: boolean; harvest_date?: string | null; grade?: string | null;
}

interface Listing {
  id: string; title: string; description: string; price: number; seller_id: string;
  quantity: number; unit?: string; status: string; listing_type: string;
  media: Array<{ id: string; media_url: string }>; category_id?: string; created_at: string;
  rating_avg?: number | null; review_count?: number;
  active_discount_percent?: number | null;
  available_offers?: string[] | null; return_policy?: string | null;
  job_details?: JobDetails | null; agri_details?: AgriDetails | null;
}

interface ProductReview {
  id: string;
  buyer_name: string;
  rating: number;
  comment: string | null;
  seller_reply: string | null;
  seller_replied_at: string | null;
  created_at: string;
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
  const [reviews, setReviews] = useState<ProductReview[]>([]);
  const [sellerName, setSellerName] = useState<string | null>(null);
  const [applyMessage, setApplyMessage] = useState('');
  const [applying, setApplying] = useState(false);
  const [applied, setApplied] = useState(false);
  const [applyError, setApplyError] = useState('');

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    marketAPI.getListing(id).then(setProduct).catch(() => navigate('/')).finally(() => setLoading(false));
    marketAPI.getListingReviews(id).then(setReviews).catch(() => setReviews([]));
  }, [id, navigate]);

  useEffect(() => {
    if (!product?.seller_id) return;
    marketAPI.getSellerProfile(product.seller_id).then(p => setSellerName(p.full_name)).catch(() => setSellerName(null));
  }, [product?.seller_id]);

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
  const discount = product.active_discount_percent || 0;
  const originalPrice = discount > 0 ? Math.round(displayPrice / (1 - discount / 100)) : null;
  const rating = product.rating_avg ?? null;
  const reviewCount = product.review_count ?? 0;
  const images = product.media.length > 0 ? product.media.map(m => m.media_url) : [FALLBACK_IMAGE];

  const handleAddToCart = async () => {
    if (!user) return;
    const success = await addToCart(product.id);
    if (success) setAddedToCart(true);
  };

  const handleApply = async () => {
    if (!user || !product) return;
    setApplying(true);
    setApplyError('');
    try {
      await marketAPI.applyToJob(product.id, applyMessage.trim() || undefined);
      setApplied(true);
    } catch (e: any) {
      setApplyError(e.message || 'Failed to submit your application');
    }
    setApplying(false);
  };

  const isJob = !!product.job_details;
  const isAgri = !!product.agri_details;

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
          {isJob ? (
            <div style={{ marginTop: 16 }}>
              {applied ? (
                <div className="alert alert-success" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <CheckCircle size={18} /> Application submitted! The employer can now see your profile and message.
                </div>
              ) : (
                <>
                  {!user && <div className="alert alert-error" style={{ marginBottom: 10 }}>Please log in to apply for this job.</div>}
                  {applyError && <div className="alert alert-error" style={{ marginBottom: 10 }}>{applyError}</div>}
                  <textarea
                    value={applyMessage}
                    onChange={e => setApplyMessage(e.target.value)}
                    rows={3}
                    placeholder="Optional: add a short message to the employer (experience, availability, etc.)"
                    style={{ width: '100%', marginBottom: 10, padding: 10, borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)', fontSize: '0.88rem' }}
                  />
                  <button className="btn btn-buy btn-lg" onClick={handleApply} disabled={!user || applying} style={{ width: '100%' }}>
                    <Send size={18} /> {applying ? 'Submitting...' : 'Apply Now'}
                  </button>
                </>
              )}
            </div>
          ) : (
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
          )}
        </div>

        {/* Info */}
        <div className="product-info">
          <h1>{product.title}</h1>

          {sellerName && (
            <div
              onClick={() => navigate(`/sellers/${product.seller_id}`)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6, cursor: 'pointer', color: 'var(--primary)', fontSize: '0.85rem', fontWeight: 600, marginBottom: 4 }}
            >
              <Store size={14} /> Sold by {sellerName} <ChevronRight size={13} />
            </div>
          )}

          {reviewCount > 0 && rating !== null && (
            <div className="product-card-rating">
              <span className="rating-badge" style={{ fontSize: '0.85rem', padding: '3px 10px' }}>
                {rating.toFixed(1)} <Star size={12} fill="white" />
              </span>
              <span className="rating-count" style={{ fontSize: '0.9rem' }}>
                {reviewCount.toLocaleString()} verified {reviewCount === 1 ? 'review' : 'reviews'}
              </span>
            </div>
          )}

          {isJob ? (
            <div className="product-info-price" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Briefcase size={20} color="var(--primary)" />
              <span className="price-current" style={{ fontSize: '1.6rem' }}>
                {product.job_details!.salary_min || product.job_details!.salary_max
                  ? `₹${((product.job_details!.salary_min || product.job_details!.salary_max)! / 100).toLocaleString('en-IN')}${product.job_details!.salary_min && product.job_details!.salary_max && product.job_details!.salary_min !== product.job_details!.salary_max ? ` – ₹${(product.job_details!.salary_max / 100).toLocaleString('en-IN')}` : ''}`
                  : 'Salary not disclosed'}
              </span>
              {(product.job_details!.salary_min || product.job_details!.salary_max) && (
                <span style={{ fontSize: '0.95rem', color: 'var(--text-muted)' }}>/ {product.job_details!.salary_period || 'month'}</span>
              )}
            </div>
          ) : (
            <div className="product-info-price">
              <span className="price-current" style={{ fontSize: '2rem' }}>
                &#8377;{displayPrice.toLocaleString('en-IN')}{isAgri && product.unit ? <span style={{ fontSize: '1rem', color: 'var(--text-muted)' }}> / {product.unit}</span> : null}
              </span>
              {originalPrice && (
                <>
                  <span className="price-original" style={{ fontSize: '1.1rem' }}>&#8377;{originalPrice.toLocaleString('en-IN')}</span>
                  <span className="price-discount" style={{ fontSize: '1.1rem' }}>{discount}% off</span>
                </>
              )}
              {isAgri && product.agri_details?.is_organic && (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, marginLeft: 10, fontSize: '0.85rem', color: 'var(--success)', fontWeight: 600 }}>
                  <Sprout size={15} /> Certified Organic
                </span>
              )}
            </div>
          )}

          {/* Offers — seller-entered, shown only when the seller has actually added any */}
          {product.available_offers && product.available_offers.length > 0 && (
            <div style={{ background: 'var(--bg-body)', borderRadius: 'var(--radius-md)', padding: 16 }}>
              <div style={{ fontWeight: 600, marginBottom: 8, fontSize: '0.95rem' }}>Available Offers</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                {product.available_offers.map((offer, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Tag size={14} style={{ color: 'var(--success)', flexShrink: 0 }} /> <span>{offer}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Delivery */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 12, border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)' }}>
              <Truck size={20} color="var(--text-muted)" />
              <div><div style={{ fontWeight: 600, fontSize: '0.85rem' }}>Delivery Available</div><div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Fee calculated at checkout by pincode</div></div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 12, border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)' }}>
              <RotateCcw size={20} color="var(--text-muted)" />
              <div><div style={{ fontWeight: 600, fontSize: '0.85rem' }}>Return Policy</div><div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{product.return_policy || 'Set by seller — contact seller for details'}</div></div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 12, border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)' }}>
              <Shield size={20} color="var(--text-muted)" />
              <div><div style={{ fontWeight: 600, fontSize: '0.85rem' }}>Secure Payment</div><div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>100% protected via Samuday escrow</div></div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 12, border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)' }}>
              <Shield size={20} color="var(--text-muted)" />
              <div><div style={{ fontWeight: 600, fontSize: '0.85rem' }}>Genuine Products</div><div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Community verified</div></div>
            </div>
          </div>

          {/* Description */}
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 8 }}>Product Description</h3>
            <div className="product-info-desc">{renderFormattedText(product.description)}</div>
          </div>

          {/* Specs */}
          <div style={{ border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
            <div style={{ padding: '10px 16px', fontWeight: 600, fontSize: '0.95rem', background: 'var(--bg-body)' }}>
              {isJob ? 'Job Details' : isAgri ? 'Produce Details' : 'Specifications'}
            </div>
            <div style={{ padding: 16, display: 'grid', gridTemplateColumns: '140px 1fr', gap: '8px 16px', fontSize: '0.85rem' }}>
              {isJob ? (
                <>
                  <span style={{ color: 'var(--text-muted)' }}>Job Type</span>
                  <span style={{ textTransform: 'capitalize' }}>{product.job_details!.job_type.replace('-', ' ')}</span>
                  <span style={{ color: 'var(--text-muted)' }}>Openings</span>
                  <span>{product.job_details!.openings}</span>
                  {product.job_details!.experience_required && (
                    <>
                      <span style={{ color: 'var(--text-muted)' }}>Experience</span>
                      <span>{product.job_details!.experience_required}</span>
                    </>
                  )}
                  {product.job_details!.application_deadline && (
                    <>
                      <span style={{ color: 'var(--text-muted)' }}>Apply By</span>
                      <span>{new Date(product.job_details!.application_deadline).toLocaleDateString('en-IN')}</span>
                    </>
                  )}
                  <span style={{ color: 'var(--text-muted)' }}>Status</span>
                  <span style={{ textTransform: 'capitalize' }}>{product.status}</span>
                  <span style={{ color: 'var(--text-muted)' }}>Posted On</span>
                  <span>{new Date(product.created_at).toLocaleDateString('en-IN')}</span>
                </>
              ) : isAgri ? (
                <>
                  {product.agri_details!.crop_type && (
                    <>
                      <span style={{ color: 'var(--text-muted)' }}>Crop Type</span>
                      <span>{product.agri_details!.crop_type}</span>
                    </>
                  )}
                  {product.agri_details!.grade && (
                    <>
                      <span style={{ color: 'var(--text-muted)' }}>Grade</span>
                      <span>{product.agri_details!.grade}</span>
                    </>
                  )}
                  {product.agri_details!.harvest_date && (
                    <>
                      <span style={{ color: 'var(--text-muted)' }}>Harvest Date</span>
                      <span>{new Date(product.agri_details!.harvest_date).toLocaleDateString('en-IN')}</span>
                    </>
                  )}
                  <span style={{ color: 'var(--text-muted)' }}>Available Qty</span>
                  <span>{product.quantity} {product.unit || 'units'}</span>
                  <span style={{ color: 'var(--text-muted)' }}>Status</span>
                  <span style={{ textTransform: 'capitalize' }}>{product.status}</span>
                  <span style={{ color: 'var(--text-muted)' }}>Listed On</span>
                  <span>{new Date(product.created_at).toLocaleDateString('en-IN')}</span>
                </>
              ) : (
                <>
                  <span style={{ color: 'var(--text-muted)' }}>Listing Type</span>
                  <span style={{ textTransform: 'capitalize' }}>{product.listing_type}</span>
                  <span style={{ color: 'var(--text-muted)' }}>Available Qty</span>
                  <span>{product.quantity} {product.unit || 'units'}</span>
                  <span style={{ color: 'var(--text-muted)' }}>Status</span>
                  <span style={{ textTransform: 'capitalize' }}>{product.status}</span>
                  <span style={{ color: 'var(--text-muted)' }}>Listed On</span>
                  <span>{new Date(product.created_at).toLocaleDateString('en-IN')}</span>
                </>
              )}
            </div>
          </div>

          {/* Ratings & Reviews */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Ratings & Reviews {reviewCount > 0 && `(${reviewCount})`}</h3>
              {user && (
                <button className="btn btn-outline btn-sm" onClick={() => navigate('/orders')}>
                  Bought this? Leave a review
                </button>
              )}
            </div>
            {reviews.length === 0 ? (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                No reviews yet. Reviews appear here once buyers rate a completed order — you can leave one from your Orders page after your order is marked completed.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {reviews.map(r => (
                  <div key={r.id} style={{ border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', padding: 14 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                      <span style={{ fontWeight: 600, fontSize: '0.88rem' }}>{r.buyer_name}</span>
                      <div style={{ display: 'flex', gap: 2, color: '#FFA41C' }}>
                        {[...Array(r.rating)].map((_, i) => <Star key={i} size={13} fill="currentColor" />)}
                      </div>
                    </div>
                    {r.comment && <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', marginBottom: r.seller_reply ? 10 : 0 }}>{r.comment}</p>}
                    {r.seller_reply && (
                      <div style={{ background: 'var(--bg-body)', borderRadius: 6, padding: 10, fontSize: '0.82rem' }}>
                        <strong>Seller's Response:</strong> {r.seller_reply}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
