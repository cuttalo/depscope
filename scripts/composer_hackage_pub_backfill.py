#!/usr/bin/env python3
"""Backfill Composer (packagist), Hackage, Pub (dart) metadata.

- Packagist: https://repo.packagist.org/p2/<vendor>/<name>.json → versions[].homepage/source/dist
- Hackage: https://hackage.haskell.org/package/<name>/<name>.cabal (text cabal) or JSON from /src
  Easier: https://hackage.haskell.org/package/<name>.json → Homepage, BugReports, SourceRepository
  Actually use: https://hackage.haskell.org/package/<name> HTML scrape, or the cabal file.
  Best: just use the package URL https://hackage.haskell.org/package/<name> as repo fallback.
- Pub: https://pub.dev/api/packages/<name> → latest.pubspec.homepage/repository/issue_tracker
"""
import asyncio
import json
import re
import sys
sys.path.insert(0, "/home/deploy/depscope")

import aiohttp
from api.database import get_pool

HEADERS = {"Accept": "application/json", "User-Agent": "DepScope/0.1 (https://depscope.dev)"}


async def fetch_packagist(session, name):
    if "/" not in name:
        return None
    try:
        async with session.get(
            f"https://repo.packagist.org/p2/{name}.json",
            headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            if r.status != 200:
                return None
            return await r.json()
    except Exception:
        return None


async def fetch_pub(session, name):
    try:
        async with session.get(
            f"https://pub.dev/api/packages/{name}",
            headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            if r.status != 200:
                return None
            return await r.json()
    except Exception:
        return None


async def fetch_hackage_cabal(session, name):
    """Get cabal file text, parse homepage/source-repository."""
    try:
        async with session.get(
            f"https://hackage.haskell.org/package/{name}/{name}.cabal",
            headers={"User-Agent": HEADERS["User-Agent"]},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            if r.status != 200:
                return None
            return await r.text()
    except Exception:
        return None


def parse_cabal(text):
    """Extract homepage + source-repository location from .cabal."""
    if not text:
        return {}
    out = {}
    # homepage: single-line "homepage: ..."
    m = re.search(r"^\s*homepage\s*:\s*(\S.+)$", text, re.IGNORECASE | re.MULTILINE)
    if m:
        out["homepage"] = m.group(1).strip()
    # source-repository head { location: ... }
    m = re.search(r"source-repository[^\n]*\n(?:\s+[^\n]+\n)*?\s*location\s*:\s*(\S+)", text, re.IGNORECASE)
    if m:
        out["repository"] = m.group(1).strip()
    return out


async def main():
    pool = await get_pool()
    async with pool.acquire() as conn:
        composer_rows = await conn.fetch(
            """SELECT id, name, homepage, repository FROM packages
               WHERE ecosystem='composer'
                 AND (homepage = '' OR homepage IS NULL)"""
        )
        hackage_rows = await conn.fetch(
            """SELECT id, name, homepage, repository FROM packages
               WHERE ecosystem='hackage'
                 AND (repository = '' OR repository IS NULL)"""
        )
        pub_rows = await conn.fetch(
            """SELECT id, name, homepage, repository FROM packages
               WHERE ecosystem='pub'
                 AND (repository = '' OR repository IS NULL)"""
        )
    print(f"composer: {len(composer_rows)}, hackage: {len(hackage_rows)}, pub: {len(pub_rows)}", flush=True)

    sem = asyncio.Semaphore(10)
    stats = {"composer_ok": 0, "composer_miss": 0, "hackage_ok": 0, "hackage_miss": 0, "pub_ok": 0, "pub_miss": 0}

    async with aiohttp.ClientSession() as session:
        async def do_composer(p):
            async with sem:
                data = await fetch_packagist(session, p["name"])
                if not data:
                    stats["composer_miss"] += 1
                    return
                pkgs = (data.get("packages") or {}).get(p["name"]) or []
                if not pkgs:
                    stats["composer_miss"] += 1
                    return
                # pkgs[0] is latest
                latest = pkgs[0] if isinstance(pkgs, list) and pkgs else {}
                homepage = (latest.get("homepage") or "").strip()
                source = ((latest.get("source") or {}).get("url") or "").strip()
                repo = source if source and "github.com" in source else ""
                sets, args = [], [p["id"]]
                if homepage and not p["homepage"]:
                    args.append(homepage[:2000]); sets.append(f"homepage=${len(args)}")
                if repo and not p["repository"]:
                    args.append(repo[:2000]); sets.append(f"repository=${len(args)}")
                if not sets:
                    stats["composer_miss"] += 1
                    return
                async with pool.acquire() as conn:
                    await conn.execute(
                        f"UPDATE packages SET {', '.join(sets)}, updated_at=NOW() WHERE id=$1", *args,
                    )
                stats["composer_ok"] += 1

        async def do_hackage(p):
            async with sem:
                cabal = await fetch_hackage_cabal(session, p["name"])
                meta = parse_cabal(cabal)
                repo = meta.get("repository") or f"https://hackage.haskell.org/package/{p['name']}"
                homepage = meta.get("homepage") or p["homepage"]
                sets, args = [], [p["id"]]
                if repo and not p["repository"]:
                    args.append(repo[:2000]); sets.append(f"repository=${len(args)}")
                if homepage and homepage != p["homepage"] and not p["homepage"]:
                    args.append(homepage[:2000]); sets.append(f"homepage=${len(args)}")
                if not sets:
                    stats["hackage_miss"] += 1
                    return
                async with pool.acquire() as conn:
                    await conn.execute(
                        f"UPDATE packages SET {', '.join(sets)}, updated_at=NOW() WHERE id=$1", *args,
                    )
                stats["hackage_ok"] += 1

        async def do_pub(p):
            async with sem:
                data = await fetch_pub(session, p["name"])
                if not data:
                    stats["pub_miss"] += 1
                    return
                ps = ((data.get("latest") or {}).get("pubspec") or {})
                repo = (ps.get("repository") or "").strip()
                homepage = (ps.get("homepage") or "").strip()
                issue_tracker = (ps.get("issue_tracker") or "").strip()
                # If no repository, derive from issue_tracker or homepage (if github)
                if not repo:
                    for src in (issue_tracker, homepage):
                        if src and "github.com" in src:
                            repo = src.rstrip("/")
                            # strip /issues suffix if present
                            repo = re.sub(r"/issues/?$", "", repo)
                            break
                if not repo:
                    repo = f"https://pub.dev/packages/{p['name']}"
                sets, args = [], [p["id"]]
                if repo and not p["repository"]:
                    args.append(repo[:2000]); sets.append(f"repository=${len(args)}")
                if homepage and not p["homepage"]:
                    args.append(homepage[:2000]); sets.append(f"homepage=${len(args)}")
                if not sets:
                    stats["pub_miss"] += 1
                    return
                async with pool.acquire() as conn:
                    await conn.execute(
                        f"UPDATE packages SET {', '.join(sets)}, updated_at=NOW() WHERE id=$1", *args,
                    )
                stats["pub_ok"] += 1

        await asyncio.gather(
            *[do_composer(p) for p in composer_rows],
            *[do_hackage(p) for p in hackage_rows],
            *[do_pub(p) for p in pub_rows],
        )

    print(f"DONE {stats}", flush=True)


asyncio.run(main())
