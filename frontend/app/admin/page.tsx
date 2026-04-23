"use client";
import { AdminShell, Card, Stat, Grid, Table, Pill } from "./AdminShell";
import { useAdminMany, asArray } from "./admin_hooks";
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { LiveFeed } from "./LiveFeed";

export default function AdminOverviewPage() {
  const s = useAdminMany<{
    dash: any; ts: any; stats: any; pm: any; auto: any; intel: any;
  }>({
    dash:  "/api/admin/dashboard",
    ts:    "/api/admin/timeseries?range=30d&view=all",
    stats: "/api/stats",
    pm:    "/api/admin/plan-metrics",
    auto:  "/api/admin/automation",
    intel: "/api/admin/intelligence",
  });

  if (s.loading) return <AdminShell title="Overview"><Card>Loading…</Card></AdminShell>;

  const pm = s.data.pm || {};
  const stats = s.data.stats || {};
  const auto = s.data.auto || {};
  const intel = s.data.intel || {};
  const ts    = s.data.ts    || {};
  const daily = asArray(ts.daily_kpis);

  const totals7d = intel.totals_7d || {};
  const calls7d = totals7d.calls_7d ?? pm?.usage?.api_calls_7d ?? 0;
  const calls30d = pm?.usage?.api_calls_30d ?? 0;

  const pm2 = asArray(auto.pm2);
  const pm2Online = pm2.filter((p: any) => p.status === "online").length;

  const agents = asArray(intel.agents_7d);
  const countries = asArray(intel.countries_7d);
  const topSearch = asArray(intel.top_searches_24h);
  const verticals = pm.verticals || {};

  return (
    <AdminShell title="Overview"
      subtitle={`DepScope · 7d ${num(calls7d)} calls · ${pm2Online}/${pm2.length} services online`}
      actions={<button onClick={() => location.reload()}
                 className="text-xs px-3 py-1 rounded"
                 style={{ background: "var(--bg-hover)", color: "var(--text-dim)" }}>⟳</button>}>

      <Card>
        <div className="p-5 text-xs leading-relaxed" style={{ color: "var(--text-dim)" }}>
          <div className="font-semibold mb-2 text-sm" style={{ color: "var(--text)" }}>About DepScope</div>
          <p className="mb-2">
            <strong style={{ color: "var(--text)" }}>Sistema.</strong>{" "}
            API + MCP gratuita che dice agli agent AI se un pacchetto è sicuro
            prima di <code>npm install</code>/<code>pip install</code>. 17 ecosistemi,
            392k package, 7.3k CVE arricchite con KEV+EPSS, 22 MCP tools.
          </p>
          <p className="mb-2">
            <strong style={{ color: "var(--text)" }}>Obiettivo.</strong>{" "}
            Diventare il default anti-hallucination per ogni coding agent (Claude,
            Cursor, Copilot, Windsurf) e monetizzare l&apos;intelligence derivata dalle
            query (top pacchetti allucinati, uso per-agent, trust maintainer).
          </p>
          <p className="mb-2">
            <strong style={{ color: "var(--text)" }}>Potenzialità.</strong>{" "}
            ClaudeBot+GPTBot già crawlano aggressivamente (22k/week). Ogni query
            agent alimenta un dataset unico che nessun competitor ha. Acqui-hire offer
            da Socket.dev declinata — moat data confermato.
          </p>
          <p className="mb-2">
            <strong style={{ color: "var(--green)" }}>Forza.</strong>{" "}
            Zero-auth/free per agent (flywheel), 17 ecosistemi (long-tail che
            Socket/Snyk ignorano), FAQPage citation-ready per LLM, GDPR-hashed
            telemetry, trust score 0-100 per maintainer (differenziante).
          </p>
          <p>
            <strong style={{ color: "var(--red)" }}>Debolezza.</strong>{" "}
            No capitale/team (single operator), copertura mainstream ancora parziale
            (npm 45k/3M), brand collision su Devpost, dipendenza da GitHub/Cloudflare,
            DB PostgreSQL SQL_ASCII legacy (Unicode sanitizer come workaround).
          </p>
        </div>
      </Card>

      <div className="mt-4" />

      <Grid cols={4}>
        <Card><Stat label="Packages"       value={num(verticals.packages ?? stats.packages_indexed)}
                    sub={`${stats.ecosystems?.length ?? "—"} ecosystems`} /></Card>
        <Card><Stat label="Vulnerabilities" value={num(verticals.vulnerabilities ?? stats.vulnerabilities_tracked)}
                    sub="99% EPSS-enriched" /></Card>
        <Card><Stat label="API calls 7d"    value={num(calls7d)}
                    sub={`${num(calls30d)} last 30d`} /></Card>
        <Card><Stat label="MCP tools"       value={stats.mcp_tools ?? "—"} sub="v0.6.x" /></Card>
      </Grid>

      <div className="mt-6">
        <LiveFeed max={100} />
      </div>

      <div className="grid grid-cols-2 gap-4 mt-6">
        <Card title="API calls per day (30d)">
          {daily.length === 0 ? <Empty /> : (
            <div style={{ width: "100%", height: 220 }}>
              <ResponsiveContainer>
                <LineChart data={daily}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="day" stroke="var(--text-dim)" fontSize={10} />
                  <YAxis stroke="var(--text-dim)" fontSize={10} />
                  <Tooltip contentStyle={{ background: "var(--bg-card)", border: "1px solid var(--border)", fontSize: 12 }} />
                  <Line type="monotone" dataKey="calls" stroke="#3b82f6" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="unique_ips" stroke="#10b981" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card title="Agent clients (7d)">
          {agents.length === 0 ? <Empty /> : (
            <div style={{ width: "100%", height: 220 }}>
              <ResponsiveContainer>
                <BarChart data={agents.slice(0, 8)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="source" stroke="var(--text-dim)" fontSize={10} />
                  <YAxis stroke="var(--text-dim)" fontSize={10} />
                  <Tooltip contentStyle={{ background: "var(--bg-card)", border: "1px solid var(--border)", fontSize: 12 }} />
                  <Bar dataKey="calls" fill="#6366f1" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-2 gap-4 mt-6">
        <Card title="System health"
              action={<a href="/admin/infrastructure" className="text-xs hover:text-[var(--accent)]"
                         style={{ color: "var(--text-faded)" }}>→ details</a>}>
          {pm2.length === 0 ? <Empty /> :
            <Table
              headers={["process", "status", "cpu", "mem"]}
              rows={pm2.map((p: any) => [
                p.name,
                <Pill key={p.name} color={p.status === "online" ? "green" : "red"}>{p.status}</Pill>,
                p.cpu != null ? `${p.cpu}%` : "—",
                p.memory_mb != null ? `${Math.round(p.memory_mb)}MB` : "—",
              ])}
            />
          }
        </Card>

        <Card title="Traffic sources (7d)"
              action={<a href="/admin/traffic" className="text-xs hover:text-[var(--accent)]"
                         style={{ color: "var(--text-faded)" }}>→ details</a>}>
          {agents.length === 0 ? <Empty /> :
            <Table
              headers={["source", "calls", "uniq IPs"]}
              rows={agents.slice(0, 8).map((a: any) => [
                a.source || "—",
                num(a.calls),
                a.unique_ips ?? "—",
              ])}
            />
          }
        </Card>
      </div>

      <div className="grid grid-cols-3 gap-4 mt-6">
        <Card title="Top packages (24h)"
              action={<a href="/admin/traffic" className="text-xs hover:text-[var(--accent)]"
                         style={{ color: "var(--text-faded)" }}>→</a>}>
          {topSearch.length === 0 ? <Empty /> :
            <Table
              headers={["eco", "pkg", "hits"]}
              rows={topSearch.slice(0, 10).map((r: any) => [
                <Pill key={r.package_name} color="blue">{r.ecosystem}</Pill>,
                (r.package_name || "—").toString().slice(0, 28),
                num(r.calls ?? 0),
              ])}
            />
          }
        </Card>

        <Card title="Top countries (7d)">
          {countries.length === 0 ? <Empty /> :
            <Table
              headers={["country", "calls"]}
              rows={countries.slice(0, 10).map((c: any) => [
                c.country || "—",
                num(c.calls ?? 0),
              ])}
            />
          }
        </Card>

        <Card title="Quick nav">
          <div className="text-xs space-y-1">
            <Nav href="/admin/traffic"        label="Traffic"       />
            <Nav href="/admin/database"       label="Database"      />
            <Nav href="/admin/infrastructure" label="Infrastructure"/>
            <Nav href="/admin/marketing"      label="Marketing"     />
            <Nav href="/admin/agents"         label="Agents"        />
            <Nav href="/admin/launch"         label="Launch"        />
            <Nav href="/admin/settings"       label="Settings"      />
          </div>
        </Card>
      </div>
    </AdminShell>
  );
}

function num(n: any) { return (Number(n) || 0).toLocaleString(); }
function Empty() {
  return <div className="text-xs" style={{ color: "var(--text-faded)" }}>No data.</div>;
}
function Nav({ href, label }: { href: string; label: string }) {
  return (
    <a href={href} className="flex items-center justify-between px-2 py-1 rounded hover:bg-[var(--bg-hover)]"
       style={{ color: "var(--text-dim)" }}>
      <span>{label}</span><span style={{ color: "var(--text-faded)" }}>→</span>
    </a>
  );
}
