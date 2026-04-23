"use client";
import { AdminShell, Card, Stat, Grid, Table, Pill } from "../AdminShell";
import { useAdminMany, asArray } from "../admin_hooks";
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";

export default function TrafficPage() {
  const s = useAdminMany<{ src: any; ts: any; intel: any }>({
    src:   "/api/admin/sources",
    ts:    "/api/admin/timeseries",
    intel: "/api/admin/intelligence",
  });

  if (s.loading) return <AdminShell title="Traffic"><Card>Loading…</Card></AdminShell>;

  const src = s.data.src || {};
  const ts = s.data.ts || {};
  const intel = s.data.intel || {};

  const daily = asArray(ts.daily_kpis);
  const last7 = daily.reduce((a, d) => a + (d.calls || 0), 0);
  const last1 = daily.length > 0 ? daily[0].calls : 0;  // most recent day
  const last24 = last1; // approx for last "day" of the series
  // Cache hit % (weighted by calls)
  const totalCalls = daily.reduce((a, d) => a + (d.calls || 0), 0);
  const weightedCache = daily.reduce((a, d) => a + (d.cache_hit_rate || 0) * (d.calls || 0), 0);
  const cacheHitPct = totalCalls > 0 ? Math.round((weightedCache / totalCalls) * 100) : null;

  // Heatmap → peak hour
  const heatmap = asArray(ts.heatmap);
  const peak = heatmap.reduce((m: any, h: any) => (h.n > (m?.n || 0) ? h : m), null);
  const peakLabel = peak ? `${peak.hour}:00 (dow=${peak.dow})` : "—";

  // UAs from intelligence.agents_7d (proper count)
  const agents = asArray(intel.agents_7d);
  const totalAgents = agents.reduce((a: number, x: any) => a + (x.calls || 0), 0);
  const uaRows = agents.map((a: any) => ({
    source: a.source,
    calls: a.calls,
    share: totalAgents > 0 ? Math.round((a.calls / totalAgents) * 100) : 0,
    uniq: a.unique_ips,
  }));

  // Endpoints from timeseries.by_endpoint
  const byEndpoint = asArray(ts.by_endpoint);

  // Top packages from intelligence.top_searches_24h
  const topPkgs = asArray(intel.top_searches_24h);

  // Countries from intelligence.countries_7d
  const countries = asArray(intel.countries_7d);

  return (
    <AdminShell title="Traffic"
      subtitle="API usage, crawler breakdown, cache efficiency"
      actions={<button onClick={() => location.reload()}
                 className="text-xs px-3 py-1 rounded"
                 style={{ background: "var(--bg-hover)", color: "var(--text-dim)" }}>⟳ refresh</button>}>

      <Grid cols={4}>
        <Card><Stat label="Last day"   value={num(last24)} /></Card>
        <Card><Stat label="Last 7d"    value={num(last7)} /></Card>
        <Card><Stat label="Cache hit"  value={cacheHitPct != null ? `${cacheHitPct}%` : "—"}
                    sub="weighted by calls" /></Card>
        <Card><Stat label="Peak slot"  value={peakLabel}
                    sub={peak ? `${num(peak.n)} calls/slot` : undefined} /></Card>
      </Grid>

      <div className="grid grid-cols-2 gap-4 mt-6">
        <Card title="Calls per day (7d)">
          {daily.length === 0 ? <Empty /> : (
            <div style={{ width: "100%", height: 220 }}>
              <ResponsiveContainer>
                <LineChart data={daily}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="day" stroke="var(--text-dim)" fontSize={10} />
                  <YAxis stroke="var(--text-dim)" fontSize={10} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--bg-card)",
                      border: "1px solid var(--border)",
                      fontSize: 12,
                    }}
                  />
                  <Line type="monotone" dataKey="calls" stroke="#3b82f6" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="unique_ips" stroke="#10b981" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card title="Top agent clients (7d)">
          {uaRows.length === 0 ? <Empty /> : (
            <div style={{ width: "100%", height: 220 }}>
              <ResponsiveContainer>
                <BarChart data={uaRows.slice(0, 8)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="source" stroke="var(--text-dim)" fontSize={10} />
                  <YAxis stroke="var(--text-dim)" fontSize={10} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--bg-card)",
                      border: "1px solid var(--border)",
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="calls" fill="#6366f1" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-2 gap-4 mt-6">
        <Card title="Traffic sources (7d)">
          {uaRows.length === 0 ? <Empty /> :
            <Table
              headers={["source", "calls", "%", "uniq IPs"]}
              rows={uaRows.slice(0, 12).map((r: any) => [
                r.source || "—",
                num(r.calls),
                `${r.share}%`,
                r.uniq ?? "—",
              ])}
            />
          }
        </Card>

        <Card title="Top endpoints (7d)">
          {byEndpoint.length === 0 ? <Empty /> :
            <Table
              headers={["endpoint", "calls"]}
              rows={byEndpoint.slice(0, 15).map((r: any) => [
                r.endpoint || "—",
                num(r.calls ?? 0),
              ])}
            />
          }
        </Card>
      </div>

      <div className="grid grid-cols-2 gap-4 mt-6">
        <Card title="Top packages (24h)">
          {topPkgs.length === 0 ? <Empty /> :
            <Table
              headers={["eco", "package", "calls"]}
              rows={topPkgs.slice(0, 15).map((r: any) => [
                <Pill key={r.ecosystem} color="blue">{r.ecosystem || "—"}</Pill>,
                r.package_name || "—",
                num(r.calls ?? 0),
              ])}
            />
          }
        </Card>

        <Card title="Top countries (7d)">
          {countries.length === 0 ? <Empty /> :
            <Table
              headers={["country", "calls", "uniq"]}
              rows={countries.slice(0, 12).map((r: any) => [
                r.country || "—",
                num(r.calls ?? 0),
                r.unique_ips ?? "—",
              ])}
            />
          }
        </Card>
      </div>

      {/* Daily KPIs timeline */}
      {daily.length > 0 && (
        <div className="mt-6">
          <Card title="Daily KPIs (last 7d)">
            <Table
              headers={["day", "calls", "cache %", "err %", "uniq IPs", "avg ms", "p95 ms"]}
              rows={daily.map((d: any) => [
                d.day,
                num(d.calls),
                d.cache_hit_rate != null ? `${Math.round(d.cache_hit_rate * 100)}%` : "—",
                d.error_rate != null ? `${Math.round(d.error_rate * 100)}%` : "—",
                d.unique_ips ?? "—",
                d.avg_ms ?? "—",
                d.p95_ms ?? "—",
              ])}
            />
          </Card>
        </div>
      )}
    </AdminShell>
  );
}

function num(n: any) { return (Number(n) || 0).toLocaleString(); }
function Empty() {
  return <div className="text-xs" style={{ color: "var(--text-faded)" }}>No data.</div>;
}
