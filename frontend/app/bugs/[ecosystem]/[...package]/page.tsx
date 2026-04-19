import { Metadata } from "next";
import Link from "next/link";
import {
  Card,
  CardBody,
  CardHeader,
  Badge,
  SeverityBadge,
  Table,
  Thead,
  Tbody,
  Th,
  Td,
  Tr,
  Footer,
} from "../../../../components/ui";
import { CopyButton } from "../../../../components/CopyButton";

interface Bug {
  id: number;
  ecosystem: string;
  package_name: string;
  affected_version: string | null;
  fixed_version: string | null;
  bug_id: string | null;
  title: string;
  description: string | null;
  severity: string | null;
  status: string | null;
  source: string | null;
  source_url: string | null;
  labels: string[] | null;
  created_at: string | null;
  updated_at: string | null;
}

interface BugsPayload {
  ecosystem: string;
  package: string;
  version: string | null;
  bugs: Bug[];
  total: number;
}

const ECOSYSTEMS = [
  "npm", "pypi", "cargo", "go", "composer", "maven", "nuget",
  "rubygems", "pub", "hex", "swift", "cocoapods", "cpan",
  "hackage", "cran", "conda", "homebrew",
];

const ECO_LABEL: Record<string, string> = {
  npm: "npm", pypi: "PyPI", cargo: "Cargo", go: "Go",
  composer: "Composer", maven: "Maven", nuget: "NuGet",
  rubygems: "RubyGems", pub: "Pub", hex: "Hex",
  swift: "Swift", cocoapods: "CocoaPods", cpan: "CPAN",
  hackage: "Hackage", cran: "CRAN", conda: "Conda", homebrew: "Homebrew",
};

async function fetchBugs(ecosystem: string, pkg: string): Promise<BugsPayload | null> {
  try {
    const res = await fetch(
      `http://127.0.0.1:8000/api/bugs/${ecosystem}/${pkg}`,
      { next: { revalidate: 1800 } },
    );
    if (!res.ok) return null;
    return (await res.json()) as BugsPayload;
  } catch {
    return null;
  }
}

type Props = {
  params: Promise<{ ecosystem: string; package: string[] }>;
};

// SEO quality gate: pages with < 3 known bugs get noindex + canonical
// consolidated on /pkg/{eco}/{name} to avoid thin-content penalty.
const SEO_MIN_BUGS = 3;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { ecosystem, package: pkgParts } = await params;
  const pkg = pkgParts.join("/");
  const data = await fetchBugs(ecosystem, pkg);
  const count = data?.total ?? 0;

  const shouldIndex = count >= SEO_MIN_BUGS;

  const title = count
    ? `${pkg} bugs \u2014 known issues per version | DepScope`
    : `${pkg} \u2014 no known bugs indexed | DepScope`;
  const description = count
    ? `${count} known bug${count === 1 ? "" : "s"} in ${pkg}. See affected versions, fixed versions and workarounds. Indexed by DepScope from upstream issue trackers.`
    : `No known bugs recorded for ${pkg}. Check package health and breaking changes on DepScope.`;

  const canonical = shouldIndex
    ? `https://depscope.dev/bugs/${ecosystem}/${pkg}`
    : `https://depscope.dev/pkg/${ecosystem}/${pkg}`;

  return {
    title,
    description,
    keywords: [
      pkg, ecosystem, "known bugs", "issues",
      `${pkg} bugs`, `${pkg} known issues`, `${pkg} regression`,
      `${pkg} ${ecosystem}`,
    ],
    openGraph: {
      title,
      description,
      url: `https://depscope.dev/bugs/${ecosystem}/${pkg}`,
      siteName: "DepScope",
      type: "article",
      images: [
        {
          url: `https://depscope.dev/og/pkg/${ecosystem}/${pkg}`,
          width: 1200,
          height: 630,
          alt: `${pkg} known bugs on DepScope`,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [`https://depscope.dev/og/pkg/${ecosystem}/${pkg}`],
    },
    alternates: {
      canonical,
    },
    robots: shouldIndex
      ? {
          index: true,
          follow: true,
          googleBot: {
            index: true,
            follow: true,
            "max-snippet": -1,
            "max-image-preview": "large",
          },
        }
      : {
          index: false,
          follow: true,
          googleBot: { index: false, follow: true },
        },
  };
}

export default async function BugsDetailPage({ params }: Props) {
  const { ecosystem, package: pkgParts } = await params;
  const pkg = pkgParts.join("/");
  const ecoLower = ecosystem.toLowerCase();
  const validEco = ECOSYSTEMS.includes(ecoLower);
  const data = validEco ? await fetchBugs(ecoLower, pkg) : null;

  const breadcrumbLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "DepScope", item: "https://depscope.dev" },
      { "@type": "ListItem", position: 2, name: "Bugs", item: "https://depscope.dev/explore/bugs" },
      { "@type": "ListItem", position: 3, name: ECO_LABEL[ecoLower] || ecoLower, item: `https://depscope.dev/ecosystems/${ecoLower}` },
      { "@type": "ListItem", position: 4, name: pkg },
    ],
  };

  const faqLd = data && data.bugs.length
    ? {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        mainEntity: data.bugs.slice(0, 20).map((b) => ({
          "@type": "Question",
          name: `Is there a bug in ${pkg}${b.affected_version ? " " + b.affected_version : ""}?`,
          acceptedAnswer: {
            "@type": "Answer",
            text: b.fixed_version
              ? `${b.title}${b.description ? " " + b.description : ""} Fixed in ${pkg} ${b.fixed_version}.`
              : `${b.title}${b.description ? " " + b.description : ""}`,
          },
        })),
      }
    : null;

  const curlCmd = `curl https://depscope.dev/api/bugs/${ecoLower}/${pkg}`;

  // Content-density gate: mirror the generateMetadata threshold.
  const shouldIndex = (data?.total ?? 0) >= SEO_MIN_BUGS;
  const canonicalHref = shouldIndex
    ? `https://depscope.dev/bugs/${ecoLower}/${pkg}`
    : `https://depscope.dev/pkg/${ecoLower}/${pkg}`;

  return (
    <div className="min-h-screen">
      <head>
        <meta
          name="robots"
          content={shouldIndex
            ? "index, follow, max-snippet:-1, max-image-preview:large"
            : "noindex, follow"}
        />
        <link rel="canonical" href={canonicalHref} />
        <link rel="alternate" type="application/json" href={`https://depscope.dev/api/bugs/${ecoLower}/${pkg}`} />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbLd) }}
        />
        {faqLd && (
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(faqLd) }}
          />
        )}
      </head>

      <main className="max-w-6xl mx-auto px-4 py-8 space-y-4">
        <nav className="text-xs text-[var(--text-dim)] font-mono">
          <Link href="/" className="hover:text-[var(--accent)] transition">depscope</Link>
          <span className="mx-1.5 text-[var(--text-faded)]">/</span>
          <Link href="/explore/bugs" className="hover:text-[var(--accent)] transition">bugs</Link>
          <span className="mx-1.5 text-[var(--text-faded)]">/</span>
          <Link href={`/ecosystems/${ecoLower}`} className="hover:text-[var(--accent)] transition">
            {ecoLower}
          </Link>
          <span className="mx-1.5 text-[var(--text-faded)]">/</span>
          <span className="text-[var(--text)]">{pkg}</span>
        </nav>

        {!shouldIndex && (
          <div className="text-xs rounded border border-[var(--border)] bg-[var(--bg-input)] px-3 py-2 text-[var(--text-dim)]">
            This package has limited bug data ({data?.total ?? 0} entr{(data?.total ?? 0) === 1 ? "y" : "ies"}).
            Check back later or see the{" "}
            <Link href={`/pkg/${ecoLower}/${pkg}`} className="text-[var(--accent)] hover:underline">
              package health page
            </Link>{" "}
            for the full signal.
          </div>
        )}

        <Card>
          <CardBody>
            <div className="flex items-start justify-between gap-6 flex-wrap">
              <div className="flex-1 min-w-[260px]">
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <h1 className="text-2xl font-semibold tracking-tight">
                    {pkg} <span className="text-[var(--text-dim)] font-normal">known bugs</span>
                  </h1>
                  <Badge variant="accent">{ecoLower}</Badge>
                </div>
                <p className="text-sm text-[var(--text-dim)] max-w-2xl leading-relaxed">
                  {data && data.total > 0
                    ? `${data.total} known bug${data.total === 1 ? "" : "s"} in ${pkg}, with affected versions, fixes and workarounds. Sourced from upstream issue trackers.`
                    : `No known bugs currently indexed for ${pkg}.`}
                </p>
                <div className="mt-3 flex flex-wrap gap-3 text-xs text-[var(--text-dim)]">
                  <Link
                    href={`/pkg/${ecoLower}/${pkg}`}
                    className="text-[var(--accent)] hover:underline"
                  >
                    View package health \u2192
                  </Link>
                  <Link
                    href={`/breaking/${ecoLower}/${pkg}`}
                    className="text-[var(--accent)] hover:underline"
                  >
                    Breaking changes \u2192
                  </Link>
                </div>
              </div>
              <div className="text-center shrink-0">
                <div
                  className="text-4xl font-semibold tabular-nums tracking-tight"
                  style={{ color: (data?.total ?? 0) > 0 ? "var(--orange)" : "var(--green)" }}
                >
                  {data?.total ?? 0}
                </div>
                <div className="text-[10px] text-[var(--text-dim)] uppercase tracking-wider mt-1">
                  bugs
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {data && data.bugs.length > 0 ? (
          <Card>
            <CardHeader>
              <span className="text-sm font-medium">Known bugs</span>
            </CardHeader>
            <Table>
              <Thead>
                <Tr>
                  <Th className="w-24">Severity</Th>
                  <Th className="w-28">Affected</Th>
                  <Th className="w-28">Fixed in</Th>
                  <Th>Title</Th>
                  <Th className="w-24">Status</Th>
                  <Th className="w-20">Source</Th>
                </Tr>
              </Thead>
              <Tbody>
                {data.bugs.map((b) => (
                  <Tr key={b.id}>
                    <Td className="whitespace-nowrap">
                      {b.severity ? <SeverityBadge severity={b.severity} /> : <span className="text-[var(--text-dim)]">\u2014</span>}
                    </Td>
                    <Td className="font-mono text-xs whitespace-nowrap">
                      {b.affected_version || <span className="text-[var(--text-dim)]">any</span>}
                    </Td>
                    <Td className="font-mono text-xs whitespace-nowrap">
                      {b.fixed_version ? (
                        <span className="text-[var(--green)]">{b.fixed_version}</span>
                      ) : (
                        <span className="text-[var(--text-dim)]">\u2014</span>
                      )}
                    </Td>
                    <Td>
                      <div className="text-sm text-[var(--text)]">{b.title}</div>
                      {b.description && (
                        <div className="text-xs text-[var(--text-dim)] mt-0.5 line-clamp-2">
                          {b.description}
                        </div>
                      )}
                    </Td>
                    <Td className="whitespace-nowrap text-xs">
                      {b.status ? (
                        <Badge variant={b.status === "closed" ? "success" : "warning"}>{b.status}</Badge>
                      ) : (
                        <span className="text-[var(--text-dim)]">\u2014</span>
                      )}
                    </Td>
                    <Td className="whitespace-nowrap">
                      {b.source_url ? (
                        <a
                          href={b.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-[var(--accent)] hover:underline font-mono"
                        >
                          {b.bug_id || b.source || "link"}
                        </a>
                      ) : (
                        <span className="text-xs text-[var(--text-dim)] font-mono">{b.bug_id || "\u2014"}</span>
                      )}
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Card>
        ) : (
          <Card>
            <CardBody>
              <p className="text-sm text-[var(--text-dim)]">
                No bugs recorded for <span className="font-mono text-[var(--text)]">{pkg}</span>.
              </p>
              <p className="text-xs text-[var(--text-dim)] mt-2">
                See the <Link href={`/pkg/${ecoLower}/${pkg}`} className="text-[var(--accent)] hover:underline">package health page</Link> for vulnerabilities and overall risk.
              </p>
            </CardBody>
          </Card>
        )}

        <Card>
          <CardHeader>
            <span className="text-sm font-medium">API access</span>
          </CardHeader>
          <CardBody>
            <p className="text-xs text-[var(--text-dim)] mb-2">
              Get this data programmatically \u2014 free, no authentication.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-[var(--bg-input)] border border-[var(--border)] rounded px-3 py-2 text-xs text-[var(--accent)] font-mono overflow-x-auto">
                {curlCmd}
              </code>
              <CopyButton text={curlCmd} />
            </div>
          </CardBody>
        </Card>
      </main>

      <Footer />
    </div>
  );
}
