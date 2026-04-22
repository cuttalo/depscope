#!/usr/bin/env python3
"""Backfill hex.pm package homepage + repository from hex.pm API.

Hex API: https://hex.pm/api/packages/<name>
Returns {meta: {links: {"GitHub": "...", "Docs": "..."}, "description": "..."}}
"""
import asyncio
import sys
sys.path.insert(0, "/home/deploy/depscope")

import aiohttp
from api.database import get_pool

HEADERS = {"Accept": "application/json", "User-Agent": "DepScope/0.1"}


async def fetch_hex(session, name):
    url = f"https://hex.pm/api/packages/{name}"
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                return None
            return await r.json()
    except Exception:
        return None


def extract(data):
    meta = (data or {}).get("meta") or {}
    links = meta.get("links") or {}
    out = {}
    # homepage: prefer "Homepage" → "Website" → "GitHub" → any first link
    for key in ("Homepage", "homepage", "Website", "website"):
        v = links.get(key)
        if v:
            out["homepage"] = v
            break
    if "homepage" not in out and links:
        out["homepage"] = next(iter(links.values()))
    # repository: prefer "GitHub" → "Source" → "Repository"
    for key in ("GitHub", "Github", "github", "Source", "source", "Repository", "repository"):
        v = links.get(key)
        if v:
            out["repository"] = v
            break
    # description
    d = meta.get("description")
    if d:
        out["description"] = d.strip()[:2000]
    return out


async def main():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, name, homepage, repository, description FROM packages
               WHERE ecosystem='hex'
                 AND (homepage = '' OR homepage IS NULL
                      OR repository = '' OR repository IS NULL)"""
        )
    print(f"{len(rows)} hex packages to backfill", flush=True)
    sem = asyncio.Semaphore(8)
    updated = 0
    missed = 0
    async with aiohttp.ClientSession() as session:
        async def one(p):
            nonlocal updated, missed
            async with sem:
                data = await fetch_hex(session, p["name"])
                if not data:
                    missed += 1
                    return
                meta = extract(data)
                if not meta:
                    missed += 1
                    return
                sets = []
                args = [p["id"]]
                for k in ("homepage", "repository", "description"):
                    if meta.get(k) and not p.get(k):
                        args.append(meta[k][:2000])
                        sets.append(f"{k}=${len(args)}")
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
