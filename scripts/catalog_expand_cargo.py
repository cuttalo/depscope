#!/usr/bin/env python3
"""Expand Cargo catalog by crawling crates.io top-downloads."""
import asyncio
import aiohttp
import asyncpg
import os
import time

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
DATABASE_URL = os.environ.get("DATABASE_URL", os.environ["DATABASE_URL"])
TARGET = int(os.environ.get("TARGET", "5000"))
CONCURRENCY = int(os.environ.get("CONCURRENCY", "4"))


async def fetch_top_crates():
    names = []
    async with aiohttp.ClientSession(headers={"User-Agent": "depscope-expand/1.0"}) as s:
        page = 1
        while len(names) < TARGET:
            url = f"https://crates.io/api/v1/crates?sort=downloads&per_page=100&page={page}"
            try:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=20)) as r:
                    if r.status != 200:
                        break
                    data = await r.json()
                    crates = data.get("crates", [])
                    if not crates:
                        break
                    names.extend(c["id"] for c in crates)
            except Exception:
                break
            page += 1
            await asyncio.sleep(0.4)
    return names[:TARGET]


async def get_existing():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch("SELECT name FROM packages WHERE ecosystem='cargo'")
    finally:
        await conn.close()
    return {r["name"].lower() for r in rows}


async def process(sem, session, name, counters):
    async with sem:
        url = f"{API_BASE}/api/check/cargo/{name}"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=25)) as r:
                if r.status == 200:
                    counters["ok"] += 1
                elif r.status == 404:
                    counters["not_found"] += 1
                else:
                    counters["err"] += 1
        except Exception:
            counters["timeout"] += 1


async def main():
    top = await fetch_top_crates()
    existing = await get_existing()
    todo = [p for p in top if p.lower() not in existing]
    print(f"[cargo] top={len(top)} existing={len(existing)} todo={len(todo)}", flush=True)
    sem = asyncio.Semaphore(CONCURRENCY)
    counters = {"ok": 0, "not_found": 0, "err": 0, "timeout": 0}
    start = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(process(sem, session, p, counters)) for p in todo]
        done = 0
        for t in asyncio.as_completed(tasks):
            await t
            done += 1
            if done % 200 == 0:
                el = int(time.time() - start)
                rate = done / max(el, 1)
                eta = int((len(todo) - done) / max(rate, 0.01))
                print(f"[cargo] {done}/{len(todo)}  ok={counters['ok']}  nf={counters['not_found']}  "
                      f"err={counters['err']}  rate={rate:.1f}/s  eta={eta}s", flush=True)
    el = int(time.time() - start)
    print(f"[cargo] DONE ok={counters['ok']} nf={counters['not_found']} err={counters['err']} "
          f"timeout={counters['timeout']} elapsed={el}s", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
