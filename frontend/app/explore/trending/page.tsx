import Link from "next/link";
import type { Metadata } from "next";
import {
  Card,
  Table,
  Thead,
  Tbody,
  Th,
  Td,
  Tr,
  Badge,
  PageHeader,
  Section,
  Footer,
} from "../../../components/ui";
import EcosystemFilter from "./EcosystemFilter";

interface TrendingRow {
  ecosystem: string;
  package_name: string;
  call_count: number;
  rank: number;
  rank_change: number;
  week_growth_pct: number;
}

interface TrendingResponse {
  generated_at: string;
  scope: string;
  trending: TrendingRow[];
}

const ECOSYSTEMS = [
  "all", "npm", "pypi", "cargo", "go", "composer", "maven", "nuget",
  "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage",
  "cran", "conda", "homebrew",
];

const ECO_LABELS: Record<string, string> = {
  all: "All ecosystems",
  npm: "npm", pypi: "PyPI", cargo: "Cargo", go: "Go",
  composer: "Composer", maven: "Maven", nuget: "NuGet", rubygems: "RubyGems",
  pub: "Pub", hex: "Hex", swift: "Swift", cocoapods: "CocoaPods",
  cpan: "CPAN", hackage: "Hackage", cran: "CRAN", conda: "Conda", homebrew: "Homebrew",
};

function ArrowUp() {
  return (
    <svg width="10" height="10" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 14V2M8 2l-5 5M8 2l5 5" />
    </svg>
  );
}

function ArrowDown() {
  return (
    <svg width="10" height="10" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 2v12M8 14l-5-5M8 14l5-5" />
    </svg>
  );
}

export async function generateMetadata(
  { searchParams }: { searchParams: Promise<{ ecosystem?: string }> },
): Promise<Metadata> {
  const params = await searchParams;
  const eco = (params.ecosystem || "").toLowerCase();
  const label = eco && ECO_LABELS[eco] ? ECO_LABELS[eco] : "packages";
  return {
    title: `Trending ${label} — DepScope`,
    description: `Packages AI agents are querying most right now. ${
      eco && eco !== "all" ? `Ecosystem: ${eco}.` : "Across 17 ecosystems."
    } Live rank, movement and weekly growth.`,
    alternates: {
      canonical: eco && eco !== "all"
        ? `https://depscope.dev/explore/trending?ecosystem=${eco}`
        : "https://depscope.dev/explore/trending",
    },
  };
}

async function loadTrending(ecosystem: string): Promise<TrendingResponse | null> {
  const qs = ecosystem && ecosystem !== "all" ? `ecosystem=${ecosystem}&` : "";
  const url = `https://depscope.dev/api/trending?${qs}limit=50`;
  try {
    const res = await fetch(url, { next: { revalidate: 300 } });
    if (!res.ok) return null;
    return (await res.json()) as TrendingResponse;
  } catch {
    return null;
  }
}

export default async function TrendingPage(
  { searchParams }: { searchParams: Promise<{ ecosystem?: string }> },
) {
  const params = await searchParams;
  const rawEco = (params.ecosystem || "all").toLowerCase();
  const ecosystem = ECOSYSTEMS.includes(rawEco) ? rawEco : "all";

  const data = await loadTrending(ecosystem);
  const rows = data?.trending ?? [];

  return (
    <div className="min-h-screen">
      <main className="max-w-6xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="Explore · Trending"
          title="What AI agents are searching right now"
          description="Live rank, movement and weekly growth across 17 ecosystems. Server-rendered, cached 5 minutes."
          actions={<EcosystemFilter current={ecosystem} ecosystems={ECOSYSTEMS} labels={ECO_LABELS} />}
        />

        <Section>
          <Card>
            {!data ? (
              <div className="p-8 text-center text-sm text-[var(--red)]">
                Failed to load trending data. Try again in a moment.
              </div>
            ) : rows.length === 0 ? (
              <div className="p-8 text-center text-sm text-[var(--text-dim)]">
                No trending data for this scope.
              </div>
            ) : (
              <Table>
                <Thead>
                  <Tr>
                    <Th className="w-12">#</Th>
                    <Th>Package</Th>
                    <Th>Ecosystem</Th>
                    <Th className="text-right">Rank change</Th>
                    <Th className="text-right">Weekly growth</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {rows.map((r) => {
                    const href = `/pkg/${r.ecosystem}/${r.package_name}`;
                    const growth = r.week_growth_pct ?? 0;
                    const growthColor =
                      growth >= 50 ? "var(--green)" :
                      growth >= 10 ? "var(--accent)" :
                      growth > 0 ? "var(--text)" :
                      growth < 0 ? "var(--red)" :
                      "var(--text-dim)";
                    const change = r.rank_change ?? 0;
                    return (
                      <Tr key={`${r.ecosystem}-${r.package_name}`}>
                        <Td className="tabular-nums text-[var(--text-dim)]">{r.rank}</Td>
                        <Td className="font-mono text-[var(--text)]">
                          <Link href={href} className="hover:text-[var(--accent)] transition">
                            {r.package_name}
                          </Link>
                        </Td>
                        <Td>
                          <Badge variant="accent">{r.ecosystem}</Badge>
                        </Td>
                        <Td className="text-right">
                          {change === 0 ? (
                            <span className="text-[var(--text-dim)] font-mono text-xs">—</span>
                          ) : change > 0 ? (
                            <span className="inline-flex items-center gap-1 text-[var(--green)] font-mono text-xs tabular-nums">
                              <ArrowUp /> {change}
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[var(--red)] font-mono text-xs tabular-nums">
                              <ArrowDown /> {Math.abs(change)}
                            </span>
                          )}
                        </Td>
                        <Td className="text-right tabular-nums font-mono text-xs">
                          <span style={{ color: growthColor }}>
                            {growth > 0 ? "+" : ""}
                            {growth.toFixed(1)}%
                          </span>
                        </Td>
                      </Tr>
                    );
                  })}
                </Tbody>
              </Table>
            )}
          </Card>
          {data?.generated_at && (
            <p className="mt-3 text-[11px] font-mono text-[var(--text-faded)] text-right">
              generated_at {new Date(data.generated_at).toISOString().replace("T", " ").slice(0, 19)} · cache 5min
            </p>
          )}
        </Section>
      </main>
      <Footer />
    </div>
  );
}
