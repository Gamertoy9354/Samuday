import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authAPI, setTokens, clearTokens } from '../api/client';

interface User {
  id: string;
  full_name: string;
  email?: string;
  avatar_url?: string;
  is_seller: boolean;
  is_admin: boolean;
  seller_tier?: 'official' | 'local' | null;
  seller_verification_status: 'unverified' | 'pending' | 'approved' | 'rejected';
  phone_number?: string;
  alternate_phone?: string;
  gender?: string;
  date_of_birth?: string;
  profile_bio?: string;
  preferred_language: string;
  status: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (token: string, refreshToken?: string) => Promise<void>;
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
      clearTokens();
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

  // A 401 that survives the API client's own refresh-token retry means the
  // session is truly over (refresh token missing/expired too) — reflect that
  // in React state immediately rather than leaving stale "logged in" UI up.
  useEffect(() => {
    const onSessionExpired = () => {
      setUser(null);
      setToken(null);
    };
    window.addEventListener('samuday:session-expired', onSessionExpired);
    return () => window.removeEventListener('samuday:session-expired', onSessionExpired);
  }, []);

  const login = async (jwt: string, refreshTokenValue?: string) => {
    setTokens(jwt, refreshTokenValue);
    await fetchUser(jwt);
  };

  const logout = () => {
    clearTokens();
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
