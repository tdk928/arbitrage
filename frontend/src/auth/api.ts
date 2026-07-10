import type { TokenResponse } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function postJson<T>(path: string, body: Record<string, string>): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : "Request failed";
    throw new Error(detail);
  }

  return data as T;
}

export function register(email: string, password: string): Promise<TokenResponse> {
  return postJson<TokenResponse>("/auth/register", { email, password });
}

export function login(email: string, password: string): Promise<TokenResponse> {
  return postJson<TokenResponse>("/auth/login", { email, password });
}
