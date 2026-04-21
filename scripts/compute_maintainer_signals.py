import os
"""Compute maintainer trust signals for top packages.
GitHub API rate limit: 5000/hour with token. We budget per run (top 500 cumulative).
"""
import asyncio, asyncpg, aiohttp, re, os, sys
from datetime import datetime, timezone, timedelta

DB_URL = os.environ["DATABASE_URL"]
GH_TOKEN = os.environ.get("GH_TOKEN", "")
GH_API = "https://api.github.com"
PER_ECOSYSTEM_LIMIT = int(os.environ.get("PER_ECO", "50"))  # keep modest for a single run

GH_PAT = re.compile(r"github\.com[/:]([^/]+)/([^/#?.\s]+?)(?:\.git)?/?$")


def extract_owner_repo(repo_url: str):
    if not repo_url:
        return None, None
    m = GH_PAT.search(repo_url.strip())
    if not m:
        return None, None
    return m.group(1), m.group(2)


async def gh(session, path, **kwargs):
    async with session.get(
        f"{GH_API}{path}",
        headers={"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json",
                 "User-Agent": "DepScope/1.0"},
        params=kwargs or None,
        timeout=aiohttp.ClientTimeout(total=15),
    ) as r:
        if r.status == 200:
            return await r.json()
        if r.status == 404:
            return None
        if r.status == 403:
            rl = r.headers.get("X-RateLimit-Remaining", "?")
            print(f"  [403] rate-limit remaining={rl}")
        return None


async def signals_for(session, owner, repo):
    info = await gh(session, f"/repos/{owner}/{repo}")
    if not info:
        return None
    repo_created = info.get("created_at")
    repo_pushed = info.get("pushed_at")
    stars = info.get("stargazers_count", 0)
    forks = info.get("forks_count", 0)
    issues = info.get("open_issues_count", 0)
    archived = info.get("archived", False)

    # Commits last 90 days
    since_90 = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    commits_90 = await gh(session, f"/repos/{owner}/{repo}/commits", since=since_90, per_page=100) or []
    authors_90 = set()
    for c in commits_90:
        a = (c.get("author") or {}).get("login") or (c.get("commit") or {}).get("author", {}).get("email")
        if a: authors_90.add(a)
    bus_factor = len(authors_90) or 1

    # Commits last 365 days
    since_365 = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
    commits_365 = await gh(session, f"/repos/{owner}/{repo}/commits", since=since_365, per_page=100) or []
    authors_365 = {}
    for c in commits_365:
        a = (c.get("author") or {}).get("login") or (c.get("commit") or {}).get("author", {}).get("email")
        if a:
            authors_365[a] = authors_365.get(a, 0) + 1
    if authors_365:
        primary_author, primary_count = max(authors_365.items(), key=lambda kv: kv[1])
        primary_ratio = primary_count / sum(authors_365.values())
    else:
        primary_author, primary_ratio = None, 0.0

    # Owner account age
    owner_info = await gh(session, f"/users/{owner}") or await gh(session, f"/orgs/{owner}")
    owner_age_days = None
    if owner_info and owner_info.get("created_at"):
        dt = datetime.fromisoformat(owner_info["created_at"].replace("Z","+00:00"))
        owner_age_days = (datetime.now(timezone.utc) - dt).days

    # Recent ownership transfer (simplified): repo_created vs repo first commit
    # We approximate via "updated_at < 180 days ago and name_with_owner differs from canonical URL"
    # Easier proxy: rename/transfer surfaces as a 301 on the old URL; skip heavy check, mark None.
    recent_transfer = False
    # crude: if account age < repo age/2 (rare but signal)
    if owner_age_days and repo_created:
        rc = datetime.fromisoformat(repo_created.replace("Z","+00:00"))
        repo_age_days = (datetime.now(timezone.utc) - rc).days
        if owner_age_days * 2 < repo_age_days:
            recent_transfer = True

    return {
        "repo_created_at": repo_created,
        "repo_pushed_at": repo_pushed,
        "bus_factor_3m": bus_factor,
        "active_contributors_12m": len(authors_365),
        "primary_author": primary_author,
        "primary_author_ratio": primary_ratio,
        "owner_account_age_days": owner_age_days,
        "recent_ownership_change": recent_transfer,
        "is_archived": archived,
        "stars": stars,
        "forks": forks,
        "open_issues": issues,
    }


async def main():
    conn = await asyncpg.connect(DB_URL)
    total = 0
    async with aiohttp.ClientSession() as session:
        ecos = await conn.fetch("SELECT DISTINCT ecosystem FROM packages WHERE repository IS NOT NULL AND repository ILIKE '%github.com%'")
        for eco_row in ecos:
            eco = eco_row["ecosystem"]
            pkgs = await conn.fetch("""
                SELECT name, repository FROM packages
                WHERE ecosystem=$1 AND repository IS NOT NULL AND repository ILIKE '%github.com%'
                ORDER BY downloads_weekly DESC NULLS LAST
                LIMIT $2
            """, eco, PER_ECOSYSTEM_LIMIT)
            eco_count = 0
            for p in pkgs:
                owner, repo = extract_owner_repo(p["repository"])
                if not owner or not repo:
                    continue
                s = await signals_for(session, owner, repo)
                if not s:
                    continue
                import json as J
                await conn.execute("""
                    INSERT INTO maintainer_signals
                      (ecosystem, package_name, repo_owner, repo_name,
                       repo_created_at, repo_pushed_at,
                       bus_factor_3m, active_contributors_12m,
                       primary_author, primary_author_ratio, owner_account_age_days,
                       recent_ownership_change, is_archived, stars, forks, open_issues, data_json, updated_at)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,NOW())
                    ON CONFLICT (ecosystem, package_name) DO UPDATE SET
                      repo_owner=EXCLUDED.repo_owner, repo_name=EXCLUDED.repo_name,
                      repo_created_at=EXCLUDED.repo_created_at, repo_pushed_at=EXCLUDED.repo_pushed_at,
                      bus_factor_3m=EXCLUDED.bus_factor_3m, active_contributors_12m=EXCLUDED.active_contributors_12m,
                      primary_author=EXCLUDED.primary_author, primary_author_ratio=EXCLUDED.primary_author_ratio,
                      owner_account_age_days=EXCLUDED.owner_account_age_days,
                      recent_ownership_change=EXCLUDED.recent_ownership_change,
                      is_archived=EXCLUDED.is_archived, stars=EXCLUDED.stars, forks=EXCLUDED.forks,
                      open_issues=EXCLUDED.open_issues, data_json=EXCLUDED.data_json, updated_at=NOW()
                """,
                    eco, p["name"], owner, repo,
                    datetime.fromisoformat(s["repo_created_at"].replace("Z","+00:00")) if s.get("repo_created_at") else None,
                    datetime.fromisoformat(s["repo_pushed_at"].replace("Z","+00:00")) if s.get("repo_pushed_at") else None,
                    s["bus_factor_3m"], s["active_contributors_12m"],
                    s["primary_author"], s["primary_author_ratio"], s["owner_account_age_days"],
                    s["recent_ownership_change"], s["is_archived"], s["stars"], s["forks"], s["open_issues"],
                    J.dumps({"raw": None})
                )
                eco_count += 1
                total += 1
            print(f"[{eco}] computed {eco_count} / {len(pkgs)}")
    print(f"TOTAL maintainer_signals: {total}")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
