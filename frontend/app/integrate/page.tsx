import { Card, CardBody, CardHeader, CardTitle, PageHeader, Section, Footer, Badge } from "../../components/ui";
import { CopyButton } from "../../components/CopyButton";

interface Snippet {
  id: string;
  title: string;
  blurb: string;
  file?: string;
  lang?: string;
  code: string;
}

const SNIPPETS: Snippet[] = [
  {
    id: "mcp",
    title: "MCP server (Claude Code / Desktop / Cursor)",
    blurb: "Install via npm. 29 tools for package intelligence (incl. ai_brief, audit_stack, get_migration_path), zero config.",
    lang: "sh",
    code: `# Claude Code (one-liner — local stdio)
claude mcp add depscope -- npx -y depscope-mcp

# Remote MCP (no install, recommended)
# Add to ~/.claude/mcp_servers.json or Cursor mcp.json:
{
  "mcpServers": {
    "depscope": { "url": "https://mcp.depscope.dev/mcp" }
  }
}

# 23 tools available. Most-used for AI agents:
#   ai_brief         — 300-token package verdict
#   audit_stack      — one-call audit for N packages
#   get_migration_path — code diff to migrate deprecated → modern`,
  },
  {
    id: "claude",
    title: "Claude Code",
    blurb: "Add one line to CLAUDE.md or MEMORY.md.",
    file: "CLAUDE.md",
    lang: "md",
    code: `## DEPSCOPE — Before any install: curl depscope.dev/api/check/{eco}/{pkg}`,
  },
  {
    id: "cursor",
    title: "Cursor",
    blurb: "Add to your .cursorrules file.",
    file: ".cursorrules",
    code: `Before any install: curl depscope.dev/api/check/{eco}/{pkg} — if deprecated, curl depscope.dev/api/alternatives/{eco}/{pkg}. No auth, free.`,
  },
  {
    id: "windsurf",
    title: "Windsurf / Codeium",
    blurb: "Add to .windsurfrules or project instructions.",
    file: ".windsurfrules",
    code: `Before any install: curl depscope.dev/api/check/{eco}/{pkg}`,
  },
  {
    id: "curl",
    title: "Any AI agent (curl / HTTP)",
    blurb: "Just call the API. No auth, no signup.",
    lang: "sh",
    code: `# Check a package
curl https://depscope.dev/api/check/npm/express

# Compare packages
curl https://depscope.dev/api/compare/npm/express,fastify,hono

# Scan entire project
curl -X POST https://depscope.dev/api/scan \\
  -H "Content-Type: application/json" \\
  -d '{"ecosystem":"npm","packages":{"express":"*","lodash":"*"}}'`,
  },
  {
    id: "chatgpt",
    title: "ChatGPT",
    blurb: 'Direct link: https://chatgpt.com/g/g-69e02d12226c8191a7f24f3a8481bc4e-depscope. Or OpenAPI spec:',
    code: `https://depscope.dev/openapi-gpt.json`,
  },
  {
    id: "cli",
    title: "CLI — one-line audit before install",
    blurb: "Published on npm as depscope-cli. Works on any machine with Node 18+.",
    lang: "sh",
    code: `# Audit before install (CI-friendly, exit 1 on critical)
npx -y depscope-cli audit express request lodash

# From a manifest
npx -y depscope-cli audit --file package.json
npx -y depscope-cli audit --file requirements.txt

# Drop-in code diff for deprecated → modern
npx -y depscope-cli migration npm request axios

# One-package AI brief (~300 tokens, paste into system prompt)
npx -y depscope-cli brief npm/express`,
  },
  {
    id: "migration",
    title: "Migration paths (deprecated → modern with code diff)",
    blurb: "Curated migrations with literal before/after snippets ready to apply. Call via MCP get_migration_path or REST.",
    lang: "sh",
    code: `# MCP tool call (23 of 26 tools)
{"name":"get_migration_path","arguments":{"ecosystem":"npm","from_package":"request","to_package":"axios"}}

# REST
curl https://depscope.dev/api/migration/npm/request/axios
curl https://depscope.dev/api/migration/pypi/urllib2/requests
curl https://depscope.dev/api/migration/npm/moment/dayjs

# Returns: rationale, effort_minutes, diff_examples[], breaking_changes[]`,
  },
  {
    id: "vscode",
    title: "VS Code (Copilot, Cline, Continue.dev)",
    blurb: "VS Code itself has no MCP — works through any AI extension that supports MCP. Drop the same URL.",
    file: ".vscode/mcp.json",
    lang: "json",
    code: `// 1) VS Code + GitHub Copilot (MCP preview)
//    Settings: "chat.mcp.enabled": true
//    Then create .vscode/mcp.json (workspace) or user-global:
{
  "servers": {
    "depscope": { "type": "http", "url": "https://mcp.depscope.dev/mcp" }
  }
}

// 2) VS Code + Cline — Settings UI → MCP Servers → Add
//    URL: https://mcp.depscope.dev/mcp

// 3) VS Code + Continue.dev (~/.continue/config.json)
{
  "mcpServers": [
    { "name": "depscope",
      "transport": { "type": "sse", "url": "https://mcp.depscope.dev/mcp" } }
  ]
}

// 4) Fallback (no MCP extension): .vscode/tasks.json
//    Run "DepScope: audit" from the Tasks menu
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "DepScope: audit",
      "type": "shell",
      "command": "npx -y depscope-cli audit --file package.json",
      "problemMatcher": []
    }
  ]
}`,
  },
  {
    id: "gha",
    title: "GitHub Actions",
    blurb: "Fail PRs on deprecated, malicious, or actively-exploited packages.",
    file: ".github/workflows/depscope.yml",
    lang: "yaml",
    code: `name: Dependency audit
on: [pull_request, push]

jobs:
  depscope:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: cuttalo/depscope-audit-action@v1
        with:
          manifest: package.json
          fail-on: critical   # critical | risk | none`,
  },
  {
    id: "python",
    title: "Python / LangChain",
    blurb: "Use as a LangChain tool.",
    file: "tools/depscope.py",
    lang: "py",
    code: `from langchain.tools import tool
import requests

@tool
def check_package(ecosystem: str, package: str) -> str:
    """Check if a package is safe to install."""
    r = requests.get(f"https://depscope.dev/api/check/{ecosystem}/{package}")
    return r.json()["recommendation"]["summary"]`,
  },
  {
    id: "badge",
    title: "README badge",
    blurb: "Add a health badge to your README.",
    lang: "md",
    code: `[![health](https://depscope.dev/badge/npm/YOUR-PACKAGE)](https://depscope.dev/pkg/npm/YOUR-PACKAGE)`,
  },
];

export default function IntegratePage() {
  return (
    <div className="min-h-screen">
      <main className="max-w-4xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="Integrate"
          title="Add DepScope to your AI agent"
          description="One line in your config. No signup, no API key. Works with every major agent and CI."
          actions={<Badge variant="success">Free · no auth</Badge>}
        />


        <Section>
          <Card>
            <CardBody>
              <div className="flex items-center justify-between mb-3">
                <div>
                  <div className="text-xs uppercase tracking-wider text-[var(--text-faded)]">Install in 1 click</div>
                  <div className="text-sm text-[var(--text-dim)] mt-1">No JSON to edit. Click the button for your IDE.</div>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--accent)]/10 text-[var(--accent)] border border-[var(--accent)]/30">29 tools · zero auth</span>
              </div>
              <div className="grid md:grid-cols-3 gap-3">
                <a href="cursor://anysphere.cursor-deeplink/mcp/install?name=depscope&config=eyJ1cmwiOiJodHRwczovL21jcC5kZXBzY29wZS5kZXYvbWNwIn0="
                   className="rounded border border-[var(--border)] bg-[var(--bg-input)] hover:bg-[var(--bg-hover)] hover:border-[var(--accent)]/40 px-4 py-3 transition flex items-center gap-3">
                  <svg className="w-5 h-5 text-[var(--accent)]" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L2 7v10l10 5 10-5V7L12 2zm0 2.18L19.82 8 12 11.82 4.18 8 12 4.18zM4 9.6l7 3.5v7.7l-7-3.5V9.6zm16 0v7.7l-7 3.5v-7.7l7-3.5z"/></svg>
                  <div>
                    <div className="font-semibold text-sm text-[var(--text)]">Add to Cursor</div>
                    <div className="text-[11px] text-[var(--text-faded)]">Opens Cursor &rarr; auto-installs.</div>
                  </div>
                </a>
                <div className="rounded border border-[var(--border)] bg-[var(--bg-input)] px-4 py-3 flex items-center justify-between gap-2">
                  <div>
                    <div className="font-semibold text-sm text-[var(--text)]">Claude Code</div>
                    <div className="text-[11px] text-[var(--text-faded)]">Run this once in any terminal.</div>
                  </div>
                  <CopyButton text="claude mcp add depscope --transport http https://mcp.depscope.dev/mcp" />
                </div>
                <div className="rounded border border-[var(--border)] bg-[var(--bg-input)] px-4 py-3 flex items-center justify-between gap-2">
                  <div>
                    <div className="font-semibold text-sm text-[var(--text)]">VS Code (.vscode/mcp.json)</div>
                    <div className="text-[11px] text-[var(--text-faded)]">Drop-in workspace config.</div>
                  </div>
                  <CopyButton text={'{"servers":{"depscope":{"type":"http","url":"https://mcp.depscope.dev/mcp"}}}'} />
                </div>
              </div>
              <div className="mt-3 text-[11px] text-[var(--text-faded)]">
                Claude Desktop, Windsurf, Cline, Continue, ChatGPT, Aider &mdash; full snippets below.
              </div>
            </CardBody>
          </Card>
        </Section>

        <div className="space-y-4">
          {SNIPPETS.map((s) => (
            <Section key={s.id}>
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>{s.title}</CardTitle>
                      <p className="text-xs text-[var(--text-dim)] mt-0.5">{s.blurb}</p>
                    </div>
                    <CopyButton text={s.code} />
                  </div>
                </CardHeader>
                <div className="px-4 py-3 bg-[var(--bg-input)] border-t border-[var(--border)]">
                  {s.file && (
                    <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-faded)] mb-2">
                      {s.file}
                    </div>
                  )}
                  <pre className="text-xs text-[var(--accent)] font-mono overflow-x-auto whitespace-pre-wrap leading-relaxed">
                    {s.code}
                  </pre>
                </div>
              </Card>
            </Section>
          ))}
        </div>

        <Section className="mt-10">
          <Card>
            <CardBody className="flex items-center justify-between flex-wrap gap-3">
              <div>
                <div className="text-sm font-semibold text-[var(--text)]">Need the full API reference?</div>
                <div className="text-xs text-[var(--text-dim)] mt-1">Every endpoint, parameter, and example.</div>
              </div>
              <a
                href="/api-docs"
                className="inline-flex items-center gap-1 text-sm font-medium px-4 py-2 rounded border border-[var(--border)] hover:bg-[var(--bg-hover)] transition"
              >
                API Docs →
              </a>
            </CardBody>
          </Card>
        </Section>
      </main>
      <Footer />
    </div>
  );
}
