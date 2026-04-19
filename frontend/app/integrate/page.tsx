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
    blurb: 'Search "DepScope" in the GPT Store, or use the OpenAPI spec.',
    code: `https://depscope.dev/openapi-gpt.json`,
  },
  {
    id: "gha",
    title: "GitHub Actions",
    blurb: "Add to your CI pipeline.",
    file: ".github/workflows/depscope.yml",
    lang: "yaml",
    code: `- name: DepScope Audit
  run: |
    curl -s -X POST https://depscope.dev/api/scan \\
      -H "Content-Type: application/json" \\
      -d "{\\"ecosystem\\":\\"npm\\",\\"packages\\":$(cat package.json | jq '.dependencies')}" \\
      | jq '.project_risk'`,
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
