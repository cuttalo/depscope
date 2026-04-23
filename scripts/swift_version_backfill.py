#!/usr/bin/env python3
"""Backfill latest_version for Swift packages that have NULL/empty.

Queries GitHub /releases/latest, falls back to /tags?per_page=1.
Uses GH_TOKEN (5000/hr).
"""
import asyncio
import os
import re
import sys
import time

sys.path.insert(0, "/home/deploy/depscope")

import aiohttp
import asyncpg

from api.config import DATABASE_URL

GH_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "DepScope/1.0 (+https://depscope.dev)",
    "X-GitHub-Api-Version": "2022-11-28",
}
if GH_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GH_TOKEN}"


async def fetch_version(session, owner_repo):
    try:
        # Latest release
        async with session.get(
            f"https://api.github.com/repos/{owner_repo}/releases/latest",
            headers=HEADERS, timeout=aiohttp.ClientTimeout(total=12),
        ) as r:
            if r.status == 200:
                data = await r.json()
                tag = data.get("tag_name")
                if tag:
                    return tag
    except Exception:
        pass
    try:
        # Fallback: latest tag
        async with session.get(
            f"https://api.github.com/repos/{owner_repo}/tags?per_page=1",
            headers=HEADERS, timeout=aiohttp.ClientTimeout(total=12),
        ) as r:
            if r.status == 200:
                data = await r.json()
                if data and isinstance(data, list) and data[0].get("name"):
                    return data[0]["name"]
    except Exception:
        pass
    return None


async def worker(sem, session, pool, row, counters):
    async with sem:
        name = row["name"]  # owner/repo
        if "/" not in name:
            counters["skip"] += 1
            return
        owner_repo = name.strip("/")
        v = await fetch_version(session, owner_repo)
        if not v:
            counters["no_version"] += 1
            return
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE packages SET latest_version=$1, updated_at=NOW() WHERE id=$2",
                v, row["id"],
            )
        counters["updated"] += 1


async def main():
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=6)
    async with pool.acquire() as c:
        rows = await c.fetch(
            "SELECT id, name FROM packages "
            "WHERE ecosystem='swift' AND (latest_version IS NULL OR latest_version='') "
            "ORDER BY id"
        )
    print(f"swift rows missing version: {len(rows)}")

    sem = asyncio.Semaphore(3)  # stay well under GH 5000/hr
    counters = {"updated": 0, "no_version": 0, "skip": 0}
    start = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = [
            asyncio.create_task(worker(sem, session, pool, dict(r), counters))
            for r in rows
        ]
        done = 0
        for t in asyncio.as_completed(tasks):
            await t
            done += 1
            if done % 100 == 0 or done == len(rows):
                el = max(int(time.time()-start), 1)
                rate = done/el
                eta = int((len(rows)-done)/max(rate, 0.01))
                print(f"  {done}/{len(rows)}  updated={counters['updated']}  "
                      f"no_version={counters['no_version']}  skip={counters['skip']}  "
                      f"rate={rate:.1f}/s  eta={eta//60}m{eta%60}s")
    await pool.close()
    print(f"\n=== DONE: {counters} elapsed={int(time.time()-start)}s ===")


if __name__ == "__main__":
    asyncio.run(main())
