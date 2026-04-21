import os
"""Re-classify npm publish_security with 3 tiers: attested (best), signed, unsigned."""
import asyncio, asyncpg, aiohttp, json

DB_URL = os.environ["DATABASE_URL"]

async def main():
    conn = await asyncpg.connect(DB_URL)
    rows = await conn.fetch("""
        SELECT DISTINCT package_name FROM package_quality
        WHERE ecosystem='npm' AND publish_security IS NOT NULL
        ORDER BY package_name
    """)
    async with aiohttp.ClientSession(headers={"User-Agent": "DepScope/1.0"}) as s:
        n = 0
        counts = {"attested": 0, "signed": 0, "unsigned": 0, "err": 0}
        for r in rows:
            pkg = r["package_name"]
            try:
                async with s.get(f"https://registry.npmjs.org/{pkg}", timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status != 200:
                        counts["err"] += 1; continue
                    d = await resp.json()
            except Exception:
                counts["err"] += 1; continue
            lv = (d.get("dist-tags") or {}).get("latest")
            if not lv:
                counts["err"] += 1; continue
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
            try:
                await conn.execute("""
                    UPDATE package_quality SET publish_security=$1, publish_detail=$2, last_checked=NOW()
                    WHERE ecosystem='npm' AND package_name=$3
                """, sec, detail, pkg)
                n += 1
            except Exception:
                pass
        print(f"refresh done: {n} updates")
        print("distribution:", counts)
    await conn.close()

asyncio.run(main())
