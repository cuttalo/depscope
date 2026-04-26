#!/usr/bin/env python3
"""Fetch closed bug-labeled GitHub issues from top 5 npm packages.

Populates the `known_bugs` table with data from GitHub Issues API.
Idempotent: uses ON CONFLICT DO NOTHING on (ecosystem, package_name, bug_id).

Usage:
    DATABASE_URL=<url> GH_TOKEN=<token> python3 scripts/ingest_known_bugs.py

Environment:
    DATABASE_URL: PostgreSQL connection string
    GH_TOKEN: GitHub personal access token (optional, increases rate limit)
"""
import asyncio
import os
import sys
import time
from typing import Optional

import aiohttp
import asyncpg

# Try to import DATABASE_URL from api.config, fallback to environment variable
try:
    sys.path.insert(0, "/home/deploy/depscope")
    from api.config import DATABASE_URL  # noqa: E402
except (ImportError, ModuleNotFoundError):
    # Fallback to environment variable for local testing
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in api.config or environment")
        sys.exit(1)


def get_github_token() -> Optional[str]:
    """Load GitHub token from env or config."""
    return os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")


def parse_github_repo(repo_url: Optional[str]) -> Optional[tuple[str, str]]:
    """Extract (owner, repo) from a GitHub URL."""
    if not repo_url:
        return None
    import re
    url = repo_url.strip()
    url = re.sub(r"^git\+", "", url)
    url = re.sub(r"^ssh://git@", "https://", url)
    url = re.sub(r"^git://", "https://", url)
    m = re.search(r"github\.com[/:]([^/]+)/([^/#?]+?)(?:\.git)?/?$", url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    return (owner, repo) if owner and repo else None


async def fetch_bug_issues(
    session: aiohttp.ClientSession,
    owner: str,
    repo: str,
    headers: dict,
    per_page: int = 10,
) -> list[dict]:
    """Fetch closed issues with 'bug' label from a GitHub repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    params = {
        "state": "closed",
        "labels": "bug",
        "per_page": per_page,
        "sort": "created",
        "direction": "desc",
    }
    try:
        async with session.get(
            url,
            headers=headers,
            params=params,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                if data and isinstance(data, list):
                    # Filter out pull requests
                    return [i for i in data if isinstance(i, dict) and not i.get("pull_request")]
            elif resp.status == 403:
                print(f"⚠️  Rate limit or forbidden for {owner}/{repo}")
            return []
    except Exception as e:
        print(f"⚠️  Fetch failed for {owner}/{repo}: {e}")
        return []


def pick_severity(labels: list) -> str:
    """Map GitHub labels to severity scale (critical/high/medium/low)."""
    label_text = " ".join(str(lab.get("name", "")) if isinstance(lab, dict) else str(lab) for lab in labels).lower()
    if any(k in label_text for k in ("critical", "p0", "security", "crash")):
        return "critical"
    if any(k in label_text for k in ("high", "p1", "major")):
        return "high"
    if any(k in label_text for k in ("low", "p3", "minor", "trivial")):
        return "low"
    return "medium"


async def insert_bug(
    conn: asyncpg.Connection,
    pkg_id: int,
    ecosystem: str,
    pkg_name: str,
    issue: dict,
) -> bool:
    """Insert a single bug into known_bugs table. Returns True if inserted."""
    try:
        number = issue.get("number")
        title = (issue.get("title") or "").strip()
        body = (issue.get("body") or "")[:500]  # First 500 chars
        html_url = issue.get("html_url") or ""
        closed_at = issue.get("closed_at")

        if not title or not number:
            return False

        # Extract labels
        labels_raw = issue.get("labels") or []
        labels = [
            lab.get("name") if isinstance(lab, dict) else str(lab)
            for lab in labels_raw
        ]

        bug_id = f"github:{number}"
        status = "fixed" if issue.get("state") == "closed" else "open"
        severity = pick_severity(labels_raw)

        result = await conn.execute(
            """
            INSERT INTO known_bugs(
                package_id, ecosystem, package_name,
                affected_version, fixed_version, bug_id,
                title, description, severity, status,
                source, source_url, labels
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            ON CONFLICT (ecosystem, package_name, bug_id) DO NOTHING
            """,
            pkg_id,
            ecosystem,
            pkg_name,
            None,  # affected_version (not parsed from issue)
            None,  # fixed_version (not parsed from issue)
            bug_id,
            title[:2000],
            body or None,
            severity,
            status,
            "github_issues",
            html_url,
            labels[:20],  # Limit to 20 labels
        )
        # asyncpg returns "INSERT 0 1" on success, "INSERT 0 0" on conflict
        return result and result.endswith("1")
    except Exception as e:
        print(f"⚠️  Insert failed for {pkg_name} issue #{issue.get('number')}: {e}")
        return False


async def main() -> dict:
    """Main ingestion routine."""
    start_time = time.time()

    # Connect to database
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)

    try:
        # Setup GitHub API headers
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "depscope-ingest/1.0",
        }
        gh_token = get_github_token()
        if gh_token:
            headers["Authorization"] = f"Bearer {gh_token}"
            print("✓ Using authenticated GitHub token")
        else:
            print("⚠️  No GitHub token — unauthenticated (60 req/hour limit)")

        # Fetch top 5 npm packages by weekly downloads
        async with pool.acquire() as conn:
            packages = await conn.fetch(
                """
                SELECT id, name, repository, downloads_weekly
                FROM packages
                WHERE ecosystem = 'npm'
                  AND downloads_weekly > 100000000
                  AND repository IS NOT NULL
                  AND repository ILIKE '%github.com%'
                ORDER BY downloads_weekly DESC
                LIMIT 5
                """
            )

        if not packages:
            print("⚠️  No packages found matching criteria")
            return {
                "status": "failed",
                "error": "No packages found",
                "bugs_ingested": 0,
                "packages_processed": 0,
            }

        print(f"\n📦 Processing {len(packages)} top npm packages:\n")
        for pkg in packages:
            print(f"  • {pkg['name']}")
        print()

        bugs_ingested = 0
        packages_processed = 0
        errors = 0

        # Process each package
        async with aiohttp.ClientSession() as session:
            for pkg in packages:
                repo_parsed = parse_github_repo(pkg["repository"])
                if not repo_parsed:
                    print(f"⚠️  Skipping {pkg['name']}: invalid repo URL")
                    errors += 1
                    continue

                owner, repo = repo_parsed
                print(f"🔍 Fetching bugs from {owner}/{repo} ({pkg['name']})...")

                issues = await fetch_bug_issues(session, owner, repo, headers)

                if not issues:
                    print(f"  ℹ️  No closed bug issues found")
                    packages_processed += 1
                    continue

                # Insert each issue
                inserted = 0
                async with pool.acquire() as conn:
                    for issue in issues:
                        if await insert_bug(conn, pkg["id"], "npm", pkg["name"], issue):
                            inserted += 1

                bugs_ingested += inserted
                packages_processed += 1
                print(f"  ✓ Inserted {inserted}/{len(issues)} bugs\n")

        elapsed = time.time() - start_time

        print(f"\n{'='*60}")
        print(f"BUGS_INGESTED={bugs_ingested}  PACKAGES_PROCESSED={packages_processed}  ERRORS={errors}")
        print(f"Completed in {elapsed:.1f}s")
        print(f"{'='*60}\n")

        return {
            "status": "success",
            "bugs_ingested": bugs_ingested,
            "packages_processed": packages_processed,
            "errors": errors,
            "elapsed_seconds": round(elapsed, 1),
        }

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "failed",
            "error": str(e),
            "bugs_ingested": 0,
            "packages_processed": 0,
        }

    finally:
        await pool.close()


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result["status"] == "success" else 1)
