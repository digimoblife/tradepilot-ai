"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import { getMe, login as apiLogin, logout as apiLogout } from "@/lib/api/auth";
import type { LoginRequest } from "@/types/auth";

interface AuthState {
  user: { id: string; email: string } | null;
  loading: boolean;
  login: (data: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  check: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthState["user"]>(null);
  const [loading, setLoading] = useState(true);
  const initialized = useRef(false);

  if (!initialized.current) {
    initialized.current = true;
    getMe()
      .then((me) => setUser({ id: me.id, email: me.email }))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }

  const check = useCallback(async () => {
    try {
      const me = await getMe();
      setUser({ id: me.id, email: me.email });
    } catch {
      setUser(null);
    }
  }, []);

  const login = useCallback(async (data: LoginRequest) => {
    const res = await apiLogin(data);
    setUser({ id: res.id, email: res.email });
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, check }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
