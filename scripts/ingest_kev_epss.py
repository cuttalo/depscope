import os
"""Daily ingest: CISA KEV catalog + EPSS scores.

CISA KEV: https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
EPSS:     https://epss.cyentia.com/epss_scores-current.csv.gz (updated daily)
"""
import asyncio, asyncpg, aiohttp, csv, gzip, io, sys
from datetime import datetime, timezone

DB_URL = os.environ["DATABASE_URL"]
KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
EPSS_URL = "https://epss.cyentia.com/epss_scores-current.csv.gz"


async def ingest_kev(conn, session):
    print("[kev] fetching CISA KEV catalog …")
    async with session.get(KEV_URL, timeout=aiohttp.ClientTimeout(total=60)) as r:
        if r.status != 200:
            print(f"[kev] HTTP {r.status}, skip")
            return 0
        data = await r.json(content_type=None)

    vulns = data.get("vulnerabilities", [])
    print(f"[kev] got {len(vulns)} entries")

    # Upsert
    n = 0
    for v in vulns:
        cve = v.get("cveID")
        if not cve:
            continue
        await conn.execute(
            """
            INSERT INTO kev_catalog
              (cve_id, vendor, product, vuln_name, date_added, short_desc, required_action, due_date, known_ransomware, updated_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,NOW())
            ON CONFLICT (cve_id) DO UPDATE SET
              vendor=EXCLUDED.vendor, product=EXCLUDED.product, vuln_name=EXCLUDED.vuln_name,
              date_added=EXCLUDED.date_added, short_desc=EXCLUDED.short_desc,
              required_action=EXCLUDED.required_action, due_date=EXCLUDED.due_date,
              known_ransomware=EXCLUDED.known_ransomware, updated_at=NOW()
            """,
            cve,
            v.get("vendorProject"),
            v.get("product"),
            v.get("vulnerabilityName"),
            __import__("datetime").date.fromisoformat(v["dateAdded"]) if v.get("dateAdded") else None,
            v.get("shortDescription"),
            v.get("requiredAction"),
            __import__("datetime").date.fromisoformat(v["dueDate"]) if v.get("dueDate") else None,
            v.get("knownRansomwareCampaignUse"),
        )
        n += 1
    print(f"[kev] upserted {n}")
    return n


async def ingest_epss(conn, session):
    print("[epss] fetching EPSS daily scores …")
    async with session.get(EPSS_URL, timeout=aiohttp.ClientTimeout(total=120)) as r:
        if r.status != 200:
            print(f"[epss] HTTP {r.status}, skip")
            return 0
        raw = await r.read()
    # gzip CSV
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as f:
        text = f.read().decode("utf-8", errors="ignore")
    lines = text.splitlines()
    # First line: #model_version: v2025-xx-xx, score_date: YYYY-MM-DD
    score_date = None
    for line in lines[:3]:
        if "score_date" in line:
            try:
                score_date = line.split("score_date:")[1].strip().strip(",").strip()
            except Exception:
                pass
    reader = csv.DictReader([l for l in lines if not l.startswith("#")])
    n = 0
    batch = []
    async with conn.transaction():
        for row in reader:
            cve = row.get("cve")
            epss = row.get("epss")
            pct = row.get("percentile")
            if not cve or not epss:
                continue
            from datetime import date as _D; sd = score_date[:10] if score_date else None; sd = _D.fromisoformat(sd) if sd else None; batch.append((cve, float(epss), float(pct) if pct else None, sd))
            if len(batch) >= 5000:
                await conn.executemany(
                    """
                    INSERT INTO epss_scores(cve_id, epss, percentile, score_date, updated_at)
                    VALUES ($1,$2,$3,$4,NOW())
                    ON CONFLICT (cve_id) DO UPDATE SET
                      epss=EXCLUDED.epss, percentile=EXCLUDED.percentile,
                      score_date=EXCLUDED.score_date, updated_at=NOW()
                    """, batch
                )
                n += len(batch)
                batch = []
        if batch:
            await conn.executemany(
                """
                INSERT INTO epss_scores(cve_id, epss, percentile, score_date, updated_at)
                VALUES ($1,$2,$3,$4,NOW())
                ON CONFLICT (cve_id) DO UPDATE SET
                  epss=EXCLUDED.epss, percentile=EXCLUDED.percentile,
                  score_date=EXCLUDED.score_date, updated_at=NOW()
                """, batch
            )
            n += len(batch)
    print(f"[epss] upserted {n} (score_date={score_date})")
    return n


async def main():
    conn = await asyncpg.connect(DB_URL)
    async with aiohttp.ClientSession(headers={"User-Agent": "DepScope/1.0 (+https://depscope.dev)"}) as session:
        try:
            n_kev = await ingest_kev(conn, session)
        except Exception as e:
            print(f"[kev] ERROR {e}")
            n_kev = 0
        try:
            n_epss = await ingest_epss(conn, session)
        except Exception as e:
            print(f"[epss] ERROR {e}")
            n_epss = 0
    total_kev = await conn.fetchval("SELECT COUNT(*) FROM kev_catalog")
    total_epss = await conn.fetchval("SELECT COUNT(*) FROM epss_scores")
    max_epss = await conn.fetchval("SELECT MAX(epss) FROM epss_scores")
    print(f"[done] kev_catalog={total_kev} rows; epss_scores={total_epss} rows; max_epss={max_epss}")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
