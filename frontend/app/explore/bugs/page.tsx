"use client";

import { useState } from "react";
import {
  Card,
  CardBody,
  PageHeader,
  Section,
  Button,
  Badge,
  SeverityBadge,
  Input,
  Select,
  Table,
  Thead,
  Tbody,
  Th,
  Td,
  Tr,
  Footer,
} from "../../../components/ui";

interface BugRow {
  id: number;
  ecosystem: string;
  package_name: string;
  affected_version: string | null;
  fixed_version: string | null;
  bug_id: string;
  title: string;
  description: string;
  severity: string;
  status: string;
  source: string;
  source_url: string | null;
}

interface BugsResponse {
  ecosystem: string;
  package: string;
  version: string | null;
  bugs: BugRow[];
}

interface BugsSearchResponse {
  query: string;
  results: BugRow[];
}

const ECOSYSTEMS = [
  "npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems",
  "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew",
];

function StatusBadge({ status }: { status: string }) {
  const s = (status || "").toLowerCase();
  const variant =
    s === "closed" || s === "fixed" ? "success" :
    s === "open" ? "danger" :
    s === "wontfix" ? "neutral" :
    "warning";
  return <Badge variant={variant}>{s || "unknown"}</Badge>;
}

export default function BugsPage() {
  const [ecosystem, setEcosystem] = useState("npm");
  const [pkg, setPkg] = useState("");
  const [version, setVersion] = useState("");
  const [bugs, setBugs] = useState<BugRow[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [globalQuery, setGlobalQuery] = useState("");
  const [globalResults, setGlobalResults] = useState<BugRow[] | null>(null);
  const [globalLoading, setGlobalLoading] = useState(false);

  const search = async () => {
    if (!pkg.trim()) return;
    setLoading(true);
    setError("");
    setBugs(null);
    try {
      const qs = version.trim() ? `?version=${encodeURIComponent(version.trim())}` : "";
      const r = await fetch(`/api/bugs/${ecosystem}/${encodeURIComponent(pkg.trim())}${qs}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d: BugsResponse = await r.json();
      setBugs(d.bugs || []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load bugs");
    } finally {
      setLoading(false);
    }
  };

  const searchGlobal = async () => {
    if (!globalQuery.trim()) return;
    setGlobalLoading(true);
    setGlobalResults(null);
    try {
      const r = await fetch(`/api/bugs/search?q=${encodeURIComponent(globalQuery.trim())}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d: BugsSearchResponse = await r.json();
      setGlobalResults(d.results || []);
    } catch {
      setGlobalResults([]);
    } finally {
      setGlobalLoading(false);
    }
  };

  const renderTable = (rows: BugRow[]) => (
    <Table>
      <Thead>
        <Tr>
          <Th>Title</Th>
          <Th>Affected</Th>
          <Th>Fixed</Th>
          <Th>Severity</Th>
          <Th>Status</Th>
          <Th>Source</Th>
        </Tr>
      </Thead>
      <Tbody>
        {rows.map((b) => (
          <Tr key={b.id}>
            <Td>
              <div className="font-medium text-[var(--text)]">{b.title}</div>
              <div className="text-[11px] font-mono text-[var(--text-faded)] mt-0.5">
                {b.ecosystem}/{b.package_name} · {b.bug_id}
              </div>
            </Td>
            <Td className="font-mono text-xs tabular-nums">
              {b.affected_version || <span className="text-[var(--text-faded)]">—</span>}
            </Td>
            <Td className="font-mono text-xs tabular-nums text-[var(--green)]">
              {b.fixed_version || <span className="text-[var(--text-faded)]">—</span>}
            </Td>
            <Td>
              <SeverityBadge severity={b.severity} />
            </Td>
            <Td>
              <StatusBadge status={b.status} />
            </Td>
            <Td>
              {b.source_url ? (
                <a href={b.source_url} target="_blank" rel="noopener" className="text-xs font-mono text-[var(--accent)] hover:underline">
                  {b.source}
                </a>
              ) : (
                <span className="text-xs text-[var(--text-faded)] font-mono">{b.source}</span>
              )}
            </Td>
          </Tr>
        ))}
      </Tbody>
    </Table>
  );

  return (
    <div className="min-h-screen">
      <main className="max-w-6xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="Explore · Bugs"
          title="Known Bugs per Package & Version"
          description="Version-specific regressions tracked from GitHub issues, registries and maintainer notes."
        />

        <Section>
          <Card>
            <CardBody>
              <div className="flex flex-col md:flex-row gap-2">
                <Select value={ecosystem} onChange={(e) => setEcosystem(e.target.value)} className="md:w-40">
                  {ECOSYSTEMS.map((e) => (
                    <option key={e} value={e}>{e}</option>
                  ))}
                </Select>
                <Input
                  placeholder="package (e.g. react)"
                  value={pkg}
                  onChange={(e) => setPkg(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && search()}
                  className="flex-1"
                />
                <Input
                  placeholder="version (optional)"
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && search()}
                  className="md:w-40"
                />
                <Button variant="primary" onClick={search} disabled={loading || !pkg.trim()}>
                  {loading ? "Loading..." : "Find bugs"}
                </Button>
              </div>
              {error && <p className="text-xs text-[var(--red)] mt-2 font-mono">{error}</p>}
            </CardBody>
          </Card>
        </Section>

        {bugs !== null && (
          <Section title={`${bugs.length} bug${bugs.length === 1 ? "" : "s"} for ${ecosystem}/${pkg}${version ? `@${version}` : ""}`} className="mt-6">
            <Card>
              {bugs.length === 0 ? (
                <div className="p-8 text-center text-sm text-[var(--text-dim)]">
                  No known bugs indexed for this package{version ? ` at version ${version}` : ""}.
                </div>
              ) : (
                renderTable(bugs)
              )}
            </Card>
          </Section>
        )}

        <Section
          title="Search all bugs"
          description="Full-text search across the bug database"
          className="mt-8"
        >
          <Card>
            <CardBody>
              <div className="flex gap-2">
                <Input
                  placeholder="e.g. hydration mismatch, memory leak, segfault..."
                  value={globalQuery}
                  onChange={(e) => setGlobalQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && searchGlobal()}
                  className="flex-1"
                />
                <Button variant="secondary" onClick={searchGlobal} disabled={globalLoading || !globalQuery.trim()}>
                  {globalLoading ? "..." : "Search"}
                </Button>
              </div>
            </CardBody>
          </Card>

          {globalResults !== null && (
            <Card className="mt-4">
              {globalResults.length === 0 ? (
                <div className="p-8 text-center text-sm text-[var(--text-dim)]">
                  No results. Try different keywords.
                </div>
              ) : (
                renderTable(globalResults)
              )}
            </Card>
          )}
        </Section>
      </main>
      <Footer />
    </div>
  );
}
