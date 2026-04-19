"""Recalculate health_score for ALL packages recently updated (any ecosystem).

Same logic as recalc_health_minor but scopes over ALL ecosystems. Meant to run
once a month, right after mass_populate expands the DB. Idempotent: rebuilds
health from existing data_json + OSV vulnerability lookup. Safe to re-run.

Filters on updated_at >= NOW() - SINCE_HOURS (default 720h = 30 days) so the
monthly cron only touches rows that actually changed.
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/home/deploy/depscope")

from api.registries import fetch_vulnerabilities
from api.health import calculate_health_score


async def main():
    import asyncpg
    db_url = os.environ.get("DATABASE_URL") or "postgresql://depscope:depscope2026@localhost:5432/depscope"
    conn = await asyncpg.connect(db_url)

    # Monthly job: default look-back 30 days. Override via env.
    since_hours = int(os.environ.get("SINCE_HOURS", "720"))
    since = datetime.now(timezone.utc) - timedelta(hours=since_hours)

    rows = await conn.fetch("""
        SELECT id, ecosystem, name, latest_version, data_json
        FROM packages
        WHERE updated_at >= $1
        ORDER BY ecosystem, name
    """, since)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Found {len(rows)} packages updated since {since.isoformat()}")

    updated = 0
    errors = 0
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
            vulns = await fetch_vulnerabilities(
                r["ecosystem"], r["name"],
                latest_version=r["latest_version"] or "",
            )
        except Exception as e:
            vulns = []
            errors += 1
            if errors <= 5:
                print(f"  vuln fetch error {r['ecosystem']}/{r['name']}: {e}")
        try:
            health = calculate_health_score(pkg_data, vulns)
            await conn.execute(
                "UPDATE packages SET health_score=$1, updated_at=NOW() WHERE id=$2",
                health["score"], r["id"],
            )
            updated += 1
        except Exception as e:
            errors += 1
            if errors <= 10:
                print(f"  health calc error {r['ecosystem']}/{r['name']}: {e}")
        if updated % 100 == 0 and updated > 0:
            print(f"  Recalculated {updated}/{len(rows)}  last={r['ecosystem']}/{r['name']}")
        # Gentle on OSV API
        await asyncio.sleep(0.2)

    await conn.close()
    print(f"[{datetime.now(timezone.utc).isoformat()}] Done. Recalculated {updated}/{len(rows)} packages, {errors} errors.")


if __name__ == "__main__":
    asyncio.run(main())
