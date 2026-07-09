import type { AuthSession, TokenClaims } from "./types";

const TOKEN_STORAGE_KEY = "arbitrage_access_token";

type JwtPayload = TokenClaims & Record<string, unknown>;

function decodeBase64Url(value: string): string {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  return atob(padded);
}

export function parseTokenClaims(token: string): TokenClaims | null {
  const parts = token.split(".");
  if (parts.length !== 3) {
    return null;
  }

  try {
    const payload = JSON.parse(decodeBase64Url(parts[1])) as JwtPayload;
    if (
      typeof payload.sub !== "string" ||
      typeof payload.email !== "string" ||
      (payload.role !== "client" && payload.role !== "admin") ||
      typeof payload.has_active_subscription !== "boolean" ||
      typeof payload.exp !== "number" ||
      typeof payload.iat !== "number"
    ) {
      return null;
    }

    return {
      sub: payload.sub,
      email: payload.email,
      role: payload.role,
      has_active_subscription: payload.has_active_subscription,
      iat: payload.iat,
      exp: payload.exp,
    };
  } catch {
    return null;
  }
}

export function isTokenExpired(claims: TokenClaims, nowMs: number = Date.now()): boolean {
  return claims.exp * 1000 <= nowMs;
}

export function validateStoredToken(token: string | null): AuthSession {
  if (!token) {
    return anonymousSession();
  }

  const claims = parseTokenClaims(token);
  if (!claims || isTokenExpired(claims)) {
    return anonymousSession();
  }

  return {
    role: claims.role,
    email: claims.email,
    hasActiveSubscription: claims.has_active_subscription,
    expiresAt: claims.exp * 1000,
  };
}

export function anonymousSession(): AuthSession {
  return {
    role: "anonymous",
    email: null,
    hasActiveSubscription: false,
    expiresAt: null,
  };
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function storeToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}
