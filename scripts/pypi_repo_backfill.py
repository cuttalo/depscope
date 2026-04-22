#!/usr/bin/env python3
"""Backfill PyPI repository field by extracting github/gitlab/bitbucket URLs
from project_urls in the PyPI JSON API.

PyPI API: https://pypi.org/pypi/<name>/json
Returns info.project_urls = {"Homepage": "...", "Source": "...", "Code": "...",
  "Repository": "...", "Bug Tracker": "...", ...}
We look for any URL containing github.com / gitlab.com / bitbucket.org
across project_urls AND info.home_page.
"""
import asyncio
import re
import sys
sys.path.insert(0, "/home/deploy/depscope")

import aiohttp
from api.database import get_pool

HEADERS = {"Accept": "application/json", "User-Agent": "DepScope/0.1 (https://depscope.dev)"}
REPO_HOSTS = ("github.com", "gitlab.com", "bitbucket.org", "codeberg.org", "sourcehut.org", "git.sr.ht")


async def fetch_pypi(session, name):
    try:
        async with session.get(
            f"https://pypi.org/pypi/{name}/json",
            headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            if r.status != 200:
                return None
            return await r.json()
    except Exception:
        return None


def pick_repo(info):
    """Scan project_urls + home_page for a repo-host URL."""
    urls = dict(info.get("project_urls") or {})
    # Preferred keys first
    preferred_keys = ("Source", "Source Code", "Repository", "Code",
                      "GitHub", "Github", "GitLab", "Gitlab", "Homepage")
    for k in preferred_keys:
        v = urls.get(k)
        if v and any(h in v for h in REPO_HOSTS):
            return v.strip()
    # Fallback: any value
    for v in urls.values():
        if v and any(h in v for h in REPO_HOSTS):
            return v.strip()
    # home_page
    hp = (info.get("home_page") or "").strip()
    if hp and any(h in hp for h in REPO_HOSTS):
        return hp
    return None


async def main():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, name, homepage, repository FROM packages
               WHERE ecosystem='pypi'
                 AND (repository = '' OR repository IS NULL)"""
        )
    print(f"{len(rows)} pypi packages missing repository", flush=True)
    sem = asyncio.Semaphore(12)
    updated = 0
    missed = 0
    async with aiohttp.ClientSession() as session:
        async def one(p):
            nonlocal updated, missed
            async with sem:
                data = await fetch_pypi(session, p["name"])
                if not data:
                    missed += 1
                    return
                info = (data or {}).get("info") or {}
                repo = pick_repo(info)
                if not repo:
                    missed += 1
                    return
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE packages SET repository=$2, updated_at=NOW() WHERE id=$1",
                        p["id"], repo[:2000],
                    )
                updated += 1
        await asyncio.gather(*[one(p) for p in rows])
    print(f"DONE updated={updated} missed={missed}", flush=True)


asyncio.run(main())
