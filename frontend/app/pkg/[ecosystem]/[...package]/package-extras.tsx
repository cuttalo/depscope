"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
  CartesianGrid,
} from "recharts";

// ===== Types =====
interface BundleInfo {
  size_kb: number;
  gzip_kb: number;
  dependency_count: number;
  has_js_module: boolean;
  has_side_effects: boolean;
  scoped: boolean;
  source: string;
}

interface TypeScriptInfo {
  score: number;
  has_types: boolean;
  types_source: string;
  types_package: string | null;
}

interface HistoryPoint {
  date: string;
  score: number;
  risk: string;
  vuln_count: number;
}

interface HistoryData {
  package: string;
  ecosystem: string;
  days: number;
  snapshot_count: number;
  trend: string;
  stats: {
    min: number;
    max: number;
    avg: number;
    current: number;
    first: number;
    delta: number;
  };
  history: HistoryPoint[];
}

interface TreeNode {
  name: string;
  version: string;
  health_score: number;
  risk: string;
  vuln_count: number;
  license: string | null;
  deprecated: boolean;
  depth: number;
  deps: TreeNode[];
}

interface TreeData {
  package: string;
  ecosystem: string;
  version: string;
  health_score: number;
  total_deps: number;
  direct_deps_count: number;
  max_depth: number;
  risk_summary: {
    critical_vulns: number;
    deprecated_count: number;
    low_health_count: number;
  };
  tree: TreeNode[];
}

interface LicenseData {
  package: string;
  ecosystem: string;
  total_deps_analyzed: number;
  licenses: Record<string, number>;
  unknown_count: number;
  warnings: string[];
  commercial_safe: boolean;
  recommended_license_file: string | null;
}

// ===== Color helpers =====
function scoreColor(score: number): string {
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#eab308";
  if (score >= 40) return "#f97316";
  return "#ef4444";
}

function scoreBadgeClass(score: number): string {
  if (score >= 80) return "bg-green-500/20 text-green-400 border-green-500/30";
  if (score >= 60) return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
  if (score >= 40) return "bg-orange-500/20 text-orange-400 border-orange-500/30";
  return "bg-red-500/20 text-red-400 border-red-500/30";
}

// ===== Skeleton =====
function SectionSkeleton({ label }: { label: string }) {
  return (
    <div className="card p-6 animate-pulse">
      <h3 className="font-semibold mb-3 text-[var(--text-dim)]">{label}</h3>
      <div className="h-4 bg-[var(--bg)] rounded w-3/4 mb-2"></div>
      <div className="h-4 bg-[var(--bg)] rounded w-1/2"></div>
    </div>
  );
}

// ===== Bundle & TypeScript =====
export function BundleTypescriptCard({
  bundle,
  typescript,
}: {
  bundle: BundleInfo | null;
  typescript: TypeScriptInfo | null;
}) {
  if (!bundle && !typescript) return null;

  const tsScoreColor = typescript ? scoreColor(typescript.score * 10) : "#eab308";
  const tsSourceLabel: Record<string, string> = {
    "definitely-typed": "DefinitelyTyped",
    "built-in": "Built-in types",
    "none": "No types",
  };

  return (
    <div className="card p-6">
      <h2 className="font-semibold mb-4">Bundle &amp; TypeScript</h2>
      <div className="grid md:grid-cols-2 gap-6">
        {bundle && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xl">&#128230;</span>
              <h3 className="font-semibold">Bundle Size</h3>
            </div>
            <div className="text-2xl font-bold text-[var(--accent)]">
              {bundle.size_kb.toFixed(1)} KB
              <span className="text-sm text-[var(--text-dim)] font-normal ml-2">
                minified
              </span>
            </div>
            <div className="text-lg text-[var(--text-dim)]">
              {bundle.gzip_kb.toFixed(1)} KB gzipped
            </div>
            <div className="text-sm text-[var(--text-dim)] mt-2">
              {bundle.dependency_count} direct dependencies
            </div>
            <div className="flex flex-wrap gap-2 mt-3 text-xs">
              {bundle.has_js_module && (
                <span className="px-2 py-0.5 rounded border border-[var(--border)] text-[var(--text-dim)]">
                  ESM
                </span>
              )}
              {bundle.has_side_effects && (
                <span className="px-2 py-0.5 rounded border border-orange-500/30 text-orange-400">
                  side effects
                </span>
              )}
              {bundle.scoped && (
                <span className="px-2 py-0.5 rounded border border-[var(--border)] text-[var(--text-dim)]">
                  scoped
                </span>
              )}
            </div>
          </div>
        )}

        {typescript && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xl">&#127775;</span>
              <h3 className="font-semibold">TypeScript</h3>
            </div>
            <div className="flex items-baseline gap-2">
              <span
                className="text-2xl font-bold"
                style={{ color: tsScoreColor }}
              >
                {typescript.score}/10
              </span>
              <span className="text-sm text-[var(--text-dim)]">
                {typescript.has_types ? "typed" : "untyped"}
              </span>
            </div>
            {typescript.types_package && (
              <div className="text-sm text-[var(--text-dim)] mt-2">
                Types from{" "}
                <code className="text-[var(--accent)]">
                  {typescript.types_package}
                </code>
                {typescript.types_source === "definitely-typed" && (
                  <> (DefinitelyTyped)</>
                )}
              </div>
            )}
            {!typescript.types_package && typescript.has_types && (
              <div className="text-sm text-[var(--text-dim)] mt-2">
                {tsSourceLabel[typescript.types_source] || typescript.types_source}
              </div>
            )}
            {!typescript.has_types && (
              <div className="text-sm text-orange-400 mt-2">
                No type definitions available
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ===== Health History =====
export function HealthHistorySection({
  ecosystem,
  pkg,
}: {
  ecosystem: string;
  pkg: string;
}) {
  const [data, setData] = useState<HistoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let alive = true;
    fetch(`/api/history/${ecosystem}/${pkg}?days=90`)
      .then((r) => {
        if (!r.ok) throw new Error("not ok");
        return r.json();
      })
      .then((d) => {
        if (alive) {
          setData(d);
          setLoading(false);
        }
      })
      .catch(() => {
        if (alive) {
          setError(true);
          setLoading(false);
        }
      });
    return () => {
      alive = false;
    };
  }, [ecosystem, pkg]);

  if (loading) return <SectionSkeleton label="Health History" />;
  if (error || !data) return null;

  const singlePoint = data.history.length <= 1;

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <h2 className="font-semibold">Health History (90 days)</h2>
        <div className="flex items-center gap-3 text-xs text-[var(--text-dim)]">
          <span>
            Trend:{" "}
            <span
              className={
                data.trend === "up"
                  ? "text-green-400"
                  : data.trend === "down"
                  ? "text-red-400"
                  : "text-[var(--text-dim)]"
              }
            >
              {data.trend}
            </span>
          </span>
          <span>
            Delta:{" "}
            <span
              className={
                data.stats.delta > 0
                  ? "text-green-400"
                  : data.stats.delta < 0
                  ? "text-red-400"
                  : ""
              }
            >
              {data.stats.delta > 0 ? "+" : ""}
              {data.stats.delta}
            </span>
          </span>
        </div>
      </div>

      {singlePoint ? (
        <div className="text-center py-10 text-[var(--text-dim)]">
          <p className="text-sm">
            Collecting data — come back tomorrow to see the trend.
          </p>
          <p className="text-xs mt-2">
            Current score:{" "}
            <span
              className="font-bold"
              style={{ color: scoreColor(data.stats.current) }}
            >
              {data.stats.current}/100
            </span>
          </p>
        </div>
      ) : (
        <div className="w-full h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={data.history}
              margin={{ top: 8, right: 12, left: 0, bottom: 4 }}
            >
              <CartesianGrid stroke="#2a2a3a" strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tick={{ fill: "#9ca3af", fontSize: 11 }}
                stroke="#2a2a3a"
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: "#9ca3af", fontSize: 11 }}
                stroke="#2a2a3a"
              />
              <ReferenceArea y1={0} y2={40} fill="#ef4444" fillOpacity={0.08} />
              <ReferenceArea y1={40} y2={60} fill="#f97316" fillOpacity={0.08} />
              <ReferenceArea y1={60} y2={80} fill="#eab308" fillOpacity={0.08} />
              <ReferenceArea y1={80} y2={100} fill="#22c55e" fillOpacity={0.08} />
              <Tooltip
                contentStyle={{
                  background: "#1a1a2a",
                  border: "1px solid #2a2a3a",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
                labelStyle={{ color: "#9ca3af" }}
                itemStyle={{ color: "#eab308" }}
                formatter={((value: unknown, _name: unknown, entry: unknown) => {
                  const v = typeof value === "number" ? value : Number(value);
                  const e = entry as { payload?: { vuln_count?: number } } | undefined;
                  const vc = e?.payload?.vuln_count ?? 0;
                  return [`${v}/100 — ${vc} vuln${vc === 1 ? "" : "s"}`, "Score"];
                }) as never}
              />
              <Line
                type="monotone"
                dataKey="score"
                stroke="var(--accent)"
                strokeWidth={2}
                dot={{ r: 3, fill: "var(--accent)" }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid grid-cols-4 gap-3 mt-4 text-center text-xs text-[var(--text-dim)]">
        <div>
          <div className="text-sm font-bold text-[var(--text)]">
            {data.stats.current}
          </div>
          <div>current</div>
        </div>
        <div>
          <div className="text-sm font-bold text-[var(--text)]">
            {data.stats.min}
          </div>
          <div>min</div>
        </div>
        <div>
          <div className="text-sm font-bold text-[var(--text)]">
            {data.stats.max}
          </div>
          <div>max</div>
        </div>
        <div>
          <div className="text-sm font-bold text-[var(--text)]">
            {data.stats.avg.toFixed(0)}
          </div>
          <div>avg</div>
        </div>
      </div>
    </div>
  );
}

// ===== Dependency Tree =====
export function DependencyTreeSection({
  ecosystem,
  pkg,
}: {
  ecosystem: string;
  pkg: string;
}) {
  const [data, setData] = useState<TreeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    let alive = true;
    fetch(`/api/tree/${ecosystem}/${pkg}`)
      .then((r) => {
        if (!r.ok) throw new Error("not ok");
        return r.json();
      })
      .then((d) => {
        if (alive) {
          setData(d);
          setLoading(false);
        }
      })
      .catch(() => {
        if (alive) {
          setError(true);
          setLoading(false);
        }
      });
    return () => {
      alive = false;
    };
  }, [ecosystem, pkg]);

  if (loading) return <SectionSkeleton label="Dependency Tree" />;
  if (error || !data || !data.tree || data.tree.length === 0) return null;

  // Flatten tree (excluding root) up to 2 levels
  const flat: TreeNode[] = [];
  const walk = (nodes: TreeNode[]) => {
    for (const n of nodes) {
      flat.push(n);
      if (n.deps && n.deps.length > 0) walk(n.deps);
    }
  };
  walk(data.tree);

  // Deduplicate by name, keep lowest health (most risky first)
  const seen = new Set<string>();
  const unique: TreeNode[] = [];
  for (const n of flat.sort((a, b) => a.health_score - b.health_score)) {
    if (seen.has(n.name)) continue;
    seen.add(n.name);
    unique.push(n);
  }

  const visible = showAll ? unique : unique.slice(0, 20);
  const lowHealthPct = data.total_deps
    ? Math.round((data.risk_summary.low_health_count / data.total_deps) * 100)
    : 0;

  return (
    <div className="card p-6">
      <h2 className="font-semibold mb-2">Dependency Tree</h2>
      <p className="text-sm text-[var(--text-dim)] mb-4">
        <span className="font-semibold text-[var(--text)]">
          {data.total_deps} total deps
        </span>
        {" — "}
        <span
          className={
            data.risk_summary.low_health_count > 0 ? "text-orange-400" : ""
          }
        >
          {data.risk_summary.low_health_count} low health ({lowHealthPct}%)
        </span>
        {", "}
        <span
          className={
            data.risk_summary.critical_vulns > 0 ? "text-red-400" : ""
          }
        >
          {data.risk_summary.critical_vulns} critical vulns
        </span>
        {", "}
        <span
          className={
            data.risk_summary.deprecated_count > 0 ? "text-orange-400" : ""
          }
        >
          {data.risk_summary.deprecated_count} deprecated
        </span>
      </p>

      <ul className="space-y-2">
        {visible.map((dep) => (
          <li key={dep.name}>
            <Link
              href={`/pkg/${ecosystem}/${dep.name}`}
              className="flex items-center justify-between gap-3 p-2 rounded-lg bg-[var(--bg)] hover:bg-[var(--accent)]/5 transition"
            >
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <span className="text-sm font-mono truncate">{dep.name}</span>
                <span className="text-xs text-[var(--text-dim)]">
                  {dep.version}
                </span>
                {dep.deprecated && (
                  <span className="text-xs px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-400">
                    deprecated
                  </span>
                )}
                {dep.vuln_count > 0 && (
                  <span className="text-xs px-1.5 py-0.5 rounded bg-red-500/20 text-red-400">
                    {dep.vuln_count} vuln
                  </span>
                )}
              </div>
              <span
                className={`text-xs px-2 py-0.5 rounded border ${scoreBadgeClass(
                  dep.health_score
                )}`}
              >
                {dep.health_score}
              </span>
            </Link>
          </li>
        ))}
      </ul>

      {unique.length > 20 && (
        <div className="mt-4 text-center">
          <button
            onClick={() => setShowAll(!showAll)}
            className="text-sm text-[var(--accent)] hover:underline font-medium"
          >
            {showAll
              ? "Show less"
              : `Show all ${unique.length} \u2192`}
          </button>
        </div>
      )}

      <div className="mt-3 text-right text-xs text-[var(--text-dim)]">
        <Link
          href={`/pkg/${ecosystem}/${pkg}`}
          className="hover:text-[var(--accent)] transition"
        >
          See all deps &rarr;
        </Link>
      </div>
    </div>
  );
}

// ===== License Audit =====
export function LicenseAuditSection({
  ecosystem,
  pkg,
}: {
  ecosystem: string;
  pkg: string;
}) {
  const [data, setData] = useState<LicenseData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let alive = true;
    fetch(`/api/licenses/${ecosystem}/${pkg}`)
      .then((r) => {
        if (!r.ok) throw new Error("not ok");
        return r.json();
      })
      .then((d) => {
        if (alive) {
          setData(d);
          setLoading(false);
        }
      })
      .catch(() => {
        if (alive) {
          setError(true);
          setLoading(false);
        }
      });
    return () => {
      alive = false;
    };
  }, [ecosystem, pkg]);

  if (loading) return <SectionSkeleton label="License Audit" />;
  if (error || !data) return null;

  const entries = Object.entries(data.licenses).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((s, [, v]) => s + v, 0) || 1;

  const licenseColors: Record<string, string> = {
    MIT: "#22c55e",
    ISC: "#3b82f6",
    "Apache-2.0": "#8b5cf6",
    "BSD-3-Clause": "#eab308",
    "BSD-2-Clause": "#f59e0b",
    "GPL-3.0": "#ef4444",
    "AGPL-3.0": "#ef4444",
    "LGPL-3.0": "#f97316",
  };

  return (
    <div className="card p-6">
      <h2 className="font-semibold mb-4">License Audit</h2>

      <div className="mb-4">
        {data.commercial_safe ? (
          <span className="inline-block px-4 py-2 rounded-lg bg-green-500/20 text-green-400 border border-green-500/30 font-semibold">
            Commercial safe &#10003;
          </span>
        ) : (
          <span className="inline-block px-4 py-2 rounded-lg bg-orange-500/20 text-orange-400 border border-orange-500/30 font-semibold">
            &#9888; Review licenses
          </span>
        )}
        <span className="ml-3 text-sm text-[var(--text-dim)]">
          {data.total_deps_analyzed} deps analyzed
          {data.unknown_count > 0 && `, ${data.unknown_count} unknown`}
        </span>
      </div>

      {/* Horizontal stacked bar */}
      {entries.length > 0 && (
        <div className="mb-4">
          <div className="flex h-3 rounded-full overflow-hidden bg-[var(--bg)]">
            {entries.map(([name, count]) => (
              <div
                key={name}
                style={{
                  width: `${(count / total) * 100}%`,
                  background: licenseColors[name] || "#6b7280",
                }}
                title={`${name}: ${count}`}
              />
            ))}
          </div>
          <div className="flex flex-wrap gap-3 mt-3 text-sm">
            {entries.map(([name, count]) => (
              <div key={name} className="flex items-center gap-2">
                <span
                  className="w-3 h-3 rounded-sm"
                  style={{ background: licenseColors[name] || "#6b7280" }}
                />
                <span className="text-[var(--text)]">{name}</span>
                <span className="text-[var(--text-dim)]">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.warnings.length > 0 && (
        <div className="mt-4 p-3 rounded-lg bg-orange-500/10 border border-orange-500/30">
          <h3 className="text-sm font-semibold text-orange-400 mb-2">
            &#9888; Warnings
          </h3>
          <ul className="space-y-1">
            {data.warnings.map((w, i) => (
              <li key={i} className="text-sm text-[var(--text-dim)]">
                &bull; {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-3 text-right text-xs text-[var(--text-dim)]">
        <a
          href={`/api/licenses/${ecosystem}/${pkg}`}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-[var(--accent)] transition"
        >
          License details &rarr;
        </a>
      </div>
    </div>
  );
}
