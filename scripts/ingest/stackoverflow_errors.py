"""Ingest error-style Stack Overflow questions into `errors`.

Uses the public StackExchange API (no auth → 300 req/day/IP filter-free,
10k req/day with a free key). We do a conservative paging strategy and
drop anything that doesn't look like a concrete error signature.
"""
import asyncio
import hashlib
import re
import sys
import time
from typing import Optional

import aiohttp

sys.path.insert(0, "/home/deploy/depscope")

from api.verticals import hash_error_pattern, normalize_error  # noqa: E402
from scripts.ingest._common import (
    RateLimiter,
    get_db_pool,
    get_logger,
    http_get,
    strip_html,
)

logger = get_logger("stackoverflow_errors")

# (tag, ecosystem). We use SO tags that are package-oriented.
TAG_MAP: list[tuple[str, str]] = [
    # npm ecosystem
    ("node.js", "npm"),
    ("npm", "npm"),
    ("npm-install", "npm"),
    ("reactjs", "npm"),
    ("next.js", "npm"),
    ("webpack", "npm"),
    ("vite", "npm"),
    ("typescript", "npm"),
    ("vue.js", "npm"),
    ("express", "npm"),
    ("nestjs", "npm"),
    ("angular", "npm"),
    ("nuxt.js", "npm"),
    ("svelte", "npm"),
    ("babel", "npm"),
    ("eslint", "npm"),
    ("prettier", "npm"),
    ("jest", "npm"),
    ("vitest", "npm"),
    ("mongoose", "npm"),
    ("prisma", "npm"),
    ("axios", "npm"),
    ("react-native", "npm"),
    ("electron", "npm"),
    ("nodejs-stream", "npm"),
    ("npm-scripts", "npm"),
    ("yarn", "npm"),
    ("pnpm", "npm"),
    ("rollup", "npm"),
    ("esbuild", "npm"),
    # pypi
    ("python", "pypi"),
    ("pip", "pypi"),
    ("pip-install", "pypi"),
    ("django", "pypi"),
    ("flask", "pypi"),
    ("pandas", "pypi"),
    ("numpy", "pypi"),
    ("pytorch", "pypi"),
    ("tensorflow", "pypi"),
    ("fastapi", "pypi"),
    ("sqlalchemy", "pypi"),
    ("celery", "pypi"),
    ("pytest", "pypi"),
    ("asyncio", "pypi"),
    ("aiohttp", "pypi"),
    ("requests", "pypi"),
    ("pydantic", "pypi"),
    ("huggingface-transformers", "pypi"),
    ("scikit-learn", "pypi"),
    ("matplotlib", "pypi"),
    ("scipy", "pypi"),
    ("beautifulsoup", "pypi"),
    ("selenium", "pypi"),
    ("boto3", "pypi"),
    ("pipenv", "pypi"),
    ("poetry", "pypi"),
    ("virtualenv", "pypi"),
    # cargo
    ("rust", "cargo"),
    ("cargo", "cargo"),
    ("rust-cargo", "cargo"),
    ("tokio", "cargo"),
    ("serde", "cargo"),
    ("actix-web", "cargo"),
    ("rust-axum", "cargo"),
    ("rust-diesel", "cargo"),
    # go
    ("go", "go"),
    ("go-modules", "go"),
    ("go-gin", "go"),
    ("go-gorm", "go"),
    ("grpc-go", "go"),
]

QUESTIONS_PER_TAG = 100  # 50 per page × 2 pages
PAGESIZE = 50
MIN_TITLE_LEN = 15
MIN_SOLUTION_LEN = 60
MIN_SCORE = 1  # question min score (relaxed)
MIN_ANSWER_SCORE = 3  # accepted/top answer min score (relaxed)

API = "https://api.stackexchange.com/2.3"


def extract_package_from_tags_and_title(
    ecosystem: str, tags: list[str], title: str
) -> Optional[str]:
    """Cheap heuristic: known package names appearing in tags or title."""
    low = (title or "").lower()
    for t in tags or []:
        tl = t.lower()
        if tl in ("javascript", "html", "css", "python", "go", "rust"):
            continue
        if re.match(r"^[a-z0-9][a-z0-9_\-.]+$", tl):
            return tl
    # Look for quoted module name in title (e.g. "Cannot find module 'express'")
    m = re.search(r"['\"]([a-z0-9][\w\-./@]{1,40})['\"]", low)
    if m:
        return m.group(1)
    return None


async def fetch_questions(
    session: aiohttp.ClientSession,
    tag: str,
    limiter: RateLimiter,
    pages: int = 2,
) -> list[dict]:
    out: list[dict] = []
    for page in range(1, pages + 1):
        await limiter.acquire()
        params = {
            "tagged": tag,
            "sort": "votes",
            "order": "desc",
            "site": "stackoverflow",
            "pagesize": PAGESIZE,
            "page": page,
            "filter": "withbody",  # include body in response
        }
        data = await http_get(
            session,
            f"{API}/questions",
            params=params,
            logger=logger,
        )
        if not data or not isinstance(data, dict):
            break
        items = data.get("items") or []
        out.extend(items)
        if not data.get("has_more"):
            break
        backoff = data.get("backoff")
        if backoff:
            logger.info(f"SO backoff {backoff}s on tag {tag}")
            await asyncio.sleep(int(backoff))
        if data.get("quota_remaining", 9999) < 20:
            logger.warning(f"SO quota low: {data.get('quota_remaining')}")
            break
    return out


async def fetch_answers(
    session: aiohttp.ClientSession,
    question_ids: list[int],
    limiter: RateLimiter,
) -> dict[int, dict]:
    """Return {question_id: best_answer_dict} for ids that have one."""
    if not question_ids:
        return {}
    best: dict[int, dict] = {}
    # Batch in groups of 100
    for i in range(0, len(question_ids), 100):
        chunk = question_ids[i : i + 100]
        ids = ";".join(str(x) for x in chunk)
        await limiter.acquire()
        params = {
            "site": "stackoverflow",
            "sort": "votes",
            "order": "desc",
            "pagesize": 100,
            "filter": "withbody",
        }
        data = await http_get(
            session,
            f"{API}/questions/{ids}/answers",
            params=params,
            logger=logger,
        )
        if not data or not isinstance(data, dict):
            continue
        for a in data.get("items") or []:
            qid = a.get("question_id")
            if not qid:
                continue
            if qid not in best:
                best[qid] = a
            else:
                # Keep the higher-scoring one (accepted beats score)
                cur = best[qid]
                if a.get("is_accepted") and not cur.get("is_accepted"):
                    best[qid] = a
                elif (a.get("score") or 0) > (cur.get("score") or 0):
                    best[qid] = a
        if data.get("backoff"):
            await asyncio.sleep(int(data.get("backoff")))
    return best


async def process_tag(
    session: aiohttp.ClientSession,
    tag: str,
    ecosystem: str,
    limiter: RateLimiter,
    pool,
) -> int:
    try:
        questions = await fetch_questions(session, tag, limiter)
    except Exception as e:
        logger.warning(f"SO questions fetch failed tag={tag}: {e}")
        return 0
    # Keep questions that look like an error and meet quality bar
    candidates: list[dict] = []
    ERROR_KEYWORDS = (
        "error", "cannot", "failed", "exception", "undefined", "unexpected",
        "typeerror", "referenceerror", "syntaxerror", "importerror",
        "modulenotfound", "permission denied", "not found", "invalid",
        "deprecated", "warning", "segfault", "panic", "abort",
        "einval", "econnrefused", "eacces", "enoent",
    )
    for q in questions:
        title = q.get("title") or ""
        tl = title.lower()
        if not any(k in tl for k in ERROR_KEYWORDS):
            continue
        if len(title) < MIN_TITLE_LEN:
            continue
        if (q.get("score") or 0) < MIN_SCORE:
            continue
        candidates.append(q)
    if not candidates:
        return 0

    qids = [q["question_id"] for q in candidates if q.get("question_id")]
    answers = await fetch_answers(session, qids, limiter)

    inserted = 0
    async with pool.acquire() as conn:
        for q in candidates:
            qid = q.get("question_id")
            ans = answers.get(qid)
            if not ans:
                continue
            if (ans.get("score") or 0) < MIN_ANSWER_SCORE and not ans.get(
                "is_accepted"
            ):
                continue
            title = (q.get("title") or "").strip()
            body_html = q.get("body") or ""
            body_text = strip_html(body_html)
            solution_text = strip_html(ans.get("body") or "")
            if len(solution_text) < MIN_SOLUTION_LEN:
                continue
            # Pattern = clean title (error signature)
            pattern = title
            norm = normalize_error(pattern)
            if len(norm) < 20:
                continue
            h = hash_error_pattern(pattern)
            tags = q.get("tags") or []
            pkg_name = extract_package_from_tags_and_title(ecosystem, tags, title)
            source_url = q.get("link") or f"https://stackoverflow.com/q/{qid}"
            confidence = min(
                0.95,
                0.4 + 0.05 * min((ans.get("score") or 0), 20)
                + (0.1 if ans.get("is_accepted") else 0),
            )
            try:
                res = await conn.execute(
                    """
                    INSERT INTO errors(
                        hash, pattern, full_message, ecosystem, package_name,
                        solution, confidence, source, source_url, votes
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                    ON CONFLICT (hash) DO UPDATE SET
                        votes = errors.votes + 1,
                        updated_at = now()
                    """,
                    h,
                    pattern[:800],
                    body_text[:6000] or None,
                    ecosystem,
                    pkg_name,
                    solution_text[:8000],
                    float(confidence),
                    "stackoverflow",
                    source_url,
                    int(q.get("score") or 0),
                )
                if res and res.endswith("1"):
                    inserted += 1
            except Exception as e:
                logger.warning(f"insert SO {qid}: {e}")
    if inserted:
        logger.info(f"SO tag={tag} eco={ecosystem}: +{inserted}")
    return inserted


async def main() -> int:
    start = time.time()
    pool = await get_db_pool()
    try:
        # SO allows ~30 req/s but we stay conservative at 2/s
        limiter = RateLimiter(max_calls=2, period=1.0)
        before = await pool.fetchval("SELECT COUNT(*) FROM errors")
        total = 0
        async with aiohttp.ClientSession() as session:
            for tag, eco in TAG_MAP:
                try:
                    total += await process_tag(session, tag, eco, limiter, pool)
                except Exception as e:
                    logger.warning(f"tag {tag} failed: {e}")
        after = await pool.fetchval("SELECT COUNT(*) FROM errors")
        logger.info(
            f"stackoverflow_errors done: +{total} ({before} -> {after}) "
            f"in {time.time()-start:.1f}s"
        )
        return total
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
