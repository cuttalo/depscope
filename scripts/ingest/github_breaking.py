"""Fetch GitHub releases from top packages and extract breaking changes.

Each matching release becomes a row in `breaking_changes`. Uses the
(package_id, from_version, to_version, change_type, desc_hash) unique index
to avoid duplicates.
"""
import asyncio
import hashlib
import re
import time
from typing import Optional

import aiohttp

from scripts.ingest._common import (
    GITHUB_TOKEN,
    RateLimiter,
    get_db_pool,
    get_logger,
    get_top_packages,
    http_get,
    normalize_version,
    parse_github_repo,
)

logger = get_logger("github_breaking")

PER_PACKAGE_RELEASES = 20
PACKAGES_PER_ECOSYSTEM = 100
ECOSYSTEMS = ["npm", "pypi", "cargo", "go"]

BREAKING_KEYWORDS = [
    "breaking change",
    "breaking-change",
    "breaking:",
    "breaking!",
    "backward-incompatible",
    "backwards incompatible",
    "⚠️",
    "bc break",
    "bc-break",
    "removed:",
    "removal:",
]

# Section headers commonly used in release notes for breaking changes
_SECTION_HEADERS = re.compile(
    r"(?im)^\s*#+\s*(?:\W*)?(breaking changes?|bc breaks?|removed|"
    r"backwards[- ]?incompatible[^\n]*)\s*$"
)

_MIGRATION_HEADER = re.compile(
    r"(?im)^\s*#+\s*(?:\W*)?(migration(?: guide)?|upgrade guide|how to migrate)\s*$"
)

_BULLET = re.compile(r"(?m)^\s*[-*]\s+(.*?)(?:\n|$)")


def _extract_block(text: str, header_re: re.Pattern) -> Optional[str]:
    """Return block of text under the first matching header, up to next header."""
    if not text:
        return None
    m = header_re.search(text)
    if not m:
        return None
    start = m.end()
    # Find next top-level header of any kind
    rest = text[start:]
    next_header = re.search(r"(?m)^\s*#{1,6}\s+\S", rest)
    block = rest[: next_header.start()] if next_header else rest
    block = block.strip()
    return block or None


def _contains_breaking(body: str) -> bool:
    low = body.lower()
    return any(k in low for k in BREAKING_KEYWORDS)


def _split_into_changes(block: str) -> list[str]:
    """Extract bullet points or split paragraphs into individual changes."""
    bullets = [b.strip() for b in _BULLET.findall(block) if b.strip()]
    if bullets:
        return bullets[:25]
    # Fallback: paragraphs
    paras = [p.strip() for p in re.split(r"\n{2,}", block) if len(p.strip()) > 20]
    return paras[:15]


def desc_hash(text: str) -> str:
    return hashlib.md5(text.strip().lower().encode("utf-8")).hexdigest()


def classify_change(text: str) -> str:
    low = text.lower()
    if "remov" in low or "delet" in low:
        return "removed"
    if "rename" in low:
        return "renamed"
    if "deprecat" in low:
        return "deprecated"
    if "api" in low or "signature" in low or "argument" in low or "parameter" in low:
        return "api"
    if "behav" in low or "default" in low:
        return "behavior"
    return "breaking"


async def fetch_releases(
    session: aiohttp.ClientSession,
    owner: str,
    repo: str,
    headers: dict,
    limiter: RateLimiter,
) -> list[dict]:
    await limiter.acquire()
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    params = {"per_page": PER_PACKAGE_RELEASES}
    data = await http_get(session, url, headers=headers, params=params, logger=logger)
    if not data or not isinstance(data, list):
        return []
    return data


async def fetch_changelog_raw(
    session: aiohttp.ClientSession,
    owner: str,
    repo: str,
    raw_limiter: RateLimiter,
) -> Optional[str]:
    """Try common changelog locations via raw.githubusercontent.com.

    No GitHub API quota cost. We try the 4 most common {branch,path}
    combinations and bail out early on the first hit.
    """
    candidates = [
        ("main", "CHANGELOG.md"),
        ("master", "CHANGELOG.md"),
        ("main", "HISTORY.md"),
        ("master", "HISTORY.md"),
    ]
    for branch, path in candidates:
        await raw_limiter.acquire()
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status == 200:
                    txt = await resp.text()
                    if len(txt) > 2_000_000:
                        return txt[:2_000_000]
                    return txt
        except Exception:
            continue
    return None


# Regex for typical changelog version headers
_CHANGELOG_HEADER = re.compile(
    r"(?m)^\s*#{1,3}\s*\[?v?([0-9]+\.[0-9]+(?:\.[0-9]+)?(?:[-.+][\w.]+)?)\]?"
)


def parse_changelog(text: str) -> list[dict]:
    """Split a changelog into `[{version, body}]` sections (newest first)."""
    if not text:
        return []
    matches = list(_CHANGELOG_HEADER.finditer(text))
    sections: list[dict] = []
    for i, m in enumerate(matches):
        version = normalize_version(m.group(1))
        if not version:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append({"version": version, "body": body})
    return sections


async def process_package_changelog(
    session: aiohttp.ClientSession,
    pkg: dict,
    raw_limiter: RateLimiter,
    pool,
) -> int:
    repo = parse_github_repo(pkg.get("repository"))
    if not repo:
        return 0
    owner, name = repo
    try:
        text = await fetch_changelog_raw(session, owner, name, raw_limiter)
    except Exception as e:
        logger.warning(f"changelog fetch {owner}/{name}: {e}")
        return 0
    if not text:
        return 0
    sections = parse_changelog(text)
    if not sections:
        return 0
    inserted = 0
    prev: Optional[str] = None
    # Sections are newest-first; we iterate newest-first and use the NEXT
    # section as from_version for each entry.
    async with pool.acquire() as conn:
        for idx, sec in enumerate(sections):
            to_version = sec["version"]
            from_version = sections[idx + 1]["version"] if idx + 1 < len(sections) else "unknown"
            body = sec["body"]
            if not _contains_breaking(body):
                continue
            block = _extract_block(body, _SECTION_HEADERS) or body
            migration = _extract_block(body, _MIGRATION_HEADER)
            changes = _split_into_changes(block)
            if not changes:
                changes = [block[:500]]
            for ch in changes:
                desc = ch.strip()
                if len(desc) < 15 or len(desc) > 1000:
                    continue
                ct = classify_change(desc)
                h = desc_hash(desc)
                try:
                    res = await conn.execute(
                        """
                        INSERT INTO breaking_changes(
                            package_id, from_version, to_version,
                            change_type, description, migration_hint, desc_hash
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (package_id, from_version, to_version,
                                     change_type, desc_hash) DO NOTHING
                        """,
                        pkg["id"],
                        from_version,
                        to_version,
                        ct,
                        desc,
                        (migration or None),
                        h,
                    )
                    if res and res.endswith("1"):
                        inserted += 1
                except Exception as e:
                    logger.warning(f"insert changelog {owner}/{name}: {e}")
    if inserted:
        logger.info(f"CHANGELOG {pkg['ecosystem']}/{pkg['name']}: +{inserted}")
    return inserted


async def process_package(
    session: aiohttp.ClientSession,
    pkg: dict,
    headers: dict,
    limiter: RateLimiter,
    pool,
) -> int:
    repo = parse_github_repo(pkg.get("repository"))
    if not repo:
        return 0
    owner, name = repo
    try:
        releases = await fetch_releases(session, owner, name, headers, limiter)
    except Exception as e:
        logger.warning(f"releases fetch failed {owner}/{name}: {e}")
        return 0
    if not releases:
        return 0
    # Sort oldest -> newest to compute from_version / to_version
    releases_sorted = sorted(
        releases,
        key=lambda r: r.get("published_at") or r.get("created_at") or "",
    )
    prev_version: Optional[str] = None
    inserted = 0
    async with pool.acquire() as conn:
        for rel in releases_sorted:
            body = rel.get("body") or ""
            to_version = normalize_version(rel.get("tag_name") or rel.get("name"))
            from_version = prev_version
            prev_version = to_version or prev_version
            if not to_version:
                continue
            if not _contains_breaking(body):
                continue
            block = _extract_block(body, _SECTION_HEADERS) or body
            migration = _extract_block(body, _MIGRATION_HEADER)
            changes = _split_into_changes(block)
            if not changes:
                changes = [block[:500]]
            for ch in changes:
                desc = ch.strip()
                if len(desc) < 15 or len(desc) > 1000:
                    continue
                ct = classify_change(desc)
                h = desc_hash(desc)
                try:
                    res = await conn.execute(
                        """
                        INSERT INTO breaking_changes(
                            package_id, from_version, to_version,
                            change_type, description, migration_hint, desc_hash
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (package_id, from_version, to_version,
                                     change_type, desc_hash) DO NOTHING
                        """,
                        pkg["id"],
                        from_version or "unknown",
                        to_version,
                        ct,
                        desc,
                        (migration or None),
                        h,
                    )
                    if res and res.endswith("1"):
                        inserted += 1
                except Exception as e:
                    logger.warning(f"insert breaking {owner}/{name}: {e}")
    if inserted:
        logger.info(f"{pkg['ecosystem']}/{pkg['name']}: +{inserted} breaking")
    return inserted


async def main() -> int:
    start = time.time()
    pool = await get_db_pool()
    try:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "depscope-ingest/1.0",
        }
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
            logger.info("github_breaking: authenticated")
        else:
            logger.warning("github_breaking: unauthenticated")

        limiter = RateLimiter(max_calls=1, period=1.0)
        raw_limiter = RateLimiter(max_calls=10, period=1.0)

        before = await pool.fetchval("SELECT COUNT(*) FROM breaking_changes")
        pkgs = await get_top_packages(
            pool,
            ecosystems=ECOSYSTEMS,
            limit_per_ecosystem=PACKAGES_PER_ECOSYSTEM,
        )
        logger.info(f"github_breaking: processing {len(pkgs)} packages")

        # Budget GitHub Releases API calls
        gh_remaining = 0
        gh_limit = 0
        async with aiohttp.ClientSession() as probe:
            rl = await http_get(
                probe, "https://api.github.com/rate_limit",
                headers=headers, logger=logger,
            )
            if isinstance(rl, dict):
                core = (rl.get("resources") or {}).get("core", {})
                gh_remaining = int(core.get("remaining") or 0)
                gh_limit = int(core.get("limit") or 0)
        if gh_limit < 500:
            gh_budget = 0
            logger.warning(
                "github_breaking: low-quota tier — skipping Releases API, "
                "relying on raw CHANGELOG only"
            )
        else:
            gh_budget = max(0, gh_remaining - 20)
        logger.info(
            f"github_breaking: github core quota {gh_remaining}/{gh_limit}"
        )

        total_gh = 0
        total_cl = 0
        async with aiohttp.ClientSession() as session:
            for i, pkg in enumerate(pkgs, 1):
                # Primary: CHANGELOG via raw.githubusercontent.com (free)
                try:
                    total_cl += await process_package_changelog(
                        session, pkg, raw_limiter, pool
                    )
                except Exception as e:
                    logger.warning(f"changelog pkg {pkg.get('name')}: {e}")
                # Secondary: Releases API — only while quota allows
                if gh_budget >= 1:
                    try:
                        total_gh += await process_package(
                            session, pkg, headers, limiter, pool
                        )
                        gh_budget = max(0, gh_budget - 1)
                    except Exception as e:
                        logger.warning(f"releases pkg {pkg.get('name')}: {e}")
                if i % 25 == 0:
                    logger.info(
                        f"github_breaking progress: {i}/{len(pkgs)}, "
                        f"+{total_gh} GH, +{total_cl} CL (budget={gh_budget})"
                    )

        after = await pool.fetchval("SELECT COUNT(*) FROM breaking_changes")
        total = total_gh + total_cl
        logger.info(
            f"github_breaking done: +{total} inserted (GH={total_gh} CL={total_cl}) "
            f"({before} -> {after}) in {time.time()-start:.1f}s"
        )
        return total
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
