#!/usr/bin/env python3
"""Universal retry-aware expander: PyPI + Cargo + Rubygems missing packages with backoff."""
import asyncio
import aiohttp
import asyncpg
import os
import time

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
DATABASE_URL = os.environ.get("DATABASE_URL", os.environ["DATABASE_URL"])
CONCURRENCY = 2  # kind to external registries

SOURCES = {
    "pypi": ("https://hugovk.github.io/top-pypi-packages/top-pypi-packages.json", lambda j: [r["project"] for r in j["rows"]], 15000),
    "cargo": (None, None, 5000),   # crates.io paginated; computed below
    "rubygems": (None, None, 3000), # rubygems paginated; computed below
}


async def fetch_top_cargo(target):
    names = []
    async with aiohttp.ClientSession(headers={"User-Agent": "depscope/1.0"}) as s:
        for page in range(1, target // 100 + 2):
            try:
                async with s.get(f"https://crates.io/api/v1/crates?sort=downloads&per_page=100&page={page}", timeout=aiohttp.ClientTimeout(total=15)) as r:
                    if r.status != 200: break
                    data = await r.json()
                    crates = data.get("crates", [])
                    if not crates: break
                    names.extend(c["id"] for c in crates)
            except Exception:
                break
            await asyncio.sleep(0.3)
            if len(names) >= target: break
    return names[:target]


async def fetch_top_rubygems(target):
    names = []
    async with aiohttp.ClientSession(headers={"User-Agent": "depscope/1.0"}) as s:
        for page in range(1, target // 30 + 2):
            try:
                async with s.get(f"https://rubygems.org/api/v1/search.json?query=*&page={page}&order=downloads", timeout=aiohttp.ClientTimeout(total=15)) as r:
                    if r.status != 200: break
                    data = await r.json()
                    if not data: break
                    names.extend(g["name"] for g in data if "name" in g)
            except Exception:
                break
            await asyncio.sleep(0.3)
            if len(names) >= target: break
            if page > 100: break
    return names[:target]


async def fetch_top_pypi(target):
    async with aiohttp.ClientSession() as s:
        async with s.get(SOURCES["pypi"][0], timeout=aiohttp.ClientTimeout(total=30)) as r:
            data = await r.json()
    return [row["project"] for row in data["rows"][:target]]


async def get_existing(eco):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch("SELECT name FROM packages WHERE ecosystem=$1", eco)
    finally:
        await conn.close()
    return {r["name"].lower() for r in rows}


async def process(sem, session, eco, name, counters):
    async with sem:
        url = f"{API_BASE}/api/check/{eco}/{name}"
        for attempt in range(3):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
                    if r.status == 200:
                        counters["ok"] += 1
                        return
                    if r.status == 404:
                        counters["nf"] += 1
                        return
                    if r.status in (502, 503, 504, 429):
                        await asyncio.sleep(2 + attempt * 3)
                        continue
                    counters["err"] += 1
                    return
            except asyncio.TimeoutError:
                await asyncio.sleep(1 + attempt * 2)
                continue
            except Exception:
                counters["err"] += 1
                return
        counters["err"] += 1


async def expand_one(eco, target):
    if eco == "pypi":
        top = await fetch_top_pypi(target)
    elif eco == "cargo":
        top = await fetch_top_cargo(target)
    elif eco == "rubygems":
        top = await fetch_top_rubygems(target)
    else:
        return
    existing = await get_existing(eco)
    todo = [p for p in top if p.lower() not in existing]
    print(f"[{eco}] top={len(top)} existing={len(existing)} todo={len(todo)}", flush=True)
    sem = asyncio.Semaphore(CONCURRENCY)
    counters = {"ok": 0, "nf": 0, "err": 0}
    start = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(process(sem, session, eco, p, counters)) for p in todo]
        done = 0
        for t in asyncio.as_completed(tasks):
            await t
            done += 1
            if done % 100 == 0:
                el = int(time.time() - start)
                rate = done / max(el, 1)
                eta = int((len(todo) - done) / max(rate, 0.01))
                print(f"[{eco}] {done}/{len(todo)}  ok={counters['ok']}  nf={counters['nf']}  err={counters['err']}  rate={rate:.1f}/s  eta={eta}s", flush=True)
    el = int(time.time() - start)
    print(f"[{eco}] DONE ok={counters['ok']} nf={counters['nf']} err={counters['err']} elapsed={el}s", flush=True)


async def main():
    # Run sequentially to avoid overwhelming external registries
    for eco in ("cargo", "rubygems", "pypi"):
        target = SOURCES[eco][2]
        try:
            await expand_one(eco, target)
        except Exception as e:
            print(f"[{eco}] FAILED: {e}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
