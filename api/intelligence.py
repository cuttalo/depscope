"""DepScope intelligence: bundle size, TypeScript quality, dep tree, license aggregation."""
import asyncio
import aiohttp
from api.cache import cache_get, cache_set
from api.registries import fetch_package, fetch_vulnerabilities
from api.health import calculate_health_score


# ---- Cache TTLs (seconds) ----
TTL_BUNDLE = 7 * 24 * 3600       # 7 days
TTL_TYPESCRIPT = 7 * 24 * 3600   # 7 days
TTL_TREE = 24 * 3600             # 24 hours
TTL_LICENSES = 24 * 3600         # 24 hours
TTL_SUBDEP_HEALTH = 6 * 3600     # 6 hours

# ---- External bundle API ----
BUNDLEPHOBIA_URL = "https://bundlephobia.com/api/size"
NPM_REGISTRY = "https://registry.npmjs.org"

# ---- Concurrency guards ----
_BUNDLE_SEM = asyncio.Semaphore(4)
_TREE_SEM = asyncio.Semaphore(8)


# =================================================================
# Feature 3 — Bundle size (JS / npm only)
# =================================================================

async def fetch_bundle_size(name: str, version: str | None = None) -> dict | None:
    """Return bundle size info for an npm package via bundlephobia.

    Returns None on any failure (graceful degradation).
    Cached 7 days in Redis.
    """
    tag = f"{name}@{version}" if version else name
    cache_key = f"bundle:{tag}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    params = {"package": tag}
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; DepScope/0.1; +https://depscope.dev)",
        "Accept": "application/json",
    }
    try:
        async with _BUNDLE_SEM:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(
                    BUNDLEPHOBIA_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=12),
                ) as resp:
                    if resp.status != 200:
                        # Cache a negative for 1 day to avoid hammering
                        await cache_set(cache_key, {"_unavailable": True}, ttl=86400)
                        return None
                    data = await resp.json()
    except Exception:
        return None

    result = {
        "size_kb": round(data.get("size", 0) / 1024, 1) if data.get("size") else None,
        "gzip_kb": round(data.get("gzip", 0) / 1024, 1) if data.get("gzip") else None,
        "dependency_count": data.get("dependencyCount", 0),
        "has_js_module": data.get("hasJSModule", False),
        "has_side_effects": bool(data.get("hasSideEffects", False)),
        "scoped": data.get("scoped", False),
        "source": "bundlephobia",
    }
    await cache_set(cache_key, result, ttl=TTL_BUNDLE)
    return result


# =================================================================
# Feature 4 — TypeScript quality (npm only)
# =================================================================

async def _npm_has_types_field(name: str) -> tuple[bool, bool]:
    """Return (has_types_field, has_dts_file_hint) by reading npm metadata."""
    url = f"{NPM_REGISTRY}/{name}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    return False, False
                data = await resp.json()
    except Exception:
        return False, False

    latest = data.get("dist-tags", {}).get("latest", "")
    info = data.get("versions", {}).get(latest, {})
    has_types = bool(info.get("types") or info.get("typings"))
    # Heuristic: main/module ends with .d.ts, or types listed in files
    files = info.get("files") or []
    has_dts = has_types or any(isinstance(f, str) and f.endswith(".d.ts") for f in files)
    return has_types, has_dts


async def _definitely_typed_exists(name: str) -> bool:
    """Check if @types/<name> exists on npm registry."""
    # Scoped packages like @foo/bar become @types/foo__bar
    if name.startswith("@"):
        slug = name[1:].replace("/", "__")
    else:
        slug = name
    url = f"{NPM_REGISTRY}/@types/{slug}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                return resp.status == 200
    except Exception:
        return False


async def check_typescript(name: str) -> dict:
    """Return TypeScript quality info for an npm package.

    Score legend:
      10 — types bundled in package (has types field / .d.ts)
       7 — types via @types/<name> on DefinitelyTyped
       4 — partial: description/keywords mention typescript (weak signal)
       0 — none found
    Graceful on API failure — returns score 0.
    """
    cache_key = f"ts:{name}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    has_types, has_dts = await _npm_has_types_field(name)
    if has_types or has_dts:
        result = {
            "score": 10,
            "has_types": True,
            "types_source": "bundled",
            "types_package": None,
        }
    else:
        dt = await _definitely_typed_exists(name)
        if dt:
            result = {
                "score": 7,
                "has_types": True,
                "types_source": "definitely-typed",
                "types_package": f"@types/{name[1:].replace('/', '__') if name.startswith('@') else name}",
            }
        else:
            result = {
                "score": 0,
                "has_types": False,
                "types_source": None,
                "types_package": None,
            }

    await cache_set(cache_key, result, ttl=TTL_TYPESCRIPT)
    return result


# =================================================================
# Feature 2 — Transitive dep tree
# =================================================================

def _parse_deps_list(ecosystem: str, pkg_data: dict) -> list[str]:
    """Normalize the `dependencies` field of fetch_package() output into a list of names."""
    raw = pkg_data.get("dependencies", []) or []
    names: list[str] = []
    if ecosystem == "pypi":
        # requires_dist entries look like: 'requests (>=2.0); extra == "security"'
        for entry in raw:
            if not isinstance(entry, str):
                continue
            # Drop environment marker after ';'
            head = entry.split(";", 1)[0].strip()
            # Name is text before any of: space, (, ==, >=, <=, >, <, ~=, !=, [
            import re as _re
            m = _re.match(r"[A-Za-z0-9_.\-]+", head)
            if m:
                names.append(m.group(0).lower())
    else:
        for entry in raw:
            if isinstance(entry, str) and entry.strip():
                names.append(entry.strip())
            elif isinstance(entry, dict) and entry.get("name"):
                names.append(entry["name"])
    # Dedup preserving order
    seen = set()
    out = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


async def _mini_health(ecosystem: str, name: str) -> dict:
    """Cheap health lookup for a sub-dependency.

    Caches result 6h. Returns {score, risk, vuln_count, license, deprecated, version}.
    """
    cache_key = f"subdep:{ecosystem}:{name}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    async with _TREE_SEM:
        try:
            pkg_data = await fetch_package(ecosystem, name)
        except Exception:
            pkg_data = None
        if not pkg_data:
            result = {
                "found": False,
                "score": None,
                "risk": "unknown",
                "vuln_count": 0,
                "license": None,
                "deprecated": None,
                "version": None,
                "deps": [],
            }
            await cache_set(cache_key, result, ttl=TTL_SUBDEP_HEALTH)
            return result
        try:
            vulns = await fetch_vulnerabilities(
                ecosystem, name, latest_version=pkg_data.get("latest_version", "")
            )
        except Exception:
            vulns = []
        h = calculate_health_score(pkg_data, vulns)

    result = {
        "found": True,
        "score": h["score"],
        "risk": h["risk"],
        "vuln_count": len(vulns),
        "license": pkg_data.get("license") or None,
        "deprecated": pkg_data.get("deprecated", False),
        "version": pkg_data.get("latest_version"),
        "deps": _parse_deps_list(ecosystem, pkg_data),
    }
    await cache_set(cache_key, result, ttl=TTL_SUBDEP_HEALTH)
    return result


async def _expand_tree(
    ecosystem: str,
    name: str,
    depth: int,
    max_depth: int,
    max_deps: int,
    visited: set,
    budget: list,
) -> dict:
    """Recursively expand the tree node for `name`.

    visited: names already expanded (loop protection)
    budget: single-element list tracking remaining sub-deps to avoid pathological trees.
    """
    node_info = await _mini_health(ecosystem, name)
    node = {
        "name": name,
        "version": node_info.get("version"),
        "health_score": node_info.get("score"),
        "risk": node_info.get("risk"),
        "vuln_count": node_info.get("vuln_count", 0),
        "license": node_info.get("license"),
        "deprecated": node_info.get("deprecated", False),
        "depth": depth,
        "deps": [],
    }

    if depth >= max_depth or not node_info.get("found"):
        return node

    children_names = [n for n in node_info.get("deps", []) if n not in visited]
    if not children_names:
        return node

    # Respect the global budget
    if budget[0] <= 0:
        return node
    take = min(len(children_names), budget[0])
    children_names = children_names[:take]
    budget[0] -= take

    for cn in children_names:
        visited.add(cn)

    tasks = [
        _expand_tree(ecosystem, cn, depth + 1, max_depth, max_deps, visited, budget)
        for cn in children_names
    ]
    children = await asyncio.gather(*tasks, return_exceptions=True)
    node["deps"] = [c for c in children if not isinstance(c, Exception)]
    return node


def _count_and_summarize(root: dict) -> dict:
    """Walk the tree and build summary metrics."""
    total = 0
    critical_vulns = 0
    deprecated_count = 0
    low_health_count = 0

    def walk(node):
        nonlocal total, critical_vulns, deprecated_count, low_health_count
        for child in node.get("deps", []):
            total += 1
            if child.get("vuln_count", 0) > 0:
                # We don't have severity breakdown here; conservative: count presence of any vuln
                critical_vulns += 1 if child.get("risk") == "critical" else 0
            if child.get("deprecated"):
                deprecated_count += 1
            sc = child.get("health_score")
            if sc is not None and sc < 60:
                low_health_count += 1
            walk(child)

    walk(root)
    return {
        "total_deps": total,
        "risk_summary": {
            "critical_vulns": critical_vulns,
            "deprecated_count": deprecated_count,
            "low_health_count": low_health_count,
        },
    }


async def build_dep_tree(
    ecosystem: str,
    package: str,
    max_depth: int = 3,
    max_deps: int = 200,
) -> dict | None:
    """Build a transitive dependency tree with health per node.

    - depth limit: max_depth (default 3)
    - total sub-dep budget: max_deps (default 200)
    - visited-set cycle protection
    - aggressively cached (24h)
    """
    cache_key = f"tree:{ecosystem}:{package}:d{max_depth}:m{max_deps}"
    cached = await cache_get(cache_key)
    if cached is not None:
        cached["_cache"] = "hit"
        return cached

    # Root: full fetch for correctness
    try:
        root_data = await fetch_package(ecosystem, package)
    except Exception:
        root_data = None
    if not root_data:
        return None

    try:
        root_vulns = await fetch_vulnerabilities(
            ecosystem, package, latest_version=root_data.get("latest_version", "")
        )
    except Exception:
        root_vulns = []
    root_health = calculate_health_score(root_data, root_vulns)

    direct_deps = _parse_deps_list(ecosystem, root_data)
    visited = set([package] + direct_deps)
    budget = [max_deps]

    tasks = [
        _expand_tree(ecosystem, dep, 1, max_depth, max_deps, visited, budget)
        for dep in direct_deps[: max_deps]
    ]
    budget[0] = max(0, budget[0] - len(tasks))
    children = await asyncio.gather(*tasks, return_exceptions=True)
    children = [c for c in children if not isinstance(c, Exception)]

    tree_root = {
        "name": package,
        "version": root_data.get("latest_version"),
        "health_score": root_health["score"],
        "risk": root_health["risk"],
        "vuln_count": len(root_vulns),
        "license": root_data.get("license") or None,
        "deprecated": root_data.get("deprecated", False),
        "depth": 0,
        "deps": children,
    }

    summary = _count_and_summarize(tree_root)

    result = {
        "package": package,
        "ecosystem": ecosystem,
        "version": root_data.get("latest_version"),
        "health_score": root_health["score"],
        "total_deps": summary["total_deps"],
        "direct_deps_count": len(direct_deps),
        "max_depth": max_depth,
        "max_deps_budget": max_deps,
        "risk_summary": summary["risk_summary"],
        "tree": children,
        "_cache": "miss",
    }
    await cache_set(cache_key, result, ttl=TTL_TREE)
    return result


# =================================================================
# Feature 5 — License aggregation
# =================================================================

# Licenses considered problematic in a proprietary/commercial context
COPYLEFT_STRONG = {"GPL", "AGPL"}
COPYLEFT_WEAK = {"LGPL", "MPL"}
PERMISSIVE = {"MIT", "ISC", "APACHE", "BSD", "UNLICENSE", "CC0"}


def _normalize_license(raw) -> str:
    if not raw:
        return "Unknown"
    if isinstance(raw, dict):
        raw = raw.get("type") or raw.get("name") or ""
    s = str(raw).strip()
    if not s:
        return "Unknown"
    # Common SPDX-ish cleanups
    upper = s.upper()
    for token in ("AGPL-3.0", "AGPL"):
        if token in upper:
            return "AGPL-3.0" if "3" in upper else "AGPL"
    for token in ("GPL-3.0", "GPL-2.0", "GPL"):
        if token in upper:
            if "3" in upper:
                return "GPL-3.0"
            if "2" in upper:
                return "GPL-2.0"
            return "GPL"
    for token in ("LGPL-3.0", "LGPL-2", "LGPL"):
        if token in upper:
            return "LGPL"
    if "APACHE" in upper:
        return "Apache-2.0"
    if "MIT" in upper:
        return "MIT"
    if "ISC" in upper:
        return "ISC"
    if "BSD-3" in upper:
        return "BSD-3-Clause"
    if "BSD-2" in upper:
        return "BSD-2-Clause"
    if "BSD" in upper:
        return "BSD"
    if "MPL" in upper:
        return "MPL-2.0"
    if "UNLICENSE" in upper:
        return "Unlicense"
    if "CC0" in upper:
        return "CC0-1.0"
    return s[:60]


def _license_category(lic: str) -> str:
    u = lic.upper()
    if any(c in u for c in COPYLEFT_STRONG):
        return "copyleft_strong"
    if any(c in u for c in COPYLEFT_WEAK):
        return "copyleft_weak"
    if any(c in u for c in PERMISSIVE):
        return "permissive"
    if u == "UNKNOWN":
        return "unknown"
    return "other"


async def aggregate_licenses(ecosystem: str, package: str) -> dict | None:
    """Aggregate licenses across the (cached) transitive tree."""
    cache_key = f"licenses:{ecosystem}:{package}"
    cached = await cache_get(cache_key)
    if cached is not None:
        cached["_cache"] = "hit"
        return cached

    tree = await build_dep_tree(ecosystem, package)
    if not tree:
        return None

    counts: dict[str, int] = {}
    unknown = 0
    analyzed = 0

    def walk(node):
        nonlocal unknown, analyzed
        for child in node.get("deps", []):
            analyzed += 1
            lic = _normalize_license(child.get("license"))
            if lic == "Unknown":
                unknown += 1
            counts[lic] = counts.get(lic, 0) + 1
            walk(child)

    walk({"deps": tree.get("tree", [])})

    warnings = []
    strong_copyleft = []
    weak_copyleft = []
    for lic, cnt in counts.items():
        cat = _license_category(lic)
        if cat == "copyleft_strong":
            strong_copyleft.append((lic, cnt))
        elif cat == "copyleft_weak":
            weak_copyleft.append((lic, cnt))

    if strong_copyleft:
        warnings.append({
            "level": "high",
            "message": "Strong copyleft licenses (GPL/AGPL) detected — incompatible with proprietary distribution",
            "licenses": [f"{l} (x{c})" for l, c in strong_copyleft],
        })
    if weak_copyleft:
        warnings.append({
            "level": "medium",
            "message": "Weak copyleft (LGPL/MPL) — safe if linked dynamically, review static linking",
            "licenses": [f"{l} (x{c})" for l, c in weak_copyleft],
        })
    if unknown > 0:
        warnings.append({
            "level": "low",
            "message": f"{unknown} dep(s) with unknown/missing license — manual review recommended",
            "licenses": [],
        })

    commercial_safe = not strong_copyleft

    # Pick a recommended license file: match root package if known, else MIT
    root_lic = _normalize_license(tree.get("license") if isinstance(tree, dict) else None)
    if root_lic == "Unknown":
        # Fall back to most common in tree
        if counts:
            root_lic = max(counts.items(), key=lambda kv: kv[1])[0]
        else:
            root_lic = "MIT"

    result = {
        "package": package,
        "ecosystem": ecosystem,
        "total_deps_analyzed": analyzed,
        "licenses": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
        "unknown_count": unknown,
        "warnings": warnings,
        "commercial_safe": commercial_safe,
        "recommended_license_file": root_lic if root_lic != "Unknown" else "MIT",
        "_cache": "miss",
    }
    await cache_set(cache_key, result, ttl=TTL_LICENSES)
    return result
