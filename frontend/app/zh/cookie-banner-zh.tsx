"use client";

import { useState, useEffect } from "react";

type Consent = {
  necessary: true;
  analytics: boolean;
  marketing: boolean;
  ts: string;
};

const STORAGE_KEY = "ds_consent";
const TTL_DAYS = 180;

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

export default function CookieBannerZh() {
  const [show, setShow] = useState(false);
  const [panel, setPanel] = useState(false);
  const [analytics, setAnalytics] = useState(false);
  const [marketing, setMarketing] = useState(false);

  useEffect(() => {
    if (!loadConsent()) setShow(true);
    const handler = () => setShow(true);
    window.addEventListener("ds:open-cookie-settings", handler);
    return () => window.removeEventListener("ds:open-cookie-settings", handler);
  }, []);

  if (!show) return null;

  const close = (c: Omit<Consent, "ts">) => {
    saveConsent(c);
    setShow(false);
    setPanel(false);
  };

  const acceptAll = () => close({ necessary: true, analytics: true, marketing: true });
  const rejectAll = () => close({ necessary: true, analytics: false, marketing: false });
  const saveCustom = () => close({ necessary: true, analytics, marketing });

  return (
    <div role="dialog" aria-labelledby="cookie-banner-title" className="fixed bottom-0 left-0 right-0 z-50 p-4 bg-[var(--bg-card)] border-t border-[var(--border)]">
      <div className="max-w-4xl mx-auto">
        {!panel && (
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="text-sm text-[var(--text-dim)]">
              <div id="cookie-banner-title" className="font-semibold text-[var(--text)] mb-1">
                depscope.dev 上的 Cookie
              </div>
              <p>
                我们使用严格必要的 Cookie 用于身份验证和安全。可选类别（分析、营销）默认关闭，
                需要您同意。您可随时在页脚更改选择。{" "}
                <a href="/zh/cookies" className="text-[var(--accent)] hover:underline">
                  阅读 Cookie 政策
                </a>
                。
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button onClick={rejectAll} aria-label="拒绝所有非必要 Cookie" className="px-4 py-2 border border-[var(--border)] text-[var(--text)] text-sm font-semibold rounded-lg hover:bg-[var(--bg-soft)] transition whitespace-nowrap">
                全部拒绝
              </button>
              <button onClick={() => setPanel(true)} className="px-4 py-2 border border-[var(--border)] text-[var(--text-dim)] text-sm font-medium rounded-lg hover:bg-[var(--bg-soft)] transition whitespace-nowrap">
                自定义
              </button>
              <button onClick={acceptAll} aria-label="接受所有 Cookie" className="px-4 py-2 bg-[var(--accent)] text-black text-sm font-semibold rounded-lg hover:bg-[var(--accent-dim)] transition whitespace-nowrap">
                全部接受
              </button>
            </div>
          </div>
        )}

        {panel && (
          <div className="space-y-3">
            <div className="font-semibold text-[var(--text)]">Cookie 偏好</div>
            <div className="flex items-center justify-between gap-4 border-t border-[var(--border)] pt-3">
              <div>
                <div className="text-sm font-medium text-[var(--text)]">严格必要</div>
                <p className="text-xs text-[var(--text-dim)]">登录、CSRF 及存储您的 Cookie 偏好所必需。不能禁用。</p>
              </div>
              <span className="text-xs text-[var(--text-dim)]">始终启用</span>
            </div>
            <div className="flex items-center justify-between gap-4 border-t border-[var(--border)] pt-3">
              <div>
                <div className="text-sm font-medium text-[var(--text)]">分析</div>
                <p className="text-xs text-[var(--text-dim)]">匿名的、汇总的使用指标。尚未使用。</p>
              </div>
              <label className="inline-flex items-center cursor-pointer">
                <input type="checkbox" className="sr-only peer" checked={analytics} onChange={(e) => setAnalytics(e.target.checked)} />
                <span className="w-10 h-5 bg-[var(--border)] rounded-full relative peer-checked:bg-[var(--accent)] transition">
                  <span className={"absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition " + (analytics ? "translate-x-5" : "")} />
                </span>
              </label>
            </div>
            <div className="flex items-center justify-between gap-4 border-t border-[var(--border)] pt-3">
              <div>
                <div className="text-sm font-medium text-[var(--text)]">营销</div>
                <p className="text-xs text-[var(--text-dim)]">目前未使用。切换仅在引入时激活。</p>
              </div>
              <label className="inline-flex items-center cursor-pointer">
                <input type="checkbox" className="sr-only peer" checked={marketing} onChange={(e) => setMarketing(e.target.checked)} />
                <span className="w-10 h-5 bg-[var(--border)] rounded-full relative peer-checked:bg-[var(--accent)] transition">
                  <span className={"absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition " + (marketing ? "translate-x-5" : "")} />
                </span>
              </label>
            </div>
            <div className="flex flex-wrap gap-2 justify-end pt-2">
              <button onClick={rejectAll} className="px-4 py-2 border border-[var(--border)] text-[var(--text)] text-sm font-semibold rounded-lg hover:bg-[var(--bg-soft)] transition">
                全部拒绝
              </button>
              <button onClick={saveCustom} className="px-4 py-2 bg-[var(--accent)] text-black text-sm font-semibold rounded-lg hover:bg-[var(--accent-dim)] transition">
                保存偏好
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
