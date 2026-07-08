import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Autoplay, Pagination, Navigation } from 'swiper/modules';
import 'swiper/css';
import 'swiper/css/pagination';
import 'swiper/css/navigation';
import { marketAPI, promoAPI } from '../api/client';
import { ProductCard } from '../components/product/ProductCard';
import { 
  ChevronRight, Smartphone, Shirt, Sprout, Home, HeartPulse, Car, 
  GraduationCap, ShoppingBag, Factory, Calendar, Building, Briefcase, Package
} from 'lucide-react';

interface Listing {
  id: string; title: string; price: number; description: string; seller_id: string;
  category_id?: string; media: Array<{ media_url: string }>; status: string;
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

// Generate pseudo-random rating from product id
function pseudoRating(id: string): { rating: number; reviews: number } {
  let hash = 0;
  for (let i = 0; i < id.length; i++) { hash = ((hash << 5) - hash) + id.charCodeAt(i); hash |= 0; }
  const rating = 3.5 + (Math.abs(hash) % 15) / 10;
  const reviews = 100 + (Math.abs(hash) % 9900);
  return { rating: Math.min(rating, 4.9), reviews };
}

export const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const [listings, setListings] = useState<Listing[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [saleEvents, setSaleEvents] = useState<SaleEvent[]>([]);
  const [bannerAds, setBannerAds] = useState<Advertisement[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [listRes, catRes, salesRes, adsRes] = await Promise.allSettled([
          marketAPI.getListings(),
          marketAPI.getCategories(),
          promoAPI.getSaleEvents(),
          promoAPI.getAds('hero_banner'),
        ]);
        if (listRes.status === 'fulfilled') setListings(listRes.value);
        if (catRes.status === 'fulfilled') setCategories(catRes.value);
        if (salesRes.status === 'fulfilled') setSaleEvents(salesRes.value);
        if (adsRes.status === 'fulfilled') setBannerAds(adsRes.value);
      } catch { /* graceful degradation */ }
      setLoading(false);
    };
    load();
  }, []);

  const getProductImage = (listing: Listing) => listing.media?.[0]?.media_url || '';
  const getDiscountForProduct = (_listing: Listing) => {
    if (saleEvents.length === 0) return undefined;
    // If any sale is active, show its discount on random products
    return saleEvents[0]?.discount_percent;
  };

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
  // Deal products (random subset with discounts)
  const deals = listings.filter((_, i) => i % 3 === 0).slice(0, 8);

  return (
    <div className="page-content">
      {/* Hero Banner Carousel */}
      {(bannerAds.length > 0 || saleEvents.length > 0) && (
        <section className="hero-section">
          <Swiper
            modules={[Autoplay, Pagination, Navigation]}
            autoplay={{ delay: 4000, disableOnInteraction: false }}
            pagination={{ clickable: true }}
            navigation={true}
            loop={true}
            className="hero-banner"
          >
            {bannerAds.map(ad => (
              <SwiperSlide key={ad.id}>
                <img src={ad.image_url} alt={ad.title} />
                <div className="hero-overlay">
                  <h2>{ad.title}</h2>
                </div>
              </SwiperSlide>
            ))}
            {saleEvents.map(se => se.banner_image_url && (
              <SwiperSlide key={se.id}>
                <img src={se.banner_image_url} alt={se.title} />
                <div className="hero-overlay">
                  <h2>{se.title}</h2>
                  <p>{se.description}</p>
                </div>
              </SwiperSlide>
            ))}
          </Swiper>
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
              <div key={se.id} className="sale-event-card" onClick={() => navigate('/search')}>
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

      {/* Deals of the Day */}
      {deals.length > 0 && (
        <section>
          <div className="section-title" style={{ background: 'var(--bg-white)', padding: '16px 20px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', marginBottom: 0 }}>
            <span>Deals of the Day</span>
            <span className="view-all" onClick={() => navigate('/search')}>View All <ChevronRight size={14} /></span>
          </div>
          <div style={{ background: 'var(--bg-white)', padding: '0 12px 12px', borderRadius: '0 0 var(--radius-md) var(--radius-md)', border: '1px solid var(--border-card)', borderTop: 'none' }}>
            <div className="product-scroll-row">
              {deals.map(l => {
                const { rating, reviews } = pseudoRating(l.id);
                return (
                  <ProductCard
                    key={l.id}
                    id={l.id}
                    title={l.title}
                    price={l.price}
                    imageUrl={getProductImage(l)}
                    rating={rating}
                    reviewCount={reviews}
                    discountPercent={getDiscountForProduct(l)}
                  />
                );
              })}
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
            {featured.map(l => {
              const { rating, reviews } = pseudoRating(l.id);
              return (
                <ProductCard
                  key={l.id}
                  id={l.id}
                  title={l.title}
                  price={l.price}
                  imageUrl={getProductImage(l)}
                  rating={rating}
                  reviewCount={reviews}
                  discountPercent={Math.random() > 0.5 ? Math.floor(10 + Math.random() * 50) : undefined}
                />
              );
            })}
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
                {products.map(l => {
                  const { rating, reviews } = pseudoRating(l.id);
                  return (
                    <ProductCard
                      key={l.id}
                      id={l.id}
                      title={l.title}
                      price={l.price}
                      imageUrl={getProductImage(l)}
                      rating={rating}
                      reviewCount={reviews}
                    />
                  );
                })}
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
