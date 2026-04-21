#!/usr/bin/env python3
"""Backfill scorecard_scores for the top 100 npm packages by weekly downloads.

Also backfills maintainer_signals (repo_owner, repo_name) for those packages so
future code paths that read maintainer_signals first find them directly.
"""
from __future__ import annotations
import asyncio
import json
import os
import re
import sys
from datetime import date as _date

import aiohttp
import asyncpg

sys.path.insert(0, "/home/deploy/depscope")
DATABASE_URL = os.environ["DATABASE_URL"]

GITHUB_RE = re.compile(r"github\.com[/:]([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")


async def backfill_maintainer_signals(conn) -> int:
    """Populate (repo_owner, repo_name) from packages.repository where missing."""
    rows = await conn.fetch(
        """
        SELECT p.ecosystem, p.name, p.repository
        FROM packages p
        LEFT JOIN maintainer_signals ms
          ON ms.ecosystem = p.ecosystem AND ms.package_name = p.name
        WHERE p.repository ILIKE '%github.com%'
          AND (ms.id IS NULL OR ms.repo_owner IS NULL)
        ORDER BY COALESCE(p.downloads_weekly, 0) DESC
        LIMIT 500
        """
    )
    n = 0
    for r in rows:
        m = GITHUB_RE.search(r["repository"] or "")
        if not m:
            continue
        owner, name = m.group(1), m.group(2)
        try:
            await conn.execute(
                """
                INSERT INTO maintainer_signals (ecosystem, package_name, repo_owner, repo_name, updated_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (ecosystem, package_name) DO UPDATE SET
                  repo_owner = COALESCE(maintainer_signals.repo_owner, EXCLUDED.repo_owner),
                  repo_name = COALESCE(maintainer_signals.repo_name, EXCLUDED.repo_name),
                  updated_at = NOW()
                """,
                r["ecosystem"], r["name"], owner, name,
            )
            n += 1
        except Exception as e:
            print(f"[maint] {r['ecosystem']}/{r['name']}: {e}")
    return n


async def fetch_scorecards(conn, limit: int = 150) -> int:
    rows = await conn.fetch(
        """
        SELECT DISTINCT repo_owner, repo_name
        FROM maintainer_signals
        WHERE repo_owner IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM scorecard_scores s
            WHERE s.repo_url = 'github.com/' || maintainer_signals.repo_owner || '/' || maintainer_signals.repo_name
          )
        LIMIT $1
        """,
        limit,
    )
    print(f"[sc] fetching scorecards for {len(rows)} new repos")
    stored = 0
    async with aiohttp.ClientSession(headers={"User-Agent": "DepScope/1.0"}) as session:
        for r in rows:
            platform_url = f"github.com/{r['repo_owner']}/{r['repo_name']}"
            api_url = f"https://api.securityscorecards.dev/projects/{platform_url}"
            try:
                async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()
            except Exception:
                continue
            score = data.get("score")
            if score is None:
                continue
            sd = data.get("date") or (data.get("scorecard") or {}).get("date")
            try:
                date_val = _date.fromisoformat(sd[:10]) if sd else None
            except Exception:
                date_val = None
            checks = {
                c.get("name"): {"score": c.get("score"), "reason": c.get("reason")}
                for c in data.get("checks", [])
                if c.get("name")
            }
            try:
                await conn.execute(
                    """
                    INSERT INTO scorecard_scores (repo_url, score, checks_json, scorecard_date, updated_at)
                    VALUES ($1, $2, $3::jsonb, $4, NOW())
                    ON CONFLICT (repo_url) DO UPDATE SET
                      score = EXCLUDED.score,
                      checks_json = EXCLUDED.checks_json,
                      scorecard_date = EXCLUDED.scorecard_date,
                      updated_at = NOW()
                    """,
                    platform_url, float(score), json.dumps(checks), date_val,
                )
                stored += 1
                if stored % 20 == 0:
                    print(f"[sc] {stored} stored…")
            except Exception as e:
                print(f"[sc] {platform_url}: {e}")
    return stored


async def main() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        n_maint = await backfill_maintainer_signals(conn)
        print(f"[maint] backfilled {n_maint} rows in maintainer_signals")
        n_sc = await fetch_scorecards(conn, limit=150)
        print(f"[sc] stored {n_sc} new scorecards")
        total_sc = await conn.fetchval("SELECT COUNT(*) FROM scorecard_scores")
        total_maint = await conn.fetchval("SELECT COUNT(*) FROM maintainer_signals WHERE repo_owner IS NOT NULL")
        print(f"[done] maintainer_signals (with repo): {total_maint}, scorecards: {total_sc}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
