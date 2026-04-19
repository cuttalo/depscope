import { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import {
  Card,
  CardBody,
  PageHeader,
  Section,
  Badge,
  Footer,
} from "../../../components/ui";

interface PackageEntry {
  ecosystem: string;
  name: string;
}

interface HealthData {
  package: string;
  health: { score: number; risk: string };
  latest_version: string;
  description: string;
  downloads_weekly?: number;
}

const ECO_LABELS: Record<string, string> = {
  npm: "npm", pypi: "PyPI", cargo: "Cargo", go: "Go",
  composer: "Composer", maven: "Maven", nuget: "NuGet",
  rubygems: "RubyGems", pub: "Pub", hex: "Hex",
  swift: "Swift", cocoapods: "CocoaPods", cpan: "CPAN",
  hackage: "Hackage", cran: "CRAN", conda: "Conda", homebrew: "Homebrew",
};

const ECO_DESC: Record<string, string> = {
  npm: "JavaScript and Node.js packages from the npm registry",
  pypi: "Python packages from the Python Package Index",
  cargo: "Rust crates from the Cargo registry",
  go: "Go modules from the Go module proxy",
  composer: "PHP packages from Packagist",
  maven: "Java/Kotlin/Scala artifacts from Maven Central",
  nuget: ".NET packages from the NuGet gallery",
  rubygems: "Ruby gems from RubyGems.org",
  pub: "Dart and Flutter packages from pub.dev",
  hex: "Elixir and Erlang packages from Hex.pm",
  swift: "Swift packages from the Swift Package Manager ecosystem",
  cocoapods: "iOS/macOS libraries from CocoaPods",
  cpan: "Perl modules from CPAN",
  hackage: "Haskell packages from Hackage",
  cran: "R packages from the Comprehensive R Archive Network",
  conda: "Python/R/C++ packages from conda-forge",
  homebrew: "macOS/Linux formulae from Homebrew",
};

const ECO_LIST = Object.keys(ECO_LABELS);

type Props = {
  params: Promise<{ ecosystem: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { ecosystem } = await params;
  const label = ECO_LABELS[ecosystem] || ecosystem;
  const title = `${label} Packages — Health Scores | DepScope`;
  const description = `Explore ${label} packages with health scores, vulnerability data, and recommendations. ${ECO_DESC[ecosystem] || ""}. Free data by DepScope.`;
  return {
    title,
    description,
    openGraph: { title, description, url: `https://depscope.dev/ecosystems/${ecosystem}`, siteName: "DepScope", type: "website" },
    twitter: { card: "summary", title, description },
    alternates: { canonical: `https://depscope.dev/ecosystems/${ecosystem}` },
    robots: { index: true, follow: true },
  };
}

async function fetchPackages(ecosystem: string): Promise<PackageEntry[]> {
  try {
    const res = await fetch("http://127.0.0.1:8000/api/sitemap-packages", { next: { revalidate: 3600 } });
    if (!res.ok) return [];
    const all: PackageEntry[] = await res.json();
    return all.filter((p) => p.ecosystem === ecosystem);
  } catch {
    return [];
  }
}

async function fetchHealth(ecosystem: string, pkg: string): Promise<HealthData | null> {
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/check/${ecosystem}/${pkg}`, { next: { revalidate: 3600 } });
    if (!res.ok) return null;
    const data = await res.json();
    return {
      package: data.package,
      health: { score: data.health?.score ?? 0, risk: data.health?.risk ?? "unknown" },
      latest_version: data.latest_version,
      description: data.description || "",
    };
  } catch {
    return null;
  }
}

function ScorePill({ score }: { score: number }) {
  const variant =
    score >= 80 ? "success" :
    score >= 60 ? "warning" :
    score >= 40 ? "warning" : "danger";
  return <Badge variant={variant}><span className="tabular-nums font-mono">{score}</span></Badge>;
}

function RiskBadge({ risk }: { risk: string }) {
  const variant =
    risk === "low" ? "success" :
    risk === "medium" ? "warning" :
    risk === "high" ? "danger" : "neutral";
  return <Badge variant={variant}>{risk} risk</Badge>;
}

export default async function EcosystemPage({ params }: Props) {
  const { ecosystem } = await params;
  if (!ECO_LIST.includes(ecosystem)) notFound();

  const packages = await fetchPackages(ecosystem);
  const label = ECO_LABELS[ecosystem];

  const top20 = packages.slice(0, 20);
  const healthResults = await Promise.allSettled(top20.map((p) => fetchHealth(ecosystem, p.name)));
  const healthMap = new Map<string, HealthData>();
  healthResults.forEach((result, i) => {
    if (result.status === "fulfilled" && result.value) {
      healthMap.set(top20[i].name, result.value);
    }
  });

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: `${label} Packages — DepScope`,
    description: ECO_DESC[ecosystem],
    url: `https://depscope.dev/ecosystems/${ecosystem}`,
    mainEntity: {
      "@type": "ItemList",
      numberOfItems: packages.length,
      itemListElement: top20.map((p, i) => ({
        "@type": "ListItem",
        position: i + 1,
        name: p.name,
        url: `https://depscope.dev/pkg/${ecosystem}/${p.name}`,
      })),
    },
  };

  return (
    <div className="min-h-screen">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <nav className="text-xs font-mono text-[var(--text-dim)] mb-4">
          <Link href="/" className="hover:text-[var(--accent)] transition">depscope</Link>
          <span className="mx-1 text-[var(--text-faded)]">/</span>
          <Link href="/popular" className="hover:text-[var(--accent)] transition">ecosystems</Link>
          <span className="mx-1 text-[var(--text-faded)]">/</span>
          <span className="text-[var(--text)]">{ecosystem}</span>
        </nav>

        <PageHeader
          eyebrow={`Ecosystem · ${ecosystem}`}
          title={`${label} packages`}
          description={`${ECO_DESC[ecosystem]}. ${packages.length.toLocaleString()} packages indexed with health scores.`}
        />

        {top20.length > 0 && (
          <Section title="Top packages" description="Highest ranked & most cached" className="mb-10">
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {top20.map((p) => {
                const h = healthMap.get(p.name);
                return (
                  <Link key={p.name} href={`/pkg/${ecosystem}/${p.name}`} className="group">
                    <Card className="h-full hover:border-[var(--accent)]/40 transition">
                      <CardBody>
                        <div className="flex items-center justify-between mb-2 gap-2">
                          <h3 className="font-mono text-sm text-[var(--text)] truncate group-hover:text-[var(--accent)] transition">
                            {p.name}
                          </h3>
                          {h && <ScorePill score={h.health.score} />}
                        </div>
                        {h && (
                          <>
                            <p className="text-xs text-[var(--text-dim)] line-clamp-2 mb-2">{h.description}</p>
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-xs font-mono tabular-nums text-[var(--text-dim)]">v{h.latest_version}</span>
                              <RiskBadge risk={h.health.risk} />
                            </div>
                          </>
                        )}
                      </CardBody>
                    </Card>
                  </Link>
                );
              })}
            </div>
          </Section>
        )}

        {packages.length > 20 && (
          <Section title={`All ${label} packages`} description={`${packages.length.toLocaleString()} indexed`} className="mb-10">
            <Card>
              <CardBody>
                <div className="flex flex-wrap gap-1.5">
                  {packages.slice(20).map((p) => (
                    <Link
                      key={p.name}
                      href={`/pkg/${ecosystem}/${p.name}`}
                      className="px-2.5 py-1 text-xs rounded-full bg-[var(--bg-input)] text-[var(--text-dim)] hover:text-[var(--accent)] hover:bg-[var(--accent)]/10 transition border border-[var(--border)] font-mono"
                    >
                      {p.name}
                    </Link>
                  ))}
                </div>
              </CardBody>
            </Card>
          </Section>
        )}

        <Section title="Other ecosystems">
          <Card>
            <CardBody>
              <div className="flex flex-wrap gap-2">
                {ECO_LIST.filter((e) => e !== ecosystem).map((e) => (
                  <Link
                    key={e}
                    href={`/ecosystems/${e}`}
                    className="px-3 py-1.5 rounded border border-[var(--border)] hover:border-[var(--accent)]/40 hover:text-[var(--accent)] transition text-sm font-mono"
                  >
                    {ECO_LABELS[e]}
                  </Link>
                ))}
              </div>
            </CardBody>
          </Card>
        </Section>
      </main>
      <Footer />
    </div>
  );
}
