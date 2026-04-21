import os
"""Ingest OSS Criticality Score + download velocity + npm 2FA (signed) + PyPI Trusted Publishing."""
import asyncio, asyncpg, aiohttp, json, csv, io, gzip
from datetime import date, datetime, timezone, timedelta

DB_URL = os.environ["DATABASE_URL"]

SYSTEM_MAP = {"npm":"NPM","pypi":"PYPI","cargo":"CARGO","go":"GO","nuget":"NUGET","rubygems":"RUBYGEMS","maven":"MAVEN"}


async def ingest_criticality(conn, session, limit=1500):
    """Use deps.dev projectInsight to derive OSSF criticality-like score, fall back to synthetic."""
    rows = await conn.fetch("""
        SELECT ecosystem, name, downloads_weekly, maintainers_count, first_published
        FROM packages
        WHERE downloads_weekly > 500
        ORDER BY downloads_weekly DESC LIMIT $1
    """, limit)
    print(f"[crit] computing for {len(rows)} packages")
    import math
    n = 0
    for r in rows:
        sys_name = SYSTEM_MAP.get(r["ecosystem"])
        score = None
        # Try deps.dev
        if sys_name:
            try:
                url = f"https://api.deps.dev/v3alpha/systems/{sys_name}/packages/{r['name']}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                    if resp.status == 200:
                        d = await resp.json()
                        # projectInsights gives scorecard & other signals
                        ins = (d.get("projectInsights") or [{}])[0] if d.get("projectInsights") else {}
                        sc = (ins.get("scorecard") or {}).get("overallScore")
                        if sc is not None:
                            score = float(sc) / 10.0
            except Exception:
                pass
        # Synthetic fallback: log(downloads) * contrib
        if score is None:
            dl = r["downloads_weekly"] or 0
            mc = r["maintainers_count"] or 1
            age_days = 0
            if r["first_published"]:
                age_days = max(0, (datetime.now(timezone.utc) - r["first_published"].replace(tzinfo=timezone.utc) if r["first_published"].tzinfo is None else datetime.now(timezone.utc) - r["first_published"]).days)
            score_dl = min(1.0, math.log10(dl + 1) / 8.0)
            score_m = min(1.0, mc / 10.0)
            score_age = min(1.0, age_days / 1825.0)
            score = round(score_dl * 0.5 + score_m * 0.25 + score_age * 0.25, 3)
        try:
            await conn.execute("""
                INSERT INTO package_quality(ecosystem, package_name, criticality_score, criticality_date, last_checked)
                VALUES ($1,$2,$3,CURRENT_DATE,NOW())
                ON CONFLICT (ecosystem, package_name) DO UPDATE SET
                  criticality_score=EXCLUDED.criticality_score,
                  criticality_date=EXCLUDED.criticality_date,
                  last_checked=NOW()
            """, r["ecosystem"], r["name"], score)
            n += 1
        except Exception:
            pass
        if n % 200 == 0 and n > 0:
            print(f"[crit]   {n}…")
    print(f"[crit] total: {n}")
    return n


async def ingest_velocity(conn, session):
    """Track weekly downloads snapshot + compute velocity vs 4-week avg."""
    rows = await conn.fetch("""
        SELECT ecosystem, name, downloads_weekly
        FROM packages
        WHERE downloads_weekly > 100
        ORDER BY downloads_weekly DESC
        LIMIT 3000
    """)
    today = date.today()
    # Snapshot today
    n_snap = 0
    for r in rows:
        if not r["downloads_weekly"]:
            continue
        try:
            await conn.execute("""
                INSERT INTO download_history(ecosystem, package_name, week_date, downloads)
                VALUES ($1,$2,$3,$4)
                ON CONFLICT (ecosystem, package_name, week_date) DO UPDATE SET downloads=EXCLUDED.downloads
            """, r["ecosystem"], r["name"], today, r["downloads_weekly"])
            n_snap += 1
        except Exception:
            pass
    print(f"[vel] snapshot: {n_snap}")
    # Compute velocity: current vs prior 4 weeks avg
    n_vel = 0
    for r in rows:
        hist = await conn.fetch("""
            SELECT downloads FROM download_history
            WHERE ecosystem=$1 AND package_name=$2 AND week_date < $3 AND week_date >= $3 - INTERVAL '35 days'
            ORDER BY week_date DESC LIMIT 4
        """, r["ecosystem"], r["name"], today)
        if len(hist) < 1:
            # No history yet: just store 4w_avg = current
            avg = r["downloads_weekly"]
            vel = 0.0
        else:
            vals = [h["downloads"] for h in hist]
            avg = int(sum(vals) / len(vals))
            if avg > 0:
                vel = (r["downloads_weekly"] - avg) / avg * 100.0
            else:
                vel = 0.0
        try:
            await conn.execute("""
                INSERT INTO package_quality(ecosystem, package_name, downloads_4w_avg, velocity_pct, last_checked)
                VALUES ($1,$2,$3,$4,NOW())
                ON CONFLICT (ecosystem, package_name) DO UPDATE SET
                  downloads_4w_avg=EXCLUDED.downloads_4w_avg,
                  velocity_pct=EXCLUDED.velocity_pct,
                  last_checked=NOW()
            """, r["ecosystem"], r["name"], avg, vel)
            n_vel += 1
        except Exception:
            pass
    print(f"[vel] velocity computed: {n_vel}")
    return n_vel


async def ingest_npm_signed(conn, session, limit=800):
    """Check npm packument for dist.signatures (signed publishes require 2FA publish token)."""
    rows = await conn.fetch("""
        SELECT name FROM packages
        WHERE ecosystem='npm' AND downloads_weekly > 1000
        ORDER BY downloads_weekly DESC LIMIT $1
    """, limit)
    print(f"[npm-2fa] checking {len(rows)} packages")
    n = 0
    for r in rows:
        pkg = r["name"]
        try:
            async with session.get(f"https://registry.npmjs.org/{pkg}", timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    continue
                data = await resp.json()
        except Exception:
            continue
        # Check latest dist.signatures
        latest_ver = (data.get("dist-tags") or {}).get("latest")
        if not latest_ver:
            continue
        latest = (data.get("versions") or {}).get(latest_ver) or {}
        dist = latest.get("dist") or {}
        signatures = dist.get("signatures") or []
        has_attestations = bool(dist.get("attestations"))
        if signatures or has_attestations:
            sec = "signed" if signatures else "attested"
            detail = f"latest {latest_ver}: {len(signatures)} sig{'s' if len(signatures)!=1 else ''}"
            if has_attestations:
                detail += " +provenance"
        else:
            sec = "unsigned"
            detail = f"latest {latest_ver}: no signatures"
        try:
            await conn.execute("""
                INSERT INTO package_quality(ecosystem, package_name, publish_security, publish_detail, last_checked)
                VALUES ('npm',$1,$2,$3,NOW())
                ON CONFLICT (ecosystem, package_name) DO UPDATE SET
                  publish_security=EXCLUDED.publish_security,
                  publish_detail=EXCLUDED.publish_detail,
                  last_checked=NOW()
            """, pkg, sec, detail)
            n += 1
        except Exception:
            pass
        if n % 100 == 0 and n > 0:
            print(f"[npm-2fa]   {n}…")
    print(f"[npm-2fa] stored: {n}")
    return n


async def ingest_pypi_trusted(conn, session, limit=600):
    """Check PyPI attestations (Trusted Publishing via OIDC)."""
    rows = await conn.fetch("""
        SELECT name FROM packages
        WHERE ecosystem='pypi' AND downloads_weekly > 1000
        ORDER BY downloads_weekly DESC LIMIT $1
    """, limit)
    print(f"[pypi-tp] checking {len(rows)} packages")
    n = 0
    for r in rows:
        pkg = r["name"]
        try:
            async with session.get(f"https://pypi.org/pypi/{pkg}/json", timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    continue
                data = await resp.json()
        except Exception:
            continue
        urls = data.get("urls") or []
        if not urls:
            continue
        # Check for any url with "attestations" (PEP 740) or provenance URLs
        has_attestations = any(u.get("attestations") or u.get("provenance") for u in urls)
        # Fallback heuristic: check if uploaded_via contains "github-actions" or "trusted-publisher"
        uploader = None
        for u in urls:
            up = (u.get("uploaded_via_metadata") or {}).get("uploaded_via") or u.get("uploader")
            if up:
                uploader = up
                break
        if has_attestations:
            sec = "trusted"
            detail = "PEP 740 attestations present"
        elif uploader and ("trusted" in (uploader or "").lower() or "github" in (uploader or "").lower()):
            sec = "likely_trusted"
            detail = f"uploader: {uploader}"
        else:
            sec = "api_token"
            detail = "no attestations on latest release"
        try:
            await conn.execute("""
                INSERT INTO package_quality(ecosystem, package_name, publish_security, publish_detail, last_checked)
                VALUES ('pypi',$1,$2,$3,NOW())
                ON CONFLICT (ecosystem, package_name) DO UPDATE SET
                  publish_security=EXCLUDED.publish_security,
                  publish_detail=EXCLUDED.publish_detail,
                  last_checked=NOW()
            """, pkg, sec, detail)
            n += 1
        except Exception:
            pass
        if n % 100 == 0 and n > 0:
            print(f"[pypi-tp]   {n}…")
    print(f"[pypi-tp] stored: {n}")
    return n


async def main():
    conn = await asyncpg.connect(DB_URL)
    async with aiohttp.ClientSession(headers={"User-Agent": "DepScope/1.0"}) as s:
        try:
            await ingest_criticality(conn, s)
        except Exception as e:
            print(f"[crit] FAIL {e}")
        try:
            await ingest_velocity(conn, s)
        except Exception as e:
            print(f"[vel] FAIL {e}")
        try:
            await ingest_npm_signed(conn, s)
        except Exception as e:
            print(f"[npm-2fa] FAIL {e}")
        try:
            await ingest_pypi_trusted(conn, s)
        except Exception as e:
            print(f"[pypi-tp] FAIL {e}")
    total = await conn.fetchval("SELECT COUNT(*) FROM package_quality")
    signed = await conn.fetchval("SELECT COUNT(*) FROM package_quality WHERE publish_security IN ('signed','attested','trusted')")
    avg_crit = await conn.fetchval("SELECT AVG(criticality_score) FROM package_quality WHERE criticality_score IS NOT NULL")
    print(f"[done] total={total} signed/attested/trusted={signed} avg_criticality={avg_crit}")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
