"""Shared utilities for all agents."""

import os
import json
import asyncpg
from datetime import datetime, date, timezone
from urllib.request import urlopen, Request as URLRequest
from urllib.error import URLError

DB_URL = os.getenv("DATABASE_URL", "postgresql://depscope:${DB_PASSWORD}@localhost:5432/depscope")

# Email config
IMAP_HOST = "10.10.0.130"
IMAP_PORT = 993
SMTP_HOST = "10.10.0.130"
SMTP_PORT = 25
EMAIL_USER = "depscope@cuttalo.com"
EMAIL_PASS = os.getenv("EMAIL_PASSWORD", "")
EMAIL_FROM_NAME = "Vincenzo Rubino - DepScope"

# Dev.to
DEVTO_API = "https://dev.to/api"
DEVTO_API_KEY = "VuqtfNaAJifTz4h2ckG3sCdG"

DEVTO_TAGS = ["npm", "pypi", "security", "ai", "python", "javascript", "cargo", "dependencies", "opensource", "webdev"]
DEVTO_KEYWORDS = ["dependency", "dependencies", "package", "npm", "pypi", "cargo", "vulnerability", "supply chain", "mcp", "ai agent", "security audit"]

REDDIT_SUBS = ["programming", "webdev", "node", "python", "SideProject"]
REDDIT_KEYWORDS = ["package", "deprecated", "vulnerability", "npm", "pip", "dependency", "dependencies", "security", "supply chain"]

HN_QUERIES = ["npm+security", "dependency+vulnerability", "package+deprecated", "supply+chain+attack"]


async def get_pool():
    return await asyncpg.create_pool(DB_URL, min_size=1, max_size=3)


async def log_action(pool, action_type: str, platform: str, target_url: str = "", content: str = "", status: str = "executed", response: str = "", thread_id: str = None, parent_id: int = None):
    """Log an action to the database."""
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO agent_actions (action_type, platform, target_url, content, status, response, thread_id, parent_id) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            action_type, platform, target_url, content, status, response, thread_id, parent_id
        )


async def update_platform_status(pool, platform: str, last_action: bool = False):
    """Update platform rate limiting status."""
    async with pool.acquire() as conn:
        if last_action:
            await conn.execute("""
                UPDATE agent_platform_status 
                SET last_action_at = NOW(), actions_today = actions_today + 1, updated_at = NOW()
                WHERE platform = $1
            """, platform)
        # Reset daily counter if it's a new day
        await conn.execute("""
            UPDATE agent_platform_status 
            SET actions_today = 0, updated_at = NOW()
            WHERE platform = $1 AND DATE(updated_at) < CURRENT_DATE
        """, platform)


async def check_rate_limit(pool, platform: str) -> bool:
    """Check if platform has remaining daily actions."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT actions_today, daily_limit, api_status FROM agent_platform_status WHERE platform = $1",
            platform
        )
        if not row:
            return False
        if row["api_status"] == "manual_only":
            return False
        if row["api_status"] == "rate_limited":
            return False
        return row["actions_today"] < row["daily_limit"]


async def load_rules(pool) -> list[dict]:
    """Load all active rules."""
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM agent_rules WHERE active = true ORDER BY priority")
    return [dict(r) for r in rows]


def fetch_json(url: str, headers: dict | None = None) -> dict | list | None:
    """Simple HTTP GET returning JSON."""
    try:
        req = URLRequest(url, headers=headers or {})
        req.add_header("User-Agent", "DepScope-Agent/1.0")
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except (URLError, json.JSONDecodeError, Exception) as e:
        print(f"  [WARN] fetch {url[:80]}: {e}")
        return None


def score_text(text: str, keywords: list[str]) -> int:
    """Score relevance of text against keywords."""
    text_lower = text.lower()
    score = 0
    for kw in keywords:
        if kw in text_lower:
            score += 2
    return min(score, 10)


# ═══════════════════════════════════════════════════
# Config helpers — read from agent_config table
# ═══════════════════════════════════════════════════

async def get_config(key: str, default: str = "") -> str:
    """Read config value from DB using a direct connection."""
    conn = await asyncpg.connect(DB_URL)
    try:
        row = await conn.fetchrow("SELECT value FROM agent_config WHERE key = $1", key)
        return row["value"] if row else default
    finally:
        await conn.close()


async def get_config_int(key: str, default: int = 0) -> int:
    """Read config value as int."""
    val = await get_config(key, str(default))
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


async def get_config_bool(key: str, default: bool = False) -> bool:
    """Read config value as bool."""
    val = await get_config(key, str(default).lower())
    return val.lower() in ("true", "1", "yes")
