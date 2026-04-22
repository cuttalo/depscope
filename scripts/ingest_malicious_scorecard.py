import os
"""Ingest:
1. OpenSSF Malicious Packages — https://github.com/ossf/malicious-packages (via OSV export)
   Each record is an OSV format with ecosystem/package/version_ranges + malicious flag.
2. OSS Scorecard — api.securityscorecards.dev fetch on-demand for top repos
"""
import asyncio, asyncpg, aiohttp, json, sys, os, tempfile, zipfile, io
from datetime import datetime, timezone

DB_URL = os.environ["DATABASE_URL"]
# OpenSSF publishes malicious packages through OSV's malicious-packages dataset
OSV_BUCKET_BASE = "https://osv-vulnerabilities.storage.googleapis.com"
# OpenSSF Malicious is under multiple ecosystem prefixes via OSV. We use the dedicated repo instead:
OSSF_ALL_JSON = "https://raw.githubusercontent.com/ossf/malicious-packages/main/osv/all.json"


async def ingest_malicious(conn, session):
    print("[mal] fetching OpenSSF Malicious Packages …")
    async with session.get(OSSF_ALL_JSON, timeout=aiohttp.ClientTimeout(total=60)) as r:
        if r.status != 200:
            # Fallback: enumerate with JSON dump endpoints
            print(f"[mal] {OSSF_ALL_JSON} HTTP {r.status}, trying per-ecosystem…")
            return await ingest_malicious_per_eco(conn, session)
        try:
            data = await r.json(content_type=None)
        except Exception as e:
            print(f"[mal] JSON parse failed: {e}")
            return 0
    # all.json is a list of OSV records
    if not isinstance(data, list):
        print(f"[mal] unexpected structure: {type(data)}")
        return 0
    print(f"[mal] got {len(data)} entries")
    n = 0
    for entry in data:
        if entry.get("withdrawn"):
            continue
        affected = entry.get("affected") or []
        for aff in affected:
            pkg = aff.get("package") or {}
            eco = (pkg.get("ecosystem") or "").lower()
            name = pkg.get("name")
            if not name or not eco:
                continue
            # Normalize ecosystem names: OSV uses 'npm', 'PyPI', 'crates.io', 'Go', ...
            eco_norm = {
                "pypi": "pypi", "npm": "npm", "crates.io": "cargo", "go": "go",
                "maven": "maven", "nuget": "nuget", "rubygems": "rubygems",
                "packagist": "composer", "pub": "pub", "hex": "hex",
                "swift": "swift", "cocoapods": "cocoapods", "cpan": "cpan",
                "hackage": "hackage", "cran": "cran", "conda": "conda", "homebrew": "homebrew",
            }.get(eco, eco)
            summary = entry.get("summary") or entry.get("details", "")[:500]
            published = entry.get("published") or entry.get("modified")
            try:
                pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00")) if published else None
            except Exception:
                pub_dt = None
            try:
                await conn.execute("""
                    INSERT INTO malicious_packages
                      (ecosystem, package_name, vuln_id, published_at, summary, source, data_json, updated_at)
                    VALUES ($1,$2,$3,$4,$5,'openssf',$6::jsonb,NOW())
                    ON CONFLICT (ecosystem, package_name) DO UPDATE SET
                      vuln_id=EXCLUDED.vuln_id, published_at=EXCLUDED.published_at,
                      summary=EXCLUDED.summary, data_json=EXCLUDED.data_json, updated_at=NOW()
                """, eco_norm, name, entry.get("id"), pub_dt, summary, json.dumps(entry))
                n += 1
            except Exception:
                pass
    print(f"[mal] upserted {n}")
    return n


async def ingest_malicious_per_eco(conn, session):
    """Fallback: fetch OSV all.zip per ecosystem and filter for MAL- IDs."""
    ecos = [("PyPI", "pypi"), ("npm", "npm"), ("crates.io", "cargo"),
            ("RubyGems", "rubygems"), ("Packagist", "composer"), ("Maven", "maven"),
            ("NuGet", "nuget"), ("Go", "go"), ("Pub", "pub"), ("Hex", "hex")]
    n_total = 0
    for osv_eco, our_eco in ecos:
        url = f"{OSV_BUCKET_BASE}/{osv_eco}/all.zip"
        print(f"[mal] fetching {url}")
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as r:
                if r.status != 200:
                    continue
                raw = await r.read()
        except Exception as e:
            print(f"[mal]  err: {e}")
            continue
        zf = zipfile.ZipFile(io.BytesIO(raw))
        n_eco = 0
        for name in zf.namelist():
            if not name.endswith(".json"):
                continue
            try:
                entry = json.loads(zf.read(name))
            except Exception:
                continue
            # Only canonical OpenSSF malicious-packages entries (MAL-*).
            # Keyword match on "malicious" in summary caused massive false positives
            # (e.g., "vulnerable to X via malicious URL" on mainstream packages).
            if not entry.get("id", "").startswith("MAL-"):
                continue
            if entry.get("withdrawn"):
                continue
            for aff in (entry.get("affected") or []):
                pkg = aff.get("package") or {}
                pname = pkg.get("name")
                if not pname:
                    continue
                summary = entry.get("summary") or entry.get("details", "")[:500]
                published = entry.get("published") or entry.get("modified")
                try:
                    pub_dt = datetime.fromisoformat(published.replace("Z","+00:00")) if published else None
                except Exception:
                    pub_dt = None
                try:
                    await conn.execute("""
                        INSERT INTO malicious_packages
                          (ecosystem, package_name, vuln_id, published_at, summary, source, data_json, updated_at)
                        VALUES ($1,$2,$3,$4,$5,'osv',$6::jsonb,NOW())
                        ON CONFLICT (ecosystem, package_name) DO UPDATE SET
                          vuln_id=EXCLUDED.vuln_id, published_at=EXCLUDED.published_at,
                          summary=EXCLUDED.summary, data_json=EXCLUDED.data_json, updated_at=NOW()
                    """, our_eco, pname, entry.get("id"), pub_dt, summary, json.dumps(entry))
                    n_eco += 1
                except Exception:
                    pass
        print(f"[mal] {osv_eco}: {n_eco} malicious entries")
        n_total += n_eco
    print(f"[mal] fallback total: {n_total}")
    return n_total


async def ingest_scorecards(conn, session, limit_per_eco=200):
    """Fetch OSS Scorecard scores on-demand for top repos we track."""
    # Get unique repos from maintainer_signals (most tracked set)
    rows = await conn.fetch("""
        SELECT DISTINCT repo_owner, repo_name
        FROM maintainer_signals
        WHERE repo_owner IS NOT NULL AND repo_name IS NOT NULL
        LIMIT $1
    """, limit_per_eco * 10)
    print(f"[scorecard] checking {len(rows)} repos")
    n = 0
    for r in rows:
        platform_url = f"github.com/{r['repo_owner']}/{r['repo_name']}"
        api_url = f"https://api.securityscorecards.dev/projects/{platform_url}"
        try:
            async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    continue
                data = await resp.json()
        except Exception:
            continue
        score = data.get("score")
        if score is None:
            continue
        sd = data.get("date") or data.get("scorecard", {}).get("date")
        try:
            from datetime import date as _D
            date_val = _D.fromisoformat(sd[:10]) if sd else None
        except Exception:
            date_val = None
        checks = {c.get("name"): {"score": c.get("score"), "reason": c.get("reason")}
                  for c in data.get("checks", []) if c.get("name")}
        try:
            await conn.execute("""
                INSERT INTO scorecard_scores(repo_url, score, checks_json, scorecard_date, updated_at)
                VALUES ($1,$2,$3::jsonb,$4,NOW())
                ON CONFLICT (repo_url) DO UPDATE SET
                  score=EXCLUDED.score, checks_json=EXCLUDED.checks_json,
                  scorecard_date=EXCLUDED.scorecard_date, updated_at=NOW()
            """, platform_url, float(score), json.dumps(checks), date_val)
            n += 1
        except Exception as e:
            pass
        if n % 50 == 0 and n > 0:
            print(f"[scorecard] {n} stored…")
    print(f"[scorecard] total stored: {n}")
    return n


async def main():
    conn = await asyncpg.connect(DB_URL)
    async with aiohttp.ClientSession(headers={"User-Agent": "DepScope/1.0"}) as s:
        try:
            await ingest_malicious(conn, s)
        except Exception as e:
            print(f"[mal] ERROR {e}")
        try:
            await ingest_scorecards(conn, s, limit_per_eco=100)
        except Exception as e:
            print(f"[scorecard] ERROR {e}")
    mal = await conn.fetchval("SELECT COUNT(*) FROM malicious_packages")
    sc = await conn.fetchval("SELECT COUNT(*) FROM scorecard_scores")
    avg_sc = await conn.fetchval("SELECT AVG(score) FROM scorecard_scores")
    print(f"[done] malicious={mal}, scorecard={sc} (avg={avg_sc})")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
