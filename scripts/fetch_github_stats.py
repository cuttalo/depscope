"""Bulk fetch GitHub stats for all packages with a GitHub repository URL.
Rate limit: 1 req/sec, max 50 per run (stay under GitHub's 60 req/h unauthenticated).
Runs via cron every 12 hours.
"""
import asyncio
import sys
import time
sys.path.insert(0, "/home/deploy/depscope")

from api.database import get_pool, close_pool
from api.registries import fetch_github_stats, save_github_stats


MAX_PER_RUN = 50
DELAY_SECONDS = 1.2  # ~50 requests per minute, well under 60/h


async def main():
    start = time.time()
    print(f"=== GitHub Stats Fetcher ===")
    print(f"Started at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    pool = await get_pool()

    # Get packages with github repos, prioritize those without stats or oldest stats
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT p.id, p.ecosystem, p.name, p.repository
            FROM packages p
            LEFT JOIN github_stats gs ON gs.package_id = p.id
            WHERE p.repository LIKE '%github.com%'
            ORDER BY gs.updated_at ASC NULLS FIRST
            LIMIT $1
        """, MAX_PER_RUN)

    print(f"Found {len(rows)} packages to process")
    success = 0
    errors = 0

    for i, row in enumerate(rows):
        pkg_id = row["id"]
        name = row["name"]
        repo = row["repository"]

        stats = await fetch_github_stats(repo)
        if stats:
            await save_github_stats(pkg_id, repo, stats)
            stars = stats.get("stars", 0)
            archived = stats.get("is_archived", False)
            print(f"  [{i+1}/{len(rows)}] {row['ecosystem']}/{name}: stars={stars:,}, forks={stats.get('forks', 0):,}, archived={archived}")
            success += 1
        else:
            print(f"  [{i+1}/{len(rows)}] {row['ecosystem']}/{name}: FAILED (repo: {repo})")
            errors += 1

        # Rate limit
        await asyncio.sleep(DELAY_SECONDS)

    elapsed = time.time() - start
    print(f"\n=== Done: {success} OK, {errors} errors in {elapsed:.0f}s ===")

    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
