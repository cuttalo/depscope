#!/usr/bin/env python3
"""Nightly GitHub changelog → breaking_changes crawler.

For each top-N package per ecosystem that has a GitHub repository URL,
fetch the last 30 releases via GitHub API, scan the body for BREAKING
sections, and insert entries into breaking_changes.

Uses GH_TOKEN (5000 req/h). Idempotent (desc_hash UNIQUE).

ENV:
  TARGET_PER_ECO   default 100
  CONCURRENCY      default 4
  MAX_PER_PKG      default 5  (cap per release body)
"""
import asyncio
import hashlib
import os
import re
import sys
import time

sys.path.insert(0, "/home/deploy/depscope")

import aiohttp
import asyncpg

from api.config import DATABASE_URL

GH_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
TARGET_PER_ECO = int(os.environ.get("TARGET_PER_ECO", "100"))
CONCURRENCY = int(os.environ.get("CONCURRENCY", "4"))
MAX_PER_PKG = int(os.environ.get("MAX_PER_PKG", "5"))

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "DepScope/1.0 (+https://depscope.dev)",
    "X-GitHub-Api-Version": "2022-11-28",
}
if GH_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GH_TOKEN}"

BREAKING_HEADER_RE = re.compile(
    r"(?im)^[\s>#*\-]*(?:⚠+\s*)?(?:\*\*)?\s*(?:BREAKING(?:\s+CHANGES?)?|Breaking(?:\s+Change(?:s)?)?|Major(?:\s+breaking)?)\b",
)
BULLET_RE = re.compile(r"^[\s>]*[-*+]\s+(.+?)(?=\n[\s>]*[-*+]\s+|\n\n|\Z)", re.DOTALL | re.MULTILINE)


def extract_breaking_bullets(body: str) -> list[str]:
    """Scan release body. Return up to MAX_PER_PKG bullet items from BREAKING section(s)."""
    if not body:
        return []
    # Find all BREAKING headers, capture the block until next ## or end
    results: list[str] = []
    for m in BREAKING_HEADER_RE.finditer(body):
        start = m.end()
        # Block ends at next header (## or ###) or EOF
        tail = body[start:]
        # crude: stop at next heading that starts with # at line-start
        stop_m = re.search(r"\n#{1,4}\s+\w", tail)
        chunk = tail[: stop_m.start()] if stop_m else tail
        # Collect bullet items
        for bm in BULLET_RE.finditer(chunk):
            line = " ".join(bm.group(1).split())[:500]
            if len(line) >= 20:  # filter noise
                results.append(line)
            if len(results) >= MAX_PER_PKG:
                return results
    return results[:MAX_PER_PKG]


def parse_owner_repo(repo_url: str) -> tuple[str, str] | None:
    m = re.search(r"github\.com[/:]([^/]+)/([^/\s#?]+)", repo_url or "")
    if not m:
        return None
    return m.group(1), m.group(2).rstrip("/").removesuffix(".git")


async def fetch_releases(session, owner: str, repo: str) -> list[dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=30"
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status != 200:
                return []
            return await r.json(content_type=None)
    except Exception:
        return []


async def process_pkg(sem, session, pool, row, counters):
    async with sem:
        parsed = parse_owner_repo(row["repository"] or "")
        if not parsed:
            counters["no_repo"] += 1
            return
        owner, repo = parsed
        releases = await fetch_releases(session, owner, repo)
        if not releases:
            counters["no_release"] += 1
            return
        # Releases are ordered newest-first per GH API.
        tags = [r.get("tag_name") for r in releases if r.get("tag_name")]
        for i, rel in enumerate(releases):
            body = rel.get("body") or ""
            bullets = extract_breaking_bullets(body)
            if not bullets:
                continue
            this_ver = rel.get("tag_name") or ""
            prev_ver = tags[i + 1] if i + 1 < len(tags) else ""
            if not this_ver:
                continue
            async with pool.acquire() as conn:
                for desc in bullets:
                    desc_hash = hashlib.md5(desc.encode("utf-8", errors="replace")).hexdigest()[:32]
                    try:
                        await conn.execute(
                            """INSERT INTO breaking_changes
                                 (package_id, from_version, to_version, change_type,
                                  description, desc_hash)
                               VALUES ($1, $2, $3, 'breaking', $4, $5)
                               ON CONFLICT (package_id, from_version, to_version, change_type, desc_hash)
                               DO NOTHING""",
                            row["id"], prev_ver or "unknown", this_ver, desc[:2000], desc_hash,
                        )
                        counters["inserted"] += 1
                    except Exception as e:
                        counters["err"] += 1
                        if counters["err"] < 5:
                            print(f"  INSERT fail {owner}/{repo} {this_ver}: {type(e).__name__}: {e}")
        counters["ok"] += 1


async def main():
    start = time.time()
    conn_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=CONCURRENCY + 2)
    print(f"=== changelog_crawler TARGET_PER_ECO={TARGET_PER_ECO} CONCURRENCY={CONCURRENCY} ===")

    async with conn_pool.acquire() as c0:
        # Select top TARGET_PER_ECO packages per ecosystem by downloads_weekly,
        # that have a GitHub repository.
        rows = await c0.fetch(
            f"""WITH ranked AS (
                 SELECT id, ecosystem, name, repository,
                        ROW_NUMBER() OVER (PARTITION BY ecosystem ORDER BY downloads_weekly DESC NULLS LAST) AS rn
                   FROM packages
                  WHERE repository ILIKE '%github.com%'
               )
               SELECT id, ecosystem, name, repository
                 FROM ranked WHERE rn <= $1""",
            TARGET_PER_ECO,
        )
    print(f"Candidates: {len(rows)}")

    sem = asyncio.Semaphore(CONCURRENCY)
    counters = {"ok": 0, "no_repo": 0, "no_release": 0, "inserted": 0, "err": 0}

    async with aiohttp.ClientSession() as session:
        tasks = [
            asyncio.create_task(process_pkg(sem, session, conn_pool, dict(r), counters))
            for r in rows
        ]
        if True:
            done = 0
            for t in asyncio.as_completed(tasks):
                await t
                done += 1
                if done % 50 == 0 or done == len(rows):
                    el = max(int(time.time() - start), 1)
                    rate = done / el
                    eta = int((len(rows) - done) / max(rate, 0.01))
                    print(f"  {done}/{len(rows)}  ok={counters['ok']}  "
                          f"inserted={counters['inserted']}  no_repo={counters['no_repo']}  "
                          f"no_release={counters['no_release']}  err={counters['err']}  "
                          f"rate={rate:.1f}/s  eta={eta}s")

    await conn_pool.close()
    print(f"\n=== DONE: {counters} elapsed={int(time.time()-start)}s ===")


if __name__ == "__main__":
    asyncio.run(main())
