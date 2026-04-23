import type { Metadata } from "next";
import { Footer } from "../../components/ui";

export const metadata: Metadata = {
  title: "Status — DepScope",
  description:
    "DepScope operational status. Uptime, component health, packages indexed, API call volume. Real-time, zero-auth.",
  alternates: { canonical: "https://depscope.dev/status" },
};

interface StatusData {
  ok: boolean;
  status: string;
  version: string;
  uptime_s: number;
  uptime_human: string;
  components: Record<string, string>;
  stats: {
    packages_indexed: number;
    malicious_advisories: number;
    ecosystems_supported: number;
    mcp_tools: number;
    api_calls_last_hour: number | null;
  };
  probe_ms: number;
}

async function fetchStatus(): Promise<StatusData | null> {
  try {
    const r = await fetch("http://127.0.0.1:8000/api/status", {
      next: { revalidate: 30 },
    });
    if (!r.ok) return null;
    return (await r.json()) as StatusData;
  } catch {
    return null;
  }
}

function Pill({ state }: { state: string }) {
  const ok = state === "ok";
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-mono"
      style={{
        background: ok
          ? "color-mix(in srgb, var(--green) 15%, transparent)"
          : "color-mix(in srgb, var(--red) 15%, transparent)",
        color: ok ? "var(--green)" : "var(--red)",
      }}
    >
      <span
        className="inline-block w-1.5 h-1.5 rounded-full"
        style={{ background: ok ? "var(--green)" : "var(--red)" }}
      />
      {ok ? "operational" : state}
    </span>
  );
}

export default async function StatusPage() {
  const s = await fetchStatus();

  if (!s) {
    return (
      <div className="min-h-screen">
        <main className="max-w-4xl mx-auto px-4 py-10">
          <h1 className="text-3xl font-semibold mb-4">Status</h1>
          <div
            className="rounded-lg p-5 text-sm"
            style={{
              background: "color-mix(in srgb, var(--red) 8%, transparent)",
              border: "1px solid var(--red)",
              color: "var(--red)",
            }}
          >
            <strong>Probe failed.</strong> The status endpoint didn't respond.
            This likely means the API is down — but this page is served from the
            frontend, so we're at least partially up.
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  const overall = s.ok;

  return (
    <div className="min-h-screen">
      <main className="max-w-4xl mx-auto px-4 py-10">
        {/* Header */}
        <header className="mb-8 flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight mb-2">System Status</h1>
            <div className="flex items-center gap-3 flex-wrap">
              <Pill state={overall ? "ok" : "degraded"} />
              <span className="text-sm text-[var(--text-dim)]">
                uptime <span className="font-mono text-[var(--text)]">{s.uptime_human}</span>
              </span>
              <span className="text-xs font-mono text-[var(--text-faded)]">
                v{s.version} · probe {s.probe_ms}ms
              </span>
            </div>
          </div>
          <a
            href="/api/status"
            className="text-xs font-mono text-[var(--accent)] hover:underline"
          >
            GET /api/status →
          </a>
        </header>

        {/* Components */}
        <section className="mb-8">
          <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-dim)] mb-3">
            Components
          </div>
          <div
            className="rounded-lg divide-y"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderColor: "var(--border)" }}
          >
            {Object.entries(s.components)
              .filter(([k]) => !k.endsWith("_error"))
              .map(([k, v]) => (
                <div
                  key={k}
                  className="px-5 py-3 flex items-center justify-between"
                  style={{ borderColor: "var(--border)" }}
                >
                  <span className="text-sm">
                    <span className="font-mono font-semibold capitalize">{k}</span>
                    <span className="ml-2 text-[var(--text-faded)] text-xs">
                      {k === "db" ? "PostgreSQL 17"
                        : k === "redis" ? "cache + pub/sub"
                        : k === "api" ? "FastAPI / uvicorn"
                        : ""}
                    </span>
                  </span>
                  <Pill state={v} />
                </div>
              ))}
          </div>
        </section>

        {/* Stats */}
        <section className="mb-8">
          <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-dim)] mb-3">
            Scale
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div
              className="rounded-lg p-4 text-center"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              <div className="text-2xl font-semibold tabular-nums text-[var(--text)]">
                {s.stats.packages_indexed.toLocaleString()}
              </div>
              <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-dim)] mt-1">
                Packages indexed
              </div>
            </div>
            <div
              className="rounded-lg p-4 text-center"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              <div className="text-2xl font-semibold tabular-nums text-[var(--red)]">
                {s.stats.malicious_advisories.toLocaleString()}
              </div>
              <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-dim)] mt-1">
                Malicious advisories
              </div>
            </div>
            <div
              className="rounded-lg p-4 text-center"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              <div className="text-2xl font-semibold tabular-nums text-[var(--green)]">
                {s.stats.ecosystems_supported}
              </div>
              <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-dim)] mt-1">
                Ecosystems
              </div>
            </div>
            <div
              className="rounded-lg p-4 text-center"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              <div className="text-2xl font-semibold tabular-nums text-[var(--accent)]">
                {s.stats.mcp_tools}
              </div>
              <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-dim)] mt-1">
                MCP tools
              </div>
            </div>
          </div>
        </section>

        {/* Recent activity */}
        {typeof s.stats.api_calls_last_hour === "number" && s.stats.api_calls_last_hour > 0 && (
          <section className="mb-8">
            <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-dim)] mb-3">
              Activity
            </div>
            <div
              className="rounded-lg p-5 flex items-center justify-between"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              <span className="text-sm">API calls — last hour</span>
              <span className="font-mono text-lg tabular-nums text-[var(--accent)]">
                {s.stats.api_calls_last_hour.toLocaleString()}
              </span>
            </div>
          </section>
        )}

        {/* Integrations */}
        <section className="mb-8">
          <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-dim)] mb-3">
            Ways to monitor
          </div>
          <div
            className="rounded-lg p-5 text-sm text-[var(--text-dim)] leading-relaxed"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
          >
            <p className="mb-3">
              The <code className="font-mono text-xs text-[var(--accent)]">/api/status</code>{" "}
              endpoint returns machine-readable JSON. Point any uptime monitor at it —
              it returns HTTP 200 + <code className="font-mono text-xs">{"{\"ok\":true}"}</code>{" "}
              when everything is green.
            </p>
            <pre className="bg-[var(--bg-input)] border border-[var(--border)] rounded p-3 text-xs font-mono overflow-x-auto">
{`# curl
curl https://depscope.dev/api/status

# Pingdom / Checkly / UptimeRobot
URL: https://depscope.dev/api/status
Expect: JSON body contains "ok": true

# Grafana / Datadog HTTP check
Same URL, assert response.ok === true`}
            </pre>
          </div>
        </section>

        {/* Footer note */}
        <section>
          <div
            className="rounded-lg p-5 text-xs text-[var(--text-faded)]"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
          >
            This page is rebuilt every 30 seconds from the live API. For incident
            history and long-term availability, see the{" "}
            <a href="https://github.com/cuttalo/depscope" className="text-[var(--accent)] hover:underline">
              GitHub repo
            </a>
            . Report an incident:{" "}
            <a href="/contact" className="text-[var(--accent)] hover:underline">
              /contact
            </a>
            .
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
