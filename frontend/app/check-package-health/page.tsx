import type { Metadata } from "next";
import Link from "next/link";
import { Card, CardBody, PageHeader, Section, Footer, Badge } from "../../components/ui";

export const metadata: Metadata = {
  title: "Check Package Health — Free Score for Any npm, pip, Cargo Package",
  description:
    "Instantly check the health score of any npm, PyPI, Cargo, Go, Maven or NuGet package. Free, no signup. Vulnerabilities, deprecation, maintenance and popularity in one score.",
  alternates: { canonical: "https://depscope.dev/check-package-health" },
  robots: { index: true, follow: true },
  openGraph: {
    title: "Check Package Health — Free Score for Any Package",
    description: "Instantly check health of any npm, pip, Cargo, Go, Maven, NuGet package.",
    url: "https://depscope.dev/check-package-health",
    siteName: "DepScope",
    type: "website",
  },
  twitter: { card: "summary_large_image" },
};

const EXAMPLES = [
  { eco: "npm", pkg: "express" },
  { eco: "npm", pkg: "react" },
  { eco: "pypi", pkg: "django" },
  { eco: "pypi", pkg: "fastapi" },
  { eco: "cargo", pkg: "serde" },
  { eco: "cargo", pkg: "tokio" },
];

export default function Page() {
  return (
    <div className="min-h-screen">
      <main className="max-w-3xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="Free Tool"
          title="Check Package Health"
          description="One score from 0 to 100. Free. Covers 17 ecosystems. No signup."
        />
        <Section>
          <Card>
            <CardBody>
              <h2 className="text-base font-semibold mb-2">How the health score works</h2>
              <p className="text-sm text-[var(--text-dim)] leading-relaxed mb-3">
                Every DepScope package has a 0-100 score built from five signals:
              </p>
              <ul className="list-disc list-inside text-sm text-[var(--text-dim)] space-y-1">
                <li><strong>Maintenance (25)</strong>: release cadence, last publish, issue responsiveness</li>
                <li><strong>Security (25)</strong>: known vulnerabilities, severity, patched versions</li>
                <li><strong>Popularity (20)</strong>: weekly downloads, GitHub stars, usage trend</li>
                <li><strong>Maturity (15)</strong>: age, version stability, semver track record</li>
                <li><strong>Community (15)</strong>: maintainers, contributors, deprecation status</li>
              </ul>
            </CardBody>
          </Card>
        </Section>
        <Section>
          <h2 className="text-base font-semibold mb-3">Try it on a popular package</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {EXAMPLES.map((e) => (
              <Link
                key={`${e.eco}/${e.pkg}`}
                href={`/pkg/${e.eco}/${e.pkg}`}
                className="p-3 rounded border border-[var(--border)] hover:border-[var(--accent)] hover:bg-[var(--bg-card)] transition text-sm font-mono"
              >
                <Badge variant="accent">{e.eco}</Badge> {e.pkg}
              </Link>
            ))}
          </div>
        </Section>
        <Section>
          <Card>
            <CardBody>
              <h2 className="text-base font-semibold mb-2">Or use the API directly</h2>
              <pre className="text-xs bg-[var(--bg-input)] rounded p-3 font-mono overflow-x-auto">curl https://depscope.dev/api/check/npm/express</pre>
              <p className="text-xs text-[var(--text-dim)] mt-2">No API key. 200 requests per minute.</p>
            </CardBody>
          </Card>
        </Section>
        <Footer />
      </main>
    </div>
  );
}
