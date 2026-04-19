"use client";

import { useState, useEffect } from "react";

export default function CookieBannerZh() {
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
          本站仅使用必要Cookie。无追踪，无分析Cookie，无第三方Cookie。{" "}
          <a href="/privacy" className="text-[var(--accent)] hover:underline">隐私政策</a>
        </p>
        <button
          onClick={() => { localStorage.setItem("ds_cookie_ok", "1"); setShow(false); }}
          className="px-4 py-2 bg-[var(--accent)] text-black text-sm font-semibold rounded-lg hover:bg-[var(--accent-dim)] transition whitespace-nowrap"
        >
          知道了
        </button>
      </div>
    </div>
  );
}
