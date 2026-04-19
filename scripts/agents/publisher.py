#!/usr/bin/env python3
"""PUBLISHER Agent — Content Publishing across platforms.

Posts comments on Dev.to via API.
Publishes articles on Dev.to via API.
For Reddit/HN/Discord: marks as 'manual' with instructions.
Manages rate limits per platform (max N actions/day/platform).
"""

import asyncio
import json
import urllib.request
from datetime import datetime, timezone

from .common import (
    get_pool, log_action, update_platform_status, check_rate_limit,
    DEVTO_API, DEVTO_API_KEY, fetch_json,
)


async def post_devto_comment(pool, opp: dict, content: str) -> bool:
    """Post a comment on Dev.to article."""
    url = opp["url"]
    try:
        path = url.replace("https://dev.to/", "")
        article_data = fetch_json(f"{DEVTO_API}/articles/{path}")
        if not article_data or "id" not in article_data:
            print(f"  [WARN] Could not get Dev.to article ID for {url[:60]}")
            return False

        article_id = article_data["id"]

        comment_payload = json.dumps({
            "comment": {
                "body_markdown": content,
                "commentable_id": article_id,
                "commentable_type": "Article"
            }
        }).encode()
        req = urllib.request.Request(
            f"{DEVTO_API}/comments",
            data=comment_payload,
            headers={
                "api-key": DEVTO_API_KEY,
                "Content-Type": "application/json",
                "User-Agent": "DepScope-Agent/1.0",
            },
            method="POST"
        )
        from urllib.request import urlopen
        with urlopen(req, timeout=15) as resp:
            resp_data = json.loads(resp.read().decode())

        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE agent_opportunities SET status = 'done', executed_at = NOW() WHERE id = $1",
                opp["id"]
            )
        await log_action(pool, "post_comment", "devto", url, content[:200], "executed", json.dumps(resp_data)[:500])
        await update_platform_status(pool, "devto", last_action=True)
        print(f"  [OK] Posted comment on Dev.to: {opp['title'][:40]}")
        return True

    except Exception as e:
        print(f"  [ERR] Dev.to comment failed: {e}")
        await log_action(pool, "post_comment", "devto", url, content[:200], "failed", str(e)[:200])
        return False


async def publish_devto_article(pool, item: dict, content: str, title: str, tags: list) -> bool:
    """Publish article on Dev.to."""
    try:
        article_payload = json.dumps({
            "article": {
                "title": title,
                "body_markdown": content,
                "published": True,
                "tags": tags[:4],
            }
        }).encode()
        req = urllib.request.Request(
            f"{DEVTO_API}/articles",
            data=article_payload,
            headers={
                "api-key": DEVTO_API_KEY,
                "Content-Type": "application/json",
            },
            method="POST"
        )
        from urllib.request import urlopen
        with urlopen(req, timeout=30) as resp:
            resp_data = json.loads(resp.read().decode())

        article_url = resp_data.get("url", "")
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE agent_plan SET status = 'completed', result = $1, completed_at = NOW() WHERE id = $2",
                f"Published: {article_url}", item["id"]
            )
        await log_action(pool, "publish_article", "devto", article_url, title, "executed")
        await update_platform_status(pool, "devto", last_action=True)
        print(f"    [OK] Published: {article_url}")
        return True

    except Exception as e:
        print(f"    [ERR] Article publish failed: {e}")
        await log_action(pool, "publish_article", "devto", "", title[:100], "failed", str(e)[:200])
        return False


async def run(pool) -> dict:
    """Execute confirmed actions (status='execute')."""
    print("[PUBLISHER] Processing confirmed actions...")
    
    async with pool.acquire() as conn:
        to_execute = await conn.fetch(
            "SELECT * FROM agent_opportunities WHERE status = 'execute' AND platform != 'email' ORDER BY created_at LIMIT 5"
        )

    if not to_execute:
        print("  No actions to execute")
        return {"executed": 0, "manual": 0}

    executed = 0
    manual = 0
    
    for opp in to_execute:
        opp = dict(opp)
        platform = opp["platform"]
        content = opp.get("suggested_content", "")
        url = opp["url"]

        if not content:
            print(f"  [SKIP] No content for {opp['title'][:40]}")
            continue

        # Check rate limit
        can_post = await check_rate_limit(pool, platform)

        if platform == "devto" and can_post:
            success = await post_devto_comment(pool, opp, content)
            if success:
                executed += 1
        else:
            # Reddit, HN, Cursor, or rate-limited platforms
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE agent_opportunities SET status = 'manual_post' WHERE id = $1",
                    opp["id"]
                )
            await log_action(
                pool, "manual_post", platform, url,
                f"MANUAL POST REQUIRED:\n\nURL: {url}\n\nContent:\n{content}",
                "pending"
            )
            manual += 1
            print(f"  [MANUAL] {platform}: {opp['title'][:40]}")

    print(f"[PUBLISHER] Executed: {executed}, Manual: {manual}")
    return {"executed": executed, "manual": manual}


if __name__ == "__main__":
    async def _main():
        pool = await get_pool()
        try:
            await run(pool)
        finally:
            await pool.close()
    asyncio.run(_main())
