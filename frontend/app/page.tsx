"use client";

import { useState, useEffect } from "react";
import SavingsCounter from "./savings-counter";
import {
  Card,
  CardBody,
  CardHeader,
  Stat,
  Badge,
  SeverityBadge,
  ActionBadge,
  Button,
  Select,
  Section,
  Footer,
  Table,
  Thead,
  Tbody,
  Th,
  Td,
  Tr,
} from "../components/ui";
import { CopyButton } from "../components/CopyButton";

interface HealthBreakdown {
  maintenance: number;
  popularity: number;
  security: number;
  maturity: number;
  community: number;
}

interface Vulnerability {
  vuln_id: string;
  severity: string;
  summary: string;
  fixed_version: string | null;
}

interface PackageResult {
  package: string;
  ecosystem: string;
  latest_version: string;
  description: string;
  license: string;
  repository: string;
  health: {
    score: number;
    risk: string;
    breakdown: HealthBreakdown;
    deprecated: boolean;
  };
  vulnerabilities: {
    count: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
    details: Vulnerability[];
  };
  versions: {
    latest: string;
    total_count: number;
    recent: string[];
  };
  metadata: {
    deprecated: boolean;
    deprecated_message: string | null;
    maintainers_count: number;
    last_published: string;
    first_published: string;
    dependencies_count: number;
    dependencies: string[];
  };
  recommendation: {
    action: string;
    issues: string[];
    use_version: string;
    version_hint: string | null;
    summary: string;
  };
  _response_ms: number;
  _cache: string;
}

function ScoreRing({ score }: { score: number }) {
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color =
    score >= 80 ? "var(--green)" :
    score >= 60 ? "var(--yellow)" :
    score >= 40 ? "var(--orange)" :
    "var(--red)";

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="108" height="108" className="-rotate-90">
        <circle cx="54" cy="54" r={radius} stroke="var(--border)" strokeWidth="6" fill="none" />
        <circle
          cx="54"
          cy="54"
          r={radius}
          stroke={color}
          strokeWidth="6"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="score-ring"
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-2xl font-semibold tabular-nums" style={{ color }}>
          {score}
        </span>
        <span className="text-[10px] text-[var(--text-dim)] font-mono">/100</span>
      </div>
    </div>
  );
}

const SETUP_TABS = [
  {
    id: "claude",
    label: "Claude Code",
    file: "CLAUDE.md",
    snippet: `## DEPSCOPE — Before any install: curl depscope.dev/api/check/{eco}/{pkg}`,
  },
  {
    id: "cursor",
    label: "Cursor",
    file: ".cursorrules",
    snippet: `Before any install: curl depscope.dev/api/check/{eco}/{pkg} — no auth, free`,
  },
  {
    id: "windsurf",
    label: "Windsurf",
    file: ".windsurfrules",
    snippet: `Before any install: curl depscope.dev/api/check/{eco}/{pkg}`,
  },
  {
    id: "copilot",
    label: "Copilot",
    file: ".github/copilot-instructions.md",
    snippet: `Before any install: curl depscope.dev/api/check/{eco}/{pkg} — free, no auth`,
  },
  {
    id: "chatgpt",
    label: "ChatGPT",
    file: "GPT Store",
    snippet: `Search "DepScope" in the GPT Store — or use the OpenAPI spec:
https://depscope.dev/openapi-gpt.json`,
  },
  {
    id: "curl",
    label: "Any Agent",
    file: "curl / HTTP",
    snippet: `curl https://depscope.dev/api/check/npm/express`,
  },
];

function SetupSnippets() {
  const [activeTab, setActiveTab] = useState("claude");
  const active = SETUP_TABS.find((t) => t.id === activeTab) || SETUP_TABS[0];

  return (
    <Card className="overflow-hidden">
      <div className="flex overflow-x-auto border-b border-[var(--border)]">
        {SETUP_TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 text-sm whitespace-nowrap transition border-b-2 ${
              activeTab === tab.id
                ? "text-[var(--text)] border-[var(--accent)] bg-[var(--bg-hover)]/50"
                : "text-[var(--text-dim)] border-transparent hover:text-[var(--text)] hover:bg-[var(--bg-hover)]/30"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="p-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-[11px] text-[var(--text-dim)] font-mono uppercase tracking-wide">
            {active.file}
          </span>
          <CopyButton text={active.snippet} />
        </div>
        <pre className="bg-[var(--bg-input)] border border-[var(--border)] rounded p-3 text-xs text-[var(--accent)] overflow-x-auto whitespace-pre-wrap leading-relaxed font-mono">
          {active.snippet}
        </pre>
      </div>
    </Card>
  );
}

interface StatsData {
  packages_indexed: number;
  vulnerabilities_tracked: number;
  ecosystems: string[];
  mcp_tools?: number;
}

const EXPLORE_CARDS = [
  { href: "/explore/trending", label: "Trending", hint: "Hot now" },
  { href: "/explore/errors", label: "Errors", hint: "Fix any" },
  { href: "/explore/compat", label: "Compat", hint: "Test stack" },
  { href: "/explore/bugs", label: "Bugs", hint: "Per version" },
];

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

export default function Home() {
  const [query, setQuery] = useState("");
  const [ecosystem, setEcosystem] = useState("npm");
  const [availableEcosystems, setAvailableEcosystems] = useState<string[]>([
    "npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems",
    "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew",
  ]);
  const [stats, setStats] = useState<StatsData | null>(null);

  useEffect(() => {
    fetch("/api/stats")
      .then((r) => r.json())
      .then((d) => {
        if (d.ecosystems?.length) setAvailableEcosystems(d.ecosystems);
        setStats(d);
      })
      .catch(() => {});
  }, []);

  const [result, setResult] = useState<PackageResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await fetch(`/api/check/${ecosystem}/${query.trim()}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Package not found (${res.status})`);
      }
      setResult(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to fetch");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen">
      <main className="max-w-6xl mx-auto px-4">
        {/* === HERO === */}
        <header className="pt-12 md:pt-16 pb-6 text-center" id="top">
          <div className="text-[11px] font-mono text-[var(--accent)] mb-3 tracking-[0.2em] uppercase">
            Package Intelligence for AI Agents
          </div>
          <h1 className="text-3xl md:text-5xl font-semibold mb-3 leading-[1.1] tracking-tight">
            Save tokens. Save energy.
            <br />
            <span className="text-[var(--accent)]">Ship safer code.</span>
          </h1>
          <p className="text-sm md:text-base text-[var(--text-dim)] mb-8 max-w-xl mx-auto leading-relaxed">
            One API for package health across {stats?.ecosystems?.length || 17} ecosystems.
            Cached for every AI agent. Free, no auth.
          </p>

          {/* Search */}
          <div className="max-w-2xl mx-auto mb-4">
            <div className="flex flex-col sm:flex-row items-stretch gap-2 bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-1.5">
              <Select
                value={ecosystem}
                onChange={(e) => setEcosystem(e.target.value)}
                className="sm:border-0 sm:bg-transparent text-[var(--accent)] font-medium"
              >
                {availableEcosystems.map((eco) => (
                  <option key={eco} value={eco}>{eco}</option>
                ))}
              </Select>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && search()}
                placeholder="express, fastapi, serde, @anthropic-ai/sdk..."
                className="flex-1 bg-transparent px-3 py-2 text-sm md:text-base focus:outline-none placeholder:text-[var(--text-faded)]"
              />
              <Button onClick={search} disabled={loading} variant="primary" className="px-5">
                {loading ? "..." : "Check"}
              </Button>
            </div>
            {error && (
              <p className="text-[var(--red)] text-xs mt-2 text-left font-mono">{error}</p>
            )}
          </div>

          {/* Ecosystem chips */}
          <div className="flex flex-wrap justify-center gap-1.5 text-xs">
            {availableEcosystems.map((eco) => (
              <a
                key={eco}
                href={`/ecosystems/${eco}`}
                className="px-2.5 py-1 rounded border border-[var(--border)] text-[var(--text-dim)] hover:border-[var(--accent)]/40 hover:text-[var(--accent)] transition font-mono"
              >
                {ECOSYSTEM_LABELS[eco] || eco}
              </a>
            ))}
          </div>

          {/* MCP tools banner */}
          <div className="mt-6 flex flex-wrap justify-center items-center gap-x-3 gap-y-1 text-[11px] text-[var(--text-faded)] font-mono">
            <span className="tabular-nums"><span className="text-[var(--text-dim)]">{stats?.mcp_tools ?? 12}</span> MCP tools</span>
            <span>·</span>
            <span className="tabular-nums"><span className="text-[var(--text-dim)]">{stats?.ecosystems?.length || 17}</span> ecosystems</span>
            <span>·</span>
            <span className="tabular-nums"><span className="text-[var(--text-dim)]">{stats?.packages_indexed?.toLocaleString() || "14,744"}</span> packages</span>
            <span>·</span>
            <span className="tabular-nums"><span className="text-[var(--text-dim)]">{stats?.vulnerabilities_tracked ?? 402}</span> vulnerabilities</span>
            <span>·</span>
            <span className="text-[var(--green)]">Free</span>
          </div>
        </header>

        {/* === RESULT === */}
        {result && (
          <div className="pb-16 space-y-4">
            {/* Header row */}
            <Card>
              <CardBody>
                <div className="flex items-start justify-between gap-6 flex-wrap">
                  <div className="flex-1 min-w-[200px]">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <h2 className="text-xl font-semibold tracking-tight">{result.package}</h2>
                      <Badge variant="accent">{result.ecosystem}</Badge>
                      <span className="text-sm text-[var(--text-dim)] font-mono tabular-nums">
                        v{result.latest_version}
                      </span>
                      {result._cache === "hit" && (
                        <Badge variant="success">cached</Badge>
                      )}
                    </div>
                    <p className="text-sm text-[var(--text-dim)] mb-3 max-w-2xl">
                      {result.description}
                    </p>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-[var(--text-dim)]">
                      {result.license && (
                        <span>
                          License <span className="text-[var(--text)] font-mono">{result.license}</span>
                        </span>
                      )}
                      <span className="tabular-nums">
                        <span className="text-[var(--text)] font-mono">{result.versions.total_count}</span> versions
                      </span>
                      <span className="tabular-nums">
                        <span className="text-[var(--text)] font-mono">{result.metadata.maintainers_count}</span> maintainers
                      </span>
                      <span className="tabular-nums">
                        <span className="text-[var(--text)] font-mono">{result.metadata.dependencies_count}</span> deps
                      </span>
                      <span className="tabular-nums">
                        <span className="text-[var(--text)] font-mono">{result._response_ms}</span> ms
                      </span>
                    </div>
                    {result.repository && (
                      <a
                        href={result.repository}
                        target="_blank"
                        rel="noopener"
                        className="text-xs text-[var(--accent)] hover:underline mt-2 inline-block font-mono"
                      >
                        {result.repository.replace("https://github.com/", "")}
                      </a>
                    )}
                  </div>
                  <ScoreRing score={result.health.score} />
                </div>
              </CardBody>
            </Card>

            {/* Recommendation */}
            <Card>
              <CardBody className="flex items-start gap-3">
                <ActionBadge action={result.recommendation.action} />
                <div className="flex-1">
                  <p className="text-sm text-[var(--text)]">{result.recommendation.summary}</p>
                  {result.recommendation.version_hint && (
                    <p className="text-xs text-[var(--text-dim)] mt-1">
                      {result.recommendation.version_hint}
                    </p>
                  )}
                  {result.recommendation.issues.length > 0 && (
                    <ul className="mt-2 text-xs text-[var(--text-dim)] space-y-0.5 list-disc list-inside">
                      {result.recommendation.issues.map((issue, i) => (
                        <li key={i}>{issue}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </CardBody>
            </Card>

            {/* Health Breakdown + Vulns summary: 2 col */}
            <div className="grid md:grid-cols-3 gap-4">
              <Card className="md:col-span-2">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Health breakdown</span>
                    <span className="text-[11px] text-[var(--text-dim)] font-mono uppercase tracking-wide">
                      0 – 100
                    </span>
                  </div>
                </CardHeader>
                <CardBody>
                  <div className="grid grid-cols-5 gap-4">
                    {Object.entries(result.health.breakdown).map(([key, value]) => {
                      const max =
                        key === "maintenance" || key === "security" ? 25 :
                        key === "popularity" ? 20 : 15;
                      const pct = (value / max) * 100;
                      return (
                        <div key={key}>
                          <div className="text-lg font-semibold tabular-nums">
                            {value}
                            <span className="text-[10px] text-[var(--text-dim)] font-mono">/{max}</span>
                          </div>
                          <div className="w-full bg-[var(--bg-input)] rounded h-1 my-1.5 overflow-hidden">
                            <div
                              className="h-1 rounded bg-[var(--accent)]"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <div className="text-[10px] text-[var(--text-dim)] uppercase tracking-wide">
                            {key}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardBody>
              </Card>

              <Card>
                <CardHeader>
                  <span className="text-sm font-medium">Vulnerabilities</span>
                </CardHeader>
                <CardBody>
                  <div className="text-3xl font-semibold tabular-nums mb-3">
                    {result.vulnerabilities.count}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {result.vulnerabilities.critical > 0 && (
                      <Badge variant="danger">{result.vulnerabilities.critical} critical</Badge>
                    )}
                    {result.vulnerabilities.high > 0 && (
                      <Badge variant="warning">{result.vulnerabilities.high} high</Badge>
                    )}
                    {result.vulnerabilities.medium > 0 && (
                      <Badge variant="warning">{result.vulnerabilities.medium} medium</Badge>
                    )}
                    {result.vulnerabilities.low > 0 && (
                      <Badge variant="success">{result.vulnerabilities.low} low</Badge>
                    )}
                    {result.vulnerabilities.count === 0 && (
                      <Badge variant="success">none</Badge>
                    )}
                  </div>
                </CardBody>
              </Card>
            </div>

            {/* Vulns table */}
            {result.vulnerabilities.count > 0 && (
              <Card>
                <CardHeader>
                  <span className="text-sm font-medium">
                    Advisories ({result.vulnerabilities.count})
                  </span>
                </CardHeader>
                <Table>
                  <Thead>
                    <Tr>
                      <Th>Severity</Th>
                      <Th>ID</Th>
                      <Th>Summary</Th>
                      <Th>Fixed in</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {result.vulnerabilities.details.slice(0, 20).map((v, i) => (
                      <Tr key={i}>
                        <Td className="whitespace-nowrap">
                          <SeverityBadge severity={v.severity} />
                        </Td>
                        <Td className="font-mono text-xs text-[var(--text-dim)] whitespace-nowrap">
                          {v.vuln_id}
                        </Td>
                        <Td>{v.summary}</Td>
                        <Td className="font-mono text-xs whitespace-nowrap">
                          {v.fixed_version ? (
                            <span className="text-[var(--green)]">{v.fixed_version}</span>
                          ) : (
                            <span className="text-[var(--text-dim)]">—</span>
                          )}
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
                {result.vulnerabilities.count > 20 && (
                  <div className="px-4 py-2.5 text-xs text-[var(--text-dim)] text-center border-t border-[var(--border)]">
                    ... and {result.vulnerabilities.count - 20} more
                  </div>
                )}
              </Card>
            )}

            {/* Dependencies table */}
            {result.metadata.dependencies?.length > 0 && (
              <Card>
                <CardHeader>
                  <span className="text-sm font-medium">
                    Dependencies ({result.metadata.dependencies_count})
                  </span>
                </CardHeader>
                <CardBody>
                  <div className="flex flex-wrap gap-1.5">
                    {result.metadata.dependencies.slice(0, 40).map((dep, i) => {
                      const depName = typeof dep === "string" ? dep.split(/[<>=! ]/)[0] : dep;
                      return (
                        <button
                          key={i}
                          onClick={() => {
                            setQuery(depName);
                            search();
                          }}
                          className="px-2 py-0.5 text-xs rounded font-mono text-[var(--text-dim)] bg-[var(--bg-input)] border border-[var(--border)] hover:text-[var(--accent)] hover:border-[var(--accent)]/40 transition"
                        >
                          {depName}
                        </button>
                      );
                    })}
                  </div>
                </CardBody>
              </Card>
            )}

            {/* API call footer */}
            <Card>
              <CardBody className="flex items-center justify-between gap-3 flex-wrap">
                <code className="text-xs text-[var(--text-dim)] font-mono">
                  GET /api/check/{result.ecosystem}/{result.package}
                </code>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-[var(--text-dim)] tabular-nums">
                    {result._response_ms}ms
                  </span>
                  <Badge variant={result._cache === "hit" ? "success" : "neutral"}>
                    {result._cache}
                  </Badge>
                  <CopyButton text={`curl https://depscope.dev/api/check/${result.ecosystem}/${result.package}`} />
                </div>
              </CardBody>
            </Card>
          </div>
        )}

        {/* === LANDING === */}
        {!result && (
          <div className="pb-12 space-y-12">
            {/* KPI strip */}
            <Section>
              <Card>
                <div className="grid grid-cols-2 md:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-[var(--border)]">
                  <div className="p-5">
                    <Stat
                      value={stats?.packages_indexed?.toLocaleString() || "14,744"}
                      label="Packages indexed"
                    />
                  </div>
                  <div className="p-5">
                    <Stat
                      value={stats?.ecosystems?.length || 17}
                      label="Ecosystems"
                      color="var(--green)"
                    />
                  </div>
                  <div className="p-5">
                    <Stat
                      value={stats?.vulnerabilities_tracked?.toLocaleString() || "402"}
                      label="Vulnerabilities"
                      color="var(--red)"
                    />
                  </div>
                  <div className="p-5">
                    <Stat
                      value={stats?.mcp_tools ?? 12}
                      label="MCP tools"
                      color="var(--accent)"
                    />
                  </div>
                </div>
              </Card>
            </Section>

            {/* Setup */}
            <Section
              title="Add DepScope to your AI agent"
              description="One line in your config. Your agent saves tokens, your users save energy, you ship safer code."
            >
              <SetupSnippets />
            </Section>

            {/* More than package health */}
            <Section
              title="More than package health"
              description="Four dimensions of package intelligence. Explore them all."
            >
              <Card>
                <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-y md:divide-y-0 divide-[var(--border)]">
                  {EXPLORE_CARDS.map((c) => (
                    <a
                      key={c.href}
                      href={c.href}
                      className="p-5 hover:bg-[var(--bg-hover)] transition group"
                    >
                      <div className="text-sm font-semibold text-[var(--text)] group-hover:text-[var(--accent)] transition">
                        {c.label}
                      </div>
                      <div className="text-xs text-[var(--text-dim)] mt-0.5">{c.hint}</div>
                    </a>
                  ))}
                </div>
              </Card>
            </Section>

            {/* Problem / Solution — compact, 3 col */}
            <Section title="Why it matters">
              <div className="grid md:grid-cols-3 gap-3">
                <Card className="border-l-2 border-l-[var(--red)]">
                  <CardBody>
                    <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--red)] mb-2">
                      Problem · security
                    </div>
                    <h3 className="font-medium text-sm mb-1.5">Your AI agent guesses</h3>
                    <p className="text-xs text-[var(--text-dim)] leading-relaxed">
                      Stale training data suggests wrong versions, deprecated libraries, known vulnerabilities.
                    </p>
                  </CardBody>
                </Card>

                <Card className="border-l-2 border-l-[var(--orange)]">
                  <CardBody>
                    <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--orange)] mb-2">
                      Problem · waste
                    </div>
                    <h3 className="font-medium text-sm mb-1.5">Everyone fetches the same data</h3>
                    <p className="text-xs text-[var(--text-dim)] leading-relaxed">
                      Agents independently hit npm, PyPI, OSV. Same queries, millions of times. Wasted compute, tokens, CO2.
                    </p>
                  </CardBody>
                </Card>

                <Card className="border-l-2 border-l-[var(--accent)]">
                  <CardBody>
                    <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--accent)] mb-2">
                      Solution
                    </div>
                    <h3 className="font-medium text-sm mb-1.5">One API call. Done.</h3>
                    <p className="text-xs text-[var(--text-dim)] leading-relaxed">
                      Health score, vulnerabilities, recommendation. {stats?.ecosystems?.length || 17} ecosystems. Cached. Free. No auth.
                    </p>
                  </CardBody>
                </Card>
              </div>
            </Section>

            {/* Three savings */}
            <Section title="What DepScope saves">
              <div className="grid md:grid-cols-3 gap-3">
                <Card>
                  <CardBody>
                    <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--blue)] mb-2">
                      Tokens
                    </div>
                    <div className="text-2xl font-semibold tabular-nums text-[var(--text)] mb-2">
                      ~92%
                    </div>
                    <p className="text-xs text-[var(--text-dim)] leading-relaxed">
                      ~3K tokens per npm/PyPI JSON parse collapses to &lt;100 tokens of structured answer.
                    </p>
                  </CardBody>
                </Card>
                <Card>
                  <CardBody>
                    <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--orange)] mb-2">
                      Energy
                    </div>
                    <div className="text-2xl font-semibold tabular-nums text-[var(--text)] mb-2">
                      1 fetch · N agents
                    </div>
                    <p className="text-xs text-[var(--text-dim)] leading-relaxed">
                      Shared cache serves thousands. Less compute, bandwidth, CO2 on public registries.
                    </p>
                  </CardBody>
                </Card>
                <Card>
                  <CardBody>
                    <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--red)] mb-2">
                      Security
                    </div>
                    <div className="text-2xl font-semibold tabular-nums text-[var(--text)] mb-2">
                      {stats?.vulnerabilities_tracked?.toLocaleString() || "400+"}
                    </div>
                    <p className="text-xs text-[var(--text-dim)] leading-relaxed">
                      Vulnerabilities tracked, filtered to latest version. Plus transitive deps, license, deprecation.
                    </p>
                  </CardBody>
                </Card>
              </div>
            </Section>

            {/* With vs Without — compact table */}
            <Section title="With vs. without DepScope">
              <Card>
                <Table>
                  <Thead>
                    <Tr>
                      <Th className="w-1/3">Moment</Th>
                      <Th>Without DepScope</Th>
                      <Th>With DepScope</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    <Tr>
                      <Td className="text-[var(--text-dim)]">Package suggestion</Td>
                      <Td>Stale training data</Td>
                      <Td>Live health check before suggesting</Td>
                    </Tr>
                    <Tr>
                      <Td className="text-[var(--text-dim)]">Vulnerability check</Td>
                      <Td>None</Td>
                      <Td>OSV + registry advisories, severity + fix</Td>
                    </Tr>
                    <Tr>
                      <Td className="text-[var(--text-dim)]">Deprecation</Td>
                      <Td>Invisible</Td>
                      <Td>Flagged with reason</Td>
                    </Tr>
                    <Tr>
                      <Td className="text-[var(--text-dim)]">Discovery of issues</Td>
                      <Td className="text-[var(--red)]">In production</Td>
                      <Td className="text-[var(--green)]">Before a single line of code</Td>
                    </Tr>
                  </Tbody>
                </Table>
              </Card>
            </Section>

            {/* Example JSON */}
            <Section title="Sample response" description="What your agent sees back.">
              <Card>
                <CardBody>
                  <div className="flex items-center justify-between mb-2">
                    <code className="text-xs font-mono text-[var(--text-dim)]">
                      GET /api/check/npm/express
                    </code>
                    <CopyButton text="curl https://depscope.dev/api/check/npm/express" />
                  </div>
                  <pre className="bg-[var(--bg-input)] border border-[var(--border)] rounded p-3 text-xs font-mono overflow-x-auto leading-relaxed text-[var(--text-dim)]">
{`{
  `}<span className="text-[var(--purple)]">&quot;health&quot;</span>{`: {
    `}<span className="text-[var(--purple)]">&quot;score&quot;</span>{`: `}<span className="text-[var(--accent)]">80</span>{`,
    `}<span className="text-[var(--purple)]">&quot;risk&quot;</span>{`: `}<span className="text-[var(--green)]">&quot;low&quot;</span>{`
  },
  `}<span className="text-[var(--purple)]">&quot;recommendation&quot;</span>{`: {
    `}<span className="text-[var(--purple)]">&quot;action&quot;</span>{`: `}<span className="text-[var(--green)]">&quot;safe_to_use&quot;</span>{`
  },
  `}<span className="text-[var(--purple)]">&quot;vulnerabilities&quot;</span>{`: {
    `}<span className="text-[var(--purple)]">&quot;count&quot;</span>{`: `}<span className="text-[var(--green)]">0</span>{`
  }
}`}
                  </pre>
                </CardBody>
              </Card>
            </Section>

            {/* Ecosystems grid */}
            <Section title="Ecosystems">
              <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
                {availableEcosystems.map((eco) => (
                  <a
                    key={eco}
                    href={`/ecosystems/${eco}`}
                    className="p-3 rounded border border-[var(--border)] bg-[var(--bg-card)] hover:border-[var(--accent)]/40 hover:bg-[var(--bg-hover)] transition text-center"
                  >
                    <div className="font-mono text-sm text-[var(--text)]">
                      {ECOSYSTEM_LABELS[eco] || eco}
                    </div>
                    <div className="text-[10px] text-[var(--text-dim)] mt-0.5">Browse</div>
                  </a>
                ))}
              </div>
            </Section>

            {/* Efficiency by design */}
            <Section title="Built for efficiency">
              <SavingsCounter />
            </Section>

            {/* Footer CTA */}
            <Section>
              <Card>
                <CardBody className="flex flex-col md:flex-row items-center justify-between gap-4 py-8">
                  <div>
                    <h2 className="text-lg font-semibold tracking-tight">Ready to ship safer code?</h2>
                    <p className="text-sm text-[var(--text-dim)] mt-1">
                      No signup. No API key. Start with a single curl.
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <a
                      href="/integrate"
                      className="inline-flex items-center gap-1 text-sm font-medium px-4 py-2 rounded bg-[var(--accent)] text-black hover:bg-[var(--accent-dim)] transition"
                    >
                      Integration Guide
                    </a>
                    <a
                      href="/api-docs"
                      className="inline-flex items-center gap-1 text-sm font-medium px-4 py-2 rounded border border-[var(--border)] text-[var(--text)] hover:bg-[var(--bg-hover)] transition"
                    >
                      API Docs
                    </a>
                  </div>
                </CardBody>
              </Card>
            </Section>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
