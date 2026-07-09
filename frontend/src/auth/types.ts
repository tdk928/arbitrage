export type UserRole = "anonymous" | "client" | "admin";

export type AuthSession = {
  role: UserRole;
  email: string | null;
  hasActiveSubscription: boolean;
  expiresAt: number | null;
};

export type TokenClaims = {
  sub: string;
  email: string;
  role: "client" | "admin";
  has_active_subscription: boolean;
  iat: number;
  exp: number;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};
