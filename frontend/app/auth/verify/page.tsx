"use client";
import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";

function VerifyInner() {
  const params = useSearchParams();
  const router = useRouter();
  const token = params.get("token");
  const [status, setStatus] = useState<"verifying" | "ok" | "error">("verifying");
  const [message, setMessage] = useState("Verifying your sign-in link...");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Missing token. Request a new magic link.");
      return;
    }
    (async () => {
      try {
        const r = await fetch("/api/auth/magic-link/verify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
          credentials: "include",
        });
        if (!r.ok) {
          const d = await r.json().catch(() => ({}));
          throw new Error(d.detail || d.error || "Verification failed");
        }
        setStatus("ok");
        setMessage("Signed in. Redirecting...");
        setTimeout(() => router.replace("/dashboard"), 600);
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "Verification failed";
        setStatus("error");
        setMessage(msg);
      }
    })();
  }, [token, router]);

  return (
    <div className="min-h-[calc(100vh-68px)] flex items-center justify-center px-4">
      <div className="w-full max-w-sm card p-8 text-center">
        <div className="text-4xl mb-4">
          {status === "verifying" ? "⏳" : status === "ok" ? "✅" : "⚠️"}
        </div>
        <h1 className="text-xl font-semibold mb-2">
          {status === "verifying"
            ? "Verifying..."
            : status === "ok"
            ? "Signed in"
            : "Sign-in failed"}
        </h1>
        <p className="text-sm text-[var(--text-dim)]">{message}</p>
        {status === "error" && (
          <a
            href="/login"
            className="inline-block mt-6 text-[var(--accent)] hover:underline text-sm"
          >
            Request a new link
          </a>
        )}
      </div>
    </div>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-[var(--text-dim)]">Loading...</div>}>
      <VerifyInner />
    </Suspense>
  );
}
