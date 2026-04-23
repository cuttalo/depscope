"use client";

// Centralised fetch helper for admin pages. Handles:
//   - 401/403 → setNeedsAuth(true) so the page shows a login prompt
//   - non-ok HTTP → throws with message including status + body detail
//   - non-JSON body → returns {} gracefully
import { useEffect, useState } from "react";

export interface AdminState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  needsAuth: boolean;
}

export function useAdmin<T = any>(path: string): AdminState<T> {
  const [state, setState] = useState<AdminState<T>>({
    data: null, loading: true, error: null, needsAuth: false,
  });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(path, { credentials: "include" });
        if (r.status === 401 || r.status === 403) {
          if (!cancelled) {
            setState({ data: null, loading: false, error: null, needsAuth: true });
            if (typeof window !== "undefined" && !window.location.pathname.startsWith("/admin-login")) {
              const next = encodeURIComponent(window.location.pathname + window.location.search);
              window.location.href = `/admin-login?next=${next}`;
            }
          }
          return;
        }
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        let body: any;
        const ct = r.headers.get("content-type") || "";
        if (ct.includes("application/json")) {
          body = await r.json();
        } else {
          body = await r.text();
        }
        if (!cancelled) setState({ data: body, loading: false, error: null, needsAuth: false });
      } catch (e: any) {
        if (!cancelled) setState({ data: null, loading: false, error: e.message || "error", needsAuth: false });
      }
    })();
    return () => { cancelled = true; };
  }, [path]);

  return state;
}

// Combine multiple admin endpoints
export function useAdminMany<T extends Record<string, any>>(paths: Record<keyof T, string>): {
  data: Partial<T>;
  loading: boolean;
  errors: Partial<Record<keyof T, string>>;
  needsAuth: boolean;
} {
  const [state, setState] = useState<any>({ data: {}, loading: true, errors: {}, needsAuth: false });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const entries = Object.entries(paths) as [string, string][];
      const results = await Promise.all(entries.map(async ([k, p]) => {
        try {
          const r = await fetch(p, { credentials: "include" });
          if (r.status === 401 || r.status === 403) return [k, { _auth: true }] as const;
          if (!r.ok) return [k, { _err: `HTTP ${r.status}` }] as const;
          const ct = r.headers.get("content-type") || "";
          const body = ct.includes("application/json") ? await r.json() : await r.text();
          return [k, body] as const;
        } catch (e: any) {
          return [k, { _err: e.message }] as const;
        }
      }));
      if (cancelled) return;
      const data: any = {}; const errors: any = {};
      let needsAuth = false;
      for (const [k, v] of results) {
        if (v && (v as any)._auth) { needsAuth = true; continue; }
        if (v && (v as any)._err) { errors[k] = (v as any)._err; continue; }
        data[k] = v;
      }
      setState({ data, loading: false, errors, needsAuth });
      if (needsAuth && typeof window !== "undefined" && !window.location.pathname.startsWith("/admin-login")) {
        const next = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.href = `/admin-login?next=${next}`;
      }
    })();
    return () => { cancelled = true; };
  }, [JSON.stringify(paths)]);

  return state;
}

// Always-array coerce
export function asArray(x: any): any[] {
  if (Array.isArray(x)) return x;
  if (x && typeof x === "object") {
    for (const k of ["items", "results", "rows", "list", "data", "emails",
                      "opportunities", "packages", "endpoints", "sources",
                      "user_agents", "by_ua", "by_endpoint", "hourly"]) {
      if (Array.isArray(x[k])) return x[k];
    }
  }
  return [];
}

// UI: shared auth banner
export function NeedsAuthBanner() {
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  return (
    <div className="rounded-lg p-5 text-sm"
         style={{ background: "var(--bg-card)", border: "1px solid var(--red)",
                  color: "var(--text-dim)" }}>
      <strong style={{ color: "var(--red)" }}>Not authorized.</strong>
      <br />
      Open <a className="underline" style={{ color: "var(--accent)" }}
              href={`${origin}/login`}>{origin}/login</a> and sign in with your admin account.
      Session cookies are scoped per-subdomain: if you logged in on depscope.dev
      but are viewing stage.depscope.dev (or vice-versa), you'll need to log in
      here separately.
    </div>
  );
}
