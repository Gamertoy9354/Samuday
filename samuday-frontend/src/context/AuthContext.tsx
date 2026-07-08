import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authAPI } from '../api/client';

interface User {
  id: string;
  full_name: string;
  email?: string;
  avatar_url?: string;
  is_seller: boolean;
  phone_number?: string;
  preferred_language: string;
  status: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  loading: true,
  login: async () => {},
  logout: () => {},
  refreshUser: async () => {},
});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = useCallback(async (jwt: string) => {
    try {
      localStorage.setItem('samuday_token', jwt);
      const userData = await authAPI.getMe();
      setUser(userData);
      setToken(jwt);
    } catch {
      localStorage.removeItem('samuday_token');
      setUser(null);
      setToken(null);
    }
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem('samuday_token');
    if (stored) {
      fetchUser(stored).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [fetchUser]);

  const login = async (jwt: string) => {
    await fetchUser(jwt);
  };

  const logout = () => {
    localStorage.removeItem('samuday_token');
    setUser(null);
    setToken(null);
  };

  const refreshUser = async () => {
    const stored = localStorage.getItem('samuday_token');
    if (stored) await fetchUser(stored);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};
