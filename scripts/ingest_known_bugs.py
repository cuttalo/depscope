#!/usr/bin/env python3
"""Ingest known bugs from GitHub Issues for top npm packages.

Simplified single-ecosystem version focused on npm packages with >1M weekly downloads.
Implements flexible label search and excludes packages already covered in known_bugs.

Idempotent: ON CONFLICT DO NOTHING via unique (ecosystem, package_name, bug_id).
"""
import asyncio
import os
import re
import sys
from typing import Optional

import aiohttp
import asyncpg


# ─── Config ───────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")
GH_TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
ECOSYSTEM = "npm"
DOWNLOAD_THRESHOLD = 1_000_000
LIMIT = 5
PER_PACKAGE_ISSUES = 10

# Flexible label search (tries in order, stops at first non-empty result)
BUG_LABELS = ["bug", "type:bug", "kind/bug", "Type: Bug"]
# Fallback: filter by title keywords if all labels fail
TITLE_KEYWORDS = ["bug", "fix", "error", "crash", "broken", "fail"]


# ─── Helpers ──────────────────────────────────────────────────────────────
_VERSION_PATTERNS = [
    re.compile(r"version[^\w\n]{0,4}([0-9]+(?:\.[0-9]+){1,3}(?:[-.+][\w.]+)?)", re.I),
    re.compile(r"v([0-9]+\.[0-9]+(?:\.[0-9]+)?)\b"),
    re.compile(r"\b([0-9]+\.[0-9]+\.[0-9]+)\b"),
]

_FIXED_PATTERNS = [
    re.compile(r"fixed in[^\w\n]{0,4}v?([0-9]+(?:\.[0-9]+){1,3}(?:[-.+][\w.]+)?)", re.I),
    re.compile(r"released in[^\w\n]{0,4}v?([0-9]+(?:\.[0-9]+){1,3})", re.I),
    re.compile(r"resolved in[^\w\n]{0,4}v?([0-9]+(?:\.[0-9]+){1,3})", re.I),
]


def normalize_version(raw: str) -> str:
    """Strip v-prefix and normalize separators."""
    s = raw.strip().lstrip("vV")
    return s.replace("_", ".").replace(" ", "")


def extract_version(text: str) -> Optional[str]:
    if not text:
        return None
    for pat in _VERSION_PATTERNS:
        m = pat.search(text)
        if m:
            return normalize_version(m.group(1))
    return None


def extract_fixed_version(text: str) -> Optional[str]:
    if not text:
        return None
    for pat in _FIXED_PATTERNS:
        m = pat.search(text)
        if m:
            return normalize_version(m.group(1))
    return None


def parse_github_repo(url: Optional[str]) -> Optional[tuple[str, str]]:
    """Extract (owner, name) from github.com URL."""
    if not url:
        return None
    m = re.search(r"github\.com[/:]([^/]+)/([^/.]+)", url, re.I)
    if m:
        return m.group(1), m.group(2).replace(".git", "")
    return None


def pick_severity(labels: list[str]) -> str:
    """Map GitHub labels to severity bucket."""
    labels_lower = [lbl.lower() for lbl in labels]
    if any("critical" in lbl or "p0" in lbl for lbl in labels_lower):
        return "critical"
    if any("high" in lbl or "p1" in lbl for lbl in labels_lower):
        return "high"
    if any("low" in lbl or "minor" in lbl for lbl in labels_lower):
        return "low"
    return "medium"


async def fetch_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    headers: dict,
    params: Optional[dict] = None,
    retries: int = 3,
) -> Optional[list]:
    """Fetch JSON from URL with exponential backoff."""
    for attempt in range(retries):
        try:
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list):
                        return data
                    return None
                if resp.status in (429, 502, 503):
                    await asyncio.sleep(2 ** attempt)
                    continue
                return None
        except Exception:
            await asyncio.sleep(2 ** attempt)
    return None


async def fetch_bug_issues(
    session: aiohttp.ClientSession,
    owner: str,
    repo: str,
    headers: dict,
) -> list[dict]:
    """Fetch closed issues with flexible label search.

    Tries multiple bug labels in order (bug, type:bug, kind/bug, Type: Bug).
    Falls back to keyword search in title if all labels yield zero results.
    """
    base_url = f"https://api.github.com/repos/{owner}/{repo}/issues"

    # Try each label in order
    for label in BUG_LABELS:
        params = {
            "state": "closed",
            "labels": label,
            "per_page": PER_PACKAGE_ISSUES,
            "sort": "created",
            "direction": "desc",
        }
        data = await fetch_with_retry(session, base_url, headers, params)
        if data:
            # Filter out pull requests
            issues = [i for i in data if isinstance(i, dict) and not i.get("pull_request")]
            if issues:
                return issues

    # Fallback: fetch recent closed issues and filter by title keywords
    params = {
        "state": "closed",
        "per_page": 20,
        "sort": "created",
        "direction": "desc",
    }
    data = await fetch_with_retry(session, base_url, headers, params)
    if data:
        issues = [
            i for i in data
            if isinstance(i, dict)
            and not i.get("pull_request")
            and any(kw in (i.get("title") or "").lower() for kw in TITLE_KEYWORDS)
        ]
        return issues[:PER_PACKAGE_ISSUES]

    return []


async def process_package(
    session: aiohttp.ClientSession,
    pkg: dict,
    headers: dict,
    pool: asyncpg.Pool,
) -> int:
    """Fetch and insert bugs for one package. Returns insert count."""
    repo = parse_github_repo(pkg.get("repository"))
    if not repo:
        print(f"  ⚠ {pkg['name']}: no GitHub repo", file=sys.stderr)
        return 0

    owner, name = repo
    try:
        issues = await fetch_bug_issues(session, owner, name, headers)
    except Exception as e:
        print(f"  ⚠ {pkg['name']}: fetch failed — {e}", file=sys.stderr)
        return 0

    if not issues:
        print(f"  ⚠ {pkg['name']}: zero bug issues found", file=sys.stderr)
        return 0

    inserted = 0
    async with pool.acquire() as conn:
        for issue in issues:
            try:
                number = issue.get("number")
                title = (issue.get("title") or "").strip()
                body = (issue.get("body") or "")[:20000]

                if not title or not number or len(title) < 8:
                    continue

                labels = [
                    lab.get("name") if isinstance(lab, dict) else str(lab)
                    for lab in (issue.get("labels") or [])
                ]

                severity = pick_severity(labels)
                affected = extract_version(body) or extract_version(title)
                fixed = extract_fixed_version(body)
                bug_id = f"github:{number}"
                status = "fixed" if issue.get("state") == "closed" else "open"
                source_url = issue.get("html_url") or f"https://github.com/{owner}/{name}/issues/{number}"

                res = await conn.execute(
                    """
                    INSERT INTO known_bugs(
                        package_id, ecosystem, package_name,
                        affected_version, fixed_version, bug_id,
                        title, description, severity, status,
                        source, source_url, labels
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
                    )
                    ON CONFLICT (ecosystem, package_name, bug_id) DO NOTHING
                    """,
                    pkg["id"],
                    pkg["ecosystem"],
                    pkg["name"],
                    affected,
                    fixed,
                    bug_id,
                    title[:2000],
                    body[:10000] or None,
                    severity,
                    status,
                    "github_issues",
                    source_url,
                    labels[:20],
                )

                # asyncpg returns tag like "INSERT 0 1" → count insertions
                if res and res.endswith(" 1"):
                    inserted += 1

            except Exception as e:
                print(f"  ⚠ {pkg['name']}#{issue.get('number')}: insert failed — {e}", file=sys.stderr)

    if inserted:
        print(f"  ✓ {pkg['name']}: +{inserted} bugs")

    return inserted


async def main() -> int:
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        return 1

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3)

    try:
        # FIX #1: Exclude packages already covered in known_bugs via NOT EXISTS
        query = """
            SELECT p.id, p.name, p.ecosystem, p.repository, p.downloads_weekly
            FROM packages p
            WHERE p.ecosystem = $1
              AND p.downloads_weekly > $2
              AND p.repository LIKE '%github.com%'
              AND NOT EXISTS (
                  SELECT 1 FROM known_bugs kb
                  WHERE kb.ecosystem = p.ecosystem
                    AND kb.package_name = p.name
              )
            ORDER BY p.downloads_weekly DESC
            LIMIT $3
        """

        packages = await pool.fetch(query, ECOSYSTEM, DOWNLOAD_THRESHOLD, LIMIT)

        if not packages:
            print(f"No uncovered {ECOSYSTEM} packages found (threshold={DOWNLOAD_THRESHOLD:,}, limit={LIMIT})")
            print("BUGS_INGESTED=0  PACKAGES_PROCESSED=0  ERRORS=0")
            return 0

        print(f"Found {len(packages)} uncovered {ECOSYSTEM} packages to process")

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "depscope-ingest/1.0",
        }

        if GH_TOKEN:
            headers["Authorization"] = f"Bearer {GH_TOKEN}"
            print("Using authenticated GitHub token")
        else:
            print("⚠ No GH_TOKEN — using unauthenticated (60 req/hour limit)", file=sys.stderr)

        total_inserted = 0
        total_errors = 0

        async with aiohttp.ClientSession() as session:
            for pkg in packages:
                try:
                    count = await process_package(session, pkg, headers, pool)
                    total_inserted += count
                except Exception as e:
                    print(f"  ⚠ {pkg['name']}: package processing failed — {e}", file=sys.stderr)
                    total_errors += 1

        print(f"\nBUGS_INGESTED={total_inserted}  PACKAGES_PROCESSED={len(packages)}  ERRORS={total_errors}")
        return 0

    finally:
        await pool.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
