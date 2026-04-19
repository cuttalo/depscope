import { Card, CardBody, CardHeader, CardTitle, PageHeader, Section, Footer, Badge } from "../../components/ui";
import { CopyButton } from "../../components/CopyButton";

interface Endpoint {
  method: "GET" | "POST";
  path: string;
  desc: string;
  example: string;
  params?: { name: string; type: string; desc: string }[];
}

const ENDPOINTS: Endpoint[] = [
  { method: "GET", path: "/api/check/{ecosystem}/{package}", desc: "Full package intelligence: health score, vulnerabilities, versions, recommendation.", example: "curl https://depscope.dev/api/check/npm/express", params: [{ name: "ecosystem", type: "string", desc: "17 supported ecosystems (see /api/stats)" }, { name: "package", type: "string", desc: "Package name (supports scoped: @org/pkg)" }, { name: "version", type: "query", desc: "Optional: specific version to check" }] },
  { method: "GET", path: "/api/latest/{ecosystem}/{package}", desc: "Get latest version only. Ultra-fast, cached response.", example: "curl https://depscope.dev/api/latest/npm/express" },
  { method: "GET", path: "/api/exists/{ecosystem}/{package}", desc: "Check if a package exists in the registry.", example: "curl https://depscope.dev/api/exists/pypi/django" },
  { method: "GET", path: "/api/health/{ecosystem}/{package}", desc: "Quick health score only (0-100).", example: "curl https://depscope.dev/api/health/pypi/fastapi" },
  { method: "GET", path: "/api/vulns/{ecosystem}/{package}", desc: "Known vulnerabilities from OSV database.", example: "curl https://depscope.dev/api/vulns/npm/lodash" },
  { method: "GET", path: "/api/versions/{ecosystem}/{package}", desc: "Version history and latest version info.", example: "curl https://depscope.dev/api/versions/cargo/serde" },
  { method: "GET", path: "/api/tree/{ecosystem}/{package}", desc: "Full transitive dependency tree.", example: "curl https://depscope.dev/api/tree/npm/express" },
  { method: "GET", path: "/api/licenses/{ecosystem}/{package}", desc: "License audit across all transitive dependencies.", example: "curl https://depscope.dev/api/licenses/npm/express" },
  { method: "GET", path: "/api/history/{ecosystem}/{package}", desc: "Health and vulnerability history for a package.", example: "curl https://depscope.dev/api/history/npm/express" },
  { method: "GET", path: "/api/prompt/{ecosystem}/{package}", desc: "LLM-optimized text prompt summarizing a package.", example: "curl https://depscope.dev/api/prompt/npm/express" },
  { method: "GET", path: "/api/search/{ecosystem}", desc: "Search packages by keyword within an ecosystem.", example: "curl https://depscope.dev/api/search/npm?q=http", params: [{ name: "q", type: "query", desc: "Search keyword" }] },
  { method: "GET", path: "/api/alternatives/{ecosystem}/{package}", desc: "Recommended alternatives (especially useful for deprecated).", example: "curl https://depscope.dev/api/alternatives/npm/request" },
  { method: "GET", path: "/api/compare/{ecosystem}/{pkg1},{pkg2},{pkg3}", desc: "Compare multiple packages side by side (2-10).", example: "curl https://depscope.dev/api/compare/npm/express,fastify,hono" },
  { method: "GET", path: "/api/trending", desc: "Trending packages across ecosystems, live rank and weekly growth.", example: "curl https://depscope.dev/api/trending?limit=20" },
  { method: "GET", path: "/api/error", desc: "Match an error message against the fix database.", example: "curl 'https://depscope.dev/api/error?q=Cannot+find+module'" },
  { method: "POST", path: "/api/error/resolve", desc: "Resolve a full stack trace (POST body).", example: "curl -X POST https://depscope.dev/api/error/resolve -H 'content-type: application/json' -d '{\"error\":\"...\"}'" },
  { method: "GET", path: "/api/compat", desc: "Check stack compatibility (e.g. next@16,react@19).", example: "curl 'https://depscope.dev/api/compat?stack=next@16,react@19'" },
  { method: "GET", path: "/api/bugs/{ecosystem}/{package}", desc: "Known bugs for a package, optionally filtered by version.", example: "curl 'https://depscope.dev/api/bugs/npm/react?version=19.0.0'" },
  { method: "GET", path: "/api/bugs/search", desc: "Full-text search across the bug database.", example: "curl 'https://depscope.dev/api/bugs/search?q=hydration'" },
  { method: "POST", path: "/api/scan", desc: "Audit an entire project's dependencies at once (max 100 packages).", example: 'curl -X POST https://depscope.dev/api/scan -H "Content-Type: application/json" -d \'{"ecosystem":"npm","packages":{"express":"^4.0"}}\'' },
  { method: "GET", path: "/api/now", desc: "Current UTC date/time. Useful for agents to check server time.", example: "curl https://depscope.dev/api/now" },
  { method: "GET", path: "/api/stats", desc: "Coverage and ecosystem statistics.", example: "curl https://depscope.dev/api/stats" },
];

const BADGE_ENDPOINTS = [
  { path: "/badge/{ecosystem}/{package}", desc: "Health score badge (SVG). Embed in README or docs.", curl: "curl https://depscope.dev/badge/npm/express", md: "![DepScope](https://depscope.dev/badge/npm/express)" },
  { path: "/badge/score/{ecosystem}/{package}", desc: "Score-only badge variant (compact).", curl: "curl https://depscope.dev/badge/score/pypi/django", md: "![Score](https://depscope.dev/badge/score/pypi/django)" },
];

export default function ApiDocsPage() {
  return (
    <div className="min-h-screen">
      <main className="max-w-5xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="API Reference"
          title="API Documentation"
          description="Free, open API. No auth required for public endpoints. 200 req/min per IP. JSON responses."
        />

        <Section>
          <Card>
            <CardBody>
              <dl className="grid grid-cols-[120px_1fr] gap-y-2 text-sm">
                <dt className="text-[var(--text-dim)]">Base URL</dt>
                <dd className="font-mono text-[var(--accent)]">https://depscope.dev</dd>
                <dt className="text-[var(--text-dim)]">Auth</dt>
                <dd>
                  None for public endpoints. Higher limits via <a href="/account/api-keys" className="text-[var(--accent)] hover:underline">API keys</a>.
                </dd>
                <dt className="text-[var(--text-dim)]">Rate limit</dt>
                <dd className="tabular-nums">200 req/min per IP</dd>
                <dt className="text-[var(--text-dim)]">Format</dt>
                <dd>JSON (UTF-8)</dd>
                <dt className="text-[var(--text-dim)]">MCP tools</dt>
                <dd>12 tools available at <a href="/mcp" className="text-[var(--accent)] hover:underline">/mcp</a></dd>
              </dl>
            </CardBody>
          </Card>
        </Section>

        <div className="flex flex-wrap gap-4 my-6 text-xs font-mono">
          <a href="#endpoints" className="text-[var(--accent)] hover:underline">Endpoints</a>
          <a href="#badges" className="text-[var(--accent)] hover:underline">Badges</a>
          <a href="#scoring" className="text-[var(--accent)] hover:underline">Health score</a>
          <a href="#ai-agents" className="text-[var(--accent)] hover:underline">AI agents</a>
        </div>

        <Section title="Endpoints" className="mt-6">
          <div id="endpoints" className="space-y-3">
            {ENDPOINTS.map((ep, i) => (
              <Card key={i}>
                <CardBody>
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <Badge variant={ep.method === "GET" ? "success" : "info"}>{ep.method}</Badge>
                    <code className="text-sm font-mono text-[var(--accent)]">{ep.path}</code>
                    <span className="ml-auto"><CopyButton text={ep.example} /></span>
                  </div>
                  <p className="text-sm text-[var(--text-dim)] mb-3">{ep.desc}</p>
                  {ep.params && ep.params.length > 0 && (
                    <div className="mb-3">
                      <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-faded)] mb-1">Parameters</div>
                      <div className="space-y-1">
                        {ep.params.map((p, j) => (
                          <div key={j} className="flex gap-3 text-xs">
                            <code className="text-[var(--accent)] font-mono w-28 shrink-0">{p.name}</code>
                            <span className="text-[var(--text-faded)] w-16 shrink-0">{p.type}</span>
                            <span className="text-[var(--text-dim)]">{p.desc}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  <pre className="bg-[var(--bg-input)] border border-[var(--border)] rounded px-3 py-2 text-xs text-[var(--text-dim)] font-mono overflow-x-auto">
                    {ep.example}
                  </pre>
                </CardBody>
              </Card>
            ))}
          </div>
        </Section>

        <Section title="Badges" description="Embed health score badges in your README or docs." className="mt-10">
          <div id="badges" className="space-y-3">
            {BADGE_ENDPOINTS.map((ep, i) => (
              <Card key={i}>
                <CardBody>
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <Badge variant="accent">GET</Badge>
                    <code className="text-sm font-mono text-[var(--accent)]">{ep.path}</code>
                  </div>
                  <p className="text-sm text-[var(--text-dim)] mb-3">{ep.desc}</p>
                  <div className="space-y-2">
                    <div>
                      <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-faded)] mb-1">curl</div>
                      <pre className="bg-[var(--bg-input)] border border-[var(--border)] rounded px-3 py-2 text-xs text-[var(--text-dim)] font-mono overflow-x-auto">{ep.curl}</pre>
                    </div>
                    <div>
                      <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-faded)] mb-1">Markdown</div>
                      <pre className="bg-[var(--bg-input)] border border-[var(--border)] rounded px-3 py-2 text-xs text-[var(--text-dim)] font-mono overflow-x-auto">{ep.md}</pre>
                    </div>
                  </div>
                </CardBody>
              </Card>
            ))}
            <Card>
              <CardHeader>
                <CardTitle>Badge colors</CardTitle>
              </CardHeader>
              <CardBody>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
                  {[
                    { range: "80–100", color: "var(--green)", label: "Green" },
                    { range: "60–79", color: "var(--yellow)", label: "Yellow" },
                    { range: "40–59", color: "var(--orange)", label: "Orange" },
                    { range: "0–39", color: "var(--red)", label: "Red" },
                  ].map((b) => (
                    <div key={b.label} className="p-3 rounded border border-[var(--border)] bg-[var(--bg-input)]">
                      <div className="text-lg font-semibold tabular-nums" style={{ color: b.color }}>{b.range}</div>
                      <div className="text-xs text-[var(--text-dim)] mt-0.5">{b.label}</div>
                    </div>
                  ))}
                </div>
              </CardBody>
            </Card>
          </div>
        </Section>

        <Section title="Health score breakdown" description="Algorithmic score (0–100) from multiple signals." className="mt-10">
          <Card>
            <CardBody>
              <div id="scoring" className="grid grid-cols-2 md:grid-cols-5 gap-3 text-center">
                {[
                  { pts: 25, label: "Maintenance", hint: "Last release date" },
                  { pts: 25, label: "Security", hint: "Known CVEs" },
                  { pts: 20, label: "Popularity", hint: "Weekly downloads" },
                  { pts: 15, label: "Maturity", hint: "Version count" },
                  { pts: 15, label: "Community", hint: "Maintainers" },
                ].map((x) => (
                  <div key={x.label} className="p-3 rounded border border-[var(--border)] bg-[var(--bg-input)]">
                    <div className="text-xl font-semibold tabular-nums text-[var(--accent)]">{x.pts}</div>
                    <div className="text-xs text-[var(--text)] mt-1">{x.label}</div>
                    <div className="text-[11px] text-[var(--text-dim)] mt-0.5">{x.hint}</div>
                  </div>
                ))}
              </div>
            </CardBody>
          </Card>
        </Section>

        <Section title="For AI agents" className="mt-10">
          <div id="ai-agents">
            <Card>
              <CardBody>
                <p className="text-sm text-[var(--text-dim)] mb-4 leading-relaxed">
                  DepScope is designed to be called by AI agents before suggesting any package. The API returns structured JSON.
                </p>
                <div className="space-y-2">
                  {[
                    { label: "ChatGPT / OpenAI Actions", url: "https://depscope.dev/.well-known/ai-plugin.json" },
                    { label: "OpenAPI spec", url: "https://depscope.dev/openapi.json" },
                    { label: "Interactive docs (Swagger)", url: "https://depscope.dev/docs" },
                    { label: "MCP server (JSON-RPC)", url: "https://depscope.dev/mcp" },
                  ].map((x) => (
                    <div key={x.url} className="flex items-center justify-between gap-3 flex-wrap bg-[var(--bg-input)] border border-[var(--border)] rounded px-3 py-2">
                      <div>
                        <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-faded)]">{x.label}</div>
                        <code className="text-sm font-mono text-[var(--accent)] break-all">{x.url}</code>
                      </div>
                      <CopyButton text={x.url} />
                    </div>
                  ))}
                </div>
              </CardBody>
            </Card>
          </div>
        </Section>
      </main>
      <Footer />
    </div>
  );
}
