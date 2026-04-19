#!/usr/bin/env python3
"""
DepScope — Weekly Package Health Report generator.

Runs weekly (cron: 0 10 * * 1). Queries the DepScope DB for health stats and
regenerates:

  1. Markdown: /home/deploy/depscope/content/weekly-report-NNN.md
  2. SSR page: /home/deploy/depscope/frontend/app/updates/weekly-report-NNN/page.tsx
  3. Sitemap:  /home/deploy/depscope/frontend/app/sitemap.ts (appends the new URL)

Idempotent: re-running for the same week overwrites that week's files.
Report #001 (hand-written commentary) is NEVER overwritten — this script only
generates #002 onwards. To force a specific number: REPORT_NUMBER=5 python3 ...

Uses asyncpg (already in the project venv) — run with:
    /home/deploy/depscope/.venv/bin/python scripts/generate_weekly_report.py
"""
from __future__ import annotations
import os
import re
import sys
import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

ROOT = Path("/home/deploy/depscope")
CONTENT_DIR = ROOT / "content"
UPDATES_DIR = ROOT / "frontend" / "app" / "updates"
SITEMAP = ROOT / "frontend" / "app" / "sitemap.ts"

DB_URL = os.environ.get(
    "DB_URL", "postgresql://depscope:depscope2026@localhost:5432/depscope"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fmt_int(n) -> str:
    try:
        return f"{int(n or 0):,}"
    except (TypeError, ValueError):
        return "0"

def next_report_number() -> int:
    """Highest existing weekly-report-NNN dir under /updates, plus 1. Never
    overwrites #001 (hand-curated)."""
    if not UPDATES_DIR.exists():
        return 2
    pat = re.compile(r"^weekly-report-(\d+)$")
    nums = [int(m.group(1)) for d in UPDATES_DIR.iterdir() if (m := pat.match(d.name))]
    n = (max(nums) + 1) if nums else 2
    return max(n, 2)  # never touch #001

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

async def gather(conn: asyncpg.Connection) -> dict:
    total_packages = await conn.fetchval("SELECT COUNT(*) FROM packages")
    hb = await conn.fetchrow("""
        SELECT
          COUNT(*) FILTER (WHERE health_score > 0 AND health_score < 40) AS critical,
          COUNT(*) FILTER (WHERE health_score >= 40 AND health_score < 60) AS poor,
          COUNT(*) FILTER (WHERE health_score >= 60 AND health_score < 80) AS fair,
          COUNT(*) FILTER (WHERE health_score >= 80) AS good,
          COUNT(*) FILTER (WHERE health_score IS NULL OR health_score = 0) AS unknown
        FROM packages
    """)
    total_vulns = await conn.fetchval("SELECT COUNT(*) FROM vulnerabilities")
    vuln_popular = await conn.fetch("""
        SELECT p.ecosystem, p.name, COUNT(v.id) AS vulns, p.downloads_weekly
        FROM packages p JOIN vulnerabilities v ON v.package_id = p.id
        WHERE p.downloads_weekly > 100000
        GROUP BY p.id, p.ecosystem, p.name, p.downloads_weekly
        ORDER BY COUNT(v.id) DESC, p.downloads_weekly DESC
        LIMIT 15
    """)
    zombies = await conn.fetch("""
        SELECT ecosystem, name, downloads_weekly, deprecated_message
        FROM packages
        WHERE deprecated = true AND downloads_weekly > 100000
        ORDER BY downloads_weekly DESC
        LIMIT 15
    """)
    worst = await conn.fetch("""
        SELECT ecosystem, name, health_score, downloads_weekly
        FROM packages
        WHERE downloads_weekly > 500000 AND health_score IS NOT NULL AND health_score > 0
        ORDER BY health_score ASC
        LIMIT 10
    """)
    breaking = await conn.fetch("""
        SELECT p.ecosystem, p.name, bc.from_version, bc.to_version, bc.change_type,
               LEFT(bc.description, 180) AS description
        FROM breaking_changes bc JOIN packages p ON p.id = bc.package_id
        WHERE p.downloads_weekly > 100000
        ORDER BY p.downloads_weekly DESC
        LIMIT 15
    """)
    ecosystems = await conn.fetch("""
        SELECT ecosystem, COUNT(*) AS pkgs,
               ROUND(AVG(health_score)::numeric, 1) AS avg_health,
               COUNT(*) FILTER (WHERE deprecated = true) AS deprecated
        FROM packages
        WHERE health_score > 0
        GROUP BY ecosystem
        HAVING COUNT(*) >= 50
        ORDER BY avg_health DESC
    """)
    popular_with_vulns = await conn.fetchval("""
        SELECT COUNT(DISTINCT p.id) FROM packages p
        JOIN vulnerabilities v ON v.package_id = p.id
        WHERE p.downloads_weekly > 1000000
    """)
    zombie_summary = await conn.fetchrow("""
        SELECT COUNT(*) AS cnt, COALESCE(SUM(downloads_weekly), 0) AS total_dl
        FROM packages WHERE deprecated = true AND downloads_weekly > 1000000
    """)
    return {
        "total_packages": total_packages,
        "health_buckets": dict(hb),
        "total_vulns": total_vulns,
        "vuln_popular": [dict(r) for r in vuln_popular],
        "zombies": [dict(r) for r in zombies],
        "worst": [dict(r) for r in worst],
        "breaking": [dict(r) for r in breaking],
        "ecosystems": [dict(r) for r in ecosystems],
        "popular_with_vulns": popular_with_vulns,
        "zombie_summary": (zombie_summary["cnt"], zombie_summary["total_dl"]),
    }

# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_markdown(n: int, date_iso: str, d: dict) -> str:
    hb = d["health_buckets"]
    lines = [
        "---",
        f'title: "The State of Package Health: Weekly Report #{n:03d}"',
        f"slug: weekly-report-{n:03d}",
        f"date: {date_iso}",
        "author: DepScope",
        "tags: [package-health, supply-chain, weekly-report]",
        f'description: "Fresh package health numbers from the DepScope index — {fmt_int(d["total_packages"])} packages across 17 ecosystems."',
        "---",
        "",
        f"# The State of Package Health — Weekly Report #{n:03d}",
        "",
        f"Snapshot date: **{date_iso}**. Index: **{fmt_int(d['total_packages'])} packages**, "
        f"**{fmt_int(d['total_vulns'])} vulnerabilities** tracked.",
        "",
        "## Health distribution",
        "",
        "| Bucket | Count |",
        "|---|---:|",
        f"| Critical (< 40)   | {fmt_int(hb['critical'])} |",
        f"| Poor (40–59)      | {fmt_int(hb['poor'])} |",
        f"| Fair (60–79)      | {fmt_int(hb['fair'])} |",
        f"| Good (80+)        | {fmt_int(hb['good'])} |",
        f"| Unknown/unscored  | {fmt_int(hb['unknown'])} |",
        "",
        "## Popular packages with open vulnerabilities",
        "",
        f"**{fmt_int(d['popular_with_vulns'])}** packages with >1M weekly downloads "
        f"have at least one tracked advisory.",
        "",
        "| Ecosystem | Package | Vulns | Weekly downloads |",
        "|---|---|---:|---:|",
    ]
    for r in d["vuln_popular"]:
        lines.append(
            f"| {r['ecosystem']} | `{r['name']}` | {r['vulns']} | {fmt_int(r['downloads_weekly'])} |"
        )
    lines += ["", "## Zombie packages (deprecated, still installed)", ""]
    cnt, total_dl = d["zombie_summary"]
    lines.append(
        f"**{fmt_int(cnt)} deprecated packages** with >1M weekly downloads — "
        f"combined downloads: {fmt_int(total_dl)}/week."
    )
    lines += ["", "| Package | Weekly downloads | Why it's deprecated |", "|---|---:|---|"]
    for r in d["zombies"]:
        msg = (r["deprecated_message"] or "").replace("|", "/").strip()[:120]
        lines.append(f"| `{r['name']}` | {fmt_int(r['downloads_weekly'])} | {msg} |")
    lines += ["", "## Worst health scores among popular packages", "",
              "| Package | Health | Weekly downloads |", "|---|---:|---:|"]
    for r in d["worst"]:
        lines.append(
            f"| `{r['name']}` ({r['ecosystem']}) | {r['health_score']} | {fmt_int(r['downloads_weekly'])} |"
        )
    lines += ["", "## Ecosystem comparison (avg health)", "",
              "| Ecosystem | Packages | Avg health | Deprecated |", "|---|---:|---:|---:|"]
    for r in d["ecosystems"]:
        lines.append(
            f"| {r['ecosystem']} | {fmt_int(r['pkgs'])} | {float(r['avg_health']):.1f} | {r['deprecated']} |"
        )
    lines += ["", "## Breaking changes in popular packages", ""]
    for r in d["breaking"][:10]:
        lines.append(
            f"- **{r['name']}** ({r['ecosystem']}) `{r['from_version']} → {r['to_version']}` "
            f"*{r['change_type']}* — {r['description']}"
        )
    lines += ["", "## Try it yourself", "",
              "```bash",
              "curl -s https://depscope.dev/api/check/npm/next | jq '.health_score'",
              "curl -s https://depscope.dev/api/check/pypi/pydantic | jq '.deprecated'",
              "```", ""]
    return "\n".join(lines)


def render_tsx(n: int, date_iso: str, d: dict) -> str:
    slug = f"weekly-report-{n:03d}"
    title = f"Weekly Package Health Report #{n:03d}"
    description = (
        f"DepScope weekly snapshot — {fmt_int(d['total_packages'])} packages indexed, "
        f"{fmt_int(d['total_vulns'])} vulnerabilities tracked, live numbers by ecosystem."
    )
    url = f"https://depscope.dev/updates/{slug}"
    hb = d["health_buckets"]
    vuln_rows = [
        {"eco": r["ecosystem"], "name": r["name"], "vulns": r["vulns"],
         "dl": int(r["downloads_weekly"] or 0)}
        for r in d["vuln_popular"]
    ]
    zombie_rows = [
        {"name": r["name"], "dl": int(r["downloads_weekly"] or 0),
         "msg": (r["deprecated_message"] or "").strip()[:160]}
        for r in d["zombies"]
    ]
    worst_rows = [
        {"name": r["name"], "eco": r["ecosystem"],
         "score": r["health_score"], "dl": int(r["downloads_weekly"] or 0)}
        for r in d["worst"]
    ]
    eco_rows = [
        {"eco": r["ecosystem"], "pkgs": int(r["pkgs"]),
         "avg": float(r["avg_health"]), "dep": int(r["deprecated"])}
        for r in d["ecosystems"]
    ]
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "datePublished": date_iso,
        "dateModified": date_iso,
        "author": {"@type": "Organization", "name": "DepScope", "url": "https://depscope.dev"},
        "publisher": {"@type": "Organization", "name": "DepScope"},
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
    }

    tsx = (
        'import type { Metadata } from "next";\n'
        'import Link from "next/link";\n'
        'import { Card, CardBody, PageHeader, Section, Footer, Badge } from "../../../components/ui";\n\n'
        f"const TITLE = {json.dumps(title)};\n"
        f"const DESCRIPTION = {json.dumps(description)};\n"
        f"const DATE_PUBLISHED = {json.dumps(date_iso)};\n"
        f"const URL = {json.dumps(url)};\n\n"
        "export const metadata: Metadata = {\n"
        "  title: TITLE,\n"
        "  description: DESCRIPTION,\n"
        "  openGraph: {\n"
        "    title: TITLE,\n"
        "    description: DESCRIPTION,\n"
        "    url: URL,\n"
        '    siteName: "DepScope",\n'
        '    type: "article",\n'
        "    publishedTime: DATE_PUBLISHED,\n"
        '    authors: ["DepScope"],\n'
        "  },\n"
        '  twitter: { card: "summary_large_image", title: TITLE, description: DESCRIPTION },\n'
        "  alternates: { canonical: URL },\n"
        "  robots: { index: true, follow: true },\n"
        "};\n\n"
        f"const jsonLd = {json.dumps(jsonld)};\n\n"
        f"const HEALTH = {json.dumps([{'label': 'Critical (< 40)', 'count': int(hb['critical'])}, {'label': 'Poor (40–59)', 'count': int(hb['poor'])}, {'label': 'Fair (60–79)', 'count': int(hb['fair'])}, {'label': 'Good (80+)', 'count': int(hb['good'])}, {'label': 'Unknown', 'count': int(hb['unknown'])}])};\n"
        f"const VULN = {json.dumps(vuln_rows)};\n"
        f"const ZOMBIES = {json.dumps(zombie_rows)};\n"
        f"const WORST = {json.dumps(worst_rows)};\n"
        f"const ECO = {json.dumps(eco_rows)};\n"
        f"const TOTAL_PACKAGES = {int(d['total_packages'])};\n"
        f"const TOTAL_VULNS = {int(d['total_vulns'])};\n\n"
        'function fmt(n: number) { return n.toLocaleString("en-US"); }\n\n'
        "export default function Page() {\n"
        "  return (\n"
        "    <>\n"
        '      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />\n'
        "      <PageHeader\n"
        f'        eyebrow={{`Weekly Report #{n:03d} · Published ${{DATE_PUBLISHED}}`}}\n'
        '        title="The State of Package Health"\n'
        '        description={`Snapshot of ${fmt(TOTAL_PACKAGES)} packages across 17 ecosystems.`}\n'
        '        actions={<Badge variant="info">Weekly</Badge>}\n'
        "      />\n"
        "      <Section>\n"
        "        <Card>\n"
        "          <CardBody>\n"
        '            <article className="max-w-3xl space-y-6">\n'
        '              <p className="text-[var(--text-dim)] leading-7">\n'
        f"                Automated snapshot for report #{n:03d}. The DepScope index tracks{{' '}}\n"
        "                <strong>{fmt(TOTAL_PACKAGES)}</strong> packages and <strong>{fmt(TOTAL_VULNS)}</strong> vulnerabilities as of {DATE_PUBLISHED}.\n"
        '                See <Link href="/updates/weekly-report-001" className="text-[var(--accent)] underline">report #001</Link> for methodology.\n'
        "              </p>\n\n"
        '              <h2 className="text-xl font-semibold mt-6">Health distribution</h2>\n'
        "              <DataTable cols={[{k:\"label\",l:\"Bucket\"},{k:\"count\",l:\"Count\",r:true,f:fmt}]} rows={HEALTH} />\n\n"
        '              <h2 className="text-xl font-semibold mt-6">Popular but vulnerable</h2>\n'
        "              <DataTable cols={[{k:\"eco\",l:\"Ecosystem\",b:true},{k:\"name\",l:\"Package\",mono:true,link:(r:any)=>`/pkg/${r.eco}/${r.name}`},{k:\"vulns\",l:\"Vulns\",r:true},{k:\"dl\",l:\"Weekly\",r:true,f:fmt}]} rows={VULN} />\n\n"
        '              <h2 className="text-xl font-semibold mt-6">Zombie packages</h2>\n'
        "              <DataTable cols={[{k:\"name\",l:\"Package\",mono:true},{k:\"dl\",l:\"Weekly\",r:true,f:fmt},{k:\"msg\",l:\"Why\"}]} rows={ZOMBIES} />\n\n"
        '              <h2 className="text-xl font-semibold mt-6">Worst health, popular</h2>\n'
        "              <DataTable cols={[{k:\"name\",l:\"Package\",mono:true},{k:\"score\",l:\"Health\",r:true,danger:true},{k:\"dl\",l:\"Weekly\",r:true,f:fmt}]} rows={WORST} />\n\n"
        '              <h2 className="text-xl font-semibold mt-6">Ecosystem comparison</h2>\n'
        "              <DataTable cols={[{k:\"eco\",l:\"Ecosystem\"},{k:\"pkgs\",l:\"Packages\",r:true,f:fmt},{k:\"avg\",l:\"Avg health\",r:true,f:(x:number)=>x.toFixed(1)},{k:\"dep\",l:\"Deprecated\",r:true}]} rows={ECO} />\n\n"
        '              <p className="text-[var(--text-dim)] text-sm mt-8">\n'
        '                Previous reports: <Link href="/updates" className="text-[var(--accent)] underline">all updates</Link>.\n'
        '                Raw data via <Link href="/api-docs" className="text-[var(--accent)] underline">API</Link>.\n'
        "              </p>\n"
        "            </article>\n"
        "          </CardBody>\n"
        "        </Card>\n"
        "      </Section>\n"
        "      <Footer />\n"
        "    </>\n"
        "  );\n"
        "}\n\n"
        "type Col = { k: string; l: string; r?: boolean; mono?: boolean; b?: boolean; link?: (row: any) => string; f?: (v: any) => string; danger?: boolean };\n"
        "function DataTable({ cols, rows }: { cols: Col[]; rows: any[] }) {\n"
        "  return (\n"
        '    <div className="overflow-x-auto border border-[var(--border)] rounded-lg my-4">\n'
        '      <table className="min-w-full text-sm">\n'
        "        <thead><tr>\n"
        '          {cols.map(c => <th key={c.l} className={`px-4 py-2 text-[11px] uppercase tracking-wider font-medium text-[var(--text-dim)] border-b border-[var(--border)] ${c.r ? "text-right" : "text-left"}`}>{c.l}</th>)}\n'
        "        </tr></thead>\n"
        "        <tbody>\n"
        "          {rows.map((row, i) => (\n"
        "            <tr key={i}>\n"
        "              {cols.map(c => {\n"
        "                const v = row[c.k];\n"
        "                const display = c.f ? c.f(v) : String(v);\n"
        '                const cls = `px-4 py-2 border-b border-[var(--border)] ${c.r ? "text-right tabular-nums" : ""} ${c.mono ? "font-mono" : ""} ${c.danger ? "text-red-500" : ""}`;\n'
        "                return <td key={c.l} className={cls}>{\n"
        "                  c.b ? <Badge variant=\"neutral\">{display}</Badge> :\n"
        "                  c.link ? <Link href={c.link(row)} className=\"text-[var(--accent)] hover:underline\">{display}</Link> :\n"
        "                  display\n"
        "                }</td>;\n"
        "              })}\n"
        "            </tr>\n"
        "          ))}\n"
        "        </tbody>\n"
        "      </table>\n"
        "    </div>\n"
        "  );\n"
        "}\n"
    )
    return tsx


def update_sitemap(n: int) -> bool:
    """String-based, regex-free. Inserts the new URL right after the most
    recent weekly-report entry (or after the /updates anchor)."""
    src = SITEMAP.read_text()
    needle = f"weekly-report-{n:03d}"
    if needle in src:
        return False
    new_line = (
        f'    {{ url: `${{BASE}}/updates/weekly-report-{n:03d}`, '
        f'changeFrequency: "monthly", priority: 0.8, lastModified: now }},\n'
    )
    lines = src.splitlines(keepends=True)
    insert_idx = None
    for i, line in enumerate(lines):
        if "/updates/weekly-report-" in line:
            insert_idx = i + 1  # keep scanning to find the last one
    if insert_idx is None:
        # fall back to /updates anchor
        for i, line in enumerate(lines):
            if "`${BASE}/updates`" in line:
                insert_idx = i + 1
                break
    if insert_idx is None:
        return False
    lines.insert(insert_idx, new_line)
    SITEMAP.write_text("".join(lines))
    return True

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def _run():
    n = int(os.environ.get("REPORT_NUMBER") or next_report_number())
    if n == 1:
        print("[skip] report #001 is hand-curated — use REPORT_NUMBER=2+ to regenerate", file=sys.stderr)
        return 1
    date_iso = datetime.now(timezone.utc).date().isoformat()

    conn = await asyncpg.connect(DB_URL)
    try:
        data = await gather(conn)
    finally:
        await conn.close()

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = CONTENT_DIR / f"weekly-report-{n:03d}.md"
    md_path.write_text(render_markdown(n, date_iso, data))

    page_dir = UPDATES_DIR / f"weekly-report-{n:03d}"
    page_dir.mkdir(parents=True, exist_ok=True)
    (page_dir / "page.tsx").write_text(render_tsx(n, date_iso, data))

    updated = update_sitemap(n)

    print(f"[ok] report #{n:03d} written")
    print(f"     md:   {md_path}")
    print(f"     tsx:  {page_dir/'page.tsx'}")
    print(f"     sitemap updated: {updated}")
    print(
        f"     numbers: {fmt_int(data['total_packages'])} pkgs, "
        f"{fmt_int(data['total_vulns'])} vulns, "
        f"{fmt_int(data['popular_with_vulns'])} popular-with-vulns, "
        f"{fmt_int(data['zombie_summary'][0])} deprecated >1M"
    )

    # --- Dev.to auto-publish ---------------------------------------------
    # SKIP_DEVTO=1 disables; DEVTO_API_KEY env overrides default key.
    if os.environ.get("SKIP_DEVTO") != "1":
        publish_result = publish_to_devto(n, date_iso, md_path)
        print(f"     devto: {publish_result}")

    return 0


def publish_to_devto(n: int, date_iso: str, md_path) -> str:
    """POST the freshly generated markdown to Dev.to as a published article.

    Dev.to doesn't upsert by slug, so re-runs create duplicates. That's fine:
    this only runs on a new report number and REPORT_NUMBER is monotone.
    """
    import requests

    api_key = os.environ.get("DEVTO_API_KEY", "VuqtfNaAJifTz4h2ckG3sCdG")

    body = md_path.read_text()
    # Strip YAML front-matter — Dev.to expects plain markdown body + fields.
    if body.startswith("---"):
        parts = body.split("---", 2)
        if len(parts) >= 3:
            body = parts[2].lstrip()

    canonical = f"https://depscope.dev/updates/weekly-report-{n:03d}"
    title = f"The State of Package Health: Weekly Report #{n:03d}"

    payload = {
        "article": {
            "title": title,
            "published": True,
            "body_markdown": body,
            "tags": ["security", "webdev", "devops", "opensource"],
            "canonical_url": canonical,
            "description": (
                f"Weekly package health numbers from the DepScope index — "
                f"snapshot {date_iso}."
            ),
        }
    }
    try:
        r = requests.post(
            "https://dev.to/api/articles",
            headers={"api-key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if 200 <= r.status_code < 300:
            d = r.json()
            return f"published id={d.get('id')} url={d.get('url')}"
        return f"FAILED status={r.status_code} body={r.text[:200]!r}"
    except Exception as e:
        return f"FAILED exception={e!r}"


if __name__ == "__main__":
    sys.exit(asyncio.run(_run()))
