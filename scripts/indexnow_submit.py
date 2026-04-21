"""IndexNow protocol submission.

Notifies Bing/Yandex/Seznam/Yep of newly updated URLs so they get crawled fast.
Key is served from /public/{KEY}.txt. Runs daily.

Only submits URLs that pass SEO quality gates (mirrors /api/sitemap-quality-pages
logic) to avoid burning our key reputation on thin-content pages.
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asyncpg
import requests

sys.path.insert(0, "/home/deploy/depscope")

HOST = "depscope.dev"
BASE_URL = f"https://{HOST}"
PUBLIC_DIR = Path("/home/deploy/depscope/frontend/public")
ENDPOINT = "https://api.indexnow.org/IndexNow"
DB_URL = os.environ.get("DATABASE_URL") or os.environ["DATABASE_URL"]

# SEO quality gates (same thresholds as api/main.py)
SEO_MIN_BREAKING = 3
SEO_MIN_BUGS = 3
SEO_MIN_DOWNLOADS = 1000
SEO_MIN_SOLUTION_LEN = 200
SEO_MIN_CONFIDENCE = 0.7

# IndexNow limits: 10,000 URLs per POST
BATCH_SIZE = 10_000


def find_key() -> str:
    """Locate the existing IndexNow key file in /public. Key == filename stem
    == file contents (by protocol). Returns the key or raises."""
    for f in PUBLIC_DIR.glob("*.txt"):
        stem = f.stem
        # IndexNow keys are 8-128 hex-ish chars. Skip obvious non-keys.
        if len(stem) < 8 or not stem.replace("-", "").isalnum():
            continue
        try:
            content = f.read_text().strip()
        except Exception:
            continue
        if content == stem:
            return stem
    raise RuntimeError(f"No IndexNow key file found in {PUBLIC_DIR}")


async def collect_urls(conn: asyncpg.Connection, since_hours: int) -> list[str]:
    since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    urls: list[str] = []

    # --- packages (recently updated, quality gate) -------------------------
    pkg_rows = await conn.fetch("""
        SELECT ecosystem, name
        FROM packages
        WHERE updated_at >= $1
          AND health_score IS NOT NULL
          AND health_score > 0
          AND downloads_weekly > $2
        ORDER BY downloads_weekly DESC NULLS LAST
        LIMIT 50000
    """, since, SEO_MIN_DOWNLOADS)
    for r in pkg_rows:
        urls.append(f"{BASE_URL}/pkg/{r['ecosystem']}/{r['name']}")

    # --- breaking changes --------------------------------------------------
    # breaking_changes has no updated_at column; use packages.updated_at as
    # a proxy (when the package row was last touched, its breaking page is
    # the freshest view we have).
    br_rows = await conn.fetch("""
        SELECT p.ecosystem, p.name, p.updated_at AS last_upd, COUNT(*) AS n
        FROM breaking_changes b
        JOIN packages p ON p.id = b.package_id
        WHERE p.updated_at >= $1
        GROUP BY p.id, p.ecosystem, p.name, p.updated_at
        HAVING COUNT(*) >= $2
    """, since, SEO_MIN_BREAKING)
    for r in br_rows:
        urls.append(f"{BASE_URL}/breaking/{r['ecosystem']}/{r['name']}")

    # --- known bugs --------------------------------------------------------
    bg_rows = await conn.fetch("""
        SELECT ecosystem, package_name, MAX(updated_at) AS last_upd, COUNT(*) AS n
        FROM known_bugs
        GROUP BY ecosystem, package_name
        HAVING COUNT(*) >= $1
    """, SEO_MIN_BUGS)
    for r in bg_rows:
        lu = r["last_upd"]
        if lu is None:
            continue
        if lu.tzinfo is None:
            lu = lu.replace(tzinfo=timezone.utc)
        if lu >= since:
            urls.append(f"{BASE_URL}/bugs/{r['ecosystem']}/{r['package_name']}")

    # --- error fingerprints ------------------------------------------------
    err_rows = await conn.fetch("""
        SELECT hash
        FROM errors
        WHERE updated_at >= $1
          AND LENGTH(solution) >= $2
          AND confidence >= $3
    """, since, SEO_MIN_SOLUTION_LEN, SEO_MIN_CONFIDENCE)
    for r in err_rows:
        urls.append(f"{BASE_URL}/errors/{r['hash']}")

    # Dedup + sort for deterministic output
    return sorted(set(urls))


def submit_batch(key: str, url_list: list[str]) -> dict:
    payload = {
        "host": HOST,
        "key": key,
        "keyLocation": f"{BASE_URL}/{key}.txt",
        "urlList": url_list,
    }
    try:
        r = requests.post(ENDPOINT, json=payload, timeout=60)
        return {"status": r.status_code, "body": r.text[:200], "n": len(url_list)}
    except Exception as e:
        return {"status": 0, "body": f"ERROR: {e}", "n": len(url_list)}


async def main():
    key = find_key()
    since_hours = int(os.environ.get("SINCE_HOURS", "24"))
    ts = datetime.now(timezone.utc).isoformat()

    conn = await asyncpg.connect(DB_URL)
    try:
        urls = await collect_urls(conn, since_hours)
    finally:
        await conn.close()

    print(f"[{ts}] IndexNow: {len(urls)} qualifying URLs, key={key}, since={since_hours}h")

    if not urls:
        print("  nothing to submit")
        return 0

    total_ok = 0
    for i in range(0, len(urls), BATCH_SIZE):
        batch = urls[i:i + BATCH_SIZE]
        res = submit_batch(key, batch)
        print(f"  batch {i // BATCH_SIZE + 1}: n={res['n']} status={res['status']} body={res['body']!r}")
        if 200 <= res["status"] < 300:
            total_ok += res["n"]
        await asyncio.sleep(1)

    print(f"[{datetime.now(timezone.utc).isoformat()}] submitted={total_ok}/{len(urls)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
