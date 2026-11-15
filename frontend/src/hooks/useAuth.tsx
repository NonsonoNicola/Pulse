import { createContext, useContext, useState, useEffect } from 'react';
import { login as apiLogin, logout as apiLogout, me, updatePreferences as apiUpdatePreferences } from '../api/client';
import type { User } from '../types';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  savePreferences: (payload: { locale?: string; explanation_level?: string }) => Promise<User>;
  hasRole: (roles: string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const login = async (username: string, password: string) => {
    const { user } = await apiLogin(username, password);
    setUser(user);
    return user;
  };

  const logout = async () => {
    await apiLogout();
    setUser(null);
  };

  const savePreferences = async (payload: { locale?: string; explanation_level?: string }) => {
    const updated = await apiUpdatePreferences(payload);
    setUser(updated);
    return updated;
  };

  const hasRole = (roles: string[]) => {
    if (!user) return false;
    return roles.includes(user.role);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, savePreferences, hasRole }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}