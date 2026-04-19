#!/usr/bin/env python3
"""SCOUT Agent — Discovery of marketing opportunities across platforms.

Scans Dev.to, Reddit, HN, Cursor Forum every 4 hours.
Finds articles/discussions where an expert comment makes sense.
Calculates relevance score (1-10) based on keyword match.
Saves opportunities to DB. Auto-skips if relevance < 5.
"""

import asyncio
from datetime import datetime, timezone

from .common import (
    get_pool, log_action, fetch_json, score_text,
    DEVTO_API, DEVTO_TAGS, DEVTO_KEYWORDS,
    REDDIT_SUBS, REDDIT_KEYWORDS, HN_QUERIES,
)

PLATFORM_ICONS = {
    "devto": "\U0001f4dd",
    "reddit": "\U0001f534",
    "hn": "\U0001f7e0",
    "cursor": "\U0001f4bb",
    "email": "\U0001f4e7",
}


async def get_existing_urls(pool) -> set:
    async with pool.acquire() as conn:
        return set(r["url"] for r in await conn.fetch("SELECT url FROM agent_opportunities"))


async def save_opportunity(pool, platform: str, url: str, title: str, score: int, action: str, extra: str, existing: set):
    if url in existing or score < 3:
        return False
    score = min(score, 10)
    icon = PLATFORM_ICONS.get(platform, "")
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO agent_opportunities (platform, url, title, relevance_score, suggested_action, suggested_content, status, platform_icon) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            platform, url, title[:200], score, action, extra, "found", icon
        )
    existing.add(url)
    return True


async def discover_devto(pool, existing: set) -> int:
    print("[SCOUT] Scanning Dev.to...")
    found = 0
    for tag in DEVTO_TAGS[:6]:
        url = f"{DEVTO_API}/articles?tag={tag}&per_page=10&top=7"
        articles = fetch_json(url)
        if not articles:
            continue
        for art in articles:
            art_url = art.get("url", "")
            if not art_url:
                continue
            title = art.get("title", "")
            desc = art.get("description", "")
            text = f"{title} {desc}"
            score = score_text(text, DEVTO_KEYWORDS)
            reactions = art.get("positive_reactions_count", 0)
            comments = art.get("comments_count", 0)
            if reactions > 20: score = min(score + 1, 10)
            if reactions > 50: score = min(score + 1, 10)
            if comments < 10: score = min(score + 1, 10)

            text_lower = text.lower()
            if any(kw in text_lower for kw in ["vulnerability", "security", "supply chain"]):
                action = "Comment with security analysis expertise"
            elif any(kw in text_lower for kw in ["npm", "pypi", "cargo", "dependency", "dependencies"]):
                action = "Comment with package management insight"
            elif any(kw in text_lower for kw in ["mcp", "ai agent"]):
                action = "Comment about AI tooling for developers"
            else:
                action = "Comment with relevant technical insight"

            extra = f"By {art.get('user', {}).get('username', '?')} | {reactions}r, {comments}c | Tags: {', '.join(art.get('tag_list', []))}"
            if await save_opportunity(pool, "devto", art_url, title, score, action, extra, existing):
                found += 1
                print(f"  [+] Score {score}: {title[:60]}")
    return found


async def discover_reddit(pool, existing: set) -> int:
    print("[SCOUT] Scanning Reddit...")
    found = 0
    for sub in REDDIT_SUBS:
        url = f"https://old.reddit.com/r/{sub}/new.json?limit=15"
        data = fetch_json(url, headers={"User-Agent": "DepScope-Agent/1.0 (depscope.dev)"})
        if not data or "data" not in data:
            continue
        for post in data["data"].get("children", []):
            pd = post.get("data", {})
            post_url = f"https://reddit.com{pd.get('permalink', '')}"
            title = pd.get("title", "")
            selftext = pd.get("selftext", "")[:500]
            text = f"{title} {selftext}"
            score = score_text(text, REDDIT_KEYWORDS)
            ups = pd.get("ups", 0)
            num_comments = pd.get("num_comments", 0)
            if ups > 10: score = min(score + 1, 10)
            if ups > 50: score = min(score + 1, 10)
            if num_comments < 20: score = min(score + 1, 10)

            action = "Comment with relevant developer insight (manual post)"
            extra = f"r/{sub} | {ups} upvotes, {num_comments} comments"
            if await save_opportunity(pool, "reddit", post_url, title, score, action, extra, existing):
                found += 1
                print(f"  [+] Score {score}: r/{sub} -- {title[:50]}")
    return found


async def discover_hn(pool, existing: set) -> int:
    print("[SCOUT] Scanning Hacker News...")
    found = 0
    for query in HN_QUERIES:
        url = f"https://hn.algolia.com/api/v1/search_by_date?query={query}&tags=story&hitsPerPage=10"
        data = fetch_json(url)
        if not data or "hits" not in data:
            continue
        for hit in data["hits"]:
            hn_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
            title = hit.get("title", "")
            score_val = score_text(title, DEVTO_KEYWORDS)
            points = hit.get("points", 0) or 0
            num_comments = hit.get("num_comments", 0) or 0
            if points > 10: score_val = min(score_val + 1, 10)
            if points > 50: score_val = min(score_val + 2, 10)
            if num_comments < 20: score_val = min(score_val + 1, 10)

            action = "Comment on HN (manual post -- admin from browser)"
            extra = f"HN | {points} points, {num_comments} comments"
            if await save_opportunity(pool, "hn", hn_url, title, score_val, action, extra, existing):
                found += 1
                print(f"  [+] Score {score_val}: HN -- {title[:50]}")
    return found


async def discover_cursor_forum(pool, existing: set) -> int:
    print("[SCOUT] Scanning Cursor Forum...")
    found = 0
    data = fetch_json("https://forum.cursor.com/latest.json")
    if not data or "topic_list" not in data:
        return 0
    for topic in data["topic_list"].get("topics", [])[:15]:
        topic_url = f"https://forum.cursor.com/t/{topic.get('slug', '')}/{topic.get('id', '')}"
        title = topic.get("title", "")
        score_val = score_text(title, ["mcp", "package", "dependency", "npm", "pip", "security", "api", "tool", "agent"])
        views = topic.get("views", 0)
        reply_count = topic.get("reply_count", 0)
        if views > 100: score_val = min(score_val + 1, 10)
        if views > 500: score_val = min(score_val + 1, 10)
        if reply_count < 10: score_val = min(score_val + 1, 10)

        action = "Comment on Cursor Forum (manual post)"
        extra = f"Cursor Forum | {views} views, {reply_count} replies"
        if await save_opportunity(pool, "cursor", topic_url, title, score_val, action, extra, existing):
            found += 1
            print(f"  [+] Score {score_val}: Cursor -- {title[:50]}")
    return found


async def auto_skip_low_relevance(pool) -> int:
    """Auto-skip opportunities with relevance < 5."""
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE agent_opportunities SET status = 'skipped' WHERE status = 'found' AND relevance_score < 5"
        )
        count = int(result.split()[-1]) if result else 0
    if count:
        print(f"[SCOUT] Auto-skipped {count} low-relevance opportunities (score < 5)")
    return count


async def run(pool) -> dict:
    """Main scout entry point. Returns summary."""
    existing = await get_existing_urls(pool)
    
    devto_found = await discover_devto(pool, existing)
    reddit_found = await discover_reddit(pool, existing)
    hn_found = await discover_hn(pool, existing)
    cursor_found = await discover_cursor_forum(pool, existing)
    
    total_found = devto_found + reddit_found + hn_found + cursor_found
    skipped = await auto_skip_low_relevance(pool)
    
    await log_action(
        pool, "discovery", "all",
        content=f"Found {total_found}: devto={devto_found}, reddit={reddit_found}, hn={hn_found}, cursor={cursor_found}. Skipped {skipped}.",
        status="executed"
    )
    
    print(f"[SCOUT] Total found: {total_found}, auto-skipped: {skipped}")
    return {
        "total_found": total_found,
        "devto": devto_found,
        "reddit": reddit_found,
        "hn": hn_found,
        "cursor": cursor_found,
        "skipped": skipped,
    }


if __name__ == "__main__":
    async def _main():
        pool = await get_pool()
        try:
            await run(pool)
        finally:
            await pool.close()
    asyncio.run(_main())
