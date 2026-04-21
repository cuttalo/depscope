"""Recalculate health_score for recently updated packages in minor ecosystems.

Reads packages where updated_at > $since, rebuilds pkg_data from data_json,
fetches current vulnerabilities, calls calculate_health_score, updates row.
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/home/deploy/depscope")

from api.registries import fetch_vulnerabilities
from api.health import calculate_health_score


MINOR_ECOSYSTEMS = ["pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"]


async def main():
    import asyncpg
    db_url = os.environ.get("DATABASE_URL") or os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)

    since_hours = int(os.environ.get("SINCE_HOURS", "6"))
    since = datetime.now(timezone.utc) - timedelta(hours=since_hours)

    rows = await conn.fetch("""
        SELECT id, ecosystem, name, latest_version, data_json
        FROM packages
        WHERE ecosystem = ANY($1) AND updated_at >= $2
        ORDER BY ecosystem, name
    """, MINOR_ECOSYSTEMS, since)

    print(f"Found {len(rows)} packages updated since {since.isoformat()}")

    updated = 0
    for r in rows:
        pkg_data = r["data_json"]
        if isinstance(pkg_data, str):
            try:
                pkg_data = json.loads(pkg_data)
            except Exception:
                pkg_data = {}
        if not isinstance(pkg_data, dict):
            pkg_data = {}
        try:
            vulns = await fetch_vulnerabilities(r["ecosystem"], r["name"],
                                                latest_version=r["latest_version"] or "")
        except Exception:
            vulns = []
        health = calculate_health_score(pkg_data, vulns)
        await conn.execute("""
            UPDATE packages SET health_score=$1, updated_at=NOW() WHERE id=$2
        """, health["score"], r["id"])
        updated += 1
        if updated % 25 == 0:
            print(f"  Recalculated {updated}/{len(rows)}  last={r['ecosystem']}/{r['name']} score={health['score']}")
        await asyncio.sleep(0.3)

    await conn.close()
    print(f"Done. Recalculated {updated} packages.")


if __name__ == "__main__":
    asyncio.run(main())
