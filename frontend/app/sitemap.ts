import { MetadataRoute } from "next";

interface PackageEntry {
  ecosystem: string;
  name: string;
  downloads_weekly?: number;
  updated_at?: string | null;
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

// Upper bound for dynamic pkg URLs per sitemap file (Google limit 50k).
const MAX_PKG_URLS = 10000;

async function safeFetch<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url, { next: { revalidate: 3600 } });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
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
    // Legal
    { url: `${BASE}/privacy`, changeFrequency: "monthly", priority: 0.3, lastModified: now },
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
  ];

  const ecosystemPages: MetadataRoute.Sitemap = ECOSYSTEMS.map((eco) => ({
    url: `${BASE}/ecosystems/${eco}`,
    changeFrequency: "daily" as const,
    priority: 0.9,
    lastModified: now,
  }));

  // Top packages by downloads (weekly)
  let packagePages: MetadataRoute.Sitemap = [];
  const packages = await safeFetch<PackageEntry[]>(
    `http://127.0.0.1:8000/api/sitemap-packages?order=downloads&limit=${MAX_PKG_URLS}`,
  );
  if (packages && packages.length) {
    packagePages = packages.map((p) => ({
      url: `${BASE}/pkg/${p.ecosystem}/${p.name.split("/").map(s => encodeURIComponent(s)).join("/")}`,
      changeFrequency: "weekly" as const,
      priority:
        (p.downloads_weekly ?? 0) > 1_000_000 ? 0.8 :
        (p.downloads_weekly ?? 0) > 100_000 ? 0.7 :
        (p.downloads_weekly ?? 0) > 10_000 ? 0.6 : 0.5,
      lastModified: p.updated_at ? new Date(p.updated_at) : now,
    }));
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
