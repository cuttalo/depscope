import { Card, CardBody, CardHeader, CardTitle, PageHeader, Section, Footer, Badge } from "../../components/ui";
import { CopyButton } from "../../components/CopyButton";

interface Endpoint {
  method: "GET" | "POST";
  path: string;
  desc: string;
  example: string;
  params?: { name: string; type: string; desc: string }[];
  returns?: string[];
}

// Grouped for readability — agents also read this top-to-bottom.
const CORE_ENDPOINTS: Endpoint[] = [
  {
    method: "GET",
    path: "/api/check/{ecosystem}/{package}",
    desc: "Full package intelligence. THE most-used endpoint. Returns health + vulns + versions + license_risk + historical_compromise + recommendation.",
    example: "curl https://depscope.dev/api/check/npm/axios",
    params: [
      { name: "ecosystem", type: "path", desc: "One of 17 supported (npm, pypi, cargo, go, maven, ...)" },
      { name: "package", type: "path", desc: "Package name (scoped OK: @anthropic-ai/sdk)" },
      { name: "version", type: "query", desc: "Optional pinned version. Returns version_scoped block with CVE filter for THAT version." },
    ],
    returns: [
      "recommendation.action (safe_to_use | update_required | use_with_caution | find_alternative | do_not_use | legacy_but_working | insufficient_data)",
      "license_risk (permissive | weak_copyleft | strong_copyleft | network_copyleft | proprietary | unknown)",
      "commercial_use_notes — one-line commercial-use guidance",
      "historical_compromise — KB matches (event-stream@3.3.6, ua-parser-js 0.7.29, etc.)",
      "version_scoped (when ?version= passed): vulns + recommendation scoped to that version",
      "downloads_weekly (null when registry does not expose)",
    ],
  },
  {
    method: "GET",
    path: "/api/prompt/{ecosystem}/{package}",
    desc: "LLM-optimized plain-text brief (~500 tokens). Drop-in for system prompts. Token-saving vs raw JSON.",
    example: "curl https://depscope.dev/api/prompt/npm/axios?version=0.21.1",
    params: [
      { name: "version", type: "query", desc: "Optional pinned version. The brief renders THAT version's view." },
    ],
  },
  {
    method: "GET",
    path: "/api/health/{ecosystem}/{package}",
    desc: "Just the 0–100 health score + breakdown. Cheapest call.",
    example: "curl https://depscope.dev/api/health/pypi/fastapi",
    params: [
      { name: "version", type: "query", desc: "Optional pinned version." },
    ],
  },
  {
    method: "GET",
    path: "/api/exists/{ecosystem}/{package}",
    desc: "DB-only existence probe. <10ms. Use before suggesting an unfamiliar name.",
    example: "curl https://depscope.dev/api/exists/pypi/django",
  },
  {
    method: "GET",
    path: "/api/latest/{ecosystem}/{package}",
    desc: "Latest version only. Cached.",
    example: "curl https://depscope.dev/api/latest/npm/express",
  },
];

const SECURITY_ENDPOINTS: Endpoint[] = [
  {
    method: "GET",
    path: "/api/vulns/{ecosystem}/{package}",
    desc: "Known vulnerabilities from OSV (filtered to latest version). KEV + EPSS enriched.",
    example: "curl https://depscope.dev/api/vulns/npm/lodash",
  },
  {
    method: "GET",
    path: "/api/malicious/{ecosystem}/{package}",
    desc: "OpenSSF malicious package feed (224k entries). Sanity-guarded on mainstream packages.",
    example: "curl https://depscope.dev/api/malicious/npm/ua-parser-js",
  },
  {
    method: "GET",
    path: "/api/typosquat/{ecosystem}/{package}",
    desc: "Typosquat detector. Pre-computed + runtime Levenshtein against top-1M-downloads packages.",
    example: "curl https://depscope.dev/api/typosquat/npm/lodsh",
  },
  {
    method: "GET",
    path: "/api/maintainers/{ecosystem}/{package}",
    desc: "Per-package maintainer info: count, bus factor, alerts.",
    example: "curl https://depscope.dev/api/maintainers/npm/express",
  },
  {
    method: "GET",
    path: "/api/maintainer/trust/{platform}/{username}",
    desc: "Per-maintainer trust score (0–100). E.g. check if 'vercel' or 'facebook' is a safe maintainer.",
    example: "curl https://depscope.dev/api/maintainer/trust/npm/vercel",
  },
  {
    method: "GET",
    path: "/api/scorecard/{ecosystem}/{package}",
    desc: "OSS Scorecard score (0–10) + branch-protection, signed-releases, pinned-dependencies signals.",
    example: "curl https://depscope.dev/api/scorecard/npm/react",
  },
  {
    method: "GET",
    path: "/api/provenance/{ecosystem}/{package}",
    desc: "npm provenance / Sigstore attestations.",
    example: "curl https://depscope.dev/api/provenance/npm/prettier",
  },
];

const STACK_ENDPOINTS: Endpoint[] = [
  {
    method: "POST",
    path: "/api/scan",
    desc: "Audit a whole project. Accepts explicit packages dict OR a lockfile string (9 formats: package-lock, pnpm-lock, yarn.lock, poetry.lock, Pipfile.lock, composer.lock, Cargo.lock, requirements.txt, go.sum). Optional SBOM output.",
    example: `curl -X POST https://depscope.dev/api/scan -H 'content-type: application/json' -d '{"lockfile":"flask==3.0.0\\nrequests==2.31.0","lockfile_kind":"requirements.txt"}'`,
    params: [
      { name: "ecosystem", type: "body", desc: "(string) npm, pypi, cargo, etc. Auto-detected when lockfile is passed." },
      { name: "packages", type: "body", desc: "(object) {name: version_or_range}. Required unless lockfile is sent." },
      { name: "lockfile", type: "body", desc: "(string) raw lockfile content — alternative to packages." },
      { name: "lockfile_kind", type: "body", desc: "(string, optional) pnpm-lock.yaml / yarn.lock / poetry.lock / Pipfile.lock / composer.lock / Cargo.lock / requirements.txt / go.sum / package-lock.json. Auto-detected if omitted." },
      { name: "format", type: "body", desc: "native | cyclonedx | spdx. Default native." },
      { name: "include_transitive", type: "body", desc: "(bool) Reserved — lockfiles already give full graph." },
    ],
  },
  {
    method: "GET",
    path: "/api/compare/{ecosystem}/{pkg1},{pkg2},...}",
    desc: "Side-by-side comparison (2–10 packages). Caveats per package (deprecated, low-adoption, vulns, higher-deps).",
    example: "curl https://depscope.dev/api/compare/npm/express,fastify,hono",
  },
  {
    method: "POST",
    path: "/api/compat",
    desc: "Test compatibility of a stack before upgrading.",
    example: `curl -X POST https://depscope.dev/api/compat -H 'content-type: application/json' -d '{"packages":{"next":"15","react":"19"}}'`,
    params: [
      { name: "packages", type: "body", desc: "(object) {name: version}. E.g. {next:\"15\",react:\"19\",react-dom:\"19\"}." },
    ],
  },
  {
    method: "GET",
    path: "/api/alternatives/{ecosystem}/{package}",
    desc: "Curated alternatives (especially for deprecated packages: request → axios/got, moment → dayjs, …).",
    example: "curl https://depscope.dev/api/alternatives/npm/request",
  },
  {
    method: "GET",
    path: "/api/migration/{ecosystem}/{from}/{to}",
    desc: "Curated migration path with before/after code diff, rationale, breaking changes, estimated effort.",
    example: "curl https://depscope.dev/api/migration/npm/request/axios",
  },
];

const DISCOVERY_ENDPOINTS: Endpoint[] = [
  {
    method: "GET",
    path: "/api/trending",
    desc: "Trending packages across ecosystems. Live rank + weekly growth.",
    example: "curl 'https://depscope.dev/api/trending?limit=20'",
  },
  {
    method: "GET",
    path: "/api/tree/{ecosystem}/{package}",
    desc: "Full transitive dependency tree (flattened).",
    example: "curl https://depscope.dev/api/tree/npm/express",
  },
  {
    method: "GET",
    path: "/api/licenses/{ecosystem}/{package}",
    desc: "License audit across transitive deps.",
    example: "curl https://depscope.dev/api/licenses/npm/express",
  },
  {
    method: "GET",
    path: "/api/versions/{ecosystem}/{package}",
    desc: "Full version history.",
    example: "curl https://depscope.dev/api/versions/cargo/serde",
  },
  {
    method: "GET",
    path: "/api/history/{ecosystem}/{package}",
    desc: "Historical health and download trajectory (90d).",
    example: "curl https://depscope.dev/api/history/npm/express",
  },
  {
    method: "GET",
    path: "/api/install/{ecosystem}/{package}",
    desc: "Install command generator (cross-ecosystem: npm install, pip install, cargo add, ...).",
    example: "curl https://depscope.dev/api/install/cargo/serde",
  },
  {
    method: "GET",
    path: "/api/pin_safe/{ecosystem}/{package}",
    desc: "Recommend a safe version to pin (latest stable, with no known critical CVEs).",
    example: "curl https://depscope.dev/api/pin_safe/npm/express",
  },
];

const ERROR_BUG_ENDPOINTS: Endpoint[] = [
  {
    method: "GET",
    path: "/api/error",
    desc: "Free-text search across the error → fix database.",
    example: "curl 'https://depscope.dev/api/error?q=Cannot+find+module'",
    params: [
      { name: "q", type: "query", desc: "Search keyword(s)" },
    ],
  },
  {
    method: "POST",
    path: "/api/error/resolve",
    desc: "Exact-match resolution from a full stack trace.",
    example: `curl -X POST https://depscope.dev/api/error/resolve -H 'content-type: application/json' -d '{"error":"Error: Cannot find module \\'express\\' at Function.Module._resolveFilename..."}'`,
  },
  {
    method: "GET",
    path: "/api/bugs/{ecosystem}/{package}",
    desc: "Known non-CVE bugs (GitHub issues with repro).",
    example: "curl 'https://depscope.dev/api/bugs/npm/react?version=19.0.0'",
  },
  {
    method: "GET",
    path: "/api/breaking/{ecosystem}/{package}",
    desc: "Breaking changes between two majors (with migration hints).",
    example: "curl 'https://depscope.dev/api/breaking/npm/next?from_version=14&to_version=16'",
  },
];

const META_ENDPOINTS: Endpoint[] = [
  {
    method: "GET",
    path: "/api/stats",
    desc: "Platform stats (ecosystem counts, trending, intel — agents_breakdown, hallucinations_week).",
    example: "curl https://depscope.dev/api/stats",
  },
  {
    method: "GET",
    path: "/api/ecosystems",
    desc: "Supported ecosystems with package/vuln counts + registry URLs.",
    example: "curl https://depscope.dev/api/ecosystems",
  },
  {
    method: "GET",
    path: "/api/now",
    desc: "Current UTC time. Agents use this to check server time awareness.",
    example: "curl https://depscope.dev/api/now",
  },
];

const GROUPS: { title: string; hint: string; items: Endpoint[] }[] = [
  { title: "Core", hint: "The 5 endpoints that cover 80% of agent use.", items: CORE_ENDPOINTS },
  { title: "Security", hint: "Typosquat, malicious, maintainer trust, Scorecard, provenance.", items: SECURITY_ENDPOINTS },
  { title: "Stack / projects", hint: "Scan (with lockfile + SBOM), compare, compat, alternatives, migration.", items: STACK_ENDPOINTS },
  { title: "Discovery", hint: "Trending, tree, versions, install command, pin-safe.", items: DISCOVERY_ENDPOINTS },
  { title: "Errors & bugs", hint: "Text search + exact-match resolution + breaking changes.", items: ERROR_BUG_ENDPOINTS },
  { title: "Meta", hint: "Stats, ecosystems metadata, time.", items: META_ENDPOINTS },
];

const BADGE_ENDPOINTS = [
  { path: "/badge/{ecosystem}/{package}", desc: "Health score badge (SVG). Embed in README.", curl: "curl https://depscope.dev/badge/npm/express", md: "![DepScope](https://depscope.dev/badge/npm/express)" },
  { path: "/badge/score/{ecosystem}/{package}", desc: "Score-only badge variant (compact).", curl: "curl https://depscope.dev/badge/score/pypi/django", md: "![Score](https://depscope.dev/badge/score/pypi/django)" },
];

export default function ApiDocsPage() {
  return (
    <div className="min-h-screen">
      <main className="max-w-5xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="API Reference"
          title="API Documentation"
          description="Free, open API. No auth required for public endpoints. JSON responses."
        />

        <Section>
          <Card>
            <CardBody>
              <dl className="grid grid-cols-[140px_1fr] gap-y-2 text-sm">
                <dt className="text-[var(--text-dim)]">Base URL</dt>
                <dd className="font-mono text-[var(--accent)]">https://depscope.dev</dd>
                <dt className="text-[var(--text-dim)]">Auth</dt>
                <dd>
                  None for public endpoints. Higher limits via <a href="/account/api-keys" className="text-[var(--accent)] hover:underline">API keys</a>.
                </dd>
                <dt className="text-[var(--text-dim)]">Rate limit</dt>
                <dd className="tabular-nums">200 req/min per IP (bypassed for major AI agents: Claude, GPT, Cursor, Windsurf, Copilot, ...)</dd>
                <dt className="text-[var(--text-dim)]">Format</dt>
                <dd>JSON (UTF-8). /api/prompt returns text/plain.</dd>
                <dt className="text-[var(--text-dim)]">Caching</dt>
                <dd>6h edge (Cloudflare) + 6h Redis. gzip + brotli. Cache-Control with stale-while-revalidate — agents never wait on refresh.</dd>
                <dt className="text-[var(--text-dim)]">MCP</dt>
                <dd>22 consolidated tools at <a href="https://mcp.depscope.dev/mcp" className="text-[var(--accent)] hover:underline">mcp.depscope.dev/mcp</a> (remote, zero install).</dd>
                <dt className="text-[var(--text-dim)]">OpenAPI</dt>
                <dd><a href="/openapi.json" className="text-[var(--accent)] hover:underline">openapi.json</a> · <a href="/docs" className="text-[var(--accent)] hover:underline">Swagger UI</a></dd>
              </dl>
            </CardBody>
          </Card>
        </Section>

        <div className="flex flex-wrap gap-3 my-6 text-xs font-mono">
          {GROUPS.map((g) => (
            <a key={g.title} href={`#g-${g.title.toLowerCase().replace(/[^a-z0-9]+/g,"-")}`} className="text-[var(--accent)] hover:underline">
              {g.title}
            </a>
          ))}
          <a href="#badges" className="text-[var(--accent)] hover:underline">Badges</a>
          <a href="#scoring" className="text-[var(--accent)] hover:underline">Health score</a>
          <a href="#ai-agents" className="text-[var(--accent)] hover:underline">AI agents</a>
        </div>

        {GROUPS.map((g) => (
          <Section key={g.title} title={g.title} description={g.hint} className="mt-8">
            <div id={`g-${g.title.toLowerCase().replace(/[^a-z0-9]+/g,"-")}`} className="space-y-3">
              {g.items.map((ep, i) => (
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
                    {ep.returns && ep.returns.length > 0 && (
                      <div className="mb-3">
                        <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-faded)] mb-1">Notable fields</div>
                        <ul className="text-xs text-[var(--text-dim)] space-y-0.5 list-disc list-inside">
                          {ep.returns.map((r, j) => <li key={j}>{r}</li>)}
                        </ul>
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
        ))}

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
                  { pts: 25, label: "Security", hint: "Known CVEs, KEV, EPSS" },
                  { pts: 20, label: "Popularity", hint: "Weekly downloads" },
                  { pts: 15, label: "Maturity", hint: "Version count" },
                  { pts: 15, label: "Community", hint: "Maintainers + bus factor" },
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
                  DepScope is designed to be called by AI agents before suggesting any package install.
                  Wire it in once and every <code className="font-mono text-xs text-[var(--accent)]">npm install</code> /
                  {" "}<code className="font-mono text-xs text-[var(--accent)]">pip install</code> decision is one fresh
                  HTTP call away. Use <code className="font-mono text-xs text-[var(--accent)]">/api/prompt</code> for
                  cheap token-efficient briefs, <code className="font-mono text-xs text-[var(--accent)]">/api/check</code>
                  {" "}when you need the full JSON.
                </p>
                <div className="space-y-2">
                  {[
                    { label: "ChatGPT / OpenAI Actions", url: "https://depscope.dev/.well-known/ai-plugin.json" },
                    { label: "OpenAPI spec", url: "https://depscope.dev/openapi.json" },
                    { label: "Interactive docs (Swagger)", url: "https://depscope.dev/docs" },
                    { label: "MCP server (remote, zero install)", url: "https://mcp.depscope.dev/mcp" },
                    { label: "MCP manifest (.well-known)", url: "https://depscope.dev/.well-known/mcp.json" },
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
