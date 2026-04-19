"use client";

import { useEffect, useState } from "react";

interface Job {
  schedule: string;
  name: string;
  log: string;
  last_run: string | null;
  last_line: string;
  status: "ok" | "warning" | "error" | "unknown";
}

interface Pm2Proc {
  name?: string;
  status?: string;
  restarts?: number;
  uptime_ms?: number;
  cpu?: number;
  memory_mb?: number;
  error?: string;
}

interface AutomationData {
  jobs: Job[];
  disk: { total: number; used: number; free: number; pct: number };
  db: { size: string; packages: number; vulnerabilities: number };
  pm2: Pm2Proc[];
  generated_at: string;
}

const STATUS_COLOR: Record<string, string> = {
  ok: "text-green-500",
  warning: "text-amber-500",
  error: "text-red-500",
  unknown: "text-[var(--text-dim)]",
};

function humanBytes(n: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }
  return `${n.toFixed(1)} ${units[i]}`;
}

function timeAgo(iso: string | null): string {
  if (!iso) return "never";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}

export default function AutomationPage() {
  const [apiKey, setApiKey] = useState("");
  const [authed, setAuthed] = useState(false);
  const [data, setData] = useState<AutomationData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = async (key: string) => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/admin/automation", {
        headers: { "X-API-Key": key },
      });
      if (!res.ok) throw new Error("Access denied. Check your admin API key.");
      setData(await res.json());
      setAuthed(true);
      localStorage.setItem("ds_admin_key", key);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error");
      setAuthed(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const saved = localStorage.getItem("ds_admin_key");
    if (saved) {
      setApiKey(saved);
      load(saved);
    }
  }, []);

  // Auto-refresh every 60s when authed
  useEffect(() => {
    if (!authed) return;
    const id = setInterval(() => load(apiKey), 60000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed, apiKey]);

  if (!authed) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="w-full max-w-sm border border-[var(--border)] rounded-lg p-6">
          <h1 className="text-lg font-semibold mb-4">Admin · Automation</h1>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Admin API key (ds_admin_...)"
            className="w-full px-3 py-2 rounded border border-[var(--border)] bg-transparent mb-3 font-mono text-sm"
          />
          <button
            onClick={() => load(apiKey)}
            disabled={loading || !apiKey}
            className="w-full px-3 py-2 rounded bg-[var(--accent)] text-white disabled:opacity-50"
          >
            {loading ? "Loading…" : "Load dashboard"}
          </button>
          {error && <p className="mt-3 text-sm text-red-500">{error}</p>}
        </div>
      </div>
    );
  }

  if (!data) return <div className="p-8">Loading…</div>;

  const diskWarn = data.disk.pct >= 80;
  const diskCrit = data.disk.pct >= 90;

  return (
    <div className="min-h-screen p-6 max-w-[1200px] mx-auto">
      <header className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Automation</h1>
        <div className="text-xs text-[var(--text-dim)]">
          refreshed {timeAgo(data.generated_at)} · auto-refresh 60s
        </div>
      </header>

      {/* Top metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className={`border rounded-lg p-4 ${diskCrit ? "border-red-500" : diskWarn ? "border-amber-500" : "border-[var(--border)]"}`}>
          <div className="text-xs text-[var(--text-dim)] uppercase tracking-wider mb-1">Disk usage</div>
          <div className="text-2xl font-semibold">{data.disk.pct}%</div>
          <div className="text-xs text-[var(--text-dim)] mt-1">
            {humanBytes(data.disk.used)} / {humanBytes(data.disk.total)} · free {humanBytes(data.disk.free)}
          </div>
        </div>
        <div className="border border-[var(--border)] rounded-lg p-4">
          <div className="text-xs text-[var(--text-dim)] uppercase tracking-wider mb-1">Database</div>
          <div className="text-2xl font-semibold">{data.db.size}</div>
          <div className="text-xs text-[var(--text-dim)] mt-1">
            {data.db.packages.toLocaleString()} pkgs · {data.db.vulnerabilities.toLocaleString()} vulns
          </div>
        </div>
        <div className="border border-[var(--border)] rounded-lg p-4">
          <div className="text-xs text-[var(--text-dim)] uppercase tracking-wider mb-1">PM2 processes</div>
          <div className="text-2xl font-semibold">
            {data.pm2.filter((p) => p.status === "online").length}/{data.pm2.length}
          </div>
          <div className="text-xs text-[var(--text-dim)] mt-1">online</div>
        </div>
      </div>

      {/* Jobs table */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--text-dim)] mb-3">Cron jobs</h2>
        <div className="overflow-x-auto border border-[var(--border)] rounded-lg">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="px-4 py-2 text-left text-[11px] uppercase tracking-wider text-[var(--text-dim)] font-medium">Status</th>
                <th className="px-4 py-2 text-left text-[11px] uppercase tracking-wider text-[var(--text-dim)] font-medium">Job</th>
                <th className="px-4 py-2 text-left text-[11px] uppercase tracking-wider text-[var(--text-dim)] font-medium">Schedule</th>
                <th className="px-4 py-2 text-left text-[11px] uppercase tracking-wider text-[var(--text-dim)] font-medium">Last run</th>
                <th className="px-4 py-2 text-left text-[11px] uppercase tracking-wider text-[var(--text-dim)] font-medium">Last line</th>
              </tr>
            </thead>
            <tbody>
              {data.jobs.map((j) => (
                <tr key={j.name} className="border-b border-[var(--border)] last:border-0">
                  <td className={`px-4 py-2 font-medium ${STATUS_COLOR[j.status]}`}>{j.status}</td>
                  <td className="px-4 py-2 font-mono text-xs">{j.name}</td>
                  <td className="px-4 py-2 font-mono text-xs text-[var(--text-dim)]">{j.schedule}</td>
                  <td className="px-4 py-2 text-xs text-[var(--text-dim)]">{timeAgo(j.last_run)}</td>
                  <td className="px-4 py-2 text-xs text-[var(--text-dim)] truncate max-w-[400px]" title={j.last_line}>
                    {j.last_line || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* PM2 table */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--text-dim)] mb-3">PM2 processes</h2>
        <div className="overflow-x-auto border border-[var(--border)] rounded-lg">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="px-4 py-2 text-left text-[11px] uppercase tracking-wider text-[var(--text-dim)] font-medium">Name</th>
                <th className="px-4 py-2 text-left text-[11px] uppercase tracking-wider text-[var(--text-dim)] font-medium">Status</th>
                <th className="px-4 py-2 text-right text-[11px] uppercase tracking-wider text-[var(--text-dim)] font-medium">Restarts</th>
                <th className="px-4 py-2 text-right text-[11px] uppercase tracking-wider text-[var(--text-dim)] font-medium">CPU</th>
                <th className="px-4 py-2 text-right text-[11px] uppercase tracking-wider text-[var(--text-dim)] font-medium">Memory</th>
              </tr>
            </thead>
            <tbody>
              {data.pm2.map((p, i) => (
                <tr key={p.name || i} className="border-b border-[var(--border)] last:border-0">
                  <td className="px-4 py-2 font-mono text-xs">{p.name ?? p.error ?? "—"}</td>
                  <td className={`px-4 py-2 text-xs ${p.status === "online" ? "text-green-500" : "text-red-500"}`}>{p.status ?? "—"}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{p.restarts ?? "—"}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{p.cpu != null ? `${p.cpu}%` : "—"}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{p.memory_mb != null ? `${p.memory_mb} MB` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
