"""Fetch closed `bug`-labeled issues from top-package GitHub repos and
insert them into `known_bugs`.

Idempotent: `bug_id = "github:{issue_number}"`, UPSERT via the existing
unique (ecosystem, package_name, bug_id) constraint.
"""
import asyncio
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
    pick_severity,
)

logger = get_logger("github_bugs")

PER_PACKAGE_ISSUES = 30
PACKAGES_PER_ECOSYSTEM = 100
ECOSYSTEMS = ["npm", "pypi", "cargo", "go"]

OSV_BATCH_URL = "https://api.osv.dev/v1/query"
OSV_ECO_MAP = {
    "npm": "npm",
    "pypi": "PyPI",
    "cargo": "crates.io",
    "go": "Go",
}

# Parse version strings from issue bodies. First match wins.
_VERSION_PATTERNS = [
    re.compile(r"version[^\w\n]{0,4}([0-9]+(?:\.[0-9]+){1,3}(?:[-.+][\w.]+)?)", re.I),
    re.compile(r"v([0-9]+\.[0-9]+(?:\.[0-9]+)?)\b"),
    re.compile(r"\b([0-9]+\.[0-9]+\.[0-9]+)\b"),
]

_FIXED_PATTERNS = [
    re.compile(r"fixed in[^\w\n]{0,4}v?([0-9]+(?:\.[0-9]+){1,3}(?:[-.+][\w.]+)?)", re.I),
    re.compile(r"released in[^\w\n]{0,4}v?([0-9]+(?:\.[0-9]+){1,3})", re.I),
    re.compile(r"resolved in[^\w\n]{0,4}v?([0-9]+(?:\.[0-9]+){1,3})", re.I),
]


def extract_version(text: str) -> Optional[str]:
    if not text:
        return None
    for pat in _VERSION_PATTERNS:
        m = pat.search(text)
        if m:
            return normalize_version(m.group(1))
    return None


def extract_fixed_version(text: str) -> Optional[str]:
    if not text:
        return None
    for pat in _FIXED_PATTERNS:
        m = pat.search(text)
        if m:
            return normalize_version(m.group(1))
    return None


async def fetch_bug_issues(
    session: aiohttp.ClientSession,
    owner: str,
    repo: str,
    headers: dict,
    limiter: RateLimiter,
) -> list[dict]:
    """Fetch closed issues labeled `bug`. Falls back to generic closed issues."""
    out: list[dict] = []
    for label in ("bug", "kind/bug", "type: bug", "type/bug"):
        await limiter.acquire()
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        params = {
            "state": "closed",
            "labels": label,
            "per_page": PER_PACKAGE_ISSUES,
            "sort": "created",
            "direction": "desc",
        }
        data = await http_get(
            session, url, headers=headers, params=params, logger=logger
        )
        if data and isinstance(data, list):
            # Filter out pull requests (GitHub returns them on issues endpoint)
            out = [i for i in data if isinstance(i, dict) and not i.get("pull_request")]
            if out:
                return out
    return out


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
        issues = await fetch_bug_issues(session, owner, name, headers, limiter)
    except Exception as e:
        logger.warning(f"fetch failed {owner}/{name}: {e}")
        return 0
    if not issues:
        return 0
    inserted = 0
    async with pool.acquire() as conn:
        for issue in issues:
            try:
                number = issue.get("number")
                title = (issue.get("title") or "").strip()
                body = (issue.get("body") or "")[:20000]
                if not title or not number:
                    continue
                if len(title) < 8:
                    continue
                labels = [
                    lab.get("name") if isinstance(lab, dict) else str(lab)
                    for lab in (issue.get("labels") or [])
                ]
                severity = pick_severity(labels)
                affected = extract_version(body) or extract_version(title)
                fixed = extract_fixed_version(body)
                bug_id = f"github:{number}"
                status = "fixed" if issue.get("state") == "closed" else "open"
                source_url = issue.get("html_url") or (
                    f"https://github.com/{owner}/{name}/issues/{number}"
                )
                res = await conn.execute(
                    """
                    INSERT INTO known_bugs(
                        package_id, ecosystem, package_name,
                        affected_version, fixed_version, bug_id,
                        title, description, severity, status,
                        source, source_url, labels
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
                    )
                    ON CONFLICT (ecosystem, package_name, bug_id) DO NOTHING
                    """,
                    pkg["id"],
                    pkg["ecosystem"],
                    pkg["name"],
                    affected,
                    fixed,
                    bug_id,
                    title[:2000],
                    body[:10000] or None,
                    severity,
                    status,
                    "github_issues",
                    source_url,
                    labels[:20],
                )
                if res and res.endswith("1"):
                    inserted += 1
            except Exception as e:
                logger.warning(f"insert failed {owner}/{name}#{issue.get('number')}: {e}")
    if inserted:
        logger.info(f"{pkg['ecosystem']}/{pkg['name']}: +{inserted} bugs")
    return inserted


async def fetch_osv_bugs(
    session: aiohttp.ClientSession,
    pkg: dict,
    osv_limiter: RateLimiter,
) -> list[dict]:
    """Fetch all OSV vulnerabilities for a package (counts as 'bugs')."""
    eco = OSV_ECO_MAP.get(pkg["ecosystem"])
    if not eco:
        return []
    await osv_limiter.acquire()
    payload = {"package": {"name": pkg["name"], "ecosystem": eco}}
    for attempt in range(3):
        try:
            async with session.post(
                OSV_BATCH_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    return data.get("vulns") or []
                if resp.status in (429, 502, 503):
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                return []
        except Exception:
            await asyncio.sleep(1.5 * (attempt + 1))
    return []


def _osv_affected_fixed(vuln: dict) -> tuple[Optional[str], Optional[str]]:
    """Pull affected range + first fixed version from an OSV record."""
    for aff in vuln.get("affected") or []:
        for r in aff.get("ranges") or []:
            events = r.get("events") or []
            introduced = None
            fixed = None
            for ev in events:
                if "introduced" in ev and ev["introduced"] != "0":
                    introduced = ev["introduced"]
                if "fixed" in ev:
                    fixed = ev["fixed"]
            if introduced or fixed:
                return (
                    normalize_version(introduced) if introduced else None,
                    normalize_version(fixed) if fixed else None,
                )
    return None, None


async def process_package_osv(
    session: aiohttp.ClientSession,
    pkg: dict,
    osv_limiter: RateLimiter,
    pool,
) -> int:
    try:
        vulns = await fetch_osv_bugs(session, pkg, osv_limiter)
    except Exception as e:
        logger.warning(f"osv fetch {pkg.get('name')}: {e}")
        return 0
    if not vulns:
        return 0
    inserted = 0
    async with pool.acquire() as conn:
        for v in vulns:
            vid = v.get("id")
            if not vid:
                continue
            title = (v.get("summary") or "").strip() or f"{vid}: advisory"
            details = (v.get("details") or "")[:8000]
            if len(title) < 8 and len(details) < 50:
                continue
            affected, fixed = _osv_affected_fixed(v)
            db_specific = v.get("database_specific") or {}
            severity_s = str(db_specific.get("severity") or "").lower()
            # OSV severity is usually CRITICAL/HIGH/MODERATE/LOW
            if "critical" in severity_s:
                severity = "critical"
            elif "high" in severity_s:
                severity = "high"
            elif "low" in severity_s:
                severity = "low"
            else:
                severity = "medium"
            url_refs = [r.get("url") for r in (v.get("references") or []) if r.get("url")]
            source_url = url_refs[0] if url_refs else f"https://osv.dev/vulnerability/{vid}"
            labels = v.get("aliases") or []
            try:
                res = await conn.execute(
                    """
                    INSERT INTO known_bugs(
                        package_id, ecosystem, package_name,
                        affected_version, fixed_version, bug_id,
                        title, description, severity, status,
                        source, source_url, labels
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                    ON CONFLICT (ecosystem, package_name, bug_id) DO NOTHING
                    """,
                    pkg["id"],
                    pkg["ecosystem"],
                    pkg["name"],
                    affected,
                    fixed,
                    f"osv:{vid}",
                    title[:2000],
                    details or None,
                    severity,
                    "fixed" if fixed else "open",
                    "osv",
                    source_url,
                    labels[:20],
                )
                if res and res.endswith("1"):
                    inserted += 1
            except Exception as e:
                logger.warning(f"osv insert {pkg['name']} {vid}: {e}")
    if inserted:
        logger.info(f"OSV {pkg['ecosystem']}/{pkg['name']}: +{inserted} bugs")
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
            logger.info("github_bugs: using authenticated token")
        else:
            logger.warning("github_bugs: no token — unauthenticated mode")

        # GitHub: unauth = 60 req/hour → pace at 1 per 70s to not burn quota;
        # when auth works we go faster. We sample rate_limit first.
        limiter = RateLimiter(max_calls=1, period=1.0)
        # OSV: very generous (no documented hard cap). We still throttle.
        osv_limiter = RateLimiter(max_calls=5, period=1.0)

        before = await pool.fetchval("SELECT COUNT(*) FROM known_bugs")
        pkgs = await get_top_packages(
            pool,
            ecosystems=ECOSYSTEMS,
            limit_per_ecosystem=PACKAGES_PER_ECOSYSTEM,
        )
        logger.info(f"github_bugs: processing {len(pkgs)} packages")

        # Check remaining GitHub quota before we start
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
        logger.info(
            f"github_bugs: github core quota {gh_remaining}/{gh_limit}"
        )
        # If we're on the unauth tier (limit=60), skip GitHub entirely —
        # OSV alone gives us enough bugs and repeated GitHub calls waste
        # time on long 120s sleeps. We only use the API when the token
        # actually buys us the 5000/h tier.
        if gh_limit < 500:
            logger.warning(
                "github_bugs: low-quota tier detected — skipping GitHub "
                "issues, relying on OSV only"
            )
            gh_budget = 0
        else:
            gh_budget = max(0, gh_remaining - 20)

        total_gh = 0
        total_osv = 0
        async with aiohttp.ClientSession() as session:
            for i, pkg in enumerate(pkgs, 1):
                # Primary: OSV (no-quota path for real bugs/CVEs)
                try:
                    total_osv += await process_package_osv(
                        session, pkg, osv_limiter, pool
                    )
                except Exception as e:
                    logger.warning(f"osv pkg {pkg.get('name')}: {e}")
                # Secondary: GitHub issues — only while budget allows
                if gh_budget >= 2:
                    try:
                        delta = await process_package(
                            session, pkg, headers, limiter, pool
                        )
                        total_gh += delta
                        # `fetch_bug_issues` tries up to 4 labels — at worst
                        # 4 reqs; at best 1. Be conservative.
                        gh_budget = max(0, gh_budget - 2)
                    except Exception as e:
                        logger.warning(f"gh pkg {pkg.get('name')}: {e}")
                if i % 25 == 0:
                    logger.info(
                        f"github_bugs progress: {i}/{len(pkgs)} pkgs — "
                        f"+{total_gh} GH, +{total_osv} OSV (gh_budget={gh_budget})"
                    )

        after = await pool.fetchval("SELECT COUNT(*) FROM known_bugs")
        total = total_gh + total_osv
        logger.info(
            f"github_bugs done: +{total} inserted (GH={total_gh} OSV={total_osv}) "
            f"({before} -> {after}) in {time.time()-start:.1f}s"
        )
        return total
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
