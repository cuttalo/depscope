"""Three agent-first endpoints built on top of DepScope's existing data:

- POST /api/check_bulk       — fast DB-only pre-flight for up to 100 packages
- GET  /api/install/{eco}/{pkg} — canonical install commands per ecosystem
- GET  /api/pin_safe/{eco}/{pkg} — highest version without high/critical CVE

All three are zero-auth and designed so an LLM agent can call them before
emitting an `npm install` / `pip install` / version bump.
"""
from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.database import get_pool
from api.stdlib_modules import lookup as lookup_stdlib
from api.historical_compromises import lookup as lookup_historical


router = APIRouter(tags=["verticals-v2"])


# ============================================================================
# /api/check_bulk
# ============================================================================

class _BulkItem(BaseModel):
    ecosystem: str
    package: str


class _BulkRequest(BaseModel):
    items: list[_BulkItem]


@router.post("/api/check_bulk")
async def check_bulk(body: _BulkRequest) -> dict[str, Any]:
    """Pre-flight existence + risk check for up to 100 (ecosystem, package) pairs.

    DB-only: no live registry fetch. Returns a status per item:
      - `stdlib`:             language builtin (no install needed)
      - `malicious`:          actively flagged by OSV/OpenSSF
      - `typosquat_suspect`:  matches a typosquat pattern (pre-computed or runtime)
      - `historical_incident`: previously compromised (check current version)
      - `exists`:             known safe in our index
      - `unknown`:            not in our index — caller may fall back to /api/check
    Typical latency: <100ms for 100 items.
    """
    items = (body.items or [])[:100]
    if not items:
        raise HTTPException(400, "Provide at least 1 item in `items` (max 100)")

    stage1: list[dict] = []
    db_keys: list[str] = []
    for it in items:
        eco = (it.ecosystem or "").lower()
        pkg = it.package or ""
        entry: dict[str, Any] = {"ecosystem": eco, "package": pkg}
        sh = lookup_stdlib(eco, pkg)
        if sh:
            entry["status"] = "stdlib"
            entry["hint"] = sh
            stage1.append(entry)
            continue
        hist = lookup_historical(eco, pkg)
        if hist:
            entry["historical_compromise"] = hist
        stage1.append(entry)
        db_keys.append(f"{eco}:{pkg.lower()}")

    pkg_map: dict = {}
    tq_map: dict = {}
    mal_map: dict = {}
    runtime_tq: dict[str, list[dict]] = {}

    if db_keys:
        pool = await get_pool()
        async with pool.acquire() as conn:
            pkg_rows = await conn.fetch(
                """
                SELECT ecosystem || ':' || LOWER(name) AS k,
                       latest_version, deprecated, health_score
                FROM packages
                WHERE ecosystem || ':' || LOWER(name) = ANY($1::text[])
                """,
                db_keys,
            )
            pkg_map = {r["k"]: r for r in pkg_rows}

            tq_rows = await conn.fetch(
                """
                SELECT ecosystem || ':' || LOWER(suspect) AS k,
                       legitimate, distance
                FROM typosquat_candidates
                WHERE ecosystem || ':' || LOWER(suspect) = ANY($1::text[])
                """,
                db_keys,
            )
            for r in tq_rows:
                tq_map.setdefault(r["k"], []).append(
                    {"legitimate": r["legitimate"], "distance": r["distance"]}
                )

            mal_rows = await conn.fetch(
                """
                SELECT ecosystem || ':' || LOWER(package_name) AS k,
                       vuln_id, summary
                FROM malicious_packages
                WHERE ecosystem || ':' || LOWER(package_name) = ANY($1::text[])
                  AND (data_json->>'withdrawn' IS NULL)
                """,
                db_keys,
            )
            mal_map = {r["k"]: r for r in mal_rows}

            # Runtime Levenshtein for items absent from the index.
            unknown_keys = [
                k for k in db_keys
                if k not in pkg_map and k not in mal_map and k not in tq_map
            ]
            if unknown_keys:
                ecos = [k.split(":", 1)[0] for k in unknown_keys]
                names = [k.split(":", 1)[1] for k in unknown_keys]
                runtime_rows = await conn.fetch(
                    """
                    WITH suspects AS (
                        SELECT * FROM unnest($1::text[], $2::text[]) AS t(eco, pkg)
                    )
                    SELECT DISTINCT ON (s.eco, s.pkg)
                           s.eco AS eco,
                           s.pkg AS pkg,
                           LOWER(p.name) AS legitimate,
                           levenshtein(LOWER(s.pkg), LOWER(p.name)) AS distance,
                           p.downloads_weekly AS downloads_legit
                    FROM suspects s
                    JOIN packages p ON p.ecosystem = s.eco
                    WHERE p.downloads_weekly > 1000000
                      AND LOWER(p.name) <> LOWER(s.pkg)
                      AND levenshtein(LOWER(s.pkg), LOWER(p.name)) <= 2
                    ORDER BY s.eco, s.pkg, distance, p.downloads_weekly DESC
                    """,
                    ecos, names,
                )
                for r in runtime_rows:
                    rk = f"{r['eco']}:{r['pkg']}"
                    runtime_tq.setdefault(rk, []).append({
                        "legitimate": r["legitimate"],
                        "distance": r["distance"],
                        "downloads_legit": r["downloads_legit"],
                    })

    counters = {"stdlib": 0, "malicious": 0, "typosquat_suspect": 0,
                "historical_incident": 0, "exists": 0, "unknown": 0}
    results: list[dict] = []
    for entry in stage1:
        if "status" in entry:
            counters[entry["status"]] += 1
            results.append(entry)
            continue
        key = f"{entry['ecosystem']}:{entry['package'].lower()}"
        if key in mal_map:
            r = mal_map[key]
            entry["status"] = "malicious"
            entry["advisory_id"] = r["vuln_id"]
            entry["summary"] = r["summary"]
        elif key in tq_map:
            entry["status"] = "typosquat_suspect"
            entry["typosquat_targets"] = tq_map[key]
            entry["detection_source"] = "precomputed"
        elif key in pkg_map:
            r = pkg_map[key]
            entry["status"] = "exists"
            entry["latest_version"] = r["latest_version"]
            entry["deprecated"] = bool(r["deprecated"])
            entry["health_score"] = r["health_score"]
        elif key in runtime_tq:
            entry["status"] = "typosquat_suspect"
            entry["typosquat_targets"] = runtime_tq[key]
            entry["detection_source"] = "runtime_levenshtein"
        elif entry.get("historical_compromise"):
            entry["status"] = "historical_incident"
        else:
            entry["status"] = "unknown"
        counters[entry["status"]] += 1
        results.append(entry)

    return {
        "count": len(results),
        "summary": counters,
        "results": results,
        "_powered_by": "depscope.dev check_bulk — DB-only, 1 round-trip",
    }


# ============================================================================
# /api/install/{ecosystem}/{package}
# ============================================================================

_INSTALL_TEMPLATES: dict[str, dict[str, str]] = {
    "npm": {
        "npm":          "npm install {pkg}",
        "npm_pinned":   "npm install {pkg}@{ver}",
        "npm_dev":      "npm install --save-dev {pkg}",
        "pnpm":         "pnpm add {pkg}",
        "pnpm_pinned":  "pnpm add {pkg}@{ver}",
        "yarn":         "yarn add {pkg}",
        "yarn_pinned":  "yarn add {pkg}@{ver}",
        "bun":          "bun add {pkg}",
        "package_json": '"{pkg}": "^{ver}"',
    },
    "pypi": {
        "pip":           "pip install {pkg}",
        "pip_pinned":    "pip install '{pkg}=={ver}'",
        "uv":            "uv add {pkg}",
        "uv_pinned":     "uv add '{pkg}=={ver}'",
        "poetry":        "poetry add {pkg}",
        "poetry_pinned": "poetry add '{pkg}@^{ver}'",
        "requirements":  "{pkg}=={ver}",
        "pyproject":     '{pkg} = "^{ver}"',
    },
    "cargo": {
        "cargo":        "cargo add {pkg}",
        "cargo_pinned": "cargo add {pkg}@{ver}",
        "cargo_toml":   '{pkg} = "{ver}"',
    },
    "go": {
        "go":        "go get {pkg}",
        "go_pinned": "go get {pkg}@v{ver}",
        "go_mod":    "require {pkg} v{ver}",
    },
    "composer": {
        "composer":        "composer require {pkg}",
        "composer_pinned": "composer require {pkg}:^{ver}",
        "composer_json":   '"{pkg}": "^{ver}"',
    },
    "maven": {
        "maven_xml":   "<dependency><groupId>{group}</groupId><artifactId>{artifact}</artifactId><version>{ver}</version></dependency>",
        "gradle":      'implementation "{pkg}:{ver}"',
        "gradle_kts":  'implementation("{pkg}:{ver}")',
    },
    "nuget": {
        "dotnet":        "dotnet add package {pkg}",
        "dotnet_pinned": "dotnet add package {pkg} --version {ver}",
        "package_ref":   '<PackageReference Include="{pkg}" Version="{ver}" />',
    },
    "rubygems": {
        "gem":        "gem install {pkg}",
        "gem_pinned": "gem install {pkg} -v {ver}",
        "gemfile":    "gem '{pkg}', '~> {ver}'",
    },
    "pub": {
        "dart":     "dart pub add {pkg}",
        "flutter":  "flutter pub add {pkg}",
        "pubspec":  "{pkg}: ^{ver}",
    },
    "hex": {
        "mix":       "mix deps.get",
        "mix_exs":   '{{:{pkg}, "~> {ver}"}}',
    },
    "swift": {
        "spm":             '.package(url: "https://github.com/{pkg}.git", from: "{ver}")',
        "xcode_project":   'Add via Xcode: File > Add Package Dependencies (search "{pkg}")',
    },
    "cocoapods": {
        "pod":         "pod '{pkg}', '~> {ver}'",
        "pod_install": "pod install",
    },
    "cpan": {
        "cpanm":        "cpanm {pkg}",
        "cpanm_pinned": "cpanm {pkg}@{ver}",
    },
    "hackage": {
        "cabal":        "cabal install {pkg}",
        "cabal_pinned": "cabal install {pkg}-{ver}",
        "stack":        "stack install {pkg}",
    },
    "cran": {
        "install":     "install.packages(\"{pkg}\")",
        "remotes":     "remotes::install_version(\"{pkg}\", version = \"{ver}\")",
    },
    "conda": {
        "conda":         "conda install -c conda-forge {pkg}",
        "conda_pinned":  "conda install -c conda-forge {pkg}={ver}",
        "mamba":         "mamba install -c conda-forge {pkg}",
    },
    "homebrew": {
        "brew":        "brew install {pkg}",
    },
}


def _render(tpl: str, pkg: str, ver: str | None) -> str | None:
    if "{ver}" in tpl and not ver:
        return None
    group = artifact = pkg
    if ":" in pkg:
        group, _, artifact = pkg.partition(":")
    return tpl.format(pkg=pkg, ver=ver or "", group=group, artifact=artifact)


@router.get("/api/install/{ecosystem}/{package:path}")
async def install_command(ecosystem: str, package: str, version: str | None = None) -> dict:
    """Canonical install commands for ecosystem+package across common tools.

    Saves agents 100-200 tokens of "how do I install this" reasoning and
    prevents syntax hallucinations (pnpm flags, pyproject.toml quoting,
    Maven XML structure).

    If `version` is omitted, DepScope resolves the latest from its index.
    """
    eco = (ecosystem or "").lower()
    templates = _INSTALL_TEMPLATES.get(eco)
    if not templates:
        raise HTTPException(
            400,
            f"Unsupported ecosystem: {ecosystem}. Supported: {', '.join(sorted(_INSTALL_TEMPLATES))}",
        )

    resolved = version
    if not resolved:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT latest_version FROM packages WHERE ecosystem=$1 AND LOWER(name)=LOWER($2)",
                eco, package,
            )
            if row and row["latest_version"]:
                resolved = row["latest_version"]
    if resolved and resolved.startswith("v"):
        resolved = resolved[1:]

    variants: dict[str, str] = {}
    for key, tpl in templates.items():
        rendered = _render(tpl, package, resolved)
        if rendered is not None:
            variants[key] = rendered

    primary = (
        variants.get("npm_pinned")
        or variants.get("pip_pinned")
        or variants.get("cargo_pinned")
        or variants.get("go_pinned")
        or variants.get("composer_pinned")
        or variants.get("gem_pinned")
        or variants.get("dotnet_pinned")
        or variants.get("maven_xml")
        or variants.get("dart")
        or variants.get("mix_exs")
        or variants.get("spm")
        or variants.get("pod")
        or variants.get("cpanm_pinned") or variants.get("cpanm")
        or variants.get("cabal_pinned") or variants.get("cabal")
        or variants.get("remotes") or variants.get("install")
        or variants.get("conda_pinned") or variants.get("conda")
        or variants.get("brew")
        or next(iter(variants.values()), None)
    )

    return {
        "package": package,
        "ecosystem": eco,
        "version": resolved,
        "primary": primary,
        "variants": variants,
        "note": "Use `primary` for a pinned single-line install. `variants` covers alternative package managers and config-file entries.",
        "_powered_by": "depscope.dev install",
    }


# ============================================================================
# /api/pin_safe/{ecosystem}/{package}
# ============================================================================

_SEMVER_RE = re.compile(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?")
_PRERELEASE_RE = re.compile(
    r"[-+](alpha|beta|rc|canary|dev|next|pre|preview|snapshot|nightly|experimental)",
    re.IGNORECASE,
)


def _is_prerelease(v: str) -> bool:
    return bool(v and _PRERELEASE_RE.search(v))


def _parse_major_minor(v: str) -> tuple[int, int, int] | None:
    if not v:
        return None
    m = _SEMVER_RE.match(v)
    if not m:
        return None
    return (
        int(m.group(1)),
        int(m.group(2) or 0),
        int(m.group(3) or 0),
    )


def _satisfies_constraint(version: str, constraint: str | None) -> bool:
    if not constraint:
        return True
    vp = _parse_major_minor(version)
    if not vp:
        return False
    c = constraint.strip()
    if c.startswith("^"):
        base = _parse_major_minor(c[1:])
        if not base:
            return True
        if base[0] == 0 and base[1] > 0:
            return vp[0] == 0 and vp[1] == base[1] and vp >= base
        if base[0] == 0:
            return vp == base
        return vp[0] == base[0] and vp >= base
    if c.startswith("~"):
        base = _parse_major_minor(c[1:])
        if not base:
            return True
        return vp[0] == base[0] and vp[1] == base[1] and vp >= base
    if c.startswith(">="):
        base = _parse_major_minor(c[2:].lstrip())
        if not base:
            return True
        return vp >= base
    base = _parse_major_minor(c)
    return base is not None and vp == base


def _vuln_affects(version: str, vuln: dict) -> bool:
    fixed = vuln.get("fixed_version")
    if fixed:
        fp = _parse_major_minor(fixed)
        vp = _parse_major_minor(version)
        if fp and vp:
            return vp < fp
    av = (vuln.get("affected_versions") or "").lower()
    v = version.lower()
    if not av:
        return False
    if v == av:
        return True
    for tok in re.split(r"[,\s;]+", av):
        if tok.strip() == v:
            return True
    return False


_SEVERITY_TIERS = {
    "critical": ["critical"],
    "high": ["critical", "high"],
    "medium": ["critical", "high", "medium"],
    "low": ["critical", "high", "medium", "low"],
}


async def _fetch_versions_list(ecosystem: str, package: str) -> list[str]:
    """Pull the recent version history: versions table → packages.data_json
    → live registry. Returns newest-first."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        pkg_row = await conn.fetchrow(
            "SELECT id, data_json FROM packages WHERE ecosystem=$1 AND LOWER(name)=LOWER($2)",
            ecosystem, package,
        )
        if not pkg_row:
            return []
        rows = await conn.fetch(
            "SELECT version FROM versions WHERE package_id=$1 ORDER BY published_at DESC NULLS LAST LIMIT 50",
            pkg_row["id"],
        )
        if rows:
            return [r["version"] for r in rows if r["version"]]
        data_json = pkg_row["data_json"] or {}
        if isinstance(data_json, dict):
            versions = data_json.get("versions") or []
            if isinstance(versions, list) and versions:
                return list(reversed([v for v in versions if isinstance(v, str)]))
    try:
        from api.registries import fetch_package
        live = await fetch_package(ecosystem, package)
    except Exception:
        live = None
    if not live:
        return []
    versions = live.get("versions") or []
    if isinstance(versions, list):
        return list(reversed([v for v in versions if isinstance(v, str)]))
    return []


@router.get("/api/pin_safe/{ecosystem}/{package:path}")
async def pin_safe(
    ecosystem: str,
    package: str,
    min_severity: str = "high",
    constraint: str | None = None,
    limit_checked: int = 50,
    include_prerelease: bool = False,
) -> dict:
    """Return the highest version whose known CVEs are below the given severity.

    - `min_severity=high` (default) excludes versions with any critical or high CVE.
    - `constraint` accepts npm-style `^X.Y.Z`, `~X.Y.Z`, `>=X`, or exact `X.Y.Z`.
    - `include_prerelease=false` (default) skips alpha/beta/rc/canary/nightly.
    - `limit_checked` caps how many versions we walk through (newest-first).

    Sources: versions table → packages.data_json.versions → live registry.
    """
    eco = (ecosystem or "").lower()
    tiers = _SEVERITY_TIERS.get(min_severity.lower())
    if not tiers:
        raise HTTPException(400, "min_severity must be one of: critical, high, medium, low")

    pool = await get_pool()
    async with pool.acquire() as conn:
        pkg_row = await conn.fetchrow(
            "SELECT id, latest_version, deprecated FROM packages WHERE ecosystem=$1 AND LOWER(name)=LOWER($2)",
            eco, package,
        )
        if not pkg_row:
            raise HTTPException(404, f"Package not found: {eco}/{package}")
        vuln_rows = await conn.fetch(
            "SELECT vuln_id, severity, affected_versions, fixed_version FROM vulnerabilities WHERE package_id=$1 AND LOWER(severity) = ANY($2::text[])",
            pkg_row["id"], tiers,
        )

    vulns = [dict(r) for r in vuln_rows]
    versions_list = await _fetch_versions_list(eco, package)
    if not versions_list and pkg_row["latest_version"]:
        versions_list = [pkg_row["latest_version"]]

    recommended: str | None = None
    considered: list[dict] = []
    for v in versions_list[:limit_checked]:
        if not include_prerelease and _is_prerelease(v):
            considered.append({"version": v, "status": "prerelease_skipped"})
            continue
        if constraint and not _satisfies_constraint(v, constraint):
            considered.append({"version": v, "status": "out_of_constraint"})
            continue
        affecting = [x for x in vulns if _vuln_affects(v, x)]
        if not affecting:
            recommended = v
            considered.append({"version": v, "status": "safe"})
            break
        considered.append({
            "version": v,
            "status": "vulnerable",
            "vuln_ids": [x["vuln_id"] for x in affecting][:3],
        })

    if recommended is None and not vulns and versions_list:
        candidates = versions_list if include_prerelease else [
            v for v in versions_list if not _is_prerelease(v)
        ]
        recommended = next(
            (v for v in candidates if not constraint or _satisfies_constraint(v, constraint)),
            None,
        )

    return {
        "ecosystem": eco,
        "package": package,
        "latest_version": pkg_row["latest_version"],
        "recommended_version": recommended,
        "min_severity_excluded": min_severity,
        "constraint": constraint,
        "include_prerelease": include_prerelease,
        "versions_checked": len(considered),
        "known_vuln_count": len(vulns),
        "walk": considered[:10],
        "deprecated": bool(pkg_row["deprecated"]),
        "_powered_by": "depscope.dev pin_safe",
    }
