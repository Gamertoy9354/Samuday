import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { marketAPI } from '../api/client';
import { ProductCard } from '../components/product/ProductCard';
import { Star, ShieldCheck, Package, User as UserIcon } from 'lucide-react';
import { FALLBACK_IMAGE } from '../utils/placeholder';

interface SellerProfile {
  id: string;
  full_name: string;
  avatar_url?: string | null;
  profile_bio?: string | null;
  seller_tier?: string | null;
  seller_verification_status: string;
  member_since: string;
  rating: number | null;
  total_transactions: number;
  active_listing_count: number;
}

interface Listing {
  id: string; title: string; price: number;
  media: Array<{ media_url: string }>;
  rating_avg?: number | null; review_count?: number; active_discount_percent?: number | null;
}

export const SellerPage: React.FC = () => {
  const { sellerId } = useParams<{ sellerId: string }>();
  const [profile, setProfile] = useState<SellerProfile | null>(null);
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!sellerId) return;
    setLoading(true);
    setNotFound(false);
    Promise.all([
      marketAPI.getSellerProfile(sellerId),
      marketAPI.getSellerListings(sellerId),
    ])
      .then(([p, l]) => { setProfile(p); setListings(l); })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }, [sellerId]);

  if (loading) {
    return (
      <div className="page-content" style={{ paddingTop: 16 }}>
        <div className="skeleton" style={{ height: 140, marginBottom: 20 }} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: 12 }}>
          {[...Array(8)].map((_, i) => <div key={i} className="skeleton" style={{ height: 260 }} />)}
        </div>
      </div>
    );
  }

  if (notFound || !profile) {
    return (
      <div className="page-content" style={{ paddingTop: 32 }}>
        <div className="empty-state"><h3>Seller not found</h3></div>
      </div>
    );
  }

  return (
    <div className="page-content" style={{ paddingTop: 16 }}>
      <div style={{
        background: 'var(--bg-white)', border: '1px solid var(--border-card)', borderRadius: 'var(--radius-md)',
        padding: 24, display: 'flex', alignItems: 'center', gap: 20, marginBottom: 24, flexWrap: 'wrap'
      }}>
        <div style={{
          width: 72, height: 72, borderRadius: '50%', overflow: 'hidden', flexShrink: 0,
          background: 'var(--bg-body)', display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          {profile.avatar_url ? (
            <img src={profile.avatar_url} alt={profile.full_name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          ) : (
            <UserIcon size={32} color="var(--text-muted)" />
          )}
        </div>
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <h1 style={{ fontSize: '1.4rem', fontWeight: 700 }}>{profile.full_name}</h1>
            {profile.seller_verification_status === 'approved' && (
              <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.78rem', fontWeight: 600, color: 'var(--success)', background: 'var(--success-light)', padding: '3px 8px', borderRadius: 10 }}>
                <ShieldCheck size={13} /> Verified {profile.seller_tier === 'official' ? 'Business' : 'Seller'}
              </span>
            )}
          </div>
          {profile.profile_bio && <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginTop: 4 }}>{profile.profile_bio}</p>}
          <div style={{ display: 'flex', gap: 18, marginTop: 10, fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            {profile.rating !== null && (
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Star size={14} fill="#FFA41C" color="#FFA41C" /> {profile.rating.toFixed(1)} rating
              </span>
            )}
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <Package size={14} /> {profile.active_listing_count} product{profile.active_listing_count === 1 ? '' : 's'}
            </span>
            <span>{profile.total_transactions} completed order{profile.total_transactions === 1 ? '' : 's'}</span>
            <span>Member since {new Date(profile.member_since).toLocaleDateString('en-IN', { year: 'numeric', month: 'short' })}</span>
          </div>
        </div>
      </div>

      <div className="section-title">All Products from {profile.full_name}</div>
      {listings.length === 0 ? (
        <div className="empty-state"><h3>No active listings</h3><p>This seller doesn't have any products live right now.</p></div>
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
