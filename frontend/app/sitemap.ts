import { MetadataRoute } from "next";

interface QualityPackage {
  ecosystem: string;
  name: string;
  downloads_weekly?: number;
  updated_at?: string | null;
}

interface QualityCounted {
  ecosystem: string;
  name: string;
  count: number;
}

interface QualityError {
  hash: string;
  votes: number;
  confidence: number;
  updated_at: string | null;
}

interface QualityResponse {
  packages: QualityPackage[];
  breaking: QualityCounted[];
  bugs: QualityCounted[];
  errors: QualityError[];
  thresholds: Record<string, number>;
}

interface ComparePair {
  ecosystem: string;
  packages: string[];
}

export const dynamic = "force-dynamic";
export const revalidate = 3600;

const BASE = "https://depscope.dev";

const ECOSYSTEMS = [
  "npm", "pypi", "cargo", "go", "composer", "maven", "nuget",
  "rubygems", "pub", "hex", "swift", "cocoapods", "cpan",
  "hackage", "cran", "conda", "homebrew",
];

async function safeFetch<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url, { next: { revalidate: 3600 } });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

// Long-tail priority: scales from 0.4 up to 0.9 based on record count.
// priority = min(0.4 + 0.1 * min(n, 10), 0.9)
function longTailPriority(count: number): number {
  const n = Math.max(0, Math.floor(count));
  return Math.min(0.4 + 0.1 * Math.min(n, 10), 0.9);
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const staticPages: MetadataRoute.Sitemap = [
    // Top-level
    { url: `${BASE}/`, changeFrequency: "daily", priority: 1.0, lastModified: now },
    // Explore hub
    { url: `${BASE}/explore`, changeFrequency: "daily", priority: 0.9, lastModified: now },
    { url: `${BASE}/explore/trending`, changeFrequency: "daily", priority: 0.9, lastModified: now },
    { url: `${BASE}/explore/errors`, changeFrequency: "weekly", priority: 0.9, lastModified: now },
    { url: `${BASE}/explore/compat`, changeFrequency: "weekly", priority: 0.9, lastModified: now },
    { url: `${BASE}/explore/bugs`, changeFrequency: "weekly", priority: 0.9, lastModified: now },
    { url: `${BASE}/explore/breaking`, changeFrequency: "weekly", priority: 0.9, lastModified: now },
    // Discovery
    { url: `${BASE}/popular`, changeFrequency: "daily", priority: 0.9, lastModified: now },
    { url: `${BASE}/stats`, changeFrequency: "daily", priority: 0.7, lastModified: now },
    // Developer docs
    { url: `${BASE}/api-docs`, changeFrequency: "weekly", priority: 0.9, lastModified: now },
    { url: `${BASE}/integrate`, changeFrequency: "weekly", priority: 0.9, lastModified: now },
    // Content
    { url: `${BASE}/report`, changeFrequency: "monthly", priority: 0.8, lastModified: now },
    { url: `${BASE}/updates`, changeFrequency: "weekly", priority: 0.7, lastModified: now },
    { url: `${BASE}/updates/weekly-report-001`, changeFrequency: "monthly", priority: 0.8, lastModified: now },
    // Legal (EN)
    { url: `${BASE}/legal`, changeFrequency: "monthly", priority: 0.4, lastModified: now },
    { url: `${BASE}/privacy`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
    { url: `${BASE}/terms`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
    { url: `${BASE}/aup`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
    { url: `${BASE}/cookies`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
    { url: `${BASE}/attribution`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
    { url: `${BASE}/dpa`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
    { url: `${BASE}/subprocessors`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
    { url: `${BASE}/security`, changeFrequency: "monthly", priority: 0.4, lastModified: now },
    { url: `${BASE}/security/disclosure`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
    { url: `${BASE}/imprint`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
    { url: `${BASE}/contact`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
    // Auth (public entry)
    { url: `${BASE}/login`, changeFrequency: "monthly", priority: 0.4, lastModified: now },
    // Landing pages
    { url: `${BASE}/check-package-health`, changeFrequency: "monthly", priority: 0.8, lastModified: now },
    { url: `${BASE}/npm-vulnerability-scanner`, changeFrequency: "monthly", priority: 0.8, lastModified: now },
    { url: `${BASE}/supply-chain-security-api`, changeFrequency: "monthly", priority: 0.8, lastModified: now },
    { url: `${BASE}/alternatives-to-snyk-advisor`, changeFrequency: "monthly", priority: 0.8, lastModified: now },
    // Chinese
    { url: `${BASE}/zh`, changeFrequency: "weekly", priority: 0.8, lastModified: now },
    { url: `${BASE}/zh/api-docs`, changeFrequency: "weekly", priority: 0.7, lastModified: now },
    { url: `${BASE}/zh/integrate`, changeFrequency: "weekly", priority: 0.7, lastModified: now },
    { url: `${BASE}/zh/legal`, changeFrequency: "monthly", priority: 0.4, lastModified: now },
    { url: `${BASE}/zh/privacy`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
    { url: `${BASE}/zh/terms`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
    { url: `${BASE}/zh/aup`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
    { url: `${BASE}/zh/cookies`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
    { url: `${BASE}/zh/attribution`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
    { url: `${BASE}/zh/dpa`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
    { url: `${BASE}/zh/subprocessors`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
    { url: `${BASE}/zh/security`, changeFrequency: "monthly", priority: 0.4, lastModified: now },
    { url: `${BASE}/zh/security/disclosure`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
    { url: `${BASE}/zh/imprint`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
  ];

  const ecosystemPages: MetadataRoute.Sitemap = ECOSYSTEMS.map((eco) => ({
    url: `${BASE}/ecosystems/${eco}`,
    changeFrequency: "daily" as const,
    priority: 0.9,
    lastModified: now,
  }));

  // Quality-gated pages: only URLs that pass SEO thresholds make it to Google.
  // Single endpoint returns all 4 lists already filtered by quality gates.
  const quality = await safeFetch<QualityResponse>(
    "http://127.0.0.1:8000/api/sitemap-quality-pages",
  );

  const packagePages: MetadataRoute.Sitemap = [];

  if (quality) {
    // /pkg/{eco}/{name} — only if health_score > 0 AND downloads_weekly > 1000
    for (const p of quality.packages) {
      packagePages.push({
        url: `${BASE}/pkg/${p.ecosystem}/${p.name.split("/").map((s) => encodeURIComponent(s)).join("/")}`,
        changeFrequency: "weekly" as const,
        priority:
          (p.downloads_weekly ?? 0) > 1_000_000 ? 0.8 :
          (p.downloads_weekly ?? 0) > 100_000 ? 0.7 :
          (p.downloads_weekly ?? 0) > 10_000 ? 0.6 : 0.5,
        lastModified: p.updated_at ? new Date(p.updated_at) : now,
      });
    }

    // /breaking/{eco}/{name} — only packages with >= 3 breaking changes
    for (const b of quality.breaking) {
      packagePages.push({
        url: `${BASE}/breaking/${b.ecosystem}/${b.name.split("/").map(encodeURIComponent).join("/")}`,
        changeFrequency: "weekly" as const,
        priority: longTailPriority(b.count),
        lastModified: now,
      });
    }

    // /bugs/{eco}/{name} — only packages with >= 3 bugs
    for (const bg of quality.bugs) {
      packagePages.push({
        url: `${BASE}/bugs/${bg.ecosystem}/${bg.name.split("/").map(encodeURIComponent).join("/")}`,
        changeFrequency: "weekly" as const,
        priority: longTailPriority(bg.count),
        lastModified: now,
      });
    }

    // /error/{hash} — only entries with solution >= 200 chars AND confidence >= 0.7
    for (const e of quality.errors) {
      if (!e.hash) continue;
      // priority grows with votes (proxy for utility)
      const votes = e.votes || 0;
      const priority = Math.min(0.4 + 0.05 * Math.min(votes, 10), 0.9);
      packagePages.push({
        url: `${BASE}/error/${e.hash}`,
        changeFrequency: "monthly" as const,
        priority,
        lastModified: e.updated_at ? new Date(e.updated_at) : now,
      });
    }
  }

  // Compare pairs — curated + dynamic
  const curatedCompare: ComparePair[] = [
    { ecosystem: "npm", packages: ["express", "fastify", "hono"] },
    { ecosystem: "npm", packages: ["react", "vue", "svelte"] },
    { ecosystem: "npm", packages: ["prisma", "drizzle-orm", "typeorm"] },
    { ecosystem: "npm", packages: ["jest", "vitest"] },
    { ecosystem: "npm", packages: ["axios", "got", "node-fetch"] },
    { ecosystem: "npm", packages: ["zod", "yup", "joi"] },
    { ecosystem: "npm", packages: ["webpack", "vite", "turbopack"] },
    { ecosystem: "npm", packages: ["eslint", "biome"] },
    { ecosystem: "npm", packages: ["next", "remix", "astro"] },
    { ecosystem: "npm", packages: ["pnpm", "yarn", "npm"] },
    { ecosystem: "pypi", packages: ["django", "flask", "fastapi"] },
    { ecosystem: "pypi", packages: ["numpy", "pandas", "polars"] },
    { ecosystem: "pypi", packages: ["requests", "httpx", "aiohttp"] },
    { ecosystem: "pypi", packages: ["pytest", "unittest"] },
    { ecosystem: "pypi", packages: ["sqlalchemy", "tortoise-orm"] },
    { ecosystem: "cargo", packages: ["actix-web", "axum", "rocket"] },
    { ecosystem: "cargo", packages: ["serde", "serde_json"] },
    { ecosystem: "cargo", packages: ["tokio", "async-std"] },
    { ecosystem: "cargo", packages: ["reqwest", "hyper"] },
    { ecosystem: "cargo", packages: ["clap", "structopt"] },
  ];
  const dynamicCompare =
    (await safeFetch<ComparePair[]>(
      "http://127.0.0.1:8000/api/sitemap-compare-pairs?limit=20",
    )) || [];

  const comparePairs = [...curatedCompare, ...dynamicCompare];
  const seen = new Set<string>();
  const comparePages: MetadataRoute.Sitemap = comparePairs
    .map((p) => {
      const slug = p.packages.join("-vs-");
      const key = `${p.ecosystem}/${slug}`;
      if (seen.has(key)) return null;
      seen.add(key);
      return {
        url: `${BASE}/compare/${p.ecosystem}/${slug}`,
        changeFrequency: "weekly" as const,
        priority: 0.7,
        lastModified: now,
      };
    })
    .filter(Boolean) as MetadataRoute.Sitemap;

  return [
    ...staticPages,
    ...ecosystemPages,
    ...comparePages,
    ...packagePages,
  ];
}
