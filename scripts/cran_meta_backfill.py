#!/usr/bin/env python3
"""Backfill CRAN repository + homepage using crandb.r-pkg.org.

API: https://crandb.r-pkg.org/<name>
Returns {URL, BugReports, Title, Description, License, ...}
URL may contain multiple comma-separated URLs.
"""
import asyncio
import re
import sys
sys.path.insert(0, "/home/deploy/depscope")

import aiohttp
from api.database import get_pool

HEADERS = {"Accept": "application/json", "User-Agent": "DepScope/0.1 (https://depscope.dev)"}


async def fetch_cran(session, name):
    try:
        async with session.get(
            f"https://crandb.r-pkg.org/{name}",
            headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            if r.status != 200:
                return None
            return await r.json()
    except Exception:
        return None


URL_SPLIT = re.compile(r"[,\s]+")


def pick_urls(url_field):
    """CRAN URL field can be multiline/comma-separated. Return (homepage, repo)."""
    if not url_field:
        return None, None
    urls = [u.strip().strip("<>") for u in URL_SPLIT.split(str(url_field)) if u.strip()]
    urls = [u for u in urls if u.startswith("http")]
    if not urls:
        return None, None
    github = next((u for u in urls if "github.com" in u or "gitlab.com" in u or "bitbucket.org" in u), None)
    non_github = next((u for u in urls if u != github), None)
    return non_github or urls[0], github


async def main():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, name, homepage, repository FROM packages
               WHERE ecosystem='cran'
                 AND (repository = '' OR repository IS NULL
                      OR homepage = '' OR homepage IS NULL)"""
        )
    print(f"{len(rows)} cran packages to enrich", flush=True)
    sem = asyncio.Semaphore(10)
    updated = 0
    missed = 0
    async with aiohttp.ClientSession() as session:
        async def one(p):
            nonlocal updated, missed
            async with sem:
                data = await fetch_cran(session, p["name"])
                if not data:
                    # Fallback: use CRAN canonical URL as repository
                    if not p["repository"]:
                        async with pool.acquire() as conn:
                            await conn.execute(
                                "UPDATE packages SET repository=$2, updated_at=NOW() WHERE id=$1",
                                p["id"], f"https://CRAN.R-project.org/package={p['name']}",
                            )
                        updated += 1
                    else:
                        missed += 1
                    return
                homepage, repo = pick_urls(data.get("URL"))
                # Fallback repo: CRAN canonical
                if not repo:
                    repo = f"https://CRAN.R-project.org/package={p['name']}"
                sets, args = [], [p["id"]]
                if homepage and not p["homepage"]:
                    args.append(homepage[:2000])
                    sets.append(f"homepage=${len(args)}")
                if repo and not p["repository"]:
                    args.append(repo[:2000])
                    sets.append(f"repository=${len(args)}")
                if not sets:
                    return
                async with pool.acquire() as conn:
                    await conn.execute(
                        f"UPDATE packages SET {', '.join(sets)}, updated_at=NOW() WHERE id=$1",
                        *args,
                    )
                updated += 1
        await asyncio.gather(*[one(p) for p in rows])
    print(f"DONE updated={updated} missed={missed}", flush=True)


asyncio.run(main())
