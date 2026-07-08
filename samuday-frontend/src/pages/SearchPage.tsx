import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { marketAPI } from '../api/client';
import { ProductCard } from '../components/product/ProductCard';

interface Listing {
  id: string; title: string; price: number; media: Array<{ media_url: string }>; category_id?: string;
}

interface Category {
  id: string; name: string;
}

function pseudoRating(id: string) {
  let hash = 0;
  for (let i = 0; i < id.length; i++) { hash = ((hash << 5) - hash) + id.charCodeAt(i); hash |= 0; }
  return { rating: Math.min(3.5 + (Math.abs(hash) % 15) / 10, 4.9), reviews: 100 + (Math.abs(hash) % 9900) };
}

export const SearchPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const query = searchParams.get('q') || '';
  const categoryId = searchParams.get('category') || '';
  const categoryName = searchParams.get('name') || '';

  const [listings, setListings] = useState<Listing[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState('relevance');
  const [selectedCats, setSelectedCats] = useState<string[]>(categoryId ? [categoryId] : []);

  useEffect(() => {
    marketAPI.getCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (query) params.set('query', query);
    if (categoryId) params.set('category_id', categoryId);
    marketAPI.getListings(params.toString()).then(setListings).catch(() => {}).finally(() => setLoading(false));
  }, [query, categoryId]);

  let filteredListings = listings;
  if (selectedCats.length > 0 && !categoryId) {
    filteredListings = listings.filter(l => l.category_id && selectedCats.includes(l.category_id));
  }
  if (query) {
    const q = query.toLowerCase();
    filteredListings = filteredListings.filter(l => l.title.toLowerCase().includes(q));
  }

  // Sort
  if (sortBy === 'price_low') filteredListings.sort((a, b) => a.price - b.price);
  else if (sortBy === 'price_high') filteredListings.sort((a, b) => b.price - a.price);

  const toggleCategory = (catId: string) => {
    setSelectedCats(prev => prev.includes(catId) ? prev.filter(c => c !== catId) : [...prev, catId]);
  };

  const title = query ? `Results for "${query}"` : categoryName || 'All Products';

  return (
    <div className="page-content" style={{ paddingTop: 16 }}>
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
              {filteredListings.map(l => {
                const { rating, reviews } = pseudoRating(l.id);
                return (
                  <ProductCard
                    key={l.id}
                    id={l.id}
                    title={l.title}
                    price={l.price}
                    imageUrl={l.media?.[0]?.media_url}
                    rating={rating}
                    reviewCount={reviews}
                    discountPercent={Math.random() > 0.6 ? Math.floor(10 + Math.random() * 40) : undefined}
                  />
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
