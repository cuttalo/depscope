#!/usr/bin/env python3
"""Daily snapshot of health scores into health_history.

- Iterates over all rows in packages
- Upserts one row per (package_id, today) in health_history
- Counts vulnerabilities from the vulnerabilities table
- Idempotent: safe to re-run (ON CONFLICT DO UPDATE)
"""
import asyncio
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg
from api.config import DATABASE_URL


def _risk_from_score(score: int) -> str:
    if score >= 80:
        return "low"
    if score >= 60:
        return "moderate"
    if score >= 40:
        return "high"
    return "critical"


async def record_snapshot() -> dict:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Use a single SQL pass joining with vulnerabilities count
        # packages -> left join (vulnerability counts) -> upsert into health_history
        sql = """
        WITH vuln_counts AS (
            SELECT package_id, COUNT(*) AS vc
            FROM vulnerabilities
            GROUP BY package_id
        )
        INSERT INTO health_history (package_id, health_score, risk, vuln_count, recorded_at)
        SELECT
            p.id,
            COALESCE(p.health_score, 0),
            CASE
                WHEN COALESCE(p.health_score, 0) >= 80 THEN 'low'
                WHEN COALESCE(p.health_score, 0) >= 60 THEN 'moderate'
                WHEN COALESCE(p.health_score, 0) >= 40 THEN 'high'
                ELSE 'critical'
            END,
            COALESCE(vc.vc, 0),
            CURRENT_DATE
        FROM packages p
        LEFT JOIN vuln_counts vc ON vc.package_id = p.id
        ON CONFLICT (package_id, recorded_at) DO UPDATE
        SET health_score = EXCLUDED.health_score,
            risk = EXCLUDED.risk,
            vuln_count = EXCLUDED.vuln_count
        """
        start = date.today()
        await conn.execute(sql)
        inserted = await conn.fetchval(
            "SELECT COUNT(*) FROM health_history WHERE recorded_at = CURRENT_DATE"
        )
        return {"date": str(start), "rows": inserted}
    finally:
        await conn.close()


async def main():
    result = await record_snapshot()
    print(f"[health-snapshot] date={result['date']} rows={result['rows']}")


if __name__ == "__main__":
    asyncio.run(main())
