"use client";
import { useState } from "react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const r = await fetch("/api/auth/magic-link/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(d.detail || d.error || "Request failed");
      }
      setSent(true);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to send";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-68px)] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-2">Sign in to DepScope</h1>
        <p className="text-sm text-[var(--text-dim)] mb-8">
          Enter your email. We&apos;ll send you a magic link.
        </p>

        {!sent ? (
          <form onSubmit={submit} className="space-y-3">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoFocus
              className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-4 py-3 text-base focus:outline-none focus:border-[var(--accent)]"
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[var(--accent)] text-black font-semibold rounded-lg px-4 py-3 hover:bg-[var(--accent-dim)] disabled:opacity-50 transition"
            >
              {loading ? "Sending..." : "Send magic link"}
            </button>
            {error && <p className="text-red-400 text-sm">{error}</p>}
          </form>
        ) : (
          <div className="card p-6 text-center">
            <div className="text-3xl mb-3">📧</div>
            <h2 className="font-semibold mb-2">Check your inbox</h2>
            <p className="text-sm text-[var(--text-dim)]">
              We sent a magic link to <strong>{email}</strong>. Click it to sign in.
            </p>
            <p className="text-xs text-[var(--text-dim)] mt-4">
              The link expires in 15 minutes. Not in inbox? Check spam.
            </p>
          </div>
        )}

        <p className="text-xs text-[var(--text-dim)] mt-8 text-center">
          By signing in, you agree to our{" "}
          <a href="/privacy" className="underline">
            Privacy Policy
          </a>
          .
        </p>
      </div>
    </div>
  );
}
