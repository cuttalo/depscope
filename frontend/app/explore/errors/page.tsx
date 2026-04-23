"use client";

import { useEffect, useState } from "react";
import {
  Card,
  CardBody,
  PageHeader,
  Section,
  Button,
  Badge,
  Footer,
} from "../../../components/ui";

interface ErrorMatch {
  id?: number;
  hash?: string;
  pattern?: string;
  full_message?: string;
  ecosystem?: string;
  package_name?: string | null;
  package_version?: string | null;
  solution?: string;
  source_url?: string | null;
  confidence?: number;
}

function SolutionBlock({ text }: { text: string }) {
  if (!text) return null;
  const parts = text.split(/```/);
  return (
    <div className="text-sm leading-relaxed space-y-2">
      {parts.map((p, i) =>
        i % 2 === 1 ? (
          <pre
            key={`pre-${i}`}
            className="bg-[var(--bg-input)] border border-[var(--border)] rounded p-3 text-xs text-[var(--accent)] overflow-x-auto whitespace-pre-wrap font-mono"
          >
            {p.trim()}
          </pre>
        ) : (
          <div key={`txt-${i}`}>
            {p
              .split("\n")
              .filter((l) => l.trim().length > 0)
              .map((line, j) => (
                <p key={`l-${i}-${j}`} className="text-[var(--text-dim)]">
                  {line}
                </p>
              ))}
          </div>
        )
      )}
    </div>
  );
}

function normalizeMatches(raw: unknown): ErrorMatch[] {
  if (!raw || typeof raw !== "object") return [];
  const d = raw as Record<string, unknown>;
  // /api/error/resolve can return either matches:[] or match:{} or {solution}
  if (Array.isArray(d.matches)) return d.matches as ErrorMatch[];
  if (d.match && typeof d.match === "object") return [d.match as ErrorMatch];
  if (typeof d.solution === "string" && d.solution) return [d as ErrorMatch];
  return [];
}

export default function ErrorsPage() {
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<ErrorMatch[] | null>(null);
  const [commonErrors, setCommonErrors] = useState<ErrorMatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      for (const q of ["error", "cannot find", "not defined"]) {
        try {
          const r = await fetch(`/api/error?q=${encodeURIComponent(q)}`);
          if (!r.ok) continue;
          const d = await r.json();
          const list = Array.isArray(d?.common_errors) && d.common_errors.length
            ? d.common_errors
            : Array.isArray(d?.matches) ? d.matches : [];
          if (list.length) {
            setCommonErrors(list.slice(0, 20));
            return;
          }
        } catch {
          /* try next */
        }
      }
    })();
  }, []);

  const search = async () => {
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError("");
    setMatches(null);
    try {
      // Try POST /api/error/resolve first — handles full stack traces.
      let data: unknown = null;
      try {
        const r = await fetch("/api/error/resolve", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ error: q }),
        });
        if (r.ok) {
          data = await r.json();
        }
      } catch {
        /* fall through to GET */
      }

      // Fallback: GET /api/error?q=... for free-text search.
      if (!data) {
        const g = await fetch(`/api/error?q=${encodeURIComponent(q)}`);
        if (!g.ok) throw new Error(`Search failed (HTTP ${g.status})`);
        data = await g.json();
      }

      const m = normalizeMatches(data);
      setMatches(m);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Search failed — try a shorter excerpt.");
      setMatches([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen">
      <main className="max-w-4xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="Explore · Errors"
          title="Error → Fix Database"
          description="Paste a stack trace or error message. We match it against a growing database of known errors with proven fixes."
        />

        <Section>
          <Card>
            <CardBody>
              <div className="space-y-3">
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") search();
                  }}
                  placeholder={"Error: Cannot find module 'express'\n    at Function.Module._resolveFilename..."}
                  rows={6}
                  className="w-full bg-[var(--bg-input)] border border-[var(--border)] rounded px-3 py-2 text-sm text-[var(--text)] font-mono placeholder:text-[var(--text-faded)] focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]/30 transition"
                />
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11px] text-[var(--text-faded)] font-mono">⌘+Enter to search</span>
                  <Button onClick={search} disabled={loading || !query.trim()} variant="primary">
                    {loading ? "Searching..." : "Find fix"}
                  </Button>
                </div>
                {error && <p className="text-xs text-[var(--red)] font-mono">{error}</p>}
              </div>
            </CardBody>
          </Card>
        </Section>

        {matches && (
          <Section title={`${matches.length} match${matches.length === 1 ? "" : "es"}`} className="mt-6">
            {matches.length === 0 ? (
              <Card>
                <CardBody>
                  <p className="text-sm text-[var(--text-dim)]">
                    No match found. Try with a shorter excerpt (the first error line usually works best).
                  </p>
                </CardBody>
              </Card>
            ) : (
              <div className="space-y-3">
                {matches.map((m, idx) => (
                  <Card key={m.id ?? m.hash ?? idx}>
                    <CardBody>
                      <div className="flex items-center gap-2 flex-wrap mb-3">
                        {m.ecosystem && <Badge variant="accent">{m.ecosystem}</Badge>}
                        {m.package_name && (
                          <Badge variant="neutral">
                            <span className="font-mono">{m.package_name}</span>
                            {m.package_version && (
                              <span className="ml-1 text-[var(--text-faded)]">@{m.package_version}</span>
                            )}
                          </Badge>
                        )}
                        {typeof m.confidence === "number" && (
                          <Badge
                            variant={m.confidence >= 0.8 ? "success" : m.confidence >= 0.5 ? "warning" : "neutral"}
                          >
                            {Math.round(m.confidence * 100)}% match
                          </Badge>
                        )}
                      </div>
                      {m.pattern && (
                        <pre className="bg-[var(--bg-input)] border border-[var(--border)] rounded p-2 text-xs text-[var(--red)] font-mono overflow-x-auto whitespace-pre-wrap mb-3">
                          {m.pattern}
                        </pre>
                      )}
                      <SolutionBlock text={m.solution || ""} />
                      {m.source_url && (
                        <a
                          href={m.source_url}
                          target="_blank"
                          rel="noopener"
                          className="text-xs font-mono text-[var(--accent)] hover:underline mt-3 inline-block"
                        >
                          {String(m.source_url).replace(/^https?:\/\//, "")}
                        </a>
                      )}
                    </CardBody>
                  </Card>
                ))}
              </div>
            )}
          </Section>
        )}

        {!matches && commonErrors.length > 0 && (
          <Section title="Common errors" description="Top patterns from the database" className="mt-8">
            <Card>
              <div className="divide-y divide-[var(--border)]">
                {commonErrors.map((m, idx) => (
                  <button
                    key={m.id ?? m.hash ?? idx}
                    onClick={() => {
                      setQuery(m.pattern || m.full_message || "");
                      setTimeout(search, 0);
                    }}
                    className="w-full text-left px-5 py-3 hover:bg-[var(--bg-hover)] transition group"
                  >
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      {m.ecosystem && (
                        <span className="text-[10px] font-mono uppercase tracking-wider text-[var(--accent)]">
                          {m.ecosystem}
                        </span>
                      )}
                      {m.package_name && (
                        <span className="text-[10px] font-mono text-[var(--text-faded)]">
                          {m.package_name}
                        </span>
                      )}
                    </div>
                    <code className="text-xs text-[var(--text-dim)] font-mono block truncate group-hover:text-[var(--text)] transition">
                      {m.pattern || m.full_message}
                    </code>
                  </button>
                ))}
              </div>
            </Card>
          </Section>
        )}
      </main>
      <Footer />
    </div>
  );
}
