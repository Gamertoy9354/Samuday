import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Autoplay, Pagination, Navigation, EffectFade } from 'swiper/modules';
import 'swiper/css';
import 'swiper/css/pagination';
import 'swiper/css/navigation';
import 'swiper/css/effect-fade';
import { marketAPI, promoAPI } from '../api/client';
import { ProductCard } from '../components/product/ProductCard';
import {
  ChevronRight, Smartphone, Shirt, Sprout, Home, HeartPulse, Car,
  GraduationCap, ShoppingBag, Factory, Calendar, Building, Briefcase, Package, Users, Tag, ArrowRight
} from 'lucide-react';
import { FALLBACK_IMAGE } from '../utils/placeholder';

interface Listing {
  id: string; title: string; price: number; description: string; seller_id: string;
  category_id?: string; media: Array<{ media_url: string }>; status: string;
  rating_avg?: number | null; review_count?: number; active_discount_percent?: number | null;
}

interface SaleEvent {
  id: string; title: string; description?: string; banner_image_url?: string;
  discount_percent: number; start_date: string; end_date: string;
}

interface Advertisement {
  id: string; title: string; image_url: string; link_url?: string; placement: string;
}

interface Category {
  id: string; name: string; icon_url?: string;
}

const CATEGORY_ICONS: Record<string, React.ComponentType<any>> = {
  'Electronics': Smartphone,
  'Fashion': Shirt,
  'Agriculture': Sprout,
  'Home & Construction': Home,
  'Home/Construction': Home,
  'Health': HeartPulse,
  'Automobiles': Car,
  'Education': GraduationCap,
  'Retail/FMCG': ShoppingBag,
  'Industrial/B2B': Factory,
  'Events': Calendar,
  'Real Estate': Building,
  'Jobs': Briefcase,
};

type HeroSlide =
  | { kind: 'ad'; id: string; image: string; title: string; subtitle?: string }
  | { kind: 'sale'; id: string; image: string; title: string; subtitle?: string; discount: number };

export const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const [listings, setListings] = useState<Listing[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [saleEvents, setSaleEvents] = useState<SaleEvent[]>([]);
  const [bannerAds, setBannerAds] = useState<Advertisement[]>([]);
  const [categoryStripAds, setCategoryStripAds] = useState<Advertisement[]>([]);
  const [sidebarAds, setSidebarAds] = useState<Advertisement[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [listRes, catRes, salesRes, adsRes, stripRes, sideRes] = await Promise.allSettled([
          marketAPI.getListings(),
          marketAPI.getCategories(),
          promoAPI.getSaleEvents(),
          promoAPI.getAds('hero_banner'),
          promoAPI.getAds('category_strip'),
          promoAPI.getAds('sidebar'),
        ]);
        if (listRes.status === 'fulfilled') setListings(listRes.value);
        if (catRes.status === 'fulfilled') setCategories(catRes.value);
        if (salesRes.status === 'fulfilled') setSaleEvents(salesRes.value);
        if (adsRes.status === 'fulfilled') setBannerAds(adsRes.value);
        if (stripRes.status === 'fulfilled') setCategoryStripAds(stripRes.value);
        if (sideRes.status === 'fulfilled') setSidebarAds(sideRes.value);
      } catch { /* graceful degradation */ }
      setLoading(false);
    };
    load();
  }, []);

  const getProductImage = (listing: Listing) => listing.media?.[0]?.media_url || '';

  // Group products by category
  const groupedProducts: Record<string, Listing[]> = {};
  listings.forEach(l => {
    const cat = categories.find(c => c.id === l.category_id);
    const catName = cat?.name || 'Other';
    if (!groupedProducts[catName]) groupedProducts[catName] = [];
    groupedProducts[catName].push(l);
  });

  // Featured products (first 12)
  const featured = listings.slice(0, 12);
  // Deals of the Day: listings actually covered by an active seller sale event
  const deals = listings.filter(l => (l.active_discount_percent || 0) > 0).slice(0, 8);

  const heroSlides: HeroSlide[] = [
    ...bannerAds.map((ad): HeroSlide => ({ kind: 'ad', id: ad.id, image: ad.image_url, title: ad.title })),
    ...saleEvents.filter(se => se.banner_image_url).map((se): HeroSlide => ({
      kind: 'sale', id: se.id, image: se.banner_image_url!, title: se.title, subtitle: se.description, discount: se.discount_percent
    })),
  ];

  const goToSlide = (slide: HeroSlide) => navigate(slide.kind === 'ad' ? `/ad/${slide.id}` : `/sale/${slide.id}`);

  return (
    <div className="page-content">
      {/* Hero Banner Carousel */}
      {heroSlides.length > 0 && (
        <section className="hero-section">
          <Swiper
            modules={[Autoplay, Pagination, Navigation, EffectFade]}
            effect="fade"
            fadeEffect={{ crossFade: true }}
            autoplay={{ delay: 5000, disableOnInteraction: false }}
            pagination={{ clickable: true }}
            navigation={true}
            loop={heroSlides.length > 1}
            className="hero-banner"
          >
            {heroSlides.map(slide => (
              <SwiperSlide key={`${slide.kind}-${slide.id}`}>
                <div className="hero-slide" onClick={() => goToSlide(slide)}>
                  <img src={slide.image} alt={slide.title} onError={e => { (e.target as HTMLImageElement).src = FALLBACK_IMAGE; }} />
                  <div className="hero-overlay">
                    {slide.kind === 'sale' && (
                      <span className="hero-badge"><Tag size={12} /> Up to {slide.discount}% OFF</span>
                    )}
                    {slide.kind === 'ad' && <span className="hero-badge hero-badge-ad">Sponsored</span>}
                    <h2>{slide.title}</h2>
                    {slide.subtitle && <p>{slide.subtitle}</p>}
                    <span className="hero-cta">
                      {slide.kind === 'sale' ? 'Shop the Sale' : 'Explore'} <ArrowRight size={15} />
                    </span>
                  </div>
                </div>
              </SwiperSlide>
            ))}
          </Swiper>
        </section>
      )}

      {/* Kutumb Network Promo */}
      <section
        onClick={() => navigate('/kutumb')}
        style={{
          background: 'linear-gradient(135deg, #7C4DFF, #B388FF)', borderRadius: 'var(--radius-md)',
          padding: '18px 22px', display: 'flex', alignItems: 'center', gap: 16, color: 'white', cursor: 'pointer'
        }}
      >
        <div style={{ width: 44, height: 44, borderRadius: 10, background: 'rgba(255,255,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <Users size={24} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: '1rem' }}>Kutumb Network</div>
          <div style={{ fontSize: '0.83rem', opacity: 0.9 }}>Register your family, join local community groups, and explore a separate, opt-in matrimonial layer for adults.</div>
        </div>
        <ChevronRight size={20} />
      </section>

      {/* Sponsored (sidebar-placement) ads — shown as a compact promo row */}
      {sidebarAds.length > 0 && (
        <section style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(sidebarAds.length, 3)}, 1fr)`, gap: 12 }}>
          {sidebarAds.slice(0, 3).map(ad => (
            <div
              key={ad.id}
              onClick={() => navigate(`/ad/${ad.id}`)}
              style={{ position: 'relative', borderRadius: 'var(--radius-md)', overflow: 'hidden', cursor: 'pointer', aspectRatio: '3 / 1', boxShadow: 'var(--shadow-card)' }}
            >
              <img src={ad.image_url} alt={ad.title} onError={e => { (e.target as HTMLImageElement).src = FALLBACK_IMAGE; }} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(transparent 40%, rgba(15,23,42,0.75))', display: 'flex', alignItems: 'flex-end', padding: 10 }}>
                <span style={{ color: '#fff', fontWeight: 700, fontSize: '0.85rem' }}>{ad.title}</span>
              </div>
              <span style={{ position: 'absolute', top: 6, left: 6, fontSize: '0.65rem', fontWeight: 700, background: 'rgba(255,255,255,0.9)', color: '#1e1b4b', padding: '2px 6px', borderRadius: 4 }}>Sponsored</span>
            </div>
          ))}
        </section>
      )}

      {/* Sale Events Strip */}
      {saleEvents.length > 0 && (
        <section>
          <div className="section-title">
            Live Sales & Events
            <span className="view-all" onClick={() => navigate('/search')}>View All <ChevronRight size={14} /></span>
          </div>
          <div className="sale-events-strip">
            {saleEvents.map(se => (
              <div
                key={se.id}
                className="sale-event-card"
                onClick={() => navigate(`/sale/${se.id}`)}
                style={se.banner_image_url ? {
                  backgroundImage: `linear-gradient(rgba(15,23,42,0.15), rgba(15,23,42,0.75)), url(${se.banner_image_url})`,
                  backgroundSize: 'cover', backgroundPosition: 'center',
                } : undefined}
              >
                <h3>{se.title}</h3>
                <p>{se.description?.slice(0, 80)}</p>
                <div className="sale-event-discount">Up to {se.discount_percent}% OFF</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Category Grid */}
      <section>
        <div className="section-title">Shop by Category</div>
        <div className="category-grid">
          {categories.map(cat => (
            <div
              key={cat.id}
              className="category-card"
              onClick={() => navigate(`/search?category=${cat.id}&name=${encodeURIComponent(cat.name)}`)}
            >
              <div className="category-card-icon">
                {(() => {
                  const Icon = CATEGORY_ICONS[cat.name] || Package;
                  return <Icon size={28} />;
                })()}
              </div>
              <div className="category-card-name">{cat.name}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Category-strip placement ads — a banner strip near the category grid */}
      {categoryStripAds.length > 0 && (
        <section className="category-strip-ads">
          {categoryStripAds.map(ad => (
            <div key={ad.id} className="category-strip-ad" onClick={() => navigate(`/ad/${ad.id}`)}>
              <img src={ad.image_url} alt={ad.title} onError={e => { (e.target as HTMLImageElement).src = FALLBACK_IMAGE; }} />
              <div className="category-strip-ad-overlay">
                <span>{ad.title}</span>
              </div>
            </div>
          ))}
        </section>
      )}

      {/* Deals of the Day */}
      {deals.length > 0 && (
        <section>
          <div className="section-title" style={{ background: 'var(--bg-white)', padding: '16px 20px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', marginBottom: 0 }}>
            <span>Deals of the Day</span>
            <span className="view-all" onClick={() => navigate('/search')}>View All <ChevronRight size={14} /></span>
          </div>
          <div style={{ background: 'var(--bg-white)', padding: '0 12px 12px', borderRadius: '0 0 var(--radius-md) var(--radius-md)', border: '1px solid var(--border-card)', borderTop: 'none' }}>
            <div className="product-scroll-row">
              {deals.map(l => (
                <ProductCard
                  key={l.id}
                  id={l.id}
                  title={l.title}
                  price={l.price}
                  imageUrl={getProductImage(l)}
                  rating={l.rating_avg ?? undefined}
                  reviewCount={l.review_count}
                  discountPercent={l.active_discount_percent ?? undefined}
                />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Featured Products Grid */}
      {featured.length > 0 && (
        <section>
          <div className="section-title">
            Featured Products
            <span className="view-all" onClick={() => navigate('/search')}>View All <ChevronRight size={14} /></span>
          </div>
          <div className="products-grid">
            {featured.map(l => (
              <ProductCard
                key={l.id}
                id={l.id}
                title={l.title}
                price={l.price}
                imageUrl={getProductImage(l)}
                rating={l.rating_avg ?? undefined}
                reviewCount={l.review_count}
                discountPercent={l.active_discount_percent ?? undefined}
              />
            ))}
          </div>
        </section>
      )}

      {/* Category-wise Product Rows */}
      {Object.entries(groupedProducts).slice(0, 5).map(([catName, products]) => (
        products.length > 2 && (
          <section key={catName}>
            <div className="section-title" style={{ background: 'var(--bg-white)', padding: '16px 20px', borderRadius: 'var(--radius-md) var(--radius-md) 0 0', border: '1px solid var(--border-card)', marginBottom: 0 }}>
              <span>{catName}</span>
              <span className="view-all" onClick={() => {
                const cat = categories.find(c => c.name === catName);
                navigate(`/search?category=${cat?.id || ''}&name=${encodeURIComponent(catName)}`);
              }}>View All <ChevronRight size={14} /></span>
            </div>
            <div style={{ background: 'var(--bg-white)', padding: '0 12px 12px', borderRadius: '0 0 var(--radius-md) var(--radius-md)', border: '1px solid var(--border-card)', borderTop: 'none' }}>
              <div className="product-scroll-row">
                {products.map(l => (
                  <ProductCard
                    key={l.id}
                    id={l.id}
                    title={l.title}
                    price={l.price}
                    imageUrl={getProductImage(l)}
                    rating={l.rating_avg ?? undefined}
                    reviewCount={l.review_count}
                    discountPercent={l.active_discount_percent ?? undefined}
                  />
                ))}
              </div>
            </div>
          </section>
        )
      ))}

      {loading && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: 12 }}>
          {[...Array(8)].map((_, i) => (
            <div key={i} style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
              <div className="skeleton" style={{ height: 200 }} />
              <div style={{ padding: 14 }}>
                <div className="skeleton" style={{ height: 16, marginBottom: 8 }} />
                <div className="skeleton" style={{ height: 14, width: '60%' }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
