import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { returnsAPI } from '../services/api';
import { useAuth } from './AuthContext';

const ReturnsBadgeContext = createContext({ pending: 0, approved: 0 });

export function ReturnsBadgeProvider({ children }) {
  const { user } = useAuth();
  const [counts, setCounts] = useState({ pending: 0, approved: 0 });

  const refresh = useCallback(async () => {
    if (!user) return;
    try {
      const res = await returnsAPI.getStats();
      setCounts({
        pending:  res.data?.pending?.count  ?? 0,
        approved: res.data?.approved?.count ?? 0,
      });
    } catch {
      // صامت — مش نكسر الـ UI لو الـ API فشل
    }
  }, [user]);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 60_000);   // كل دقيقة
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <ReturnsBadgeContext.Provider value={{ ...counts, refresh }}>
      {children}
    </ReturnsBadgeContext.Provider>
  );
}

export const useReturnsBadge = () => useContext(ReturnsBadgeContext);
