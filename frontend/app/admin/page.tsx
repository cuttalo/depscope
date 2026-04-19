"use client";

import { useEffect, useState } from "react";
import { AreaChart, Area, BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

interface DashboardData {
  users: { id: number; email: string; role: string; plan: string; api_key: string; created_at: string }[];
  usage_by_day: { day: string; calls: number }[];
  usage_by_ecosystem: { ecosystem: string; calls: number }[];
  top_packages: { ecosystem: string; package_name: string; searches: number }[];
  top_agents: { agent: string; calls: number }[];
}

interface RealtimeStats {
  api_calls_total: number;
  api_calls_today: number;
  registered_users: number;
  packages_indexed: number;
  vulnerabilities_tracked: number;
  trending: { ecosystem: string; package: string; searches: number }[];
  ecosystems?: string[];
  ecosystem_counts?: Record<string, number>;
}


interface PageViewsEntry { path: string; views: number }
interface PageViewsByDay { day: string; views: number; unique: number }
interface PageViewsByCountry { country: string; views: number }
interface PageViewsByReferrer { referrer: string; views: number }

interface PageViews {
  total: number;
  today: number;
  unique_today: number;
  by_page: PageViewsEntry[];
  by_day: PageViewsByDay[];
  by_country: PageViewsByCountry[];
  by_referrer: PageViewsByReferrer[];
}

const FLAG_MAP: Record<string, string> = {
  US: "🇺🇸", IT: "🇮🇹", CN: "🇨🇳", FI: "🇫🇮", IE: "🇮🇪",
  SG: "🇸🇬", GB: "🇬🇧", DE: "🇩🇪", FR: "🇫🇷", JP: "🇯🇵",
  IN: "🇮🇳", BR: "🇧🇷", CA: "🇨🇦", AU: "🇦🇺", NL: "🇳🇱", NZ: "🇳🇿", KR: "🇰🇷", SE: "🇸🇪", ES: "🇪🇸", RU: "🇷🇺", MX: "🇲🇽", PL: "🇵🇱", TW: "🇹🇼", IL: "🇮🇱", AR: "🇦🇷", TH: "🇹🇭",
};

export default function AdminPage() {
  const [apiKey, setApiKey] = useState("");
  const [authed, setAuthed] = useState(false);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [stats, setStats] = useState<RealtimeStats | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [pageviews, setPageviews] = useState<PageViews | null>(null);
  const [sources, setSources] = useState<Record<string, any> | null>(null);
  const [charts, setCharts] = useState<any>(null);

  const login = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/admin/dashboard", {
        headers: { "X-API-Key": apiKey },
      });
      if (!res.ok) throw new Error("Access denied. Check your API key.");
      const data = await res.json();
      setDashboard(data);
      setAuthed(true);
      localStorage.setItem("ds_admin_key", apiKey);

      const statsRes = await fetch("/api/admin/stats", { headers: { "X-API-Key": apiKey } });
      if (statsRes.ok) setStats(await statsRes.json());

      const pvRes = await fetch("/api/admin/pageviews", { headers: { "X-API-Key": apiKey } });
      if (pvRes.ok) setPageviews(await pvRes.json());

      const chartsRes = await fetch("/api/admin/charts", { headers: { "X-API-Key": apiKey } });
      if (chartsRes.ok) setCharts(await chartsRes.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setLoading(false);
    }
  };

  const refresh = async () => {
    if (!apiKey) return;
    try {
      const [dashRes, statsRes, pvRes, , chartsRes] = await Promise.all([
        fetch("/api/admin/dashboard", { headers: { "X-API-Key": apiKey } }),
        fetch("/api/admin/stats", { headers: { "X-API-Key": apiKey } }),
        fetch("/api/admin/pageviews", { headers: { "X-API-Key": apiKey } }),
        fetch("/api/admin/sources", { headers: { "X-API-Key": apiKey } }),
        fetch("/api/admin/charts", { headers: { "X-API-Key": apiKey } }),
      ]);
      if (dashRes.ok) setDashboard(await dashRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
      if (pvRes.ok) setPageviews(await pvRes.json());
      if (chartsRes.ok) setCharts(await chartsRes.json());
    } catch {}
  };

  useEffect(() => {
    const saved = localStorage.getItem("ds_admin_key");
    if (saved) {
      setApiKey(saved);
      setTimeout(() => {
        fetch("/api/admin/dashboard", { headers: { "X-API-Key": saved } })
          .then((r) => {
            if (r.ok) return r.json();
            throw new Error("expired");
          })
          .then((data) => {
            setDashboard(data);
            setAuthed(true);
            fetch("/api/admin/stats", { headers: { "X-API-Key": saved } }).then((r) => r.ok ? r.json() : null).then((d) => d && setStats(d));
            fetch("/api/admin/pageviews", { headers: { "X-API-Key": saved } }).then((r) => r.ok ? r.json() : null).then((d) => d && setPageviews(d));
            fetch("/api/admin/sources", { headers: { "X-API-Key": saved } }).then((r) => r.ok ? r.json() : null).then((d) => d && setSources(d));
            fetch("/api/admin/charts", { headers: { "X-API-Key": saved } }).then((r) => r.ok ? r.json() : null).then((d) => d && setCharts(d));
          })
          .catch(() => localStorage.removeItem("ds_admin_key"));
      }, 100);
    }
  }, []);

  // Auto-refresh every 30s
  useEffect(() => {
    if (!authed) return;
    const interval = setInterval(refresh, 30000);
    return () => clearInterval(interval);
  }, [authed, apiKey]);

  if (!authed) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="card p-8 w-full max-w-md">
          <h1 className="text-2xl font-bold mb-6 gradient-text">DepScope Admin</h1>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && login()}
            placeholder="Admin API Key (ds_admin_...)"
            className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-4 py-3 mb-4 focus:outline-none focus:border-[var(--accent)]"
          />
          <button
            onClick={login}
            disabled={loading}
            className="w-full bg-[var(--accent)] text-black font-semibold py-3 rounded-lg hover:bg-[var(--accent-dim)] transition disabled:opacity-50"
          >
            {loading ? "..." : "Login"}
          </button>
          {error && <p className="text-red-400 text-sm mt-3">{error}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold gradient-text">DepScope Admin</h1>
          <a href="/agent" className="text-sm px-4 py-2 rounded-lg border border-[var(--accent)]/30 text-[var(--accent)] hover:bg-[var(--accent)]/10 transition">Marketing Agent</a><a href="/mission-control" className="text-sm px-4 py-2 rounded-lg border border-[var(--accent)]/30 text-[var(--accent)] hover:bg-[var(--accent)]/10 transition">Mission Control</a>
          <div className="flex gap-3">
            <button onClick={refresh} className="text-sm px-4 py-2 rounded-lg border border-[var(--border)] hover:bg-[var(--bg-card)] transition">
              Refresh
            </button>
            <button
              onClick={() => { setAuthed(false); localStorage.removeItem("ds_admin_key"); }}
              className="text-sm px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 transition"
            >
              Logout
            </button>
          </div>
        </div>

        {/* KPI Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
            <div className="card p-5">
              <div className="text-3xl font-bold text-[var(--accent)]">{(stats.api_calls_total ?? 0).toLocaleString()}</div>
              <div className="text-xs text-[var(--text-dim)] mt-1">Total API Calls</div>
            </div>
            <div className="card p-5">
              <div className="text-3xl font-bold text-[var(--green)]">{(stats.api_calls_today ?? 0).toLocaleString()}</div>
              <div className="text-xs text-[var(--text-dim)] mt-1">Today</div>
            </div>
            <div className="card p-5">
              <div className="text-3xl font-bold text-[var(--yellow)]">{stats.registered_users ?? 0}</div>
              <div className="text-xs text-[var(--text-dim)] mt-1">Users</div>
            </div>
            <div className="card p-5">
              <div className="text-3xl font-bold text-[var(--orange)]">{stats.packages_indexed ?? 0}</div>
              <div className="text-xs text-[var(--text-dim)] mt-1">Packages</div>
            </div>
            <div className="card p-5">
              <div className="text-3xl font-bold text-[var(--red)]">{stats.vulnerabilities_tracked ?? 0}</div>
              <div className="text-xs text-[var(--text-dim)] mt-1">Vulns Tracked</div>
            </div>
          </div>
        )}


        {/* Page Views KPI Cards */}
        {pageviews && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div className="card p-5">
              <div className="text-3xl font-bold text-[var(--accent)]">{(pageviews.today ?? 0).toLocaleString()}</div>
              <div className="text-xs text-[var(--text-dim)] mt-1">Page Views Today</div>
            </div>
            <div className="card p-5">
              <div className="text-3xl font-bold text-[var(--green)]">{(pageviews.unique_today ?? 0).toLocaleString()}</div>
              <div className="text-xs text-[var(--text-dim)] mt-1">Unique Visitors Today</div>
            </div>
            <div className="card p-5">
              <div className="text-3xl font-bold text-[var(--yellow)]">{pageviews.by_country?.length ?? 0}</div>
              <div className="text-xs text-[var(--text-dim)] mt-1">Countries</div>
            </div>
          </div>
        )}

        {/* Charts Section */}
        {charts && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            {/* Traffic Hourly */}
            {charts.pageviews_hourly?.length > 0 && (
              <div className="card p-6">
                <h2 className="font-semibold mb-4">Traffic (Hourly)</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <AreaChart data={charts.pageviews_hourly}>
                    <XAxis dataKey="hour" tick={{ fontSize: 10, fill: "#888" }} tickFormatter={(v: string) => v.slice(11, 16)} />
                    <YAxis tick={{ fontSize: 10, fill: "#888" }} />
                    <Tooltip contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 8 }} />
                    <Area type="monotone" dataKey="views" stroke="#22c55e" fill="#22c55e" fillOpacity={0.2} name="Views" />
                    <Area type="monotone" dataKey="unique" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.15} name="Unique" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Daily Views */}
            {charts.pageviews_daily?.length > 0 && (
              <div className="card p-6">
                <h2 className="font-semibold mb-4">Daily Views</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={charts.pageviews_daily}>
                    <XAxis dataKey="day" tick={{ fontSize: 10, fill: "#888" }} tickFormatter={(v: string) => v.slice(5)} />
                    <YAxis tick={{ fontSize: 10, fill: "#888" }} />
                    <Tooltip contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 8 }} />
                    <Bar dataKey="views" fill="#facc15" radius={[4, 4, 0, 0]} name="Views" />
                    <Bar dataKey="unique" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Unique" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* API Calls Hourly */}
            {charts.api_calls_hourly?.length > 0 && (
              <div className="card p-6">
                <h2 className="font-semibold mb-4">API Calls (Hourly)</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <AreaChart data={charts.api_calls_hourly}>
                    <XAxis dataKey="hour" tick={{ fontSize: 10, fill: "#888" }} tickFormatter={(v: string) => v.slice(11, 16)} />
                    <YAxis tick={{ fontSize: 10, fill: "#888" }} />
                    <Tooltip contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 8 }} />
                    <Area type="monotone" dataKey="calls" stroke="#facc15" fill="#facc15" fillOpacity={0.2} name="Calls" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* API Sources Pie */}
            {sources && Object.keys(sources.total || {}).length > 0 && (
              <div className="card p-6">
                <h2 className="font-semibold mb-4">API Sources</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={Object.entries(sources.total || {}).map(([name, value]) => ({ name, value: value as number }))}
                      cx="50%" cy="50%" outerRadius={90} innerRadius={40}
                      dataKey="value" nameKey="name" label={({ name, percent }: any) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {Object.keys(sources.total || {}).map((_, i) => (
                        <Cell key={i} fill={["#facc15", "#22c55e", "#3b82f6", "#f97316", "#8b5cf6", "#ef4444", "#06b6d4"][i % 7]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 8 }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Packages by Ecosystem (horizontal bar) */}
            {stats?.ecosystem_counts && Object.keys(stats.ecosystem_counts).length > 0 && (
              <div className="card p-6">
                <h2 className="font-semibold mb-4">Packages by Ecosystem</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={Object.entries(stats.ecosystem_counts).sort((a, b) => (b[1] as number) - (a[1] as number)).map(([name, count]) => ({ name, count }))} layout="vertical">
                    <XAxis type="number" tick={{ fontSize: 10, fill: "#888" }} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: "#ccc" }} width={80} />
                    <Tooltip contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 8 }} />
                    <Bar dataKey="count" fill="#facc15" radius={[0, 4, 4, 0]} name="Packages" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Countries Timeline */}
            {charts.countries_timeline?.length > 0 && (
              <div className="card p-6">
                <h2 className="font-semibold mb-4">Countries Reached</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={charts.countries_timeline}>
                    <XAxis dataKey="day" tick={{ fontSize: 10, fill: "#888" }} tickFormatter={(v: string) => v.slice(5)} />
                    <YAxis tick={{ fontSize: 10, fill: "#888" }} allowDecimals={false} />
                    <Tooltip contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 8 }} />
                    <Line type="monotone" dataKey="countries" stroke="#06b6d4" strokeWidth={2} dot={{ fill: "#06b6d4", r: 3 }} name="Countries" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}

        {/* Page Views Details Grid */}
        {pageviews && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {/* Countries */}
            <div className="card p-6">
              <h2 className="font-semibold mb-4">Countries</h2>
              <div className="space-y-3 max-h-80 overflow-y-auto">
                {pageviews.by_country?.map((c, i) => {
                  const max = Math.max(...(pageviews.by_country?.map((x) => x.views) || [1]));
                  const pct = max > 0 ? (c.views / max) * 100 : 0;
                  return (
                    <div key={i}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="font-medium">{FLAG_MAP[c.country] || "\u{1F30D}"} {c.country}</span>
                        <span className="text-[var(--text-dim)]">{c.views}</span>
                      </div>
                      <div className="w-full bg-[var(--bg)] rounded-full h-2">
                        <div className="h-2 rounded-full bg-[var(--accent)]" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Top Pages */}
            <div className="card p-6">
              <h2 className="font-semibold mb-4">Top Pages</h2>
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {pageviews.by_page?.map((p, i) => (
                  <div key={i} className="flex items-center justify-between p-2 rounded bg-[var(--bg)]">
                    <span className="text-sm font-mono truncate mr-2">{p.path}</span>
                    <span className="text-xs text-[var(--text-dim)] whitespace-nowrap">{p.views}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Referrers */}
            <div className="card p-6">
              <h2 className="font-semibold mb-4">Referrers</h2>
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {pageviews.by_referrer && pageviews.by_referrer.length > 0 ? (
                  pageviews.by_referrer.map((r, i) => (
                    <div key={i} className="flex items-center justify-between p-2 rounded bg-[var(--bg)]">
                      <span className="text-sm truncate mr-2">{r.referrer}</span>
                      <span className="text-xs text-[var(--text-dim)] whitespace-nowrap">{r.views}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-[var(--text-dim)]">No external referrers yet</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Visitor Timeline */}
        {pageviews?.by_day && pageviews.by_day.length > 0 && (
          <div className="card p-6 mb-8">
            <h2 className="font-semibold mb-4">Visitor Timeline</h2>
            <div className="flex items-end gap-1 h-40">
              {pageviews.by_day.map((d, i) => {
                const max = Math.max(...pageviews.by_day.map((x) => x.views));
                const h = max > 0 ? (d.views / max) * 100 : 0;
                return (
                  <div key={i} className="flex-1 flex flex-col items-center group relative">
                    <div
                      className="w-full bg-[var(--green)] rounded-t opacity-80 hover:opacity-100 transition min-h-[2px]"
                      style={{ height: `${h}%` }}
                    />
                    <div className="absolute -top-8 hidden group-hover:block bg-[var(--bg-card)] border border-[var(--border)] px-2 py-1 rounded text-xs whitespace-nowrap z-10">
                      {d.day}: {d.views} views, {d.unique} unique
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="flex justify-between text-xs text-[var(--text-dim)] mt-2">
              <span>{pageviews.by_day[0]?.day}</span>
              <span>{pageviews.by_day[pageviews.by_day.length - 1]?.day}</span>
            </div>
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-6 mb-8">
          {/* Usage by Day (chart with bars) */}
          {dashboard?.usage_by_day && dashboard.usage_by_day.length > 0 && (
            <div className="card p-6">
              <h2 className="font-semibold mb-4">API Calls (30 days)</h2>
              <div className="flex items-end gap-1 h-40">
                {dashboard.usage_by_day.map((d, i) => {
                  const max = Math.max(...dashboard.usage_by_day.map((x) => x.calls));
                  const h = max > 0 ? (d.calls / max) * 100 : 0;
                  return (
                    <div key={i} className="flex-1 flex flex-col items-center group relative">
                      <div
                        className="w-full bg-[var(--accent)] rounded-t opacity-80 hover:opacity-100 transition min-h-[2px]"
                        style={{ height: `${h}%` }}
                      />
                      <div className="absolute -top-8 hidden group-hover:block bg-[var(--bg-card)] border border-[var(--border)] px-2 py-1 rounded text-xs whitespace-nowrap">
                        {d.day}: {d.calls}
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="flex justify-between text-xs text-[var(--text-dim)] mt-2">
                <span>{dashboard.usage_by_day[0]?.day}</span>
                <span>{dashboard.usage_by_day[dashboard.usage_by_day.length - 1]?.day}</span>
              </div>
            </div>
          )}

          {/* Usage by Ecosystem */}
          {dashboard?.usage_by_ecosystem && (
            <div className="card p-6">
              <h2 className="font-semibold mb-4">By Ecosystem</h2>
              <div className="space-y-3">
                {dashboard.usage_by_ecosystem.map((e, i) => {
                  const max = Math.max(...dashboard.usage_by_ecosystem.map((x) => x.calls));
                  const pct = max > 0 ? (e.calls / max) * 100 : 0;
                  return (
                    <div key={i}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="font-medium">{e.ecosystem}</span>
                        <span className="text-[var(--text-dim)]">{e.calls}</span>
                      </div>
                      <div className="w-full bg-[var(--bg)] rounded-full h-2">
                        <div className="h-2 rounded-full bg-[var(--accent)]" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        <div className="grid md:grid-cols-2 gap-6 mb-8">
          {/* Top Packages */}
          {dashboard?.top_packages && (
            <div className="card p-6">
              <h2 className="font-semibold mb-4">Top Packages (7 days)</h2>
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {dashboard.top_packages.map((p, i) => (
                  <div key={i} className="flex items-center justify-between p-2 rounded bg-[var(--bg)]">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-[var(--accent)] w-10">{p.ecosystem}</span>
                      <span className="text-sm">{p.package_name}</span>
                    </div>
                    <span className="text-xs text-[var(--text-dim)]">{p.searches}x</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Agents (User-Agent) */}
          {dashboard?.top_agents && (
            <div className="card p-6">
              <h2 className="font-semibold mb-4">AI Agents Using Us</h2>
              <div className="space-y-2">
                {dashboard.top_agents.map((a, i) => {
                  const max = Math.max(...dashboard.top_agents.map((x) => x.calls));
                  const pct = max > 0 ? (a.calls / max) * 100 : 0;
                  const colors: Record<string, string> = {
                    Claude: "bg-orange-500", ChatGPT: "bg-green-500", Cursor: "bg-blue-500",
                    Windsurf: "bg-purple-500", "MCP Server": "bg-cyan-500", curl: "bg-gray-500",
                    Python: "bg-yellow-500", "Node.js": "bg-lime-500",
                  };
                  return (
                    <div key={i}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="font-medium">{a.agent}</span>
                        <span className="text-[var(--text-dim)]">{a.calls}</span>
                      </div>
                      <div className="w-full bg-[var(--bg)] rounded-full h-2">
                        <div className={`h-2 rounded-full ${colors[a.agent] || "bg-[var(--accent)]"}`} style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Sources */}
        {sources && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div className="card p-6">
              <h2 className="font-semibold mb-4">API Sources</h2>
              {Object.keys(sources.total || {}).length === 0 ? (
                <p className="text-[var(--text-dim)] text-sm">Nessuna chiamata tracciata con source</p>
              ) : (
                <div className="space-y-2">
                  {Object.entries(sources.total || {}).sort((a: any, b: any) => b[1] - a[1]).map(([src, count]: [string, any]) => (
                    <div key={src} className="flex justify-between items-center">
                      <span className="text-sm">{{ rapidapi: '⚡', gpt: '🤖', gpt_bot: '🕷️', claude: '🧠', claude_bot: '🕷️', cursor: '💻', mcp: '🔌', sdk: '📦', browser: '🌐', internal: '⚙️', unknown: '❓' }[src] || '📡'} {src}</span>
                      <div className="flex gap-4 items-center">
                        <span className="text-xs text-[var(--text-dim)]">oggi: {(sources.today || {})[src] || 0}</span>
                        <span className="text-sm font-mono text-[var(--accent)]">{count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="card p-6">
              <h2 className="font-semibold mb-4">Ecosystems ({stats?.ecosystems?.length || 0})</h2>
              <div className="space-y-2">
                {Object.entries(stats?.ecosystem_counts || {}).sort((a: any, b: any) => b[1] - a[1]).map(([eco, count]: [string, any]) => (
                  <div key={eco} className="flex justify-between items-center">
                    <span className="text-sm">{{ npm: '📦', pypi: '🐍', cargo: '🦀', go: '🐹', composer: '🎼', maven: '☕', nuget: '💎', rubygems: '💎' }[eco] || '📦'} {eco}</span>
                    <span className="text-sm font-mono text-[var(--accent)]">{count.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Users Table */}
        {dashboard?.users && (
          <div className="card p-6 mb-8">
            <h2 className="font-semibold mb-4">Users ({dashboard.users.length})</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-[var(--text-dim)]">
                    <th className="pb-2">ID</th>
                    <th className="pb-2">Email</th>
                    <th className="pb-2">Role</th>
                    <th className="pb-2">Plan</th>
                    <th className="pb-2">API Key</th>
                    <th className="pb-2">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.users.map((u) => (
                    <tr key={u.id} className="border-b border-[var(--border)]/30">
                      <td className="py-2">{u.id}</td>
                      <td className="py-2">{u.email}</td>
                      <td className="py-2">
                        <span className={`px-2 py-0.5 rounded text-xs ${u.role === "admin" ? "bg-red-500/20 text-red-400" : "bg-gray-500/20 text-gray-400"}`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="py-2">{u.plan}</td>
                      <td className="py-2 font-mono text-xs text-[var(--text-dim)]">
                        {u.api_key ? u.api_key.substring(0, 15) + "..." : "-"}
                      </td>
                      <td className="py-2 text-[var(--text-dim)]">{new Date(u.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Trending Live */}
        {stats?.trending && stats.trending.length > 0 && (
          <div className="card p-6">
            <h2 className="font-semibold mb-4">Trending Now</h2>
            <div className="flex flex-wrap gap-2">
              {stats.trending.map((t, i) => (
                <a
                  key={i}
                  href={`/pkg/${t.ecosystem}/${t.package}`}
                  className="px-3 py-1.5 rounded-full bg-[var(--bg)] border border-[var(--border)] text-sm hover:border-[var(--accent)] transition"
                >
                  <span className="text-[var(--accent)]">{t.ecosystem}/</span>
                  {t.package} <span className="text-[var(--text-dim)]">({t.searches})</span>
                </a>
              ))}
            </div>
          </div>
        )}

        <p className="text-center text-xs text-[var(--text-dim)] mt-8">Auto-refreshes every 30 seconds</p>
      </div>
    </div>
  );
}
