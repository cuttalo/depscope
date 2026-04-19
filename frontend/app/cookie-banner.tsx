"use client";

import { useState, useEffect } from "react";

export default function CookieBanner() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem("ds_cookie_ok")) {
      setShow(true);
    }
  }, []);

  if (!show) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4 bg-[var(--bg-card)] border-t border-[var(--border)]">
      <div className="max-w-4xl mx-auto flex items-center justify-between gap-4 flex-wrap">
        <p className="text-sm text-[var(--text-dim)]">
          This site uses only essential cookies for session management. No tracking, no analytics cookies, no third-party cookies.{" "}
          <a href="/privacy" className="text-[var(--accent)] hover:underline">Privacy Policy</a>
        </p>
        <button
          onClick={() => { localStorage.setItem("ds_cookie_ok", "1"); setShow(false); }}
          className="px-4 py-2 bg-[var(--accent)] text-black text-sm font-semibold rounded-lg hover:bg-[var(--accent-dim)] transition whitespace-nowrap"
        >
          Got it
        </button>
      </div>
    </div>
  );
}
