import React, { createContext, useContext, useState, useCallback } from 'react';
import { cartAPI } from '../api/client';
import { useAuth } from './AuthContext';

interface CartContextType {
  cartCount: number;
  refreshCart: () => Promise<void>;
  addToCart: (listingId: string, qty?: number) => Promise<boolean>;
}

const CartContext = createContext<CartContextType>({
  cartCount: 0,
  refreshCart: async () => {},
  addToCart: async () => false,
});

export const useCart = () => useContext(CartContext);

export const CartProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [cartCount, setCartCount] = useState(0);
  const { token } = useAuth();

  const refreshCart = useCallback(async () => {
    if (!token) { setCartCount(0); return; }
    try {
      const data = await cartAPI.getCount();
      setCartCount(data.count || 0);
    } catch {
      setCartCount(0);
    }
  }, [token]);

  const addToCart = async (listingId: string, qty: number = 1): Promise<boolean> => {
    if (!token) return false;
    try {
      await cartAPI.addToCart(listingId, qty);
      await refreshCart();
      return true;
    } catch {
      return false;
    }
  };

  return (
    <CartContext.Provider value={{ cartCount, refreshCart, addToCart }}>
      {children}
    </CartContext.Provider>
  );
};
