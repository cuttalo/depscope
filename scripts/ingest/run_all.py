"""Master runner: execute all ingestion steps sequentially.

Logs to /var/log/depscope/ingest.log. A failure in one step is caught and
logged; remaining steps still run.
"""
import asyncio
import time
import traceback

from scripts.ingest._common import get_db_pool, get_logger

logger = get_logger("run_all")


async def run_step(name: str, coro_fn):
    start = time.time()
    logger.info(f"===== START {name} =====")
    try:
        added = await coro_fn()
        logger.info(
            f"===== END   {name}: +{added} rows in {time.time()-start:.1f}s ====="
        )
        return added or 0
    except Exception as e:
        logger.error(f"===== FAIL  {name}: {e}\n{traceback.format_exc()} =====")
        return 0


async def snapshot_counts() -> dict[str, int]:
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            errors = await conn.fetchval("SELECT COUNT(*) FROM errors")
            bugs = await conn.fetchval("SELECT COUNT(*) FROM known_bugs")
            breaking = await conn.fetchval("SELECT COUNT(*) FROM breaking_changes")
            compat = await conn.fetchval("SELECT COUNT(*) FROM compat_matrix")
            alt = await conn.fetchval("SELECT COUNT(*) FROM alternatives")
        return {
            "errors": errors,
            "known_bugs": bugs,
            "breaking_changes": breaking,
            "compat_matrix": compat,
            "alternatives": alt,
        }
    finally:
        await pool.close()


async def main():
    overall_start = time.time()
    before = await snapshot_counts()
    logger.info(f"BEFORE: {before}")

    # Imported lazily so partial failures don't cascade at import time
    from scripts.ingest.github_bugs import main as step_bugs
    from scripts.ingest.github_breaking import main as step_breaking
    from scripts.ingest.stackoverflow_errors import main as step_errors
    from scripts.ingest.npm_compat import main as step_compat
    from scripts.ingest.discover_alternatives import main as step_alt

    results = {}
    results["github_bugs"] = await run_step("github_bugs", step_bugs)
    results["github_breaking"] = await run_step("github_breaking", step_breaking)
    results["stackoverflow_errors"] = await run_step(
        "stackoverflow_errors", step_errors
    )
    results["npm_compat"] = await run_step("npm_compat", step_compat)
    results["discover_alternatives"] = await run_step(
        "discover_alternatives", step_alt
    )

    after = await snapshot_counts()
    logger.info(f"AFTER : {after}")
    logger.info(f"DELTA : { {k: after[k]-before[k] for k in after} }")
    logger.info(
        f"run_all done in {time.time()-overall_start:.1f}s — {results}"
    )


if __name__ == "__main__":
    asyncio.run(main())
