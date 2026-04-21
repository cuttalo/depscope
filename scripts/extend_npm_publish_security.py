import os
"""Extend publish_security check to ALL npm packages in package_quality (not just top 800)."""
import asyncio, asyncpg, aiohttp

DB_URL = os.environ["DATABASE_URL"]

async def main():
    conn = await asyncpg.connect(DB_URL)
    rows = await conn.fetch("""
        SELECT DISTINCT package_name FROM package_quality
        WHERE ecosystem='npm' AND publish_security IS NULL
    """)
    print(f"to check: {len(rows)}")
    sem = asyncio.Semaphore(20)
    counts = {"attested": 0, "signed": 0, "unsigned": 0, "err": 0}

    async def check_one(session, pkg):
        async with sem:
            try:
                async with session.get(f"https://registry.npmjs.org/{pkg}", timeout=aiohttp.ClientTimeout(total=8)) as r:
                    if r.status != 200:
                        counts["err"] += 1; return None, None, None
                    d = await r.json()
            except Exception:
                counts["err"] += 1; return None, None, None
            lv = (d.get("dist-tags") or {}).get("latest")
            if not lv:
                counts["err"] += 1; return None, None, None
            latest = (d.get("versions") or {}).get(lv) or {}
            dist = latest.get("dist") or {}
            att = dist.get("attestations") or {}
            sigs = dist.get("signatures") or []
            if att:
                sec, detail = "attested", f"latest {lv}: SLSA provenance + {len(sigs)} sig"
            elif sigs:
                sec, detail = "signed", f"latest {lv}: {len(sigs)} registry sig"
            else:
                sec, detail = "unsigned", f"latest {lv}: no signatures"
            counts[sec] += 1
            return pkg, sec, detail

    async with aiohttp.ClientSession(headers={"User-Agent": "DepScope/1.0"}) as s:
        tasks = [check_one(s, r["package_name"]) for r in rows]
        results = await asyncio.gather(*tasks)

    for pkg, sec, detail in results:
        if pkg:
            try:
                await conn.execute("""
                    UPDATE package_quality SET publish_security=$1, publish_detail=$2, last_checked=NOW()
                    WHERE ecosystem='npm' AND package_name=$3
                """, sec, detail, pkg)
            except Exception:
                pass
    print("done:", counts)
    await conn.close()

asyncio.run(main())
