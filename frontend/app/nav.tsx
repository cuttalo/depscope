"use client";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

interface WithEaster extends Window {
  _dc?: number;
  _dt?: ReturnType<typeof setTimeout>;
}

const EXPLORE_ITEMS = [
  { href: "/explore/trending", label: "Trending", hint: "what agents search now" },
  { href: "/explore/errors", label: "Errors", hint: "error → fix database" },
  { href: "/explore/compat", label: "Compat", hint: "stack compatibility" },
  { href: "/explore/bugs", label: "Bugs", hint: "known bugs per version" },
  { href: "/popular", label: "Popular", hint: "most-searched packages" },
];

export default function Nav() {
  const path = usePathname();
  const isZh = path.startsWith("/zh");
  const isHidden = path === "/admin" || path === "/agent" || path === "/mission-control";

  const [exploreOpen, setExploreOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const exploreRef = useRef<HTMLDivElement>(null);

  // Close explore dropdown on outside click
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (exploreRef.current && !exploreRef.current.contains(e.target as Node)) {
        setExploreOpen(false);
      }
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);

  // Close mobile nav on path change
  useEffect(() => {
    setMobileOpen(false);
    setExploreOpen(false);
  }, [path]);

  if (isHidden) return null;

  const navLinks = [
    { href: isZh ? "/zh" : "/", label: isZh ? "首页" : "Packages", match: (p: string) => p === "/" || p === "/zh" },
    {
      href: "/explore",
      label: isZh ? "探索" : "Explore",
      match: (p: string) => p === "/explore" || p.startsWith("/explore/") || p === "/popular",
      dropdown: true,
    },
    { href: isZh ? "/zh/integrate" : "/integrate", label: "Integrate", match: (p: string) => p.includes("integrate") },
    { href: isZh ? "/zh/api-docs" : "/api-docs", label: "API Docs", match: (p: string) => p.includes("api-docs") },
    { href: "/stats", label: "Coverage", match: (p: string) => p === "/stats" },
  ];

  const handleLogoClick = () => {
    const w = window as unknown as WithEaster;
    w._dc = (w._dc || 0) + 1;
    if (w._dc >= 5) {
      window.location.href = "/admin";
      w._dc = 0;
    }
    if (w._dt) clearTimeout(w._dt);
    w._dt = setTimeout(() => {
      w._dc = 0;
    }, 3000);
  };

  const openCmdK = () => {
    window.dispatchEvent(new Event("depscope:open-cmdk"));
  };

  return (
    <>
      <nav className="sticky top-0 z-40 h-12 flex items-center px-4 md:px-6 border-b border-[var(--border)] bg-[var(--bg)]/85 backdrop-blur-md">
        <Link
          href="/"
          onClick={(e) => {
            e.preventDefault();
            handleLogoClick();
            window.location.href = "/";
          }}
          className="font-mono text-sm font-semibold text-[var(--text)] tracking-tight select-none"
        >
          <span className="text-[var(--accent)]">dep</span>scope
        </Link>

        <div className="hidden md:flex items-center gap-1 ml-8">
          {navLinks.map((l) => {
            const active = l.match(path);
            if (l.dropdown) {
              return (
                <div key={l.href} ref={exploreRef} className="relative">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setExploreOpen((o) => !o);
                    }}
                    className={`text-sm px-2.5 py-1 rounded transition inline-flex items-center gap-1 ${
                      active
                        ? "text-[var(--text)] bg-[var(--bg-hover)]"
                        : "text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)]"
                    }`}
                  >
                    {l.label}
                    <svg width="10" height="10" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M4 6l4 4 4-4" />
                    </svg>
                  </button>
                  {exploreOpen && (
                    <div className="absolute left-0 top-full mt-1 w-56 bg-[var(--bg-card)] border border-[var(--border)] rounded-lg shadow-xl overflow-hidden z-50">
                      {EXPLORE_ITEMS.map((it) => (
                        <a
                          key={it.href}
                          href={it.href}
                          className="block px-3 py-2 hover:bg-[var(--bg-hover)] transition"
                        >
                          <div className="text-sm text-[var(--text)]">{it.label}</div>
                          <div className="text-[11px] text-[var(--text-faded)]">{it.hint}</div>
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              );
            }
            return (
              <a
                key={l.href}
                href={l.href}
                className={`text-sm px-2.5 py-1 rounded transition ${
                  active
                    ? "text-[var(--text)] bg-[var(--bg-hover)]"
                    : "text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)]"
                }`}
              >
                {l.label}
              </a>
            );
          })}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={openCmdK}
            className="hidden sm:inline-flex items-center gap-2 text-xs text-[var(--text-faded)] px-2.5 py-1 border border-[var(--border)] rounded bg-[var(--bg-input)] hover:border-[var(--border-strong)] hover:text-[var(--text-dim)] transition"
            aria-label="Open command palette"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.3-4.3" />
            </svg>
            <span>Search</span>
            <kbd className="font-mono text-[10px] px-1 py-0.5 border border-[var(--border)] rounded text-[var(--text-faded)]">⌘K</kbd>
          </button>

          <a
            href="/login"
            className="hidden sm:inline-flex text-xs font-medium px-3 py-1.5 rounded text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition"
          >
            Sign in
          </a>
          <a
            href="/account/api-keys"
            className="hidden sm:inline-flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded bg-[var(--accent)] text-black hover:bg-[var(--accent-dim)] transition"
          >
            Get API access
          </a>

          <button
            onClick={() => setMobileOpen(true)}
            className="md:hidden p-1.5 rounded text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition"
            aria-label="Open menu"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="4" y1="6" x2="20" y2="6" />
              <line x1="4" y1="12" x2="20" y2="12" />
              <line x1="4" y1="18" x2="20" y2="18" />
            </svg>
          </button>
        </div>
      </nav>

      {mobileOpen && (
        <div className="md:hidden fixed inset-0 bg-[var(--bg)]/95 z-50 overflow-y-auto" onClick={() => setMobileOpen(false)}>
          <div className="p-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <span className="font-mono text-sm font-semibold">
                <span className="text-[var(--accent)]">dep</span>scope
              </span>
              <button
                onClick={() => setMobileOpen(false)}
                className="p-1.5 rounded text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)]"
                aria-label="Close menu"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <button
              onClick={() => { setMobileOpen(false); openCmdK(); }}
              className="w-full mb-4 flex items-center gap-2 text-sm text-[var(--text-dim)] px-3 py-2 border border-[var(--border)] rounded bg-[var(--bg-input)]"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.3-4.3" />
              </svg>
              Search DepScope...
            </button>

            <nav className="space-y-1">
              <a href="/" className="block px-3 py-2.5 rounded hover:bg-[var(--bg-hover)]">Packages</a>
              <div className="px-3 pt-3 pb-1 text-[10px] font-mono uppercase tracking-wider text-[var(--text-faded)]">Explore</div>
              {EXPLORE_ITEMS.map((it) => (
                <a key={it.href} href={it.href} className="block px-3 py-2.5 rounded hover:bg-[var(--bg-hover)]">
                  <div className="text-sm">{it.label}</div>
                  <div className="text-[11px] text-[var(--text-faded)]">{it.hint}</div>
                </a>
              ))}
              <div className="px-3 pt-3 pb-1 text-[10px] font-mono uppercase tracking-wider text-[var(--text-faded)]">Build</div>
              <a href="/integrate" className="block px-3 py-2.5 rounded hover:bg-[var(--bg-hover)]">Integrate</a>
              <a href="/api-docs" className="block px-3 py-2.5 rounded hover:bg-[var(--bg-hover)]">API Docs</a>
              <a href="/stats" className="block px-3 py-2.5 rounded hover:bg-[var(--bg-hover)]">Coverage</a>
              <div className="px-3 pt-3 pb-1 text-[10px] font-mono uppercase tracking-wider text-[var(--text-faded)]">Account</div>
              <a href="/login" className="block px-3 py-2.5 rounded hover:bg-[var(--bg-hover)]">Sign in</a>
              <a href="/dashboard" className="block px-3 py-2.5 rounded hover:bg-[var(--bg-hover)]">Dashboard</a>

              <div className="pt-4">
                <a href="/integrate" className="block w-full text-center px-3 py-2.5 rounded bg-[var(--accent)] text-black font-medium text-sm">
                  Get API access
                </a>
              </div>
            </nav>
          </div>
        </div>
      )}
    </>
  );
}
