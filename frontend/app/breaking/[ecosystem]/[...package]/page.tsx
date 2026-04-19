import { Metadata } from "next";
import Link from "next/link";
import {
  Card,
  CardBody,
  CardHeader,
  Badge,
  Footer,
} from "../../../../components/ui";
import { CopyButton } from "../../../../components/CopyButton";

interface BreakingChange {
  from_version: string;
  to_version: string;
  change_type: string;
  description: string;
  migration_hint: string | null;
}

interface BreakingPayload {
  ecosystem: string;
  package: string;
  from_version: string | null;
  to_version: string | null;
  changes: BreakingChange[];
  total: number;
  note: string;
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

async function fetchBreaking(ecosystem: string, pkg: string): Promise<BreakingPayload | null> {
  try {
    const res = await fetch(
      `http://127.0.0.1:8000/api/breaking/${ecosystem}/${pkg}`,
      { next: { revalidate: 3600 } },
    );
    if (!res.ok) return null;
    return (await res.json()) as BreakingPayload;
  } catch {
    return null;
  }
}

type Props = {
  params: Promise<{ ecosystem: string; package: string[] }>;
};

// SEO quality gate: pages with < 3 breaking changes get noindex + canonical
// consolidated on /pkg/{eco}/{name} to avoid thin-content penalty.
const SEO_MIN_BREAKING = 3;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { ecosystem, package: pkgParts } = await params;
  const pkg = pkgParts.join("/");
  const data = await fetchBreaking(ecosystem, pkg);
  const count = data?.total ?? 0;

  const shouldIndex = count >= SEO_MIN_BREAKING;

  const transitions = data && data.changes.length
    ? Array.from(new Set(data.changes.map((c) => `${c.from_version} \u2192 ${c.to_version}`))).slice(0, 3).join(", ")
    : null;

  const title = count
    ? `${pkg} breaking changes \u2014 ${ECO_LABEL[ecosystem] || ecosystem} migration guide`
    : `${pkg} \u2014 no breaking changes recorded | DepScope`;
  const description = count
    ? `${count} breaking changes in ${pkg}. Migration guide${transitions ? " for " + transitions : ""}. DepScope curated data for AI coding agents.`
    : `No major-version breaking changes recorded for ${pkg}. See package health on DepScope.`;

  // When thin, consolidate canonical on the package health page.
  const canonical = shouldIndex
    ? `https://depscope.dev/breaking/${ecosystem}/${pkg}`
    : `https://depscope.dev/pkg/${ecosystem}/${pkg}`;

  return {
    title,
    description,
    keywords: [
      pkg, ecosystem, "breaking changes", "migration guide",
      `${pkg} breaking changes`, `${pkg} migration`, `${pkg} upgrade`,
      `${pkg} major version`,
    ],
    openGraph: {
      title,
      description,
      url: `https://depscope.dev/breaking/${ecosystem}/${pkg}`,
      siteName: "DepScope",
      type: "article",
      images: [
        {
          url: `https://depscope.dev/og/pkg/${ecosystem}/${pkg}`,
          width: 1200,
          height: 630,
          alt: `${pkg} breaking changes on DepScope`,
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

export default async function BreakingDetailPage({ params }: Props) {
  const { ecosystem, package: pkgParts } = await params;
  const pkg = pkgParts.join("/");
  const ecoLower = ecosystem.toLowerCase();
  const validEco = ECOSYSTEMS.includes(ecoLower);
  const data = validEco ? await fetchBreaking(ecoLower, pkg) : null;

  const breadcrumbLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "DepScope", item: "https://depscope.dev" },
      { "@type": "ListItem", position: 2, name: "Breaking Changes", item: "https://depscope.dev/explore/breaking" },
      { "@type": "ListItem", position: 3, name: ECO_LABEL[ecoLower] || ecoLower, item: `https://depscope.dev/ecosystems/${ecoLower}` },
      { "@type": "ListItem", position: 4, name: pkg },
    ],
  };

  const howToLd = data && data.changes.length
    ? {
        "@context": "https://schema.org",
        "@type": "HowTo",
        name: `How to migrate ${pkg} across major versions`,
        description: `Step-by-step guide for ${data.changes.length} breaking changes in ${pkg}.`,
        totalTime: "PT30M",
        step: data.changes.slice(0, 20).map((c, i) => ({
          "@type": "HowToStep",
          position: i + 1,
          name: `${c.from_version} \u2192 ${c.to_version}: ${c.change_type}`,
          text: c.migration_hint
            ? `${c.description} Migration: ${c.migration_hint}`
            : c.description,
        })),
      }
    : null;

  const curlCmd = `curl https://depscope.dev/api/breaking/${ecoLower}/${pkg}`;

  // Content-density gate: mirror the generateMetadata threshold so the in-body
  // robots tag and UI note stay consistent with the HTTP-level signal.
  const shouldIndex = (data?.total ?? 0) >= SEO_MIN_BREAKING;
  const canonicalHref = shouldIndex
    ? `https://depscope.dev/breaking/${ecoLower}/${pkg}`
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
        <link rel="alternate" type="application/json" href={`https://depscope.dev/api/breaking/${ecoLower}/${pkg}`} />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbLd) }}
        />
        {howToLd && (
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(howToLd) }}
          />
        )}
      </head>

      <main className="max-w-6xl mx-auto px-4 py-8 space-y-4">
        <nav className="text-xs text-[var(--text-dim)] font-mono">
          <Link href="/" className="hover:text-[var(--accent)] transition">depscope</Link>
          <span className="mx-1.5 text-[var(--text-faded)]">/</span>
          <Link href="/explore/breaking" className="hover:text-[var(--accent)] transition">breaking</Link>
          <span className="mx-1.5 text-[var(--text-faded)]">/</span>
          <Link href={`/ecosystems/${ecoLower}`} className="hover:text-[var(--accent)] transition">
            {ecoLower}
          </Link>
          <span className="mx-1.5 text-[var(--text-faded)]">/</span>
          <span className="text-[var(--text)]">{pkg}</span>
        </nav>

        {!shouldIndex && (
          <div className="text-xs rounded border border-[var(--border)] bg-[var(--bg-input)] px-3 py-2 text-[var(--text-dim)]">
            This package has limited breaking-change data ({data?.total ?? 0} entr{(data?.total ?? 0) === 1 ? "y" : "ies"}).
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
                    {pkg} <span className="text-[var(--text-dim)] font-normal">breaking changes</span>
                  </h1>
                  <Badge variant="accent">{ecoLower}</Badge>
                </div>
                <p className="text-sm text-[var(--text-dim)] max-w-2xl leading-relaxed">
                  {data && data.total > 0
                    ? `${data.total} curated breaking change${data.total === 1 ? "" : "s"} across major versions of ${pkg}. Use this as a migration checklist before bumping dependencies.`
                    : `No breaking changes currently recorded for ${pkg}. Check back after the next major release.`}
                </p>
                <div className="mt-3 flex flex-wrap gap-3 text-xs text-[var(--text-dim)]">
                  <Link
                    href={`/pkg/${ecoLower}/${pkg}`}
                    className="text-[var(--accent)] hover:underline"
                  >
                    View package health \u2192
                  </Link>
                  <Link
                    href={`/bugs/${ecoLower}/${pkg}`}
                    className="text-[var(--accent)] hover:underline"
                  >
                    Known bugs \u2192
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
                  changes
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {data && data.changes.length > 0 ? (
          <Card>
            <CardHeader>
              <span className="text-sm font-medium">Breaking changes by transition</span>
            </CardHeader>
            <CardBody>
              <ul className="space-y-4">
                {data.changes.map((c, i) => (
                  <li
                    key={i}
                    className="border-l-2 border-[var(--border)] hover:border-[var(--accent)]/60 pl-4 transition"
                  >
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="font-mono text-sm text-[var(--text)]">
                        {c.from_version} <span className="text-[var(--text-dim)]">\u2192</span> {c.to_version}
                      </span>
                      <Badge variant="warning">{c.change_type}</Badge>
                    </div>
                    <p className="text-sm text-[var(--text)] leading-relaxed">
                      {c.description}
                    </p>
                    {c.migration_hint && (
                      <div className="mt-2 p-3 bg-[var(--bg-input)] border border-[var(--border)] rounded">
                        <div className="text-[10px] uppercase tracking-wider text-[var(--text-dim)] mb-1 font-mono">
                          Migration
                        </div>
                        <p className="text-xs text-[var(--text)] font-mono whitespace-pre-wrap break-words">
                          {c.migration_hint}
                        </p>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </CardBody>
          </Card>
        ) : (
          <Card>
            <CardBody>
              <p className="text-sm text-[var(--text-dim)]">
                No breaking changes recorded for <span className="font-mono text-[var(--text)]">{pkg}</span>.
              </p>
              <p className="text-xs text-[var(--text-dim)] mt-2">
                This either means the package has a strong backwards-compatibility policy, or we have not indexed its major transitions yet.
                See the <Link href={`/pkg/${ecoLower}/${pkg}`} className="text-[var(--accent)] hover:underline">package health page</Link> for other signals.
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
