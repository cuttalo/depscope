import type { Metadata } from "next";
import Link from "next/link";
import { Card, CardBody, PageHeader, Section, Footer, Badge } from "../../../components/ui";

const TITLE =
  "The State of Package Health: What We Learned Indexing 14,812 Packages Across 17 Ecosystems";
const DESCRIPTION =
  "Real numbers from DepScope's package intelligence database — vulnerabilities in popular packages, deprecated zombies still pulling hundreds of millions of downloads, and how ecosystems stack up on health.";
const DATE_PUBLISHED = "2026-04-19";
const URL = "https://depscope.dev/updates/weekly-report-001";
const OG_IMAGE = "https://depscope.dev/og/weekly-report-001.png";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  openGraph: {
    title: TITLE,
    description: DESCRIPTION,
    url: URL,
    siteName: "DepScope",
    type: "article",
    publishedTime: DATE_PUBLISHED,
    authors: ["DepScope"],
    images: [{ url: OG_IMAGE, width: 1200, height: 630, alt: TITLE }],
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
    images: [OG_IMAGE],
  },
  alternates: { canonical: URL },
  robots: { index: true, follow: true },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "Article",
  headline: TITLE,
  description: DESCRIPTION,
  datePublished: DATE_PUBLISHED,
  dateModified: DATE_PUBLISHED,
  author: { "@type": "Organization", name: "DepScope", url: "https://depscope.dev" },
  publisher: {
    "@type": "Organization",
    name: "DepScope",
    logo: { "@type": "ImageObject", url: "https://depscope.dev/favicon-32x32.png" },
  },
  mainEntityOfPage: { "@type": "WebPage", "@id": URL },
  image: OG_IMAGE,
  keywords:
    "package health, supply chain security, npm vulnerabilities, pypi vulnerabilities, deprecated packages, breaking changes, AI agents",
};

// ---------- data tables (frozen snapshot 2026-04-19) ----------

const HEALTH_BUCKETS = [
  { label: "Critical (< 40)", count: 1980, pct: "13.4%" },
  { label: "Poor (40–59)", count: 6353, pct: "42.9%" },
  { label: "Fair (60–79)", count: 4743, pct: "32.0%" },
  { label: "Good (80+)", count: 1680, pct: "11.3%" },
  { label: "Unknown / unscored", count: 56, pct: "0.4%" },
];

const VULNERABLE_POPULAR = [
  { eco: "npm", name: "next", vulns: 5, dl: 35_930_460 },
  { eco: "pypi", name: "Pillow", vulns: 3, dl: 106_391_425 },
  { eco: "pypi", name: "pip", vulns: 2, dl: 127_105_550 },
  { eco: "pypi", name: "nltk", vulns: 3, dl: 13_395_750 },
  { eco: "pypi", name: "opencv-python", vulns: 2, dl: 10_926_573 },
  { eco: "npm", name: "sequelize", vulns: 2, dl: 2_798_158 },
  { eco: "pypi", name: "pycrypto", vulns: 2, dl: 1_994_633 },
  { eco: "pypi", name: "opencv-contrib-python-headless", vulns: 2, dl: 959_622 },
  { eco: "pypi", name: "lmdb", vulns: 5, dl: 893_100 },
  { eco: "npm", name: "angular", vulns: 9, dl: 524_366 },
  { eco: "pypi", name: "paddlepaddle", vulns: 5, dl: 370_918 },
  { eco: "npm", name: "oauth2-server", vulns: 2, dl: 240_495 },
  { eco: "cargo", name: "rust-crypto", vulns: 3, dl: 216_521 },
];

const ZOMBIES = [
  { name: "mimic-fn", dl: 104_431_747, msg: "Renamed to mimic-function" },
  { name: "pkg-dir", dl: 78_705_523, msg: "Renamed to package-directory" },
  {
    name: "path-is-absolute",
    dl: 76_082_652,
    msg: "No longer relevant — Node.js 0.12 is unmaintained",
  },
  { name: "find-cache-dir", dl: 42_672_386, msg: "Renamed to find-cache-directory" },
  { name: "read-pkg-up", dl: 36_291_504, msg: "Renamed to read-package-up" },
  {
    name: "node-domexception",
    dl: 35_167_032,
    msg: "Use the platform's native DOMException",
  },
  { name: "no-case", dl: 34_918_820, msg: "Use change-case" },
  { name: "p-finally", dl: 29_798_243, msg: "Deprecated" },
  { name: "camel-case", dl: 28_182_607, msg: "Use change-case" },
  { name: "param-case", dl: 27_221_685, msg: "Use change-case" },
  { name: "snake-case", dl: 20_292_295, msg: "Use change-case" },
  {
    name: "lodash.isequal",
    dl: 19_136_778,
    msg: "Use require('node:util').isDeepStrictEqual",
  },
  { name: "lodash.get", dl: 17_431_501, msg: "Use optional chaining (?.)" },
  { name: "querystring", dl: 16_287_294, msg: "Legacy — use URLSearchParams" },
  { name: "prebuild-install", dl: 15_998_022, msg: "No longer maintained" },
];

const WORST_SCORES = [
  { name: "angular (legacy AngularJS)", score: 8, dl: 524_366 },
  { name: "trim-right", score: 15, dl: 3_089_154 },
  { name: "level-concat-iterator", score: 16, dl: 571_283 },
  { name: "crypto (npm shim)", score: 17, dl: 1_537_680 },
  { name: "scmp", score: 20, dl: 3_747_349 },
  { name: "bin-version-check", score: 20, dl: 4_092_095 },
  { name: "path-is-absolute", score: 20, dl: 76_082_652 },
  { name: "p-finally", score: 20, dl: 29_798_243 },
  { name: "querystring", score: 21, dl: 16_287_294 },
  { name: "header-case", score: 23, dl: 12_020_838 },
];

const ECOSYSTEMS = [
  { eco: "Composer", pkgs: 484, avg: 67.6, dep: 21 },
  { eco: "npm", pkgs: 8645, avg: 59.4, dep: 115 },
  { eco: "NuGet", pkgs: 300, avg: 58.5, dep: 6 },
  { eco: "PyPI", pkgs: 3282, avg: 57.1, dep: 0 },
  { eco: "Cargo", pkgs: 1219, avg: 50.7, dep: 0 },
  { eco: "RubyGems", pkgs: 493, avg: 50.5, dep: 0 },
  { eco: "Go", pkgs: 73, avg: 50.3, dep: 0 },
  { eco: "Maven", pkgs: 242, avg: 39.3, dep: 0 },
];

function fmt(n: number) {
  return n.toLocaleString("en-US");
}

// ---------- UI helpers ----------

function H2({ children, id }: { children: React.ReactNode; id: string }) {
  return (
    <h2
      id={id}
      className="text-xl font-semibold text-[var(--text)] mt-10 mb-4 scroll-mt-20"
    >
      {children}
    </h2>
  );
}

function P({ children }: { children: React.ReactNode }) {
  return <p className="text-[var(--text-dim)] leading-7 mb-4">{children}</p>;
}

function Table({ children }: { children: React.ReactNode }) {
  return (
    <div className="overflow-x-auto my-6 border border-[var(--border)] rounded-lg">
      <table className="min-w-full text-sm">{children}</table>
    </div>
  );
}

function Th({ children, align = "left" }: { children: React.ReactNode; align?: "left" | "right" }) {
  return (
    <th
      className={`px-4 py-2 text-[11px] uppercase tracking-wider font-medium text-[var(--text-dim)] border-b border-[var(--border)] ${
        align === "right" ? "text-right" : "text-left"
      }`}
    >
      {children}
    </th>
  );
}

function Td({
  children,
  align = "left",
  mono = false,
}: {
  children: React.ReactNode;
  align?: "left" | "right";
  mono?: boolean;
}) {
  return (
    <td
      className={`px-4 py-2 border-b border-[var(--border)] ${
        align === "right" ? "text-right tabular-nums" : ""
      } ${mono ? "font-mono" : ""}`}
    >
      {children}
    </td>
  );
}

function Code({ children }: { children: React.ReactNode }) {
  return (
    <code className="px-1.5 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border)] text-[13px] font-mono">
      {children}
    </code>
  );
}

function Pre({ children }: { children: React.ReactNode }) {
  return (
    <pre className="my-6 p-4 bg-[var(--bg-card)] border border-[var(--border)] rounded-lg text-xs overflow-x-auto font-mono">
      {children}
    </pre>
  );
}

// ---------- page ----------

export default function WeeklyReport001Page() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <PageHeader
        eyebrow="Weekly Report #001 · Published 2026-04-19"
        title="The State of Package Health"
        description="What we learned indexing 14,812 packages across 17 ecosystems."
        actions={<Badge variant="info">Weekly</Badge>}
      />

      <Section>
        <Card>
          <CardBody>
            <article className="max-w-3xl">
              <blockquote className="border-l-2 border-[var(--accent)] pl-4 my-4 italic text-[var(--text)]">
                <strong>Pillow</strong> alone accounts for 106 million weekly
                downloads. It ships with 3 unpatched vulnerabilities in our
                index.{" "}
                <Code>path-is-absolute</Code> has a health score of 20 out of
                100, is officially deprecated, and is downloaded 76 million
                times per week.
              </blockquote>

              <P>
                Those two facts are not outliers. They are representative.
                We&apos;ve spent the last several months indexing{" "}
                <strong>14,812 packages across 17 ecosystems</strong> — npm,
                PyPI, Cargo, Go, Maven, NuGet, RubyGems, Composer, Pub, Hex,
                Swift, CocoaPods, CPAN, Hackage, CRAN, Conda, Homebrew — and
                running the same health pipeline against each one. This is a
                report on what the data actually says. Not marketing.
              </P>

              <H2 id="methodology">Methodology</H2>
              <P>For every package in the index we fetch, on a rolling schedule:</P>
              <ul className="list-disc pl-6 space-y-1 text-[var(--text-dim)] mb-4">
                <li>
                  <strong>Registry metadata</strong> — versions, maintainers,
                  license, publish dates, deprecation flags.
                </li>
                <li>
                  <strong>Weekly/monthly downloads</strong> — from the native
                  registry where exposed.
                </li>
                <li>
                  <strong>Vulnerabilities</strong> — from{" "}
                  <a
                    href="https://osv.dev"
                    className="text-[var(--accent)] underline"
                    target="_blank"
                    rel="noreferrer"
                  >
                    OSV.dev
                  </a>
                  , mapped to affected version ranges.
                </li>
                <li>
                  <strong>Repository stats</strong> — GitHub stars, open
                  issues, last commit, bus-factor proxy.
                </li>
                <li>
                  <strong>Breaking changes</strong> — curated migration notes
                  between major versions.
                </li>
              </ul>
              <P>
                A <Code>health_score</Code> (0–100) is computed from maintenance
                cadence, vulnerability count/severity, deprecation status,
                license clarity, and repository vitality. Scores below 40 are{" "}
                <strong>critical</strong>, 40–59 <strong>poor</strong>, 60–79{" "}
                <strong>fair</strong>, 80+ <strong>good</strong>. No secret
                sauce.
              </P>

              <H2 id="numbers">The Numbers</H2>
              <P>Across the 14,812 packages currently tracked:</P>
              <Table>
                <thead>
                  <tr>
                    <Th>Bucket</Th>
                    <Th align="right">Count</Th>
                    <Th align="right">% of total</Th>
                  </tr>
                </thead>
                <tbody>
                  {HEALTH_BUCKETS.map((b) => (
                    <tr key={b.label}>
                      <Td>{b.label}</Td>
                      <Td align="right">{fmt(b.count)}</Td>
                      <Td align="right">{b.pct}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
              <P>
                <strong>
                  More than half the packages we index score below 60.
                </strong>{" "}
                These are not obscure libraries. The crawler prioritises
                popularity — to be in this index a package generally had to
                clear a download threshold or appear as a dependency of a
                popular one.
              </P>
              <P>
                We also track <strong>400 vulnerabilities</strong> against{" "}
                <strong>72 packages</strong> with more than 1,000,000 weekly
                downloads. Severity breakdown: 221 medium, 179 unknown /
                unclassified by source. (We conservatively surface OSV records
                even when severity is not filled in upstream. Absence of
                severity is not absence of exploitability.)
              </P>

              <H2 id="vulnerable">Popular but Vulnerable</H2>
              <P>
                All of these packages ship more than 100k downloads per week
                and have at least one open advisory in our index:
              </P>
              <Table>
                <thead>
                  <tr>
                    <Th>Ecosystem</Th>
                    <Th>Package</Th>
                    <Th align="right">Vulns</Th>
                    <Th align="right">Weekly downloads</Th>
                  </tr>
                </thead>
                <tbody>
                  {VULNERABLE_POPULAR.map((p) => (
                    <tr key={`${p.eco}-${p.name}`}>
                      <Td>
                        <Badge variant="neutral">{p.eco}</Badge>
                      </Td>
                      <Td mono>
                        <Link
                          href={`/pkg/${p.eco}/${p.name}`}
                          className="text-[var(--accent)] hover:underline"
                        >
                          {p.name}
                        </Link>
                      </Td>
                      <Td align="right">{p.vulns}</Td>
                      <Td align="right">{fmt(p.dl)}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
              <P>
                A few of these are well-known (<Code>next</Code>,{" "}
                <Code>Pillow</Code>, <Code>pip</Code>). A few are quietly
                dangerous: <Code>rust-crypto</Code> has been unmaintained for
                years, <Code>pycrypto</Code> is effectively abandoned in favor
                of <Code>pycryptodome</Code>, and <Code>oauth2-server</Code> —
                which, yes, handles your auth flow — has open advisories and
                minimal upstream activity.
              </P>

              <H2 id="zombies">Zombie Packages</H2>
              <P>
                Packages that registries have <strong>officially marked
                deprecated</strong> but that continue to ship tens to hundreds
                of millions of weekly downloads:
              </P>
              <Table>
                <thead>
                  <tr>
                    <Th>Package</Th>
                    <Th align="right">Weekly downloads</Th>
                    <Th>Why it&apos;s deprecated</Th>
                  </tr>
                </thead>
                <tbody>
                  {ZOMBIES.map((z) => (
                    <tr key={z.name}>
                      <Td mono>
                        <Link
                          href={`/pkg/npm/${z.name}`}
                          className="text-[var(--accent)] hover:underline"
                        >
                          {z.name}
                        </Link>
                      </Td>
                      <Td align="right">{fmt(z.dl)}</Td>
                      <Td>{z.msg}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
              <P>
                <strong>
                  Fifty packages in our index are deprecated and still pull
                  more than 1M weekly downloads. Summed, that&apos;s roughly
                  740 million weekly downloads of code that the authors
                  themselves say you should stop using.
                </strong>{" "}
                Most of this traffic is transitive — a dependency of a
                dependency of a dependency — which is exactly why package
                intelligence needs to be programmatic. No one is auditing{" "}
                <Code>camel-case</Code> by hand in 2026.
              </P>

              <H2 id="worst">Worst-Scoring Popular Packages</H2>
              <P>
                Filtering by weekly downloads &gt; 500,000 and sorting by{" "}
                <Code>health_score</Code> ascending:
              </P>
              <Table>
                <thead>
                  <tr>
                    <Th>Package</Th>
                    <Th align="right">Health</Th>
                    <Th align="right">Weekly downloads</Th>
                  </tr>
                </thead>
                <tbody>
                  {WORST_SCORES.map((w) => (
                    <tr key={w.name}>
                      <Td mono>{w.name}</Td>
                      <Td align="right">
                        <span className="text-red-500 font-medium">
                          {w.score}
                        </span>
                      </Td>
                      <Td align="right">{fmt(w.dl)}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
              <P>
                Note <Code>angular</Code> at <strong>8/100</strong> with half
                a million weekly downloads — that&apos;s AngularJS 1.x, EOL
                since 2022, still installed somewhere new every few seconds.
              </P>

              <H2 id="breaking">Breaking Changes in the Wild</H2>
              <P>
                Seventy-nine curated breaking changes are tracked across
                popular packages. A sample of what&apos;s actively biting
                upgrade PRs this quarter:
              </P>
              <ul className="list-disc pl-6 space-y-2 text-[var(--text-dim)] mb-4">
                <li>
                  <strong>pydantic v1 → v2</strong> — core rewritten in Rust,
                  up to 100x faster, but <Code>@validator</Code> becomes{" "}
                  <Code>@field_validator</Code> (must be classmethod).{" "}
                  <Code>class Config</Code> replaced by{" "}
                  <Code>model_config: ConfigDict</Code>.
                </li>
                <li>
                  <strong>numpy 1 → 2</strong> — cleaned namespace, many
                  aliases removed, tightened mixed-type promotion rules (NEP
                  50).
                </li>
                <li>
                  <strong>pandas 1 → 2</strong> — PyArrow-backed dtypes,
                  copy-on-write opt-in (default in 3.0), nullable dtypes
                  default.
                </li>
                <li>
                  <strong>react 18 → 19</strong> — <Code>ref</Code> is now a
                  regular prop; <Code>forwardRef</Code> no longer required for
                  most function components. String refs removed.{" "}
                  <Code>useFormState</Code> renamed to{" "}
                  <Code>useActionState</Code>.
                </li>
                <li>
                  <strong>eslint 8 → 9</strong> — flat config{" "}
                  (<Code>eslint.config.js</Code>) is the default; legacy{" "}
                  <Code>.eslintrc.*</Code> no longer read. Many formatting
                  rules removed. Node 18.18+ required.
                </li>
                <li>
                  <strong>typescript 4.9 → 5.0</strong> — Node 12.20+
                  required, stage-3 decorators replace experimental ones.
                </li>
                <li>
                  <strong>tokio 0.2 → 1</strong> — stable API, feature flags
                  reorganized.
                </li>
              </ul>
              <P>
                These are the ones agents get wrong. An LLM trained before
                2023 will happily write you a <Code>@validator</Code> on a
                Pydantic 2 model and waste half an hour of your day.
              </P>

              <H2 id="ecosystems">Ecosystem Comparison</H2>
              <P>
                Average <Code>health_score</Code> by ecosystem, for packages
                where a score was computed:
              </P>
              <Table>
                <thead>
                  <tr>
                    <Th>Ecosystem</Th>
                    <Th align="right">Packages scored</Th>
                    <Th align="right">Avg health</Th>
                    <Th align="right">Deprecated</Th>
                  </tr>
                </thead>
                <tbody>
                  {ECOSYSTEMS.map((e) => (
                    <tr key={e.eco}>
                      <Td>{e.eco}</Td>
                      <Td align="right">{fmt(e.pkgs)}</Td>
                      <Td align="right">{e.avg.toFixed(1)}</Td>
                      <Td align="right">{e.dep}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
              <P>Two things jump out:</P>
              <ol className="list-decimal pl-6 space-y-1 text-[var(--text-dim)] mb-4">
                <li>
                  <strong>Composer (PHP) leads.</strong> Surprising to anyone
                  who hasn&apos;t touched PHP since 2012 — the modern Composer
                  ecosystem is small, curated, and actively maintained.
                </li>
                <li>
                  <strong>Maven trails significantly.</strong> The Java
                  ecosystem has a long tail of ancient artifacts still pulled
                  transitively by enterprise stacks. Many score poorly not
                  because they&apos;re buggy but because &quot;maintained&quot;
                  means a commit in 2017.
                </li>
              </ol>
              <P>
                npm, despite dominating in absolute vulnerability count, is
                not the worst on a per-package basis. It&apos;s just the
                biggest — any per-package pathology is magnified by sheer
                volume.
              </P>

              <H2 id="agents">What This Means for AI Agents</H2>
              <P>
                If an AI coding agent suggests <Code>lodash.get</Code> in new
                code, or imports <Code>pycrypto</Code> because that&apos;s
                what its 2022 training data remembers, the resulting code
                review burden falls on <strong>you</strong>. The agent
                doesn&apos;t know <Code>path-is-absolute</Code> was
                deprecated. It doesn&apos;t know pandas 2 shipped
                copy-on-write. It doesn&apos;t know <Code>next</Code> has 5
                open advisories today.
              </P>
              <P>
                This is the gap DepScope is built to close. Every package
                recommendation an agent makes should be checked against live
                data: current version, current health, current
                vulnerabilities, current deprecation status. Not once. Every
                call.
              </P>

              <H2 id="try">Try It Yourself</H2>
              <P>
                All of the data above is queryable without auth:
              </P>
              <Pre>
{`# Health snapshot for a package
curl -s https://depscope.dev/api/check/npm/next | jq '.health_score, .vulnerabilities | length'

# Is it deprecated?
curl -s https://depscope.dev/api/check/npm/path-is-absolute | jq '.deprecated, .deprecated_message'

# Compare alternatives
curl -s https://depscope.dev/api/compare/pypi/pycrypto,pycryptodome | jq '.recommendation'

# Recent breaking changes for a package
curl -s https://depscope.dev/api/breaking/pypi/pydantic | jq '.changes[]'`}
              </Pre>
              <P>
                MCP tools are available for Claude Code and Cursor — the agent
                gets the data without you having to paste it in. See{" "}
                <Link
                  href="/integrate"
                  className="text-[var(--accent)] underline"
                >
                  /integrate
                </Link>
                .
              </P>

              <H2 id="next">Next Report</H2>
              <P>
                This report is generated weekly from live database snapshots.
                Numbers will shift as the index grows and vulnerabilities are
                published. Report #002 lands next Monday.
              </P>
              <P>
                If you want the raw data behind any figure above, every number
                in this article is a single query away in the public{" "}
                <Link
                  href="/api-docs"
                  className="text-[var(--accent)] underline"
                >
                  API
                </Link>
                .
              </P>
            </article>
          </CardBody>
        </Card>
      </Section>

      <Footer />
    </>
  );
}
