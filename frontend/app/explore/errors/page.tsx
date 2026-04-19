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
  id: number;
  hash: string;
  pattern: string;
  full_message: string;
  ecosystem: string;
  package_name: string | null;
  package_version: string | null;
  solution: string;
  source_url: string | null;
  confidence: number;
}

interface ErrorResponse {
  query: string;
  matches: ErrorMatch[];
  common_errors?: ErrorMatch[];
}

function renderSolution(text: string): string {
  // Very light markdown: triple backticks -> <pre>, inline code, bold
  // Everything else as plain text (safe since we escape HTML via textContent on React side)
  return text;
}

function SolutionBlock({ text }: { text: string }) {
  // Split by ``` blocks
  const parts = text.split(/```/);
  return (
    <div className="text-sm leading-relaxed space-y-2">
      {parts.map((p, i) => {
        if (i % 2 === 1) {
          return (
            <pre
              key={i}
              className="bg-[var(--bg-input)] border border-[var(--border)] rounded p-3 text-xs text-[var(--accent)] overflow-x-auto whitespace-pre-wrap font-mono"
            >
              {p.trim()}
            </pre>
          );
        }
        return p
          .split("\n")
          .filter((l) => l.trim().length > 0)
          .map((line, j) => (
            <p key={`${i}-${j}`} className="text-[var(--text-dim)]">
              {line}
            </p>
          ));
      })}
    </div>
  );
}

export default function ErrorsPage() {
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<ErrorMatch[] | null>(null);
  const [commonErrors, setCommonErrors] = useState<ErrorMatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    // Load common errors - try a broad query that usually returns many matches
    (async () => {
      const tryQueries = ["error", "cannot find", "not defined"];
      for (const q of tryQueries) {
        try {
          const r = await fetch(`/api/error?q=${encodeURIComponent(q)}`);
          if (!r.ok) continue;
          const d: ErrorResponse = await r.json();
          const list = d.common_errors?.length ? d.common_errors : d.matches;
          if (list?.length) {
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
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    setMatches(null);
    try {
      const r = await fetch("/api/error/resolve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ error: query.trim() }),
      });
      if (!r.ok) {
        // Fallback to GET /api/error?q=
        const g = await fetch(`/api/error?q=${encodeURIComponent(query.trim())}`);
        if (!g.ok) throw new Error(`HTTP ${g.status}`);
        const d: ErrorResponse = await g.json();
        setMatches(d.matches || []);
      } else {
        const d = await r.json();
        setMatches(d.matches || (d.solution ? [d] : []));
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to search");
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
                  placeholder="Error: Cannot find module 'express'&#10;    at Function.Module._resolveFilename..."
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
                {matches.map((m) => (
                  <Card key={m.id}>
                    <CardBody>
                      <div className="flex items-center gap-2 flex-wrap mb-3">
                        <Badge variant="accent">{m.ecosystem}</Badge>
                        {m.package_name && (
                          <Badge variant="neutral">
                            <span className="font-mono">{m.package_name}</span>
                            {m.package_version && <span className="ml-1 text-[var(--text-faded)]">@{m.package_version}</span>}
                          </Badge>
                        )}
                        {typeof m.confidence === "number" && (
                          <Badge variant={m.confidence >= 0.8 ? "success" : m.confidence >= 0.5 ? "warning" : "neutral"}>
                            {Math.round(m.confidence * 100)}% match
                          </Badge>
                        )}
                      </div>
                      <pre className="bg-[var(--bg-input)] border border-[var(--border)] rounded p-2 text-xs text-[var(--red)] font-mono overflow-x-auto whitespace-pre-wrap mb-3">
                        {m.pattern}
                      </pre>
                      <SolutionBlock text={renderSolution(m.solution || "")} />
                      {m.source_url && (
                        <a
                          href={m.source_url}
                          target="_blank"
                          rel="noopener"
                          className="text-xs font-mono text-[var(--accent)] hover:underline mt-3 inline-block"
                        >
                          {m.source_url.replace(/^https?:\/\//, "")}
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
                {commonErrors.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => {
                      setQuery(m.pattern);
                      setTimeout(search, 0);
                    }}
                    className="w-full text-left px-4 py-2.5 hover:bg-[var(--bg-hover)] transition flex items-center gap-3"
                  >
                    <Badge variant="accent" className="shrink-0">{m.ecosystem}</Badge>
                    <code className="text-xs text-[var(--text)] font-mono flex-1 truncate">{m.pattern}</code>
                    {m.package_name && (
                      <span className="text-[11px] text-[var(--text-dim)] font-mono shrink-0">{m.package_name}</span>
                    )}
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
