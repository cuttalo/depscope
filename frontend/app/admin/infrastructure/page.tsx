"use client";
import { AdminShell, Card, Stat, Grid, Table, Pill } from "../AdminShell";
import { useAdminMany, asArray } from "../admin_hooks";

export default function InfrastructurePage() {
  const s = useAdminMany<{ auto: any; seo: any }>({
    auto: "/api/admin/automation",
    seo:  "/api/admin/seo-health",
  });

  if (s.loading) return <AdminShell title="Infrastructure"><Card>Loading…</Card></AdminShell>;

  const data = s.data.auto || {};
  const seo = s.data.seo || {};

  const pm2 = asArray(data.pm2);
  const jobs = asArray(data.jobs);
  const disk = data.disk || {};
  const db = data.db || {};

  const pm2Online = pm2.filter((p: any) => p.status === "online").length;

  return (
    <AdminShell title="Infrastructure"
      subtitle="PM2 processes, cron schedule, disk, DB size, SEO health">

      <Grid cols={4}>
        <Card><Stat label="PM2 online"  value={pm2.length ? `${pm2Online}/${pm2.length}` : "—"} /></Card>
        <Card><Stat label="Cron jobs"   value={jobs.length || "—"} /></Card>
        <Card><Stat label="Disk used"   value={disk.pct != null ? `${disk.pct}%` : "—"}
                    sub={disk.used && disk.total ? `${disk.used} / ${disk.total}` : undefined} /></Card>
        <Card><Stat label="DB size"     value={db.size || "—"}
                    sub={db.packages ? `${num(db.packages)} pkg, ${num(db.vulnerabilities)} vulns` : undefined} /></Card>
      </Grid>

      <div className="grid grid-cols-2 gap-4 mt-6">
        <Card title="PM2 processes">
          {pm2.length === 0 ? <Empty /> :
            <Table
              headers={["name", "status", "uptime", "↺", "cpu", "mem"]}
              rows={pm2.map((p: any) => [
                p.name,
                <Pill key={p.name} color={p.status === "online" ? "green" : "red"}>{p.status}</Pill>,
                p.uptime_ms ? `${Math.round(p.uptime_ms / 60000)}m` : "—",
                p.restarts ?? "—",
                p.cpu != null ? `${p.cpu}%` : "—",
                p.memory_mb != null ? `${Math.round(p.memory_mb)}MB` : "—",
              ])}
            />
          }
        </Card>

        <Card title="Cron jobs">
          {jobs.length === 0 ? <Empty /> :
            <Table
              headers={["schedule", "script", "last", "status"]}
              rows={jobs.map((c: any) => [
                <code key={c.name + "s"} className="text-xs">{c.schedule}</code>,
                c.name || c.script,
                c.last_run ? new Date(c.last_run).toISOString().slice(0, 16).replace("T", " ") : "—",
                <Pill key={c.name}
                      color={c.status === "ok" ? "green"
                            : c.status === "failed" ? "red"
                            : c.status === "unknown" ? "default" : "orange"}>
                  {c.status || "—"}
                </Pill>,
              ])}
            />
          }
        </Card>
      </div>

      <div className="grid grid-cols-2 gap-4 mt-6">
        <Card title="Disk">
          <Table
            headers={["metric", "value"]}
            rows={[
              ["total", disk.total || "—"],
              ["used",  disk.used  || "—"],
              ["free",  disk.free  || "—"],
              ["pct",   disk.pct != null ? `${disk.pct}%` : "—"],
            ]}
          />
        </Card>

        <Card title="SEO health">
          {Object.keys(seo).length === 0 ? <Empty /> : (() => {
            const rows: any[] = [];
            const overall: any = (seo as any).overall;
            if (overall && typeof overall === "object") {
              const pct = overall.ratio != null ? Math.round(overall.ratio * 100) : null;
              const label = pct != null
                ? (pct + "% (" + overall.indexable + "/" + overall.total + ")")
                : "—";
              rows.push([
                "overall",
                <Pill key="overall" color={overall.warn ? "red" : "green"}>{label}</Pill>,
              ]);
            }
            const routes: any = (seo as any).routes || {};
            for (const k of Object.keys(routes)) {
              const rr: any = routes[k];
              const pct = rr?.ratio != null ? Math.round(rr.ratio * 100) : null;
              const label = pct != null
                ? (pct + "% (" + rr.indexable + "/" + rr.total + ")")
                : "—";
              rows.push([
                "routes." + k,
                <Pill key={"r-" + k} color={rr?.warn ? "red" : "green"}>{label}</Pill>,
              ]);
            }
            const thresholds: any = (seo as any).thresholds || {};
            for (const k of Object.keys(thresholds)) {
              rows.push(["thr." + k, String(thresholds[k])]);
            }
            return <Table headers={["check", "status"]} rows={rows} />;
          })()}
        </Card>
      </div>
    </AdminShell>
  );
}

function num(n: any) { return (Number(n) || 0).toLocaleString(); }
function Empty() {
  return <div className="text-xs" style={{ color: "var(--text-faded)" }}>No data.</div>;
}
