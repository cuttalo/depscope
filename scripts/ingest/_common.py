"""Common utilities for DepScope ingestion pipelines.

Rate-limited HTTP helpers, DB pool, logging, package selection.
"""
import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import aiohttp
import asyncpg

sys.path.insert(0, "/home/deploy/depscope")

from api.config import DATABASE_URL  # noqa: E402

LOG_DIR = Path("/var/log/depscope")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "ingest.log"

CONFIG_DIR = Path("/home/deploy/depscope/config")


def get_logger(name: str) -> logging.Logger:
    lg = logging.getLogger(name)
    if lg.handlers:
        return lg
    lg.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    fh = logging.FileHandler(LOG_PATH)
    fh.setFormatter(fmt)
    lg.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    lg.addHandler(sh)
    return lg


def load_github_token() -> Optional[str]:
    env = os.getenv("GITHUB_TOKEN")
    if env:
        return env.strip()
    p = CONFIG_DIR / "github.json"
    if p.exists():
        try:
            return json.loads(p.read_text()).get("token")
        except Exception:
            return None
    return None


GITHUB_TOKEN = load_github_token()


async def get_db_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=4)


_REPO_RE = re.compile(r"github\.com[/:]([^/]+)/([^/#?]+?)(?:\.git)?/?$")


def parse_github_repo(repo_url: Optional[str]) -> Optional[tuple[str, str]]:
    if not repo_url:
        return None
    # Normalize common prefixes
    url = repo_url.strip()
    url = re.sub(r"^git\+", "", url)
    url = re.sub(r"^ssh://git@", "https://", url)
    url = re.sub(r"^git://", "https://", url)
    m = _REPO_RE.search(url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    if not owner or not repo:
        return None
    return owner, repo


class RateLimiter:
    """Simple per-host rate limiter: `max_calls` per `period` seconds."""

    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self.calls: list[float] = []
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            now = time.monotonic()
            # Drop old entries
            self.calls = [t for t in self.calls if now - t < self.period]
            if len(self.calls) >= self.max_calls:
                wait = self.period - (now - self.calls[0]) + 0.05
                if wait > 0:
                    await asyncio.sleep(wait)
                    now = time.monotonic()
                    self.calls = [t for t in self.calls if now - t < self.period]
            self.calls.append(time.monotonic())


async def http_get(
    session: aiohttp.ClientSession,
    url: str,
    *,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: int = 20,
    max_retries: int = 4,
    logger: Optional[logging.Logger] = None,
) -> Optional[Any]:
    """GET with exponential backoff on 429/5xx. Returns parsed JSON or None."""
    backoff = 1.5
    for attempt in range(max_retries):
        try:
            async with session.get(
                url,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status == 200:
                    try:
                        return await resp.json(content_type=None)
                    except Exception:
                        txt = await resp.text()
                        try:
                            return json.loads(txt)
                        except Exception:
                            return None
                if resp.status in (429, 502, 503, 504):
                    # Rate limited / transient
                    retry_after = resp.headers.get("Retry-After")
                    wait = (
                        float(retry_after)
                        if retry_after and retry_after.replace(".", "").isdigit()
                        else backoff
                    )
                    if logger:
                        logger.warning(
                            f"{resp.status} on {url} — sleep {wait:.1f}s (attempt {attempt+1})"
                        )
                    await asyncio.sleep(wait)
                    backoff *= 2
                    continue
                if resp.status == 403 and "x-ratelimit-remaining" in resp.headers:
                    remaining = resp.headers.get("x-ratelimit-remaining")
                    reset = resp.headers.get("x-ratelimit-reset")
                    if remaining == "0" and reset:
                        wait = max(1, int(reset) - int(time.time()) + 2)
                        wait = min(wait, 120)
                        if logger:
                            logger.warning(
                                f"GitHub rate limit reached — sleep {wait}s"
                            )
                        await asyncio.sleep(wait)
                        continue
                if resp.status in (404, 410, 451):
                    return None
                if logger:
                    logger.warning(f"HTTP {resp.status} on {url}")
                return None
        except asyncio.TimeoutError:
            if logger:
                logger.warning(f"Timeout on {url} (attempt {attempt+1})")
            await asyncio.sleep(backoff)
            backoff *= 2
        except aiohttp.ClientError as e:
            if logger:
                logger.warning(f"ClientError on {url}: {e}")
            await asyncio.sleep(backoff)
            backoff *= 2
    return None


async def get_top_packages(
    pool: asyncpg.Pool,
    ecosystems: list[str] | None = None,
    limit_per_ecosystem: int = 100,
    require_repo: bool = True,
) -> list[dict]:
    """Top packages per ecosystem ordered by weekly downloads desc."""
    ecosystems = ecosystems or ["npm", "pypi", "cargo", "go"]
    out: list[dict] = []
    async with pool.acquire() as conn:
        for eco in ecosystems:
            q = """
                SELECT id, ecosystem, name, repository, latest_version,
                       downloads_weekly
                FROM packages
                WHERE ecosystem = $1
            """
            if require_repo:
                q += " AND repository IS NOT NULL AND repository ILIKE '%github.com%'"
            q += " ORDER BY downloads_weekly DESC NULLS LAST LIMIT $2"
            rows = await conn.fetch(q, eco, limit_per_ecosystem)
            for r in rows:
                out.append(dict(r))
    return out


def strip_html(html: str) -> str:
    if not html:
        return ""
    # Remove script/style blocks
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S | re.I)
    # Convert <br>, <p> to newlines for readability
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    html = re.sub(r"</p\s*>", "\n\n", html, flags=re.I)
    # Strip all remaining tags
    text = re.sub(r"<[^>]+>", "", html)
    # Decode common entities
    replacements = {
        "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&quot;": '"', "&#39;": "'", "&nbsp;": " ",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_version(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    v = str(v).strip()
    v = v.strip("vV").strip()
    # Drop pre-release noise beyond a sane length
    if len(v) > 50:
        return None
    return v or None


def pick_severity(labels: list[str]) -> str:
    """Map GitHub-style labels to our 4-bucket severity scale."""
    s = " ".join((labels or [])).lower()
    if any(k in s for k in ("critical", "p0", "security", "severe", "crash")):
        return "critical"
    if any(k in s for k in ("high", "p1", "major")):
        return "high"
    if any(k in s for k in ("low", "p3", "minor", "trivial")):
        return "low"
    return "medium"
