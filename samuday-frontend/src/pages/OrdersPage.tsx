import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { orderAPI, marketAPI } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Package, CheckCircle2, XCircle, Clock, Truck, Star, Pencil, Trash2 } from 'lucide-react';
import { FALLBACK_IMAGE } from '../utils/placeholder';

interface Order {
  id: string;
  listing_id: string;
  listing_title?: string;
  listing_image?: string;
  quantity: number;
  total_amount: number;
  product_amount: number;
  platform_fee_amount: number;
  delivery_fee_amount: number;
  status: string;
  fulfillment_type: string;
  created_at: string;
  courier_status?: string;
  waybill_number?: string;
  tracking_url?: string;
  is_simulated_shipment?: boolean;
  has_review?: boolean;
  review_id?: string | null;
  review_rating?: number | null;
  review_comment?: string | null;
}

const STATUS_META: Record<string, { label: string; color: string; icon: React.ComponentType<any> }> = {
  pending: { label: 'Pending Payment', color: '#E67A00', icon: Clock },
  paid: { label: 'Paid — Awaiting Delivery', color: '#0052CC', icon: Truck },
  completed: { label: 'Completed', color: '#137333', icon: CheckCircle2 },
  cancelled: { label: 'Cancelled', color: '#B00020', icon: XCircle },
  refunded: { label: 'Refunded', color: '#B00020', icon: XCircle },
};

export const OrdersPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [actingId, setActingId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [editingReviewId, setEditingReviewId] = useState<string | null>(null);
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewComment, setReviewComment] = useState('');
  const [reviewSubmitting, setReviewSubmitting] = useState(false);
  const [deletingReviewId, setDeletingReviewId] = useState<string | null>(null);

  const loadOrders = async () => {
    setLoading(true);
    try {
      const data = await orderAPI.getMyOrders('buyer');
      setOrders(data);
    } catch {
      setOrders([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (user) loadOrders();
    else setLoading(false);
  }, [user]);

  const handleComplete = async (id: string) => {
    setActingId(id);
    setError('');
    try {
      await orderAPI.completeOrder(id);
      await loadOrders();
    } catch (err: any) {
      setError(err.message || 'Failed to mark order as received');
    }
    setActingId(null);
  };

  const handleCancel = async (id: string) => {
    if (!confirm('Cancel this order? Your escrowed funds will be refunded.')) return;
    setActingId(id);
    setError('');
    try {
      await orderAPI.cancelOrder(id);
      await loadOrders();
    } catch (err: any) {
      setError(err.message || 'Failed to cancel order');
    }
    setActingId(null);
  };

  const openReviewForm = (id: string) => {
    setReviewingId(id);
    setEditingReviewId(null);
    setReviewRating(5);
    setReviewComment('');
  };

  const openEditReviewForm = (order: Order) => {
    setReviewingId(order.id);
    setEditingReviewId(order.review_id || null);
    setReviewRating(order.review_rating || 5);
    setReviewComment(order.review_comment || '');
  };

  const handleSubmitReview = async (id: string) => {
    setReviewSubmitting(true);
    setError('');
    try {
      if (editingReviewId) {
        await marketAPI.updateReview(editingReviewId, { rating: reviewRating, comment: reviewComment.trim() || undefined });
      } else {
        await marketAPI.submitReview({ order_id: id, rating: reviewRating, comment: reviewComment.trim() || undefined });
      }
      setReviewingId(null);
      setEditingReviewId(null);
      await loadOrders();
    } catch (err: any) {
      setError(err.message || 'Failed to submit review');
    }
    setReviewSubmitting(false);
  };

  const handleDeleteReview = async (reviewId: string) => {
    if (!confirm('Delete this review? This cannot be undone.')) return;
    setDeletingReviewId(reviewId);
    setError('');
    try {
      await marketAPI.deleteReview(reviewId);
      await loadOrders();
    } catch (err: any) {
      setError(err.message || 'Failed to delete review');
    }
    setDeletingReviewId(null);
  };

  if (!user) {
    return (
      <div className="page-content" style={{ paddingTop: 32 }}>
        <div className="empty-state"><h3>Please login to view your orders</h3></div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="page-content" style={{ paddingTop: 16 }}>
        <div className="skeleton" style={{ height: 300 }} />
      </div>
    );
  }

  return (
    <div className="page-content" style={{ paddingTop: 16 }}>
      <div style={{ maxWidth: 800, margin: '0 auto' }}>
        <h2 style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: 16 }}>My Orders</h2>

        {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

        {orders.length === 0 ? (
          <div className="empty-state">
            <Package size={64} />
            <h3>No orders yet</h3>
            <p>Your past and current orders will appear here</p>
            <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate('/')}>
              Start Shopping
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {orders.map(o => {
              const meta = STATUS_META[o.status] || STATUS_META.pending;
              const StatusIcon = meta.icon;
              return (
                <div key={o.id} style={{ background: 'var(--bg-white)', border: '1px solid var(--border-card)', borderRadius: 'var(--radius-md)', padding: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <img
                    src={o.listing_image || FALLBACK_IMAGE}
                    alt=""
                    onClick={() => navigate(`/product/${o.listing_id}`)}
                    style={{ width: 64, height: 64, objectFit: 'cover', borderRadius: 6, cursor: 'pointer' }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, cursor: 'pointer' }} onClick={() => navigate(`/product/${o.listing_id}`)}>
                      {o.listing_title || 'Product'}
                    </div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                      Qty: {o.quantity} · &#8377;{(o.total_amount / 100).toLocaleString('en-IN')} · {new Date(o.created_at).toLocaleDateString('en-IN')}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6, color: meta.color, fontSize: '0.82rem', fontWeight: 600 }}>
                      <StatusIcon size={14} /> {meta.label}
                    </div>
                    {o.fulfillment_type === 'courier' && o.courier_status && (
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Truck size={12} /> Courier: <span style={{ textTransform: 'capitalize' }}>{o.courier_status}</span>
                        {o.waybill_number && <span>· AWB {o.waybill_number}</span>}
                        {o.is_simulated_shipment && <span>(estimated — no courier account connected yet)</span>}
                      </div>
                    )}
                  </div>
                  {o.status === 'paid' && (
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button className="btn btn-primary btn-sm" onClick={() => handleComplete(o.id)} disabled={actingId === o.id}>
                        {actingId === o.id ? 'Updating...' : 'Mark Received'}
                      </button>
                      <button className="btn btn-outline btn-sm" onClick={() => handleCancel(o.id)} disabled={actingId === o.id}>
                        Cancel
                      </button>
                    </div>
                  )}
                  {o.status === 'completed' && !o.has_review && reviewingId !== o.id && (
                    <button className="btn btn-outline btn-sm" onClick={() => openReviewForm(o.id)} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Star size={14} /> Leave a Review
                    </button>
                  )}
                  {o.status === 'completed' && o.has_review && reviewingId !== o.id && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ fontSize: '0.8rem', color: 'var(--success)', fontWeight: 600 }}>Reviewed</span>
                      <button className="btn btn-outline btn-sm" onClick={() => openEditReviewForm(o)} title="Edit your review" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Pencil size={13} /> Edit
                      </button>
                      <button
                        className="btn btn-outline btn-sm"
                        onClick={() => o.review_id && handleDeleteReview(o.review_id)}
                        disabled={deletingReviewId === o.review_id}
                        title="Delete your review"
                        style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--danger)', borderColor: 'var(--danger)' }}
                      >
                        <Trash2 size={13} /> {deletingReviewId === o.review_id ? 'Deleting...' : 'Delete'}
                      </button>
                    </div>
                  )}
                </div>

                {o.status === 'completed' && reviewingId === o.id && (
                  <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--border-light)' }}>
                    {editingReviewId && (
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 8 }}>
                        Editing your review — the AI will draft a fresh seller reply once you save.
                      </div>
                    )}
                    <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
                      {[1, 2, 3, 4, 5].map(n => (
                        <Star
                          key={n}
                          size={22}
                          color="#FFA41C"
                          fill={n <= reviewRating ? '#FFA41C' : 'none'}
                          style={{ cursor: 'pointer' }}
                          onClick={() => setReviewRating(n)}
                        />
                      ))}
                    </div>
                    <textarea
                      value={reviewComment}
                      onChange={e => setReviewComment(e.target.value)}
                      rows={3}
                      placeholder="Share your experience with this product/seller (optional)..."
                      style={{ width: '100%', marginBottom: 10 }}
                    />
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button className="btn btn-primary btn-sm" onClick={() => handleSubmitReview(o.id)} disabled={reviewSubmitting}>
                        {reviewSubmitting ? 'Submitting...' : editingReviewId ? 'Save Changes' : 'Submit Review'}
                      </button>
                      <button className="btn btn-outline btn-sm" onClick={() => { setReviewingId(null); setEditingReviewId(null); }} disabled={reviewSubmitting}>
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
