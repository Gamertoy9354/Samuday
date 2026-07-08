import React from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Smartphone, Shirt, Sprout, Home, HeartPulse, Car, GraduationCap, 
  ShoppingBag, Factory, Calendar, Building, Briefcase, Package
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

  return (
    <div className="category-bar">
      <div className="category-bar-inner">
        <button
          className={`category-bar-item ${!activeCategory ? 'active' : ''}`}
          onClick={() => navigate('/')}
        >
          All
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
