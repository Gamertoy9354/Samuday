import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { promoAPI } from '../api/client';
import { ProductCard } from '../components/product/ProductCard';
import { Tag, Calendar } from 'lucide-react';
import { FALLBACK_IMAGE } from '../utils/placeholder';

interface SaleEvent {
  id: string; title: string; description?: string; banner_image_url?: string;
  discount_percent: number; start_date: string; end_date: string;
}

interface Listing {
  id: string; title: string; price: number;
  media: Array<{ media_url: string }>;
  rating_avg?: number | null; review_count?: number; active_discount_percent?: number | null;
}

export const SaleEventPage: React.FC = () => {
  const { saleId } = useParams<{ saleId: string }>();
  const [event, setEvent] = useState<SaleEvent | null>(null);
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!saleId) return;
    setLoading(true);
    setNotFound(false);
    promoAPI.getSaleEventDetail(saleId)
      .then(d => { setEvent(d.event); setListings(d.listings); })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }, [saleId]);

  if (loading) {
    return (
      <div className="page-content" style={{ paddingTop: 16 }}>
        <div className="skeleton" style={{ height: 220, marginBottom: 20 }} />
      </div>
    );
  }

  if (notFound || !event) {
    return (
      <div className="page-content" style={{ paddingTop: 32 }}>
        <div className="empty-state"><h3>Sale event not found</h3><p>It may have ended or been taken down.</p></div>
      </div>
    );
  }

  return (
    <div className="page-content" style={{ paddingTop: 16 }}>
      <div style={{
        position: 'relative', borderRadius: 'var(--radius-lg)', overflow: 'hidden', marginBottom: 24,
        aspectRatio: '3.2 / 1', boxShadow: 'var(--shadow-card)'
      }}>
        <img
          src={event.banner_image_url || FALLBACK_IMAGE}
          alt={event.title}
          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
        />
        <div style={{
          position: 'absolute', bottom: 0, left: 0, right: 0, padding: '28px 36px',
          background: 'linear-gradient(transparent, rgba(15, 23, 42, 0.8))', color: '#fff'
        }}>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 800, marginBottom: 6 }}>{event.title}</h1>
          {event.description && <p style={{ opacity: 0.9, marginBottom: 8, maxWidth: 600 }}>{event.description}</p>}
          <div style={{ display: 'flex', gap: 16, fontSize: '0.85rem', flexWrap: 'wrap' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontWeight: 700, background: 'var(--accent)', color: '#1e1b4b', padding: '4px 10px', borderRadius: 6 }}>
              <Tag size={13} /> Up to {event.discount_percent}% OFF
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 5, opacity: 0.85 }}>
              <Calendar size={13} /> Ends {new Date(event.end_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
            </span>
          </div>
        </div>
      </div>

      <div className="section-title">Products in this Sale ({listings.length})</div>
      {listings.length === 0 ? (
        <div className="empty-state"><h3>No products currently listed for this sale</h3></div>
      ) : (
        <div className="products-grid">
          {listings.map(l => (
            <ProductCard
              key={l.id}
              id={l.id}
              title={l.title}
              price={l.price}
              imageUrl={l.media?.[0]?.media_url || FALLBACK_IMAGE}
              rating={l.rating_avg ?? undefined}
              reviewCount={l.review_count}
              discountPercent={l.active_discount_percent ?? undefined}
            />
          ))}
        </div>
      )}
    </div>
  );
};
