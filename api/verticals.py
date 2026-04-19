"""DepScope verticals — Error→Fix, Compatibility Matrix, Known Bugs.

Three capability modules that share the depscope.dev API, PostgreSQL database
and Redis cache. All functions are async and read/write through asyncpg.
"""
import hashlib
import json
import re
from typing import Any

from api.database import get_pool


# --------------------------------------------------------------------------- #
# A. ERROR → FIX
# --------------------------------------------------------------------------- #

# Patterns stripped to turn a raw error into a reusable signature.
# Order matters: quotes first (so we can match strings), then paths/numbers.
_QUOTED_PAT = re.compile(r"""(['"`])(?:\\.|[^\\])*?\1""")
_PATH_PAT = re.compile(r"""(?:[A-Za-z]:)?(?:/|\\)[\w\-./\\@+]+""")
_HEX_PAT = re.compile(r"\b0x[0-9a-fA-F]+\b")
_HASH_PAT = re.compile(r"\b[0-9a-f]{7,40}\b")
_NUM_PAT = re.compile(r"\b\d+\b")
_WS_PAT = re.compile(r"\s+")


def normalize_error(text: str) -> str:
    """Remove file-specific details, numbers and whitespace from an error.

    Keeps the semantic skeleton so two errors pointing to the same root cause
    produce the same signature.
    """
    if not text:
        return ""
    t = str(text).strip()
    # Strip common tracebacks preamble — keep the last useful line if huge
    if len(t) > 4000:
        t = t[-4000:]
    # Replace quoted literals with placeholder
    t = _QUOTED_PAT.sub("<STR>", t)
    # File paths -> <PATH>
    t = _PATH_PAT.sub("<PATH>", t)
    # Hex / git hashes -> <HEX>
    t = _HEX_PAT.sub("<HEX>", t)
    t = _HASH_PAT.sub("<HASH>", t)
    # Numbers -> <N>
    t = _NUM_PAT.sub("<N>", t)
    # Normalise whitespace
    t = _WS_PAT.sub(" ", t).strip().lower()
    return t


def hash_error_pattern(text: str) -> str:
    """SHA256 of the normalised error text."""
    norm = normalize_error(text)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _tsquery_any(text: str) -> str:
    """Turn free-form text into a loose OR-tsquery (`a | b | c`).

    Strips punctuation, placeholders and short tokens so short queries still
    match. Returns an empty string if no usable tokens remain (caller must
    handle that case)."""
    if not text:
        return ""
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{1,}", text.lower())
    # Drop placeholders we inject during normalisation
    tokens = [t for t in tokens if t not in ("str", "path", "hex", "hash", "n")]
    # Drop very common english stopwords that confuse the matcher
    stop = {"the", "a", "an", "of", "on", "in", "to", "is", "and", "or", "error", "warning"}
    tokens = [t for t in tokens if t not in stop]
    seen = []
    for t in tokens:
        if t not in seen:
            seen.append(t)
    return " | ".join(seen)


async def search_errors(query: str, limit: int = 10) -> list[dict]:
    """Full-text search over `pattern` plus exact hash lookup.

    Matching strategy (any of, scored):
      1. exact hash match on normalised pattern  (rank = 2.0)
      2. normalised pattern equality  (rank = 1.8)
      3. substring containment on normalised pattern  (rank = 1.5 / 1.3)
      4. raw-lowercase substring containment  (rank = 1.2 / 1.0)
      5. tsquery OR of meaningful tokens  (rank = ts_rank)

    Weak FTS matches (rank < 0.02) are dropped when at least one strong
    match exists so we don't pollute results (e.g. "Cannot find module
    express" no longer surfaces unrelated pydantic entries).

    Both the query and the stored pattern are normalised via the same
    `normalize_error` routine (quotes, paths, hex and numbers are
    replaced with placeholders), so "Cannot find module 'express'" and
    "Cannot find module express" end up on the same axis.
    """
    limit = max(1, min(int(limit or 10), 50))
    if not query:
        return []

    norm = normalize_error(query)
    h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
    ts_any = _tsquery_any(norm)
    norm_lc = norm.lower()[:200]
    # Strip quotes from the raw query so "Cannot find module express" can
    # still match the stored "Cannot find module 'express'" via substring.
    raw_lc = (query or "").strip().lower().replace("'", "").replace('"', "")[:200]

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Pre-compute a normalised form of each stored pattern once, in-query,
        # so boost rules can compare apples to apples. We still index on
        # `pattern` (ts_vector) for fallback FTS, but equality/substring
        # match against the normalised projection.
        rows = await conn.fetch(
            """
            WITH q AS (
                SELECT $1::text AS h, $2::text AS ts, $3::text AS norm,
                       $4::text AS raw, $5::int AS lim
            ),
            scored AS (
                SELECT e.id, e.hash, e.pattern, e.full_message, e.ecosystem,
                       e.package_name, e.package_version, e.solution,
                       e.confidence, e.source, e.source_url, e.votes,
                       e.created_at, e.updated_at,
                       -- normalise pattern the same way the Python side does:
                       -- lower + collapse quoted / numeric tokens.
                       regexp_replace(
                         regexp_replace(
                           regexp_replace(lower(e.pattern), '''[^'']*''', '<str>', 'g'),
                           '"[^"]*"', '<str>', 'g'),
                         '[0-9]+', '<n>', 'g') AS pat_norm
                FROM errors e
            )
            SELECT id, hash, pattern, full_message, ecosystem, package_name,
                   package_version, solution, confidence, source, source_url,
                   votes, created_at, updated_at,
                   CASE
                     WHEN hash = (SELECT h FROM q) THEN 2.0
                     WHEN pat_norm = (SELECT norm FROM q) THEN 1.8
                     WHEN POSITION(pat_norm IN (SELECT norm FROM q)) > 0 THEN 1.5
                     WHEN POSITION((SELECT norm FROM q) IN pat_norm) > 0 THEN 1.3
                     WHEN POSITION(replace(replace(LOWER(pattern), '''', ''), '"', '') IN (SELECT raw FROM q)) > 0 THEN 1.2
                     WHEN POSITION((SELECT raw FROM q) IN replace(replace(LOWER(pattern), '''', ''), '"', '')) > 0 THEN 1.0
                     WHEN (SELECT ts FROM q) <> '' THEN ts_rank(
                       to_tsvector('english', pattern),
                       to_tsquery('english', (SELECT ts FROM q))
                     )
                     ELSE 0.05
                   END AS rank
            FROM scored
            WHERE hash = (SELECT h FROM q)
               OR POSITION(pat_norm IN (SELECT norm FROM q)) > 0
               OR POSITION((SELECT norm FROM q) IN pat_norm) > 0
               OR POSITION(replace(replace(LOWER(pattern), '''', ''), '"', '') IN (SELECT raw FROM q)) > 0
               OR POSITION((SELECT raw FROM q) IN replace(replace(LOWER(pattern), '''', ''), '"', '')) > 0
               OR ((SELECT ts FROM q) <> '' AND to_tsvector('english', pattern)
                                                @@ to_tsquery('english', (SELECT ts FROM q)))
            ORDER BY rank DESC, votes DESC, confidence DESC, LENGTH(pattern) ASC
            LIMIT (SELECT lim FROM q)
            """,
            h, ts_any, norm_lc, raw_lc, limit,
        )
    results = [dict(r) for r in rows]
    # Drop weak FTS matches when we already have at least one strong match
    # (rank >= 1.0). Weak FTS pollution is the common failure mode: e.g.
    # "hydration failed" was returning "FATAL ERROR (heap ... failed)" at
    # ts_rank ~0.03 alongside the real hits at rank >= 1.0.
    if results and float(results[0].get("rank", 0) or 0) >= 1.0:
        results = [r for r in results if float(r.get("rank", 0) or 0) >= 0.1]
    return results


async def get_error_by_hash(error_hash: str) -> dict | None:
    """Fetch a single error by its normalised-pattern SHA256."""
    if not error_hash:
        return None
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM errors WHERE hash = $1",
            error_hash,
        )
    return dict(row) if row else None


# --------------------------------------------------------------------------- #
# B. COMPATIBILITY MATRIX
# --------------------------------------------------------------------------- #

def _canon_stack(packages: dict) -> dict:
    """Return a canonical dict with lowercased names and stringified versions."""
    if not isinstance(packages, dict):
        return {}
    out = {}
    for k, v in packages.items():
        if not k:
            continue
        out[str(k).strip().lower()] = str(v).strip()
    return out


def hash_stack(packages: dict) -> str:
    """Deterministic hash of a package combination (order-independent)."""
    canon = _canon_stack(packages)
    blob = json.dumps(canon, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


async def check_compat(stack: dict) -> dict:
    """Look up compatibility status for a stack.

    Matching strategy:
      1. exact stack_hash match
      2. partial match: any stored stack whose packages are a subset of the
         requested one (covers "next+react" inside "next+react+prisma")
      3. transitive inference: if every 2-package sub-pair is verified,
         mark the full stack as likely_compatible
      4. otherwise similar stacks for UI hint
    """
    packages = _canon_stack(stack)
    if not packages:
        return {
            "status": "invalid",
            "reason": "No packages provided",
            "packages": {},
            "matches": [],
        }

    h = hash_stack(packages)
    pool = await get_pool()
    async with pool.acquire() as conn:
        exact = await conn.fetchrow(
            "SELECT * FROM compat_matrix WHERE stack_hash = $1",
            h,
        )
        if exact:
            row = dict(exact)
            row["packages"] = _maybe_json(row.get("packages"))
            return {
                "status": row["status"],
                "match_type": "exact",
                "packages": packages,
                "notes": row.get("notes"),
                "source": row.get("source"),
                "source_url": row.get("source_url"),
                "stars": row.get("stars", 0),
                "reported_count": row.get("reported_count", 1),
                "updated_at": row.get("updated_at"),
            }

        # Partial / subset match — but only if the matched row covers MORE
        # than just a 2-package pair. 2-package pairs are handled by the
        # transitive inference block below (so we can aggregate ALL pairs
        # instead of returning a single one and hiding the broader picture).
        partial_rows = await conn.fetch(
            """
            SELECT stack_hash, packages, status, notes, source, source_url,
                   stars, reported_count, updated_at
            FROM compat_matrix
            WHERE packages <@ $1::jsonb
            ORDER BY jsonb_array_length(
                       COALESCE(
                         (SELECT jsonb_agg(k) FROM jsonb_object_keys(packages) k),
                         '[]'::jsonb
                       )
                     ) DESC,
                     stars DESC
            LIMIT 5
            """,
            json.dumps(packages),
        )

        def _pkg_count(row) -> int:
            pkgs = _maybe_json(row.get("packages"))
            return len(pkgs) if isinstance(pkgs, dict) else 0

        large_partials = [dict(r) for r in partial_rows if _pkg_count(dict(r)) >= 3]
        if large_partials:
            best = large_partials[0]
            best["packages"] = _maybe_json(best.get("packages"))
            return {
                "status": best["status"],
                "match_type": "subset",
                "packages": packages,
                "matched_subset": best["packages"],
                "notes": best.get("notes"),
                "source": best.get("source"),
                "source_url": best.get("source_url"),
                "stars": best.get("stars", 0),
                "reported_count": best.get("reported_count", 1),
                "other_subsets": [
                    {
                        "packages": _maybe_json(dict(r).get("packages")),
                        "status": dict(r)["status"],
                    }
                    for r in large_partials[1:]
                ],
            }

        # Fix 3: transitive inference over 2-package pairs.
        # If every pair (a,b) in the requested stack is individually verified,
        # the full stack is *likely* compatible. If any pair is broken, flag
        # the whole stack. Only runs for 3+ packages (pairs always beat exact
        # match for a 2-package stack, handled above).
        items = list(packages.items())
        if len(items) >= 3:
            pair_results: list[dict] = []
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    pair = {items[i][0]: items[i][1], items[j][0]: items[j][1]}
                    pair_hash = hash_stack(pair)
                    r = await conn.fetchrow(
                        "SELECT status, notes, source, source_url, stars, reported_count "
                        "FROM compat_matrix WHERE stack_hash = $1",
                        pair_hash,
                    )
                    if r:
                        pair_results.append({
                            "pair": pair,
                            "status": r["status"],
                            "notes": r.get("notes") if isinstance(r, dict) else r["notes"],
                            "source_url": r["source_url"],
                            "stars": r["stars"] or 0,
                        })

            total_pairs = len(items) * (len(items) - 1) // 2
            verified_pairs = [p for p in pair_results if p["status"] == "verified"]
            broken_pairs = [p for p in pair_results if p["status"] == "broken"]

            if broken_pairs:
                return {
                    "status": "broken",
                    "match_type": "transitive",
                    "inference": "transitive",
                    "confidence": 0.9,
                    "packages": packages,
                    "notes": (
                        f"Broken pair(s) detected: "
                        + ", ".join(
                            "+".join(p["pair"].keys()) for p in broken_pairs
                        )
                    ),
                    "broken_pairs": broken_pairs,
                    "verified_pairs": verified_pairs,
                    "total_pairs": total_pairs,
                }
            if verified_pairs and len(verified_pairs) == total_pairs:
                return {
                    "status": "likely_compatible",
                    "match_type": "transitive",
                    "inference": "transitive",
                    "confidence": 0.75,
                    "packages": packages,
                    "notes": (
                        f"All {total_pairs} sub-pairs verified compatible. "
                        "Full stack inferred as likely compatible."
                    ),
                    "verified_pairs": verified_pairs,
                    "total_pairs": total_pairs,
                }
            if verified_pairs:
                return {
                    "status": "partially_verified",
                    "match_type": "transitive",
                    "inference": "transitive",
                    "confidence": 0.5,
                    "packages": packages,
                    "notes": (
                        f"{len(verified_pairs)}/{total_pairs} sub-pairs verified. "
                        "The remaining combinations are untested."
                    ),
                    "verified_pairs": verified_pairs,
                    "total_pairs": total_pairs,
                    "similar_stacks": await find_similar_stacks(packages, limit=5),
                }

        similar = await find_similar_stacks(packages, limit=5)
        return {
            "status": "untested",
            "match_type": "none",
            "packages": packages,
            "notes": "No verified data for this exact combination.",
            "similar_stacks": similar,
        }


async def find_similar_stacks(stack: dict, limit: int = 5) -> list[dict]:
    """Return stacks that share at least one package name with the request."""
    packages = _canon_stack(stack)
    if not packages:
        return []
    names = list(packages.keys())
    limit = max(1, min(int(limit or 5), 20))

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT stack_hash, packages, status, notes, source,
                   source_url, stars, reported_count, updated_at
            FROM compat_matrix
            WHERE packages ?| $1::text[]
            ORDER BY stars DESC, reported_count DESC
            LIMIT $2
            """,
            names, limit,
        )
    out = []
    for r in rows:
        d = dict(r)
        d["packages"] = _maybe_json(d.get("packages"))
        out.append(d)
    return out


def _maybe_json(value: Any) -> Any:
    """asyncpg returns jsonb as text in some contexts — normalise to dict."""
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


# --------------------------------------------------------------------------- #
# C. KNOWN BUGS
# --------------------------------------------------------------------------- #

async def get_bugs_for_package(
    ecosystem: str,
    package: str,
    version: str | None = None,
) -> list[dict]:
    """Return bugs for a package, optionally filtered to a version."""
    if not ecosystem or not package:
        return []
    pool = await get_pool()
    async with pool.acquire() as conn:
        if version:
            rows = await conn.fetch(
                """
                SELECT id, ecosystem, package_name, affected_version,
                       fixed_version, bug_id, title, description, severity,
                       status, source, source_url, labels,
                       created_at, updated_at
                FROM known_bugs
                WHERE ecosystem = $1
                  AND package_name = $2
                  AND (affected_version IS NULL
                       OR affected_version = '*'
                       OR affected_version = $3
                       OR $3 LIKE REPLACE(affected_version, '*', '%')
                       OR affected_version LIKE '%' || $3 || '%')
                ORDER BY
                  CASE severity
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                    ELSE 4 END,
                  updated_at DESC
                """,
                ecosystem.lower(), package, version,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, ecosystem, package_name, affected_version,
                       fixed_version, bug_id, title, description, severity,
                       status, source, source_url, labels,
                       created_at, updated_at
                FROM known_bugs
                WHERE ecosystem = $1 AND package_name = $2
                ORDER BY
                  CASE severity
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                    ELSE 4 END,
                  updated_at DESC
                """,
                ecosystem.lower(), package,
            )
    return [dict(r) for r in rows]


async def search_bugs(query: str, limit: int = 20) -> list[dict]:
    """Full-text search across bug titles + descriptions."""
    limit = max(1, min(int(limit or 20), 50))
    if not query or not str(query).strip():
        return []
    q = str(query).strip()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, ecosystem, package_name, affected_version,
                   fixed_version, bug_id, title, description, severity,
                   status, source, source_url, labels, updated_at,
                   ts_rank(
                     to_tsvector('english', coalesce(title, '') || ' '
                                           || coalesce(description, '')),
                     plainto_tsquery('english', $1)
                   ) AS rank
            FROM known_bugs
            WHERE to_tsvector('english', coalesce(title, '') || ' '
                                       || coalesce(description, ''))
                  @@ plainto_tsquery('english', $1)
               OR title ILIKE '%' || $1 || '%'
               OR description ILIKE '%' || $1 || '%'
            ORDER BY rank DESC, updated_at DESC
            LIMIT $2
            """,
            q, limit,
        )
    return [dict(r) for r in rows]


async def get_bugs_summary(
    ecosystem: str,
    package: str,
    version: str | None = None,
) -> dict:
    """Small summary used to decorate /api/check responses.

    Strategy:
      1. try an exact version match (if version provided)
      2. fall back to "any version" so the consumer still sees that bugs
         exist for the package (useful signal) — `scope` indicates which
    """
    all_bugs = await get_bugs_for_package(ecosystem, package, None)
    if not all_bugs:
        return {"bugs_count": 0, "bugs_severity": {}, "status_breakdown": {}, "link": None, "scope": "none"}

    scope = "all"
    bugs = all_bugs
    if version:
        matched = await get_bugs_for_package(ecosystem, package, version)
        if matched:
            bugs = matched
            scope = "version"

    sev: dict[str, int] = {}
    status: dict[str, int] = {}
    for b in bugs:
        s = (b.get("severity") or "unknown").lower()
        sev[s] = sev.get(s, 0) + 1
        st = (b.get("status") or "unknown").lower()
        status[st] = status.get(st, 0) + 1

    link = f"/api/bugs/{ecosystem}/{package}"
    if version and scope == "version":
        link += f"?version={version}"

    return {
        "bugs_count": len(bugs),
        "bugs_severity": sev,
        "status_breakdown": status,
        "link": link,
        "scope": scope,
    }


# --------------------------------------------------------------------------- #
# D. ALTERNATIVES (curated, DB-backed)
# --------------------------------------------------------------------------- #

async def get_alternatives(ecosystem: str, package: str) -> list[dict]:
    """Curated alternatives for a package, sorted by score desc.

    Reads from the alternatives table (177+ curated pairs across npm/pypi/cargo).
    Each entry: {name, reason, builtin}. 'builtin' flags language/stdlib
    replacements (e.g. fs.rm, std::sync::LazyLock) that are NOT installable
    from a registry.
    """
    ecosystem = (ecosystem or "").lower()
    if not ecosystem or not package:
        return []
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            '''
            SELECT a.alternative_name AS name,
                   a.reason,
                   a.alternative_is_builtin AS builtin
            FROM alternatives a
            JOIN packages p ON p.id = a.package_id
            WHERE p.ecosystem = $1 AND p.name = $2
            ORDER BY a.score DESC, a.alternative_name
            ''',
            ecosystem, package,
        )
    return [
        {"name": r["name"], "reason": r["reason"], "builtin": r["builtin"]}
        for r in rows
    ]


# --------------------------------------------------------------------------- #
# E. BREAKING CHANGES
# --------------------------------------------------------------------------- #

async def get_breaking_changes(
    ecosystem: str,
    package: str,
    from_version: str | None = None,
    to_version: str | None = None,
) -> list[dict]:
    """Breaking changes for a package, optionally scoped to a version transition.

    Reads from breaking_changes table (48+ curated transitions across major
    packages). Each entry: {from_version, to_version, change_type,
    description, migration_hint}.
    """
    ecosystem = (ecosystem or "").lower()
    if not ecosystem or not package:
        return []
    pool = await get_pool()
    async with pool.acquire() as conn:
        sql = '''
            SELECT b.from_version, b.to_version, b.change_type,
                   b.description, b.migration_hint
            FROM breaking_changes b
            JOIN packages p ON p.id = b.package_id
            WHERE p.ecosystem = $1 AND p.name = $2
        '''
        params: list = [ecosystem, package]
        if from_version:
            params.append(from_version)
            sql += f" AND b.from_version = ${len(params)}"
        if to_version:
            params.append(to_version)
            sql += f" AND b.to_version = ${len(params)}"
        sql += " ORDER BY b.to_version DESC, b.from_version DESC, b.change_type"
        rows = await conn.fetch(sql, *params)
    return [
        {"from_version": r["from_version"], "to_version": r["to_version"],
         "change_type": r["change_type"], "description": r["description"],
         "migration_hint": r["migration_hint"]}
        for r in rows
    ]
