import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Smartphone, Shirt, Sprout, Home, HeartPulse, Car, GraduationCap,
  ShoppingBag, Factory, Calendar, Building, Briefcase, Package, UserCheck, Users
} from 'lucide-react';

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

interface CategoryBarProps {
  categories: Array<{ id: string; name: string }>;
  activeCategory?: string | null;
}

export const CategoryBar: React.FC<CategoryBarProps> = ({ categories, activeCategory }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const isLocalMarketplace = location.search.includes('seller_tier=local');

  return (
    <div className="category-bar">
      <div className="category-bar-inner">
        <button
          className={`category-bar-item ${!activeCategory && !isLocalMarketplace ? 'active' : ''}`}
          onClick={() => navigate('/')}
        >
          All
        </button>
        <button
          className={`category-bar-item ${isLocalMarketplace ? 'active' : ''}`}
          onClick={() => navigate('/search?seller_tier=local')}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          <UserCheck size={16} /> Local Marketplace
        </button>
        <button
          className={`category-bar-item ${location.pathname === '/kutumb' ? 'active' : ''}`}
          onClick={() => navigate('/kutumb')}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          <Users size={16} /> Kutumb Network
        </button>
        {categories.map(cat => {
          const IconComp = CATEGORY_ICONS[cat.name] || Package;
          return (
            <button
              key={cat.id}
              className={`category-bar-item ${activeCategory === cat.id ? 'active' : ''}`}
              onClick={() => navigate(`/search?category=${cat.id}&name=${encodeURIComponent(cat.name)}`)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              <IconComp size={16} /> {cat.name}
            </button>
          );
        })}
      </div>
    </div>
  );
};
