"use client";

import { useState } from "react";
import {
  Card,
  CardBody,
  Section,
  Button,
  Badge,
  Input,
  Select,
  Table,
  Thead,
  Tbody,
  Th,
  Td,
  Tr,
} from "../../../components/ui";

export interface ChangeRow {
  ecosystem?: string;
  package?: string;
  from_version: string;
  to_version: string;
  change_type: string;
  description: string;
  migration_hint: string | null;
}

interface BreakingResponse {
  ecosystem: string;
  package: string;
  from_version: string | null;
  to_version: string | null;
  changes: ChangeRow[];
  total: number;
  note: string;
}

const ECOSYSTEMS = [
  "npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems",
  "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew",
];

const CHANGE_VARIANTS: Record<string, "neutral" | "warning" | "danger" | "success"> = {
  removal: "danger",
  runtime: "warning",
  api: "warning",
  build: "neutral",
  config: "neutral",
  behavior: "warning",
};

function TypeBadge({ type }: { type: string }) {
  const key = (type || "").toLowerCase();
  return <Badge variant={CHANGE_VARIANTS[key] || "neutral"}>{key || "change"}</Badge>;
}

export default function BreakingClient({ initialSamples }: { initialSamples: ChangeRow[] }) {
  const [ecosystem, setEcosystem] = useState("npm");
  const [pkg, setPkg] = useState("");
  const [fromV, setFromV] = useState("");
  const [toV, setToV] = useState("");
  const [changes, setChanges] = useState<ChangeRow[] | null>(null);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const search = async () => {
    if (!pkg.trim()) return;
    setLoading(true);
    setError("");
    setChanges(null);
    setNote("");
    try {
      const qs = new URLSearchParams();
      if (fromV.trim()) qs.set("from_version", fromV.trim());
      if (toV.trim()) qs.set("to_version", toV.trim());
      const suffix = qs.toString() ? `?${qs}` : "";
      const r = await fetch(
        `/api/breaking/${ecosystem}/${encodeURIComponent(pkg.trim())}${suffix}`
      );
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d: BreakingResponse = await r.json();
      setChanges(d.changes || []);
      setNote(d.note || "");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load breaking changes");
    } finally {
      setLoading(false);
    }
  };

  const renderTable = (rows: ChangeRow[], showPackage = false) => (
    <Table>
      <Thead>
        <Tr>
          {showPackage && <Th>Package</Th>}
          <Th>From → To</Th>
          <Th>Type</Th>
          <Th>Breaking change</Th>
          <Th>Migration hint</Th>
        </Tr>
      </Thead>
      <Tbody>
        {rows.map((c, idx) => (
          <Tr key={`${c.ecosystem || ""}-${c.package || ""}-${c.from_version}-${c.to_version}-${idx}`}>
            {showPackage && (
              <Td className="font-mono text-xs whitespace-nowrap">
                <a
                  href={`/pkg/${c.ecosystem}/${encodeURIComponent(c.package || "")}`}
                  className="text-[var(--accent)] hover:underline"
                >
                  {c.ecosystem}/{c.package}
                </a>
              </Td>
            )}
            <Td className="font-mono text-xs tabular-nums whitespace-nowrap">
              <span className="text-[var(--text-dim)]">{c.from_version}</span>
              <span className="mx-1 text-[var(--text-faded)]">→</span>
              <span className="text-[var(--text)]">{c.to_version}</span>
            </Td>
            <Td>
              <TypeBadge type={c.change_type} />
            </Td>
            <Td className="text-sm text-[var(--text)] max-w-md">
              {c.description}
            </Td>
            <Td className="text-sm text-[var(--text-dim)] font-mono whitespace-pre-wrap max-w-md">
              {c.migration_hint || <span className="text-[var(--text-faded)]">—</span>}
            </Td>
          </Tr>
        ))}
      </Tbody>
    </Table>
  );

  return (
    <>
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
                placeholder="package (e.g. react, next, prisma)"
                value={pkg}
                onChange={(e) => setPkg(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && search()}
                className="flex-1"
              />
              <Input
                placeholder="from (e.g. 18)"
                value={fromV}
                onChange={(e) => setFromV(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && search()}
                className="md:w-28"
              />
              <Input
                placeholder="to (e.g. 19)"
                value={toV}
                onChange={(e) => setToV(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && search()}
                className="md:w-28"
              />
              <Button variant="primary" onClick={search} disabled={loading || !pkg.trim()}>
                {loading ? "Loading..." : "Find breaking"}
              </Button>
            </div>
            {error && <p className="text-xs text-[var(--red)] mt-2 font-mono">{error}</p>}
          </CardBody>
        </Card>
      </Section>

      {changes !== null ? (
        <Section
          title={`${changes.length} breaking change${changes.length === 1 ? "" : "s"} for ${ecosystem}/${pkg}${fromV || toV ? ` (${fromV || "?"} → ${toV || "?"})` : ""}`}
          className="mt-6"
        >
          <Card>
            {changes.length === 0 ? (
              <div className="p-8 text-center text-sm text-[var(--text-dim)]">
                {note || "No breaking changes indexed for this package yet."}
              </div>
            ) : (
              <>
                {renderTable(changes, false)}
                <div className="px-4 py-3 text-xs text-[var(--text-faded)] border-t border-[var(--border)]">
                  {note}
                </div>
              </>
            )}
          </Card>
        </Section>
      ) : (
        initialSamples.length > 0 && (
          <Section
            title={`Recent breaking changes (${initialSamples.length})`}
            className="mt-6"
          >
            <Card>
              {renderTable(initialSamples, true)}
              <div className="px-4 py-3 text-xs text-[var(--text-faded)] border-t border-[var(--border)]">
                Sample of curated entries across ecosystems. Search for a specific package above.
              </div>
            </Card>
          </Section>
        )
      )}
    </>
  );
}
