import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 3600;

interface Trending {
  ecosystem: string;
  package_name: string;
  rank: number;
  week_growth_pct: number;
}

interface TrendingResponse {
  generated_at: string;
  trending: Trending[];
}

const BASE = "https://depscope.dev";

function esc(s: string) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

async function fetchTrending(): Promise<TrendingResponse | null> {
  try {
    const r = await fetch("http://127.0.0.1:8000/api/trending?limit=25", { next: { revalidate: 3600 } });
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

const UPDATES = [
  {
    id: "2026-04-19-three-verticals",
    title: "Three new verticals: Error Fix, Compat Matrix, Known Bugs",
    date: "2026-04-19T00:00:00Z",
    link: `${BASE}/updates`,
    summary:
      "DepScope now has searchable error → fix database, stack compatibility matrix, and known bugs per version across 17 ecosystems.",
  },
  {
    id: "2026-04-18-17-ecosystems",
    title: "Expanded to 17 ecosystems",
    date: "2026-04-18T00:00:00Z",
    link: `${BASE}/updates`,
    summary:
      "Added Pub, Hex, Swift, CocoaPods, CPAN, Hackage, CRAN, Conda, Homebrew. Total: 17 ecosystems.",
  },
];

export async function GET() {
  const trending = await fetchTrending();
  const now = new Date().toISOString();

  const trendingEntries = (trending?.trending || []).slice(0, 25).map((t) => {
    const url = `${BASE}/pkg/${t.ecosystem}/${t.package_name}`;
    const id = `${BASE}/feed.xml#trending-${t.ecosystem}-${t.package_name}`;
    const title = `Trending #${t.rank}: ${t.package_name} (${t.ecosystem})`;
    const summary = `${t.package_name} is trending at rank #${t.rank} in ${t.ecosystem} with ${t.week_growth_pct > 0 ? "+" : ""}${t.week_growth_pct.toFixed(1)}% weekly growth.`;
    return `  <entry>
    <id>${esc(id)}</id>
    <title>${esc(title)}</title>
    <link href="${esc(url)}"/>
    <updated>${esc(trending?.generated_at || now)}</updated>
    <summary>${esc(summary)}</summary>
    <author><name>DepScope</name></author>
  </entry>`;
  }).join("\n");

  const updateEntries = UPDATES.map((u) => `  <entry>
    <id>${esc(u.id)}</id>
    <title>${esc(u.title)}</title>
    <link href="${esc(u.link)}"/>
    <updated>${esc(u.date)}</updated>
    <summary>${esc(u.summary)}</summary>
    <author><name>DepScope</name></author>
  </entry>`).join("\n");

  const body = `<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>${BASE}/</id>
  <title>DepScope — Trending Packages & Updates</title>
  <subtitle>Live trending packages across 17 ecosystems, plus product updates.</subtitle>
  <link href="${BASE}/" />
  <link rel="self" href="${BASE}/feed.xml" type="application/atom+xml" />
  <updated>${now}</updated>
  <author><name>DepScope</name><uri>${BASE}</uri></author>
  <generator uri="${BASE}">DepScope</generator>
${updateEntries}
${trendingEntries}
</feed>
`;

  return new NextResponse(body, {
    headers: {
      "Content-Type": "application/atom+xml; charset=utf-8",
      "Cache-Control": "public, max-age=0, s-maxage=3600, stale-while-revalidate=86400",
    },
  });
}
