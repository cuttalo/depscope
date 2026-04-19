"""Health score history — per-package 90-day trend.

The snapshot script populates health_history daily.
Here we read it and compute trend direction.
"""
from datetime import date, timedelta
from api.database import get_pool
from api.cache import cache_get, cache_set


def _trend_direction(points: list[dict]) -> str:
    """Given chronological points [{date, score}, ...], return up/down/stable.

    Simple heuristic: compare average of first third vs last third.
    - diff >= +3: up
    - diff <= -3: down
    - else: stable
    Safe on short series (< 6 points) → stable.
    """
    n = len(points)
    if n < 6:
        return "stable"
    third = max(1, n // 3)
    first = points[:third]
    last = points[-third:]
    avg_first = sum(p["score"] for p in first) / len(first)
    avg_last = sum(p["score"] for p in last) / len(last)
    diff = avg_last - avg_first
    if diff >= 3:
        return "up"
    if diff <= -3:
        return "down"
    return "stable"


async def get_history(ecosystem: str, package: str, days: int = 90) -> dict | None:
    """Return last N days of snapshots + trend. None if package unknown."""
    cache_key = f"history:{ecosystem}:{package}:{days}"
    cached = await cache_get(cache_key)
    if cached:
        cached["_cache"] = "hit"
        return cached

    pool = await get_pool()
    async with pool.acquire() as conn:
        pkg_row = await conn.fetchrow(
            "SELECT id, health_score FROM packages WHERE ecosystem = $1 AND name = $2",
            ecosystem, package,
        )
        if not pkg_row:
            return None

        cutoff = date.today() - timedelta(days=days)
        rows = await conn.fetch(
            """
            SELECT recorded_at, health_score, risk, vuln_count
            FROM health_history
            WHERE package_id = $1 AND recorded_at >= $2
            ORDER BY recorded_at ASC
            """,
            pkg_row["id"], cutoff,
        )

    points = [
        {
            "date": r["recorded_at"].isoformat(),
            "score": r["health_score"],
            "risk": r["risk"],
            "vuln_count": r["vuln_count"],
        }
        for r in rows
    ]

    if points:
        scores = [p["score"] for p in points]
        stats = {
            "min": min(scores),
            "max": max(scores),
            "avg": round(sum(scores) / len(scores), 1),
            "current": scores[-1],
            "first": scores[0],
            "delta": scores[-1] - scores[0],
        }
    else:
        stats = {"min": None, "max": None, "avg": None, "current": pkg_row["health_score"], "first": None, "delta": 0}

    result = {
        "package": package,
        "ecosystem": ecosystem,
        "days": days,
        "snapshot_count": len(points),
        "trend": _trend_direction([{"score": p["score"]} for p in points]),
        "stats": stats,
        "history": points,
        "_cache": "miss",
    }

    # Short TTL: 1h is enough, snapshot is daily
    await cache_set(cache_key, result, ttl=3600)
    return result
