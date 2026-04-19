"use client";
import { useEffect, useState } from "react";
import { Card, CardBody, Stat, Section, PageHeader, Footer, Badge } from "../../components/ui";

interface Stats {
  packages_indexed: number;
  vulnerabilities_tracked: number;
  trending: { ecosystem: string; package: string; searches: number }[];
  ecosystems: string[];
  ecosystem_counts?: Record<string, number>;
  pricing: string;
  mcp_tools?: number;
}

const ECOSYSTEM_LABELS: Record<string, string> = {
  npm: "npm",
  pypi: "PyPI",
  cargo: "Cargo",
  go: "Go",
  composer: "Composer",
  maven: "Maven",
  nuget: "NuGet",
  rubygems: "RubyGems",
  pub: "Pub",
  hex: "Hex",
  swift: "Swift",
  cocoapods: "CocoaPods",
  cpan: "CPAN",
  hackage: "Hackage",
  cran: "CRAN",
  conda: "Conda",
  homebrew: "Homebrew",
};

export default function StatsPage() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    fetch("/api/stats").then((r) => r.json()).then(setStats).catch(() => {});
  }, []);

  if (!stats) {
    return (
      <div className="min-h-screen flex items-center justify-center text-[var(--text-dim)]">
        Loading...
      </div>
    );
  }

  const ecosystemsList = stats.ecosystems || [];
  const ecosystemCounts = stats.ecosystem_counts || {};
  const sortedEcosystems = [...ecosystemsList].sort(
    (a, b) => (ecosystemCounts[b] || 0) - (ecosystemCounts[a] || 0)
  );

  return (
    <div className="min-h-screen">
      <main className="max-w-5xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="Capabilities"
          title="What DepScope covers"
          description="Registries, ecosystems, and intelligence surface. Updated in real time."
        />

        {/* Capability KPI strip */}
        <Section>
          <Card>
            <div className="grid grid-cols-2 md:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-[var(--border)]">
              <div className="p-5">
                <Stat
                  value={stats.packages_indexed?.toLocaleString() || "—"}
                  label="Packages indexed"
                />
              </div>
              <div className="p-5">
                <Stat
                  value={ecosystemsList.length || 17}
                  label="Ecosystems"
                  color="var(--green)"
                />
              </div>
              <div className="p-5">
                <Stat
                  value={stats.vulnerabilities_tracked?.toLocaleString() || "—"}
                  label="Vulnerabilities tracked"
                  color="var(--red)"
                />
              </div>
              <div className="p-5">
                <Stat
                  value={stats.mcp_tools ?? 12}
                  label="MCP tools"
                  color="var(--accent)"
                />
              </div>
            </div>
          </Card>
        </Section>

        {/* Coverage grid */}
        {sortedEcosystems.length > 0 && (
          <Section
            title="Coverage by ecosystem"
            description="Packages indexed per registry"
            className="mt-8"
          >
            <Card>
              <div className="grid grid-cols-2 md:grid-cols-3 divide-x divide-y divide-[var(--border)]">
                {sortedEcosystems.map((eco) => (
                  <a
                    key={eco}
                    href={`/ecosystems/${eco}`}
                    className="p-4 hover:bg-[var(--bg-hover)] transition"
                  >
                    <div className="font-mono text-sm text-[var(--accent)]">
                      {ECOSYSTEM_LABELS[eco] || eco}
                    </div>
                    <div className="text-lg font-semibold tabular-nums mt-1">
                      {(ecosystemCounts[eco] || 0).toLocaleString()}
                    </div>
                    <div className="text-[11px] text-[var(--text-dim)]">packages</div>
                  </a>
                ))}
              </div>
            </Card>
          </Section>
        )}

        {/* Platform features */}
        <Section title="Platform" description="How DepScope serves your agent" className="mt-8">
          <Card>
            <div className="divide-y divide-[var(--border)]">
              <div className="flex items-center justify-between px-5 py-3.5">
                <span className="text-sm text-[var(--text-dim)]">Update frequency</span>
                <span className="text-sm font-mono text-[var(--text)]">Real-time</span>
              </div>
              <div className="flex items-center justify-between px-5 py-3.5">
                <span className="text-sm text-[var(--text-dim)]">Cache TTL</span>
                <span className="text-sm font-mono text-[var(--text)]">1h metadata &middot; 6h vulnerabilities</span>
              </div>
              <div className="flex items-center justify-between px-5 py-3.5">
                <span className="text-sm text-[var(--text-dim)]">Cached response</span>
                <span className="text-sm font-mono text-[var(--text)]">&lt;100ms</span>
              </div>
              <div className="flex items-center justify-between px-5 py-3.5">
                <span className="text-sm text-[var(--text-dim)]">Token reduction per check</span>
                <span className="text-sm font-mono text-[var(--text)]">~92%</span>
              </div>
              <div className="flex items-center justify-between px-5 py-3.5">
                <span className="text-sm text-[var(--text-dim)]">Rate limit (anonymous)</span>
                <span className="text-sm font-mono text-[var(--text)]">200 req/min</span>
              </div>
              <div className="flex items-center justify-between px-5 py-3.5">
                <span className="text-sm text-[var(--text-dim)]">Auth required</span>
                <span className="text-sm font-mono text-[var(--green)]">No</span>
              </div>
              <div className="flex items-center justify-between px-5 py-3.5">
                <span className="text-sm text-[var(--text-dim)]">Data sources</span>
                <span className="text-sm font-mono text-[var(--text)]">OSV + 17 registries</span>
              </div>
            </div>
          </Card>
        </Section>

        {stats.trending && stats.trending.length > 0 && (
          <Section title="Trending packages" description="Most-searched across all ecosystems" className="mt-8">
            <Card>
              <div className="divide-y divide-[var(--border)]">
                {stats.trending.slice(0, 20).map((t, i) => (
                  <a
                    key={i}
                    href={`/pkg/${t.ecosystem}/${t.package}`}
                    className="flex items-center justify-between px-4 py-2.5 hover:bg-[var(--bg-hover)] transition"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="text-[var(--text-dim)] tabular-nums font-mono text-xs w-6">
                        {i + 1}
                      </span>
                      <Badge variant="accent">{t.ecosystem}</Badge>
                      <span className="font-mono text-sm text-[var(--text)] truncate">{t.package}</span>
                    </div>
                  </a>
                ))}
              </div>
            </Card>
          </Section>
        )}

        <Section className="mt-8">
          <Card>
            <CardBody className="flex items-center justify-between gap-3 flex-wrap">
              <span className="text-sm text-[var(--text-dim)]">Pricing</span>
              <Badge variant="success">{stats.pricing || "Free · no auth"}</Badge>
            </CardBody>
          </Card>
        </Section>
      </main>
      <Footer />
    </div>
  );
}
