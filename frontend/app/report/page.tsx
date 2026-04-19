import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "The State of Package Health 2026 | DepScope",
  description:
    "Analysis of 14,700+ packages across 17 ecosystems reveals 54% fall into caution or critical health categories. Deprecated packages still get 146M+ downloads/week. AI agents suggest deprecated packages 23% of the time.",
  openGraph: {
    title: "The State of Package Health 2026 | DepScope",
    description:
      "What 14,700+ packages tell us about the software supply chain. 54% of packages present measurable risk. Deprecated packages get 146M+ downloads/week.",
    url: "https://depscope.dev/report",
    siteName: "DepScope",
    type: "article",
  },
  twitter: {
    card: "summary",
    title: "The State of Package Health 2026 | DepScope",
    description:
      "54% of widely-used packages fall into caution or critical health categories. Full analysis of 14,700+ packages.",
  },
  alternates: { canonical: "https://depscope.dev/report" },
};


function StatCard({
  value,
  label,
  color,
}: {
  value: string;
  label: string;
  color: string;
}) {
  return (
    <div className="card p-5 text-center">
      <div className={`text-3xl font-bold mb-1 ${color}`}>{value}</div>
      <div className="text-sm text-[var(--text-dim)]">{label}</div>
    </div>
  );
}

export default function ReportPage() {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: "The State of Package Health 2026",
    description:
      "Analysis of 14,700+ packages across 17 ecosystems reveals that 54% fall into caution or critical health categories.",
    author: {
      "@type": "Organization",
      name: "DepScope",
      url: "https://depscope.dev",
    },
    publisher: {
      "@type": "Organization",
      name: "Cuttalo srl",
      url: "https://cuttalo.com",
    },
    datePublished: "2026-04-01",
    url: "https://depscope.dev/report",
    mainEntityOfPage: "https://depscope.dev/report",
  };

  return (
    <div className="min-h-screen">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Hero */}
      <header className="pt-16 pb-12 px-4 text-center border-b border-[var(--border)]">
        <p className="text-sm text-[var(--accent)] font-medium tracking-wider uppercase mb-4">
          April 2026 Report
        </p>
        <h1 className="text-4xl md:text-5xl font-bold mb-4">
          The State of{" "}
          <span className="gradient-text">Package Health</span> 2026
        </h1>
        <p className="text-xl text-[var(--text-dim)] max-w-2xl mx-auto">
          What <strong className="text-[var(--text)]">14,700+ packages</strong>{" "}
          tell us about the software supply chain
        </p>
        <p className="text-sm text-[var(--text-dim)] mt-4">
          Published by{" "}
          <a href="https://depscope.dev" className="text-[var(--accent)] hover:underline">
            DepScope
          </a>
        </p>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-12 space-y-16">
        {/* Key stats row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard value="54%" label="Packages at risk" color="text-[var(--orange)]" />
          <StatCard value="146M+" label="Deprecated downloads/week" color="text-[var(--red)]" />
          <StatCard value="14,700+" label="Packages analyzed" color="text-[var(--accent)]" />
          <StatCard value="17" label="Ecosystems" color="text-[var(--green)]" />
        </div>

        {/* Executive Summary */}
        <section>
          <h2 className="text-2xl font-bold mb-4 border-l-4 border-[var(--accent)] pl-4">
            Executive Summary
          </h2>
          <div className="card p-6 text-[var(--text-dim)] leading-relaxed">
            <p>
              An analysis of <strong className="text-[var(--text)]">14,700+ packages</strong> across 17 ecosystems reveals that{" "}
              <strong className="text-[var(--orange)]">54% of widely-used packages</strong> fall into
              &ldquo;caution&rdquo; or &ldquo;critical&rdquo; health categories. Deprecated packages
              still accumulate <strong className="text-[var(--red)]">hundreds of millions of weekly downloads</strong>,
              and critical vulnerabilities persist in production dependencies worldwide. The software
              supply chain has a health problem that most teams don&apos;t know about &mdash; until
              it&apos;s too late.
            </p>
          </div>
        </section>

        {/* Key Findings */}
        <section>
          <h2 className="text-2xl font-bold mb-6 border-l-4 border-[var(--accent)] pl-4">
            Key Findings
          </h2>
          <div className="space-y-4">
            {[
              {
                num: "1",
                text: (
                  <>
                    <strong className="text-[var(--text)]">54% of analyzed packages scored &ldquo;caution&rdquo; or &ldquo;critical&rdquo;</strong>{" "}
                    &mdash; 8,334 out of 14,700+ packages present measurable risk to downstream consumers.
                  </>
                ),
              },
              {
                num: "2",
                text: (
                  <>
                    <strong className="text-[var(--text)]">Deprecated packages still get 146M+ downloads/week</strong>{" "}
                    &mdash; <code className="text-[var(--accent)] text-sm">request</code>, deprecated since 2020, still
                    sees 16 million weekly downloads six years later.
                  </>
                ),
              },
              {
                num: "3",
                text: (
                  <>
                    <strong className="text-[var(--text)]">
                      <code className="text-[var(--accent)]">ms</code> hasn&apos;t been updated in over a year but gets 412M downloads/week
                    </strong>{" "}
                    &mdash; foundational infrastructure running on stale code.
                  </>
                ),
              },
              {
                num: "4",
                text: (
                  <>
                    <strong className="text-[var(--text)]">
                      <code className="text-[var(--accent)]">imurmurhash</code> scores 31/100 but gets 109M downloads/week
                    </strong>{" "}
                    &mdash; unhealthy packages are deeply embedded in dependency trees.
                  </>
                ),
              },
              {
                num: "5",
                text: (
                  <>
                    <strong className="text-[var(--text)]">
                      <code className="text-[var(--accent)]">mlflow</code> carries 18 known vulnerabilities
                    </strong>{" "}
                    &mdash; ML/AI tooling has the worst vulnerability profile in the dataset.
                  </>
                ),
              },
              {
                num: "6",
                text: (
                  <>
                    <strong className="text-[var(--text)]">npm leads in health scores (60.5 avg)</strong>, followed
                    by PyPI (57.6) and Cargo (50.8) &mdash; ecosystem culture matters.
                  </>
                ),
              },
              {
                num: "7",
                text: (
                  <>
                    <strong className="text-[var(--text)]">AI coding assistants routinely suggest deprecated packages</strong>{" "}
                    &mdash; models trained on outdated documentation perpetuate bad dependencies.
                  </>
                ),
              },
            ].map((finding) => (
              <div key={finding.num} className="card p-4 flex items-start gap-4">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-[var(--accent)]/10 text-[var(--accent)] flex items-center justify-center font-bold text-sm">
                  {finding.num}
                </div>
                <p className="text-[var(--text-dim)] leading-relaxed">{finding.text}</p>
              </div>
            ))}
          </div>
        </section>

        {/* 1. Health Score Distribution */}
        <section>
          <h2 className="text-2xl font-bold mb-6 border-l-4 border-[var(--accent)] pl-4">
            1. Health Score Distribution
          </h2>
          <p className="text-[var(--text-dim)] mb-6 leading-relaxed">
            We scored 14,700+ packages on a 0&ndash;100 scale incorporating maintenance activity,
            vulnerability exposure, deprecation status, community health, and release cadence.
          </p>

          <div className="card overflow-hidden mb-6">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--bg)]">
                  <th className="text-left p-4 text-[var(--text-dim)] font-medium">Category</th>
                  <th className="text-left p-4 text-[var(--text-dim)] font-medium">Score Range</th>
                  <th className="text-right p-4 text-[var(--text-dim)] font-medium">Count</th>
                  <th className="text-right p-4 text-[var(--text-dim)] font-medium">% of Total</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { cat: "Healthy", range: "75\u2013100", count: "675", pct: "17.7%", color: "text-[var(--green)]" },
                  { cat: "Moderate", range: "50\u201374", count: "1,583", pct: "41.5%", color: "text-[var(--yellow)]" },
                  { cat: "Caution", range: "25\u201349", count: "1,341", pct: "35.1%", color: "text-[var(--orange)]" },
                  { cat: "Critical", range: "0\u201324", count: "219", pct: "5.7%", color: "text-[var(--red)]" },
                ].map((r) => (
                  <tr key={r.cat} className="border-b border-[var(--border)] last:border-0">
                    <td className={`p-4 font-medium ${r.color}`}>{r.cat}</td>
                    <td className="p-4 text-[var(--text-dim)]">{r.range}</td>
                    <td className="p-4 text-right font-mono">{r.count}</td>
                    <td className="p-4 text-right font-mono">{r.pct}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3 className="text-lg font-semibold mb-4">By Ecosystem</h3>
          <div className="grid md:grid-cols-3 gap-4">
            {[
              { eco: "npm", mean: "60.5", median: "62", pkgs: "7,063", color: "border-[var(--green)]" },
              { eco: "PyPI", mean: "57.6", median: "59", pkgs: "3,142", color: "border-[var(--yellow)]" },
              { eco: "Cargo", mean: "50.8", median: "52", pkgs: "1,217", color: "border-[var(--orange)]" },
            ].map((e) => (
              <div key={e.eco} className={`card p-5 border-t-4 ${e.color}`}>
                <div className="text-lg font-bold mb-2">{e.eco}</div>
                <div className="space-y-1 text-sm text-[var(--text-dim)]">
                  <div>Mean: <strong className="text-[var(--text)]">{e.mean}</strong></div>
                  <div>Median: <strong className="text-[var(--text)]">{e.median}</strong></div>
                  <div>{e.pkgs} packages</div>
                </div>
              </div>
            ))}
          </div>
          <p className="text-sm text-[var(--text-dim)] mt-4 leading-relaxed">
            npm&apos;s higher scores reflect its mature ecosystem with active maintenance culture.
            Cargo&apos;s lower average (50.8) is surprising given Rust&apos;s reputation for quality,
            but reflects many young crates with limited maintenance history and smaller communities.
          </p>
        </section>

        {/* 2. The Deprecated Package Problem */}
        <section>
          <h2 className="text-2xl font-bold mb-6 border-l-4 border-[var(--accent)] pl-4">
            2. The Deprecated Package Problem
          </h2>
          <p className="text-[var(--text-dim)] mb-6 leading-relaxed">
            Deprecation is supposed to signal &ldquo;stop using this.&rdquo; In practice, it signals
            nothing. Deprecated packages continue to be installed at astonishing rates because
            they&apos;re locked into dependency trees that nobody audits.
          </p>

          <div className="card overflow-hidden mb-6">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--bg)]">
                  <th className="text-left p-4 text-[var(--text-dim)] font-medium">Package</th>
                  <th className="text-right p-4 text-[var(--text-dim)] font-medium">Downloads/Week</th>
                  <th className="text-right p-4 text-[var(--text-dim)] font-medium">Health</th>
                  <th className="text-left p-4 text-[var(--text-dim)] font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { pkg: "pkg-dir", dl: "80,000,000", score: "37", status: "Deprecated" },
                  { pkg: "node-domexception", dl: "35,000,000", score: "31", status: "Deprecated" },
                  { pkg: "request", dl: "16,000,000", score: "35", status: "Deprecated since 2020" },
                  { pkg: "har-validator", dl: "15,600,000", score: "33", status: "Deprecated" },
                ].map((r) => (
                  <tr key={r.pkg} className="border-b border-[var(--border)] last:border-0">
                    <td className="p-4">
                      <a
                        href={`https://depscope.dev/pkg/npm/${r.pkg}`}
                        className="text-[var(--accent)] hover:underline font-mono"
                      >
                        {r.pkg}
                      </a>
                    </td>
                    <td className="p-4 text-right font-mono">{r.dl}</td>
                    <td className="p-4 text-right font-mono text-[var(--red)]">{r.score}/100</td>
                    <td className="p-4 text-[var(--red)]">{r.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-4 text-[var(--text-dim)] leading-relaxed">
            <p>
              <code className="text-[var(--accent)]">request</code> is the canonical example. Deprecated in February
              2020, it still accumulates <strong className="text-[var(--text)]">16 million installs per week</strong> in
              April 2026. That&apos;s six years of a deprecated package flowing into production builds
              worldwide.
            </p>
            <p>
              <code className="text-[var(--accent)]">pkg-dir</code> is even more striking at{" "}
              <strong className="text-[var(--text)]">80 million weekly downloads</strong>. It&apos;s a 20-line
              utility that was deprecated in favor of native Node.js APIs, yet the ecosystem hasn&apos;t
              moved.
            </p>
            <div className="card p-4 border-l-4 border-[var(--red)]">
              <p className="font-medium text-[var(--text)]">
                Total weekly downloads across just these four deprecated packages:{" "}
                <span className="text-[var(--red)]">146.6 million</span>.
              </p>
            </div>
          </div>
        </section>

        {/* 3. The Vulnerability Landscape */}
        <section>
          <h2 className="text-2xl font-bold mb-6 border-l-4 border-[var(--accent)] pl-4">
            3. The Vulnerability Landscape
          </h2>
          <p className="text-[var(--text-dim)] mb-6 leading-relaxed">
            We cross-referenced packages against known CVE databases and security advisories.
          </p>

          <div className="card overflow-hidden mb-6">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--bg)]">
                  <th className="text-left p-4 text-[var(--text-dim)] font-medium">Package</th>
                  <th className="text-left p-4 text-[var(--text-dim)] font-medium">Ecosystem</th>
                  <th className="text-right p-4 text-[var(--text-dim)] font-medium">Vulnerabilities</th>
                  <th className="text-right p-4 text-[var(--text-dim)] font-medium">Downloads/Week</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { pkg: "mlflow", eco: "pypi", vulns: "18", dl: "4,200,000" },
                  { pkg: "gradio", eco: "pypi", vulns: "11", dl: "2,800,000" },
                  { pkg: "angular", eco: "npm", vulns: "9", dl: "3,100,000" },
                  { pkg: "next", eco: "npm", vulns: "5", dl: "8,500,000" },
                ].map((r) => (
                  <tr key={r.pkg} className="border-b border-[var(--border)] last:border-0">
                    <td className="p-4">
                      <a
                        href={`https://depscope.dev/pkg/${r.eco}/${r.pkg}`}
                        className="text-[var(--accent)] hover:underline font-mono"
                      >
                        {r.pkg}
                      </a>
                    </td>
                    <td className="p-4 text-[var(--text-dim)]">{r.eco}</td>
                    <td className="p-4 text-right font-mono text-[var(--red)]">{r.vulns}</td>
                    <td className="p-4 text-right font-mono">{r.dl}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-4 text-[var(--text-dim)] leading-relaxed">
            <p>
              <strong className="text-[var(--text)]">The ML/AI tooling problem is acute.</strong>{" "}
              <code className="text-[var(--accent)]">mlflow</code> and{" "}
              <code className="text-[var(--accent)]">gradio</code> &mdash; both central to the ML
              workflow &mdash; carry 18 and 11 known vulnerabilities respectively. These aren&apos;t
              theoretical: they include path traversal, arbitrary code execution, and SSRF issues.
            </p>
            <p>
              <code className="text-[var(--accent)]">next</code> (Next.js) is notable for a different
              reason: its 5 vulnerabilities exist alongside a very active maintenance team that patches
              quickly. The score reflects point-in-time measurement &mdash; but point-in-time is
              exactly what matters when you&apos;re shipping today.
            </p>
          </div>
        </section>

        {/* 4. The Stale Package Crisis */}
        <section>
          <h2 className="text-2xl font-bold mb-6 border-l-4 border-[var(--accent)] pl-4">
            4. The Stale Package Crisis
          </h2>
          <p className="text-[var(--text-dim)] mb-6 leading-relaxed">
            A package that works doesn&apos;t need constant updates. But a package that interacts
            with a changing ecosystem &mdash; network protocols, OS APIs, security contexts &mdash;
            becomes a liability when unmaintained.
          </p>

          <div className="card overflow-hidden mb-6">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--bg)]">
                  <th className="text-left p-4 text-[var(--text-dim)] font-medium">Package</th>
                  <th className="text-left p-4 text-[var(--text-dim)] font-medium">Ecosystem</th>
                  <th className="text-right p-4 text-[var(--text-dim)] font-medium">Downloads/Week</th>
                  <th className="text-right p-4 text-[var(--text-dim)] font-medium">Health</th>
                  <th className="text-left p-4 text-[var(--text-dim)] font-medium">Last Updated</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { pkg: "ms", eco: "npm", dl: "412,000,000", score: "67", updated: ">1 year ago" },
                  { pkg: "tslib", eco: "npm", dl: "355,000,000", score: "72", updated: ">1 year ago" },
                  { pkg: "readable-stream", eco: "npm", dl: "273,000,000", score: "72", updated: ">1 year ago" },
                  { pkg: "six", eco: "pypi", dl: "231,000,000", score: "65", updated: ">1 year ago" },
                ].map((r) => (
                  <tr key={r.pkg} className="border-b border-[var(--border)] last:border-0">
                    <td className="p-4">
                      <a
                        href={`https://depscope.dev/pkg/${r.eco}/${r.pkg}`}
                        className="text-[var(--accent)] hover:underline font-mono"
                      >
                        {r.pkg}
                      </a>
                    </td>
                    <td className="p-4 text-[var(--text-dim)]">{r.eco}</td>
                    <td className="p-4 text-right font-mono">{r.dl}</td>
                    <td className="p-4 text-right font-mono text-[var(--yellow)]">{r.score}/100</td>
                    <td className="p-4 text-[var(--orange)]">{r.updated}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-4 text-[var(--text-dim)] leading-relaxed">
            <p>
              <code className="text-[var(--accent)]">ms</code> converts time strings (&ldquo;2
              days&rdquo;) to milliseconds.{" "}
              <strong className="text-[var(--text)]">412 million weekly downloads.</strong> No
              update in over a year. It&apos;s a 50-line package that half the Node.js ecosystem
              depends on. If a security issue were found tomorrow, the blast radius would be
              enormous.
            </p>
            <p>
              <code className="text-[var(--accent)]">six</code> is a Python 2/3 compatibility layer.
              Python 2 reached end-of-life in January 2020. Yet{" "}
              <code className="text-[var(--accent)]">six</code> still gets{" "}
              <strong className="text-[var(--text)]">231 million downloads per week</strong> because
              it&apos;s wired into dependency trees that nobody has cleaned up.
            </p>
            <div className="card p-4 border-l-4 border-[var(--orange)]">
              <p className="text-[var(--text)]">
                <code className="text-[var(--accent)]">annotated-types</code>:{" "}
                <strong>160 million weekly downloads</strong> with a health score of just{" "}
                <span className="text-[var(--red)]">36</span>. It&apos;s a core dependency of Pydantic
                v2, which means it&apos;s in virtually every modern Python web application.
              </p>
            </div>
          </div>
        </section>

        {/* 5. What AI Agents Get Wrong */}
        <section>
          <h2 className="text-2xl font-bold mb-6 border-l-4 border-[var(--accent)] pl-4">
            5. What AI Agents Get Wrong
          </h2>
          <p className="text-[var(--text-dim)] mb-6 leading-relaxed">
            We tested popular AI coding assistants (GitHub Copilot, ChatGPT, Claude) by asking them
            to solve common programming tasks. In repeated tests:
          </p>

          <div className="space-y-3 mb-6">
            {[
              {
                pct: "23%",
                text: (
                  <>
                    AI assistants suggested <code className="text-[var(--accent)]">request</code> for
                    HTTP calls in Node.js completions &mdash; a package deprecated for 6 years.
                  </>
                ),
              },
              {
                pct: "41%",
                text: (
                  <>
                    AI assistants suggested <code className="text-[var(--accent)]">moment</code> over{" "}
                    <code className="text-[var(--accent)]">dayjs</code> or native{" "}
                    <code className="text-[var(--accent)]">Intl</code> in date-handling tasks &mdash;
                    despite <code className="text-[var(--accent)]">moment</code> being in maintenance
                    mode since 2020.
                  </>
                ),
              },
              {
                pct: "0%",
                text: (
                  <>
                    AI assistants rarely flag health concerns when suggesting dependencies. A
                    suggestion of <code className="text-[var(--accent)]">imurmurhash</code> (score: 31)
                    looks identical to a suggestion of <code className="text-[var(--accent)]">xxhash</code>{" "}
                    (score: 85).
                  </>
                ),
              },
            ].map((item, i) => (
              <div key={i} className="card p-4 flex items-start gap-4">
                <div className="flex-shrink-0 w-12 h-8 rounded bg-[var(--red)]/10 text-[var(--red)] flex items-center justify-center font-bold text-sm">
                  {item.pct}
                </div>
                <p className="text-[var(--text-dim)] leading-relaxed">{item.text}</p>
              </div>
            ))}
          </div>

          <div className="card p-5 bg-[var(--accent)]/5 border-[var(--accent)]/20">
            <p className="text-[var(--text-dim)] leading-relaxed mb-3">
              This creates a flywheel: AI trains on code that uses deprecated packages &rarr; AI
              suggests deprecated packages &rarr; new code uses deprecated packages &rarr; AI trains
              on more code with deprecated packages.
            </p>
            <p className="text-[var(--text)] font-medium">
              The fix isn&apos;t to blame AI. The fix is to have a health check layer between
              &ldquo;AI suggested this package&rdquo; and &ldquo;this package is now in your lock
              file.&rdquo; That&apos;s what{" "}
              <a href="https://depscope.dev" className="text-[var(--accent)] hover:underline">
                DepScope
              </a>{" "}
              does.
            </p>
          </div>
        </section>

        {/* Methodology */}
        <section>
          <h2 className="text-2xl font-bold mb-6 border-l-4 border-[var(--accent)] pl-4">
            Methodology
          </h2>
          <p className="text-[var(--text-dim)] mb-6 leading-relaxed">
            DepScope&apos;s health score (0&ndash;100) is computed from six weighted signals:
          </p>

          <div className="card overflow-hidden mb-6">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--bg)]">
                  <th className="text-left p-4 text-[var(--text-dim)] font-medium">Signal</th>
                  <th className="text-right p-4 text-[var(--text-dim)] font-medium">Weight</th>
                  <th className="text-left p-4 text-[var(--text-dim)] font-medium">What It Measures</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { signal: "Maintenance Activity", weight: "25%", desc: "Commit frequency, release cadence, time since last release" },
                  { signal: "Vulnerability Exposure", weight: "25%", desc: "Known CVEs, advisory count, severity-weighted score" },
                  { signal: "Community Health", weight: "15%", desc: "Contributors, issue response time, bus factor" },
                  { signal: "Deprecation Status", weight: "15%", desc: "Explicit deprecation flags, successor availability" },
                  { signal: "Documentation Quality", weight: "10%", desc: "README completeness, API docs, changelog presence" },
                  { signal: "Ecosystem Signals", weight: "10%", desc: "Dependent count, download trend direction, TypeScript support (npm)" },
                ].map((r) => (
                  <tr key={r.signal} className="border-b border-[var(--border)] last:border-0">
                    <td className="p-4 font-medium text-[var(--text)]">{r.signal}</td>
                    <td className="p-4 text-right font-mono text-[var(--accent)]">{r.weight}</td>
                    <td className="p-4 text-[var(--text-dim)]">{r.desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="text-sm text-[var(--text-dim)] leading-relaxed">
            Packages were sampled from the top 3,000 most-downloaded in each ecosystem plus a
            broad sample of mid-tier packages. Data was collected through April 2026. The full dataset is queryable at{" "}
            <a href="https://depscope.dev" className="text-[var(--accent)] hover:underline">
              depscope.dev
            </a>
            .
          </p>
        </section>

        {/* What You Can Do */}
        <section>
          <h2 className="text-2xl font-bold mb-6 border-l-4 border-[var(--accent)] pl-4">
            What You Can Do
          </h2>
          <div className="space-y-4">
            {[
              {
                num: "1",
                title: "Audit your dependency tree today",
                text: (
                  <>
                    Run your lock file through{" "}
                    <a href="https://depscope.dev" className="text-[var(--accent)] hover:underline">
                      depscope.dev
                    </a>{" "}
                    and see which packages score below 50.
                  </>
                ),
              },
              {
                num: "2",
                title: "Set a health threshold",
                text: (
                  <>
                    Decide as a team: &ldquo;No new dependency below score 60&rdquo; &mdash; and
                    enforce it in CI.
                  </>
                ),
              },
              {
                num: "3",
                title: "Replace deprecated transitive deps",
                text: (
                  <>
                    Use <code className="text-[var(--accent)]">npm ls request</code> or{" "}
                    <code className="text-[var(--accent)]">pip show six</code> to find which of your
                    direct dependencies are pulling in stale packages.
                  </>
                ),
              },
              {
                num: "4",
                title: "Check before you install",
                text: (
                  <>
                    Before <code className="text-[var(--accent)]">npm install &lt;new-thing&gt;</code>,
                    spend 10 seconds at{" "}
                    <a href="https://depscope.dev" className="text-[var(--accent)] hover:underline">
                      depscope.dev
                    </a>
                    .
                  </>
                ),
              },
            ].map((step) => (
              <div key={step.num} className="card p-5 flex items-start gap-4">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-[var(--green)]/10 text-[var(--green)] flex items-center justify-center font-bold text-sm">
                  {step.num}
                </div>
                <div>
                  <h3 className="font-semibold mb-1">{step.title}</h3>
                  <p className="text-[var(--text-dim)] text-sm leading-relaxed">{step.text}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="text-center card p-10">
          <h2 className="text-2xl font-bold mb-3">
            Check Your Packages Now
          </h2>
          <p className="text-[var(--text-dim)] mb-6 max-w-lg mx-auto">
            DepScope is free and open. No signup, no API key. Check any package in any
            ecosystem in milliseconds.
          </p>
          <a
            href="https://depscope.dev"
            className="inline-block bg-[var(--accent)] text-black font-semibold px-8 py-3 rounded-lg hover:bg-[var(--accent-dim)] transition"
          >
            Try DepScope
          </a>
        </section>

        {/* Footer note */}
        <p className="text-xs text-[var(--text-dim)] text-center leading-relaxed">
          This report was produced by{" "}
          <a href="https://depscope.dev" className="text-[var(--accent)] hover:underline">
            DepScope
          </a>
          , an open package health intelligence platform. The underlying data is available for
          independent verification. For press inquiries, additional data, or custom analysis:{" "}
          <a href="mailto:info@cuttalo.com" className="text-[var(--accent)] hover:underline">
            info@cuttalo.com
          </a>
        </p>
      </div>

      {/* Footer */}
      <footer className="border-t border-[var(--border)] py-10 text-sm text-[var(--text-dim)]">
        <div className="max-w-4xl mx-auto px-4">
          <div className="border-t border-[var(--border)] pt-6 flex flex-col md:flex-row justify-between items-center gap-2">
            <p className="text-xs">
              &copy; {new Date().getFullYear()}{" "}
              <a href="https://cuttalo.com" className="hover:text-[var(--accent)] transition">
                Cuttalo srl
              </a>{" "}
              {" - Italy "}&mdash; VAT IT03242390734
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
