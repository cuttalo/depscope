import type { Metadata } from "next";
import Link from "next/link";
import { Card, CardBody, PageHeader, Section, Footer } from "../../components/ui";

export const metadata: Metadata = {
  title: "Supply Chain Security API — Free for AI Agents",
  description:
    "Prevent supply chain attacks before install. DepScope API checks package health, vulnerabilities, typosquatting risk, deprecation and license across 17 ecosystems.",
  alternates: { canonical: "https://depscope.dev/supply-chain-security-api" },
  robots: { index: true, follow: true },
  openGraph: {
    title: "Supply Chain Security API — Free for AI Agents",
    description: "Stop supply chain attacks before install.",
    url: "https://depscope.dev/supply-chain-security-api",
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
          eyebrow="Security"
          title="Supply Chain Security API"
          description="Block malicious or deprecated packages before they enter your build. Free."
        />
        <Section>
          <Card>
            <CardBody>
              <h2 className="text-base font-semibold mb-2">What we flag</h2>
              <ul className="list-disc list-inside text-sm text-[var(--text-dim)] space-y-1">
                <li>Known vulnerabilities from OSV, GHSA, NVD</li>
                <li>Deprecated packages still getting downloads</li>
                <li>Typosquatting candidates (lookalike names)</li>
                <li>Single-maintainer risk and low bus factor</li>
                <li>License conflicts across transitive dependencies</li>
                <li>Large, unmaintained, or unpublished packages</li>
              </ul>
            </CardBody>
          </Card>
        </Section>
        <Section>
          <Card>
            <CardBody>
              <h2 className="text-base font-semibold mb-2">Integrate in 30 seconds</h2>
              <pre className="text-xs bg-[var(--bg-input)] rounded p-3 font-mono overflow-x-auto">curl https://depscope.dev/api/check/npm/left-pad</pre>
              <p className="text-sm text-[var(--text-dim)] leading-relaxed mt-3">
                Call once before any install. Free tier: 200 req/min, no auth. <Link className="text-[var(--accent)] hover:underline" href="/api-docs">API docs</Link>.
              </p>
            </CardBody>
          </Card>
        </Section>
        <Footer />
      </main>
    </div>
  );
}
