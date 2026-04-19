import os
"""DepScope API - Package Intelligence for AI Agents — Everything Free"""
import time
import re
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from api.config import VERSION

# IPs to exclude from analytics (our own servers, cron, preprocess)
EXCLUDED_IPS = {"127.0.0.1", "::1", "10.10.0.140", "10.10.0.1", "91.134.4.25"}
from api.database import get_pool, close_pool
from api.cache import cache_get, cache_set, rate_limit_check
from api.registries import fetch_package, fetch_vulnerabilities, save_package_to_db, fetch_github_stats, save_github_stats, get_github_stats_from_db
from api.health import calculate_health_score
from api.auth import router as auth_router, _get_user_from_request
from api.payments import router as payments_router
from api.mcp_http import mcp_router
from api.history import get_history
from api.intelligence import (
    fetch_bundle_size,
    check_typescript,
    build_dep_tree,
    aggregate_licenses,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(
    title="DepScope",
    description="Package Intelligence API for AI Agents. Free, open, no auth required. 14,700+ packages across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems, Composer, Pub, Hex, Swift, CocoaPods, CPAN, Hackage, CRAN, Conda, Homebrew). 402 vulnerabilities tracked. 12 MCP tools. Three verticals on one shared infrastructure: package health, error -> fix database, and stack compatibility matrix. Save tokens, save energy, ship safer code.",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    servers=[{"url": "https://depscope.dev", "description": "Production"}],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(payments_router)
app.include_router(mcp_router)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/") and not request.url.path.startswith("/api/auth/"):
        from api.auth import _get_user_from_request, TIER_LIMITS, ANON_LIMIT
        user = await _get_user_from_request(request)
        ip = request.headers.get("CF-Connecting-IP", request.client.host if request.client else "0.0.0.0")
        if user and user.get("role") == "admin":
            identifier, limit = f"admin:{ip}", 0
        elif user and user.get("auth_source") == "api_key":
            tier = user.get("tier") or user.get("plan", "free")
            limit = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
            identifier = f"key:{user.get('api_key_id')}"
        elif user:
            plan = user.get("plan", "free")
            limit = TIER_LIMITS.get(plan, TIER_LIMITS["free"])
            identifier = f"user:{user.get('id')}"
        else:
            limit = ANON_LIMIT
            identifier = f"ip:{ip}"
        if limit > 0:
            allowed = await rate_limit_check(identifier, limit)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"error": f"Rate limit exceeded ({limit} req/min). Upgrade your plan or slow down."},
                )
    response = await call_next(request)
    return response


@app.get("/", tags=["discovery"])
async def root():
    return {
        "service": "DepScope",
        "version": VERSION,
        "tagline": "Package Intelligence for AI Agents",
        "free": True,
        "auth_required": False,
        "endpoints": {
            "check": "/api/check/{ecosystem}/{package}",
            "prompt": "/api/prompt/{ecosystem}/{package}",
            "health": "/api/health/{ecosystem}/{package}",
            "vulns": "/api/vulns/{ecosystem}/{package}",
            "versions": "/api/versions/{ecosystem}/{package}",
            "compare": "/api/compare/{ecosystem}/{packages_csv}",
            "scan": "POST /api/scan",
            "stats": "/api/stats",
            "docs": "/docs",
        },
        "ecosystems": ["npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"],
        "rate_limit": "200 req/min per IP, no auth needed",
    }


async def _fetch_full_package(ecosystem: str, package: str) -> dict | None:
    """Internal helper: fetch package + vulns + health, save to DB, return full result.

    Optimised for <2s cache miss: the heavy external calls (registry, OSV, GitHub,
    bundlephobia, DefinitelyTyped) now all run in parallel with aggressive
    per-task timeouts (3s). A failing call degrades gracefully instead of
    dragging down the full response.
    """
    # Maven uses groupId:artifactId — support both : and / as separator
    if ecosystem == "maven" and ":" not in package and "/" in package:
        parts = package.split("/")
        if len(parts) == 2:
            package = f"{parts[0]}:{parts[1]}"

    # --- Stage 1: launch registry + OSV + (npm-only bundle/ts) in parallel.
    # OSV and bundlephobia don't need latest_version from the registry:
    # vuln filtering is re-applied once we know latest, and bundlephobia
    # accepts the package name without a version (returns latest).
    async def _with_timeout(coro, seconds=3.0):
        try:
            return await asyncio.wait_for(coro, timeout=seconds)
        except (asyncio.TimeoutError, Exception):
            return None

    registry_task = asyncio.create_task(_with_timeout(fetch_package(ecosystem, package), 3.0))
    osv_task = asyncio.create_task(_with_timeout(fetch_vulnerabilities(ecosystem, package, latest_version=None), 3.0))
    bundle_task = None
    ts_task = None
    if ecosystem == "npm":
        bundle_task = asyncio.create_task(_with_timeout(fetch_bundle_size(package, None), 3.0))
        ts_task = asyncio.create_task(_with_timeout(check_typescript(package), 3.0))

    pkg_data = await registry_task
    if not pkg_data:
        # Cancel in-flight tasks we no longer need
        for t in (osv_task, bundle_task, ts_task):
            if t is not None and not t.done():
                t.cancel()
        return None

    latest_version = pkg_data.get("latest_version", "")
    repo_url = pkg_data.get("repository", "")

    # --- Stage 2: once we have repo_url, launch GitHub in parallel and await
    # whatever's still pending.
    github_task = None
    if repo_url and "github.com" in repo_url:
        github_task = asyncio.create_task(_with_timeout(fetch_github_stats(repo_url), 3.0))

    vulns = await osv_task or []
    github_stats = await github_task if github_task is not None else None

    bundle = None
    typescript = None
    if ecosystem == "npm":
        bundle = await bundle_task if bundle_task is not None else None
        typescript = await ts_task if ts_task is not None else None
        if typescript is None:
            typescript = {"score": 0, "has_types": False, "types_source": None, "types_package": None}
        # Drop bundle if a prior fetch marked it unavailable
        if isinstance(bundle, dict) and bundle.get("_unavailable"):
            bundle = None

    # Fallback: if live GitHub fetch failed (rate limit / timeout), try DB cache.
    # Non-blocking: 1s budget.
    if github_stats is None and repo_url and "github.com" in repo_url:
        try:
            github_stats = await asyncio.wait_for(get_github_stats_from_db(repo_url), timeout=1.0)
        except Exception:
            github_stats = None

    # Re-filter OSV vulns against the known latest version (we fetched unfiltered
    # to run in parallel with the registry call).
    if latest_version and vulns:
        from api.registries import _is_vuln_relevant
        vulns = [v for v in vulns if _is_vuln_relevant(v, latest_version)]

    health = calculate_health_score(pkg_data, vulns, github=github_stats)

    # Save to PostgreSQL in background
    asyncio.create_task(save_package_to_db(pkg_data, health["score"], vulns))

    # Known-issues summary (non-CVE bugs from known_bugs table). Fast lookup,
    # but we still guard so a DB hiccup never breaks /api/check.
    known_issues = {"bugs_count": 0, "bugs_severity": {}, "link": None}
    try:
        from api.verticals import get_bugs_summary
        known_issues = await asyncio.wait_for(
            get_bugs_summary(ecosystem, package, pkg_data.get("latest_version")),
            timeout=1.5,
        )
    except Exception:
        pass

    recommendation = _build_recommendation(pkg_data, health, vulns)

    # --- Insufficient-data alignment: when the recommender downgrades to
    # "insufficient_data" (ecosystems with poor metadata — Hackage, CPAN, CRAN...)
    # the raw health score computed from those empty signals is misleading
    # (e.g. 40/high on `hackage/lens`). Surface the uncertainty in health too.
    if recommendation.get("action") == "insufficient_data":
        health = {
            **health,
            "score": None,
            "risk": "unknown",
            "note": "Insufficient data to compute reliable score",
        }

    # --- Fix 4: enrich recommendation with inline alternatives + bugs details,
    # so agents don't need a second round-trip.
    try:
        if recommendation.get("action") == "find_alternative":
            from api.verticals import get_alternatives as _get_alts_db
            alts = await _get_alts_db(ecosystem, package)
            if alts:
                recommendation["alternatives"] = alts[:3]
    except Exception:
        pass

    if known_issues.get("bugs_count", 0) > 0:
        try:
            from api.verticals import get_bugs_for_package
            # Match the scope used by get_bugs_summary(): if the summary is
            # scoped to a specific version we pass it, otherwise pull all
            # known bugs for the package so `details` is never empty when
            # `bugs_count > 0`.
            version_filter = (
                pkg_data.get("latest_version")
                if known_issues.get("scope") == "version"
                else None
            )
            bugs = await asyncio.wait_for(
                get_bugs_for_package(ecosystem, package, version_filter),
                timeout=1.5,
            )
            known_issues["details"] = [
                {
                    "title": b.get("title"),
                    "severity": b.get("severity"),
                    "status": b.get("status"),
                    "affected_version": b.get("affected_version"),
                    "fixed_version": b.get("fixed_version"),
                    "url": b.get("source_url"),
                }
                for b in (bugs or [])[:5]
            ]
        except Exception:
            pass

    return {
        "package": package,
        "ecosystem": ecosystem,
        "latest_version": pkg_data.get("latest_version"),
        "description": pkg_data.get("description", ""),
        "license": pkg_data.get("license", ""),
        "homepage": pkg_data.get("homepage", ""),
        "repository": pkg_data.get("repository", ""),
        "downloads_weekly": pkg_data.get("downloads_weekly", 0),
        "health": health,
        "vulnerabilities": {
            "count": len(vulns),
            "critical": sum(1 for v in vulns if v.get("severity") == "critical"),
            "high": sum(1 for v in vulns if v.get("severity") == "high"),
            "medium": sum(1 for v in vulns if v.get("severity") == "medium"),
            "low": sum(1 for v in vulns if v.get("severity") in ("low", "unknown")),
            "details": vulns,
        },
        "versions": {
            "latest": pkg_data.get("latest_version"),
            "total_count": pkg_data.get("all_version_count", 0),
            "recent": pkg_data.get("versions", []),
        },
        "metadata": {
            "deprecated": pkg_data.get("deprecated", False),
            "deprecated_message": pkg_data.get("deprecated_message"),
            "maintainers_count": pkg_data.get("maintainers_count", 0),
            "first_published": pkg_data.get("first_published"),
            "last_published": pkg_data.get("last_published"),
            "dependencies_count": len(pkg_data.get("dependencies", [])),
            "dependencies": pkg_data.get("dependencies", []),
        },
        "bundle": bundle,
        "typescript": typescript,
        "known_issues": known_issues,
        "recommendation": recommendation,
    }


@app.get("/api/check/{ecosystem}/{package:path}", tags=["packages"])
async def check_package(ecosystem: str, package: str, version: str = None, request: Request = None):
    """
    Full package intelligence. Returns everything: health, vulns, versions, recommendation.
    100% free. No auth. No limits on data. Use it.
    """
    start = time.time()
    ecosystem = ecosystem.lower()
    if ecosystem not in ("npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"):
        raise HTTPException(400, f"Unsupported ecosystem: {ecosystem}. Supported: npm, pypi, cargo, go, composer, maven, nuget, rubygems, pub, hex, swift, cocoapods, cpan, hackage, cran, conda, homebrew")

    cache_key = f"check:{ecosystem}:{package}"
    cached = await cache_get(cache_key)
    if cached:
        cached["_cache"] = "hit"
        cached["_response_ms"] = int((time.time() - start) * 1000)
        _log_usage(ecosystem, package, request,
                   response_time_ms=cached["_response_ms"], cache_hit=True,
                   status_code=200, endpoint="check")
        return cached

    result = await _fetch_full_package(ecosystem, package)
    if not result:
        _log_usage(ecosystem, package, request,
                   response_time_ms=int((time.time() - start) * 1000),
                   cache_hit=False, status_code=404, endpoint="check")
        raise HTTPException(404, f"Package '{package}' not found in {ecosystem}")

    result["requested_version"] = version
    result["_cache"] = "miss"
    result["_response_ms"] = int((time.time() - start) * 1000)
    result["_powered_by"] = "depscope.dev — free package intelligence for AI agents"

    await cache_set(cache_key, result, ttl=3600)
    _log_usage(ecosystem, package, request,
               response_time_ms=result["_response_ms"], cache_hit=False,
               status_code=200, endpoint="check")
    return result


def _format_age_days(iso_ts: str | None) -> str:
    """Return '(N days ago)' for an ISO date string, empty if missing."""
    if not iso_ts:
        return ""
    import datetime as _dt
    try:
        # Handle both 'Z' and '+00:00' suffixes and plain dates
        ts = iso_ts.replace("Z", "+00:00")
        if "T" not in ts:
            ts = ts + "T00:00:00+00:00"
        dt = _dt.datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_dt.timezone.utc)
        now = _dt.datetime.now(_dt.timezone.utc)
        days = (now - dt).days
        if days < 0:
            return ""
        return f"({days} days ago)"
    except Exception:
        return ""


def _build_prompt_text(result: dict, cache_age_minutes: int | None = None) -> str:
    """Format a full package result as LLM-optimized plain text.

    Token-efficient, one statement per line, no markdown, decisive recommendation.
    Target: ~500 tokens / 2000 chars.
    """
    pkg = result.get("package", "")
    eco = result.get("ecosystem", "")
    ver = result.get("latest_version") or "unknown"
    health = result.get("health") or {}
    score = health.get("score", 0)
    risk = health.get("risk", "unknown")
    vulns = result.get("vulnerabilities") or {}
    vcount = vulns.get("count", 0)
    vcrit = vulns.get("critical", 0)
    vhigh = vulns.get("high", 0)
    license_name = (result.get("license") or "").strip() or "unknown"
    meta = result.get("metadata") or {}
    deprecated = meta.get("deprecated", False)
    deps_total = meta.get("dependencies_count", 0)
    deps_list = meta.get("dependencies") or []
    last_pub = meta.get("last_published")
    bundle = result.get("bundle") or {}
    ts_info = result.get("typescript") or {}
    known = result.get("known_issues") or {}
    rec = result.get("recommendation") or {}
    rec_action = rec.get("action", "safe_to_use")

    # Decision word: USE / UPDATE / AVOID / DEPRECATED
    decision_map = {
        "safe_to_use": "USE",
        "update_required": "UPDATE",
        "use_with_caution": "USE WITH CAUTION",
        "find_alternative": "DEPRECATED",
        "do_not_use": "AVOID",
    }
    decision = decision_map.get(rec_action, "USE")

    # Status label (pre-existing semantic value)
    status = rec_action

    # License commercial-safety hint
    lic_lower = license_name.lower()
    if any(k in lic_lower for k in ("mit", "apache", "bsd", "isc", "unlicense", "cc0", "mpl")):
        lic_note = "commercial safe"
    elif any(k in lic_lower for k in ("agpl",)):
        lic_note = "copyleft — review before commercial use"
    elif any(k in lic_lower for k in ("gpl", "lgpl")):
        lic_note = "copyleft — review before commercial use"
    elif license_name == "unknown":
        lic_note = "unknown — verify manually"
    else:
        lic_note = "verify compatibility"

    # License display
    license_line = f"License: {license_name} ({lic_note})"

    # Vulnerabilities line
    if vcount == 0:
        vuln_line = "Vulnerabilities: 0 on latest"
    else:
        parts = []
        if vcrit:
            parts.append(f"{vcrit} critical")
        if vhigh:
            parts.append(f"{vhigh} high")
        extra = f" ({', '.join(parts)})" if parts else ""
        vuln_line = f"Vulnerabilities: {vcount} on latest{extra}"

    # Bundle line (npm only usually)
    bundle_line = None
    if bundle and isinstance(bundle, dict):
        size_kb = bundle.get("size_kb") or bundle.get("size")
        gzip_kb = bundle.get("gzip_kb") or bundle.get("gzip")
        if size_kb and gzip_kb:
            bundle_line = f"Bundle: {size_kb}KB minified / {gzip_kb}KB gzipped"
        elif size_kb:
            bundle_line = f"Bundle: {size_kb}KB minified"

    # TypeScript line (npm only)
    ts_line = None
    if ts_info and isinstance(ts_info, dict):
        has_types = ts_info.get("has_types")
        source = ts_info.get("types_source") or ""
        ts_score = ts_info.get("score")
        ts_pkg = ts_info.get("types_package")
        if has_types:
            if source == "bundled":
                ts_line = f"TypeScript: bundled types (score {ts_score}/10)"
            elif source == "definitelytyped" and ts_pkg:
                ts_line = f"TypeScript: via {ts_pkg} (score {ts_score}/10)"
            elif source:
                ts_line = f"TypeScript: {source} (score {ts_score}/10)"
            else:
                ts_line = f"TypeScript: types available (score {ts_score}/10)"
        elif eco == "npm":
            ts_line = "TypeScript: no types available"

    # Dependencies line
    low_health_deps = 0
    # Only count if dep entries carry a health score (dep tree is a separate call)
    for d in deps_list:
        if isinstance(d, dict):
            h = d.get("health_score") or d.get("health")
            if isinstance(h, dict):
                h = h.get("score")
            if isinstance(h, (int, float)) and h < 60:
                low_health_deps += 1
    deps_direct = len(deps_list) if deps_list else deps_total
    if low_health_deps:
        deps_line = f"Dependencies: {deps_direct} direct ({low_health_deps} with health <60)"
    else:
        deps_line = f"Dependencies: {deps_direct} direct"

    # Top 3 deps (names only)
    top_deps_line = None
    if deps_list:
        names = []
        for d in deps_list[:3]:
            if isinstance(d, dict):
                n = d.get("name") or d.get("package")
            else:
                n = str(d)
            if n:
                names.append(n)
        if names:
            top_deps_line = f"Top 3 deps: {', '.join(names)}"

    # Last release line
    last_rel_line = None
    if last_pub:
        last_rel_line = f"Last release: {last_pub[:10]} {_format_age_days(last_pub)}".strip()

    # Trend line from history (optional — skip if not cheap)
    # We keep it fixed-label style to avoid extra DB calls:
    trend_line = "Trend: see /api/history for 90-day series"

    # Recommendation sentence
    rec_summary = rec.get("summary", "")
    rec_lines = []
    if rec_action == "safe_to_use":
        rec_lines.append(f"Recommendation: {decision}. Safe to adopt.")
    elif rec_action == "update_required":
        hint = rec.get("version_hint") or "update to latest"
        rec_lines.append(f"Recommendation: {decision}. {hint}.")
    elif rec_action == "use_with_caution":
        rec_lines.append(f"Recommendation: {decision}. Low health score — consider alternatives.")
    elif rec_action == "find_alternative":
        rec_lines.append(f"Recommendation: {decision}. Package is deprecated, find a replacement.")
    elif rec_action == "do_not_use":
        rec_lines.append(f"Recommendation: {decision}. Critical vulnerabilities present.")
    else:
        rec_lines.append(f"Recommendation: {decision}.")

    if deprecated and rec_action not in ("find_alternative", "do_not_use"):
        rec_lines.append("Note: package is marked deprecated.")

    # Build text
    lines = [
        f"{pkg}@{ver} — {eco} package",
        f"Health: {score}/100 ({risk} risk)",
        f"Status: {status}",
        vuln_line,
        license_line,
    ]
    if bundle_line:
        lines.append(bundle_line)
    if ts_line:
        lines.append(ts_line)
    lines.append(deps_line)

    # Known-issues line (only if we have data)
    bugs_count = int(known.get("bugs_count") or 0)
    if bugs_count:
        sev = known.get("bugs_severity") or {}
        high = int(sev.get("high") or 0)
        status = known.get("status_breakdown") or {}
        open_count = int(status.get("open") or 0) or bugs_count
        parts = [f"{open_count} open"]
        if high:
            parts.append(f"{high} high severity")
        link = known.get("link") or f"/api/bugs/{eco}/{pkg}"
        lines.append(f"Known issues: {', '.join(parts)} — see {link}")

    lines.append(trend_line)
    lines.append("")
    lines.extend(rec_lines)
    if last_rel_line:
        lines.append(last_rel_line)
    if top_deps_line:
        lines.append(top_deps_line)

    # Footer / citation
    slug_pkg = pkg.replace(":", "/")
    src_url = f"depscope.dev/pkg/{eco}/{slug_pkg}"
    freshness = "just fetched"
    if cache_age_minutes is not None:
        freshness = f"cached {cache_age_minutes} minutes ago"
    lines.append("")
    lines.append("---")
    lines.append(f"Source: {src_url}")
    lines.append(f"Data freshness: {freshness}")

    text = "\n".join(lines) + "\n"
    # Safety: hard cap ~2200 chars to stay token-efficient
    if len(text) > 2200:
        text = text[:2180] + "\n...\n"
    return text


@app.get("/api/prompt/{ecosystem}/{package:path}", tags=["packages"])
async def get_prompt(ecosystem: str, package: str, request: Request = None):
    """LLM-optimized plain-text context for a package.

    Token-efficient, decision-ready, ~500 tokens. Use this from AI agents
    instead of /api/check to save context and tokens.
    """
    start = time.time()
    ecosystem = ecosystem.lower()
    if ecosystem not in ("npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"):
        return PlainTextResponse(
            content=f"Unsupported ecosystem: {ecosystem}.\n",
            status_code=400,
            media_type="text/plain; charset=utf-8",
        )

    cache_key = f"prompt:{ecosystem}:{package}"
    cached = await cache_get(cache_key)
    if cached and isinstance(cached, dict) and "text" in cached:
        age_min = max(0, int((time.time() - cached.get("ts", time.time())) / 60))
        # Re-stamp freshness line in cached text
        text = cached["text"]
        text = re.sub(
            r"Data freshness: [^\n]+",
            f"Data freshness: cached {age_min} minutes ago",
            text,
        )
        rt_ms = int((time.time() - start) * 1000)
        _log_usage(ecosystem, package, request, response_time_ms=rt_ms,
                   cache_hit=True, status_code=200, endpoint="prompt")
        return PlainTextResponse(
            content=text,
            media_type="text/plain; charset=utf-8",
            headers={"X-Cache": "hit", "X-Response-Ms": str(rt_ms)},
        )

    result = await _fetch_full_package(ecosystem, package)
    if not result:
        _log_usage(ecosystem, package, request,
                   response_time_ms=int((time.time() - start) * 1000),
                   cache_hit=False, status_code=404, endpoint="prompt")
        return PlainTextResponse(
            content="Package not found. Check spelling.\n",
            status_code=404,
            media_type="text/plain; charset=utf-8",
        )

    text = _build_prompt_text(result, cache_age_minutes=None)
    await cache_set(cache_key, {"text": text, "ts": time.time()}, ttl=3600)
    rt_ms = int((time.time() - start) * 1000)
    _log_usage(ecosystem, package, request, response_time_ms=rt_ms,
               cache_hit=False, status_code=200, endpoint="prompt")
    return PlainTextResponse(
        content=text,
        media_type="text/plain; charset=utf-8",
        headers={"X-Cache": "miss", "X-Response-Ms": str(rt_ms)},
    )


@app.get("/api/health/{ecosystem}/{package:path}", tags=["packages"])
async def get_health(ecosystem: str, package: str):
    """Quick health score."""
    ecosystem = ecosystem.lower()
    cache_key = f"health:{ecosystem}:{package}"
    cached = await cache_get(cache_key)
    if cached:
        return cached
    pkg_data = await fetch_package(ecosystem, package)
    if not pkg_data:
        raise HTTPException(404, f"Package '{package}' not found in {ecosystem}")
    latest_version = pkg_data.get("latest_version", "")
    vulns = await fetch_vulnerabilities(ecosystem, package, latest_version=latest_version)
    result = calculate_health_score(pkg_data, vulns)
    await cache_set(cache_key, result, ttl=3600)
    return result


@app.get("/api/vulns/{ecosystem}/{package:path}", tags=["packages"])
async def get_vulns(ecosystem: str, package: str):
    """Vulnerabilities affecting the LATEST version only."""
    ecosystem = ecosystem.lower()
    pkg_data = await fetch_package(ecosystem, package)
    latest_version = pkg_data.get("latest_version", "") if pkg_data else None
    vulns = await fetch_vulnerabilities(ecosystem, package, latest_version=latest_version)
    return {
        "package": package,
        "ecosystem": ecosystem,
        "latest_version": latest_version,
        "count": len(vulns),
        "note": "Only vulnerabilities affecting the latest version are shown",
        "vulnerabilities": vulns,
    }


@app.get("/api/versions/{ecosystem}/{package:path}", tags=["packages"])
async def get_versions(ecosystem: str, package: str):
    """Version info."""
    ecosystem = ecosystem.lower()
    pkg_data = await fetch_package(ecosystem, package)
    if not pkg_data:
        raise HTTPException(404, f"Package '{package}' not found in {ecosystem}")
    return {
        "package": package, "ecosystem": ecosystem,
        "latest": pkg_data.get("latest_version"),
        "total": pkg_data.get("all_version_count", 0),
        "recent": pkg_data.get("versions", []),
        "deprecated": pkg_data.get("deprecated", False),
    }


@app.get("/api/history/{ecosystem}/{package:path}", tags=["packages"])
async def get_history_endpoint(ecosystem: str, package: str, days: int = 90):
    """Last N days of health snapshot + trend direction (up/down/stable).

    Data is populated by the daily cron /scripts/record_health_snapshot.py.
    Max 365 days; if the package is new the series will be shorter.
    """
    ecosystem = ecosystem.lower()
    days = max(1, min(365, days))
    data = await get_history(ecosystem, package, days=days)
    if not data:
        raise HTTPException(404, f"Package '{package}' not found in {ecosystem}")
    return data


@app.get("/api/tree/{ecosystem}/{package:path}", tags=["packages"])
async def get_tree_endpoint(ecosystem: str, package: str, max_depth: int = 3, max_deps: int = 200):
    """Transitive dependency tree with health score per sub-dep.

    Cached aggressively (24h) — expensive to build.
    """
    ecosystem = ecosystem.lower()
    max_depth = max(1, min(5, max_depth))
    max_deps = max(10, min(500, max_deps))
    tree = await build_dep_tree(ecosystem, package, max_depth=max_depth, max_deps=max_deps)
    if not tree:
        raise HTTPException(404, f"Package '{package}' not found in {ecosystem}")
    return tree


@app.get("/api/licenses/{ecosystem}/{package:path}", tags=["packages"])
async def get_licenses_endpoint(ecosystem: str, package: str):
    """Aggregated licenses across the transitive dependency tree.

    Flags GPL/AGPL/LGPL for commercial-safety review. Reuses the same tree cache.
    """
    ecosystem = ecosystem.lower()
    data = await aggregate_licenses(ecosystem, package)
    if not data:
        raise HTTPException(404, f"Package '{package}' not found in {ecosystem}")
    return data


# --------------------------------------------------------------------------- #
# VERTICALS — Error→Fix, Compatibility Matrix, Known Bugs
# --------------------------------------------------------------------------- #

@app.get("/api/error", tags=["errors"])
async def search_error(q: str, limit: int = 5):
    """Search the error database by message (full-text + exact hash)."""
    q = (q or "").strip()
    if not q:
        raise HTTPException(400, "Query parameter 'q' is required")
    limit = max(1, min(int(limit or 5), 50))

    cache_key = f"err:search:{limit}:{q}"
    cached = await cache_get(cache_key)
    if cached:
        cached["_cache"] = "hit"
        return cached

    from api.verticals import search_errors
    try:
        results = await search_errors(q, limit)
    except Exception as e:
        raise HTTPException(500, f"Error search failed: {e}")
    payload = {"query": q, "matches": results, "total": len(results), "_cache": "miss"}
    await cache_set(cache_key, payload, ttl=86400)  # 24h
    return payload


@app.post("/api/error/resolve", tags=["errors"])
async def resolve_error(request: Request):
    """POST a stack trace or error message, get solutions back."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON body")
    error_text = (body or {}).get("error", "") or ""
    context = (body or {}).get("context") or {}
    if not error_text.strip():
        raise HTTPException(400, "Field 'error' is required")

    from api.verticals import (
        normalize_error, hash_error_pattern,
        get_error_by_hash, search_errors,
    )
    h = hash_error_pattern(error_text)

    cache_key = f"err:resolve:{h}"
    cached = await cache_get(cache_key)
    if cached:
        cached["_cache"] = "hit"
        return cached

    try:
        exact = await get_error_by_hash(h)
    except Exception:
        exact = None
    if exact:
        payload = {
            "status": "exact_match",
            "solution": exact,
            "confidence": 1.0,
            "context": context,
            "hash": h,
            "_cache": "miss",
        }
        await cache_set(cache_key, payload, ttl=86400)
        return payload

    try:
        similar = await search_errors(normalize_error(error_text), limit=3)
    except Exception:
        similar = []
    payload = {
        "status": "similar_matches" if similar else "not_found",
        "matches": similar,
        "confidence": 0.5 if similar else 0.0,
        "context": context,
        "hash": h,
        "_cache": "miss",
    }
    await cache_set(cache_key, payload, ttl=86400)
    return payload


@app.get("/api/error/{error_hash}", tags=["errors"])
async def get_error(error_hash: str):
    """Get a specific error entry by its normalised-pattern SHA256."""
    from api.verticals import get_error_by_hash
    r = await get_error_by_hash(error_hash)
    if not r:
        raise HTTPException(404, "Error not found")
    return r


@app.get("/api/compat", tags=["compat"])
async def check_compatibility(stack: str):
    """Check compatibility for a stack like 'next@16,react@19,prisma@6'."""
    stack = (stack or "").strip()
    if not stack:
        raise HTTPException(400, "Query parameter 'stack' is required")

    packages: dict[str, str] = {}
    for part in stack.split(","):
        part = part.strip()
        if "@" in part:
            name, version = part.rsplit("@", 1)
            name = name.strip()
            version = version.strip()
            if name:
                packages[name] = version
    if not packages:
        raise HTTPException(400, "Invalid stack format. Use 'pkg@version,pkg@version'")

    cache_key = f"compat:get:" + ",".join(f"{k}@{v}" for k, v in sorted(packages.items()))
    cached = await cache_get(cache_key)
    if cached:
        cached["_cache"] = "hit"
        return cached

    from api.verticals import check_compat
    try:
        result = await check_compat(packages)
    except Exception as e:
        raise HTTPException(500, f"Compat lookup failed: {e}")
    result["_cache"] = "miss"
    await cache_set(cache_key, result, ttl=21600)  # 6h
    return result


@app.post("/api/compat", tags=["compat"])
async def check_compatibility_post(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON body")
    packages = (body or {}).get("packages") or {}
    if not isinstance(packages, dict) or not packages:
        raise HTTPException(400, "'packages' must be a non-empty object")

    cache_key = f"compat:post:" + ",".join(
        f"{k}@{v}" for k, v in sorted({str(k).lower(): str(v) for k, v in packages.items()}.items())
    )
    cached = await cache_get(cache_key)
    if cached:
        cached["_cache"] = "hit"
        return cached

    from api.verticals import check_compat
    try:
        result = await check_compat(packages)
    except Exception as e:
        raise HTTPException(500, f"Compat lookup failed: {e}")
    result["_cache"] = "miss"
    await cache_set(cache_key, result, ttl=21600)
    return result


@app.get("/api/bugs/search", tags=["bugs"])
async def search_bugs_endpoint(q: str, limit: int = 20):
    """Search the known-bugs database by text."""
    q = (q or "").strip()
    if not q:
        raise HTTPException(400, "Query parameter 'q' is required")
    limit = max(1, min(int(limit or 20), 50))

    cache_key = f"bugs:search:{limit}:{q}"
    cached = await cache_get(cache_key)
    if cached:
        cached["_cache"] = "hit"
        return cached

    from api.verticals import search_bugs
    try:
        matches = await search_bugs(q, limit)
    except Exception as e:
        raise HTTPException(500, f"Bug search failed: {e}")
    payload = {"query": q, "matches": matches, "total": len(matches), "_cache": "miss"}
    await cache_set(cache_key, payload, ttl=43200)  # 12h
    return payload


@app.get("/api/bugs/{ecosystem}/{package:path}", tags=["bugs"])
async def get_bugs(ecosystem: str, package: str, version: str = None):
    """Get known bugs for a package, optionally filtered by version."""
    ecosystem = (ecosystem or "").lower()
    if ecosystem not in (
        "npm", "pypi", "cargo", "go", "composer", "maven", "nuget",
        "rubygems", "pub", "hex", "swift", "cocoapods", "cpan",
        "hackage", "cran", "conda", "homebrew",
    ):
        raise HTTPException(400, f"Unsupported ecosystem: {ecosystem}")

    cache_key = f"bugs:pkg:{ecosystem}:{package}:{version or 'any'}"
    cached = await cache_get(cache_key)
    if cached:
        cached["_cache"] = "hit"
        return cached

    from api.verticals import get_bugs_for_package
    try:
        bugs = await get_bugs_for_package(ecosystem, package, version)
    except Exception as e:
        raise HTTPException(500, f"Bug lookup failed: {e}")
    payload = {
        "ecosystem": ecosystem,
        "package": package,
        "version": version,
        "bugs": bugs,
        "total": len(bugs),
        "_cache": "miss",
    }
    await cache_set(cache_key, payload, ttl=43200)
    return payload


@app.get("/api/breaking", tags=["breaking"])
async def list_breaking_sample(limit: int = 12):
    """Sample of most recent curated breaking changes across all packages.

    Used by the /explore/breaking SSR page to show real examples
    without requiring the user to pick a package first.
    """
    limit = max(1, min(int(limit or 12), 50))
    cache_key = f"breaking:sample:{limit}"
    cached = await cache_get(cache_key)
    if cached:
        cached["_cache"] = "hit"
        return cached

    from api.database import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT p.ecosystem, p.name AS package,
                   b.from_version, b.to_version, b.change_type,
                   b.description, b.migration_hint
            FROM breaking_changes b
            JOIN packages p ON p.id = b.package_id
            ORDER BY b.id DESC
            LIMIT $1
            """,
            limit,
        )
    items = [dict(r) for r in rows]
    payload = {
        "total": len(items),
        "changes": items,
        "note": (
            "Sample of curated breaking changes across ecosystems. "
            "Use /api/breaking/{ecosystem}/{package} for package-specific results."
        ),
        "_cache": "miss",
    }
    await cache_set(cache_key, payload, ttl=3600)
    return payload


@app.get("/api/breaking/{ecosystem}/{package:path}", tags=["breaking"])
async def get_breaking(
    ecosystem: str,
    package: str,
    from_version: str | None = None,
    to_version: str | None = None,
):
    """Breaking changes for a package, optionally scoped to a version transition.

    Examples:
      GET /api/breaking/npm/react
      GET /api/breaking/npm/next?from_version=14&to_version=15
      GET /api/breaking/pypi/pydantic?from_version=1&to_version=2
    """
    ecosystem = (ecosystem or "").lower()
    if ecosystem not in (
        "npm", "pypi", "cargo", "go", "composer", "maven", "nuget",
        "rubygems", "pub", "hex", "swift", "cocoapods", "cpan",
        "hackage", "cran", "conda", "homebrew",
    ):
        raise HTTPException(400, f"Unsupported ecosystem: {ecosystem}")

    cache_key = f"breaking:{ecosystem}:{package}:{from_version or ''}:{to_version or ''}"
    cached = await cache_get(cache_key)
    if cached:
        cached["_cache"] = "hit"
        return cached

    from api.verticals import get_breaking_changes
    try:
        changes = await get_breaking_changes(ecosystem, package, from_version, to_version)
    except Exception as e:
        raise HTTPException(500, f"Breaking-change lookup failed: {e}")

    payload = {
        "ecosystem": ecosystem,
        "package": package,
        "from_version": from_version,
        "to_version": to_version,
        "changes": changes,
        "total": len(changes),
        "note": (
            "Curated major-version breaking changes. Always verify against the "
            "package's official changelog before migrating."
        ) if changes else "No breaking changes recorded for this package yet.",
        "_cache": "miss",
    }
    await cache_set(cache_key, payload, ttl=43200)
    return payload


@app.get("/api/compare/{ecosystem}/{packages_csv}", tags=["packages"])
async def compare_packages(ecosystem: str, packages_csv: str, request: Request = None):
    """
    Compare 2+ packages side by side.
    Usage: GET /api/compare/npm/express,fastify,hono
    Returns comparative table with health, vulns, downloads, last release.
    """
    start = time.time()
    ecosystem = ecosystem.lower()
    if ecosystem not in ("npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"):
        raise HTTPException(400, f"Unsupported ecosystem: {ecosystem}")

    names = [n.strip() for n in packages_csv.split(",") if n.strip()]
    if len(names) < 2:
        raise HTTPException(400, "Provide at least 2 packages separated by commas")
    if len(names) > 10:
        raise HTTPException(400, "Max 10 packages per comparison")

    # Check compare cache first
    sorted_names = sorted(names)
    compare_cache_key = f"compare:{ecosystem}:{','.join(sorted_names)}"
    cached_compare = await cache_get(compare_cache_key)
    if cached_compare:
        cached_compare["_cache"] = "hit"
        cached_compare["_response_ms"] = int((time.time() - start) * 1000)
        return cached_compare

    # Fetch all in parallel
    tasks = [_fetch_full_package(ecosystem, name) for name in names]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    packages = []
    for name, result in zip(names, results):
        if isinstance(result, Exception) or result is None:
            packages.append({
                "package": name,
                "error": "not_found",
            })
            continue

        packages.append({
            "package": name,
            "latest_version": result.get("latest_version"),
            "health_score": result["health"]["score"],
            "health_risk": result["health"]["risk"],
            "downloads_weekly": result.get("downloads_weekly", 0),
            "vulnerabilities_count": result["vulnerabilities"]["count"],
            "vulns_critical": result["vulnerabilities"]["critical"],
            "vulns_high": result["vulnerabilities"]["high"],
            "last_published": result["metadata"]["last_published"],
            "license": result.get("license", ""),
            "deprecated": result["metadata"]["deprecated"],
            "maintainers_count": result["metadata"]["maintainers_count"],
            "dependencies_count": result["metadata"]["dependencies_count"],
            "recommendation": result["recommendation"]["action"],
        })

    # Sort by health score descending
    valid = [p for p in packages if "error" not in p]
    valid.sort(key=lambda x: x["health_score"], reverse=True)
    winner = valid[0]["package"] if valid else None

    compare_result = {
        "ecosystem": ecosystem,
        "compared": len(packages),
        "winner": winner,
        "packages": packages,
        "_response_ms": int((time.time() - start) * 1000),
    }
    await cache_set(compare_cache_key, compare_result, ttl=3600)
    if request:
        _log_usage(ecosystem, packages_csv, request,
                   response_time_ms=compare_result["_response_ms"],
                   cache_hit=False, status_code=200, endpoint="compare")
    return compare_result


@app.post("/api/scan", tags=["packages"])
async def scan_dependencies(request: Request):
    """
    Audit an entire project's dependencies in one shot.
    POST body: {"packages": {"express": "^4.0.0", "lodash": "^4.17.0"}, "ecosystem": "npm"}
    Or: {"packages": {"fastapi": ">=0.100.0", "pydantic": "^2.0"}, "ecosystem": "pypi"}
    """
    start = time.time()
    body = await request.json()
    packages = body.get("packages", {})
    ecosystem = body.get("ecosystem", "npm").lower()

    if ecosystem not in ("npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"):
        raise HTTPException(400, f"Unsupported ecosystem: {ecosystem}")
    if not packages or not isinstance(packages, dict):
        raise HTTPException(400, "Provide 'packages' as a dict of {name: version_constraint}")
    if len(packages) > 100:
        raise HTTPException(400, "Max 100 packages per scan")

    # Fetch all in parallel
    names = list(packages.keys())
    tasks = [_fetch_full_package(ecosystem, name) for name in names]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    audit = []
    total_vulns = 0
    total_critical = 0
    total_high = 0
    worst_score = 100
    issues = []

    for name, version_constraint, result in zip(names, packages.values(), results):
        if isinstance(result, Exception) or result is None:
            audit.append({
                "package": name,
                "requested_version": version_constraint,
                "error": "not_found",
            })
            issues.append(f"{name}: package not found in {ecosystem}")
            continue

        health_score = result["health"]["score"]
        vuln_count = result["vulnerabilities"]["count"]
        crit = result["vulnerabilities"]["critical"]
        high = result["vulnerabilities"]["high"]

        total_vulns += vuln_count
        total_critical += crit
        total_high += high
        worst_score = min(worst_score, health_score)

        if crit > 0:
            issues.append(f"{name}: {crit} critical vulnerabilities")
        if high > 0:
            issues.append(f"{name}: {high} high severity vulnerabilities")
        if result["metadata"]["deprecated"]:
            issues.append(f"{name}: deprecated")
        if health_score < 40:
            issues.append(f"{name}: low health score ({health_score}/100)")

        audit.append({
            "package": name,
            "requested_version": version_constraint,
            "latest_version": result.get("latest_version"),
            "health_score": health_score,
            "health_risk": result["health"]["risk"],
            "vulnerabilities": {
                "count": vuln_count,
                "critical": crit,
                "high": high,
            },
            "deprecated": result["metadata"]["deprecated"],
            "recommendation": result["recommendation"]["action"],
        })

    # Overall project risk
    if total_critical > 0:
        project_risk = "critical"
    elif total_high > 0:
        project_risk = "high"
    elif worst_score < 60:
        project_risk = "moderate"
    else:
        project_risk = "low"

    _log_usage(ecosystem, f"scan:{len(names)}pkgs", request,
               response_time_ms=int((time.time() - start) * 1000),
               cache_hit=False, status_code=200, endpoint="scan")

    return {
        "ecosystem": ecosystem,
        "packages_scanned": len(names),
        "project_risk": project_risk,
        "summary": {
            "total_vulnerabilities": total_vulns,
            "critical": total_critical,
            "high": total_high,
            "lowest_health_score": worst_score,
            "issues": issues,
        },
        "packages": audit,
        "_response_ms": int((time.time() - start) * 1000),
    }


@app.get("/api/stats", tags=["public"])
async def get_stats():
    """Public usage stats."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        pkg_count = await conn.fetchval("SELECT COUNT(*) FROM packages")
        vuln_count = await conn.fetchval("SELECT COUNT(*) FROM vulnerabilities")
        usage_today = await conn.fetchval("SELECT COUNT(*) FROM api_usage WHERE created_at > NOW() - INTERVAL '1 day' AND user_agent NOT ILIKE '%node%' AND user_agent NOT ILIKE '%bot%' AND user_agent NOT ILIKE '%crawl%' AND user_agent NOT ILIKE '%spider%' AND user_agent NOT ILIKE '%GoogleOther%' AND user_agent != ''")
        usage_total = await conn.fetchval("SELECT COUNT(*) FROM api_usage WHERE user_agent NOT ILIKE '%node%' AND user_agent NOT ILIKE '%bot%' AND user_agent NOT ILIKE '%crawl%' AND user_agent NOT ILIKE '%spider%' AND user_agent NOT ILIKE '%GoogleOther%' AND user_agent != ''")
        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        top = await conn.fetch("""
            SELECT ecosystem, package_name, COUNT(*) as searches
            FROM api_usage WHERE created_at > NOW() - INTERVAL '7 days'
            AND user_agent NOT LIKE '%Node%' AND user_agent NOT LIKE '%bot%' AND user_agent NOT LIKE '%crawl%'
            GROUP BY ecosystem, package_name ORDER BY searches DESC LIMIT 10
        """)
        eco_rows = await conn.fetch("SELECT ecosystem, COUNT(*) as cnt FROM packages GROUP BY ecosystem ORDER BY cnt DESC")
    eco_list = [r["ecosystem"] for r in eco_rows]
    eco_counts = {r["ecosystem"]: r["cnt"] for r in eco_rows}
    STATS_THRESHOLD = 10000
    return {
        "packages_indexed": pkg_count,
        "vulnerabilities_tracked": vuln_count,
        "api_calls_today": usage_today if usage_total >= STATS_THRESHOLD else None,
        "api_calls_total": usage_total if usage_total >= STATS_THRESHOLD else None,
        "registered_users": users_count if usage_total >= STATS_THRESHOLD else None,
        "trending": [{"ecosystem": r["ecosystem"], "package": r["package_name"], "searches": r["searches"]} for r in top],
        "ecosystems": eco_list,
        "ecosystem_counts": eco_counts,
        "version": VERSION,
        "pricing": "free",
    }


@app.get("/api/admin/dashboard", include_in_schema=False)
async def admin_dashboard(request: Request):
    """Admin dashboard data."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        users = await conn.fetch("SELECT id, email, role, plan, api_key, created_at FROM users ORDER BY created_at DESC")
        usage_by_day = await conn.fetch("""
            SELECT DATE(created_at) as day, COUNT(*) as calls
            FROM api_usage WHERE created_at > NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at) ORDER BY day
        """)
        usage_by_eco = await conn.fetch("""
            SELECT ecosystem, COUNT(*) as calls FROM api_usage
            WHERE created_at > NOW() - INTERVAL '30 days'
            GROUP BY ecosystem ORDER BY calls DESC
        """)
        top_packages = await conn.fetch("""
            SELECT ecosystem, package_name, COUNT(*) as searches
            FROM api_usage WHERE created_at > NOW() - INTERVAL '7 days'
            AND user_agent NOT LIKE '%Node%' AND user_agent NOT LIKE '%bot%' AND user_agent NOT LIKE '%crawl%'
            GROUP BY ecosystem, package_name ORDER BY searches DESC LIMIT 30
        """)
        top_agents = await conn.fetch("""
            SELECT 
                CASE 
                    WHEN user_agent LIKE '%Claude%' THEN 'Claude'
                    WHEN user_agent LIKE '%ChatGPT%' OR user_agent LIKE '%OpenAI%' THEN 'ChatGPT'
                    WHEN user_agent LIKE '%Cursor%' THEN 'Cursor'
                    WHEN user_agent LIKE '%Windsurf%' THEN 'Windsurf'
                    WHEN user_agent LIKE '%DepScope-MCP%' THEN 'MCP Server'
                    WHEN user_agent LIKE '%curl%' THEN 'curl'
                    WHEN user_agent LIKE '%python%' THEN 'Python'
                    WHEN user_agent LIKE '%node%' OR user_agent LIKE '%Node%' THEN 'Node.js'
                    ELSE 'Other'
                END as agent,
                COUNT(*) as calls
            FROM api_usage WHERE created_at > NOW() - INTERVAL '7 days'
            GROUP BY agent ORDER BY calls DESC
        """)
    return {
        "users": [dict(r) for r in users],
        "usage_by_day": [{"day": str(r["day"]), "calls": r["calls"]} for r in usage_by_day],
        "usage_by_ecosystem": [dict(r) for r in usage_by_eco],
        "top_packages": [dict(r) for r in top_packages],
        "top_agents": [dict(r) for r in top_agents],
    }


@app.get("/.well-known/ai-plugin.json", tags=["discovery"])
async def ai_plugin():
    return {
        "schema_version": "v1",
        "name_for_human": "DepScope",
        "name_for_model": "depscope",
        "description_for_human": "Check package health, vulnerabilities, error fixes and stack compatibility before installing. 17 ecosystems, 14 MCP tools, 100% free.",
        "description_for_model": "Use DepScope to check if a software package is safe, maintained, and up-to-date before suggesting it to install. Supports 17 ecosystems: npm, pypi, cargo, go, composer, maven, nuget, rubygems, pub, hex, swift, cocoapods, cpan, hackage, cran, conda, homebrew. 14,700+ packages indexed, 402 vulnerabilities tracked. Three verticals on one API: (1) package health via GET /api/check/{ecosystem}/{package} for full health report with vulns+score+recommendation, GET /api/prompt/{ecosystem}/{package} for LLM-optimized plain text (saves ~74% tokens), GET /api/compare/{ecosystem}/pkg1,pkg2 to compare, GET /api/alternatives/{ecosystem}/{package} for replacements, POST /api/scan to audit dependency lists. (2) error -> fix resolution via POST /api/error/resolve with a stack trace, GET /api/error?code=X for lookups. (3) stack compatibility via GET /api/compat?packages=next@16,react@19 to verify a combo before upgrading. Also GET /api/bugs/{ecosystem}/{package} for non-CVE known bugs per version. No authentication required for public endpoints. Optional API keys for higher limits. Completely free.",
        "auth": {"type": "none"},
        "api": {"type": "openapi", "url": "https://depscope.dev/openapi.json"},
        "logo_url": "https://depscope.dev/logo.png",
        "contact_email": "depscope@cuttalo.com",
        "legal_info_url": "https://depscope.dev/terms",
    }


def _build_recommendation(pkg_data: dict, health: dict, vulns: list, requested_version: str = None) -> dict:
    issues = []
    action = "safe_to_use"

    critical = sum(1 for v in vulns if v.get("severity") == "critical")
    high = sum(1 for v in vulns if v.get("severity") == "high")

    # Priority order (last wins): low health < high vulns < deprecated < critical
    if health["score"] < 40:
        issues.append(f"Low health score ({health['score']}/100)")
        action = "use_with_caution"
    if high > 0:
        issues.append(f"{high} high severity vulnerabilities")
        action = "update_required"
    if pkg_data.get("deprecated"):
        issues.append("Package is deprecated")
        action = "find_alternative"
    if critical > 0:
        issues.append(f"{critical} critical vulnerabilities")
        action = "do_not_use"

    version_hint = None
    if vulns:
        fixed = [v.get("fixed_version") for v in vulns if v.get("fixed_version")]
        if fixed:
            version_hint = f"Update to >= {fixed[-1]} to fix known vulnerabilities"

    name = pkg_data.get("name", "")
    ver = pkg_data.get("latest_version", "")
    score = health["score"]

    # Fix 2: insufficient-data guard. Some ecosystems (Hackage, CPAN, CRAN, ...)
    # expose very little metadata; returning "safe_to_use" with a 40/100 score
    # and no description/license is dangerous for an autonomous agent. If we
    # have fewer than 3 positive signals, downgrade to "insufficient_data" so
    # the agent knows to verify manually. Only downgrade when the algorithm
    # didn't already flag a more serious issue.
    breakdown = health.get("breakdown", {}) if isinstance(health, dict) else {}
    maturity = breakdown.get("maturity", 0) or 0
    popularity = breakdown.get("popularity", 0) or 0
    community = breakdown.get("community", 0) or 0
    has_description = bool((pkg_data.get("description") or "").strip())
    has_license = bool((pkg_data.get("license") or "").strip())
    has_last_published = bool(pkg_data.get("last_published"))

    signal_count = sum([
        maturity >= 5,
        popularity >= 3,
        community >= 3,
        has_description,
        has_license,
        has_last_published,
    ])

    # Only apply the downgrade for actions where we haven't found a real problem.
    # If the package is already flagged do_not_use / update_required / find_alternative,
    # we keep the stronger signal.
    if signal_count < 3 and action in ("safe_to_use", "use_with_caution"):
        return {
            "action": "insufficient_data",
            "issues": ["Limited information available for this package"] + issues,
            "use_version": ver or None,
            "version_hint": None,
            "summary": f"{name} has limited data ({signal_count}/6 signals) — verify manually before use",
            "signals": {
                "maturity": maturity,
                "popularity": popularity,
                "community": community,
                "has_description": has_description,
                "has_license": has_license,
                "has_last_published": has_last_published,
                "count": signal_count,
            },
        }

    summaries = {
        "safe_to_use": f"{name}@{ver} is safe to use (health: {score}/100)",
        "update_required": f"{name}@{ver} has vulnerabilities — update to latest",
        "use_with_caution": f"{name}@{ver} low health ({score}/100) — consider alternatives",
        "find_alternative": f"{name} is deprecated — find an alternative",
        "do_not_use": f"{name} has critical vulnerabilities — do not use",
    }

    return {
        "action": action,
        "issues": issues,
        "use_version": ver,
        "version_hint": version_hint,
        "summary": summaries.get(action, f"{name}@{ver} — health: {score}/100"),
    }

def _detect_source(request: Request) -> str:
    """Detect if request comes from RapidAPI, GPT Store, MCP, or direct."""
    if not request:
        return "internal"
    if request.headers.get("X-RapidAPI-Proxy-Secret") or request.headers.get("X-RapidAPI-User"):
        return "rapidapi"
    ua = request.headers.get("User-Agent", "").lower()
    if "gptbot" in ua or "chatgpt-user" in ua:
        return "gpt_bot"
    if "chatgpt" in ua or "openai" in ua:
        return "gpt"
    if "claudebot" in ua:
        return "claude_bot"
    if "claude" in ua or "anthropic" in ua:
        return "claude"
    if "cursor" in ua:
        return "cursor"
    if "mcp" in ua or "depscope-mcp" in ua:
        return "mcp"
    if "python" in ua or "httpx" in ua or "aiohttp" in ua:
        return "sdk"
    if "node" in ua or "axios" in ua or "fetch" in ua:
        return "sdk"
    if not ua or ua == "": 
        return "unknown"
    return "browser"


def _derive_endpoint(path: str) -> str:
    """Normalize request.url.path into short endpoint label for analytics."""
    if not path:
        return "check"
    p = path.strip("/")
    if p.startswith("api/"):
        p = p[4:]
    # keep first 2 segments max (es. check, compare, prompt, error/resolve, scan, alternatives, licenses, tree, exists, badge)
    parts = p.split("/")
    head = parts[0] if parts else "check"
    # distinguish a few multi-segment endpoints that matter
    if head in ("error", "vulns", "versions", "badge", "admin") and len(parts) > 1:
        # only keep second segment if non-variable
        second = parts[1]
        if not any(c in second for c in (":", "{")) and second.isalpha():
            return f"{head}/{second}"[:50]
    return head[:50]


def _derive_session_id(ip: str, source: str, now: "datetime" = None) -> str:
    """Derive a short SHA256 session_id from ip + source + date_hour.
    Groups calls from same client into hourly session bucket.
    """
    import hashlib
    from datetime import datetime as _dt
    if now is None:
        now = _dt.utcnow()
    date_hour = now.strftime("%Y%m%d%H")
    raw = f"{ip}|{source}|{date_hour}".encode()
    return hashlib.sha256(raw).hexdigest()[:32]


async def _resolve_api_key_id(request: Request):
    """Best-effort: return api_keys.id for Bearer ds_live_/ds_test_ tokens, else None."""
    if not request:
        return None
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    key = auth[7:].strip()
    if not key.startswith("ds_") or key.startswith("ds_admin_"):
        return None
    import hashlib as _h
    key_hash = _h.sha256(key.encode()).hexdigest()
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM api_keys WHERE key_hash=$1 AND revoked_at IS NULL",
                key_hash,
            )
        return row["id"] if row else None
    except Exception:
        return None


def _log_usage(ecosystem: str, package: str, request: Request = None,
               response_time_ms: int = None, cache_hit: bool = False,
               status_code: int = 200, endpoint: str = None):
    async def _log():
        try:
            pool = await get_pool()
            ip = ua = source = country = ""
            ep = endpoint or "check"
            if request:
                ip = request.headers.get("CF-Connecting-IP", request.client.host if request.client else "")
                ua = request.headers.get("User-Agent", "")
                source = _detect_source(request)
                country = (request.headers.get("CF-IPCountry", "") or "")[:2].upper()
                # Override endpoint from path if not explicitly passed
                if endpoint is None:
                    try:
                        ep = _derive_endpoint(request.url.path)
                    except Exception:
                        ep = "check"
            # Skip our own infra
            if ip in EXCLUDED_IPS:
                return
            session_id = _derive_session_id(ip, source) if ip else None
            api_key_id = await _resolve_api_key_id(request)
            # Normalize country: CF sends "XX" or "T1" for Tor. Empty -> NULL
            country_val = country if country and len(country) == 2 and country.isalpha() else None
            async with pool.acquire() as conn:
                try:
                    await conn.execute(
                        """INSERT INTO api_usage
                           (endpoint, ecosystem, package_name, ip_address, user_agent, source,
                            country, response_time_ms, cache_hit, session_id, status_code, api_key_id)
                           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)""",
                        ep, ecosystem, package, ip, ua[:500], source,
                        country_val, response_time_ms, cache_hit, session_id, status_code, api_key_id,
                    )
                except Exception:
                    # Fallback su schema vecchio
                    await conn.execute(
                        "INSERT INTO api_usage (endpoint, ecosystem, package_name, ip_address, user_agent, source) VALUES ($1,$2,$3,$4,$5,$6)",
                        ep, ecosystem, package, ip, ua[:500], source,
                    )
        except Exception:
            pass
    asyncio.create_task(_log())




@app.get("/api/admin/sources", include_in_schema=False)
async def admin_sources(request: Request):
    """API usage breakdown by source (RapidAPI, GPT, Claude, MCP, browser, sdk)."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        by_source = await conn.fetch("""
            SELECT COALESCE(source, 'unknown') as source, COUNT(*) as calls
            FROM api_usage WHERE source != '' AND source IS NOT NULL
            GROUP BY source ORDER BY calls DESC
        """)
        by_source_today = await conn.fetch("""
            SELECT COALESCE(source, 'unknown') as source, COUNT(*) as calls
            FROM api_usage WHERE source != '' AND source IS NOT NULL
            AND created_at > NOW() - INTERVAL '1 day'
            GROUP BY source ORDER BY calls DESC
        """)
        by_source_week = await conn.fetch("""
            SELECT COALESCE(source, 'unknown') as source, COUNT(*) as calls
            FROM api_usage WHERE source != '' AND source IS NOT NULL
            AND created_at > NOW() - INTERVAL '7 days'
            GROUP BY source ORDER BY calls DESC
        """)
        rapidapi_users = await conn.fetch("""
            SELECT DISTINCT ip_address, user_agent, MAX(created_at) as last_seen
            FROM api_usage WHERE source = 'rapidapi'
            GROUP BY ip_address, user_agent ORDER BY last_seen DESC LIMIT 20
        """)
    return {
        "total": {r["source"]: r["calls"] for r in by_source},
        "today": {r["source"]: r["calls"] for r in by_source_today},
        "week": {r["source"]: r["calls"] for r in by_source_week},
        "rapidapi_users": [{"ip": r["ip_address"], "ua": r["user_agent"][:100], "last_seen": r["last_seen"].isoformat()} for r in rapidapi_users],
    }

@app.get("/openapi-gpt.json", include_in_schema=False)
async def openapi_for_gpt():
    """Cleaned OpenAPI spec for ChatGPT Actions."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "DepScope",
            "description": "Package Intelligence API for AI Agents. Check health, vulnerabilities, versions, find alternatives, search packages. Free, no auth.",
            "version": "0.2.0",
        },
        "servers": [{"url": "https://depscope.dev"}],
        "paths": {
            "/api/check/{ecosystem}/{package}": {
                "get": {
                    "operationId": "checkPackage",
                    "summary": "Full package health check with vulnerabilities and recommendation",
                    "parameters": [
                        {"name": "ecosystem", "in": "path", "required": True, "schema": {"type": "string", "enum": ["npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"]}},
                        {"name": "package", "in": "path", "required": True, "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "Full health report"}},
                }
            },
            "/api/latest/{ecosystem}/{package}": {
                "get": {
                    "operationId": "getLatestVersion",
                    "summary": "Get just the latest version number. Use before any install suggestion.",
                    "parameters": [
                        {"name": "ecosystem", "in": "path", "required": True, "schema": {"type": "string", "enum": ["npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"]}},
                        {"name": "package", "in": "path", "required": True, "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "Latest version and deprecation status"}},
                }
            },
            "/api/exists/{ecosystem}/{package}": {
                "get": {
                    "operationId": "checkExists",
                    "summary": "Does this package exist? Use before suggesting any install.",
                    "parameters": [
                        {"name": "ecosystem", "in": "path", "required": True, "schema": {"type": "string", "enum": ["npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"]}},
                        {"name": "package", "in": "path", "required": True, "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "Existence check result"}},
                }
            },
            "/api/search/{ecosystem}": {
                "get": {
                    "operationId": "searchPackages",
                    "summary": "Search packages by keyword. Use when user needs a package for a specific purpose.",
                    "parameters": [
                        {"name": "ecosystem", "in": "path", "required": True, "schema": {"type": "string", "enum": ["npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"]}},
                        {"name": "q", "in": "query", "required": True, "schema": {"type": "string"}, "description": "Search keywords"},
                        {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer", "default": 10}},
                    ],
                    "responses": {"200": {"description": "Search results"}},
                }
            },
            "/api/alternatives/{ecosystem}/{package}": {
                "get": {
                    "operationId": "getAlternatives",
                    "summary": "Get alternative packages for deprecated or unhealthy ones",
                    "parameters": [
                        {"name": "ecosystem", "in": "path", "required": True, "schema": {"type": "string", "enum": ["npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"]}},
                        {"name": "package", "in": "path", "required": True, "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "List of alternatives with reasons"}},
                }
            },
            "/api/compare/{ecosystem}/{packages_csv}": {
                "get": {
                    "operationId": "comparePackages",
                    "summary": "Compare 2-10 packages side by side with winner",
                    "parameters": [
                        {"name": "ecosystem", "in": "path", "required": True, "schema": {"type": "string", "enum": ["npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"]}},
                        {"name": "packages_csv", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Comma-separated names (express,fastify,hono)"},
                    ],
                    "responses": {"200": {"description": "Comparison with winner"}},
                }
            },
            "/api/now": {
                "get": {
                    "operationId": "getCurrentTime",
                    "summary": "Current UTC date and time",
                    "parameters": [],
                    "responses": {"200": {"description": "Current timestamp"}},
                }
            },
            "/api/vulns/{ecosystem}/{package}": {
                "get": {
                    "operationId": "getVulnerabilities",
                    "summary": "Known vulnerabilities for latest version",
                    "parameters": [
                        {"name": "ecosystem", "in": "path", "required": True, "schema": {"type": "string", "enum": ["npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"]}},
                        {"name": "package", "in": "path", "required": True, "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "Vulnerability list"}},
                }
            },
            "/api/breaking/{ecosystem}/{package}": {
                "get": {
                    "operationId": "getBreakingChanges",
                    "summary": "Verified breaking changes between major versions with migration hints. Call BEFORE suggesting a major-version bump.",
                    "parameters": [
                        {"name": "ecosystem", "in": "path", "required": True, "schema": {"type": "string", "enum": ["npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"]}},
                        {"name": "package", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "from_version", "in": "query", "required": False, "schema": {"type": "string"}, "description": "Optional starting major (e.g. '18', '14')."},
                        {"name": "to_version", "in": "query", "required": False, "schema": {"type": "string"}, "description": "Optional target major (e.g. '19', '15')."},
                    ],
                    "responses": {"200": {"description": "Breaking changes with migration_hint per entry"}},
                }
            },
            "/api/bugs/{ecosystem}/{package}": {
                "get": {
                    "operationId": "getKnownBugs",
                    "summary": "Non-CVE known bugs per package version (regressions, production incidents, edge cases not in CVE feeds).",
                    "parameters": [
                        {"name": "ecosystem", "in": "path", "required": True, "schema": {"type": "string", "enum": ["npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"]}},
                        {"name": "package", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "version", "in": "query", "required": False, "schema": {"type": "string"}, "description": "Filter to bugs affecting this version."},
                    ],
                    "responses": {"200": {"description": "Known bug list with fix_version when available"}},
                }
            },
            "/api/error/resolve": {
                "post": {
                    "operationId": "resolveError",
                    "summary": "POST an error message or stack trace; get a verified fix. Use instead of re-deriving diagnosis from scratch.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {"type": "string", "description": "Full error message or stack trace."},
                                        "context": {"type": "object", "description": "Optional runtime/version context."},
                                    },
                                    "required": ["error"],
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "Match status + solution"}},
                }
            },
            "/api/compat": {
                "get": {
                    "operationId": "checkCompatibility",
                    "summary": "Check whether a package stack is verified to work together. Returns verified | compatible | incompatible | warning | untested.",
                    "parameters": [
                        {"name": "stack", "in": "query", "required": True, "schema": {"type": "string"}, "description": "Comma-separated name@version pairs, e.g. 'next@15,react@19,prisma@6'."},
                    ],
                    "responses": {"200": {"description": "Compatibility verdict + similar verified stacks"}},
                }
            },
        },
    }

@app.get("/api/sitemap-packages", include_in_schema=False)
async def sitemap_packages(
    limit: int = 0,
    min_downloads: int = 0,
    order: str = "name",
):
    """Returns list of packages for sitemap generation.

    Query params:
      - limit: max rows (0 = unlimited)
      - min_downloads: only packages with >= N weekly downloads
      - order: "name" (alpha) | "downloads" (by weekly desc)
    """
    pool = await get_pool()
    order_clause = "downloads_weekly DESC, ecosystem, name" if order == "downloads" else "ecosystem, name"
    sql = f"""
        SELECT ecosystem, name, downloads_weekly, updated_at
        FROM packages
        WHERE downloads_weekly >= $1
        ORDER BY {order_clause}
    """
    if limit and limit > 0:
        sql += f" LIMIT {int(limit)}"
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, min_downloads)
    return [
        {
            "ecosystem": r["ecosystem"],
            "name": r["name"],
            "downloads_weekly": r["downloads_weekly"] or 0,
            "updated_at": (r["updated_at"].isoformat() if r["updated_at"] else None),
        }
        for r in rows
    ]


async def openapi_for_gpt():
    """Cleaned OpenAPI spec for ChatGPT Actions — only public API endpoints."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "DepScope",
            "description": "Package Intelligence API for AI Agents. Check health, vulnerabilities, versions before installing. Free, no auth.",
            "version": "0.2.0",
        },
        "servers": [{"url": "https://depscope.dev"}],
        "paths": {
            "/api/check/{ecosystem}/{package}": {
                "get": {
                    "operationId": "checkPackage",
                    "summary": "Full package health check",
                    "description": "Returns health score, vulnerabilities, versions, and recommendation for a package.",
                    "parameters": [
                        {"name": "ecosystem", "in": "path", "required": True, "schema": {"type": "string", "enum": ["npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"]}},
                        {"name": "package", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Package name (e.g. express, fastapi, serde, @anthropic-ai/sdk)"},
                    ],
                    "responses": {"200": {"description": "Package health report"}},
                }
            },
            "/api/compare/{ecosystem}/{packages_csv}": {
                "get": {
                    "operationId": "comparePackages",
                    "summary": "Compare multiple packages",
                    "description": "Compare 2-10 packages side by side. Returns ranked results with winner.",
                    "parameters": [
                        {"name": "ecosystem", "in": "path", "required": True, "schema": {"type": "string", "enum": ["npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"]}},
                        {"name": "packages_csv", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Comma-separated package names (e.g. express,fastify,hono)"},
                    ],
                    "responses": {"200": {"description": "Comparison results"}},
                }
            },
            "/api/health/{ecosystem}/{package}": {
                "get": {
                    "operationId": "getHealthScore",
                    "summary": "Quick health score",
                    "parameters": [
                        {"name": "ecosystem", "in": "path", "required": True, "schema": {"type": "string", "enum": ["npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"]}},
                        {"name": "package", "in": "path", "required": True, "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "Health score 0-100"}},
                }
            },
            "/api/vulns/{ecosystem}/{package}": {
                "get": {
                    "operationId": "getVulnerabilities",
                    "summary": "Known vulnerabilities",
                    "parameters": [
                        {"name": "ecosystem", "in": "path", "required": True, "schema": {"type": "string", "enum": ["npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"]}},
                        {"name": "package", "in": "path", "required": True, "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "Vulnerability list"}},
                }
            },
        },
    }


@app.get("/api/admin/stats", include_in_schema=False)
async def admin_stats_full(request: Request):
    """Admin only: full stats without threshold hiding."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        pkg_count = await conn.fetchval("SELECT COUNT(*) FROM packages")
        vuln_count = await conn.fetchval("SELECT COUNT(*) FROM vulnerabilities")
        usage_today = await conn.fetchval("SELECT COUNT(*) FROM api_usage WHERE created_at > NOW() - INTERVAL '1 day' AND user_agent NOT ILIKE '%node%' AND user_agent NOT ILIKE '%bot%' AND user_agent NOT ILIKE '%crawl%' AND user_agent NOT ILIKE '%spider%' AND user_agent NOT ILIKE '%GoogleOther%' AND user_agent != ''")
        usage_total = await conn.fetchval("SELECT COUNT(*) FROM api_usage WHERE user_agent NOT ILIKE '%node%' AND user_agent NOT ILIKE '%bot%' AND user_agent NOT ILIKE '%crawl%' AND user_agent NOT ILIKE '%spider%' AND user_agent NOT ILIKE '%GoogleOther%' AND user_agent != ''")
        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
    return {
        "packages_indexed": pkg_count,
        "vulnerabilities_tracked": vuln_count,
        "api_calls_today": usage_today,
        "api_calls_total": usage_total,
        "registered_users": users_count,
        "ecosystems": ["npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"],
    }


# ============================================================
# ENDPOINTS FOR AI AGENTS — what agents actually need
# ============================================================

@app.get("/api/latest/{ecosystem}/{package:path}", tags=["packages"])
async def get_latest_version(ecosystem: str, package: str, request: Request = None):
    """
    Just the latest version. Nothing else. Fastest possible response.
    Use this before suggesting any package install.
    """
    start = time.time()
    ecosystem = ecosystem.lower()
    cache_key = f"latest:{ecosystem}:{package}"
    cached = await cache_get(cache_key)
    if cached:
        _log_usage(ecosystem, package, request,
                   response_time_ms=int((time.time() - start) * 1000),
                   cache_hit=True, status_code=200, endpoint="latest")
        return cached

    pkg_data = await fetch_package(ecosystem, package)
    if not pkg_data:
        _log_usage(ecosystem, package, request,
                   response_time_ms=int((time.time() - start) * 1000),
                   cache_hit=False, status_code=404, endpoint="latest")
        raise HTTPException(404, f"Package '{package}' not found in {ecosystem}")

    result = {
        "package": package,
        "ecosystem": ecosystem,
        "latest": pkg_data.get("latest_version"),
        "deprecated": pkg_data.get("deprecated", False),
    }
    await cache_set(cache_key, result, ttl=3600)
    _log_usage(ecosystem, package, request,
               response_time_ms=int((time.time() - start) * 1000),
               cache_hit=False, status_code=200, endpoint="latest")
    return result


@app.get("/api/exists/{ecosystem}/{package:path}", tags=["packages"])
async def check_exists(ecosystem: str, package: str):
    """
    Does this package exist? Yes or no. Use before suggesting npm install X.
    """
    ecosystem = ecosystem.lower()
    cache_key = f"exists:{ecosystem}:{package}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    pkg_data = await fetch_package(ecosystem, package)
    result = {
        "package": package,
        "ecosystem": ecosystem,
        "exists": pkg_data is not None,
        "latest": pkg_data.get("latest_version") if pkg_data else None,
    }
    await cache_set(cache_key, result, ttl=3600)
    return result


@app.get("/api/now", tags=["public"])
async def get_current_time():
    """
    Current UTC time. Agents don't know what time it is.
    Also returns useful context: day of week, unix timestamp.
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return {
        "utc": now.isoformat(),
        "unix": int(now.timestamp()),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day": now.strftime("%A"),
        "timezone": "UTC",
    }


@app.get("/api/search/{ecosystem}", tags=["packages"])
async def search_packages(ecosystem: str, q: str = "", limit: int = 10):
    """
    Search packages by keyword. When user says 'I need an HTTP client for Python',
    the agent can search instead of hallucinating package names.
    """
    import aiohttp
    ecosystem = ecosystem.lower()
    if not q:
        raise HTTPException(400, "Query parameter 'q' required")
    if limit > 30:
        limit = 30

    results = []

    if ecosystem == "npm":
        url = f"https://registry.npmjs.org/-/v1/search?text={q}&size={limit}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for obj in data.get("objects", []):
                        p = obj.get("package", {})
                        results.append({
                            "name": p.get("name"),
                            "version": p.get("version"),
                            "description": p.get("description", ""),
                            "score": round(obj.get("score", {}).get("final", 0) * 100),
                        })

    elif ecosystem == "pypi":
        url = f"https://pypi.org/search/?q={q}&o="
        # PyPI doesn't have a JSON search API, use simple search
        # Fallback: search in our DB
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT name, latest_version, description, health_score
                FROM packages
                WHERE ecosystem = 'pypi' AND (name ILIKE $1 OR description ILIKE $1)
                ORDER BY health_score DESC NULLS LAST
                LIMIT $2
            """, f"%{q}%", limit)
            results = [{"name": r["name"], "version": r["latest_version"],
                       "description": r["description"] or "", "score": r["health_score"] or 0} for r in rows]

    elif ecosystem == "cargo":
        url = f"https://crates.io/api/v1/crates?q={q}&per_page={limit}"
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "DepScope/0.1 (https://depscope.dev)"}
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for c in data.get("crates", []):
                        results.append({
                            "name": c.get("name"),
                            "version": c.get("newest_version"),
                            "description": c.get("description", ""),
                            "downloads": c.get("downloads", 0),
                        })

    return {
        "ecosystem": ecosystem,
        "query": q,
        "count": len(results),
        "results": results,
    }


# Curated alternatives used by /api/alternatives and by /api/check to enrich
# `recommendation.alternatives` inline when action == "find_alternative".
_PACKAGE_ALTERNATIVES: dict = {
        "npm": {
            "request": [{"name": "axios", "reason": "Modern HTTP client with promises"}, {"name": "node-fetch", "reason": "Lightweight, fetch API compatible"}, {"name": "got", "reason": "Feature-rich, streaming support"}],
            "moment": [{"name": "dayjs", "reason": "2KB, same API as moment"}, {"name": "date-fns", "reason": "Modular, tree-shakeable"}, {"name": "luxon", "reason": "By moment team, immutable"}],
            "underscore": [{"name": "lodash", "reason": "Superset of underscore"}, {"name": "ramda", "reason": "Functional programming focused"}],
            "jade": [{"name": "pug", "reason": "Jade was renamed to Pug"}],
            "coffee-script": [{"name": "typescript", "reason": "Type-safe superset of JavaScript"}],
            "node-uuid": [{"name": "uuid", "reason": "node-uuid was renamed to uuid"}],
            "nomnom": [{"name": "commander", "reason": "Most popular CLI parser"}, {"name": "yargs", "reason": "Feature-rich CLI parser"}],
            "colors": [{"name": "chalk", "reason": "Safe, no supply chain risk"}, {"name": "picocolors", "reason": "Fastest, zero deps"}],
            "querystring": [{"name": "qs", "reason": "More features, actively maintained"}, {"name": "URLSearchParams", "reason": "Built-in, no dependency needed"}],
            "express": [{"name": "fastify", "reason": "2-3x faster, schema validation built-in"}, {"name": "hono", "reason": "Ultra-light, edge/serverless ready"}],
            "webpack": [{"name": "vite", "reason": "Lightning fast HMR, ESM native"}, {"name": "esbuild", "reason": "100x faster builds"}, {"name": "rollup", "reason": "Tree-shaking pioneer"}, {"name": "parcel", "reason": "Zero config bundler"}],
            "gulp": [{"name": "npm-scripts", "reason": "Built-in, no extra dependency"}, {"name": "vite", "reason": "Modern build tool with plugins"}],
            "grunt": [{"name": "npm-scripts", "reason": "Built-in, no extra dependency"}, {"name": "vite", "reason": "Modern build tool"}],
            "bower": [{"name": "npm", "reason": "Standard package manager"}, {"name": "yarn", "reason": "Fast, reliable package manager"}],
            "left-pad": [{"name": "String.padStart", "reason": "Built-in JavaScript method, no dependency needed"}],
            "async": [{"name": "native-async-await", "reason": "Built-in language feature since ES2017"}],
            "bluebird": [{"name": "native-Promise", "reason": "Built-in Promise is now fast enough"}],
            "node-sass": [{"name": "sass", "reason": "Dart Sass, official maintained implementation"}],
            "tslint": [{"name": "eslint", "reason": "With @typescript-eslint plugin, TSLint is deprecated"}],
            "istanbul": [{"name": "nyc", "reason": "Istanbul CLI wrapper"}, {"name": "c8", "reason": "Native V8 coverage"}, {"name": "vitest", "reason": "Built-in coverage support"}],
            "mocha": [{"name": "vitest", "reason": "Vite-native, fast, ESM"}, {"name": "jest", "reason": "All-in-one test framework"}],
            "should": [{"name": "chai", "reason": "Popular assertion library"}, {"name": "jest", "reason": "Built-in expect assertions"}],
            "superagent": [{"name": "axios", "reason": "More popular, promise-based"}, {"name": "got", "reason": "Feature-rich Node.js HTTP"}, {"name": "node-fetch", "reason": "Fetch API for Node.js"}],
            "body-parser": [{"name": "express.json", "reason": "Built-in since Express 4.16, no extra package needed"}],
            "connect": [{"name": "express", "reason": "Built on Connect with more features"}, {"name": "fastify", "reason": "Modern, faster alternative"}],
            "forever": [{"name": "pm2", "reason": "Process manager with monitoring"}, {"name": "systemd", "reason": "OS-level process management"}],
            "nodemon": [{"name": "tsx", "reason": "TypeScript execute with watch mode"}, {"name": "node --watch", "reason": "Built-in Node.js watch mode since v18.11"}],
            "phantomjs": [{"name": "puppeteer", "reason": "Chrome DevTools Protocol"}, {"name": "playwright", "reason": "Multi-browser automation"}],
            "nightmare": [{"name": "puppeteer", "reason": "Chrome DevTools Protocol"}, {"name": "playwright", "reason": "Multi-browser, modern API"}],
            "cheerio": [{"name": "happy-dom", "reason": "Fast DOM implementation"}, {"name": "linkedom", "reason": "Lightweight DOM for server"}],
            "passport": [{"name": "lucia", "reason": "Modern auth library"}, {"name": "better-auth", "reason": "Simple, type-safe auth"}, {"name": "next-auth", "reason": "Auth.js for Next.js apps"}],
            "knex": [{"name": "drizzle-orm", "reason": "Type-safe, lightweight ORM"}, {"name": "prisma", "reason": "Auto-generated types, migrations"}, {"name": "kysely", "reason": "Type-safe SQL query builder"}],
            "sequelize": [{"name": "prisma", "reason": "Modern ORM with migrations"}, {"name": "drizzle-orm", "reason": "Lightweight, type-safe"}, {"name": "typeorm", "reason": "Decorator-based ORM"}],
            "typeorm": [{"name": "prisma", "reason": "Better DX, auto migrations"}, {"name": "drizzle-orm", "reason": "Lightweight, SQL-like syntax"}],
            "mongoose": [{"name": "prisma", "reason": "Works with MongoDB, type-safe"}, {"name": "mongoist", "reason": "Lightweight MongoDB driver wrapper"}],
            "lodash": [{"name": "es-toolkit", "reason": "Modern, tree-shakeable, 2-3x faster"}, {"name": "radash", "reason": "Modern utility library, TypeScript-first"}],
            "chalk": [{"name": "picocolors", "reason": "14x smaller, zero deps, faster"}],
            "winston": [{"name": "pino", "reason": "5x faster JSON logger"}, {"name": "consola", "reason": "Elegant console wrapper"}],
            "uuid": [{"name": "nanoid", "reason": "2x faster, URL-friendly, smaller"}, {"name": "crypto.randomUUID", "reason": "Built-in since Node.js 19"}],
            "dotenv": [{"name": "dotenvy", "reason": "Stricter, fails on missing vars"}, {"name": "node --env-file", "reason": "Built-in since Node.js 20.6"}],
            "classnames": [{"name": "clsx", "reason": "228B smaller, faster, same API"}],
            "glob": [{"name": "fast-glob", "reason": "2-3x faster, more features"}, {"name": "tinyglobby", "reason": "Minimal, fast glob"}],
            "rimraf": [{"name": "fs.rm", "reason": "Built-in since Node.js 14, recursive option"}],
            "cross-env": [{"name": "node --env-file", "reason": "Built-in since Node.js 20.6"}],
            "axios": [{"name": "ky", "reason": "Tiny, modern fetch wrapper"}, {"name": "ofetch", "reason": "Better defaults, works everywhere"}],
            "react-helmet": [{"name": "react-helmet-async", "reason": "Async-safe, maintained fork"}],
            "enzyme": [{"name": "testing-library", "reason": "Tests behavior not implementation"}],
            "redux": [{"name": "zustand", "reason": "Simpler API, less boilerplate"}, {"name": "jotai", "reason": "Atomic state, minimal API"}],
            "formik": [{"name": "react-hook-form", "reason": "Better performance, less re-renders"}],
            "styled-components": [{"name": "tailwindcss", "reason": "Utility-first, better perf"}, {"name": "vanilla-extract", "reason": "Zero-runtime CSS-in-TS"}],
            "react-router": [{"name": "tanstack-router", "reason": "Type-safe, built-in search params"}],
        },
        "pypi": {
            "nose": [{"name": "pytest", "reason": "Modern, plugin ecosystem"}, {"name": "unittest", "reason": "Built-in, no dependency"}],
            "pycrypto": [{"name": "pycryptodome", "reason": "Maintained fork of pycrypto"}, {"name": "cryptography", "reason": "Modern, well-maintained"}],
            "optparse": [{"name": "argparse", "reason": "Built-in replacement"}, {"name": "click", "reason": "Decorator-based, composable"}, {"name": "typer", "reason": "Type hints based, modern"}],
            "urllib2": [{"name": "requests", "reason": "Human-friendly HTTP"}, {"name": "httpx", "reason": "Async support, modern"}],
            "beautifulsoup": [{"name": "beautifulsoup4", "reason": "Updated version"}, {"name": "lxml", "reason": "Faster parsing"}, {"name": "selectolax", "reason": "Fastest HTML parser"}],
            "PIL": [{"name": "Pillow", "reason": "Maintained fork of PIL"}],
            "fabric": [{"name": "paramiko", "reason": "SSH2 protocol library"}, {"name": "invoke", "reason": "Task execution tool"}],
            "celery": [{"name": "dramatiq", "reason": "Simpler, reliable task processing"}, {"name": "huey", "reason": "Lightweight task queue"}, {"name": "arq", "reason": "Async Redis queue, fast"}],
            "flask-restful": [{"name": "flask-smorest", "reason": "Modern REST API with marshmallow"}, {"name": "fastapi", "reason": "Async, auto-docs, type hints"}],
            "django-rest-framework": [{"name": "django-ninja", "reason": "FastAPI-like DX for Django"}, {"name": "fastapi", "reason": "Async-native, auto OpenAPI"}],
            "pipenv": [{"name": "poetry", "reason": "Better dependency resolution"}, {"name": "uv", "reason": "10-100x faster, Rust-based"}, {"name": "pdm", "reason": "PEP 582 support, modern"}],
            "setuptools": [{"name": "hatch", "reason": "Modern Python project manager"}, {"name": "flit", "reason": "Simple pure Python packages"}, {"name": "poetry", "reason": "All-in-one dependency management"}],
            "virtualenv": [{"name": "venv", "reason": "Built-in since Python 3.3"}, {"name": "uv", "reason": "Ultra-fast venv creation"}],
            "pylint": [{"name": "ruff", "reason": "100x faster, Rust-based linter"}, {"name": "flake8", "reason": "Modular, plugin ecosystem"}],
            "flake8": [{"name": "ruff", "reason": "100x faster, drop-in replacement"}],
            "black": [{"name": "ruff format", "reason": "Integrated with ruff, much faster"}],
            "isort": [{"name": "ruff", "reason": "Built-in import sorting, 100x faster"}],
            "autopep8": [{"name": "ruff format", "reason": "Faster, more consistent"}, {"name": "black", "reason": "Opinionated, widely adopted"}],
            "requests": [{"name": "httpx", "reason": "Async support, HTTP/2, modern API"}, {"name": "urllib3", "reason": "Lower-level, more control"}],
            "flask": [{"name": "fastapi", "reason": "Async, auto-docs, type validation"}, {"name": "litestar", "reason": "High-performance ASGI framework"}],
            "django": [{"name": "fastapi", "reason": "Lighter, async-native, faster APIs"}, {"name": "litestar", "reason": "Full-featured ASGI framework"}],
            "sqlalchemy": [{"name": "tortoise-orm", "reason": "Async-native ORM"}, {"name": "peewee", "reason": "Simple, lightweight ORM"}],
            "boto3": [{"name": "aiobotocore", "reason": "Async AWS SDK"}, {"name": "s3fs", "reason": "Pythonic S3 file interface"}],
            "pyyaml": [{"name": "ruamel.yaml", "reason": "Round-trip YAML, preserves comments"}],
            "python-dotenv": [{"name": "pydantic-settings", "reason": "Type-safe env config with validation"}],
            "unittest": [{"name": "pytest", "reason": "Less boilerplate, better assertions, plugins"}],
            "logging": [{"name": "loguru", "reason": "Zero-config, better formatting"}, {"name": "structlog", "reason": "Structured logging, context binding"}],
            "argparse": [{"name": "click", "reason": "Decorator-based, composable"}, {"name": "typer", "reason": "Type hints based, auto-help"}],
            "scrapy": [{"name": "httpx", "reason": "Async HTTP + BeautifulSoup4"}, {"name": "playwright", "reason": "JS-rendered pages"}],
            "tensorflow": [{"name": "pytorch", "reason": "More Pythonic, research standard"}, {"name": "jax", "reason": "Google XLA, functional API"}],
        },
        "cargo": {
            "failure": [{"name": "anyhow", "reason": "Simpler error handling"}, {"name": "thiserror", "reason": "Derive macro for Error trait"}],
            "iron": [{"name": "actix-web", "reason": "High performance"}, {"name": "axum", "reason": "Tokio ecosystem, ergonomic"}, {"name": "rocket", "reason": "Ergonomic, attribute macros"}],
            "rustc-serialize": [{"name": "serde", "reason": "De facto standard for serialization"}],
            "hyper": [{"name": "reqwest", "reason": "Higher-level HTTP client"}, {"name": "axum", "reason": "Web framework built on hyper"}],
            "nickel": [{"name": "actix-web", "reason": "High performance async"}, {"name": "axum", "reason": "Tokio-native, modular"}, {"name": "rocket", "reason": "Ergonomic web framework"}],
            "mio": [{"name": "tokio", "reason": "Full async runtime, built on mio"}],
            "lazy_static": [{"name": "once_cell", "reason": "More flexible, in std since 1.80"}, {"name": "std::sync::LazyLock", "reason": "In std since Rust 1.80"}],
            "error-chain": [{"name": "anyhow", "reason": "Simpler, more ergonomic"}, {"name": "thiserror", "reason": "Derive Error for custom types"}],
            "structopt": [{"name": "clap", "reason": "structopt merged into clap v3+"}],
            "warp": [{"name": "axum", "reason": "More flexible, better ecosystem"}, {"name": "actix-web", "reason": "Higher performance"}],
            "tide": [{"name": "axum", "reason": "More active development"}, {"name": "actix-web", "reason": "Mature, high performance"}],
            "log": [{"name": "tracing", "reason": "Structured, async-aware logging"}],
            "env_logger": [{"name": "tracing-subscriber", "reason": "Works with tracing, more features"}],
            "native-tls": [{"name": "rustls", "reason": "Pure Rust, no OpenSSL dependency"}],
            "num-cpus": [{"name": "std::thread::available_parallelism", "reason": "In std since Rust 1.59"}],
        },
}


def _get_alternatives_sync(ecosystem: str, package: str) -> list[dict]:
    """Synchronous lookup against the curated alternatives map.

    Used by `_fetch_full_package` to enrich `recommendation.alternatives`
    inline so AI agents don't need a second round-trip to /api/alternatives.
    """
    return list(_PACKAGE_ALTERNATIVES.get((ecosystem or "").lower(), {}).get(package or "", []))


@app.get("/api/alternatives/{ecosystem}/{package:path}", tags=["packages"])
async def get_alternatives(ecosystem: str, package: str):
    """
    What to use instead of a deprecated/unhealthy package.
    AI agents need this when they suggest something deprecated.
    """
    ecosystem = ecosystem.lower()

    # Check if package is deprecated first
    pkg_data = await fetch_package(ecosystem, package)
    is_deprecated = pkg_data.get("deprecated", False) if pkg_data else False

    from api.verticals import get_alternatives as _get_alts_db
    known = await _get_alts_db(ecosystem, package)

    # If not in our curated DB, try to find similar packages via search (npm only)
    if not known and ecosystem == "npm":
        # Get package description and search for similar
        if pkg_data and pkg_data.get("description"):
            desc = pkg_data["description"]
            keywords = desc.split()[:3]
            query = " ".join(keywords)
            search_result = await search_packages(ecosystem, q=query, limit=3)
            known = [{"name": r["name"], "reason": r.get("description", "")} for r in search_result.get("results", []) if r["name"] != package]

    return {
        "package": package,
        "ecosystem": ecosystem,
        "deprecated": is_deprecated,
        "deprecated_message": pkg_data.get("deprecated_message") if pkg_data else None,
        "alternatives": known,
        "note": "Alternatives are curated suggestions. Always verify they fit your use case." if known else "No known alternatives in our database yet.",
    }


@app.post("/api/track", tags=["public"])
async def track_pageview(request: Request):
    """Lightweight page view tracking. No cookies, no personal data."""
    try:
        body = await request.json()
        path = body.get("path", "/")[:500]
        referrer = body.get("referrer", "")[:500]
        ip = request.headers.get("CF-Connecting-IP", request.client.host if request.client else "")
        ua = request.headers.get("User-Agent", "")[:500]

        # Skip bots
        bot_patterns = ["bot", "crawl", "spider", "Googlebot", "ClaudeBot", "Bingbot", "facebookexternalhit", "Bytespider", "Yandex", "Slurp", "DuckDuckBot", "Applebot"]
        if any(p.lower() in ua.lower() for p in bot_patterns):
            return {"ok": True}
        country = request.headers.get("CF-IPCountry", "")

        if ip in EXCLUDED_IPS:
            return {"ok": True}
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO page_views (path, referrer, ip_address, user_agent, country) VALUES ($1, $2, $3, $4, $5)",
                path, referrer, ip, ua, country,
            )
    except Exception:
        pass
    return {"ok": True}


@app.get("/api/admin/pageviews", include_in_schema=False)
async def admin_pageviews(request: Request):
    """Admin: page view analytics."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")

    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM page_views")
        today = await conn.fetchval("SELECT COUNT(*) FROM page_views WHERE created_at > CURRENT_DATE")
        unique_today = await conn.fetchval("SELECT COUNT(DISTINCT ip_address) FROM page_views WHERE created_at > CURRENT_DATE")

        by_page = await conn.fetch("""
            SELECT path, COUNT(*) as views FROM page_views
            WHERE created_at > NOW() - INTERVAL '7 days'
            GROUP BY path ORDER BY views DESC LIMIT 20
        """)

        by_day = await conn.fetch("""
            SELECT DATE(created_at) as day, COUNT(*) as views, COUNT(DISTINCT ip_address) as unique_visitors
            FROM page_views WHERE created_at > NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at) ORDER BY day
        """)

        by_country = await conn.fetch("""
            SELECT country, COUNT(*) as views FROM page_views
            WHERE created_at > NOW() - INTERVAL '7 days' AND country != ''
            GROUP BY country ORDER BY views DESC LIMIT 15
        """)

        by_referrer = await conn.fetch("""
            SELECT referrer, COUNT(*) as views FROM page_views
            WHERE created_at > NOW() - INTERVAL '7 days' AND referrer != '' AND referrer NOT LIKE '%depscope%'
            GROUP BY referrer ORDER BY views DESC LIMIT 15
        """)

    return {
        "total": total,
        "today": today,
        "unique_today": unique_today,
        "by_page": [{"path": r["path"], "views": r["views"]} for r in by_page],
        "by_day": [{"day": str(r["day"]), "views": r["views"], "unique": r["unique_visitors"]} for r in by_day],
        "by_country": [{"country": r["country"], "views": r["views"]} for r in by_country],
        "by_referrer": [{"referrer": r["referrer"], "views": r["views"]} for r in by_referrer],
    }




@app.get("/api/admin/charts", include_in_schema=False)
async def admin_charts(request: Request):
    """Admin: chart data for dashboard graphs."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")

    pool = await get_pool()
    async with pool.acquire() as conn:
        pv_hourly = await conn.fetch(
            "SELECT date_trunc('hour', created_at) as hour, COUNT(*) as views, "
            "COUNT(DISTINCT ip_address) as unique_visitors "
            "FROM page_views WHERE created_at > NOW() - INTERVAL '3 days' "
            "GROUP BY hour ORDER BY hour"
        )

        pv_daily = await conn.fetch(
            "SELECT DATE(created_at) as day, COUNT(*) as views, "
            "COUNT(DISTINCT ip_address) as unique_visitors "
            "FROM page_views GROUP BY day ORDER BY day"
        )

        api_hourly = await conn.fetch(
            "SELECT date_trunc('hour', created_at) as hour, COUNT(*) as calls "
            "FROM api_usage WHERE created_at > NOW() - INTERVAL '3 days' "
            "AND user_agent NOT ILIKE '%node%' AND user_agent NOT ILIKE '%bot%' "
            "GROUP BY hour ORDER BY hour"
        )

        api_daily = await conn.fetch(
            "SELECT DATE(created_at) as day, COUNT(*) as calls "
            "FROM api_usage WHERE user_agent NOT ILIKE '%node%' AND user_agent NOT ILIKE '%bot%' "
            "GROUP BY day ORDER BY day"
        )

        sources_raw = await conn.fetch(
            "SELECT DATE(created_at) as day, source, COUNT(*) as cnt "
            "FROM api_usage WHERE source != '' AND source IS NOT NULL "
            "GROUP BY day, source ORDER BY day"
        )

        eco_raw = await conn.fetch(
            "SELECT DATE(created_at) as day, ecosystem, COUNT(*) as cnt "
            "FROM api_usage WHERE user_agent NOT ILIKE '%node%' "
            "AND ecosystem IS NOT NULL AND ecosystem != '' "
            "GROUP BY day, ecosystem ORDER BY day"
        )

        countries_tl = await conn.fetch(
            "SELECT DATE(created_at) as day, COUNT(DISTINCT country) as countries "
            "FROM page_views WHERE country != '' AND country IS NOT NULL "
            "GROUP BY day ORDER BY day"
        )

    sources_by_day: dict = {}
    for r in sources_raw:
        d = str(r["day"])
        if d not in sources_by_day:
            sources_by_day[d] = {"day": d}
        sources_by_day[d][r["source"]] = r["cnt"]
    sources_daily = list(sources_by_day.values())

    eco_by_day: dict = {}
    for r in eco_raw:
        d = str(r["day"])
        if d not in eco_by_day:
            eco_by_day[d] = {"day": d}
        eco_by_day[d][r["ecosystem"]] = r["cnt"]
    ecosystems_daily = list(eco_by_day.values())

    return {
        "pageviews_hourly": [
            {"hour": r["hour"].strftime("%Y-%m-%dT%H:%M"), "views": r["views"], "unique": r["unique_visitors"]}
            for r in pv_hourly
        ],
        "pageviews_daily": [
            {"day": str(r["day"]), "views": r["views"], "unique": r["unique_visitors"]}
            for r in pv_daily
        ],
        "api_calls_hourly": [
            {"hour": r["hour"].strftime("%Y-%m-%dT%H:%M"), "calls": r["calls"]}
            for r in api_hourly
        ],
        "api_calls_daily": [
            {"day": str(r["day"]), "calls": r["calls"]}
            for r in api_daily
        ],
        "sources_daily": sources_daily,
        "ecosystems_daily": ecosystems_daily,
        "countries_timeline": [
            {"day": str(r["day"]), "countries": r["countries"]}
            for r in countries_tl
        ],
    }

@app.get("/badge/{ecosystem}/{package:path}", tags=["badges"])
async def package_badge(ecosystem: str, package: str):
    """Generate SVG badge for README embedding. Like shields.io but for package health."""
    from fastapi.responses import Response

    ecosystem = ecosystem.lower()
    cache_key = f"badge:{ecosystem}:{package}"
    cached = await cache_get(cache_key)

    if cached:
        return Response(content=cached["svg"], media_type="image/svg+xml",
                       headers={"Cache-Control": "public, max-age=3600"})

    pkg_data = await fetch_package(ecosystem, package)
    if not pkg_data:
        svg = _make_badge(package, "not found", "#94a3b8")
        return Response(content=svg, media_type="image/svg+xml")

    latest = pkg_data.get("latest_version", "?")
    vulns = await fetch_vulnerabilities(ecosystem, package, latest_version=latest)
    health = calculate_health_score(pkg_data, vulns)
    score = health["score"]

    if score >= 80:
        color = "#22c55e"
        label = "healthy"
    elif score >= 60:
        color = "#eab308"
        label = "moderate"
    elif score >= 40:
        color = "#f97316"
        label = "caution"
    else:
        color = "#ef4444"
        label = "critical"

    if pkg_data.get("deprecated"):
        color = "#ef4444"
        label = "deprecated"

    svg = _make_badge(package, f"{score}/100 {label}", color)
    await cache_set(cache_key, {"svg": svg}, ttl=3600)

    _log_usage(ecosystem, package)
    return Response(content=svg, media_type="image/svg+xml",
                   headers={"Cache-Control": "public, max-age=3600"})


@app.get("/badge/{ecosystem}/{package:path}/score", tags=["badges"])
async def package_badge_score_only(ecosystem: str, package: str):
    """Minimal badge with just the score."""
    from fastapi.responses import Response

    ecosystem = ecosystem.lower()
    pkg_data = await fetch_package(ecosystem, package)
    if not pkg_data:
        svg = _make_badge_mini("?", "#94a3b8")
        return Response(content=svg, media_type="image/svg+xml")

    latest = pkg_data.get("latest_version", "?")
    vulns = await fetch_vulnerabilities(ecosystem, package, latest_version=latest)
    health = calculate_health_score(pkg_data, vulns)
    score = health["score"]
    color = "#22c55e" if score >= 80 else "#eab308" if score >= 60 else "#f97316" if score >= 40 else "#ef4444"

    svg = _make_badge_mini(str(score), color)
    return Response(content=svg, media_type="image/svg+xml",
                   headers={"Cache-Control": "public, max-age=3600"})


def _make_badge(label: str, value: str, color: str) -> str:
    label_w = len(label) * 6.5 + 12
    value_w = len(value) * 6.5 + 12
    total_w = label_w + value_w

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="20" role="img">
  <title>{label}: {value}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r"><rect width="{total_w}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_w}" height="20" fill="#555"/>
    <rect x="{label_w}" width="{value_w}" height="20" fill="{color}"/>
    <rect width="{total_w}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="11">
    <text x="{label_w/2}" y="14" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="{label_w/2}" y="13" fill="#fff">{label}</text>
    <text x="{label_w + value_w/2}" y="14" fill="#010101" fill-opacity=".3">{value}</text>
    <text x="{label_w + value_w/2}" y="13" fill="#fff">{value}</text>
  </g>
</svg>'''


def _make_badge_mini(score: str, color: str) -> str:
    w = len(score) * 7 + 16
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="20" role="img">
  <rect width="{w}" height="20" rx="3" fill="{color}"/>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="{w/2}" y="14">{score}</text>
  </g>
</svg>'''


@app.get("/api/savings", tags=["public"])
async def get_savings():
    """Real-time token and energy savings calculator based on actual API calls."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Chiamate reali (no bot, no cron)
        total_real = await conn.fetchval(
            "SELECT COUNT(*) FROM api_usage WHERE user_agent NOT ILIKE '%node%' AND user_agent NOT ILIKE '%bot%' AND user_agent NOT ILIKE '%crawl%' AND user_agent NOT ILIKE '%spider%' AND user_agent NOT ILIKE '%GoogleOther%' AND user_agent != ''"
        )
        today_real = await conn.fetchval(
            "SELECT COUNT(*) FROM api_usage WHERE created_at > CURRENT_DATE AND user_agent NOT ILIKE '%node%' AND user_agent NOT ILIKE '%bot%' AND user_agent NOT ILIKE '%crawl%' AND user_agent NOT ILIKE '%spider%' AND user_agent NOT ILIKE '%GoogleOther%' AND user_agent != ''"
        )

    tokens_without = 8500
    tokens_with = 800
    tokens_saved_per = tokens_without - tokens_with
    cost_per_million = 5.0
    wh_per_1000_tokens = 0.006

    total_tokens_saved = total_real * tokens_saved_per
    total_cost_saved = (total_tokens_saved / 1_000_000) * cost_per_million
    total_energy_wh = (total_tokens_saved / 1000) * wh_per_1000_tokens
    total_co2_g = total_energy_wh * 0.233  # grams CO2 per Wh (EU avg)
    time_saved_seconds = total_real * 12

    today_tokens_saved = today_real * tokens_saved_per
    today_cost_saved = (today_tokens_saved / 1_000_000) * cost_per_million
    today_energy_wh = (today_tokens_saved / 1000) * wh_per_1000_tokens

    return {
        "realtime": {
            "total_checks": total_real,
            "today_checks": today_real,
            "tokens_saved": total_tokens_saved,
            "tokens_saved_today": today_tokens_saved,
            "cost_saved_usd": round(total_cost_saved, 4),
            "cost_saved_today_usd": round(today_cost_saved, 4),
            "energy_saved_wh": round(total_energy_wh, 2),
            "energy_saved_today_wh": round(today_energy_wh, 2),
            "co2_saved_grams": round(total_co2_g, 2),
            "time_saved_seconds": time_saved_seconds,
        },
        "per_check": {
            "tokens_without": tokens_without,
            "tokens_with": tokens_with,
            "tokens_saved": tokens_saved_per,
            "efficiency_pct": 90.6,
            "cost_saved_usd": round((tokens_saved_per / 1_000_000) * cost_per_million, 4),
            "energy_saved_wh": round((tokens_saved_per / 1000) * wh_per_1000_tokens, 6),
        },
        "projection": {
            "note": "If all 5M AI coding agents used DepScope",
            "daily_checks": 50_000_000,
            "annual_mwh": 843,
            "annual_co2_tonnes": 196,
            "annual_cost_saved_usd": 702_625_000,
        },
    }

async def get_savings():
    """Calculate token and cost savings from using DepScope."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        total_checks = await conn.fetchval(
            "SELECT COUNT(*) FROM api_usage WHERE ip_address NOT IN ('127.0.0.1','::1','10.10.0.140','10.10.0.1','91.134.4.25')"
        )

    tokens_without = 8500   # avg tokens per check without DepScope
    tokens_with = 800       # avg tokens per check with DepScope
    tokens_saved_per = tokens_without - tokens_with
    cost_per_million = 5.0  # blended cost per 1M tokens

    total_tokens_saved = total_checks * tokens_saved_per
    total_cost_saved = (total_tokens_saved / 1_000_000) * cost_per_million
    time_saved_seconds = total_checks * 12  # ~12 sec saved per check (no web search)

    return {
        "total_checks": total_checks,
        "tokens_per_check_without": tokens_without,
        "tokens_per_check_with": tokens_with,
        "tokens_saved_per_check": tokens_saved_per,
        "total_tokens_saved": total_tokens_saved,
        "total_cost_saved_usd": round(total_cost_saved, 2),
        "time_saved_seconds": time_saved_seconds,
        "time_saved_human": f"{time_saved_seconds // 3600}h {(time_saved_seconds % 3600) // 60}m",
        "efficiency_gain_pct": round((tokens_saved_per / tokens_without) * 100, 1),
    }


# ═══════════════════════════════════════════════════════════════
# Agent Marketing System
# ═══════════════════════════════════════════════════════════════

@app.get("/api/admin/agent/rules", include_in_schema=False)
async def get_agent_rules(request: Request):
    """Get all active agent rules."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM agent_rules WHERE active = true ORDER BY priority, category")
    return [dict(r) for r in rows]

@app.post("/api/admin/agent/rules", include_in_schema=False)
async def add_agent_rule(request: Request):
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    body = await request.json()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO agent_rules (rule, category, priority) VALUES ($1, $2, $3)",
            body["rule"], body.get("category", "general"), body.get("priority", 5))
    return {"ok": True}

@app.delete("/api/admin/agent/rules/{rule_id}", include_in_schema=False)
async def delete_agent_rule(rule_id: int, request: Request):
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE agent_rules SET active = false WHERE id = $1", rule_id)
    return {"ok": True}

@app.get("/api/admin/agent/plan", include_in_schema=False)
async def get_agent_plan(request: Request):
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM agent_plan ORDER BY priority, timeframe, created_at")
    return [dict(r) for r in rows]

@app.post("/api/admin/agent/plan", include_in_schema=False)
async def add_plan_action(request: Request):
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    body = await request.json()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO agent_plan (action, category, timeframe, priority) VALUES ($1, $2, $3, $4)",
            body["action"], body.get("category", "general"), body.get("timeframe", "short"), body.get("priority", 5))
    return {"ok": True}

@app.put("/api/admin/agent/plan/{plan_id}", include_in_schema=False)
async def update_plan(plan_id: int, request: Request):
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    body = await request.json()
    pool = await get_pool()
    async with pool.acquire() as conn:
        sets = []
        vals = []
        i = 1
        for k in ["status", "result"]:
            if k in body:
                sets.append(f"{k} = ${i}")
                vals.append(body[k])
                i += 1
        if "status" in body and body["status"] == "completed":
            sets.append("completed_at = NOW()")
        if not sets:
            return {"ok": False, "error": "nothing to update"}
        vals.append(plan_id)
        await conn.execute(f"UPDATE agent_plan SET {', '.join(sets)} WHERE id = ${i}", *vals)
    return {"ok": True}

@app.get("/api/admin/agent/actions", include_in_schema=False)
async def get_agent_actions(request: Request):
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM agent_actions ORDER BY created_at DESC LIMIT 50")
    return [dict(r) for r in rows]

@app.get("/api/admin/agent/opportunities", include_in_schema=False)
async def get_opportunities(request: Request):
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM agent_opportunities WHERE status NOT IN ('skipped', 'done') ORDER BY CASE status WHEN 'execute' THEN 0 WHEN 'content_ready' THEN 1 WHEN 'approved' THEN 2 WHEN 'found' THEN 3 WHEN 'manual_post' THEN 4 ELSE 5 END, relevance_score DESC LIMIT 30")
    return [dict(r) for r in rows]

@app.put("/api/admin/agent/opportunities/{opp_id}", include_in_schema=False)
async def update_opportunity(opp_id: int, request: Request):
    """Update opportunity status and/or suggested_content."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    body = await request.json()
    pool = await get_pool()
    status = body.get("status")
    suggested_content = body.get("suggested_content")
    async with pool.acquire() as conn:
        if status and suggested_content is not None:
            await conn.execute(
                "UPDATE agent_opportunities SET status = $1, suggested_content = $2 WHERE id = $3",
                status, suggested_content, opp_id
            )
        elif status:
            await conn.execute("UPDATE agent_opportunities SET status = $1 WHERE id = $2", status, opp_id)
        elif suggested_content is not None:
            await conn.execute("UPDATE agent_opportunities SET suggested_content = $1 WHERE id = $2", suggested_content, opp_id)
    return {"ok": True}

@app.get("/api/admin/agent/metrics", include_in_schema=False)
async def get_agent_metrics(request: Request):
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM agent_metrics ORDER BY date DESC LIMIT 30")
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════
# Agent Run + Enhanced Opportunity Management
# ═══════════════════════════════════════════════════

@app.post("/api/admin/agent/run", include_in_schema=False)
async def run_agent_now(request: Request):
    """Trigger manual agent run."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    import subprocess
    result = subprocess.Popen(
        ["/home/deploy/depscope/.venv/bin/python3", "-m", "scripts.agents.orchestrator"],
        cwd="/home/deploy/depscope",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "DATABASE_URL": "postgresql://depscope:${DB_PASSWORD}@localhost:5432/depscope"}
    )
    return {"ok": True, "pid": result.pid, "message": "Agent started in background"}


@app.get("/api/admin/agent/opportunities/all", include_in_schema=False)
async def get_all_opportunities(request: Request):
    """Get all opportunities (all statuses) for the full workflow view."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM agent_opportunities WHERE status != 'skipped' ORDER BY CASE status WHEN 'execute' THEN 0 WHEN 'content_ready' THEN 1 WHEN 'approved' THEN 2 WHEN 'found' THEN 3 WHEN 'manual_post' THEN 4 WHEN 'done' THEN 5 ELSE 6 END, relevance_score DESC LIMIT 50"
        )
    return [dict(r) for r in rows]


@app.get("/api/admin/agent/dashboard", include_in_schema=False)
async def get_agent_dashboard(request: Request):
    """Dashboard KPIs and summary data."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        opps_today = await conn.fetchval(
            "SELECT COUNT(*) FROM agent_opportunities WHERE DATE(created_at) = CURRENT_DATE"
        ) or 0
        actions_today = await conn.fetchval(
            "SELECT COUNT(*) FROM agent_actions WHERE DATE(created_at) = CURRENT_DATE AND status = 'executed'"
        ) or 0
        comments_total = await conn.fetchval(
            "SELECT COUNT(*) FROM agent_actions WHERE action_type = 'post_comment' AND status = 'executed'"
        ) or 0
        emails_total = await conn.fetchval(
            "SELECT COUNT(*) FROM agent_actions WHERE action_type = 'send_email' AND status = 'executed'"
        ) or 0
        queue_count = await conn.fetchval(
            "SELECT COUNT(*) FROM agent_opportunities WHERE status IN ('found', 'approved', 'content_ready', 'execute')"
        ) or 0
        last_run = await conn.fetchval(
            "SELECT MAX(created_at) FROM agent_actions WHERE action_type = 'discovery'"
        )
        # Metrics last 7 days
        metrics_7d = await conn.fetch(
            "SELECT * FROM agent_metrics WHERE date >= CURRENT_DATE - INTERVAL '7 days' ORDER BY date"
        )
        # Pipeline breakdown
        pipeline = await conn.fetch(
            "SELECT status, COUNT(*) as count FROM agent_opportunities GROUP BY status"
        )
    return {
        "opps_today": opps_today,
        "actions_today": actions_today,
        "comments_total": comments_total,
        "emails_total": emails_total,
        "queue_count": queue_count,
        "last_run": last_run.isoformat() if last_run else None,
        "metrics_7d": [dict(r) for r in metrics_7d],
        "pipeline": {r["status"]: r["count"] for r in pipeline},
    }


# ═══════════════════════════════════════════════════
# NEW Agent Endpoints — Multi-Agent System
# ═══════════════════════════════════════════════════

@app.get("/api/admin/agent/platforms", include_in_schema=False)
async def get_platforms(request: Request):
    """Get platform connection status."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM agent_platform_status ORDER BY platform")
    return [dict(r) for r in rows]


@app.get("/api/admin/agent/timeline", include_in_schema=False)
async def get_timeline(request: Request):
    """Get chronological timeline of ALL actions."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM agent_actions 
            ORDER BY created_at DESC LIMIT 100
        """)
    return [dict(r) for r in rows]


@app.get("/api/admin/agent/emails", include_in_schema=False)
async def get_email_threads(request: Request):
    """Get email conversations grouped by thread."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM agent_actions 
            WHERE platform = 'email'
            ORDER BY created_at DESC LIMIT 50
        """)
    return [dict(r) for r in rows]


@app.put("/api/admin/agent/opportunities/{opp_id}/approve", include_in_schema=False)
async def approve_opportunity(opp_id: int, request: Request):
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        opp = await conn.fetchrow("SELECT * FROM agent_opportunities WHERE id=$1", opp_id)
        if not opp:
            raise HTTPException(404, "Not found")
        await conn.execute("UPDATE agent_opportunities SET status='approved', approved_at=NOW() WHERE id=$1", opp_id)
    # Trigger content generation in background
    asyncio.create_task(_generate_content_for_opp(dict(opp)))
    return {"ok": True, "generating": True}


async def _generate_content_for_opp(opp: dict):
    """Generate content for an approved opportunity using Claude CLI."""
    import subprocess
    import aiohttp
    pool = await get_pool()

    platform = opp["platform"]
    title = opp["title"]
    url = opp.get("url", "") or ""

    # Fetch article body for richer context
    article_body = ""
    try:
        if platform == "devto" and url:
            path = "/".join(url.replace("https://dev.to/", "").split("/"))
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://dev.to/api/articles/{path}", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        article_body = data.get("body_markdown", "")[:3000]
    except Exception as e:
        print(f"[APPROVE] Failed to fetch article: {e}")

    # Read prompt template and model from config
    async with pool.acquire() as conn:
        config_rows = await conn.fetch("SELECT key, value FROM agent_config WHERE key IN ('prompt_comment_devto', 'prompt_comment_reddit', 'prompt_email_reply', 'claude_model_comments', 'claude_model_emails')")
    config = {r["key"]: r["value"] for r in config_rows}

    if platform == "devto":
        prompt_template = config.get("prompt_comment_devto", "You are a knowledgeable developer commenting on a Dev.to article. Be genuine, add value. NEVER include links. Keep it under 4 lines.")
        model = config.get("claude_model_comments", "haiku")
    elif platform == "reddit":
        prompt_template = config.get("prompt_comment_reddit", "You are a developer responding to a Reddit discussion. Be direct, no fluff. NEVER include links. Max 3-4 sentences.")
        model = config.get("claude_model_comments", "haiku")
    elif platform == "email":
        prompt_template = config.get("prompt_email_reply", "You are Vincenzo Rubino replying to an email. Be brief, professional. Sign as Vincenzo.")
        model = config.get("claude_model_emails", "sonnet")
    else:
        prompt_template = config.get("prompt_comment_devto", "You are a knowledgeable developer commenting. Be genuine, add value. NEVER include links. Keep it short.")
        model = config.get("claude_model_comments", "haiku")

    metadata = opp.get("suggested_content", "") or ""
    if article_body:
        context = f"ARTICLE BODY (first 3000 chars):\n{article_body}\n\nMETADATA: {metadata}"
    else:
        context = metadata

    full_prompt = f"{prompt_template}\n\nARTICLE:\nTitle: {title}\nURL: {url}\nContext: {context}\n\nWrite ONLY the comment text, nothing else."

    try:
        result = subprocess.run(
            ["claude", "-p", "--model", model, full_prompt],
            capture_output=True, text=True, timeout=90,
            cwd="/home/deploy/depscope"
        )
        if result.returncode == 0 and result.stdout.strip():
            content = result.stdout.strip()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE agent_opportunities SET suggested_content=$1, status='content_ready', generated_at=NOW() WHERE id=$2",
                    content, opp["id"]
                )
            print(f"[APPROVE] Generated {len(content)} chars for opp {opp['id']} [model={model}]")
        else:
            err = result.stderr[:200] if result.stderr else "No output"
            print(f"[APPROVE] Claude CLI failed: {err}")
            async with pool.acquire() as conn:
                await conn.execute("UPDATE agent_opportunities SET status='approved' WHERE id=$1", opp["id"])
    except subprocess.TimeoutExpired:
        print(f"[APPROVE] Claude CLI timeout for opp {opp['id']}")
    except Exception as e:
        print(f"[APPROVE] Error generating: {e}")


@app.get("/api/admin/agent/opportunities/{opp_id}/article", include_in_schema=False)
async def fetch_article_content(opp_id: int, request: Request):
    """Fetch the original article/post content from the source platform."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        opp = await conn.fetchrow("SELECT platform, url, title FROM agent_opportunities WHERE id=$1", opp_id)
    if not opp:
        raise HTTPException(404, "Not found")

    import aiohttp
    platform = opp["platform"]
    url = opp["url"] or ""
    result = {"title": opp["title"], "platform": platform, "url": url, "body": "", "body_html": "", "tags": [], "reactions": 0, "comments_count": 0, "author": "", "reading_time": 0}

    try:
        async with aiohttp.ClientSession() as session:
            if platform == "devto":
                path = "/".join(url.replace("https://dev.to/", "").split("/"))
                async with session.get(f"https://dev.to/api/articles/{path}", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result["body"] = data.get("body_markdown", "")
                        result["body_html"] = data.get("body_html", "")
                        result["tags"] = data.get("tag_list", [])
                        result["reactions"] = data.get("positive_reactions_count", 0)
                        result["comments_count"] = data.get("comments_count", 0)
                        result["author"] = data.get("user", {}).get("username", "")
                        result["published_at"] = data.get("published_at", "")
                        result["reading_time"] = data.get("reading_time_minutes", 0)
            elif platform in ("hn", "hackernews"):
                async with session.get(f"https://hn.algolia.com/api/v1/search?query={opp['title']}&tags=story", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("hits"):
                            hit = data["hits"][0]
                            result["author"] = hit.get("author", "")
                            result["reactions"] = hit.get("points", 0)
                            result["comments_count"] = hit.get("num_comments", 0)
                            if hit.get("url"):
                                result["url"] = hit["url"]
    except Exception as e:
        print(f"[FETCH-ARTICLE] Error: {e}")

    return result



@app.put("/api/admin/agent/opportunities/{opp_id}/execute", include_in_schema=False)
async def execute_opportunity(opp_id: int, request: Request):
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE agent_opportunities SET status='execute' WHERE id=$1", opp_id)
    return {"ok": True}


@app.put("/api/admin/agent/opportunities/{opp_id}/reject", include_in_schema=False)
async def reject_opportunity(opp_id: int, request: Request):
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    body = await request.json()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE agent_opportunities SET status='rejected', rejected_reason=$1 WHERE id=$2", body.get("reason", ""), opp_id)
    return {"ok": True}


@app.put("/api/admin/agent/opportunities/{opp_id}/content", include_in_schema=False)
async def update_content(opp_id: int, request: Request):
    """Edit generated content before executing."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    body = await request.json()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE agent_opportunities SET suggested_content=$1 WHERE id=$2", body["content"], opp_id)
    return {"ok": True}


# ═══════════════════════════════════════════════════
# Agent Config Endpoints
# ═══════════════════════════════════════════════════

@app.get("/api/admin/agent/config", include_in_schema=False)
async def get_agent_config(request: Request):
    """Get all agent configuration values."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM agent_config ORDER BY category, key")
    return [dict(r) for r in rows]


@app.put("/api/admin/agent/config/{key}", include_in_schema=False)
async def update_agent_config(key: str, request: Request):
    """Update a single config value."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    body = await request.json()
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE agent_config SET value = $1, updated_at = NOW() WHERE key = $2",
            str(body["value"]), key
        )
    if result == "UPDATE 0":
        raise HTTPException(404, "Config key not found")
    return {"ok": True}


@app.get("/api/admin/agent/config/{key}", include_in_schema=False)
async def get_single_config(key: str, request: Request):
    """Get a single config value."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM agent_config WHERE key = $1", key)
    if not row:
        raise HTTPException(404, "Config key not found")
    return dict(row)


# ═══════════════════════════════════════════════════
# Real-Time Agent System — SSE/Polling + Toggle
# ═══════════════════════════════════════════════════

import json as json_module

# In-memory state for real-time agent
_rt_agent_state = {
    "active": False,
    "running": False,
    "pid": None,
    "queue": [],
    "status_message": "",
}


@app.get("/api/admin/agent/state", include_in_schema=False)
async def get_agent_state(request: Request):
    """Get current real-time agent state."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    return {
        "active": _rt_agent_state["active"],
        "running": _rt_agent_state["running"],
        "queue_size": len(_rt_agent_state["queue"]),
        "status": _rt_agent_state["status_message"],
    }


@app.post("/api/admin/agent/toggle", include_in_schema=False)
async def toggle_realtime_agent(request: Request):
    """Attiva/disattiva l'agente real-time."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")

    _rt_agent_state["active"] = not _rt_agent_state["active"]
    _rt_agent_state["queue"].clear()

    if _rt_agent_state["active"]:
        _rt_agent_state["running"] = True
        _rt_agent_state["status_message"] = "Starting..."
        import subprocess
        proc = subprocess.Popen(
            ["/home/deploy/depscope/.venv/bin/python3", "/home/deploy/depscope/scripts/agents/realtime_runner.py"],
            cwd="/home/deploy/depscope",
            env={**os.environ, "DATABASE_URL": "postgresql://depscope:${DB_PASSWORD}@localhost:5432/depscope"},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _rt_agent_state["pid"] = proc.pid
    else:
        _rt_agent_state["running"] = False
        _rt_agent_state["status_message"] = "Stopped"
        _rt_agent_state["pid"] = None

    return {
        "active": _rt_agent_state["active"],
        "running": _rt_agent_state["running"],
    }


@app.post("/api/admin/agent/notify", include_in_schema=False)
async def push_rt_notification(request: Request):
    """Endpoint interno per l'agente runner per pushare notifiche."""
    body = await request.json()
    msg_type = body.get("type", "")

    if msg_type == "status":
        _rt_agent_state["status_message"] = body.get("message", "")
        _rt_agent_state["running"] = True
        if "stopped" in body.get("message", "").lower():
            _rt_agent_state["running"] = False
    elif msg_type == "error":
        _rt_agent_state["status_message"] = f"Error: {body.get('message', '')}"

    # Sempre accoda per il frontend
    _rt_agent_state["queue"].append(body)
    # Limita la coda a 50 elementi
    if len(_rt_agent_state["queue"]) > 50:
        _rt_agent_state["queue"] = _rt_agent_state["queue"][-50:]

    return {"ok": True}


@app.get("/api/admin/agent/notifications", include_in_schema=False)
async def get_rt_notifications(request: Request):
    """Get pending notifications and clear queue — polling endpoint."""
    user = await _get_user_from_request(request)
    if not user or user["role"] != "admin":
        raise HTTPException(403, "Admin only")

    items = list(_rt_agent_state["queue"])
    _rt_agent_state["queue"].clear()

    return {
        "active": _rt_agent_state["active"],
        "running": _rt_agent_state["running"],
        "status": _rt_agent_state["status_message"],
        "notifications": items,
    }


@app.get("/api/translate", tags=["public"])
async def translate_text(text: str, to: str = "it"):
    """Free translation via MyMemory API."""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.mymemory.translated.net/get?q={text[:500]}&langpair=en|{to}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {"translated": data.get("responseData", {}).get("translatedText", text), "from": "en", "to": to}
    except:
        pass
    return {"translated": text, "from": "en", "to": to}


# ═══════════════════════════════════════════════════
# Intelligence endpoints — admin dashboard + public trending
# ═══════════════════════════════════════════════════

@app.get("/api/admin/intelligence", include_in_schema=False)
async def intelligence_dashboard(request: Request):
    """Aggregated AI-agent intelligence for admin dashboard."""
    user = await _get_user_from_request(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        top_searches = await conn.fetch("""
            SELECT ecosystem, package_name, COUNT(*) AS calls
            FROM api_usage
            WHERE created_at > NOW() - INTERVAL '24 hours'
              AND COALESCE(source, '') NOT IN ('sdk', 'claude_bot', 'gpt_bot', 'internal')
              AND package_name IS NOT NULL AND package_name <> ''
            GROUP BY ecosystem, package_name
            ORDER BY calls DESC
            LIMIT 20
        """)
        agent_breakdown = await conn.fetch("""
            SELECT COALESCE(source, 'unknown') AS source,
                   COUNT(*) AS calls,
                   COUNT(DISTINCT ip_address) AS unique_ips
            FROM api_usage
            WHERE created_at > NOW() - INTERVAL '7 days' AND COALESCE(source, '') <> ''
            GROUP BY source
            ORDER BY calls DESC
        """)
        countries = await conn.fetch("""
            SELECT country,
                   COUNT(*) AS calls,
                   COUNT(DISTINCT ip_address) AS unique_ips
            FROM api_usage
            WHERE country IS NOT NULL AND created_at > NOW() - INTERVAL '7 days'
            GROUP BY country
            ORDER BY calls DESC
            LIMIT 20
        """)
        intents = await conn.fetch("""
            SELECT COALESCE(inferred_intent, 'unknown') AS inferred_intent,
                   COUNT(*) AS count
            FROM api_sessions
            WHERE first_call_at > NOW() - INTERVAL '7 days'
            GROUP BY inferred_intent
            ORDER BY count DESC
        """)
        top_combos = await conn.fetch("""
            SELECT ecosystem, package_a, package_b, cooccurrence_count
            FROM package_cooccurrence
            ORDER BY cooccurrence_count DESC
            LIMIT 30
        """)
        trending = await conn.fetch("""
            SELECT ecosystem, package_name, call_count, rank, rank_change, week_growth_pct
            FROM trend_snapshots
            WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM trend_snapshots)
            ORDER BY week_growth_pct DESC NULLS LAST
            LIMIT 20
        """)
        error_searches = await conn.fetch("""
            SELECT package_name AS error_query, COUNT(*) AS searches
            FROM api_usage
            WHERE endpoint LIKE 'error%'
              AND created_at > NOW() - INTERVAL '7 days'
              AND package_name IS NOT NULL AND package_name <> ''
            GROUP BY package_name
            ORDER BY searches DESC
            LIMIT 15
        """)
        stack_breakdown = await conn.fetch("""
            SELECT COALESCE(inferred_stack, 'unknown') AS stack,
                   COUNT(*) AS sessions
            FROM api_sessions
            WHERE first_call_at > NOW() - INTERVAL '7 days'
              AND inferred_stack IS NOT NULL AND inferred_stack <> ''
            GROUP BY stack
            ORDER BY sessions DESC
            LIMIT 15
        """)
        totals = await conn.fetchrow("""
            SELECT COUNT(*) AS calls_7d,
                   COUNT(DISTINCT session_id) AS sessions_7d,
                   COUNT(DISTINCT ip_address) AS ips_7d,
                   AVG(response_time_ms)::INT AS avg_ms_7d,
                   SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::FLOAT
                     / GREATEST(COUNT(*),1) AS cache_hit_rate_7d
            FROM api_usage
            WHERE created_at > NOW() - INTERVAL '7 days'
        """)
    return {
        "totals_7d": dict(totals) if totals else {},
        "top_searches_24h": [dict(r) for r in top_searches],
        "agents_7d": [dict(r) for r in agent_breakdown],
        "countries_7d": [dict(r) for r in countries],
        "intents_7d": [dict(r) for r in intents],
        "stacks_7d": [dict(r) for r in stack_breakdown],
        "top_cooccurrence": [dict(r) for r in top_combos],
        "trending_packages": [dict(r) for r in trending],
        "top_errors": [dict(r) for r in error_searches],
    }


@app.get("/api/trending", tags=["discover"])
async def public_trending(ecosystem: str = None, limit: int = 20):
    """Public endpoint: top packages getting queried by AI agents this week."""
    from datetime import datetime as _dt
    limit = max(1, min(int(limit or 20), 100))
    eco = (ecosystem or "").strip().lower() or None
    cache_key = f"trending:{eco or 'all'}:{limit}"
    cached = await cache_get(cache_key)
    if cached:
        return cached
    pool = await get_pool()
    async with pool.acquire() as conn:
        if eco:
            rows = await conn.fetch("""
                SELECT ecosystem, package_name, call_count, rank, rank_change, week_growth_pct
                FROM trend_snapshots
                WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM trend_snapshots)
                  AND ecosystem = $1
                ORDER BY rank
                LIMIT $2
            """, eco, limit)
        else:
            rows = await conn.fetch("""
                SELECT ecosystem, package_name, call_count, rank, rank_change, week_growth_pct
                FROM trend_snapshots
                WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM trend_snapshots)
                ORDER BY call_count DESC
                LIMIT $1
            """, limit)
    result = {
        "generated_at": _dt.utcnow().isoformat() + "Z",
        "scope": eco or "all",
        "trending": [dict(r) for r in rows],
    }
    # Cache 6h
    await cache_set(cache_key, result, ttl=6 * 3600)
    return result
