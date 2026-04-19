import { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import {
  BundleTypescriptCard,
  HealthHistorySection,
  DependencyTreeSection,
  LicenseAuditSection,
} from "./package-extras";
import {
  Card,
  CardBody,
  CardHeader,
  Badge,
  SeverityBadge,
  ActionBadge,
  Table,
  Thead,
  Tbody,
  Th,
  Td,
  Tr,
  Footer,
} from "../../../../components/ui";
import { CopyButton } from "../../../../components/CopyButton";

interface HealthBreakdown {
  maintenance: number;
  popularity: number;
  security: number;
  maturity: number;
  community: number;
}

interface Vulnerability {
  vuln_id: string;
  severity: string;
  summary: string;
  fixed_version: string | null;
}

interface Recommendation {
  action: string;
  issues: string[];
  use_version: string;
  version_hint: string | null;
  summary: string;
}

interface PackageData {
  package: string;
  ecosystem: string;
  latest_version: string;
  description: string;
  license: string;
  homepage: string;
  repository: string;
  downloads_weekly: number;
  health: {
    score: number;
    risk: string;
    breakdown: HealthBreakdown;
    deprecated: boolean;
  };
  vulnerabilities: {
    count: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
    details: Vulnerability[];
  };
  versions: {
    latest: string;
    total_count: number;
    recent: string[];
  };
  metadata: {
    deprecated: boolean;
    deprecated_message: string | null;
    maintainers_count: number;
    last_published: string;
    first_published: string;
    dependencies_count: number;
    dependencies: string[];
  };
  recommendation?: Recommendation;
  bundle?: {
    size_kb: number;
    gzip_kb: number;
    dependency_count: number;
    has_js_module: boolean;
    has_side_effects: boolean;
    scoped: boolean;
    source: string;
  } | null;
  typescript?: {
    score: number;
    has_types: boolean;
    types_source: string;
    types_package: string | null;
  } | null;
}

function buildRecommendation(data: PackageData): Recommendation {
  if (data.recommendation) return data.recommendation;

  const score = data?.health?.score ?? 0;
  const vulns = data.vulnerabilities;
  const deprecated = data.metadata?.deprecated || data.health?.deprecated || false;
  const issues: string[] = [];
  let action = "safe_to_use";

  if (deprecated) {
    issues.push("Package is deprecated");
    action = "find_alternative";
  }
  if (score < 40) {
    issues.push(`Low health score (${score}/100)`);
    action = "use_with_caution";
  }
  if (vulns.critical > 0) {
    issues.push(`${vulns.critical} critical vulnerabilities`);
    action = "do_not_use";
  } else if (vulns.high > 0) {
    issues.push(`${vulns.high} high severity vulnerabilities`);
    action = "update_required";
  }

  const name = data.package;
  const ver = data.latest_version;
  const summaries: Record<string, string> = {
    safe_to_use: `${name}@${ver} is safe to use (health: ${score}/100)`,
    update_required: `${name}@${ver} has vulnerabilities — update to latest`,
    use_with_caution: `${name}@${ver} low health (${score}/100) — consider alternatives`,
    find_alternative: `${name} is deprecated — find an alternative`,
    do_not_use: `${name} has critical vulnerabilities — do not use`,
  };

  return {
    action,
    issues,
    use_version: ver,
    version_hint: null,
    summary: summaries[action] || `${name}@${ver} — health: ${score}/100`,
  };
}

async function fetchPackage(ecosystem: string, pkg: string): Promise<PackageData | null> {
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/check/${ecosystem}/${pkg}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

interface SimilarEntry { ecosystem: string; name: string; downloads_weekly?: number }
async function fetchSimilar(ecosystem: string, excludePkg: string): Promise<SimilarEntry[]> {
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/sitemap-packages?order=downloads&limit=60`, { next: { revalidate: 3600 } });
    if (!res.ok) return [];
    const all: SimilarEntry[] = await res.json();
    return all.filter((p) => p.ecosystem === ecosystem && p.name !== excludePkg).slice(0, 6);
  } catch {
    return [];
  }
}

type Props = {
  params: Promise<{ ecosystem: string; package: string[] }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { ecosystem, package: pkgParts } = await params;
  const pkg = pkgParts.join("/");
  const data = await fetchPackage(ecosystem, pkg);

  if (!data) {
    return { title: `${pkg} — Not Found | DepScope` };
  }

  const score = data?.health?.score ?? 0;
  const vulnCount = data?.vulnerabilities?.count ?? 0;
  const rec = buildRecommendation(data);
  const safeText = rec.action === "safe_to_use" ? "Safe to use" :
    rec.action === "do_not_use" ? "Not recommended" :
    rec.action === "update_required" ? "Update required" :
    rec.action === "find_alternative" ? "Find alternative" : "Use with caution";

  const title = `${pkg} — Health Score ${score}/100 | DepScope`;
  const description = `${pkg} ${data.latest_version} for ${ecosystem}: health score ${score}/100, ${vulnCount} vulnerabilit${vulnCount === 1 ? "y" : "ies"}. ${safeText}. Checked by DepScope.`;

  return {
    title,
    description,
    keywords: [pkg, ecosystem, "package health", "vulnerability check", "dependency audit", `${pkg} security`, `${pkg} vulnerabilities`, `is ${pkg} safe`],
    openGraph: {
      title,
      description,
      url: `https://depscope.dev/pkg/${ecosystem}/${pkg}`,
      siteName: "DepScope",
      type: "website",
      images: [
        {
          url: `https://depscope.dev/og/pkg/${ecosystem}/${pkg}`,
          width: 1200,
          height: 630,
          alt: `${pkg} — health ${score}/100 on DepScope`,
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
      canonical: `https://depscope.dev/pkg/${ecosystem}/${pkg}`,
    },
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        "max-snippet": -1,
        "max-image-preview": "large",
      },
    },
  };
}

export default async function PackagePage({ params }: Props) {
  const { ecosystem, package: pkgParts } = await params;
  const pkg = pkgParts.join("/");

  if (!["npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"].includes(ecosystem)) {
    notFound();
  }

  const data = await fetchPackage(ecosystem, pkg);

  if (!data) {
    notFound();
  }

  const rec = buildRecommendation(data);
  const score = data?.health?.score ?? 0;
  const similar = await fetchSimilar(ecosystem, data.package);
  const scoreColor =
    score >= 80 ? "var(--green)" :
    score >= 60 ? "var(--yellow)" :
    score >= 40 ? "var(--orange)" :
    "var(--red)";

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": data.package,
    "applicationCategory": "DeveloperApplication",
    "operatingSystem": "Any",
    "softwareVersion": data.latest_version,
    "description": data.description,
    "license": data.license || undefined,
    "url": data.homepage || data.repository || `https://depscope.dev/pkg/${ecosystem}/${pkg}`,
    "downloadUrl": ecosystem === "npm" ? `https://www.npmjs.com/package/${pkg}` :
      ecosystem === "pypi" ? `https://pypi.org/project/${pkg}/` :
      `https://crates.io/crates/${pkg}`,
    "aggregateRating": {
      "@type": "AggregateRating",
      "ratingValue": score,
      "bestRating": 100,
      "worstRating": 0,
      "ratingCount": 1,
      "reviewCount": 1,
    },
    "review": {
      "@type": "Review",
      "author": {
        "@type": "Organization",
        "name": "DepScope",
        "url": "https://depscope.dev",
      },
      "reviewRating": {
        "@type": "Rating",
        "ratingValue": score,
        "bestRating": 100,
        "worstRating": 0,
      },
      "reviewBody": rec.summary,
    },
    "offers": {
      "@type": "Offer",
      "price": "0",
      "priceCurrency": "USD",
    },
  };

  const sourceCodeLd = {
    "@context": "https://schema.org",
    "@type": "SoftwareSourceCode",
    "name": data.package,
    "description": data.description || undefined,
    "programmingLanguage":
      ecosystem === "npm" ? "JavaScript" :
      ecosystem === "pypi" ? "Python" :
      ecosystem === "cargo" ? "Rust" :
      ecosystem === "go" ? "Go" :
      ecosystem === "maven" ? "Java" :
      ecosystem === "nuget" ? "C#" :
      ecosystem === "rubygems" ? "Ruby" :
      ecosystem === "composer" ? "PHP" :
      ecosystem === "pub" ? "Dart" :
      ecosystem === "hex" ? "Elixir" :
      ecosystem === "swift" ? "Swift" :
      ecosystem === "cocoapods" ? "Objective-C" :
      ecosystem === "cpan" ? "Perl" :
      ecosystem === "hackage" ? "Haskell" :
      ecosystem === "cran" ? "R" :
      "Unknown",
    "codeRepository": data.repository || undefined,
    "license": data.license || undefined,
    "version": data.latest_version,
    "url": `https://depscope.dev/pkg/${ecosystem}/${pkg}`,
  };

  const ecoLabel: Record<string, string> = {
    npm: "npm", pypi: "PyPI", cargo: "Cargo", go: "Go",
    composer: "Composer", maven: "Maven", nuget: "NuGet",
    rubygems: "RubyGems", pub: "Pub", hex: "Hex",
    swift: "Swift", cocoapods: "CocoaPods", cpan: "CPAN",
    hackage: "Hackage", cran: "CRAN", conda: "Conda", homebrew: "Homebrew",
  };

  const breadcrumbLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      { "@type": "ListItem", "position": 1, "name": "DepScope", "item": "https://depscope.dev" },
      { "@type": "ListItem", "position": 2, "name": ecoLabel[ecosystem] || ecosystem, "item": `https://depscope.dev/ecosystems/${ecosystem}` },
      { "@type": "ListItem", "position": 3, "name": data.package },
    ],
  };

  const curlCmd = `curl https://depscope.dev/api/check/${ecosystem}/${data.package}`;

  return (
    <div className="min-h-screen">
      <head>
        <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large" />
        <link rel="alternate" type="application/json" href={`https://depscope.dev/api/check/${ecosystem}/${pkg}`} />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(sourceCodeLd) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbLd) }}
        />
      </head>

      <main className="max-w-6xl mx-auto px-4 py-8 space-y-4">
        {/* Breadcrumb */}
        <nav className="text-xs text-[var(--text-dim)] font-mono">
          <Link href="/" className="hover:text-[var(--accent)] transition">depscope</Link>
          <span className="mx-1.5 text-[var(--text-faded)]">/</span>
          <Link href={`/ecosystems/${ecosystem}`} className="hover:text-[var(--accent)] transition">
            {ecosystem}
          </Link>
          <span className="mx-1.5 text-[var(--text-faded)]">/</span>
          <span className="text-[var(--text)]">{data.package}</span>
        </nav>

        {/* Header card */}
        <Card>
          <CardBody>
            <div className="flex items-start justify-between gap-6 flex-wrap">
              <div className="flex-1 min-w-[260px]">
                <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                  <h1 className="text-2xl font-semibold tracking-tight">{data.package}</h1>
                  <Badge variant="accent">{ecosystem}</Badge>
                  <span className="text-sm text-[var(--text-dim)] font-mono tabular-nums">
                    v{data.latest_version}
                  </span>
                  {data.metadata?.deprecated && (
                    <Badge variant="danger">deprecated</Badge>
                  )}
                </div>
                <p className="text-sm text-[var(--text-dim)] mb-3 max-w-2xl leading-relaxed">
                  {data.description}
                </p>
                <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-[var(--text-dim)]">
                  {data.license && (
                    <span>
                      License <span className="text-[var(--text)] font-mono">{data.license}</span>
                    </span>
                  )}
                  <span className="tabular-nums">
                    <span className="text-[var(--text)] font-mono">{data?.versions?.total_count ?? 0}</span> versions
                  </span>
                  {(data?.metadata?.maintainers_count ?? 0) > 0 && (
                    <span className="tabular-nums">
                      <span className="text-[var(--text)] font-mono">{data?.metadata?.maintainers_count ?? 0}</span> maintainers
                    </span>
                  )}
                  <span className="tabular-nums">
                    <span className="text-[var(--text)] font-mono">{data?.metadata?.dependencies_count ?? 0}</span> deps
                  </span>
                  {(data?.downloads_weekly ?? 0) > 0 && (
                    <span className="tabular-nums">
                      <span className="text-[var(--text)] font-mono">{(data?.downloads_weekly ?? 0).toLocaleString()}</span> weekly dl
                    </span>
                  )}
                </div>
                {data.repository && (
                  <a
                    href={data.repository}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-[var(--accent)] hover:underline mt-3 inline-block font-mono"
                  >
                    {data.repository.replace("https://github.com/", "")}
                  </a>
                )}
              </div>
              <div className="text-center shrink-0">
                <div className="text-4xl font-semibold tabular-nums tracking-tight" style={{ color: scoreColor }}>
                  {score}
                </div>
                <div className="text-[10px] text-[var(--text-dim)] font-mono">/ 100</div>
                <div className="text-[10px] text-[var(--text-dim)] uppercase tracking-wider mt-1">
                  Health
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Recommendation */}
        <Card>
          <CardBody className="flex items-start gap-3">
            <ActionBadge action={rec.action} />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-[var(--text)]">{rec.summary}</p>
              {rec.version_hint && (
                <p className="text-xs text-[var(--text-dim)] mt-1">{rec.version_hint}</p>
              )}
              {rec.issues.length > 0 && (
                <ul className="mt-2 text-xs text-[var(--text-dim)] space-y-0.5 list-disc list-inside">
                  {rec.issues.map((issue, i) => (
                    <li key={i}>{issue}</li>
                  ))}
                </ul>
              )}
            </div>
          </CardBody>
        </Card>

        {/* Health breakdown + vulns summary */}
        <div className="grid md:grid-cols-3 gap-4">
          <Card className="md:col-span-2">
            <CardHeader>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Health breakdown</span>
                <span className="text-[11px] text-[var(--text-dim)] font-mono uppercase tracking-wide">
                  0 – 100
                </span>
              </div>
            </CardHeader>
            <CardBody>
              <div className="grid grid-cols-5 gap-4">
                {Object.entries(data?.health?.breakdown ?? {}).map(([key, value]) => {
                  const max =
                    key === "maintenance" || key === "security" ? 25 :
                    key === "popularity" ? 20 : 15;
                  const pct = ((value as number) / max) * 100;
                  return (
                    <div key={key}>
                      <div className="text-lg font-semibold tabular-nums">
                        {value as number}
                        <span className="text-[10px] text-[var(--text-dim)] font-mono">/{max}</span>
                      </div>
                      <div className="w-full bg-[var(--bg-input)] rounded h-1 my-1.5 overflow-hidden">
                        <div
                          className="h-1 rounded bg-[var(--accent)]"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <div className="text-[10px] text-[var(--text-dim)] uppercase tracking-wide">
                        {key}
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <span className="text-sm font-medium">Vulnerabilities</span>
            </CardHeader>
            <CardBody>
              <div
                className="text-3xl font-semibold tabular-nums mb-3"
                style={{ color: (data?.vulnerabilities?.count ?? 0) > 0 ? "var(--red)" : "var(--green)" }}
              >
                {data?.vulnerabilities?.count ?? 0}
              </div>
              <div className="flex flex-wrap gap-1">
                {(data?.vulnerabilities?.critical ?? 0) > 0 && (
                  <Badge variant="danger">{data?.vulnerabilities?.critical} critical</Badge>
                )}
                {(data?.vulnerabilities?.high ?? 0) > 0 && (
                  <Badge variant="warning">{data?.vulnerabilities?.high} high</Badge>
                )}
                {(data?.vulnerabilities?.medium ?? 0) > 0 && (
                  <Badge variant="warning">{data?.vulnerabilities?.medium} medium</Badge>
                )}
                {(data?.vulnerabilities?.low ?? 0) > 0 && (
                  <Badge variant="success">{data?.vulnerabilities?.low} low</Badge>
                )}
                {(data?.vulnerabilities?.count ?? 0) === 0 && (
                  <Badge variant="success">none known</Badge>
                )}
              </div>
            </CardBody>
          </Card>
        </div>

        {/* Vulns table */}
        {(data?.vulnerabilities?.count ?? 0) > 0 && (
          <Card>
            <CardHeader>
              <span className="text-sm font-medium">Advisories ({data?.vulnerabilities?.count})</span>
            </CardHeader>
            <Table>
              <Thead>
                <Tr>
                  <Th className="w-24">Severity</Th>
                  <Th className="w-40">ID</Th>
                  <Th>Summary</Th>
                  <Th className="w-24">Fixed in</Th>
                </Tr>
              </Thead>
              <Tbody>
                {(data?.vulnerabilities?.details ?? []).slice(0, 20).map((v, i) => (
                  <Tr key={i}>
                    <Td className="whitespace-nowrap">
                      <SeverityBadge severity={v.severity} />
                    </Td>
                    <Td className="font-mono text-xs text-[var(--text-dim)] whitespace-nowrap">
                      {v.vuln_id}
                    </Td>
                    <Td>{v.summary}</Td>
                    <Td className="font-mono text-xs whitespace-nowrap">
                      {v.fixed_version ? (
                        <span className="text-[var(--green)]">{v.fixed_version}</span>
                      ) : (
                        <span className="text-[var(--text-dim)]">—</span>
                      )}
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
            {(data?.vulnerabilities?.count ?? 0) > 20 && (
              <div className="px-4 py-2.5 text-xs text-[var(--text-dim)] text-center border-t border-[var(--border)]">
                ... and {(data?.vulnerabilities?.count ?? 0) - 20} more
              </div>
            )}
          </Card>
        )}

        {/* Bundle & TypeScript (npm only) */}
        {ecosystem === "npm" && (data.bundle || data.typescript) && (
          <BundleTypescriptCard
            bundle={data.bundle ?? null}
            typescript={data.typescript ?? null}
          />
        )}

        {/* Health History */}
        <HealthHistorySection ecosystem={ecosystem} pkg={data.package} />

        {/* Dependency Tree */}
        <DependencyTreeSection ecosystem={ecosystem} pkg={data.package} />

        {/* License Audit */}
        <LicenseAuditSection ecosystem={ecosystem} pkg={data.package} />

        {/* Dependencies list */}
        {(data?.metadata?.dependencies ?? []).length > 0 && (
          <Card>
            <CardHeader>
              <span className="text-sm font-medium">
                Dependencies ({data?.metadata?.dependencies_count ?? 0})
              </span>
            </CardHeader>
            <CardBody>
              <div className="flex flex-wrap gap-1.5">
                {(data?.metadata?.dependencies ?? []).slice(0, 60).map((dep, i) => {
                  const depName = typeof dep === "string" ? dep.split(/[<>=! ]/)[0] : String(dep);
                  return (
                    <Link
                      key={i}
                      href={`/pkg/${ecosystem}/${depName}`}
                      className="px-2 py-0.5 text-xs rounded font-mono text-[var(--text-dim)] bg-[var(--bg-input)] border border-[var(--border)] hover:text-[var(--accent)] hover:border-[var(--accent)]/40 transition"
                    >
                      {depName}
                    </Link>
                  );
                })}
              </div>
            </CardBody>
          </Card>
        )}

        {/* API snippet */}
        <Card>
          <CardHeader>
            <span className="text-sm font-medium">API access</span>
          </CardHeader>
          <CardBody>
            <p className="text-xs text-[var(--text-dim)] mb-2">
              Get this data programmatically — free, no authentication.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-[var(--bg-input)] border border-[var(--border)] rounded px-3 py-2 text-xs text-[var(--accent)] font-mono overflow-x-auto">
                {curlCmd}
              </code>
              <CopyButton text={curlCmd} />
            </div>
          </CardBody>
        </Card>

        {/* Similar packages */}
        {similar.length > 0 && (
          <Card>
            <CardHeader>
              <span className="text-sm font-medium">More from {ecosystem}</span>
            </CardHeader>
            <CardBody>
              <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-2">
                {similar.map((p) => (
                  <Link
                    key={p.name}
                    href={`/pkg/${ecosystem}/${p.name}`}
                    className="group p-2 rounded border border-[var(--border)] hover:border-[var(--accent)]/60 hover:bg-[var(--bg-card)] transition text-sm font-mono"
                  >
                    <span className="text-[var(--text)] group-hover:text-[var(--accent)] transition">{p.name}</span>
                  </Link>
                ))}
              </div>
              <div className="text-xs text-[var(--text-dim)] mt-3">
                <Link className="text-[var(--accent)] hover:underline" href={`/ecosystems/${ecosystem}`}>Browse all {ecosystem} packages →</Link>
              </div>
            </CardBody>
          </Card>
        )}

        {/* Meta footer */}
        <div className="text-[11px] text-[var(--text-faded)] text-center space-y-0.5 pt-4 font-mono">
          {data?.metadata?.first_published && (
            <p>First published · {data?.metadata?.first_published}</p>
          )}
          {data?.metadata?.last_published && (
            <p>Last updated · {data?.metadata?.last_published}</p>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
