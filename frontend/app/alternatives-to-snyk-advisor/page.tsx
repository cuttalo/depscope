import type { Metadata } from "next";
import Link from "next/link";
import { Card, CardBody, PageHeader, Section, Footer } from "../../components/ui";

export const metadata: Metadata = {
  title: "Snyk Advisor Alternative — Free Package Health API",
  description:
    "Looking for a Snyk Advisor alternative? DepScope offers free package health scores, vulnerabilities, and dependency analysis with a public API. 17 ecosystems, no signup.",
  alternates: { canonical: "https://depscope.dev/alternatives-to-snyk-advisor" },
  robots: { index: true, follow: true },
  openGraph: {
    title: "Snyk Advisor Alternative — DepScope",
    description: "Free package health scores with a public API. 17 ecosystems.",
    url: "https://depscope.dev/alternatives-to-snyk-advisor",
    siteName: "DepScope",
    type: "website",
  },
  twitter: { card: "summary_large_image" },
};

export default function Page() {
  return (
    <div className="min-h-screen">
      <main className="max-w-3xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="Alternatives"
          title="A free Snyk Advisor alternative"
          description="Same health-score philosophy, broader coverage, no paywall, built for AI agents."
        />
        <Section>
          <Card>
            <CardBody>
              <h2 className="text-base font-semibold mb-2">Why DepScope</h2>
              <ul className="list-disc list-inside text-sm text-[var(--text-dim)] space-y-1">
                <li>Free API with no signup or API keys</li>
                <li>17 ecosystems (vs 3-4 on most competitors)</li>
                <li>MCP server for Claude Code, Cursor, Cline</li>
                <li>Health score, vulns, bundle size, license, deps in one call</li>
                <li>Error → fix database and stack compatibility matrix included</li>
              </ul>
            </CardBody>
          </Card>
        </Section>
        <Section>
          <h2 className="text-base font-semibold mb-3">Get started</h2>
          <div className="space-y-1">
            <Link href="/api-docs" className="block p-2 rounded hover:bg-[var(--bg-card)] text-sm text-[var(--accent)]">API docs →</Link>
            <Link href="/integrate" className="block p-2 rounded hover:bg-[var(--bg-card)] text-sm text-[var(--accent)]">Integrate in 30s (Claude, Cursor, Cline) →</Link>
            <Link href="/explore" className="block p-2 rounded hover:bg-[var(--bg-card)] text-sm text-[var(--accent)]">Explore the data →</Link>
          </div>
        </Section>
        <Footer />
      </main>
    </div>
  );
}
