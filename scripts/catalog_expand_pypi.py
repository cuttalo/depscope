#!/usr/bin/env python3
"""Expand PyPI catalog by calling /api/check for each top package."""
import asyncio
import aiohttp
import asyncpg
import os
import sys
import time

TOP_URL = "https://hugovk.github.io/top-pypi-packages/top-pypi-packages.json"
API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
DATABASE_URL = os.environ.get(
    "DATABASE_URL", os.environ["DATABASE_URL"]
)
TARGET = int(os.environ.get("TARGET", "15000"))
CONCURRENCY = int(os.environ.get("CONCURRENCY", "8"))


async def fetch_top():
    async with aiohttp.ClientSession() as s:
        async with s.get(TOP_URL, timeout=aiohttp.ClientTimeout(total=30)) as r:
            data = await r.json()
    return [row["project"] for row in data["rows"][:TARGET]]


async def get_existing():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch("SELECT name FROM packages WHERE ecosystem='pypi'")
    finally:
        await conn.close()
    return {r["name"].lower() for r in rows}


async def process(sem, session, name, counters):
    async with sem:
        url = f"{API_BASE}/api/check/pypi/{name}"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as r:
                if r.status == 200:
                    counters["ok"] += 1
                elif r.status == 404:
                    counters["not_found"] += 1
                else:
                    counters["err"] += 1
        except Exception:
            counters["timeout"] += 1


async def main():
    top = await fetch_top()
    existing = await get_existing()
    todo = [p for p in top if p.lower() not in existing]
    print(f"[expand] pypi top={len(top)} existing={len(existing)} todo={len(todo)}", flush=True)

    sem = asyncio.Semaphore(CONCURRENCY)
    counters = {"ok": 0, "not_found": 0, "err": 0, "timeout": 0}
    start = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(process(sem, session, p, counters)) for p in todo]
        done = 0
        for t in asyncio.as_completed(tasks):
            await t
            done += 1
            if done % 100 == 0:
                el = int(time.time() - start)
                rate = done / max(el, 1)
                eta = int((len(todo) - done) / max(rate, 0.01))
                print(
                    f"[expand] {done}/{len(todo)}  ok={counters['ok']}  nf={counters['not_found']}  "
                    f"err={counters['err']}  timeout={counters['timeout']}  rate={rate:.1f}/s  eta={eta}s",
                    flush=True,
                )
    el = int(time.time() - start)
    print(f"[expand] DONE  ok={counters['ok']}  nf={counters['not_found']}  err={counters['err']}  timeout={counters['timeout']}  elapsed={el}s", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
