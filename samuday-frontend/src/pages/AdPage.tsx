import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { promoAPI } from '../api/client';
import { ProductCard } from '../components/product/ProductCard';
import { FALLBACK_IMAGE } from '../utils/placeholder';

interface Advertisement {
  id: string; title: string; image_url: string; link_url?: string; seller_id: string;
}

interface Listing {
  id: string; title: string; price: number;
  media: Array<{ media_url: string }>;
  rating_avg?: number | null; review_count?: number; active_discount_percent?: number | null;
}

export const AdPage: React.FC = () => {
  const { adId } = useParams<{ adId: string }>();
  const navigate = useNavigate();
  const [ad, setAd] = useState<Advertisement | null>(null);
  const [listing, setListing] = useState<Listing | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!adId) return;
    setLoading(true);
    setNotFound(false);
    promoAPI.getAdDetail(adId)
      .then(d => { setAd(d.ad); setListing(d.listing); })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
    promoAPI.clickAd(adId).catch(() => {});
  }, [adId]);

  if (loading) {
    return (
      <div className="page-content" style={{ paddingTop: 16 }}>
        <div className="skeleton" style={{ height: 220 }} />
      </div>
    );
  }

  if (notFound || !ad) {
    return (
      <div className="page-content" style={{ paddingTop: 32 }}>
        <div className="empty-state"><h3>Advertisement not found</h3><p>It may have expired or been taken down.</p></div>
      </div>
    );
  }

  return (
    <div className="page-content" style={{ paddingTop: 16 }}>
      <div style={{
        borderRadius: 'var(--radius-lg)', overflow: 'hidden', marginBottom: 24,
        aspectRatio: '3.2 / 1', boxShadow: 'var(--shadow-card)'
      }}>
        <img src={ad.image_url || FALLBACK_IMAGE} alt={ad.title} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
      </div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 16 }}>{ad.title}</h1>

      {listing ? (
        <>
          <div className="section-title">Featured Product</div>
          <div className="products-grid">
            <ProductCard
              id={listing.id}
              title={listing.title}
              price={listing.price}
              imageUrl={listing.media?.[0]?.media_url || FALLBACK_IMAGE}
              rating={listing.rating_avg ?? undefined}
              reviewCount={listing.review_count}
              discountPercent={listing.active_discount_percent ?? undefined}
            />
          </div>
        </>
      ) : (
        <div className="empty-state">
          <h3>Browse this seller's products</h3>
          <button className="btn btn-primary" style={{ marginTop: 12 }} onClick={() => navigate(`/sellers/${ad.seller_id}`)}>
            View Seller Storefront
          </button>
        </div>
      )}
    </div>
  );
};
