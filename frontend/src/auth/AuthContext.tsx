import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { login as loginRequest, register as registerRequest } from "./api";
import {
  anonymousSession,
  clearStoredToken,
  getStoredToken,
  isTokenExpired,
  parseTokenClaims,
  storeToken,
  validateStoredToken,
} from "./token";
import type { AuthSession } from "./types";

type AuthContextValue = {
  session: AuthSession;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function sessionFromToken(token: string): AuthSession {
  const claims = parseTokenClaims(token);
  if (!claims || isTokenExpired(claims)) {
    clearStoredToken();
    return anonymousSession();
  }

  return {
    role: claims.role,
    email: claims.email,
    hasActiveSubscription: claims.has_active_subscription,
    expiresAt: claims.exp * 1000,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession>(anonymousSession());
  const [loading, setLoading] = useState(true);

  const refreshSession = useCallback(() => {
    setSession(validateStoredToken(getStoredToken()));
  }, []);

  useEffect(() => {
    refreshSession();
    setLoading(false);
  }, [refreshSession]);

  useEffect(() => {
    if (!session.expiresAt) {
      return;
    }

    const delay = session.expiresAt - Date.now();
    if (delay <= 0) {
      clearStoredToken();
      setSession(anonymousSession());
      return;
    }

    const timer = window.setTimeout(() => {
      clearStoredToken();
      setSession(anonymousSession());
    }, delay);

    return () => window.clearTimeout(timer);
  }, [session.expiresAt]);

  const applyToken = useCallback((token: string) => {
    storeToken(token);
    setSession(sessionFromToken(token));
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await loginRequest(email, password);
      applyToken(response.access_token);
    },
    [applyToken],
  );

  const register = useCallback(
    async (email: string, password: string) => {
      const response = await registerRequest(email, password);
      applyToken(response.access_token);
    },
    [applyToken],
  );

  const logout = useCallback(() => {
    clearStoredToken();
    setSession(anonymousSession());
  }, []);

  const value = useMemo(
    () => ({
      session,
      loading,
      login,
      register,
      logout,
    }),
    [session, loading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
