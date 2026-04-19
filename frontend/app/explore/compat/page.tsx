"use client";

import { useState } from "react";
import {
  Card,
  CardBody,
  PageHeader,
  Section,
  Button,
  Badge,
  Input,
  Footer,
} from "../../../components/ui";

interface CompatResult {
  status: "verified" | "broken" | "untested" | string;
  match_type?: string;
  packages: Record<string, string>;
  notes?: string;
  source?: string;
  source_url?: string;
  stars?: number;
  reported_count?: number;
  similar_stacks?: Array<{
    stack_hash: string;
    packages: Record<string, string>;
    status: string;
    notes?: string;
    source?: string;
    source_url?: string;
    stars?: number;
  }>;
}

interface StackItem {
  name: string;
  version: string;
}

const POPULAR_STACKS: { label: string; items: StackItem[] }[] = [
  { label: "Next.js 16 + React 19", items: [{ name: "next", version: "16" }, { name: "react", version: "19" }] },
  { label: "Next.js 15 + React 18", items: [{ name: "next", version: "15" }, { name: "react", version: "18" }] },
  { label: "Vite + React", items: [{ name: "vite", version: "5" }, { name: "react", version: "18" }] },
  { label: "FastAPI + Pydantic 2", items: [{ name: "fastapi", version: "0.115" }, { name: "pydantic", version: "2" }] },
  { label: "Django + DRF", items: [{ name: "django", version: "5" }, { name: "djangorestframework", version: "3.15" }] },
  { label: "Tailwind 4 + Next.js 16", items: [{ name: "tailwindcss", version: "4" }, { name: "next", version: "16" }] },
];

export default function CompatPage() {
  const [stack, setStack] = useState<StackItem[]>([]);
  const [name, setName] = useState("");
  const [version, setVersion] = useState("");
  const [result, setResult] = useState<CompatResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const addItem = () => {
    if (!name.trim() || !version.trim()) return;
    setStack((s) => [...s, { name: name.trim(), version: version.trim() }]);
    setName("");
    setVersion("");
  };

  const removeItem = (i: number) => {
    setStack((s) => s.filter((_, idx) => idx !== i));
  };

  const check = async (items?: StackItem[]) => {
    const list = items || stack;
    if (list.length < 2) {
      setError("Add at least 2 packages to check compatibility");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    const qs = list.map((i) => `${i.name}@${i.version}`).join(",");
    try {
      const r = await fetch(`/api/compat?stack=${encodeURIComponent(qs)}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setResult(await r.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to check");
    } finally {
      setLoading(false);
    }
  };

  const loadStack = (items: StackItem[]) => {
    setStack(items);
    setResult(null);
    setTimeout(() => check(items), 0);
  };

  const statusVariant =
    result?.status === "verified" ? "success" :
    result?.status === "broken" ? "danger" :
    "warning";

  return (
    <div className="min-h-screen">
      <main className="max-w-4xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="Explore · Compat"
          title="Stack Compatibility Checker"
          description="Build a stack. We tell you if it is verified, broken or untested, with notes and references."
        />

        <Section>
          <Card>
            <CardBody>
              <div className="flex flex-wrap gap-2 mb-3 min-h-[32px]">
                {stack.length === 0 && (
                  <span className="text-xs text-[var(--text-faded)] self-center">Add packages below to start</span>
                )}
                {stack.map((it, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1.5 pl-2.5 pr-1 py-1 rounded-full border border-[var(--border)] bg-[var(--bg-input)] text-xs font-mono"
                  >
                    <span className="text-[var(--text)]">{it.name}</span>
                    <span className="text-[var(--text-faded)]">@{it.version}</span>
                    <button
                      onClick={() => removeItem(i)}
                      className="w-4 h-4 inline-flex items-center justify-center rounded-full text-[var(--text-dim)] hover:text-[var(--red)] hover:bg-[var(--bg-hover)] transition"
                      aria-label="Remove"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>

              <div className="flex flex-col sm:flex-row gap-2">
                <Input
                  placeholder="package (e.g. next)"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addItem()}
                  className="flex-1"
                />
                <Input
                  placeholder="version (e.g. 16)"
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addItem()}
                  className="sm:w-40"
                />
                <Button variant="secondary" onClick={addItem}>
                  Add
                </Button>
                <Button variant="primary" onClick={() => check()} disabled={loading || stack.length < 2}>
                  {loading ? "Checking..." : "Check compatibility"}
                </Button>
              </div>
              {error && <p className="text-xs text-[var(--red)] mt-2 font-mono">{error}</p>}
            </CardBody>
          </Card>
        </Section>

        {result && (
          <Section className="mt-6">
            <Card>
              <CardBody>
                <div className="flex items-center gap-3 flex-wrap mb-3">
                  <Badge variant={statusVariant} className="uppercase text-sm px-3 py-1">
                    {result.status}
                  </Badge>
                  {result.match_type && (
                    <span className="text-[11px] font-mono text-[var(--text-faded)] uppercase tracking-wider">
                      match: {result.match_type}
                    </span>
                  )}
                  {typeof result.stars === "number" && result.stars > 0 && (
                    <Badge variant="neutral">{result.stars.toLocaleString()} stars</Badge>
                  )}
                  {typeof result.reported_count === "number" && result.reported_count > 0 && (
                    <Badge variant="neutral">{result.reported_count} reports</Badge>
                  )}
                </div>
                {result.notes && <p className="text-sm text-[var(--text-dim)] leading-relaxed">{result.notes}</p>}
                {result.source_url && (
                  <a
                    href={result.source_url}
                    target="_blank"
                    rel="noopener"
                    className="text-xs font-mono text-[var(--accent)] hover:underline mt-2 inline-block"
                  >
                    {result.source_url.replace(/^https?:\/\//, "")}
                  </a>
                )}
              </CardBody>
            </Card>

            {result.similar_stacks && result.similar_stacks.length > 0 && (
              <Section title="Similar verified stacks" className="mt-6">
                <div className="grid md:grid-cols-2 gap-3">
                  {result.similar_stacks.slice(0, 6).map((s) => {
                    const variant =
                      s.status === "verified" ? "success" :
                      s.status === "broken" ? "danger" : "warning";
                    return (
                      <Card key={s.stack_hash}>
                        <CardBody>
                          <div className="flex items-center gap-2 mb-2 flex-wrap">
                            <Badge variant={variant} className="uppercase">{s.status}</Badge>
                            {typeof s.stars === "number" && s.stars > 0 && (
                              <span className="text-[11px] font-mono text-[var(--text-faded)]">{s.stars.toLocaleString()} stars</span>
                            )}
                          </div>
                          <div className="flex flex-wrap gap-1 mb-2">
                            {Object.entries(s.packages).map(([k, v]) => (
                              <code key={k} className="text-[11px] font-mono text-[var(--text-dim)] bg-[var(--bg-input)] border border-[var(--border)] rounded px-1.5 py-0.5">
                                {k}@{v}
                              </code>
                            ))}
                          </div>
                          {s.notes && <p className="text-xs text-[var(--text-dim)] leading-relaxed">{s.notes}</p>}
                        </CardBody>
                      </Card>
                    );
                  })}
                </div>
              </Section>
            )}
          </Section>
        )}

        <Section title="Popular stacks" className="mt-8">
          <div className="flex flex-wrap gap-2">
            {POPULAR_STACKS.map((s) => (
              <button
                key={s.label}
                onClick={() => loadStack(s.items)}
                className="px-3 py-1.5 text-xs rounded-full border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-dim)] hover:border-[var(--accent)]/40 hover:text-[var(--accent)] transition font-mono"
              >
                {s.label}
              </button>
            ))}
          </div>
        </Section>
      </main>
      <Footer />
    </div>
  );
}
