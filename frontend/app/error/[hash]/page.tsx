import { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  Card,
  CardBody,
  CardHeader,
  Badge,
  Footer,
} from "../../../components/ui";
import { CopyButton } from "../../../components/CopyButton";

interface ErrorPayload {
  id: number;
  hash: string;
  pattern: string;
  full_message: string | null;
  ecosystem: string | null;
  package_name: string | null;
  package_version: string | null;
  solution: string;
  confidence: number;
  source: string | null;
  source_url: string | null;
  votes: number;
  created_at: string | null;
  updated_at: string | null;
}

async function fetchError(hash: string): Promise<ErrorPayload | null> {
  try {
    const res = await fetch(
      `http://127.0.0.1:8000/api/error/${hash}`,
      { next: { revalidate: 3600 } },
    );
    if (!res.ok) return null;
    return (await res.json()) as ErrorPayload;
  } catch {
    return null;
  }
}

type Props = {
  params: Promise<{ hash: string }>;
};

// SEO quality gate: error entries with thin solution or low confidence get
// noindex and canonical consolidated on /explore/errors to avoid thin content.
const SEO_MIN_SOLUTION_LEN = 200;
const SEO_MIN_CONFIDENCE = 0.7;

function isErrorSubstantial(data: ErrorPayload | null): boolean {
  if (!data) return false;
  const solLen = (data.solution || "").length;
  const conf = data.confidence ?? 0;
  return solLen >= SEO_MIN_SOLUTION_LEN && conf >= SEO_MIN_CONFIDENCE;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { hash } = await params;
  const data = await fetchError(hash);

  if (!data) {
    return {
      title: "Error not found | DepScope",
      description: "This error pattern has not been indexed. Search similar errors on DepScope.",
      robots: { index: false, follow: true },
    };
  }

  const shouldIndex = isErrorSubstantial(data);

  const patternShort = data.pattern.slice(0, 60).trim();
  const solutionShort = data.solution.replace(/```[\s\S]*?```/g, "").replace(/\s+/g, " ").trim().slice(0, 150);

  const title = `${patternShort}${data.pattern.length > 60 ? "\u2026" : ""} \u2014 DepScope fix`;
  const description = solutionShort || `Solution for the error: ${patternShort}`;

  const canonical = shouldIndex
    ? `https://depscope.dev/error/${hash}`
    : `https://depscope.dev/explore/errors`;

  return {
    title,
    description,
    keywords: [
      data.ecosystem, data.package_name,
      "error solution", "how to fix",
      data.pattern.split(" ").slice(0, 4).join(" "),
    ].filter((x): x is string => Boolean(x)),
    openGraph: {
      title,
      description,
      url: `https://depscope.dev/error/${hash}`,
      siteName: "DepScope",
      type: "article",
      images: [
        {
          url: `https://depscope.dev/og`,
          width: 1200,
          height: 630,
          alt: `DepScope \u2014 ${patternShort}`,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
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

// Lightweight markdown-ish renderer: preserves code blocks, treats remainder as plain text
function renderSolution(md: string) {
  const parts: Array<{ type: "text" | "code"; lang?: string; content: string }> = [];
  const re = /```(\w+)?\n?([\s\S]*?)```/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(md)) !== null) {
    if (m.index > last) parts.push({ type: "text", content: md.slice(last, m.index) });
    parts.push({ type: "code", lang: m[1], content: m[2] });
    last = m.index + m[0].length;
  }
  if (last < md.length) parts.push({ type: "text", content: md.slice(last) });
  return parts;
}

export default async function ErrorDetailPage({ params }: Props) {
  const { hash } = await params;
  const data = await fetchError(hash);

  if (!data) {
    return (
      <div className="min-h-screen">
        <main className="max-w-3xl mx-auto px-4 py-16 text-center space-y-6">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight mb-2">Error not found</h1>
            <p className="text-sm text-[var(--text-dim)]">
              We have not indexed this error pattern yet.
            </p>
          </div>
          <div className="flex items-center justify-center gap-3">
            <Link
              href="/explore/errors"
              className="px-4 py-2 text-sm rounded bg-[var(--accent)] text-[var(--bg)] hover:opacity-90 transition font-mono"
            >
              Search similar errors
            </Link>
            <Link
              href="/explore"
              className="px-4 py-2 text-sm rounded border border-[var(--border)] text-[var(--text)] hover:border-[var(--accent)]/60 transition font-mono"
            >
              Browse DepScope
            </Link>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  const parts = renderSolution(data.solution || "");
  const confidencePct = Math.round((data.confidence || 0) * 100);

  const breadcrumbLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "DepScope", item: "https://depscope.dev" },
      { "@type": "ListItem", position: 2, name: "Errors", item: "https://depscope.dev/explore/errors" },
      { "@type": "ListItem", position: 3, name: data.pattern.slice(0, 60) },
    ],
  };

  const techArticleLd = {
    "@context": "https://schema.org",
    "@type": "TechArticle",
    headline: data.pattern.slice(0, 110),
    description: data.solution.replace(/```[\s\S]*?```/g, "").slice(0, 200),
    datePublished: data.created_at || undefined,
    dateModified: data.updated_at || undefined,
    author: { "@type": "Organization", name: "DepScope", url: "https://depscope.dev" },
    publisher: { "@type": "Organization", name: "DepScope", url: "https://depscope.dev" },
    mainEntityOfPage: `https://depscope.dev/error/${hash}`,
    about: data.package_name
      ? { "@type": "SoftwareApplication", name: data.package_name, applicationCategory: "DeveloperApplication" }
      : undefined,
    articleSection: "Error resolution",
    keywords: [data.ecosystem, data.package_name, "error", "fix"].filter(Boolean).join(", "),
  };

  const curlCmd = `curl https://depscope.dev/api/error/${hash}`;

  // Content-density gate (mirrors generateMetadata)
  const shouldIndex = isErrorSubstantial(data);
  const canonicalHref = shouldIndex
    ? `https://depscope.dev/error/${hash}`
    : `https://depscope.dev/explore/errors`;

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
        <link rel="alternate" type="application/json" href={`https://depscope.dev/api/error/${hash}`} />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbLd) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(techArticleLd) }}
        />
      </head>

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-4">
        <nav className="text-xs text-[var(--text-dim)] font-mono">
          <Link href="/" className="hover:text-[var(--accent)] transition">depscope</Link>
          <span className="mx-1.5 text-[var(--text-faded)]">/</span>
          <Link href="/explore/errors" className="hover:text-[var(--accent)] transition">errors</Link>
          <span className="mx-1.5 text-[var(--text-faded)]">/</span>
          <span className="text-[var(--text)]">{hash.slice(0, 10)}\u2026</span>
        </nav>

        {!shouldIndex && (
          <div className="text-xs rounded border border-[var(--border)] bg-[var(--bg-input)] px-3 py-2 text-[var(--text-dim)]">
            This error entry has limited data (solution {(data.solution || "").length} chars,{" "}
            confidence {Math.round((data.confidence ?? 0) * 100)}%).
            We index entries with a substantial solution and confidence &ge; 70%.
            Check back later or{" "}
            <Link href="/explore/errors" className="text-[var(--accent)] hover:underline">
              search similar errors
            </Link>.
          </div>
        )}

        <Card>
          <CardBody>
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="flex-1 min-w-[260px]">
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  {data.ecosystem && <Badge variant="accent">{data.ecosystem}</Badge>}
                  {data.package_name && (
                    <Link
                      href={`/pkg/${data.ecosystem}/${data.package_name}`}
                      className="text-xs font-mono text-[var(--accent)] hover:underline"
                    >
                      {data.package_name}
                    </Link>
                  )}
                  <Badge variant={confidencePct >= 80 ? "success" : confidencePct >= 50 ? "warning" : "danger"}>
                    {confidencePct}% confidence
                  </Badge>
                  {data.votes > 0 && (
                    <span className="text-xs text-[var(--text-dim)] font-mono">
                      \u2191 {data.votes}
                    </span>
                  )}
                </div>
                <h1 className="text-xl font-semibold tracking-tight leading-snug break-words">
                  {data.pattern}
                </h1>
              </div>
            </div>
          </CardBody>
        </Card>

        {data.full_message && data.full_message !== data.pattern && (
          <Card>
            <CardHeader>
              <span className="text-sm font-medium">Full error message</span>
            </CardHeader>
            <CardBody>
              <pre className="text-xs bg-[var(--bg-input)] border border-[var(--border)] rounded p-3 overflow-x-auto whitespace-pre-wrap break-words text-[var(--text)] font-mono">
                {data.full_message}
              </pre>
            </CardBody>
          </Card>
        )}

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Solution</span>
              {data.source_url && (
                <a
                  href={data.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-[var(--accent)] hover:underline font-mono"
                >
                  source: {data.source || "link"} \u2197
                </a>
              )}
            </div>
          </CardHeader>
          <CardBody>
            <div className="space-y-3 text-sm text-[var(--text)] leading-relaxed">
              {parts.map((p, i) =>
                p.type === "code" ? (
                  <div key={i} className="relative">
                    <pre className="bg-[var(--bg-input)] border border-[var(--border)] rounded p-3 text-xs font-mono text-[var(--accent)] overflow-x-auto">
                      <code>{p.content.trim()}</code>
                    </pre>
                    <div className="absolute top-2 right-2">
                      <CopyButton text={p.content.trim()} />
                    </div>
                  </div>
                ) : (
                  <p key={i} className="whitespace-pre-wrap">
                    {p.content.trim()}
                  </p>
                ),
              )}
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <span className="text-sm font-medium">API access</span>
          </CardHeader>
          <CardBody>
            <p className="text-xs text-[var(--text-dim)] mb-2">
              Get this solution programmatically \u2014 free, no authentication.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-[var(--bg-input)] border border-[var(--border)] rounded px-3 py-2 text-xs text-[var(--accent)] font-mono overflow-x-auto break-all">
                {curlCmd}
              </code>
              <CopyButton text={curlCmd} />
            </div>
          </CardBody>
        </Card>

        <div className="text-xs text-[var(--text-faded)] text-center pt-4 font-mono">
          hash \u00b7 {hash}
        </div>
      </main>

      <Footer />
    </div>
  );
}
