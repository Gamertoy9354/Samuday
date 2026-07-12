import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { marketAPI } from '../api/client';
import { ProductCard } from '../components/product/ProductCard';
import { UserCheck } from 'lucide-react';

interface Listing {
  id: string; title: string; price: number; media: Array<{ media_url: string }>; category_id?: string;
  rating_avg?: number | null; review_count?: number; active_discount_percent?: number | null;
}

interface Category {
  id: string; name: string;
}

export const SearchPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const query = searchParams.get('q') || '';
  const categoryId = searchParams.get('category') || '';
  const categoryName = searchParams.get('name') || '';
  const sellerTier = searchParams.get('seller_tier') || '';

  const [listings, setListings] = useState<Listing[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState('relevance');
  const [selectedCats, setSelectedCats] = useState<string[]>(categoryId ? [categoryId] : []);

  useEffect(() => {
    marketAPI.getCategories().then(setCategories).catch(() => {});
  }, []);

  // Keep the category checkboxes in sync when navigating in from a category link
  useEffect(() => {
    setSelectedCats(categoryId ? [categoryId] : []);
  }, [categoryId]);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (query) params.set('query', query);
    if (sellerTier) params.set('seller_tier', sellerTier);
    marketAPI.getListings(params.toString()).then(setListings).catch(() => setListings([])).finally(() => setLoading(false));
  }, [query, sellerTier]);

  // The backend already matches `query` against title, description, and category name,
  // so results are only narrowed further by the category checkboxes here.
  let filteredListings = listings;
  if (selectedCats.length > 0) {
    filteredListings = listings.filter(l => l.category_id && selectedCats.includes(l.category_id));
  }

  // Sort (copy first — Array.sort mutates in place, and `filteredListings` may still be the `listings` state array)
  filteredListings = [...filteredListings];
  if (sortBy === 'price_low') filteredListings.sort((a, b) => a.price - b.price);
  else if (sortBy === 'price_high') filteredListings.sort((a, b) => b.price - a.price);

  const toggleCategory = (catId: string) => {
    setSelectedCats(prev => prev.includes(catId) ? prev.filter(c => c !== catId) : [...prev, catId]);
  };

  const title = query ? `Results for "${query}"` : categoryName || (sellerTier === 'local' ? 'Local Marketplace' : 'All Products');

  return (
    <div className="page-content" style={{ paddingTop: 16 }}>
      {sellerTier === 'local' && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10, padding: '12px 18px', marginBottom: 14,
          background: 'linear-gradient(135deg, var(--accent-light), var(--bg-white))', border: '1px solid var(--accent)',
          borderRadius: 'var(--radius-md)',
        }}>
          <UserCheck size={22} color="var(--accent-dark)" />
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>Local Marketplace</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Products from verified small & local sellers in your community</div>
          </div>
        </div>
      )}
      <div className="search-layout">
        {/* Sidebar Filters */}
        <aside className="search-sidebar">
          <h3>Filters</h3>
          <div className="filter-group">
            <h4>Category</h4>
            {categories.map(cat => (
              <label key={cat.id} className="filter-option">
                <input
                  type="checkbox"
                  checked={selectedCats.includes(cat.id)}
                  onChange={() => toggleCategory(cat.id)}
                />
                {cat.name}
              </label>
            ))}
          </div>
        </aside>

        {/* Results */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 600 }}>
              {title}
              <span style={{ fontWeight: 400, color: 'var(--text-muted)', fontSize: '0.85rem', marginLeft: 8 }}>
                ({filteredListings.length} results)
              </span>
            </h2>
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value)}
              style={{ padding: '6px 12px', border: '1px solid var(--border-input)', borderRadius: 'var(--radius-sm)', fontSize: '0.85rem', fontFamily: 'inherit' }}
            >
              <option value="relevance">Relevance</option>
              <option value="price_low">Price: Low to High</option>
              <option value="price_high">Price: High to Low</option>
            </select>
          </div>

          {loading ? (
            <div className="products-grid">
              {[...Array(8)].map((_, i) => (
                <div key={i} style={{ background: 'white', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
                  <div className="skeleton" style={{ height: 200 }} />
                  <div style={{ padding: 14 }}>
                    <div className="skeleton" style={{ height: 16, marginBottom: 8 }} />
                    <div className="skeleton" style={{ height: 14, width: '60%' }} />
                  </div>
                </div>
              ))}
            </div>
          ) : filteredListings.length === 0 ? (
            <div className="empty-state">
              <h3>No products found</h3>
              <p>Try a different search term or browse categories</p>
            </div>
          ) : (
            <div className="products-grid">
              {filteredListings.map(l => (
                <ProductCard
                  key={l.id}
                  id={l.id}
                  title={l.title}
                  price={l.price}
                  imageUrl={l.media?.[0]?.media_url}
                  rating={l.rating_avg ?? undefined}
                  reviewCount={l.review_count}
                  discountPercent={l.active_discount_percent ?? undefined}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
