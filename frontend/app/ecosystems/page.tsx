import type { Metadata } from "next";
import Link from "next/link";

interface EcoRow {
  ecosystem: string;
  packages: number;
}
interface StatsResponse {
  packages_indexed?: number;
  ecosystem_counts?: Record<string, number>;
  ecosystems?: string[];
}

export const metadata: Metadata = {
  title: "Ecosystems — DepScope",
  description:
    "Browse package intelligence across 17 registries: npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems, Composer, Pub, Hex, Swift, CocoaPods, CPAN, Hackage, CRAN, Conda, Homebrew. Free, zero-auth. Agent-ready.",
  alternates: { canonical: "https://depscope.dev/ecosystems" },
  openGraph: {
    title: "Ecosystems — DepScope",
    description: "17 package registries, free package intelligence for AI agents.",
    url: "https://depscope.dev/ecosystems",
  },
};

const LABELS: Record<string, { name: string; language: string; href: string; color: string }> = {
  npm:       { name: "npm",        language: "JavaScript / TypeScript", href: "/ecosystems/npm",        color: "#cb3837" },
  pypi:      { name: "PyPI",       language: "Python",                  href: "/ecosystems/pypi",       color: "#3776ab" },
  cargo:     { name: "Cargo",      language: "Rust",                    href: "/ecosystems/cargo",      color: "#dea584" },
  go:        { name: "Go modules", language: "Go",                      href: "/ecosystems/go",         color: "#00add8" },
  composer:  { name: "Composer",   language: "PHP",                     href: "/ecosystems/composer",   color: "#4f5b93" },
  maven:     { name: "Maven",      language: "Java / JVM",              href: "/ecosystems/maven",      color: "#cb2d3e" },
  nuget:     { name: "NuGet",      language: "C# / .NET",               href: "/ecosystems/nuget",      color: "#004880" },
  rubygems:  { name: "RubyGems",   language: "Ruby",                    href: "/ecosystems/rubygems",   color: "#cc342d" },
  pub:       { name: "pub.dev",    language: "Dart / Flutter",          href: "/ecosystems/pub",        color: "#00b4ab" },
  hex:       { name: "Hex.pm",     language: "Elixir / Erlang",         href: "/ecosystems/hex",        color: "#9e5e9e" },
  swift:     { name: "Swift PM",   language: "Swift",                   href: "/ecosystems/swift",      color: "#fa7343" },
  cocoapods: { name: "CocoaPods",  language: "Objective-C / Swift",     href: "/ecosystems/cocoapods",  color: "#ee3322" },
  cpan:      { name: "CPAN",       language: "Perl",                    href: "/ecosystems/cpan",       color: "#39457e" },
  hackage:   { name: "Hackage",    language: "Haskell",                 href: "/ecosystems/hackage",    color: "#5e5086" },
  cran:      { name: "CRAN",       language: "R",                       href: "/ecosystems/cran",       color: "#276dc3" },
  conda:     { name: "Conda",      language: "Python (scientific)",     href: "/ecosystems/conda",      color: "#43b02a" },
  homebrew:  { name: "Homebrew",   language: "macOS / Linux formulae",  href: "/ecosystems/homebrew",   color: "#f5a623" },
  jsr:       { name: "JSR",        language: "TypeScript / Deno / Bun / Node", href: "/ecosystems/jsr",        color: "#f7df1e" },
  julia:     { name: "Julia",      language: "Scientific / AI / ML",                 href: "/ecosystems/julia",      color: "#9558b2" },
};

async function fetchStats(): Promise<StatsResponse> {
  try {
    const r = await fetch("http://127.0.0.1:8000/api/stats", { next: { revalidate: 300 } });
    if (!r.ok) return {};
    return (await r.json()) as StatsResponse;
  } catch {
    return {};
  }
}

export default async function EcosystemsIndex() {
  const s = await fetchStats();
  const counts = s.ecosystem_counts || {};
  const rows: EcoRow[] = (s.ecosystems || Object.keys(LABELS))
    .filter((e) => LABELS[e])
    .map((e) => ({ ecosystem: e, packages: counts[e] || 0 }))
    .sort((a, b) => b.packages - a.packages);

  const total = rows.reduce((a, r) => a + r.packages, 0) || s.packages_indexed || 0;

  const itemListLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    "name": "DepScope ecosystems",
    "numberOfItems": rows.length,
    "itemListElement": rows.map((r, i) => ({
      "@type": "ListItem",
      "position": i + 1,
      "name": LABELS[r.ecosystem].name,
      "url": `https://depscope.dev${LABELS[r.ecosystem].href}`,
    })),
  };

  return (
    <div className="min-h-screen">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(itemListLd) }}
        />
      </head>
      <main className="max-w-6xl mx-auto px-4 py-10">
        <header className="mb-8">
          <h1 className="text-3xl font-semibold tracking-tight">Ecosystems</h1>
          <p className="mt-2 text-sm text-[var(--text-dim)] max-w-2xl">
            DepScope indexes {rows.length} package registries. All free, zero-auth.
            Health score, vulnerabilities, deprecation signals, and curated alternatives
            for each.
          </p>
        </header>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {rows.map((r) => {
            const L = LABELS[r.ecosystem];
            return (
              <Link
                key={r.ecosystem}
                href={L.href}
                className="block rounded-lg p-4 hover:bg-[var(--bg-hover)] transition"
                style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span
                        aria-hidden
                        className="inline-block w-2.5 h-2.5 rounded-full"
                        style={{ background: L.color }}
                      />
                      <span className="font-semibold">{L.name}</span>
                    </div>
                    <div className="text-xs text-[var(--text-faded)] mt-1">{L.language}</div>
                  </div>
                  <div className="text-right text-[var(--text-faded)]">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                      <polyline points="9 18 15 12 9 6"/>
                    </svg>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>

        <section className="mt-12 text-sm text-[var(--text-dim)] space-y-2">
          <p>
            Need one URL for every package? Try{" "}
            <Link href="/api-docs" className="underline hover:text-[var(--accent)]">
              /api-docs
            </Link>{" "}
            or GET{" "}
            <code className="font-mono text-xs">/api/check/&lt;ecosystem&gt;/&lt;package&gt;</code>.
          </p>
          <p>
            Machine-readable catalogue at{" "}
            <Link href="/sitemap.xml" className="underline hover:text-[var(--accent)]">
              /sitemap.xml
            </Link>
            .
          </p>
        </section>
      </main>
    </div>
  );
}
