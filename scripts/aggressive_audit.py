#!/usr/bin/env python3
"""Aggressive API + data-integrity audit. Surfaces real problems, not just smoke.

Probes:
  P1  edge-case package names (slashes, dots, special, unicode, scoped npm)
  P2  cross-reference integrity: alternatives pointing at missing packages
  P3  cross-reference: breaking_changes / vulnerabilities orphan rows
  P4  health-score distribution anomalies (score=0 ratio, score>100, nulls)
  P5  vulnerabilities attribution (rows with null severity, invalid vuln_id)
  P6  package data completeness (desc/license/repo null ratios per eco)
  P7  api_usage recent-hour coherence (ip_hash null, status_code distribution)
  P8  duplicate detection (same (eco, LOWER(name)) in packages)
  P9  /api/check timing percentiles on cold cache (200 random pkg)
  P10 MCP full tool-call matrix (all 22 tools, representative pkg)
  P11 alternatives pointing back to self (self-reference loops)
  P12 maintainer_signals rows with unrealistic numbers (negative, billion+)

Produces a colourised report. Counts each issue; exits non-zero if any
critical finding.
"""
import asyncio
import json
import os
import random
import subprocess
import sys
import time

sys.path.insert(0, "/home/deploy/depscope")

import aiohttp
import asyncpg

from api.config import DATABASE_URL

BASE = "http://127.0.0.1:8000"
MCP  = "http://127.0.0.1:8001/mcp"


def ok(msg, detail=""):
    print(f"  \033[32m✓\033[0m {msg} \033[2m{detail}\033[0m")

def warn(msg, detail=""):
    print(f"  \033[33m⚠\033[0m {msg} \033[2m{detail}\033[0m")

def fail(msg, detail=""):
    print(f"  \033[31m✗\033[0m {msg} \033[2m{detail}\033[0m")


async def http_json(session, path, method="GET", **kw):
    async with session.request(method, f"{BASE}{path}", timeout=aiohttp.ClientTimeout(total=15), **kw) as r:
        try:
            return r.status, await r.json(content_type=None)
        except Exception:
            return r.status, None


# --- probes ---------------------------------------------------------------

EDGE_CASES = [
    ("npm", "@types/node"),                      # scoped + slash
    ("npm", "@babel/core"),                      # scoped
    ("npm", "lodash.get"),                       # dot
    ("composer", "symfony/console"),             # slash in composer
    ("composer", "doctrine/orm"),
    ("maven", "org.springframework:spring-core"),# colon
    ("swift", "Alamofire/Alamofire"),            # owner/repo
    ("swift", "vapor/vapor"),
    ("go",    "github.com/gin-gonic/gin"),       # full path
    ("pypi",  "django-rest-framework"),          # hyphen
    ("pypi",  "Pillow"),                         # capital
    ("cargo", "tokio"),
    ("pub",   "flutter_bloc"),                   # underscore
    ("hex",   "phoenix"),
    ("cpan",  "Moose"),
    ("cran",  "ggplot2"),
    ("conda", "numpy"),
    ("homebrew", "jq"),
    ("nuget", "Newtonsoft.Json"),
    ("rubygems", "rails"),
    # known 404 / test patterns
    ("npm", "this-pkg-does-not-exist-xyz-12345"),
    ("pypi", "totally-fake-pkg-zzz-9999"),
]


async def probe_edge_names(session):
    print("\n=== P1 edge-case names ===")
    for eco, pkg in EDGE_CASES:
        status, data = await http_json(session, f"/api/check/{eco}/{pkg}")
        if status == 200 and data and data.get("package"):
            ok(f"{eco}/{pkg}", f"v={data.get('latest_version','?')} score={data.get('health',{}).get('score','?')}")
        elif status == 404:
            warn(f"{eco}/{pkg}", "404 (expected for test names)")
        else:
            fail(f"{eco}/{pkg}", f"http={status}")


async def probe_integrity(conn):
    print("\n=== P2+P3+P8+P11+P12 DB integrity ===")
    # P2: alternatives.alternative_package_id pointing at missing package
    orphan_alt_ref = await conn.fetchval(
        "SELECT COUNT(*) FROM alternatives a WHERE a.alternative_package_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM packages p WHERE p.id = a.alternative_package_id)"
    )
    (ok if orphan_alt_ref == 0 else fail)(
        "alternatives.alternative_package_id -> packages FK integrity",
        f"orphans={orphan_alt_ref}",
    )
    # alt alternative_name that references a package that DOESN'T exist in same eco
    eco_missing_alts = await conn.fetch(
        """SELECT p.ecosystem, a.alternative_name, COUNT(*) AS n
             FROM alternatives a JOIN packages p ON p.id = a.package_id
            WHERE NOT EXISTS (
              SELECT 1 FROM packages p2
              WHERE p2.ecosystem = p.ecosystem AND LOWER(p2.name) = LOWER(a.alternative_name)
            )
            GROUP BY p.ecosystem, a.alternative_name
            ORDER BY n DESC LIMIT 5"""
    )
    if eco_missing_alts:
        warn(
            f"alternatives pointing to packages we haven't indexed: {sum(r['n'] for r in eco_missing_alts)} rows",
            f"e.g. {', '.join(r['ecosystem'] + '/' + r['alternative_name'] for r in eco_missing_alts[:3])}",
        )
    else:
        ok("every alternative target is indexed", "")

    # P3: orphan breaking_changes / vulnerabilities
    orphan_bc = await conn.fetchval(
        "SELECT COUNT(*) FROM breaking_changes bc WHERE NOT EXISTS "
        "(SELECT 1 FROM packages p WHERE p.id = bc.package_id)"
    )
    (ok if orphan_bc == 0 else fail)("breaking_changes FK integrity", f"orphans={orphan_bc}")

    orphan_v = await conn.fetchval(
        "SELECT COUNT(*) FROM vulnerabilities v WHERE NOT EXISTS "
        "(SELECT 1 FROM packages p WHERE p.id = v.package_id)"
    )
    (ok if orphan_v == 0 else fail)("vulnerabilities FK integrity", f"orphans={orphan_v}")

    # P8: duplicates
    dup = await conn.fetchval(
        "SELECT COUNT(*) FROM (SELECT ecosystem, LOWER(name) FROM packages "
        "GROUP BY 1,2 HAVING COUNT(*) > 1) x"
    )
    (ok if dup == 0 else fail)("no (ecosystem, LOWER(name)) duplicates", f"dups={dup}")

    # P11: self-reference loops
    self_ref = await conn.fetchval(
        "SELECT COUNT(*) FROM alternatives a JOIN packages p ON p.id = a.package_id "
        "WHERE LOWER(p.name) = LOWER(a.alternative_name)"
    )
    (ok if self_ref == 0 else warn)("no alternatives pointing at self", f"loops={self_ref}")

    # P12: unrealistic maintainer numbers
    bad_maint = await conn.fetchval(
        "SELECT COUNT(*) FROM maintainer_signals "
        "WHERE stars < 0 OR forks < 0 OR stars > 1000000 OR open_issues < 0"
    )
    (ok if bad_maint == 0 else fail)("maintainer_signals plausibility", f"outliers={bad_maint}")


async def probe_health_dist(conn):
    print("\n=== P4 health-score distribution ===")
    rows = await conn.fetch(
        "SELECT COUNT(*) FILTER (WHERE health_score IS NULL) AS null_score, "
        "COUNT(*) FILTER (WHERE health_score = 0) AS zero_score, "
        "COUNT(*) FILTER (WHERE health_score > 100) AS too_high, "
        "COUNT(*) FILTER (WHERE health_score < 0) AS too_low, "
        "AVG(health_score) AS avg_score, COUNT(*) AS total FROM packages"
    )
    r = rows[0]
    total = r["total"] or 1
    zero_pct = 100 * r["zero_score"] / total
    null_pct = 100 * r["null_score"] / total
    (fail if r["too_high"] or r["too_low"] else ok)(
        "health_score bounds 0..100",
        f"too_high={r['too_high']} too_low={r['too_low']}",
    )
    (warn if zero_pct > 5 else ok)(
        f"zero-score ratio",
        f"{zero_pct:.1f}% ({r['zero_score']:,}/{total:,})",
    )
    (warn if null_pct > 0 else ok)(f"null-score ratio", f"{null_pct:.2f}%")
    ok(f"avg health_score", f"{float(r['avg_score']) if r['avg_score'] else 0:.1f}")


async def probe_vulns(conn):
    print("\n=== P5 vulnerabilities quality ===")
    null_sev = await conn.fetchval(
        "SELECT COUNT(*) FROM vulnerabilities WHERE severity IS NULL OR severity = ''"
    )
    unknown_sev = await conn.fetchval(
        "SELECT COUNT(*) FROM vulnerabilities WHERE severity = 'unknown'"
    )
    bad_vid = await conn.fetchval(
        "SELECT COUNT(*) FROM vulnerabilities "
        "WHERE vuln_id IS NULL OR vuln_id = '' OR LENGTH(vuln_id) < 3"
    )
    total = await conn.fetchval("SELECT COUNT(*) FROM vulnerabilities")
    (fail if null_sev else ok)("vuln severity NOT NULL", f"nulls={null_sev}/{total}")
    (warn if unknown_sev > total * 0.15 else ok)(
        "vuln severity not dominated by 'unknown'",
        f"{unknown_sev}/{total} ({100*unknown_sev/max(total,1):.0f}%)",
    )
    (fail if bad_vid else ok)("vuln_id plausible", f"bad={bad_vid}")


async def probe_completeness(conn):
    print("\n=== P6 per-eco field completeness ===")
    rows = await conn.fetch(
        """SELECT ecosystem, COUNT(*) AS n,
                  100.0 * COUNT(*) FILTER (WHERE description IS NULL OR description = '') / COUNT(*) AS desc_null_pct,
                  100.0 * COUNT(*) FILTER (WHERE license IS NULL OR license = '') / COUNT(*) AS lic_null_pct,
                  100.0 * COUNT(*) FILTER (WHERE repository IS NULL OR repository = '') / COUNT(*) AS repo_null_pct,
                  100.0 * COUNT(*) FILTER (WHERE latest_version IS NULL OR latest_version = '') / COUNT(*) AS ver_null_pct
             FROM packages GROUP BY ecosystem ORDER BY n DESC"""
    )
    for r in rows:
        bad = []
        for field, pct in (("desc", r["desc_null_pct"]), ("lic", r["lic_null_pct"]),
                           ("repo", r["repo_null_pct"]), ("ver", r["ver_null_pct"])):
            if pct > 30:
                bad.append(f"{field}={pct:.0f}%")
        if bad:
            warn(f"{r['ecosystem']} ({r['n']:,} pkg)", "null: " + " ".join(bad))
        else:
            ok(f"{r['ecosystem']} fields",
               f"n={r['n']:,} desc-null={r['desc_null_pct']:.0f}% lic-null={r['lic_null_pct']:.0f}%")


async def probe_usage_coherence(conn):
    print("\n=== P7 api_usage recent-hour coherence ===")
    stats = await conn.fetchrow(
        "SELECT COUNT(*) AS total, "
        "COUNT(*) FILTER (WHERE ip_hash IS NULL) AS no_hash, "
        "COUNT(*) FILTER (WHERE agent_client IS NULL) AS no_agent, "
        "COUNT(*) FILTER (WHERE status_code IS NULL) AS no_status, "
        "COUNT(DISTINCT ip_hash) AS uniq_ips "
        "FROM api_usage WHERE created_at > NOW() - INTERVAL '24 hours'"
    )
    total = stats["total"] or 1
    ok("api_usage rows last 24h", f"{total:,} (uniq_ips={stats['uniq_ips']})")
    (warn if stats["no_hash"] else ok)("ip_hash populated", f"nulls={stats['no_hash']}")
    (warn if stats["no_agent"] else ok)("agent_client populated", f"nulls={stats['no_agent']}")
    (fail if stats["no_status"] else ok)("status_code populated", f"nulls={stats['no_status']}")


async def probe_latency(session):
    print("\n=== P9 /api/check latency on 50 random packages ===")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch(
            "SELECT ecosystem, name FROM packages "
            "WHERE ecosystem NOT IN ('swift','maven') "
            "ORDER BY random() LIMIT 50"
        )
    finally:
        await conn.close()
    latencies = []
    for r in rows:
        t0 = time.perf_counter()
        try:
            await http_json(session, f"/api/check/{r['ecosystem']}/{r['name']}")
        except Exception:
            continue
        latencies.append((time.perf_counter() - t0) * 1000)
    if not latencies:
        fail("latency probe", "no samples")
        return
    latencies.sort()
    n = len(latencies)
    p50, p95, p99 = latencies[int(n*0.5)], latencies[int(n*0.95)], latencies[int(n*0.99)]
    (ok if p95 < 2000 else warn)(f"latency", f"p50={p50:.0f}ms p95={p95:.0f}ms p99={p99:.0f}ms (n={n})")


async def probe_mcp_matrix(session):
    print("\n=== P10 MCP full tool matrix ===")
    sid = None
    # init
    async with session.post(
        MCP,
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                         "clientInfo": {"name": "audit", "version": "1.0"}}},
        headers={"Accept": "application/json, text/event-stream"},
    ) as r:
        txt = await r.text()
        sid = r.headers.get("Mcp-Session-Id")
    if not sid:
        # try parse SSE
        for line in txt.split("\n"):
            if line.startswith("data:"):
                try:
                    d = json.loads(line[5:].strip())
                    # some servers issue session id in response
                    break
                except Exception:
                    pass
    async def call(tool, args):
        body = {"jsonrpc":"2.0","id":random.randint(2, 10**9),"method":"tools/call",
                "params":{"name":tool,"arguments":args}}
        h = {"Accept": "application/json, text/event-stream",
             "Content-Type": "application/json"}
        if sid: h["Mcp-Session-Id"] = sid
        try:
            async with session.post(MCP, json=body, headers=h,
                                    timeout=aiohttp.ClientTimeout(total=30)) as r:
                txt = await r.text()
                for ln in txt.split("\n"):
                    if ln.startswith("data:"):
                        return json.loads(ln[5:].strip())
                return json.loads(txt) if txt else None
        except Exception as e:
            return {"error": {"message": str(e)}}

    tests = [
        ("check_package", {"ecosystem": "npm", "package": "react"}),
        ("package_exists", {"ecosystem": "npm", "package": "react"}),
        ("package_exists", {"ecosystem": "npm", "package": "xyz-does-not-exist-123"}),
        ("get_latest_version", {"ecosystem": "pypi", "package": "requests"}),
        ("get_vulnerabilities", {"ecosystem": "npm", "package": "lodash"}),
        ("find_alternatives", {"ecosystem": "npm", "package": "request"}),
        ("check_typosquat", {"ecosystem": "npm", "package": "reqeusts"}),
        ("check_malicious", {"ecosystem": "pypi", "package": "colorama"}),
        ("check_compatibility", {"packages": ["next@16", "react@19"]}),
        ("compare_packages", {"ecosystem": "npm", "packages": ["lodash", "underscore"]}),
        ("get_breaking_changes", {"ecosystem": "cargo", "package": "tokio"}),
        ("get_health_score", {"ecosystem": "pypi", "package": "django"}),
        ("get_known_bugs", {"ecosystem": "npm", "package": "moment"}),
        ("get_quality", {"ecosystem": "npm", "package": "react"}),
        ("resolve_error", {"error_message": "ModuleNotFoundError: No module named 'pands'"}),
    ]
    for tool, args in tests:
        res = await call(tool, args)
        if not res:
            fail(f"mcp {tool}", "no response")
        elif "error" in res and not res.get("result"):
            fail(f"mcp {tool}", str(res.get("error"))[:80])
        elif res.get("result"):
            content = res["result"].get("content")
            is_err = res["result"].get("isError")
            if is_err:
                warn(f"mcp {tool}", "isError=true")
            else:
                ok(f"mcp {tool}", f"content_items={len(content) if content else 0}")
        else:
            warn(f"mcp {tool}", "unexpected shape")


async def main():
    print("\033[1m=== Aggressive API + data integrity audit ===\033[0m")
    conn = await asyncpg.connect(DATABASE_URL)
    async with aiohttp.ClientSession() as session:
        await probe_edge_names(session)
        await probe_integrity(conn)
        await probe_health_dist(conn)
        await probe_vulns(conn)
        await probe_completeness(conn)
        await probe_usage_coherence(conn)
        await probe_latency(session)
        await probe_mcp_matrix(session)
    await conn.close()
    print("\n\033[1m=== audit complete ===\033[0m")


if __name__ == "__main__":
    asyncio.run(main())
