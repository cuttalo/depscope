"use client";

import { useState, useEffect } from "react";

type Consent = {
  necessary: true;
  analytics: boolean;
  marketing: boolean;
  ts: string;
};

const STORAGE_KEY = "ds_consent";
const TTL_DAYS = 180; // Garante: re-ask every 6 months

function loadConsent(): Consent | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Consent;
    const age = Date.now() - new Date(parsed.ts).getTime();
    if (age > TTL_DAYS * 86400 * 1000) return null;
    return parsed;
  } catch {
    return null;
  }
}

function saveConsent(c: Omit<Consent, "ts">) {
  const payload: Consent = { ...c, ts: new Date().toISOString() };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {}
}

export default function CookieBanner() {
  const [show, setShow] = useState(false);
  const [panel, setPanel] = useState(false);
  const [analytics, setAnalytics] = useState(false);
  const [marketing, setMarketing] = useState(false);

  useEffect(() => {
    if (!loadConsent()) setShow(true);

    // Re-open via footer link
    const handler = () => setShow(true);
    window.addEventListener("ds:open-cookie-settings", handler);
    return () =>
      window.removeEventListener("ds:open-cookie-settings", handler);
  }, []);

  if (!show) return null;

  const close = (c: Omit<Consent, "ts">) => {
    saveConsent(c);
    setShow(false);
    setPanel(false);
  };

  const acceptAll = () =>
    close({ necessary: true, analytics: true, marketing: true });
  const rejectAll = () =>
    close({ necessary: true, analytics: false, marketing: false });
  const saveCustom = () =>
    close({ necessary: true, analytics, marketing });

  return (
    <div
      role="dialog"
      aria-labelledby="cookie-banner-title"
      aria-modal="false"
      className="fixed bottom-0 left-0 right-0 z-50 p-4 bg-[var(--bg-card)] border-t border-[var(--border)]"
    >
      <div className="max-w-4xl mx-auto">
        {!panel && (
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="text-sm text-[var(--text-dim)]">
              <div
                id="cookie-banner-title"
                className="font-semibold text-[var(--text)] mb-1"
              >
                Cookies on depscope.dev
              </div>
              <p>
                We use strictly-necessary cookies for authentication and
                security. Optional categories (analytics, marketing) are off by
                default and require your consent. You can change your choice at
                any time from the footer.{" "}
                <a
                  href="/cookies"
                  className="text-[var(--accent)] hover:underline"
                >
                  Read the Cookie Policy
                </a>
                .
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={rejectAll}
                aria-label="Reject all non-essential cookies"
                className="px-4 py-2 border border-[var(--border)] text-[var(--text)] text-sm font-semibold rounded-lg hover:bg-[var(--bg-soft)] transition whitespace-nowrap"
              >
                Reject all
              </button>
              <button
                onClick={() => setPanel(true)}
                className="px-4 py-2 border border-[var(--border)] text-[var(--text-dim)] text-sm font-medium rounded-lg hover:bg-[var(--bg-soft)] transition whitespace-nowrap"
              >
                Customize
              </button>
              <button
                onClick={acceptAll}
                aria-label="Accept all cookies"
                className="px-4 py-2 bg-[var(--accent)] text-black text-sm font-semibold rounded-lg hover:bg-[var(--accent-dim)] transition whitespace-nowrap"
              >
                Accept all
              </button>
            </div>
          </div>
        )}

        {panel && (
          <div className="space-y-3">
            <div className="font-semibold text-[var(--text)]">
              Cookie preferences
            </div>
            <div className="flex items-center justify-between gap-4 border-t border-[var(--border)] pt-3">
              <div>
                <div className="text-sm font-medium text-[var(--text)]">
                  Strictly necessary
                </div>
                <p className="text-xs text-[var(--text-dim)]">
                  Required for login, CSRF, and storing your cookie preference.
                  Cannot be disabled.
                </p>
              </div>
              <span className="text-xs text-[var(--text-dim)]">Always on</span>
            </div>
            <div className="flex items-center justify-between gap-4 border-t border-[var(--border)] pt-3">
              <div>
                <div className="text-sm font-medium text-[var(--text)]">
                  Analytics
                </div>
                <p className="text-xs text-[var(--text-dim)]">
                  Anonymized, aggregate usage metrics. Not yet in use.
                </p>
              </div>
              <label className="inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={analytics}
                  onChange={(e) => setAnalytics(e.target.checked)}
                />
                <span className="w-10 h-5 bg-[var(--border)] rounded-full relative peer-checked:bg-[var(--accent)] transition">
                  <span
                    className={
                      "absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition " +
                      (analytics ? "translate-x-5" : "")
                    }
                  />
                </span>
              </label>
            </div>
            <div className="flex items-center justify-between gap-4 border-t border-[var(--border)] pt-3">
              <div>
                <div className="text-sm font-medium text-[var(--text)]">
                  Marketing
                </div>
                <p className="text-xs text-[var(--text-dim)]">
                  None used today. Toggle only activates if we introduce any.
                </p>
              </div>
              <label className="inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={marketing}
                  onChange={(e) => setMarketing(e.target.checked)}
                />
                <span className="w-10 h-5 bg-[var(--border)] rounded-full relative peer-checked:bg-[var(--accent)] transition">
                  <span
                    className={
                      "absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition " +
                      (marketing ? "translate-x-5" : "")
                    }
                  />
                </span>
              </label>
            </div>
            <div className="flex flex-wrap gap-2 justify-end pt-2">
              <button
                onClick={rejectAll}
                className="px-4 py-2 border border-[var(--border)] text-[var(--text)] text-sm font-semibold rounded-lg hover:bg-[var(--bg-soft)] transition"
              >
                Reject all
              </button>
              <button
                onClick={saveCustom}
                className="px-4 py-2 bg-[var(--accent)] text-black text-sm font-semibold rounded-lg hover:bg-[var(--accent-dim)] transition"
              >
                Save preferences
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
