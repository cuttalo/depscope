import { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import {
  Card,
  CardBody,
  PageHeader,
  Section,
  Badge,
  ActionBadge,
  Footer,
  Table,
  Thead,
  Tbody,
  Th,
  Td,
  Tr,
} from "../../../../components/ui";
import { CopyButton } from "../../../../components/CopyButton";

interface ComparePackage {
  package: string;
  latest_version: string;
  health_score: number;
  health_risk: string;
  downloads_weekly: number;
  vulnerabilities_count: number;
  vulns_critical: number;
  vulns_high: number;
  last_published: string;
  license: string;
  deprecated: boolean;
  maintainers_count: number;
  dependencies_count: number;
  recommendation: string;
}

interface CompareResult {
  ecosystem: string;
  compared: number;
  winner: string;
  packages: ComparePackage[];
  _response_ms: number;
}

const VALID_ECO = ["npm","pypi","cargo","go","composer","maven","nuget","rubygems","pub","hex","swift","cocoapods","cpan","hackage","cran","conda","homebrew"];

function parsePackages(slug: string): string[] {
  return decodeURIComponent(slug).split("-vs-").filter(Boolean);
}

async function fetchCompare(ecosystem: string, packages: string[]): Promise<CompareResult | null> {
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/compare/${ecosystem}/${packages.join(",")}`, { next: { revalidate: 3600 } });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

type Props = { params: Promise<{ ecosystem: string; packages: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { ecosystem, packages: packagesSlug } = await params;
  const pkgs = parsePackages(packagesSlug);
  if (!VALID_ECO.includes(ecosystem) || pkgs.length < 2) return { title: "Comparison — DepScope" };

  const data = await fetchCompare(ecosystem, pkgs);
  const names = pkgs.join(" vs ");
  const title = `${names} — Package Comparison | DepScope`;
  let description = `Compare ${names} for ${ecosystem}.`;
  if (data) {
    const scores = data.packages.map((p) => `${p.package}: ${p.health_score}/100`).join(", ");
    description = `${names} comparison for ${ecosystem}. Health scores: ${scores}. Winner: ${data.winner}. Free data by DepScope.`;
  }
  return {
    title,
    description,
    openGraph: { title, description, url: `https://depscope.dev/compare/${ecosystem}/${packagesSlug}`, siteName: "DepScope", type: "website" },
    twitter: { card: "summary", title, description },
    alternates: { canonical: `https://depscope.dev/compare/${ecosystem}/${packagesSlug}` },
    robots: { index: true, follow: true },
  };
}

function ScoreCell({ score }: { score: number }) {
  const color =
    score >= 80 ? "var(--green)" :
    score >= 60 ? "var(--yellow)" :
    score >= 40 ? "var(--orange)" : "var(--red)";
  return (
    <span className="text-2xl font-semibold tabular-nums" style={{ color }}>
      {score}
      <span className="text-[10px] text-[var(--text-faded)] font-mono ml-0.5">/100</span>
    </span>
  );
}

function formatDownloads(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(0) + "K";
  return String(n);
}

export default async function ComparePage({ params }: Props) {
  const { ecosystem, packages: packagesSlug } = await params;
  const pkgs = parsePackages(packagesSlug);
  if (!VALID_ECO.includes(ecosystem) || pkgs.length < 2 || pkgs.length > 5) notFound();

  const data = await fetchCompare(ecosystem, pkgs);
  if (!data || !data.packages || data.packages.length === 0) notFound();

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: `${pkgs.join(" vs ")} — Package Comparison`,
    description: `Comparison of ${pkgs.join(", ")} packages for ${ecosystem}`,
    numberOfItems: data.packages.length,
    itemListElement: data.packages.map((p, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: p.package,
      url: `https://depscope.dev/pkg/${ecosystem}/${p.package}`,
    })),
  };

  const curlCmd = `curl https://depscope.dev/api/compare/${ecosystem}/${data.packages.map(p => p.package).join(",")}`;

  return (
    <div className="min-h-screen">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <nav className="text-xs font-mono text-[var(--text-dim)] mb-4">
          <Link href="/" className="hover:text-[var(--accent)] transition">depscope</Link>
          <span className="mx-1 text-[var(--text-faded)]">/</span>
          <Link href={`/ecosystems/${ecosystem}`} className="hover:text-[var(--accent)] transition">{ecosystem}</Link>
          <span className="mx-1 text-[var(--text-faded)]">/</span>
          <span className="text-[var(--text)]">compare</span>
        </nav>

        <PageHeader
          eyebrow={`Compare · ${ecosystem}`}
          title={data.packages.map((p) => p.package).join(" vs ")}
          description={`${data.compared} packages analyzed in ${data._response_ms}ms`}
          actions={data.winner ? <Badge variant="success">Winner: {data.winner}</Badge> : undefined}
        />

        <Section>
          <Card>
            <Table>
              <Thead>
                <Tr>
                  <Th>Metric</Th>
                  {data.packages.map((p) => (
                    <Th key={p.package} className="text-center">
                      <Link href={`/pkg/${ecosystem}/${p.package}`} className="text-[var(--accent)] hover:underline font-mono">
                        {p.package}
                      </Link>
                      {p.package === data.winner && (
                        <Badge variant="accent" className="ml-2">best</Badge>
                      )}
                    </Th>
                  ))}
                </Tr>
              </Thead>
              <Tbody>
                <Tr>
                  <Td className="text-[var(--text-dim)]">Health score</Td>
                  {data.packages.map((p) => (
                    <Td key={p.package} className="text-center"><ScoreCell score={p.health_score} /></Td>
                  ))}
                </Tr>
                <Tr>
                  <Td className="text-[var(--text-dim)]">Version</Td>
                  {data.packages.map((p) => (
                    <Td key={p.package} className="text-center font-mono tabular-nums">{p.latest_version}</Td>
                  ))}
                </Tr>
                <Tr>
                  <Td className="text-[var(--text-dim)]">Weekly downloads</Td>
                  {data.packages.map((p) => (
                    <Td key={p.package} className="text-center tabular-nums font-mono">{formatDownloads(p.downloads_weekly)}</Td>
                  ))}
                </Tr>
                <Tr>
                  <Td className="text-[var(--text-dim)]">Vulnerabilities</Td>
                  {data.packages.map((p) => (
                    <Td key={p.package} className="text-center">
                      {p.vulnerabilities_count === 0 ? (
                        <Badge variant="success">0</Badge>
                      ) : (
                        <Badge variant="danger">{p.vulnerabilities_count}</Badge>
                      )}
                    </Td>
                  ))}
                </Tr>
                <Tr>
                  <Td className="text-[var(--text-dim)]">License</Td>
                  {data.packages.map((p) => (
                    <Td key={p.package} className="text-center font-mono text-xs">{p.license || "—"}</Td>
                  ))}
                </Tr>
                <Tr>
                  <Td className="text-[var(--text-dim)]">Dependencies</Td>
                  {data.packages.map((p) => (
                    <Td key={p.package} className="text-center tabular-nums font-mono">{p.dependencies_count}</Td>
                  ))}
                </Tr>
                <Tr>
                  <Td className="text-[var(--text-dim)]">Maintainers</Td>
                  {data.packages.map((p) => (
                    <Td key={p.package} className="text-center tabular-nums font-mono">{p.maintainers_count}</Td>
                  ))}
                </Tr>
                <Tr>
                  <Td className="text-[var(--text-dim)]">Last published</Td>
                  {data.packages.map((p) => (
                    <Td key={p.package} className="text-center text-xs font-mono">
                      {p.last_published ? new Date(p.last_published).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }) : "—"}
                    </Td>
                  ))}
                </Tr>
                <Tr>
                  <Td className="text-[var(--text-dim)]">Recommendation</Td>
                  {data.packages.map((p) => (
                    <Td key={p.package} className="text-center"><ActionBadge action={p.recommendation} /></Td>
                  ))}
                </Tr>
              </Tbody>
            </Table>
          </Card>
        </Section>

        <Section className="mt-6">
          <Card>
            <CardBody className="flex items-center justify-between gap-3 flex-wrap">
              <code className="text-xs font-mono text-[var(--text-dim)] break-all">{curlCmd}</code>
              <CopyButton text={curlCmd} />
            </CardBody>
          </Card>
        </Section>
      </main>
      <Footer />
    </div>
  );
}
