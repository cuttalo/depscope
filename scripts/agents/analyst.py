#!/usr/bin/env python3
"""ANALYST Agent — Metrics Collection & Reporting.

Collects daily metrics from all sources:
- Page views, unique visitors, countries (from DB)
- Dev.to stats (views, reactions) via API
- API usage stats
- Email stats (sent, received, replies)
- Platform action counts
Calculates trends and anomalies.
Generates daily report.
"""

import asyncio
from datetime import date, timezone

from .common import get_pool, log_action, fetch_json, DEVTO_API


async def run(pool) -> dict:
    """Collect and save daily metrics."""
    print("[ANALYST] Collecting daily metrics...")
    today = date.today()

    async with pool.acquire() as conn:
        pv = await conn.fetchval(
            "SELECT COUNT(*) FROM page_views WHERE DATE(created_at) = $1 AND ip_address NOT IN ('127.0.0.1','::1','10.10.0.140','10.10.0.1','91.134.4.25')",
            today
        ) or 0

        uv = await conn.fetchval(
            "SELECT COUNT(DISTINCT ip_address) FROM page_views WHERE DATE(created_at) = $1 AND ip_address NOT IN ('127.0.0.1','::1','10.10.0.140','10.10.0.1','91.134.4.25')",
            today
        ) or 0

        api = await conn.fetchval(
            "SELECT COUNT(*) FROM api_usage WHERE DATE(created_at) = $1 AND ip_address NOT IN ('127.0.0.1','::1','10.10.0.140','10.10.0.1','91.134.4.25')",
            today
        ) or 0

        countries = await conn.fetchval(
            "SELECT COUNT(DISTINCT country) FROM page_views WHERE DATE(created_at) = $1 AND country IS NOT NULL AND ip_address NOT IN ('127.0.0.1','::1','10.10.0.140','10.10.0.1','91.134.4.25')",
            today
        ) or 0

        pkgs = await conn.fetchval("SELECT COUNT(*) FROM packages") or 0

        # Dev.to stats
        devto_views = 0
        devto_reactions = 0
        cred = await conn.fetchrow("SELECT api_key FROM agent_credentials WHERE platform = 'devto' AND active = true")
        if cred:
            articles = fetch_json(f"{DEVTO_API}/articles/me/published?per_page=100", headers={"api-key": cred["api_key"]})
            if articles:
                for art in articles:
                    devto_views += art.get("page_views_count", 0)
                    devto_reactions += art.get("positive_reactions_count", 0)

        # Email stats
        email_sent = await conn.fetchval(
            "SELECT COUNT(*) FROM agent_actions WHERE action_type = 'send_email' AND status = 'executed' AND DATE(created_at) = $1",
            today
        ) or 0
        email_received = await conn.fetchval(
            "SELECT COUNT(*) FROM agent_actions WHERE action_type = 'email_received' AND DATE(created_at) = $1",
            today
        ) or 0

        # Platform action counts
        platform_actions = await conn.fetch("""
            SELECT platform, COUNT(*) as count 
            FROM agent_actions 
            WHERE DATE(created_at) = $1 AND status = 'executed'
            GROUP BY platform
        """, today)

        # Save metrics
        await conn.execute("""
            INSERT INTO agent_metrics (date, page_views, unique_visitors, api_calls, countries, db_packages, devto_views, devto_reactions, email_responses)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (date) DO UPDATE SET
                page_views = $2, unique_visitors = $3, api_calls = $4, countries = $5,
                db_packages = $6, devto_views = $7, devto_reactions = $8, email_responses = $9
        """, today, pv, uv, api, countries, pkgs, devto_views, devto_reactions, email_sent + email_received)

        # Trend: compare with yesterday
        yesterday_metrics = await conn.fetchrow(
            "SELECT page_views, unique_visitors, api_calls FROM agent_metrics WHERE date = $1 - INTERVAL '1 day'",
            today
        )

    trend = {}
    if yesterday_metrics:
        ypv = yesterday_metrics["page_views"] or 1
        yuv = yesterday_metrics["unique_visitors"] or 1
        yapi = yesterday_metrics["api_calls"] or 1
        trend = {
            "views_change_pct": round(((pv - ypv) / ypv) * 100, 1),
            "visitors_change_pct": round(((uv - yuv) / yuv) * 100, 1),
            "api_change_pct": round(((api - yapi) / yapi) * 100, 1),
        }

    summary = f"Metrics {today}: {pv}v, {uv}u, {api}api, {countries}c, {pkgs}pkg, devto:{devto_views}v/{devto_reactions}r, email:{email_sent}s/{email_received}r"
    await log_action(pool, "metrics", "internal", content=summary, status="executed")
    print(f"[ANALYST] {summary}")

    return {
        "page_views": pv,
        "unique_visitors": uv,
        "api_calls": api,
        "countries": countries,
        "packages": pkgs,
        "devto_views": devto_views,
        "devto_reactions": devto_reactions,
        "email_sent": email_sent,
        "email_received": email_received,
        "trend": trend,
        "platform_actions": {r["platform"]: r["count"] for r in platform_actions} if platform_actions else {},
    }


if __name__ == "__main__":
    async def _main():
        pool = await get_pool()
        try:
            await run(pool)
        finally:
            await pool.close()
    asyncio.run(_main())
