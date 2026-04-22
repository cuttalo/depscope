#!/usr/bin/env python3
"""Backfill crates.io homepage + repository for cargo packages.

API: https://crates.io/api/v1/crates/<name>
Returns {crate: {homepage, repository, documentation, description, ...}}
"""
import asyncio
import sys
sys.path.insert(0, "/home/deploy/depscope")

import aiohttp
from api.database import get_pool

HEADERS = {"Accept": "application/json", "User-Agent": "DepScope/0.1 (https://depscope.dev)"}


async def fetch_crate(session, name):
    try:
        async with session.get(
            f"https://crates.io/api/v1/crates/{name}",
            headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            if r.status != 200:
                return None
            return await r.json()
    except Exception:
        return None


async def main():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, name, homepage, repository FROM packages
               WHERE ecosystem='cargo'
                 AND (homepage = '' OR homepage IS NULL)"""
        )
    print(f"{len(rows)} cargo packages with missing homepage", flush=True)
    sem = asyncio.Semaphore(10)
    updated = 0
    missed = 0
    async with aiohttp.ClientSession() as session:
        async def one(p):
            nonlocal updated, missed
            async with sem:
                data = await fetch_crate(session, p["name"])
                if not data:
                    missed += 1
                    return
                crate = (data or {}).get("crate") or {}
                sets = []
                args = [p["id"]]
                homepage = (crate.get("homepage") or "").strip()
                repo = (crate.get("repository") or "").strip()
                docs = (crate.get("documentation") or "").strip()
                # Prefer homepage → documentation → repository for homepage field
                hp = homepage or docs
                if hp and not p["homepage"]:
                    args.append(hp[:2000])
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
