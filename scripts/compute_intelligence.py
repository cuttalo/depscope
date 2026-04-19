#!/usr/bin/env python3
"""DepScope — compute intelligence snapshots.

Runs daily (cron @ 04:00). Processes the last 24h of api_usage:
  A) Infer sessions (group api_usage rows by session_id already computed)
  B) Detect intent from endpoints hit
  C) Infer project stack from packages requested
  D) Compute trend snapshots with rank + growth
  E) Package co-occurrence pairs
Privacy: stores only SHA256(ip+salt) in api_sessions.ip_hash, never the raw IP.
"""
import asyncio
import hashlib
import os
import sys
import itertools
from datetime import datetime, timedelta, timezone
from collections import Counter

import asyncpg

sys.path.insert(0, "/home/deploy/depscope")
from api.config import DATABASE_URL, IP_HASH_SALT  # noqa: E402


# ---- helpers ----------------------------------------------------------------

def _hash_ip(ip: str) -> str:
    if not ip:
        return ""
    return hashlib.sha256(f"{ip}|{IP_HASH_SALT}".encode()).hexdigest()


def _detect_intent(endpoints: list[str]) -> str:
    if not endpoints:
        return "unknown"
    counts = Counter(endpoints)
    total = sum(counts.values())

    def frac(*labels):
        return sum(counts.get(l, 0) for l in labels) / total if total else 0.0

    if frac("check", "prompt", "latest", "exists", "health", "info") > 0.7:
        return "package_check"
    if frac("error", "error/resolve") > 0.4:
        return "error_resolution"
    if frac("compare", "alternatives") > 0.4:
        return "comparison"
    if frac("scan", "tree", "licenses") > 0.3:
        return "audit"
    if frac("vulns", "vulnerabilities") > 0.3:
        return "security"
    return "unknown"


# Curated stack fingerprints: highest priority match wins.
# Each rule: (stack_name, required_packages_lowercase_set)
_STACK_RULES = [
    ("next-react-ts",       {"react", "next", "typescript"}),
    ("next-react",          {"react", "next"}),
    ("react-vite-ts",       {"react", "vite", "typescript"}),
    ("react-vite",          {"react", "vite"}),
    ("react-tailwind",      {"react", "tailwindcss"}),
    ("react",               {"react"}),
    ("vue-nuxt",            {"vue", "nuxt"}),
    ("vue",                 {"vue"}),
    ("svelte-kit",          {"svelte", "@sveltejs/kit"}),
    ("svelte",              {"svelte"}),
    ("angular",             {"@angular/core"}),
    ("node-express-mongo",  {"express", "mongoose"}),
    ("node-express-pg",     {"express", "pg"}),
    ("node-fastify",        {"fastify"}),
    ("node-nestjs",         {"@nestjs/core"}),
    ("node-express",        {"express"}),
    ("python-fastapi-sqla", {"fastapi", "sqlalchemy"}),
    ("python-fastapi",      {"fastapi", "pydantic"}),
    ("python-fastapi",      {"fastapi"}),
    ("python-django",       {"django"}),
    ("python-flask",        {"flask"}),
    ("python-ml",           {"numpy", "pandas"}),
    ("python-torch",        {"torch"}),
    ("rust-axum",           {"axum", "tokio"}),
    ("rust-tokio",          {"tokio"}),
    ("go-gin",              {"github.com/gin-gonic/gin"}),
]


def _infer_stack(packages: list[str]) -> str | None:
    pkgs = {p.lower() for p in packages if p}
    for stack_name, required in _STACK_RULES:
        if required.issubset(pkgs):
            return stack_name
    return None


# ---- main pipeline ----------------------------------------------------------

async def run():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        stats = {}

        # ---- A) Infer sessions (last 48h to catch boundary) ----
        rows = await conn.fetch("""
            SELECT session_id, ip_address, source,
                   MIN(created_at) AS first_call,
                   MAX(created_at) AS last_call,
                   COUNT(*)        AS call_count,
                   ARRAY_AGG(DISTINCT package_name)
                     FILTER (WHERE package_name IS NOT NULL AND package_name <> '') AS packages,
                   ARRAY_AGG(DISTINCT ecosystem)
                     FILTER (WHERE ecosystem IS NOT NULL AND ecosystem <> '')       AS ecosystems,
                   ARRAY_AGG(DISTINCT endpoint)
                     FILTER (WHERE endpoint IS NOT NULL AND endpoint <> '')         AS endpoints,
                   MAX(country)    AS country
            FROM api_usage
            WHERE session_id IS NOT NULL
              AND created_at > NOW() - INTERVAL '48 hours'
            GROUP BY session_id, ip_address, source
        """)
        sess_upserts = 0
        for r in rows:
            sid = r["session_id"]
            endpoints = list(r["endpoints"] or [])
            packages = list(r["packages"] or [])
            intent = _detect_intent(endpoints)
            stack = _infer_stack(packages)
            ip_hash = _hash_ip(r["ip_address"] or "")
            await conn.execute("""
                INSERT INTO api_sessions (
                    session_id, source, country, ip_hash,
                    first_call_at, last_call_at, call_count,
                    packages_requested, ecosystems_hit, endpoints_hit,
                    inferred_intent, inferred_stack
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                ON CONFLICT (session_id) DO UPDATE SET
                    last_call_at       = EXCLUDED.last_call_at,
                    call_count         = EXCLUDED.call_count,
                    packages_requested = EXCLUDED.packages_requested,
                    ecosystems_hit     = EXCLUDED.ecosystems_hit,
                    endpoints_hit      = EXCLUDED.endpoints_hit,
                    inferred_intent    = EXCLUDED.inferred_intent,
                    inferred_stack     = EXCLUDED.inferred_stack
            """, sid, r["source"] or "unknown", r["country"], ip_hash,
                 r["first_call"], r["last_call"], r["call_count"],
                 packages, list(r["ecosystems"] or []), endpoints,
                 intent, stack)
            sess_upserts += 1
        stats["sessions_upserted"] = sess_upserts

        # ---- D) Trend snapshots ----
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        seven_days_ago = today - timedelta(days=7)

        # Clear today's snapshot to avoid stale rank/growth
        await conn.execute("DELETE FROM trend_snapshots WHERE snapshot_date = $1", today)

        # Counts today (last 24h)
        counts_1d = await conn.fetch("""
            SELECT ecosystem, package_name, COUNT(*) AS c
            FROM api_usage
            WHERE created_at > NOW() - INTERVAL '1 day'
              AND package_name IS NOT NULL AND package_name <> ''
              AND ecosystem    IS NOT NULL AND ecosystem    <> ''
              AND COALESCE(source,'') NOT IN ('sdk','claude_bot','gpt_bot','internal')
            GROUP BY ecosystem, package_name
        """)

        # Counts 1 day ago for day-over-day rank change
        counts_yday = {
            (r["ecosystem"], r["package_name"]): r["c"]
            for r in await conn.fetch("""
                SELECT ecosystem, package_name, COUNT(*) AS c
                FROM api_usage
                WHERE created_at >= NOW() - INTERVAL '2 days'
                  AND created_at <  NOW() - INTERVAL '1 day'
                  AND package_name IS NOT NULL AND package_name <> ''
                  AND ecosystem    IS NOT NULL AND ecosystem    <> ''
                  AND COALESCE(source,'') NOT IN ('sdk','claude_bot','gpt_bot','internal')
                GROUP BY ecosystem, package_name
            """)
        }

        # Counts 7 days ago (day of week comparable) for week growth
        counts_7d_ago = {
            (r["ecosystem"], r["package_name"]): r["c"]
            for r in await conn.fetch("""
                SELECT ecosystem, package_name, COUNT(*) AS c
                FROM api_usage
                WHERE created_at >= NOW() - INTERVAL '8 days'
                  AND created_at <  NOW() - INTERVAL '7 days'
                  AND package_name IS NOT NULL AND package_name <> ''
                  AND ecosystem    IS NOT NULL AND ecosystem    <> ''
                  AND COALESCE(source,'') NOT IN ('sdk','claude_bot','gpt_bot','internal')
                GROUP BY ecosystem, package_name
            """)
        }

        # Compute yesterday ranks
        yday_sorted = sorted(counts_yday.items(), key=lambda kv: kv[1], reverse=True)
        yday_rank = {kv[0]: i + 1 for i, kv in enumerate(yday_sorted)}

        # Sort today's counts (per ecosystem ranking)
        by_eco: dict[str, list] = {}
        for r in counts_1d:
            by_eco.setdefault(r["ecosystem"], []).append((r["package_name"], r["c"]))
        for eco in by_eco:
            by_eco[eco].sort(key=lambda t: t[1], reverse=True)

        snap_rows = 0
        for eco, entries in by_eco.items():
            for rank_idx, (pkg, c) in enumerate(entries, start=1):
                prev_rank = yday_rank.get((eco, pkg))
                rank_change = (prev_rank - rank_idx) if prev_rank else None
                c_7d_ago = counts_7d_ago.get((eco, pkg), 0)
                if c_7d_ago > 0:
                    week_growth_pct = (c - c_7d_ago) / c_7d_ago * 100.0
                elif c > 0:
                    week_growth_pct = 100.0  # new entry
                else:
                    week_growth_pct = 0.0
                await conn.execute("""
                    INSERT INTO trend_snapshots
                      (snapshot_date, ecosystem, package_name, call_count,
                       rank, rank_change, week_growth_pct)
                    VALUES ($1,$2,$3,$4,$5,$6,$7)
                    ON CONFLICT (snapshot_date, ecosystem, package_name) DO UPDATE SET
                       call_count      = EXCLUDED.call_count,
                       rank            = EXCLUDED.rank,
                       rank_change     = EXCLUDED.rank_change,
                       week_growth_pct = EXCLUDED.week_growth_pct
                """, today, eco, pkg, c, rank_idx, rank_change, week_growth_pct)
                snap_rows += 1
        stats["trend_rows"] = snap_rows

        # ---- E) Co-occurrence ----
        # From sessions in last 7 days with >= 2 distinct packages
        cooccur_rows = await conn.fetch("""
            SELECT ecosystems_hit, packages_requested
            FROM api_sessions
            WHERE first_call_at > NOW() - INTERVAL '7 days'
              AND array_length(packages_requested, 1) >= 2
        """)
        pair_count = 0
        for r in cooccur_rows:
            ecos = list(r["ecosystems_hit"] or [])
            pkgs = sorted(set(p for p in (r["packages_requested"] or []) if p))
            if len(pkgs) < 2:
                continue
            eco = ecos[0] if ecos else "mixed"
            # limit to 10 pkgs per session to avoid combinatorial blowup
            pkgs = pkgs[:10]
            for a, b in itertools.combinations(pkgs, 2):
                if a == b:
                    continue
                pa, pb = sorted([a, b])
                await conn.execute("""
                    INSERT INTO package_cooccurrence
                      (ecosystem, package_a, package_b, cooccurrence_count, last_seen)
                    VALUES ($1,$2,$3,1,NOW())
                    ON CONFLICT (ecosystem, package_a, package_b) DO UPDATE SET
                      cooccurrence_count = package_cooccurrence.cooccurrence_count + 1,
                      last_seen          = NOW()
                """, eco, pa, pb)
                pair_count += 1
        stats["cooccur_upserts"] = pair_count

        return stats
    finally:
        await conn.close()


if __name__ == "__main__":
    s = asyncio.run(run())
    print(f"[{datetime.utcnow().isoformat()}Z] intelligence run complete: {s}")
