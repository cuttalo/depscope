"""Bulk fetch downloads for packages with 0 downloads.
PyPI: uses pypistats.org API
Cargo: re-fetches from crates.io (already has recent_downloads)
npm: uses npm downloads API
Rate limit: 1 req/sec to be polite.
"""
import asyncio
import sys
import time
sys.path.insert(0, "/home/deploy/depscope")

import aiohttp
from api.database import get_pool, close_pool


MAX_PER_RUN = 100
DELAY_SECONDS = 1.0


async def fetch_pypi_downloads(name: str) -> int:
    """Fetch weekly downloads from pypistats.org."""
    url = f"https://pypistats.org/api/packages/{name.lower()}/recent"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return 0
                data = await resp.json()
                return data.get("data", {}).get("last_week", 0)
    except Exception:
        return 0


async def fetch_npm_downloads(name: str) -> int:
    """Fetch weekly downloads from npm API."""
    url = f"https://api.npmjs.org/downloads/point/last-week/{name}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    return 0
                data = await resp.json()
                return data.get("downloads", 0)
    except Exception:
        return 0


async def fetch_cargo_downloads(name: str) -> int:
    """Fetch recent downloads from crates.io."""
    url = f"https://crates.io/api/v1/crates/{name}"
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "DepScope/0.1 (https://depscope.dev)"}
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return 0
                data = await resp.json()
                return data.get("crate", {}).get("recent_downloads", 0)
    except Exception:
        return 0


FETCHERS = {
    "pypi": fetch_pypi_downloads,
    "npm": fetch_npm_downloads,
    "cargo": fetch_cargo_downloads,
}


async def main():
    start = time.time()
    print(f"=== Downloads Fetcher ===")
    print(f"Started at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    pool = await get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, ecosystem, name
            FROM packages
            WHERE downloads_weekly = 0 OR downloads_weekly IS NULL
            ORDER BY updated_at ASC NULLS FIRST
            LIMIT $1
        """, MAX_PER_RUN)

    print(f"Found {len(rows)} packages with 0 downloads")
    success = 0
    errors = 0

    for i, row in enumerate(rows):
        pkg_id = row["id"]
        eco = row["ecosystem"]
        name = row["name"]

        fetcher = FETCHERS.get(eco)
        if not fetcher:
            continue

        downloads = await fetcher(name)
        if downloads > 0:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE packages SET downloads_weekly = $1, updated_at = NOW() WHERE id = $2",
                    downloads, pkg_id,
                )
            print(f"  [{i+1}/{len(rows)}] {eco}/{name}: {downloads:,} downloads/week")
            success += 1
        else:
            print(f"  [{i+1}/{len(rows)}] {eco}/{name}: still 0")
            errors += 1

        await asyncio.sleep(DELAY_SECONDS)

    elapsed = time.time() - start
    print(f"\n=== Done: {success} updated, {errors} still 0, in {elapsed:.0f}s ===")

    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
