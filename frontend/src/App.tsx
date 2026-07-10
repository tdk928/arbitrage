import { FormEvent, useState } from "react";

import { useAuth } from "./auth/AuthContext";

type Mode = "login" | "register";

export default function App() {
  const { session, loading, login, register, logout } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <main>Loading session...</main>;
  }

  return (
    <main style={{ fontFamily: "sans-serif", maxWidth: 420, margin: "2rem auto" }}>
      <h1>Arbitrage Auth</h1>

      <section style={{ marginBottom: "1.5rem" }}>
        <p>Role: <strong>{session.role}</strong></p>
        <p>Email: {session.email ?? "—"}</p>
        <p>Active subscription: {session.hasActiveSubscription ? "yes" : "no"}</p>
        <p>
          Token expires:{" "}
          {session.expiresAt ? new Date(session.expiresAt).toLocaleString() : "—"}
        </p>
      </section>

      {session.role === "anonymous" ? (
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "0.75rem" }}>
            <button type="button" onClick={() => setMode("login")} disabled={mode === "login"}>
              Login
            </button>{" "}
            <button
              type="button"
              onClick={() => setMode("register")}
              disabled={mode === "register"}
            >
              Register
            </button>
          </div>

          <label style={{ display: "block", marginBottom: "0.5rem" }}>
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              style={{ display: "block", width: "100%" }}
            />
          </label>

          <label style={{ display: "block", marginBottom: "0.75rem" }}>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              minLength={mode === "register" ? 8 : 1}
              style={{ display: "block", width: "100%" }}
            />
          </label>

          {error ? <p style={{ color: "crimson" }}>{error}</p> : null}

          <button type="submit" disabled={submitting}>
            {submitting ? "Please wait..." : mode === "login" ? "Login" : "Register"}
          </button>
        </form>
      ) : (
        <button type="button" onClick={logout}>
          Logout
        </button>
      )}
    </main>
  );
}
