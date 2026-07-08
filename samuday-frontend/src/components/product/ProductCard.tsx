import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Star } from 'lucide-react';

interface ProductCardProps {
  id: string;
  title: string;
  price: number;
  imageUrl?: string;
  rating?: number;
  reviewCount?: number;
  discountPercent?: number;
}

export const ProductCard: React.FC<ProductCardProps> = ({
  id, title, price, imageUrl, rating, reviewCount, discountPercent
}) => {
  const navigate = useNavigate();
  const displayPrice = price / 100; // paise to rupees
  const originalPrice = discountPercent ? Math.round(displayPrice / (1 - discountPercent / 100)) : null;

  return (
    <div className="product-card" onClick={() => navigate(`/product/${id}`)}>
      <img
        className="product-card-image"
        src={imageUrl || 'https://via.placeholder.com/300x300?text=Product'}
        alt={title}
        loading="lazy"
        onError={e => { (e.target as HTMLImageElement).src = 'https://via.placeholder.com/300x300?text=Product'; }}
      />
      <div className="product-card-body">
        <div className="product-card-title">{title}</div>
        
        {rating !== undefined && (
          <div className="product-card-rating">
            <span className="rating-badge">
              {rating.toFixed(1)} <Star size={10} fill="white" />
            </span>
            {reviewCount !== undefined && (
              <span className="rating-count">({reviewCount.toLocaleString()})</span>
            )}
          </div>
        )}

        <div className="product-card-price">
          <span className="price-current">&#8377;{displayPrice.toLocaleString('en-IN')}</span>
          {originalPrice && (
            <>
              <span className="price-original">&#8377;{originalPrice.toLocaleString('en-IN')}</span>
              <span className="price-discount">{discountPercent}% off</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
