"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface PageItem {
  id: string;
  label: string;
  hint?: string;
  href: string;
  kind: "page" | "action" | "recent";
}

const PAGES: PageItem[] = [
  { id: "home", label: "Packages", hint: "search any package", href: "/", kind: "page" },
  { id: "explore", label: "Explore", hint: "trending, errors, compat, bugs", href: "/explore", kind: "page" },
  { id: "trending", label: "Trending", hint: "what agents are searching", href: "/explore/trending", kind: "page" },
  { id: "errors", label: "Errors", hint: "error → fix database", href: "/explore/errors", kind: "page" },
  { id: "compat", label: "Compat", hint: "stack compatibility", href: "/explore/compat", kind: "page" },
  { id: "bugs", label: "Bugs", hint: "known bugs per version", href: "/explore/bugs", kind: "page" },
  { id: "popular", label: "Popular", hint: "most-searched packages", href: "/popular", kind: "page" },
  { id: "api-docs", label: "API Docs", hint: "endpoints, auth, examples", href: "/api-docs", kind: "page" },
  { id: "integrate", label: "Integrate", hint: "add DepScope to your agent", href: "/integrate", kind: "page" },
  { id: "stats", label: "Stats", hint: "live numbers", href: "/stats", kind: "page" },
  { id: "dashboard", label: "Dashboard", hint: "your account", href: "/dashboard", kind: "page" },
  { id: "api-keys", label: "API Keys", hint: "manage keys", href: "/account/api-keys", kind: "page" },
];

const ACTIONS: PageItem[] = [
  { id: "act-check-npm", label: "Check npm package", hint: "e.g. express", href: "/?eco=npm", kind: "action" },
  { id: "act-check-pypi", label: "Check PyPI package", hint: "e.g. django", href: "/?eco=pypi", kind: "action" },
  { id: "act-vuln", label: "Check vulnerability", hint: "any package", href: "/", kind: "action" },
  { id: "act-compare", label: "Compare packages", hint: "up to 10 side-by-side", href: "/popular", kind: "action" },
  { id: "act-errors", label: "Find a fix for an error", hint: "paste stack trace", href: "/explore/errors", kind: "action" },
  { id: "act-compat", label: "Check stack compatibility", hint: "e.g. next@16 + react@19", href: "/explore/compat", kind: "action" },
];

const RECENT_KEY = "depscope_cmdk_recent";

function loadRecent(): PageItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw) as PageItem[];
    return arr.slice(0, 5);
  } catch {
    return [];
  }
}

function pushRecent(item: PageItem) {
  if (typeof window === "undefined") return;
  try {
    const existing = loadRecent().filter((x) => x.id !== item.id);
    const next = [{ ...item, kind: "recent" as const }, ...existing].slice(0, 5);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    /* ignore */
  }
}

export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [activeIdx, setActiveIdx] = useState(0);
  const [recent, setRecent] = useState<PageItem[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  // Global hotkey
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (open) {
      setRecent(loadRecent());
      setQ("");
      setDebounced("");
      setActiveIdx(0);
      setTimeout(() => inputRef.current?.focus(), 10);
    }
  }, [open]);

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => setDebounced(q), 300);
    return () => clearTimeout(t);
  }, [q]);

  const matches = useCallback((item: PageItem, needle: string) => {
    if (!needle) return true;
    const n = needle.toLowerCase();
    return (
      item.label.toLowerCase().includes(n) ||
      (item.hint || "").toLowerCase().includes(n)
    );
  }, []);

  const pages = PAGES.filter((p) => matches(p, debounced));
  const actions = ACTIONS.filter((a) => matches(a, debounced));
  const recents = debounced ? [] : recent;

  const flatList: PageItem[] = [...recents, ...pages, ...actions];

  const go = useCallback((item: PageItem) => {
    pushRecent(item);
    setOpen(false);
    window.location.href = item.href;
  }, []);

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, flatList.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const it = flatList[activeIdx];
      if (it) go(it);
    }
  };

  // Expose open trigger via window event for Nav button
  useEffect(() => {
    const openHandler = () => setOpen(true);
    window.addEventListener("depscope:open-cmdk", openHandler as EventListener);
    return () => window.removeEventListener("depscope:open-cmdk", openHandler as EventListener);
  }, []);

  if (!open) return null;

  const renderItem = (item: PageItem, flatIndex: number) => {
    const active = flatIndex === activeIdx;
    return (
      <button
        key={item.id + "-" + item.kind}
        onClick={() => go(item)}
        onMouseEnter={() => setActiveIdx(flatIndex)}
        className={`w-full flex items-center justify-between gap-3 px-3 py-2 rounded text-left transition ${
          active ? "bg-[var(--bg-hover)] text-[var(--text)]" : "text-[var(--text-dim)] hover:bg-[var(--bg-hover)]"
        }`}
      >
        <div className="flex-1 min-w-0">
          <div className="text-sm truncate">{item.label}</div>
          {item.hint && <div className="text-[11px] text-[var(--text-faded)] truncate">{item.hint}</div>}
        </div>
        <span className="text-[10px] font-mono text-[var(--text-faded)] uppercase shrink-0">{item.kind}</span>
      </button>
    );
  };

  let idx = -1;

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/70 backdrop-blur-sm flex items-start justify-center pt-[10vh] px-4"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-xl bg-[var(--bg-card)] border border-[var(--border)] rounded-lg shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 px-3 border-b border-[var(--border)]">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--text-faded)]">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setActiveIdx(0);
            }}
            onKeyDown={onKeyDown}
            placeholder="Search pages, actions..."
            className="flex-1 bg-transparent py-3 text-sm text-[var(--text)] placeholder:text-[var(--text-faded)] focus:outline-none"
          />
          <kbd className="font-mono text-[10px] px-1.5 py-0.5 border border-[var(--border)] rounded text-[var(--text-faded)]">ESC</kbd>
        </div>

        <div className="max-h-[60vh] overflow-y-auto p-2">
          {recents.length > 0 && (
            <div className="mb-2">
              <div className="px-3 pt-1 pb-1 text-[10px] font-mono uppercase tracking-wider text-[var(--text-faded)]">Recent</div>
              {recents.map((r) => { idx++; return renderItem(r, idx); })}
            </div>
          )}
          {pages.length > 0 && (
            <div className="mb-2">
              <div className="px-3 pt-1 pb-1 text-[10px] font-mono uppercase tracking-wider text-[var(--text-faded)]">Pages</div>
              {pages.map((p) => { idx++; return renderItem(p, idx); })}
            </div>
          )}
          {actions.length > 0 && (
            <div className="mb-2">
              <div className="px-3 pt-1 pb-1 text-[10px] font-mono uppercase tracking-wider text-[var(--text-faded)]">Quick actions</div>
              {actions.map((a) => { idx++; return renderItem(a, idx); })}
            </div>
          )}
          {flatList.length === 0 && (
            <div className="p-6 text-center text-sm text-[var(--text-dim)]">No results for &ldquo;{debounced}&rdquo;</div>
          )}
        </div>

        <div className="px-3 py-2 border-t border-[var(--border)] flex items-center justify-between text-[10px] font-mono text-[var(--text-faded)]">
          <div className="flex items-center gap-2">
            <kbd className="px-1.5 py-0.5 border border-[var(--border)] rounded">↑↓</kbd>
            <span>navigate</span>
            <kbd className="px-1.5 py-0.5 border border-[var(--border)] rounded">↵</kbd>
            <span>open</span>
          </div>
          <span>depscope.dev</span>
        </div>
      </div>
    </div>
  );
}
