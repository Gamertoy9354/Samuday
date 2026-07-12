import React, { createContext, useContext, useState, useCallback } from 'react';
import { walletAPI } from '../api/client';
import { useAuth } from './AuthContext';

interface WalletContextType {
  balancePaise: number;
  refreshBalance: () => Promise<void>;
}

const WalletContext = createContext<WalletContextType>({
  balancePaise: 0,
  refreshBalance: async () => {},
});

export const useWallet = () => useContext(WalletContext);

export const WalletProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [balancePaise, setBalancePaise] = useState(0);
  const { token } = useAuth();

  const refreshBalance = useCallback(async () => {
    if (!token) { setBalancePaise(0); return; }
    try {
      const data = await walletAPI.getBalance();
      setBalancePaise(data.balance ?? 0);
    } catch {
      setBalancePaise(0);
    }
  }, [token]);

  return (
    <WalletContext.Provider value={{ balancePaise, refreshBalance }}>
      {children}
    </WalletContext.Provider>
  );
};
