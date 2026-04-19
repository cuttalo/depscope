import type { Metadata } from "next";
import Link from "next/link";
import {
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Badge,
  PageHeader,
  Section,
  Footer,
} from "../../components/ui";

interface TrendingItem {
  ecosystem: string;
  package: string;
  searches: number;
}

interface StatsData {
  packages_indexed: number;
  trending: TrendingItem[];
}

interface HealthData {
  package: string;
  ecosystem: string;
  latest_version: string;
  description: string;
  health: { score: number; risk: string };
  vulnerabilities: { count: number };
}

export const metadata: Metadata = {
  title: "Popular Packages — Most Searched | DepScope",
  description: "Most searched packages on DepScope. Health scores, vulnerability data, and recommendations for trending packages across 17 ecosystems.",
  openGraph: {
    title: "Popular Packages — Most Searched | DepScope",
    description: "Trending packages with health scores and vulnerability data. Free package intelligence by DepScope.",
    url: "https://depscope.dev/popular",
    siteName: "DepScope",
    type: "website",
  },
  alternates: { canonical: "https://depscope.dev/popular" },
  robots: { index: true, follow: true },
};

async function fetchStats(): Promise<StatsData | null> {
  try {
    const res = await fetch("http://127.0.0.1:8000/api/stats", { next: { revalidate: 1800 } });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

async function fetchHealth(ecosystem: string, pkg: string): Promise<HealthData | null> {
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/check/${ecosystem}/${pkg}`, { next: { revalidate: 3600 } });
    if (!res.ok) return null;
    const data = await res.json();
    return {
      package: data.package,
      ecosystem: data.ecosystem,
      latest_version: data.latest_version,
      description: data.description || "",
      health: {
        score: data.health?.score ?? 0,
        risk: data.health?.risk ?? "unknown",
      },
      vulnerabilities: { count: data.vulnerabilities?.count ?? 0 },
    };
  } catch {
    return null;
  }
}

const POPULAR: { ecosystem: string; name: string }[] = [
  { ecosystem: "npm", name: "express" },
  { ecosystem: "npm", name: "react" },
  { ecosystem: "npm", name: "next" },
  { ecosystem: "npm", name: "typescript" },
  { ecosystem: "npm", name: "fastify" },
  { ecosystem: "npm", name: "hono" },
  { ecosystem: "npm", name: "zod" },
  { ecosystem: "npm", name: "prisma" },
  { ecosystem: "npm", name: "axios" },
  { ecosystem: "npm", name: "lodash" },
  { ecosystem: "pypi", name: "django" },
  { ecosystem: "pypi", name: "fastapi" },
  { ecosystem: "pypi", name: "flask" },
  { ecosystem: "pypi", name: "requests" },
  { ecosystem: "pypi", name: "numpy" },
  { ecosystem: "pypi", name: "pandas" },
  { ecosystem: "cargo", name: "serde" },
  { ecosystem: "cargo", name: "tokio" },
  { ecosystem: "cargo", name: "axum" },
  { ecosystem: "cargo", name: "reqwest" },
  { ecosystem: "go", name: "github.com/gin-gonic/gin" },
  { ecosystem: "composer", name: "laravel/framework" },
  { ecosystem: "maven", name: "org.springframework:spring-core" },
  { ecosystem: "nuget", name: "Newtonsoft.Json" },
  { ecosystem: "rubygems", name: "rails" },
  { ecosystem: "pub", name: "flutter" },
  { ecosystem: "hex", name: "phoenix" },
  { ecosystem: "swift", name: "apple/swift-nio" },
  { ecosystem: "cocoapods", name: "Alamofire" },
  { ecosystem: "cpan", name: "Moose" },
  { ecosystem: "hackage", name: "aeson" },
  { ecosystem: "cran", name: "ggplot2" },
  { ecosystem: "conda", name: "numpy" },
  { ecosystem: "homebrew", name: "git" },
];

const ECO_LABELS: Record<string, string> = {
  npm: "npm", pypi: "PyPI", cargo: "Cargo", go: "Go", composer: "Composer",
  maven: "Maven", nuget: "NuGet", rubygems: "RubyGems", pub: "Pub", hex: "Hex",
  swift: "Swift", cocoapods: "CocoaPods", cpan: "CPAN", hackage: "Hackage",
  cran: "CRAN", conda: "Conda", homebrew: "Homebrew",
};

function ScorePill({ score }: { score: number }) {
  const variant =
    score >= 80 ? "success" :
    score >= 60 ? "warning" :
    score >= 40 ? "warning" : "danger";
  return <Badge variant={variant}><span className="tabular-nums font-mono">{score}</span></Badge>;
}

export default async function PopularPage() {
  const stats = await fetchStats();

  const healthResults = await Promise.allSettled(
    POPULAR.map((p) => fetchHealth(p.ecosystem, p.name))
  );
  const healthMap = new Map<string, HealthData>();
  healthResults.forEach((result, i) => {
    if (result.status === "fulfilled" && result.value) {
      const p = POPULAR[i];
      healthMap.set(`${p.ecosystem}/${p.name}`, result.value);
    }
  });

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: "Popular Packages — DepScope",
    description: "Most popular and trending packages checked by DepScope",
    numberOfItems: POPULAR.length,
    itemListElement: POPULAR.map((p, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: p.name,
      url: `https://depscope.dev/pkg/${p.ecosystem}/${p.name}`,
    })),
  };

  return (
    <div className="min-h-screen">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="Popular"
          title="Popular packages"
          description={
            stats?.packages_indexed
              ? `${stats.packages_indexed.toLocaleString()} packages indexed across 17 ecosystems, with real-time health scores.`
              : "14,744+ packages indexed across 17 ecosystems, with real-time health scores."
          }
        />

        {stats && stats.trending && stats.trending.length > 0 && (
          <Section title="Trending now" description="Most-searched in the last period" className="mb-8">
            <Card>
              <CardBody>
                <div className="flex flex-wrap gap-2">
                  {stats.trending.filter((t) => !t.package.startsWith("scan:")).slice(0, 30).map((t, i) => (
                    <Link
                      key={i}
                      href={
                        t.package.includes(",")
                          ? `/compare/${t.ecosystem}/${t.package.split(",").join("-vs-")}`
                          : `/pkg/${t.ecosystem}/${t.package}`
                      }
                      className="inline-flex items-center gap-2 px-3 py-1 text-xs rounded-full border border-[var(--border)] bg-[var(--bg-input)] text-[var(--text-dim)] hover:border-[var(--accent)]/40 hover:text-[var(--accent)] transition"
                    >
                      <span className="text-[var(--accent)] font-mono">{t.ecosystem}</span>
                      <span className="font-mono">{t.package}</span>
                    </Link>
                  ))}
                </div>
              </CardBody>
            </Card>
          </Section>
        )}

        {Object.keys(ECO_LABELS).map((eco) => {
          const pkgs = POPULAR.filter((p) => p.ecosystem === eco);
          if (pkgs.length === 0) return null;
          return (
            <Section
              key={eco}
              title={ECO_LABELS[eco]}
              actions={
                <Link href={`/ecosystems/${eco}`} className="text-xs text-[var(--accent)] hover:underline font-mono">
                  View all →
                </Link>
              }
              className="mb-8"
            >
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {pkgs.map((p) => {
                  const h = healthMap.get(`${p.ecosystem}/${p.name}`);
                  return (
                    <Link key={p.name} href={`/pkg/${eco}/${p.name}`} className="group">
                      <Card className="h-full hover:border-[var(--accent)]/40 transition">
                        <CardBody>
                          <div className="flex items-center justify-between mb-2 gap-2">
                            <h3 className="font-mono text-sm text-[var(--text)] truncate group-hover:text-[var(--accent)] transition">
                              {p.name}
                            </h3>
                            {h && <ScorePill score={h.health.score} />}
                          </div>
                          {h ? (
                            <>
                              <p className="text-xs text-[var(--text-dim)] line-clamp-2 mb-2">{h.description}</p>
                              <div className="flex items-center gap-3 text-xs text-[var(--text-dim)]">
                                <span className="font-mono tabular-nums">v{h.latest_version}</span>
                                {h.vulnerabilities.count === 0 ? (
                                  <Badge variant="success">0 vulns</Badge>
                                ) : (
                                  <Badge variant="danger">{h.vulnerabilities.count} vulns</Badge>
                                )}
                              </div>
                            </>
                          ) : (
                            <p className="text-xs text-[var(--text-dim)]">Click to check health</p>
                          )}
                        </CardBody>
                      </Card>
                    </Link>
                  );
                })}
              </div>
            </Section>
          );
        })}

        <Section title="Popular comparisons" className="mt-10">
          <div className="grid sm:grid-cols-2 gap-3">
            {[
              { eco: "npm", pkgs: "express-vs-fastify-vs-hono", label: "express vs fastify vs hono" },
              { eco: "pypi", pkgs: "django-vs-flask-vs-fastapi", label: "django vs flask vs fastapi" },
              { eco: "cargo", pkgs: "actix-web-vs-axum-vs-rocket", label: "actix-web vs axum vs rocket" },
              { eco: "npm", pkgs: "react-vs-vue-vs-svelte", label: "react vs vue vs svelte" },
              { eco: "npm", pkgs: "prisma-vs-drizzle-orm-vs-typeorm", label: "prisma vs drizzle-orm vs typeorm" },
              { eco: "pypi", pkgs: "numpy-vs-pandas-vs-polars", label: "numpy vs pandas vs polars" },
            ].map((c) => (
              <Link key={c.pkgs} href={`/compare/${c.eco}/${c.pkgs}`} className="group">
                <Card className="hover:border-[var(--accent)]/40 transition">
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <Badge variant="accent">{c.eco}</Badge>
                      <CardTitle className="group-hover:text-[var(--accent)] transition">{c.label}</CardTitle>
                    </div>
                  </CardHeader>
                </Card>
              </Link>
            ))}
          </div>
        </Section>
      </main>
      <Footer />
    </div>
  );
}
