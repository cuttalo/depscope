"use client";

import { useEffect, useState } from "react";
import {
  BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";
import {
  Card, CardHeader, CardBody, CardTitle,
  Stat, Badge, Button,
  Table, Thead, Tbody, Th, Td, Tr,
  Input, PageHeader, Section,
} from "@/components/ui";

interface Totals {
  calls_7d?: number;
  sessions_7d?: number;
  ips_7d?: number;
  avg_ms_7d?: number;
  cache_hit_rate_7d?: number;
}
interface TopSearch { ecosystem: string; package_name: string; calls: number }
interface AgentRow { source: string; calls: number; unique_ips: number }
interface CountryRow { country: string; calls: number; unique_ips: number }
interface IntentRow { inferred_intent: string; count: number }
interface StackRow { stack: string; sessions: number }
interface ComboRow {
  ecosystem: string; package_a: string; package_b: string; cooccurrence_count: number;
}
interface TrendRow {
  ecosystem: string; package_name: string; call_count: number;
  rank: number; rank_change: number | null; week_growth_pct: number | null;
}
interface ErrorRow { error_query: string; searches: number }
interface IntelligenceData {
  totals_7d: Totals;
  top_searches_24h: TopSearch[];
  agents_7d: AgentRow[];
  countries_7d: CountryRow[];
  intents_7d: IntentRow[];
  stacks_7d: StackRow[];
  top_cooccurrence: ComboRow[];
  trending_packages: TrendRow[];
  top_errors: ErrorRow[];
}

const FLAGS: Record<string, string> = {
  US: "US", IT: "IT", CN: "CN", FI: "FI", IE: "IE", SG: "SG", GB: "GB",
  DE: "DE", FR: "FR", JP: "JP", IN: "IN", BR: "BR", CA: "CA", AU: "AU",
  NL: "NL", NZ: "NZ", KR: "KR", SE: "SE", ES: "ES", RU: "RU", MX: "MX",
  PL: "PL", TW: "TW", IL: "IL", AR: "AR", TH: "TH",
};

const PIE_COLORS = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
  "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#6366f1",
];

const TABS: { id: string; label: string }[] = [
  { id: "searches", label: "Top Searches 24h" },
  { id: "agents",   label: "AI Agents" },
  { id: "countries", label: "Countries" },
  { id: "intents", label: "Intents" },
  { id: "combos", label: "Co-occurrence" },
  { id: "trending", label: "Trending" },
  { id: "errors", label: "Errors" },
];

function fmtPct(n: number | null | undefined) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(1)}%`;
}

function growthVariant(n: number | null | undefined): "success" | "danger" | "neutral" {
  if (n === null || n === undefined) return "neutral";
  if (n > 5) return "success";
  if (n < -5) return "danger";
  return "neutral";
}

function rankChangeLabel(rc: number | null) {
  if (rc === null || rc === undefined) return "new";
  if (rc > 0) return `up ${rc}`;
  if (rc < 0) return `down ${Math.abs(rc)}`;
  return "flat";
}

export default function IntelligencePage() {
  const [apiKey, setApiKey] = useState("");
  const [authed, setAuthed] = useState(false);
  const [data, setData] = useState<IntelligenceData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState("searches");

  const loadData = async (key: string) => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/admin/intelligence", {
        headers: { "X-API-Key": key },
      });
      if (!res.ok) throw new Error("Access denied. Check your API key.");
      const d: IntelligenceData = await res.json();
      setData(d);
      setAuthed(true);
      localStorage.setItem("ds_admin_key", key);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const saved = localStorage.getItem("ds_admin_key");
    if (saved) {
      setApiKey(saved);
      loadData(saved);
    }
  }, []);

  if (!authed) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Intelligence Dashboard</CardTitle>
          </CardHeader>
          <CardBody>
            <p className="text-sm text-[var(--text-dim)] mb-4">
              Admin API key required.
            </p>
            <div className="space-y-3">
              <Input
                type="password"
                placeholder="ds_admin_..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && apiKey && loadData(apiKey)}
              />
              {error && <div className="text-xs text-[var(--red)]">{error}</div>}
              <Button onClick={() => loadData(apiKey)} disabled={!apiKey || loading}>
                {loading ? "Loading…" : "Access"}
              </Button>
            </div>
          </CardBody>
        </Card>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-6 text-sm text-[var(--text-dim)]">Loading intelligence…</div>
    );
  }

  const cacheHitPct = ((data.totals_7d?.cache_hit_rate_7d || 0) * 100).toFixed(1);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <PageHeader
        eyebrow="Analytics / Intelligence"
        title="AI Agent Intelligence"
        description="What AI agents are asking DepScope for, grouped, ranked, and inferred — 7 day window."
        actions={
          <Button onClick={() => loadData(apiKey)} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </Button>
        }
      />

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <Card><CardBody>
          <Stat value={(data.totals_7d?.calls_7d ?? 0).toLocaleString()} label="Calls 7d" />
        </CardBody></Card>
        <Card><CardBody>
          <Stat value={(data.totals_7d?.sessions_7d ?? 0).toLocaleString()} label="Sessions 7d" />
        </CardBody></Card>
        <Card><CardBody>
          <Stat value={(data.totals_7d?.ips_7d ?? 0).toLocaleString()} label="Unique IPs 7d" />
        </CardBody></Card>
        <Card><CardBody>
          <Stat value={`${data.totals_7d?.avg_ms_7d ?? 0} ms`} label="Avg latency" />
        </CardBody></Card>
        <Card><CardBody>
          <Stat value={`${cacheHitPct}%`} label="Cache hit rate" />
        </CardBody></Card>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 mb-4 border-b border-[var(--border)]">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id
                ? "border-[var(--accent)] text-[var(--text)]"
                : "border-transparent text-[var(--text-dim)] hover:text-[var(--text)]"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "searches" && (
        <Section title="Top Searches — last 24h" description="Excludes internal SDK, Claude/GPT crawler bots.">
          <Card>
            <Table>
              <Thead>
                <Tr><Th>#</Th><Th>Ecosystem</Th><Th>Package</Th><Th className="text-right">Calls</Th></Tr>
              </Thead>
              <Tbody>
                {data.top_searches_24h.map((r, i) => (
                  <Tr key={`${r.ecosystem}-${r.package_name}`}>
                    <Td className="tabular-nums text-[var(--text-dim)]">{i + 1}</Td>
                    <Td><Badge variant="neutral">{r.ecosystem}</Badge></Td>
                    <Td className="font-mono">{r.package_name}</Td>
                    <Td className="text-right tabular-nums">{r.calls.toLocaleString()}</Td>
                  </Tr>
                ))}
                {data.top_searches_24h.length === 0 && (
                  <Tr><Td className="text-[var(--text-dim)] py-4">No searches yet.</Td><Td>-</Td><Td>-</Td><Td>-</Td></Tr>
                )}
              </Tbody>
            </Table>
          </Card>
        </Section>
      )}

      {tab === "agents" && (
        <Section title="AI Agents — 7 day breakdown">
          <div className="grid md:grid-cols-2 gap-4">
            <Card>
              <CardHeader><CardTitle>Source distribution</CardTitle></CardHeader>
              <CardBody>
                <div style={{ width: "100%", height: 300 }}>
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie
                        data={data.agents_7d}
                        dataKey="calls"
                        nameKey="source"
                        cx="50%" cy="50%"
                        outerRadius={100}
                        label={(e: any) => `${e.source}`}
                      >
                        {data.agents_7d.map((_, i) => (
                          <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </CardBody>
            </Card>
            <Card>
              <Table>
                <Thead>
                  <Tr><Th>Source</Th><Th className="text-right">Calls</Th><Th className="text-right">Unique IPs</Th></Tr>
                </Thead>
                <Tbody>
                  {data.agents_7d.map((r) => (
                    <Tr key={r.source}>
                      <Td className="font-mono">{r.source}</Td>
                      <Td className="text-right tabular-nums">{r.calls.toLocaleString()}</Td>
                      <Td className="text-right tabular-nums">{r.unique_ips.toLocaleString()}</Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Card>
          </div>
        </Section>
      )}

      {tab === "countries" && (
        <Section title="Countries — last 7 days" description="Country resolved via Cloudflare CF-IPCountry header.">
          <Card>
            <Table>
              <Thead>
                <Tr><Th>Country</Th><Th>Code</Th><Th className="text-right">Calls</Th><Th className="text-right">Unique IPs</Th></Tr>
              </Thead>
              <Tbody>
                {data.countries_7d.map((r) => (
                  <Tr key={r.country}>
                    <Td className="font-mono">{FLAGS[r.country] || r.country}</Td>
                    <Td><Badge variant="neutral">{r.country}</Badge></Td>
                    <Td className="text-right tabular-nums">{r.calls.toLocaleString()}</Td>
                    <Td className="text-right tabular-nums">{r.unique_ips.toLocaleString()}</Td>
                  </Tr>
                ))}
                {data.countries_7d.length === 0 && (
                  <Tr><Td className="text-[var(--text-dim)] py-4">Not enough data yet.</Td><Td>-</Td><Td>-</Td><Td>-</Td></Tr>
                )}
              </Tbody>
            </Table>
          </Card>
        </Section>
      )}

      {tab === "intents" && (
        <Section title="Inferred intent & stacks — 7 day sessions">
          <div className="grid md:grid-cols-2 gap-4">
            <Card>
              <CardHeader><CardTitle>Intents</CardTitle></CardHeader>
              <CardBody>
                <div style={{ width: "100%", height: 260 }}>
                  <ResponsiveContainer>
                    <BarChart data={data.intents_7d}>
                      <XAxis dataKey="inferred_intent" stroke="var(--text-dim)" fontSize={11} />
                      <YAxis stroke="var(--text-dim)" fontSize={11} />
                      <Tooltip />
                      <Bar dataKey="count" fill="#3b82f6" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardBody>
            </Card>
            <Card>
              <CardHeader><CardTitle>Inferred stacks</CardTitle></CardHeader>
              <CardBody>
                <Table>
                  <Thead>
                    <Tr><Th>Stack</Th><Th className="text-right">Sessions</Th></Tr>
                  </Thead>
                  <Tbody>
                    {data.stacks_7d.map((r) => (
                      <Tr key={r.stack}>
                        <Td className="font-mono">{r.stack}</Td>
                        <Td className="text-right tabular-nums">{r.sessions.toLocaleString()}</Td>
                      </Tr>
                    ))}
                    {data.stacks_7d.length === 0 && (
                      <Tr><Td className="text-[var(--text-dim)] py-4">No stack data yet.</Td><Td>-</Td></Tr>
                    )}
                  </Tbody>
                </Table>
              </CardBody>
            </Card>
          </div>
        </Section>
      )}

      {tab === "combos" && (
        <Section
          title="Top co-occurrence"
          description="Packages frequently requested together within a session."
        >
          <Card>
            <Table>
              <Thead>
                <Tr>
                  <Th>Ecosystem</Th>
                  <Th>Package A</Th>
                  <Th>Package B</Th>
                  <Th className="text-right">Co-occurrences</Th>
                </Tr>
              </Thead>
              <Tbody>
                {data.top_cooccurrence.map((r, i) => (
                  <Tr key={i}>
                    <Td><Badge variant="neutral">{r.ecosystem}</Badge></Td>
                    <Td className="font-mono">{r.package_a}</Td>
                    <Td className="font-mono">{r.package_b}</Td>
                    <Td className="text-right tabular-nums">{r.cooccurrence_count.toLocaleString()}</Td>
                  </Tr>
                ))}
                {data.top_cooccurrence.length === 0 && (
                  <Tr><Td className="text-[var(--text-dim)] py-4">No pairs observed yet.</Td><Td>-</Td><Td>-</Td><Td>-</Td></Tr>
                )}
              </Tbody>
            </Table>
          </Card>
        </Section>
      )}

      {tab === "trending" && (
        <Section
          title="Trending packages"
          description="Snapshot ranked by week-over-week growth."
        >
          <Card>
            <Table>
              <Thead>
                <Tr>
                  <Th>Rank</Th>
                  <Th>Δ</Th>
                  <Th>Ecosystem</Th>
                  <Th>Package</Th>
                  <Th className="text-right">Calls 1d</Th>
                  <Th className="text-right">Growth 7d</Th>
                </Tr>
              </Thead>
              <Tbody>
                {data.trending_packages.map((r, i) => (
                  <Tr key={i}>
                    <Td className="tabular-nums">{r.rank}</Td>
                    <Td>
                      <Badge variant={r.rank_change && r.rank_change > 0 ? "success" : r.rank_change && r.rank_change < 0 ? "danger" : "neutral"}>
                        {rankChangeLabel(r.rank_change)}
                      </Badge>
                    </Td>
                    <Td><Badge variant="neutral">{r.ecosystem}</Badge></Td>
                    <Td className="font-mono">{r.package_name}</Td>
                    <Td className="text-right tabular-nums">{r.call_count.toLocaleString()}</Td>
                    <Td className="text-right">
                      <Badge variant={growthVariant(r.week_growth_pct)}>
                        {fmtPct(r.week_growth_pct)}
                      </Badge>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Card>
        </Section>
      )}

      {tab === "errors" && (
        <Section title="Top error queries — 7 days" description="What errors agents ask us to resolve.">
          <Card>
            <Table>
              <Thead>
                <Tr><Th>Error query</Th><Th className="text-right">Searches</Th></Tr>
              </Thead>
              <Tbody>
                {data.top_errors.map((r, i) => (
                  <Tr key={i}>
                    <Td className="font-mono">{r.error_query}</Td>
                    <Td className="text-right tabular-nums">{r.searches.toLocaleString()}</Td>
                  </Tr>
                ))}
                {data.top_errors.length === 0 && (
                  <Tr><Td className="text-[var(--text-dim)] py-4">No error queries yet.</Td><Td>-</Td></Tr>
                )}
              </Tbody>
            </Table>
          </Card>
        </Section>
      )}
    </div>
  );
}
