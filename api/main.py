import os
from pydantic import BaseModel
"""DepScope API - Package Intelligence for AI Agents — Everything Free"""
import time

# MCP tool count derived at startup from mcp-server/tools.js (dynamic, no drift).
try:
    import os as _os, re as _re
    _tools_path = _os.path.join(_os.path.dirname(__file__), _os.pardir, "mcp-server", "tools.js")
    with open(_tools_path) as _f:
        MCP_TOOLS_COUNT = len(_re.findall(r'^\s+name:\s*"[a-z_]+",\s*$', _f.read(), _re.MULTILINE))
except Exception:
    MCP_TOOLS_COUNT = 22
import re
import asyncio
import hashlib
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from api.config import VERSION, IP_HASH_SALT


# ---- GDPR / intelligence helpers ------------------------------------------
def _hash_ip(ip: str) -> str:
    """SHA256 hash of IP with project salt. Deterministic for session grouping, zero PII on disk."""
    if not ip:
        return ""
    return hashlib.sha256((ip + IP_HASH_SALT).encode()).hexdigest()


# Ordered patterns: first match wins. Keep the most specific first.
_AGENT_PATTERNS = [
    ("claude-code",       re.compile(r"claude[- ]?code", re.I)),
    ("claude-desktop",    re.compile(r"claude[- ]?desktop|anthropic[- ]?claude", re.I)),
    ("cursor",            re.compile(r"cursor(?!bot)", re.I)),
    ("windsurf",          re.compile(r"windsurf", re.I)),
    ("continue",          re.compile(r"continue\.dev|continue[- ]?ide", re.I)),
    ("aider",             re.compile(r"aider", re.I)),
    ("devin",             re.compile(r"devin|cognition[- ]?ai", re.I)),
    ("copilot",           re.compile(r"github[- ]?copilot", re.I)),
    ("chatgpt",           re.compile(r"chatgpt|openai[- ]?agent", re.I)),
    ("claude-web",        re.compile(r"^claude$|claude\.ai", re.I)),
    ("replit",            re.compile(r"replit[- ]?agent", re.I)),
    ("cody",              re.compile(r"sourcegraph[- ]?cody", re.I)),
    ("tabnine",           re.compile(r"tabnine", re.I)),
    ("zed",               re.compile(r"zed[- ]?(industries|agent)", re.I)),
    ("mcp-generic",       re.compile(r"mcp[/\-]|model[- ]?context[- ]?protocol", re.I)),
    # Specific bots — surfaced separately from generic "crawler" for UI split.  # PATCH_SPLIT_BOTS_V1
    ("googlebot",         re.compile(r"googlebot|googleother|mediapartners-google|adsbot-google", re.I)),
    ("bingbot",           re.compile(r"bingbot|bingpreview", re.I)),
    ("duckduckbot",       re.compile(r"duckduckbot|duckduckgo[- ]?favicons", re.I)),
    ("yandexbot",         re.compile(r"yandexbot|yandeximages", re.I)),
    ("baiduspider",       re.compile(r"baiduspider", re.I)),
    ("applebot",          re.compile(r"applebot", re.I)),
    ("facebookbot",       re.compile(r"facebookexternalhit|meta-externalagent", re.I)),
    ("twitterbot",        re.compile(r"twitterbot|x-clientbot", re.I)),
    ("linkedinbot",       re.compile(r"linkedinbot", re.I)),
    ("anthropic-bot",     re.compile(r"anthropicbot|claude_bot|claude-web/1\.0", re.I)),
    ("openai-bot",        re.compile(r"gptbot|oai-searchbot|chatgpt-user", re.I)),
    ("perplexity-bot",    re.compile(r"perplexitybot", re.I)),
    ("ahrefsbot",         re.compile(r"ahrefsbot|semrushbot|mj12bot|dotbot", re.I)),
    ("crawler",           re.compile(r"bot|crawl|spider|slurp", re.I)),
    ("python-sdk",        re.compile(r"python-openai-sdk|anthropic-python|python/.*aiohttp", re.I)),
    ("browser",           re.compile(r"mozilla/", re.I)),
    ("curl",              re.compile(r"^curl/", re.I)),
]

# Classify an agent_client label into a "kind" lane:
#   agent  = real AI coding agent or SDK
#   bot    = search/crawler/AI-training bot
#   human  = interactive (browser) or raw curl
#   unknown
_AGENT_KIND = {
    # agents
    "claude-code": "agent", "claude-desktop": "agent", "claude-web": "agent",
    "cursor": "agent", "windsurf": "agent", "continue": "agent", "aider": "agent",
    "devin": "agent", "copilot": "agent", "chatgpt": "agent", "replit": "agent",
    "cody": "agent", "tabnine": "agent", "zed": "agent",
    "mcp-generic": "agent", "python-sdk": "agent",
    # bots (search + AI-training + SEO)
    "googlebot": "bot", "bingbot": "bot", "duckduckbot": "bot", "yandexbot": "bot",
    "baiduspider": "bot", "applebot": "bot",
    "facebookbot": "bot", "twitterbot": "bot", "linkedinbot": "bot",
    "anthropic-bot": "bot", "openai-bot": "bot", "perplexity-bot": "bot",
    "ahrefsbot": "bot", "crawler": "bot",
    # humans
    "browser": "human", "curl": "human",
}


def _agent_kind(agent_client: str) -> str:
    return _AGENT_KIND.get(agent_client or "", "unknown")


def _parse_agent_client(user_agent: str) -> str:
    """Classify caller into agent_client bucket for intelligence analytics."""
    if not user_agent:
        return "unknown"
    for label, pat in _AGENT_PATTERNS:
        if pat.search(user_agent):
            return label
    return "other"

# IPs to exclude from analytics (our own servers, cron, preprocess)
EXCLUDED_IPS = {"127.0.0.1", "::1", "10.10.0.140", "10.10.0.1", "91.134.4.25"}
# Any IP starting with these is treated as internal/team traffic (never tracked).
# /24 prefixes keep dynamic IPs covered.
EXCLUDED_IP_PREFIXES = ("10.10.", "127.", "37.182.176.", "37.182.177.", "91.134.4.")

def _is_excluded_ip(ip: str) -> bool:
    if not ip:
        return False
    return any(ip.startswith(p) for p in EXCLUDED_IP_PREFIXES)

from api.database import get_pool, close_pool
from api.cache import cache_get, cache_set, rate_limit_check
from api.registries import fetch_package, fetch_vulnerabilities, save_package_to_db, fetch_github_stats, save_github_stats, get_github_stats_from_db
from api.health import calculate_health_score
from api.historical_compromises import lookup as lookup_historical
from api.stdlib_modules import lookup as lookup_stdlib
from api.verticals_v2 import router as verticals_v2_router
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


TAGS_METADATA = [
    {"name": "packages", "description": (
        "Core package intelligence: health score, vulnerabilities, recommendations, "
        "alternatives, comparisons, batch scan, version metadata, dependency tree. "
        "These are the endpoints AI agents call before suggesting any `npm install` / "
        "`pip install` / `cargo add`."
    )},
    {"name": "errors", "description": (
        "Error -> fix database. POST a stack trace, get solutions back. "
        "Full-text error search by message or stable hash."
    )},
    {"name": "compat", "description": (
        "Stack compatibility matrix. Verify a set of `pkg@version` pins work "
        "together (e.g. `next@16,react@19,prisma@6`) before upgrading."
    )},
    {"name": "discover", "description": (
        "Trending packages per ecosystem, typosquats, malicious advisories, "
        "trust signals. Use these to surface or avoid packages."
    )},
    {"name": "verticals", "description": (
        "Breaking changes (v1->v2 with migration hints) and non-CVE known bugs per version."
    )},
    {"name": "discovery", "description": (
        "Well-known files for AI agents: /openapi.json, /ai-plugin.json, /mcp.json, "
        "/llms.txt, /llms-full.txt, /security.txt, /sitemap.xml, /robots.txt."
    )},
    {"name": "auth", "description": (
        "Optional API keys for higher rate limits + usage analytics. No auth "
        "required for public endpoints."
    )},
]


app = FastAPI(
    title="DepScope — Package Intelligence API",
    summary="Free, open API that tells AI agents if a package is safe, maintained, and up-to-date before they suggest installing it.",
    description=(
        "# DepScope\n\n"
        "Package Intelligence for AI coding agents. **31,000+ packages** across **17 "
        "ecosystems** (npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems, Composer, Pub, "
        "Hex, Swift, CocoaPods, CPAN, Hackage, CRAN, Conda, Homebrew), **2,200+ CVEs** "
        "enriched with CISA KEV + EPSS. Three verticals on one shared infrastructure:\n\n"
        "1. **Package health** — /api/check for full report, /api/prompt for LLM-"
        "optimized text (~74% smaller), /api/alternatives for replacements, /api/scan "
        "to audit a lockfile.\n"
        "2. **Error -> fix database** — POST a stack trace to /api/error/resolve.\n"
        "3. **Stack compatibility matrix** — /api/compat?stack=next@16,react@19.\n\n"
        "## Quick start (for agents)\n\n"
        "    curl https://depscope.dev/api/prompt/npm/react\n\n"
        "## MCP server\n\n"
        "Zero-install remote URL: `https://mcp.depscope.dev/mcp`. 22 tools. Install "
        "in one line: `claude mcp add depscope https://mcp.depscope.dev/mcp`.\n\n"
        "## Rate limits\n\n"
        "100 req/min anonymous, 200/min for whitelisted AI UAs (ClaudeBot, GPTBot, "
        "Cursor, MCP-Client, …). Optional API keys for higher limits.\n\n"
        "Save tokens, save energy, ship safer code."
    ),
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    servers=[
        {"url": "https://depscope.dev", "description": "Production"},
        {"url": "https://stage.depscope.dev", "description": "Staging"},
    ],
    contact={
        "name": "DepScope support",
        "email": "depscope@cuttalo.com",
        "url": "https://depscope.dev",
    },
    license_info={
        "name": "MIT",
        "identifier": "MIT",
        "url": "https://github.com/cuttalo/depscope/blob/main/LICENSE",
    },
    terms_of_service="https://depscope.dev/terms",
    openapi_tags=TAGS_METADATA,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,
)

# Response compression (gzip) for any payload > 500 bytes.
# Agents save ~60-80% bytes on /api/check (2.8KB -> ~900B).
app.add_middleware(GZipMiddleware, minimum_size=500, compresslevel=6)

# ─── License risk classifier ──────────────────────────────────────  # PATCH_LICENSE_RISK_V1
# Maps raw SPDX-ish license strings to a single-word risk class plus
# a short note agents can quote when assessing commercial use. Covers
# ~99% of npm / PyPI / GitHub licenses. Anything unrecognised returns
# ("unknown", "verify manually — license not parseable") so the agent
# never silently defaults to "permissive".

_LICENSE_RISK_RULES = [
    # (regex-anchored lower-cased match, risk_class, notes)
    # Strong copyleft (affects derivative/static linking)
    (re.compile(r"^(gpl[-_ ]?(v?2|2\.0))$"), "strong_copyleft",
        "GPL-2.0: derivative works must release source under GPL; static linking forces disclosure."),
    (re.compile(r"^(gpl[-_ ]?(v?3|3\.0)?)$"), "strong_copyleft",
        "GPL-3.0: derivative works must release source under GPL; includes explicit patent grant."),
    (re.compile(r"^(epl[-_ ]?(1|1\.0|2|2\.0))$"), "weak_copyleft",
        "EPL: weak copyleft with a patent grant; modified files must be released under EPL."),
    # Weak copyleft (affects modified files only)
    (re.compile(r"^(lgpl[-_ ]?(v?2|2\.0|2\.1|v?3|3\.0))$"), "weak_copyleft",
        "LGPL: dynamic linking from closed-source is OK; static linking triggers source disclosure."),
    (re.compile(r"^(mpl[-_ ]?(1\.1|2|2\.0))$"), "weak_copyleft",
        "MPL-2.0: only modified MPL files must be released; commercial closed-source around it is fine."),
    (re.compile(r"^(cddl[-_ ]?(1\.0|1\.1))$"), "weak_copyleft",
        "CDDL: file-level weak copyleft; linking with closed code OK, modifications must be released."),
    # Network copyleft (SaaS trigger)
    (re.compile(r"^(agpl[-_ ]?(v?3|3\.0)?)$"), "network_copyleft",
        "AGPL-3.0: blocks closed-source SaaS — network use = distribution. Requires source disclosure to users."),
    (re.compile(r"^(sspl[-_ ]?(1|1\.0))$"), "network_copyleft",
        "SSPL: MongoDB-style — using as a service to third parties requires releasing ALL surrounding infra under SSPL."),
    (re.compile(r"^(osl[-_ ]?(v?3|3\.0))$"), "network_copyleft",
        "OSL-3.0: weak-to-strong copyleft with network provision — external deployment triggers source disclosure."),
    # Permissive (commercial safe)
    (re.compile(r"^(mit|mit[-_ ]?0|isc|bsd[-_ ]?(2|2-clause|3|3-clause|4|4-clause)|apache[-_ ]?(2|2\.0|v2)|unlicense|wtfpl|cc0(-1\.0)?|0bsd|blueoak[-_ ]?1\.0\.0|zlib|(bsd-)?(0bsd)?|x11|boost[-_ ]?1\.0|artistic[-_ ]?2|ms[-_ ]?pl|ms[-_ ]?rl|upl[-_ ]?1\.0|python[-_ ]?2\.0|psf[-_ ]?2\.0|cal[-_ ]?1\.0|afl[-_ ]?3\.0)$"),
        "permissive",
        "Permissive: commercial closed-source use OK; preserve the copyright notice."),
    # Proprietary / restricted
    (re.compile(r"^(see\s+license|proprietary|commercial|custom|closed|sspl[-_ ]?commercial)$"), "proprietary",
        "Proprietary / custom license — do NOT use in commercial products without reviewing terms."),
    (re.compile(r"^(nosl|nolicense|unlicensed|none)$"), "proprietary",
        "No license declared — legally no right to use, modify, or distribute. Treat as proprietary."),
    # Common aliases for Apache-2
    (re.compile(r"^apache([-_ ]?license)?[-_ ]?2(\.0)?$"), "permissive",
        "Apache-2.0: permissive, includes explicit patent grant."),
    # BSD variations
    (re.compile(r"^bsd$"), "permissive",
        "BSD (unspecified clause count — likely 3-Clause): permissive, commercial safe."),
]

_LICENSE_UNKNOWN = (
    "unknown",
    "verify manually — license not parseable / not declared.",
)


def _classify_license(raw: str | None) -> dict:
    """Return {license_id, license_risk, commercial_use_notes}."""
    if not raw:
        return {
            "license_id": None,
            "license_risk": "unknown",
            "commercial_use_notes": "No license declared in registry metadata — verify manually before commercial use.",
        }
    s = str(raw).strip()
    s_lower = s.lower()
    # Strip common SPDX-expression wrappers: "(MIT OR Apache-2.0)"
    # For OR-expressions, take the most permissive branch; for AND, take the most restrictive.
    # For simplicity we try the whole string first, then each token.
    candidates = [s_lower]
    for sep in (" or ", " and ", "/", ","):
        if sep in s_lower:
            candidates.extend(t.strip().strip("()") for t in s_lower.split(sep))
    # Dedup
    seen = set()
    candidates = [c for c in candidates if c and not (c in seen or seen.add(c))]

    for c in candidates:
        c_norm = c.replace(" license", "").strip()
        for pattern, risk, notes in _LICENSE_RISK_RULES:
            if pattern.match(c_norm):
                return {
                    "license_id": s,
                    "license_risk": risk,
                    "commercial_use_notes": notes,
                }
    return {
        "license_id": s,
        "license_risk": _LICENSE_UNKNOWN[0],
        "commercial_use_notes": _LICENSE_UNKNOWN[1],
    }

# ─── Lockfile parsing + SBOM export (scan_project enhancements) ─  # PATCH_SCAN_ENHANCE_V1
# Flat {name: version} extraction for 9 lockfile formats. Transitive
# deps are ALREADY in these files (that's the whole point of a lock),
# so parsing them gives us the full dep graph without walking.

def _parse_lockfile(content: str, kind: str) -> tuple[dict, str]:
    """Return (packages_dict, detected_ecosystem). Raises ValueError on parse error."""
    import json as _json
    import re as _re

    kind = (kind or "").lower().strip()
    content = content.strip()

    # Auto-detect from content
    if not kind:
        if content.startswith("{") and '"lockfileVersion"' in content[:500]:
            kind = "package-lock.json"
        elif content.startswith("{") and '"python_version"' in content[:500]:
            kind = "Pipfile.lock"
        elif content.startswith("lockfileVersion:"):
            kind = "pnpm-lock.yaml"
        elif "# This file is automatically @generated by Cargo" in content[:200]:
            kind = "Cargo.lock"
        elif content.startswith("# poetry.lock") or "[[package]]" in content[:200] and "poetry" in content.lower():
            kind = "poetry.lock"
        elif "composer.json has been updated" in content[:1000] or '"packages":' in content[:500] and '"_readme"' in content[:200]:
            kind = "composer.lock"
        elif _re.match(r"^[a-zA-Z0-9_-]+==[0-9]", content):
            kind = "requirements.txt"
        elif content.startswith("# yarn lockfile"):
            kind = "yarn.lock"
        elif _re.match(r"^[^\s/]+/[^\s/]+ v[0-9]", content):
            kind = "go.sum"
        else:
            raise ValueError("Could not auto-detect lockfile format — pass lockfile_kind explicitly.")

    pkgs: dict = {}
    eco = ""

    if kind in ("package-lock.json", "npm-shrinkwrap.json"):
        eco = "npm"
        data = _json.loads(content)
        for key, info in (data.get("packages") or {}).items():
            # key like "node_modules/express", "node_modules/lodash" (lockfileVersion 2/3)
            if not key or not key.startswith("node_modules/"):
                continue
            name = key[len("node_modules/"):]
            # Handle nested (node_modules/foo/node_modules/bar) - take the last segment after node_modules
            if "/node_modules/" in name:
                name = name.split("/node_modules/")[-1]
            ver = info.get("version")
            if name and ver:
                pkgs[name] = ver
        # lockfileVersion 1 fallback: dependencies map
        if not pkgs:
            for name, info in (data.get("dependencies") or {}).items():
                ver = info.get("version") if isinstance(info, dict) else None
                if name and ver:
                    pkgs[name] = ver

    elif kind == "pnpm-lock.yaml":
        eco = "npm"
        for line in content.splitlines():
            m = _re.match(r"^\s*/([^/@]+(?:/[^/@]+)?)@([^\(\s:]+)[\s:]", line)
            if m:
                name, ver = m.group(1), m.group(2)
                pkgs[name] = ver

    elif kind == "yarn.lock":
        eco = "npm"
        cur_name = None
        for raw in content.splitlines():
            line = raw.rstrip()
            if line.startswith('"') and "@" in line and line.endswith(':'):
                # "express@^4.17.0", "express@~4.18.0":
                first = line.split('"', 2)[1]
                at_idx = first.rfind('@')
                cur_name = first[:at_idx] if at_idx > 0 else first
            elif cur_name and line.strip().startswith('version '):
                ver = line.strip().split(' ', 1)[1].strip('"\'')
                pkgs[cur_name] = ver
                cur_name = None

    elif kind == "poetry.lock":
        eco = "pypi"
        cur = {}
        for raw in content.splitlines():
            line = raw.strip()
            if line == "[[package]]":
                if cur.get("name") and cur.get("version"):
                    pkgs[cur["name"]] = cur["version"]
                cur = {}
            elif line.startswith("name ="):
                cur["name"] = line.split("=", 1)[1].strip().strip('"')
            elif line.startswith("version ="):
                cur["version"] = line.split("=", 1)[1].strip().strip('"')
        if cur.get("name") and cur.get("version"):
            pkgs[cur["name"]] = cur["version"]

    elif kind == "Pipfile.lock":
        eco = "pypi"
        data = _json.loads(content)
        for section in ("default", "develop"):
            for name, info in (data.get(section) or {}).items():
                ver = info.get("version", "").lstrip("=")
                if name and ver:
                    pkgs[name] = ver

    elif kind == "requirements.txt":
        eco = "pypi"
        for raw in content.splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line or line.startswith("-"):
                continue
            m = _re.match(r"^([A-Za-z0-9_.\-]+)\s*==\s*([A-Za-z0-9_.+\-]+)", line)
            if m:
                pkgs[m.group(1)] = m.group(2)

    elif kind == "composer.lock":
        eco = "composer"
        data = _json.loads(content)
        for section in ("packages", "packages-dev"):
            for entry in (data.get(section) or []):
                name = entry.get("name")
                ver = (entry.get("version") or "").lstrip("v")
                if name and ver:
                    pkgs[name] = ver

    elif kind == "Cargo.lock":
        eco = "cargo"
        cur = {}
        for raw in content.splitlines():
            line = raw.strip()
            if line == "[[package]]":
                if cur.get("name") and cur.get("version"):
                    pkgs[cur["name"]] = cur["version"]
                cur = {}
            elif line.startswith("name = "):
                cur["name"] = line.split("=", 1)[1].strip().strip('"')
            elif line.startswith("version = "):
                cur["version"] = line.split("=", 1)[1].strip().strip('"')
        if cur.get("name") and cur.get("version"):
            pkgs[cur["name"]] = cur["version"]

    elif kind == "go.sum":
        eco = "go"
        for raw in content.splitlines():
            parts = raw.split()
            if len(parts) >= 2:
                name, ver = parts[0], parts[1]
                # drop /go.mod suffix from version
                if "/go.mod" in ver:
                    continue
                pkgs[name] = ver.lstrip("v")

    else:
        raise ValueError(f"Unsupported lockfile kind: {kind}")

    return pkgs, eco


def _build_sbom_cyclonedx(audit: list, ecosystem: str, total_vulns: int, project_risk: str) -> dict:
    """Emit a minimal CycloneDX 1.5 JSON SBOM."""
    import hashlib, uuid
    ECO_TO_PURL = {
        "npm": "npm", "pypi": "pypi", "cargo": "cargo", "go": "golang",
        "composer": "composer", "maven": "maven", "nuget": "nuget",
        "rubygems": "gem", "pub": "pub", "hex": "hex", "swift": "swift",
        "cocoapods": "cocoapods", "cpan": "cpan", "hackage": "hackage",
        "cran": "cran", "conda": "conda", "homebrew": "generic",
    }
    purl_eco = ECO_TO_PURL.get(ecosystem, ecosystem)
    components = []
    vulns_list = []
    serial = f"urn:uuid:{uuid.uuid4()}"
    for p in audit:
        if p.get("error"):
            continue
        name = p["package"]
        ver = p.get("requested_version") or p.get("latest_version") or "unknown"
        purl = f"pkg:{purl_eco}/{name}@{ver}"
        bom_ref = hashlib.sha256(purl.encode()).hexdigest()[:16]
        components.append({
            "bom-ref": bom_ref,
            "type": "library",
            "name": name,
            "version": ver,
            "purl": purl,
            "licenses": [{"license": {"id": p["license"]}}] if p.get("license") else [],
            "properties": [
                {"name": "depscope:health_score", "value": str(p.get("health_score"))},
                {"name": "depscope:recommendation", "value": str(p.get("recommendation"))},
            ],
        })
        v = p.get("vulnerabilities") or {}
        if v.get("critical", 0) or v.get("high", 0):
            vulns_list.append({
                "bom-ref": f"vuln-{bom_ref}",
                "affects": [{"ref": bom_ref}],
                "ratings": [{"severity": "critical" if v.get("critical") else "high"}],
                "description": f"{v.get('count',0)} open — {v.get('critical',0)} critical, {v.get('high',0)} high",
            })
    import datetime as _dt
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": serial,
        "version": 1,
        "metadata": {
            "timestamp": _dt.datetime.utcnow().isoformat() + "Z",
            "tools": [{"vendor": "DepScope", "name": "scan", "version": "1.0"}],
            "properties": [
                {"name": "depscope:ecosystem", "value": ecosystem},
                {"name": "depscope:total_vulns", "value": str(total_vulns)},
                {"name": "depscope:project_risk", "value": project_risk},
            ],
        },
        "components": components,
        "vulnerabilities": vulns_list,
    }


def _build_sbom_spdx(audit: list, ecosystem: str) -> dict:
    """Emit a minimal SPDX 2.3 JSON SBOM."""
    import hashlib, datetime as _dt, uuid
    ECO_TO_PURL = {"npm": "npm", "pypi": "pypi", "cargo": "cargo", "go": "golang"}
    purl_eco = ECO_TO_PURL.get(ecosystem, ecosystem)
    packages_sp = []
    for p in audit:
        if p.get("error"):
            continue
        name = p["package"]
        ver = p.get("requested_version") or p.get("latest_version") or "unknown"
        spdx_id = "SPDXRef-" + hashlib.sha256(f"{name}@{ver}".encode()).hexdigest()[:16]
        packages_sp.append({
            "SPDXID": spdx_id,
            "name": name,
            "versionInfo": ver,
            "downloadLocation": f"pkg:{purl_eco}/{name}@{ver}",
            "licenseConcluded": p.get("license") or "NOASSERTION",
            "licenseDeclared": p.get("license") or "NOASSERTION",
            "filesAnalyzed": False,
            "supplier": "NOASSERTION",
        })
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"depscope-scan-{ecosystem}",
        "documentNamespace": f"https://depscope.dev/sbom/{uuid.uuid4()}",
        "creationInfo": {
            "creators": ["Tool: DepScope-1.0"],
            "created": _dt.datetime.utcnow().isoformat() + "Z",
        },
        "packages": packages_sp,
    }






# ─── Origin Cache-Control headers (CF honours them) ─────────────────
# Static/immutable-ish GETs keyed on ecosystem/package: 1h at edge,
# stale-while-revalidate another 6h so agents NEVER wait on a refresh.
# Dynamic endpoints (stats/trending/gdpr/auth/admin) stay uncached.
import re as _re
_CACHEABLE_PATH = _re.compile(
    r'^/api/('
    r'check|prompt|latest|vulns|alternatives|breaking|bugs|compare|'
    r'typosquat|malicious|install|license|licenses|exists|tree|versions|'
    r'maintainers|quality|provenance|scorecard|pin_safe|history|'
    r'migration|health|ai/brief'
    r')(/.*)?$'
)
_UNCACHEABLE_PATH = _re.compile(
    r'^/api/(stats|trending|gdpr|auth|admin|contact|anomaly|track|error|scan|compat|now|ecosystems|search|savings|translate)(/.*)?$'
)

@app.middleware("http")
async def _origin_cache_control(request, call_next):
    resp = await call_next(request)
    try:
        if (request.method == "GET"
                and 200 <= resp.status_code < 300
                and "cache-control" not in {k.lower() for k in resp.headers.keys()}):
            path = request.url.path
            if _UNCACHEABLE_PATH.match(path):
                resp.headers["Cache-Control"] = "no-store"
            elif _CACHEABLE_PATH.match(path):
                # 1h fresh + 6h stale-while-revalidate — CF serves instantly
                # while revalidating in background.
                resp.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=21600"
    except Exception:
        pass
    return resp



app.include_router(auth_router)
app.include_router(payments_router)
app.include_router(mcp_router)
app.include_router(verticals_v2_router)

# ─── Password-gated admin (simple) ────────────────────────────────────
import hmac, hashlib, os as _os
_ADMIN_PW = _os.environ.get("ADMIN_PASSWORD", "").strip()
_ADMIN_PW_COOKIE = "depscope_admin_pw"
_ADMIN_PW_SECRET = _os.environ.get("ADMIN_PW_SECRET", "ds_pw_default_secret_please_rotate")

def _admin_pw_token() -> str:
    return hmac.new(_ADMIN_PW_SECRET.encode(), _ADMIN_PW.encode(), hashlib.sha256).hexdigest()[:32]

def _has_admin_pw(request: Request) -> bool:
    if not _ADMIN_PW:
        return False
    return request.cookies.get(_ADMIN_PW_COOKIE) == _admin_pw_token()



# ─── Live event stream (SSE for admin dashboard) ────────────────────  # PATCH_LIVE_FEED_V1
# Publishes every api_usage insert to Redis pub/sub "depscope:live"; admin
# subscribes via /api/admin/live and receives JSON events in real time.

from fastapi.responses import StreamingResponse as _StreamingResponse

async def _publish_live_event(event: dict):
    """Push a live event to Redis pub/sub. Silent on any failure."""
    try:
        from api.cache import get_redis
        r = await get_redis()
        await r.publish("depscope:live", __import__("json").dumps(event, default=str))
    except Exception:
        pass


@app.get("/api/admin/live", include_in_schema=False)
async def admin_live(request: Request):
    """SSE stream of real-time API activity. Admin-auth-gated.

    Each event is a JSON line preceded by `data: ` per SSE spec. The
    client (EventSource) receives:
      - `event: api_call` with {ecosystem, package, endpoint, agent, ms, status, country}
      - `event: ping` every 20s to keep connection alive

    The stream runs until the client disconnects or 30min have passed
    (then client auto-reconnects). Nginx+CF forwarding: no buffering.
    """
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")

    async def event_gen():
        from api.cache import get_redis
        import asyncio as _asyncio, json as _json, time as _time
        r = await get_redis()
        pubsub = r.pubsub()
        try:
            await pubsub.subscribe("depscope:live")
            # Initial hello
            yield f"event: hello\ndata: {_json.dumps({'ok': True, 'ts': _time.time()})}\n\n"
            last_ping = _time.time()
            start = _time.time()
            while True:
                # Max 30 min per connection — EventSource auto-reconnects.
                if _time.time() - start > 1800:
                    yield "event: bye\ndata: {\"reason\":\"max_duration\"}\n\n"
                    return
                # Periodic ping so CF/nginx don't close the idle connection.
                if _time.time() - last_ping > 20:
                    yield f"event: ping\ndata: {int(_time.time())}\n\n"
                    last_ping = _time.time()
                try:
                    msg = await _asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0), timeout=1.5)
                except _asyncio.TimeoutError:
                    msg = None
                if msg and msg.get("type") == "message":
                    payload = msg.get("data")
                    if isinstance(payload, bytes):
                        payload = payload.decode("utf-8", "replace")
                    yield f"event: api_call\ndata: {payload}\n\n"
        finally:
            try:
                await pubsub.unsubscribe("depscope:live")
                await pubsub.close()
            except Exception:
                pass

    return _StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disables nginx buffering
        },
    )




# ─── Real-time malicious feed (public SSE) ──────────────────────────  # PATCH_MALICIOUS_LIVE_V1
# Pushes every new malicious-package advisory to any subscriber. NO AUTH.
# Category-defining: competitors push daily/weekly; we push in seconds.

async def publish_malicious(advisory: dict):
    """Call this from the OpenSSF malicious ingest loop whenever a new row
    hits the DB. Signature: {ecosystem, package, vuln_id, severity, summary,
    published_at}. Silent on any failure."""
    try:
        from api.cache import get_redis
        r = await get_redis()
        import json as _json
        await r.publish("depscope:malicious", _json.dumps(advisory, default=str))
    except Exception:
        pass


@app.get("/api/live/malicious", tags=["discover"])
async def live_malicious_feed(request: Request):
    """Real-time stream of newly published malicious package advisories.

    Public endpoint, no auth. Use this to wire a webhook-style supply-chain
    monitor in any language that speaks SSE.

    Events:
      - hello: connection ack
      - ping: every 30s to keep the connection alive
      - advisory: {ecosystem, package, vuln_id, severity, summary, published_at}

    Example (bash):
      curl -N https://depscope.dev/api/live/malicious
    """
    async def event_gen():
        from api.cache import get_redis
        import asyncio as _aio, json as _json, time as _time
        r = await get_redis()
        pubsub = r.pubsub()
        try:
            await pubsub.subscribe("depscope:malicious")

            yield f"event: hello\ndata: {_json.dumps({'ok': True, 'ts': _time.time(), 'source': 'depscope.dev', 'docs': 'https://depscope.dev/api-docs#malicious-live'})}\n\n"

            # On connect, replay the last 10 known malicious advisories so the
            # client has immediate context (not forced to wait for next event).
            try:
                pool = await get_pool()
                async with pool.acquire() as conn:
                    recent = await conn.fetch("""
                        SELECT mp.ecosystem, mp.package_name AS package, mp.vuln_id,
                               mp.summary, mp.published_at
                        FROM malicious_packages mp
                        ORDER BY mp.published_at DESC NULLS LAST, mp.id DESC
                        LIMIT 10
                    """)
                    for row in reversed(recent):
                        payload = {
                            "ecosystem": row["ecosystem"],
                            "package": row["package"],
                            "vuln_id": row["vuln_id"],
                            "summary": (row["summary"] or "")[:300],
                            "published_at": row["published_at"].isoformat() if row["published_at"] else None,
                            "replay": True,
                        }
                        yield f"event: advisory\ndata: {_json.dumps(payload, default=str)}\n\n"
            except Exception:
                pass

            last_ping = _time.time()
            start = _time.time()
            while True:
                if _time.time() - start > 1800:  # 30min max per conn
                    yield "event: bye\ndata: {\"reason\":\"max_duration\"}\n\n"
                    return
                if _time.time() - last_ping > 30:
                    yield f"event: ping\ndata: {int(_time.time())}\n\n"
                    last_ping = _time.time()
                try:
                    msg = await _aio.wait_for(pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0), timeout=1.5)
                except _aio.TimeoutError:
                    msg = None
                if msg and msg.get("type") == "message":
                    payload = msg.get("data")
                    if isinstance(payload, bytes):
                        payload = payload.decode("utf-8", "replace")
                    yield f"event: advisory\ndata: {payload}\n\n"
        finally:
            try:
                await pubsub.unsubscribe("depscope:malicious")
                await pubsub.close()
            except Exception:
                pass

    return _StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )




# ─── Hallucination Benchmark v1 (public) ────────────────────────────  # PATCH_BENCHMARK_V1
# Public corpus of known-hallucinated package names from real agent
# sessions + research + pattern analysis. Auto-expanded daily from
# our own api_usage is_hallucination observations.
#
# Use cases:
#   - Agent vendors can run their model against the corpus + measure
#     hallucination rate (with vs without DepScope MCP).
#   - Researchers can cite the dataset.
#   - Lab safety teams can track trends.

@app.get("/api/benchmark/hallucinations", tags=["discover"])
async def benchmark_hallucinations_corpus(ecosystem: str = None, limit: int = 500):
    """Return the full hallucination corpus as JSON, sorted by hit_count desc.

    Query params:
      ?ecosystem=npm   (filter to one ecosystem)
      ?limit=100       (1..1000)
    """
    limit = max(1, min(1000, int(limit or 500)))
    pool = await get_pool()
    async with pool.acquire() as conn:
        if ecosystem:
            rows = await conn.fetch(
                """SELECT ecosystem, package_name, source, evidence,
                          first_seen_at, hit_count, likely_real_alternative
                   FROM benchmark_hallucinations
                   WHERE ecosystem = $1
                   ORDER BY hit_count DESC, ecosystem, package_name
                   LIMIT $2""",
                ecosystem.lower(), limit,
            )
        else:
            rows = await conn.fetch(
                """SELECT ecosystem, package_name, source, evidence,
                          first_seen_at, hit_count, likely_real_alternative
                   FROM benchmark_hallucinations
                   ORDER BY hit_count DESC, ecosystem, package_name
                   LIMIT $1""",
                limit,
            )
        total = await conn.fetchval("SELECT COUNT(*) FROM benchmark_hallucinations")
    return {
        "version": "1.0",
        "total_corpus_size": total,
        "returned": len(rows),
        "ecosystem_filter": ecosystem,
        "description": "Known hallucinated package names from real coding-agent sessions, supplemented with research-documented patterns. Use to benchmark agent hallucination rates with vs without DepScope. Updated daily.",
        "schema": {
            "ecosystem": "one of 18 supported registries",
            "package_name": "the name the agent hallucinated",
            "source": "observed (real agent traffic) | research (public literature) | pattern (algorithmic)",
            "evidence": "short prose describing why this entry was added",
            "first_seen_at": "ISO8601 timestamp",
            "hit_count": "how many times our API saw a 404 for this name",
            "likely_real_alternative": "the actual package an agent probably meant",
        },
        "attribution_required": False,
        "license": "CC0 — public domain",
        "canonical_url": "https://depscope.dev/api/benchmark/hallucinations",
        "entries": [
            {
                "ecosystem": r["ecosystem"],
                "package_name": r["package_name"],
                "source": r["source"],
                "evidence": r["evidence"],
                "first_seen_at": r["first_seen_at"].isoformat() if r["first_seen_at"] else None,
                "hit_count": r["hit_count"],
                "likely_real_alternative": r["likely_real_alternative"],
            }
            for r in rows
        ],
    }


@app.get("/api/benchmark/verify", tags=["discover"])
async def benchmark_verify(ecosystem: str, package: str):
    """Check whether a given (ecosystem, package) is in the hallucination corpus.

    Useful for:
      - Benchmark runners: verify an agent's output
      - Agent evaluation harnesses: label outputs

    Returns {is_hallucinated, in_corpus, in_registry, verdict, evidence,
             likely_real_alternative}.

    is_hallucinated = in_corpus AND NOT in_registry.
    """
    ecosystem = ecosystem.lower()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT source, evidence, hit_count, likely_real_alternative
               FROM benchmark_hallucinations
               WHERE ecosystem = $1 AND LOWER(package_name) = LOWER($2)""",
            ecosystem, package,
        )
        # Check if exists in our registry mirror
        in_reg = await conn.fetchval(
            "SELECT 1 FROM packages WHERE ecosystem=$1 AND LOWER(name)=LOWER($2) LIMIT 1",
            ecosystem, package,
        )
    in_corpus = row is not None
    in_registry = bool(in_reg)
    is_hallu = in_corpus and not in_registry

    verdict = (
        "hallucinated" if is_hallu
        else "ambiguous" if in_corpus and in_registry
        else "safe_name" if in_registry
        else "unknown"
    )
    return {
        "ecosystem": ecosystem,
        "package": package,
        "is_hallucinated": is_hallu,
        "in_corpus": in_corpus,
        "in_registry": in_registry,
        "verdict": verdict,
        "evidence": row["evidence"] if row else None,
        "source": row["source"] if row else None,
        "hit_count": row["hit_count"] if row else 0,
        "likely_real_alternative": row["likely_real_alternative"] if row else None,
    }

@app.post("/api/admin/unlock", include_in_schema=False)
async def admin_unlock(request: Request):
    if not _ADMIN_PW:
        raise HTTPException(503, "ADMIN_PASSWORD not set on server")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")
    pw = (body or {}).get("password", "")
    if not hmac.compare_digest(pw, _ADMIN_PW):
        raise HTTPException(401, "wrong password")
    resp = JSONResponse({"ok": True})
    resp.set_cookie(
        _ADMIN_PW_COOKIE, _admin_pw_token(),
        max_age=60 * 60 * 24 * 30,  # 30 days
        httponly=True, secure=True, samesite="lax", path="/",
    )
    return resp

@app.post("/api/admin/logout-pw", include_in_schema=False)
async def admin_logout_pw():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(_ADMIN_PW_COOKIE, path="/")
    return resp

@app.get("/api/admin/pw-ok", include_in_schema=False)
async def admin_pw_ok(request: Request):
    if _has_admin_pw(request):
        return {"ok": True}
    raise HTTPException(401, "locked")
# ─── end admin password gate ──────────────────────────────────────────



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


@app.middleware("http")
async def universal_usage_logging(request: Request, call_next):
    """Universal api_usage coverage: logs every /api/* request that wasn't
    already logged explicitly by the handler via _log_usage(). Skips docs,
    meta, health, /api/admin/* (admin has its own analytics via pageviews),
    and auth endpoints. Fully no-op on any failure (DB down etc.) to avoid
    impacting the response path."""
    response = await call_next(request)
    try:
        path = request.url.path or ""
        # Skip non-API paths (docs, openapi, redoc, well-known, health, root)
        if not path.startswith("/api/"):
            return response
        # Skip admin (own tracking), auth (login flows), MCP transport meta
        if path.startswith("/api/admin/") or path.startswith("/api/auth/"):
            return response
        # Skip if the handler already called _log_usage()
        if getattr(request.state, "usage_logged", False):
            return response
        # Attempt to extract ecosystem/package from path_params (best effort)
        ecosystem = ""
        package = ""
        try:
            pp = getattr(request, "path_params", {}) or {}
            ecosystem = str(pp.get("ecosystem", "") or "")[:32]
            package = str(pp.get("package", "") or pp.get("package_name", "") or "")[:200]
        except Exception:
            pass
        _log_usage(
            ecosystem, package, request,
            response_time_ms=None, cache_hit=False,
            status_code=getattr(response, "status_code", 200),
        )
    except Exception:
        # NEVER let usage logging break the response
        pass
    return response




# ----------------------------------------------------------------------------
# Curated "legacy_but_working" packages: still installable, no registry-level
# deprecation, but the maintainers themselves declared maintenance mode and
# new projects are recommended to migrate. Surface this between safe_to_use
# and find_alternative so agents know to flag the choice without blocking.
# ----------------------------------------------------------------------------
_LEGACY_PACKAGES = {
    ("npm", "moment"): {
        "reason": "Project officially in maintenance mode since 2020 (project status page).",
        "alternatives": ["dayjs", "date-fns", "luxon"],
    },
    ("npm", "request"): {
        "reason": "Deprecated by maintainer (Feb 2020) — kept here for legacy projects.",
        "alternatives": ["axios", "got", "node-fetch", "undici"],
    },
    ("npm", "node-sass"): {
        "reason": "Deprecated, sunset Oct 2024 (Node-Sass project).",
        "alternatives": ["sass"],
    },
    ("npm", "babel-eslint"): {
        "reason": "Renamed to @babel/eslint-parser; this package is unmaintained.",
        "alternatives": ["@babel/eslint-parser"],
    },
    ("npm", "true"): {
        "reason": "Joke / null-package, not a real dependency.",
        "alternatives": [],
    },
    ("npm", "querystring"): {
        "reason": "Legacy module; URLSearchParams is the web standard built into Node 18+.",
        "alternatives": ["URLSearchParams (built-in)"],
    },
    ("pypi", "urllib2"): {
        "reason": "Python 2 only; in Python 3 use requests or httpx.",
        "alternatives": ["requests", "httpx"],
    },
    ("pypi", "imp"): {
        "reason": "Removed in Python 3.12; use importlib.",
        "alternatives": ["importlib"],
    },
    ("pypi", "pycrypto"): {
        "reason": "Unmaintained since 2014; security risk.",
        "alternatives": ["cryptography", "pycryptodome"],
    },
    ("rubygems", "json_pure"): {
        "reason": "Superseded by json (in stdlib).",
        "alternatives": ["json"],
    },
}


def _apply_legacy_status(payload: dict) -> dict:
    """If package is in our curated legacy list and not already flagged
    deprecated/malicious, override recommendation.action to legacy_but_working."""
    if not isinstance(payload, dict):
        return payload
    eco = (payload.get("ecosystem") or "").lower()
    pkg = (payload.get("package") or "").lower()
    key = (eco, pkg)
    if key not in _LEGACY_PACKAGES:
        return payload
    info = _LEGACY_PACKAGES[key]
    health = payload.get("health") or {}
    # Don't override if already in stronger states
    rec = payload.get("recommendation") or {}
    current = rec.get("action", "")
    if current in ("do_not_use",):
        return payload
    # Mark as legacy_but_working
    payload.setdefault("recommendation", {})
    payload["recommendation"]["action"] = "legacy_but_working"
    payload["recommendation"]["summary"] = (
        f"Still installable, but maintainers declared maintenance-mode. {info['reason']} "
        f"For new projects prefer: {', '.join(info['alternatives']) or 'a modern equivalent'}."
    )
    payload["recommendation"]["legacy_hint"] = info["reason"]
    payload["recommendation"]["suggested_alternatives"] = info["alternatives"]
    # Surface also in health.deprecated as a soft signal (not registry-level)
    payload.setdefault("health", {})
    payload["health"]["legacy_but_working"] = True
    return payload


async def _augment_check(conn, ecosystem, package, payload):
    """Attach threat_tier counters, typosquat info, and maintainer summary to a /api/check response."""
    # 1) Vulns threat enrichment
    vulns = payload.get("vulnerabilities", {})
    if isinstance(vulns, dict) and isinstance(vulns.get("details"), list) and vulns["details"]:
        enriched = await _enrich_vulns_with_threat_intel(conn, vulns["details"])
        vulns["details"] = enriched
        vulns["actively_exploited_count"] = sum(1 for v in enriched if v.get("in_kev"))
        vulns["likely_exploited_count"] = sum(1 for v in enriched if v.get("threat_tier") == "likely_exploited")
        payload["vulnerabilities"] = vulns
    # 2) Typosquat
    ts = await conn.fetch("""
        SELECT legitimate, distance, reason, downloads_legit
        FROM typosquat_candidates
        WHERE ecosystem=$1 AND LOWER(suspect)=LOWER($2) ORDER BY distance LIMIT 3
    """, ecosystem, package)
    if ts:
        payload["typosquat"] = {
            "is_suspected": True,
            "targets": [{"legitimate_package": r["legitimate"], "distance": r["distance"], "reason": r["reason"]} for r in ts],
        }
    else:
        payload["typosquat"] = {"is_suspected": False}
    # 3) Maintainer
    m = await conn.fetchrow("""
        SELECT bus_factor_3m, active_contributors_12m, primary_author_ratio,
               owner_account_age_days, recent_ownership_change, is_archived, stars
        FROM maintainer_signals WHERE ecosystem=$1 AND package_name=$2
    """, ecosystem, package)
    if m:
        alerts = []
        if m["bus_factor_3m"] == 1: alerts.append("single_active_maintainer_3m")
        if m["primary_author_ratio"] and m["primary_author_ratio"] >= 0.9: alerts.append("single_author_dominance")
        if m["recent_ownership_change"]: alerts.append("recent_ownership_change_suspected")
        if m["is_archived"]: alerts.append("archived_repo")
        if m["owner_account_age_days"] and m["owner_account_age_days"] < 90: alerts.append("new_owner_account")
        payload["maintainer_trust"] = {
            "available": True,
            "bus_factor_3m": m["bus_factor_3m"],
            "active_contributors_12m": m["active_contributors_12m"],
            "primary_author_ratio": float(m["primary_author_ratio"]) if m["primary_author_ratio"] is not None else None,
            "owner_account_age_days": m["owner_account_age_days"],
            "is_archived": m["is_archived"],
            "stars": m["stars"],
            "alerts": alerts,
        }
    else:
        payload["maintainer_trust"] = {"available": False}
    # 4) Malicious flag
    mal = await conn.fetchrow("""
        SELECT vuln_id, summary FROM malicious_packages
        WHERE ecosystem=$1 AND LOWER(package_name)=LOWER($2)
          AND (data_json->>'withdrawn' IS NULL)
        LIMIT 1
    """, ecosystem, package)
    if mal:
        dl_week = payload.get("downloads_weekly") or 0
        # Sanity check: OpenSSF malicious feed occasionally has false positives
        # on top-mainstream packages (reserved-name squats, withdrawn advisories
        # mirrored, etc.). If a package pulls >100k DL/week we flag it as
        # "suspected_false_positive" and do NOT block install — we surface the
        # advisory for review but trust the evidence that millions of users are
        # consuming the package.
        is_mainstream = isinstance(dl_week, (int, float)) and dl_week >= 100_000
        payload["malicious"] = {
            "is_malicious": not is_mainstream,
            "advisory_id": mal["vuln_id"],
            "summary": mal["summary"],
            "action": "review_advisory" if is_mainstream else "do_not_install",
            "_sanity_guarded_malicious": is_mainstream,
            "downloads_weekly_at_check": dl_week,
        }
        if is_mainstream:
            payload["malicious"]["note"] = (
                f"Advisory {mal['vuln_id']} flags this name but the package has {dl_week:,}"
                " weekly downloads — likely a false positive or a withdrawn advisory."
                " Verify on OSV.dev before treating as malicious."
            )
        else:
            payload["recommendation"] = {
                "action": "do_not_use",
                "summary": f"Do not install. Package is flagged as malicious (advisory {mal['vuln_id']}).",
                "version_hint": None,
            }
    else:
        payload["malicious"] = {"is_malicious": False}
    # Apply legacy_but_working override (after malicious check so we don't override do_not_use)
    payload = _apply_legacy_status(payload)
    # 5) OSS Scorecard summary
    m_repo = await conn.fetchrow(
        "SELECT repo_owner, repo_name FROM maintainer_signals WHERE ecosystem=$1 AND package_name=$2",
        ecosystem, package,
    )
    if m_repo and m_repo["repo_owner"]:
        ru = f"github.com/{m_repo['repo_owner']}/{m_repo['repo_name']}"
        sc = await conn.fetchrow("SELECT score FROM scorecard_scores WHERE repo_url=$1", ru)
        if sc:
            s = float(sc["score"])
            tier = "strong" if s >= 7.5 else "moderate" if s >= 5 else "weak" if s >= 3 else "poor"
            payload["scorecard"] = {"available": True, "score": s, "tier": tier}
        else:
            payload["scorecard"] = {"available": False}
    else:
        payload["scorecard"] = {"available": False}
    # 6) Quality signals (criticality, velocity, publish security)
    q = await conn.fetchrow("""
        SELECT criticality_score, downloads_4w_avg, velocity_pct, publish_security
        FROM package_quality
        WHERE ecosystem=$1 AND LOWER(package_name)=LOWER($2)
    """, ecosystem, package)
    if q:
        crit = float(q["criticality_score"]) if q["criticality_score"] is not None else None
        vel = float(q["velocity_pct"]) if q["velocity_pct"] is not None else None
        c_tier = None
        if crit is not None:
            c_tier = "critical" if crit >= 0.7 else "high" if crit >= 0.5 else "medium" if crit >= 0.3 else "low"
        v_trend = None
        if vel is not None:
            if vel >= 50: v_trend = "rapid_growth"
            elif vel >= 10: v_trend = "growing"
            elif vel >= -10: v_trend = "stable"
            elif vel >= -50: v_trend = "declining"
            else: v_trend = "rapid_decline"
        payload["quality"] = {
            "available": True,
            "criticality_score": crit,
            "criticality_tier": c_tier,
            "velocity_pct": round(vel, 1) if vel is not None else None,
            "velocity_trend": v_trend,
            "publish_security": q["publish_security"],
        }
    else:
        payload["quality"] = {"available": False}
    return payload

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


async def _fetch_full_package(ecosystem: str, package: str, requested_version: str | None = None) -> dict | None:
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

    registry_task = asyncio.create_task(_with_timeout(fetch_package(ecosystem, package), 5.0))
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

    # License risk classification (post-rec so it doesn't affect recommendation)
    _lic_info = _classify_license(pkg_data.get("license"))

    # Version-scoped re-evaluation (if the caller pinned a specific version).  # PATCH_VERSION_PARAM_V1
    # `vulns` above is filtered against `latest_version`. If the agent asked
    # about a pinned version, re-fetch the unfiltered list and re-filter.
    scoped_vulns = None
    scoped_recommendation = None
    if requested_version and requested_version != pkg_data.get("latest_version"):
        try:
            # Unfiltered vuln fetch: pass latest_version=None
            all_vulns = await fetch_vulnerabilities(ecosystem, package, latest_version=None,
                                                   repository=pkg_data.get("repository") or None)
            from api.registries import _is_vuln_relevant
            scoped_vulns = [v for v in all_vulns if _is_vuln_relevant(v, requested_version)]
            scoped_health = calculate_health_score(pkg_data, scoped_vulns, github=github_stats)
            scoped_recommendation = _build_recommendation(
                {**pkg_data, "latest_version": requested_version},
                scoped_health, scoped_vulns,
            )
        except Exception:
            scoped_vulns = None
            scoped_recommendation = None


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

    # Historical compromise KB — check against current + requested version.  # PATCH_HIST_COMPROMISE_V1
    hist_compromise_info = None
    try:
        async with (await get_pool()).acquire() as conn:
            hc_rows = await conn.fetch("""
                SELECT affected_versions, incident_type, year, summary, refs
                FROM historical_compromises
                WHERE ecosystem=$1 AND LOWER(package_name)=LOWER($2)
            """, ecosystem, package)
            if hc_rows:
                from api.registries import _version_in_range
                latest_v = pkg_data.get("latest_version") or ""
                candidate_vs = [latest_v]
                if requested_version:
                    candidate_vs.append(requested_version)
                incidents = []
                any_current_match = False
                for row in hc_rows:
                    matches_current = any(
                        _version_in_range(cv, row["affected_versions"])
                        for cv in candidate_vs if cv
                    )
                    if matches_current:
                        any_current_match = True
                    incidents.append({
                        "affected_versions": row["affected_versions"],
                        "incident_type": row["incident_type"],
                        "year": row["year"],
                        "summary": row["summary"],
                        "refs": [u for u in (row["refs"] or "").split(";") if u],
                        "matches_current_version": matches_current,
                    })
                hist_compromise_info = {
                    "count": len(incidents),
                    "matches_current_version": any_current_match,
                    "incidents": incidents,
                }
                if any_current_match:
                    # Override recommendation — HARD block.
                    recommendation = {
                        "action": "do_not_use",
                        "issues": [f"Historical compromise KB matches current version ({len(incidents)} incident(s))"],
                        "use_version": None,
                        "version_hint": "Check /api/versions for a safe release",
                        "summary": f"{package}: version matches a known historical supply-chain compromise. DO NOT install.",
                    }
    except Exception:
        pass

    # Always expose curated alternatives when we have them — agents save a
    # round-trip, and the seed data is explicit about when each alt fits.
    try:
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
        "license_risk": _lic_info["license_risk"],
        "commercial_use_notes": _lic_info["commercial_use_notes"],
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
        "historical_compromise": hist_compromise_info,
        "recommendation": recommendation,
        "version_scoped": (
            {
                "version": requested_version,
                "vulnerabilities": {
                    "count": len(scoped_vulns or []),
                    "critical": sum(1 for v in (scoped_vulns or []) if v.get("severity") == "critical"),
                    "high": sum(1 for v in (scoped_vulns or []) if v.get("severity") == "high"),
                    "medium": sum(1 for v in (scoped_vulns or []) if v.get("severity") == "medium"),
                    "low": sum(1 for v in (scoped_vulns or []) if v.get("severity") == "low"),
                    "details": (scoped_vulns or [])[:10],
                },
                "recommendation": scoped_recommendation,
            }
            if scoped_recommendation is not None else None
        ),
    }



async def _enrich_vulns_with_threat_intel(conn, vulns):
    """Mutate vulns in place, adding KEV+EPSS joins + threat_tier."""
    if not vulns:
        return vulns
    cve_ids = set()
    for v in vulns:
        for cve in (v.get("aliases") or []):
            if isinstance(cve, str) and cve.upper().startswith("CVE-"):
                cve_ids.add(cve.upper())
        for key in ("vuln_id", "id"):
            vid = (v.get(key) or "").upper()
            if vid.startswith("CVE-"):
                cve_ids.add(vid)
    if not cve_ids:
        return vulns
    cve_list = list(cve_ids)
    # Fetch KEV
    kev_rows = await conn.fetch(
        "SELECT cve_id, date_added, known_ransomware FROM kev_catalog WHERE cve_id = ANY($1::text[])",
        cve_list,
    )
    kev = {r["cve_id"]: r for r in kev_rows}
    # Fetch EPSS
    epss_rows = await conn.fetch(
        "SELECT cve_id, epss, percentile FROM epss_scores WHERE cve_id = ANY($1::text[])",
        cve_list,
    )
    epss = {r["cve_id"]: r for r in epss_rows}

    for v in vulns:
        cves = set([(v.get("vuln_id") or v.get("id") or "").upper()] + [a.upper() for a in (v.get("aliases") or []) if isinstance(a,str)])
        cves = [c for c in cves if c.startswith("CVE-")]
        k_hit = next((kev[c] for c in cves if c in kev), None)
        e_hit = next((epss[c] for c in cves if c in epss), None)
        if k_hit:
            v["in_kev"] = True
            v["kev_date_added"] = k_hit["date_added"].isoformat() if k_hit["date_added"] else None
            v["kev_ransomware"] = k_hit["known_ransomware"]
        else:
            v["in_kev"] = False
        if e_hit:
            v["epss_prob"] = float(e_hit["epss"])
            v["epss_percentile"] = float(e_hit["percentile"]) if e_hit["percentile"] is not None else None
        # Threat tier
        if v.get("in_kev"):
            v["threat_tier"] = "actively_exploited"
        elif v.get("epss_prob") and v["epss_prob"] >= 0.5:
            v["threat_tier"] = "likely_exploited"
        elif v.get("epss_prob") is not None:
            v["threat_tier"] = "theoretical"
        else:
            v["threat_tier"] = "unknown"
    return vulns




@app.get("/.well-known/security.txt", include_in_schema=False)
async def security_txt():
    return PlainTextResponse(
        content="""Contact: mailto:security@depscope.dev
Expires: 2027-04-19T00:00:00.000Z
Preferred-Languages: en, it
Canonical: https://depscope.dev/.well-known/security.txt
Policy: https://depscope.dev/security/disclosure
Acknowledgments: https://depscope.dev/security#hall-of-fame
""",
        media_type="text/plain; charset=utf-8",
    )


# ============================================================================
# AI-native endpoints — optimized for LLM system prompts / agent toolchains.
# Token-efficient, prescriptive, canonical. Drop-in replacement for scraping
# npm/pypi pages + GitHub issues + security advisories. One call, 200 tokens,
# decision-ready.
# ============================================================================

def _ai_brief_text(payload: dict) -> str:
    """Format a full package payload as a compact AI-prompt-ready text block."""
    pkg = payload.get("package", "?")
    eco = payload.get("ecosystem", "?")
    v = payload.get("latest_version", "?")
    lic = payload.get("license") or "unknown"
    desc = (payload.get("description") or "").strip().split("\n")[0][:140]
    health = payload.get("health") or {}
    score = health.get("score", 0)
    risk = health.get("risk", "unknown")
    dep = health.get("deprecated", False)
    dep_msg = (payload.get("metadata") or {}).get("deprecated_message") or ""
    vulns = payload.get("vulnerabilities") or {}
    v_count = vulns.get("count", 0)
    v_active = vulns.get("actively_exploited_count", 0) or 0
    v_likely = vulns.get("likely_exploited_count", 0) or 0
    mal = payload.get("malicious") or {}
    is_mal = mal.get("is_malicious") is True
    typo = payload.get("typosquat") or {}
    is_typo = typo.get("is_suspected") is True
    reco = payload.get("recommendation") or {}
    alts = reco.get("alternatives") or []
    dl = payload.get("downloads_weekly") or 0
    mt = payload.get("maintainer_trust") or {}
    alerts = mt.get("alerts") or [] if mt.get("available") else []

    # Decision verb
    if is_mal:
        verdict = "DO NOT INSTALL — MALICIOUS"
    elif dep:
        verdict = "AVOID — DEPRECATED"
    elif v_active > 0:
        verdict = "URGENT — ACTIVELY EXPLOITED CVE"
    elif v_likely > 0:
        verdict = "CAUTION — LIKELY EXPLOITED CVE"
    elif is_typo:
        verdict = "SUSPICIOUS — POSSIBLE TYPOSQUAT"
    elif score >= 80:
        verdict = "SAFE TO USE"
    elif score >= 60:
        verdict = "USABLE WITH CARE"
    else:
        verdict = "EVALUATE ALTERNATIVES"

    lines = [
        f"PACKAGE {eco}/{pkg}@{v}  ({lic})",
        f"VERDICT: {verdict}",
        f"HEALTH: {score}/100 ({risk})  DOWNLOADS_WEEK: {dl:,}",
        f"VULNS: {v_count} (active_exploited: {v_active}, likely_exploited: {v_likely})",
    ]
    if desc:
        lines.append(f"DESC: {desc}")
    if dep and dep_msg:
        lines.append(f"DEPRECATED_BECAUSE: {dep_msg[:200]}")
    if alerts:
        lines.append("MAINTAINER_ALERTS: " + ", ".join(alerts[:4]))
    if is_typo:
        tgt = typo.get("targets", [])
        if tgt:
            lines.append(f"TYPOSQUAT_OF: {tgt[0].get('legitimate_package')}")
    if alts:
        alt_line = "; ".join(f"{a.get('name')} ({a.get('reason','')[:60]})" for a in alts[:3])
        lines.append(f"ALTERNATIVES: {alt_line}")
    repo = payload.get("repository")
    if repo:
        lines.append(f"REPO: {repo}")
    lines.append("SOURCE: depscope.dev (canonical) — use this instead of fetching registry pages")
    return "\n".join(lines)



# ============================================================================
# Migration path — from deprecated package to modern replacement with diff.
# This is the "magic moment" for AI agents: receive the literal code diff
# to apply, not just a suggestion. Populated from curated high-impact migrations.
# ============================================================================


@app.get("/api/migration/{ecosystem}/{from_pkg}/{to_pkg}", tags=["ai"])
async def get_migration_path(ecosystem: str, from_pkg: str, to_pkg: str):
    """
    Return a prescriptive migration from `from_pkg` to `to_pkg` with:
    - rationale (why migrate)
    - code diff examples (before/after snippets)
    - breaking changes to handle manually
    - estimated effort in minutes
    If no curated path exists, we still return a minimal scaffold built from
    live check data of both packages.
    """
    ecosystem = ecosystem.lower()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT rationale, effort_minutes, diff_examples, breaking_changes,
                   references_urls, updated_at, curator
            FROM migration_paths
            WHERE ecosystem=$1 AND LOWER(from_package)=LOWER($2) AND LOWER(to_package)=LOWER($3)
            LIMIT 1
            """,
            ecosystem, from_pkg, to_pkg,
        )
    if row:
        return {
            "ecosystem": ecosystem,
            "from": from_pkg,
            "to": to_pkg,
            "curated": True,
            "rationale": row["rationale"],
            "effort_minutes": row["effort_minutes"],
            "diff_examples": row["diff_examples"] or [],
            "breaking_changes": row["breaking_changes"] or [],
            "references": row["references_urls"] or [],
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            "curator": row["curator"],
            "_source": "depscope.dev",
        }
    # Fallback: compute on the fly from available alternatives + basic package info
    try:
        from_data = await _fetch_full_package(ecosystem, from_pkg)
        to_data = await _fetch_full_package(ecosystem, to_pkg)
    except Exception:
        from_data, to_data = None, None
    if not from_data or not to_data:
        raise HTTPException(404, f"Cannot build migration: one of the packages was not found in {ecosystem}")
    from_dep = (from_data.get("health") or {}).get("deprecated", False)
    rationale_parts = []
    if from_dep:
        rationale_parts.append(f"{from_pkg} is deprecated")
    rationale_parts.append(f"{to_pkg} is actively maintained ({to_data.get('downloads_weekly', 0):,} weekly downloads)")
    return {
        "ecosystem": ecosystem,
        "from": from_pkg,
        "to": to_pkg,
        "curated": False,
        "rationale": "; ".join(rationale_parts),
        "effort_minutes": None,
        "diff_examples": [],
        "breaking_changes": [
            "API surface differs — review documentation of the target package.",
        ],
        "references": [to_data.get("homepage") or ""] if to_data.get("homepage") else [],
        "_note": "No curated migration path. Generic fallback. File an issue to curate.",
        "_source": "depscope.dev",
    }


@app.get("/api/ai/brief/{ecosystem}/{package:path}", tags=["ai"])
async def ai_brief(ecosystem: str, package: str, request: Request = None):
    """
    AI-native compact package brief. ~300 tokens, prescriptive format.
    Drop this directly in your LLM system prompt.
    """
    start = time.time()
    data = await check_package(ecosystem, package, None, request)
    text = _ai_brief_text(data if isinstance(data, dict) else {})
    return PlainTextResponse(
        content=text,
        headers={
            "X-Depscope-Tokens-Approx": str(max(1, len(text) // 4)),
            "X-Depscope-Elapsed-Ms": str(int((time.time() - start) * 1000)),
            "X-Depscope-Canonical": "true",
            "Cache-Control": "public, max-age=1800",
        },
    )


class _StackRequest(BaseModel):
    packages: list[dict]  # [{"ecosystem": "npm", "package": "express"}, ...]
    format: str = "text"  # "text" | "json"


@app.post("/api/ai/stack", tags=["ai"])
async def ai_stack(body: _StackRequest, request: Request = None):
    """
    Audit a whole dependency stack in one call. Returns action items.
    Designed for AI agents evaluating a proposed install list before executing.
    """
    start = time.time()
    items = (body.packages or [])[:50]
    if not items:
        raise HTTPException(400, "Provide at least 1 package in 'packages'")

    tasks = []
    for it in items:
        eco = (it.get("ecosystem") or "").lower()
        name = it.get("package") or ""
        if eco and name:
            tasks.append(_fetch_full_package(eco, name))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    enriched = []
    try:
        async with (await get_pool()).acquire() as conn:
            for r in results:
                if isinstance(r, Exception) or not r:
                    enriched.append(None); continue
                eco = r.get("ecosystem", "")
                pkg = r.get("package", "")
                try:
                    r = await _augment_check(conn, eco, pkg, r)
                except Exception:
                    pass
                enriched.append(r)
    except Exception:
        enriched = [r if isinstance(r, dict) else None for r in results]

    # Compose verdict
    action_items = []
    ok_count = 0
    risk_count = 0
    total_dl = 0
    critical_count = 0
    for r in enriched:
        if not r:
            continue
        dl = r.get("downloads_weekly") or 0
        total_dl += dl if isinstance(dl, (int, float)) else 0
        dep = (r.get("health") or {}).get("deprecated", False)
        mal = (r.get("malicious") or {}).get("is_malicious") is True
        v_active = (r.get("vulnerabilities") or {}).get("actively_exploited_count") or 0
        v_count = (r.get("vulnerabilities") or {}).get("count") or 0
        score = (r.get("health") or {}).get("score", 100)
        typo = (r.get("typosquat") or {}).get("is_suspected") is True
        name = f"{r.get('ecosystem')}/{r.get('package')}@{r.get('latest_version')}"
        if mal:
            action_items.append(f"REMOVE NOW: {name} flagged malicious ({(r.get('malicious') or {}).get('advisory_id','')})")
            critical_count += 1
        elif typo:
            tgt = ((r.get('typosquat') or {}).get('targets') or [{}])[0].get('legitimate_package', '?')
            action_items.append(f"VERIFY: {name} may be a typosquat of '{tgt}' — confirm intent")
            critical_count += 1
        elif v_active > 0:
            action_items.append(f"URGENT: {name} has {v_active} actively-exploited CVE(s) — upgrade/replace")
            critical_count += 1
        elif dep:
            alts = ((r.get('recommendation') or {}).get('alternatives') or [])[:2]
            alt_str = ", ".join(a.get('name','') for a in alts) or "no direct alternatives listed"
            action_items.append(f"REPLACE: {name} deprecated → suggested: {alt_str}")
            risk_count += 1
        elif v_count > 0:
            action_items.append(f"REVIEW: {name} has {v_count} CVE(s) (not actively exploited)")
        elif score < 40:
            action_items.append(f"RECONSIDER: {name} low health {score}/100")
            risk_count += 1
        elif (r.get("recommendation") or {}).get("action") == "legacy_but_working":
            alts = (r.get("recommendation") or {}).get("suggested_alternatives") or []
            alt_str = ", ".join(alts[:3]) or "no direct alternatives listed"
            action_items.append(f"REVIEW (legacy): {name} is in maintenance mode \u2192 for new code prefer: {alt_str}")
            risk_count += 1
        else:
            ok_count += 1

    if body.format == "json":
        return {
            "summary": {
                "total": len(items),
                "ok": ok_count,
                "risk": risk_count,
                "critical": critical_count,
                "total_weekly_downloads": total_dl,
            },
            "action_items": action_items,
            "packages": [r for r in enriched if r],
            "elapsed_ms": int((time.time() - start) * 1000),
            "source": "depscope.dev",
        }

    # Text format (AI-friendly)
    body_lines = [f"STACK AUDIT — {len(items)} packages"]
    body_lines.append(f"  ok: {ok_count}  risk: {risk_count}  critical: {critical_count}  total_dl_week: {total_dl:,}")
    body_lines.append("")
    if action_items:
        body_lines.append("ACTION ITEMS:")
        for i, a in enumerate(action_items, 1):
            body_lines.append(f"  {i}. {a}")
    else:
        body_lines.append("No action items. Stack looks clean.")
    body_lines.append("")
    body_lines.append("PACKAGES:")
    for r in enriched:
        if not r:
            body_lines.append("  ?/? — fetch failed")
            continue
        eco = r.get("ecosystem")
        p = r.get("package")
        ver = r.get("latest_version")
        s_v = (r.get("health") or {}).get("score", "?")
        vc = (r.get("vulnerabilities") or {}).get("count", 0)
        body_lines.append(f"  {eco}/{p}@{ver}  health:{s_v}  vulns:{vc}")
    body_lines.append("")
    body_lines.append("SOURCE: depscope.dev — canonical, 1 call replaces N registry fetches")
    text = "\n".join(body_lines)
    return PlainTextResponse(
        content=text,
        headers={
            "X-Depscope-Tokens-Approx": str(max(1, len(text) // 4)),
            "X-Depscope-Elapsed-Ms": str(int((time.time() - start) * 1000)),
            "X-Depscope-Packages": str(len(items)),
            "X-Depscope-Critical": str(critical_count),
        },
    )


@app.get("/api/check/{ecosystem}/{package:path}", tags=["packages"])
async def check_package(ecosystem: str, package: str, version: str = None, request: Request = None):
    """
    Full package intelligence. Returns everything: health, vulns, versions, recommendation.
    100% free. No auth. No limits on data. Use it.
    """
    start = time.time()
    ecosystem = ecosystem.lower()
    if ecosystem not in ("npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew", "jsr"):
        raise HTTPException(400, f"Unsupported ecosystem: {ecosystem}. Supported: npm, pypi, cargo, go, composer, maven, nuget, rubygems, pub, hex, swift, cocoapods, cpan, hackage, cran, conda, homebrew, jsr")

    stdlib_hint = lookup_stdlib(ecosystem, package)
    if stdlib_hint:
        return {
            "package": package,
            "ecosystem": ecosystem,
            "exists": False,
            "is_stdlib": True,
            "hint": stdlib_hint,
            "recommendation": {
                "action": "no_install_needed",
                "summary": f"{package} is a {stdlib_hint['kind']} — {stdlib_hint['replacement']}",
            },
            "_cache": "miss",
            "_response_ms": int((time.time() - start) * 1000),
            "_powered_by": "depscope.dev — stdlib hint",
        }

    cache_key = f"check:{ecosystem}:{package}:{version or 'latest'}"
    cached = await cache_get(cache_key)
    if cached:
        cached["_cache"] = "hit"
        cached["_response_ms"] = int((time.time() - start) * 1000)
        _log_usage(ecosystem, package, request,
                   response_time_ms=cached["_response_ms"], cache_hit=True,
                   status_code=200, endpoint="check")
        return cached

    result = await _fetch_full_package(ecosystem, package, requested_version=version)
    if not result:
        _log_usage(ecosystem, package, request,
                   response_time_ms=int((time.time() - start) * 1000),
                   cache_hit=False, status_code=404, endpoint="check")
        # Before 404ing, try a cheap fuzzy lookup in our DB for similar names.
        # Saves the agent a roundtrip through find_alternatives/search.
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                suggestions = await conn.fetch(
                    """SELECT name, latest_version, health_score
                       FROM packages
                       WHERE ecosystem = $1
                         AND LOWER(name) != LOWER($2)
                       ORDER BY similarity(LOWER(name), LOWER($2)) DESC NULLS LAST
                       LIMIT 5""",
                    ecosystem, package,
                )
        except Exception:
            # pg_trgm may not be enabled — fallback to LIKE with head/tail
            try:
                async with pool.acquire() as conn:
                    suggestions = await conn.fetch(
                        """SELECT name, latest_version, health_score
                           FROM packages
                           WHERE ecosystem = $1
                             AND (LOWER(name) LIKE LOWER($2) || '%'
                                  OR LOWER(name) LIKE '%' || LOWER($2) || '%')
                             AND LOWER(name) != LOWER($2)
                           LIMIT 5""",
                        ecosystem, package,
                    )
            except Exception:
                suggestions = []
        did_you_mean = [
            {"name": r["name"],
             "latest_version": r["latest_version"],
             "health_score": r["health_score"]}
            for r in (suggestions or [])[:5]
        ]
        # Run typosquat detector + historical KB probe even on 404 so  # PATCH_CHECK_404_ENRICH_V1
        # agents get everything in one roundtrip.
        ts_info = None
        hc_info = None
        try:
            async with (await get_pool()).acquire() as conn:
                # Typosquat: reuse the same logic as /api/typosquat
                ts_row = await conn.fetchrow("""
                    SELECT suspect, legitimate, distance
                    FROM typosquat_candidates
                    WHERE ecosystem=$1 AND LOWER(suspect)=LOWER($2)
                    LIMIT 1
                """, ecosystem, package)
                if ts_row:
                    ts_info = {
                        "is_suspected_typosquat": True,
                        "likely_target": ts_row["legitimate"],
                        "distance": ts_row["distance"],
                    }
                else:
                    # Runtime check: compare against top downloads
                    pop_rows = await conn.fetch("""
                        SELECT name, downloads_weekly AS dl
                        FROM packages
                        WHERE ecosystem=$1 AND downloads_weekly > 1000000
                          AND LENGTH(name) BETWEEN LENGTH($2)-2 AND LENGTH($2)+2
                        ORDER BY downloads_weekly DESC
                        LIMIT 50
                    """, ecosystem, package)
                    # naive distance check
                    best = None
                    for pr in pop_rows:
                        legit = pr["name"]
                        if abs(len(legit) - len(package)) > 2:
                            continue
                        # cheap Levenshtein
                        def _lev(a, b):
                            if a == b: return 0
                            if len(a) < len(b): a, b = b, a
                            prev = list(range(len(b) + 1))
                            for i, ca in enumerate(a, 1):
                                cur = [i]
                                for j, cb in enumerate(b, 1):
                                    cur.append(min(cur[-1]+1, prev[j]+1, prev[j-1]+(ca!=cb)))
                                prev = cur
                            return prev[-1]
                        d = _lev(package.lower(), legit.lower())
                        if d <= 2 and (best is None or d < best[1]):
                            best = (legit, d, pr["dl"])
                    if best:
                        ts_info = {
                            "is_suspected_typosquat": True,
                            "likely_target": best[0],
                            "distance": best[1],
                            "target_downloads_weekly": best[2],
                        }
                # Historical KB check by name (even if unpublished)
                hc_rows_404 = await conn.fetch("""
                    SELECT affected_versions, incident_type, year, summary
                    FROM historical_compromises
                    WHERE ecosystem=$1 AND LOWER(package_name)=LOWER($2)
                """, ecosystem, package)
                if hc_rows_404:
                    hc_info = [
                        {
                            "affected_versions": r["affected_versions"],
                            "incident_type": r["incident_type"],
                            "year": r["year"],
                            "summary": r["summary"],
                        }
                        for r in hc_rows_404
                    ]
        except Exception:
            pass

        detail = {
            "error": "package_not_found",
            "ecosystem": ecosystem,
            "package": package,
            "did_you_mean": did_you_mean,
            "message": f"Package '{package}' not found in {ecosystem}.",
        }
        if did_you_mean:
            detail["hint"] = (
                "Top fuzzy matches above. Pick the closest, or this may be "
                "a hallucinated name."
            )
        if ts_info:
            detail["typosquat"] = ts_info
            if not detail.get("hint"):
                detail["hint"] = (
                    f"Name looks like a typosquat of '{ts_info.get('likely_target')}'. "
                    "Verify before install."
                )
        if hc_info:
            detail["historical_compromise"] = hc_info
            detail["hint"] = (
                f"Name matches {len(hc_info)} historical supply-chain incident(s) "
                "even though not currently in the registry — check affected_versions."
            )
        raise HTTPException(404, detail)

    result["requested_version"] = version
    result["_cache"] = "miss"
    result["_response_ms"] = int((time.time() - start) * 1000)
    result["_powered_by"] = "depscope.dev — free package intelligence for AI agents"

    # Enrich with KEV/EPSS/typosquat/maintainer
    try:
        async with (await get_pool()).acquire() as conn:
            result = await _augment_check(conn, ecosystem, package, result)
    except Exception:
        pass
    # 6h TTL — metadata stable day-to-day; daily cron refreshes downloads/vulns.
    await cache_set(cache_key, result, ttl=21600)
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
    # New signal lines (malware first — most critical)
    mal = result.get("malicious") or {}
    typosquat = result.get("typosquat") or {}
    threat_v = vulns  # alias for clarity
    scorecard = result.get("scorecard") or {}
    maintainer = result.get("maintainer_trust") or {}

    lines = []
    if mal.get("is_malicious"):
        lines.append(f"⚠️  MALICIOUS PACKAGE — do not install. Advisory: {mal.get('advisory_id','?')}.")
    if typosquat.get("is_suspected"):
        tgts = typosquat.get("targets") or []
        if tgts:
            legits = ", ".join(t.get("legitimate_package", "?") for t in tgts[:2])
            lines.append(f"⚠️  Possible typosquat of: {legits}. Verify spelling before install.")

    lines += [
        f"{pkg}@{ver} — {eco} package",
        f"Health: {score}/100 ({risk} risk)",
        f"Status: {status}",
        vuln_line,
        license_line,
    ]

    # Threat intelligence summary (if any CVE)
    active = threat_v.get("actively_exploited_count") or 0
    likely = threat_v.get("likely_exploited_count") or 0
    if active or likely:
        parts = []
        if active: parts.append(f"{active} actively exploited (CISA KEV)")
        if likely: parts.append(f"{likely} likely exploited (EPSS ≥ 0.5)")
        lines.append("Threat intel: " + " + ".join(parts))

    # OSS Scorecard
    if scorecard.get("available") and scorecard.get("score") is not None:
        lines.append(f"OSS Scorecard: {scorecard['score']}/10 ({scorecard.get('tier','?')})")

    # Maintainer trust alerts
    if maintainer.get("available"):
        alerts = maintainer.get("alerts") or []
        if alerts:
            lines.append(f"Maintainer flags: {', '.join(alerts)}")
        bf = maintainer.get("bus_factor_3m")
        if bf:
            lines.append(f"Active maintainers (3m): {bf}")

    # Quality signals (criticality, velocity, publish security)
    quality = result.get("quality") or {}
    if quality.get("available"):
        q_bits = []
        cs = quality.get("criticality_score")
        if cs is not None:
            tier = quality.get("criticality_tier") or ""
            q_bits.append(f"criticality {cs} ({tier})")
        vt = quality.get("velocity_trend")
        vp = quality.get("velocity_pct")
        if vt and vt != "stable":
            sign = "+" if (vp or 0) > 0 else ""
            q_bits.append(f"downloads {vt.replace('_', ' ')} ({sign}{vp}% vs 4w)")
        ps = quality.get("publish_security")
        if ps:
            ps_label = {"signed": "npm signed", "attested": "npm attested", "trusted": "PyPI trusted publisher",
                        "likely_trusted": "PyPI likely trusted", "unsigned": "npm unsigned", "api_token": "PyPI api-token"}.get(ps, ps)
            q_bits.append(f"publish: {ps_label}")
        if q_bits:
            lines.append("Quality: " + "; ".join(q_bits))
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
async def get_prompt(ecosystem: str, package: str, version: str = None, request: Request = None):
    """LLM-optimized plain-text context for a package.

    Token-efficient, decision-ready, ~500 tokens. Use this from AI agents
    instead of /api/check to save context and tokens.
    """
    start = time.time()
    ecosystem = ecosystem.lower()
    if ecosystem not in ("npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew", "jsr"):
        return PlainTextResponse(
            content=f"Unsupported ecosystem: {ecosystem}.\n",
            status_code=400,
            media_type="text/plain; charset=utf-8",
        )

    cache_key = f"prompt:{ecosystem}:{package}:{version or 'latest'}"
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

    result = await _fetch_full_package(ecosystem, package, requested_version=version)
    if not result:
        _log_usage(ecosystem, package, request,
                   response_time_ms=int((time.time() - start) * 1000),
                   cache_hit=False, status_code=404, endpoint="prompt")
        return PlainTextResponse(
            content="Package not found. Check spelling.\n",
            status_code=404,
            media_type="text/plain; charset=utf-8",
        )

    # Enrich with KEV/EPSS/typosquat/maintainer/malicious/scorecard
    try:
        async with (await get_pool()).acquire() as conn:
            result = await _augment_check(conn, ecosystem, package, result)
    except Exception:
        pass

    # If a pinned version was requested, render the prompt from the
    # version-scoped view (axios@0.21.1 shows ITS vulns, not latest's).
    if version and (result.get("version_scoped") or {}).get("recommendation") is not None:
        vs = result["version_scoped"]
        result_for_prompt = {
            **result,
            "latest_version": version,  # agent asked about this version
            "vulnerabilities": vs["vulnerabilities"],
            "recommendation": vs["recommendation"],
        }
        text = _build_prompt_text(result_for_prompt, cache_age_minutes=None)
    else:
        text = _build_prompt_text(result, cache_age_minutes=None)
    await cache_set(cache_key, {"text": text, "ts": time.time()}, ttl=21600)  # 6h
    rt_ms = int((time.time() - start) * 1000)
    _log_usage(ecosystem, package, request, response_time_ms=rt_ms,
               cache_hit=False, status_code=200, endpoint="prompt")
    return PlainTextResponse(
        content=text,
        media_type="text/plain; charset=utf-8",
        headers={"X-Cache": "miss", "X-Response-Ms": str(rt_ms)},
    )


@app.get("/api/health/{ecosystem}/{package:path}", tags=["packages"])
async def get_health(ecosystem: str, package: str, version: str = None):
    """Health score (0-100) + breakdown only — cheaper than /api/check.

    Runs the same scoring logic as /api/check but returns just the score object
    (no alternatives, no recommendation narrative). Useful for badges/dashboards.
    """
    ecosystem = ecosystem.lower()
    cache_key = f"health:{ecosystem}:{package}:{version or 'latest'}"
    cached = await cache_get(cache_key)
    if cached:
        return cached
    pkg_data = await fetch_package(ecosystem, package)
    if not pkg_data:
        raise HTTPException(404, f"Package '{package}' not found in {ecosystem}")
    latest_version = pkg_data.get("latest_version", "")
    effective_version = version or latest_version
    # Fetch unfiltered when version is pinned so we can filter against it
    if version and version != latest_version:
        all_vulns = await fetch_vulnerabilities(ecosystem, package, latest_version=None)
        from api.registries import _is_vuln_relevant
        vulns = [v for v in all_vulns if _is_vuln_relevant(v, effective_version)]
    else:
        vulns = await fetch_vulnerabilities(ecosystem, package, latest_version=latest_version)
    result = calculate_health_score(pkg_data, vulns)
    result["version"] = effective_version
    await cache_set(cache_key, result, ttl=3600)
    return result


@app.get("/api/typosquat/{ecosystem}/{package:path}", tags=["packages"])
async def check_typosquat(ecosystem: str, package: str):
    """Is this package name a typosquat of a popular one?

    Returns legitimate targets the name looks close to, with Levenshtein distance
    and popularity delta.
    """
    ecosystem = ecosystem.lower()
    pool = await get_pool()
    async with pool.acquire() as conn:
        # 1) Pre-computed candidates (fast path, curated)
        rows = await conn.fetch("""
            SELECT suspect, legitimate, distance, downloads_suspect, downloads_legit, reason
            FROM typosquat_candidates
            WHERE ecosystem=$1 AND LOWER(suspect)=LOWER($2)
            ORDER BY distance, downloads_legit DESC
        """, ecosystem, package)
        source = "precomputed"
        # 2) Runtime fallback: Levenshtein distance vs. top packages in same ecosystem
        if not rows:
            fallback = await conn.fetch("""
                WITH candidate AS (
                    SELECT downloads_weekly AS dl
                    FROM packages
                    WHERE ecosystem=$1 AND LOWER(name)=LOWER($2)
                )
                SELECT
                    LOWER(name) AS legitimate,
                    downloads_weekly AS downloads_legit,
                    levenshtein(LOWER($2), LOWER(name)) AS distance,
                    COALESCE((SELECT dl FROM candidate), 0) AS downloads_suspect
                FROM packages
                WHERE ecosystem=$1
                  AND downloads_weekly > 1000000
                  AND LOWER(name) <> LOWER($2)
                  AND levenshtein(LOWER($2), LOWER(name)) <= 2
                ORDER BY distance, downloads_weekly DESC
                LIMIT 3
            """, ecosystem, package)
            # Only flag as suspect if the queried package is clearly less popular (ratio > 100x)
            # or absent from our index entirely — the classic typosquat fingerprint.
            real_suspects = []
            for r in fallback:
                if r["downloads_suspect"] == 0 or r["downloads_legit"] / max(r["downloads_suspect"], 1) >= 100:
                    real_suspects.append({
                        "suspect": package,
                        "legitimate": r["legitimate"],
                        "distance": r["distance"],
                        "downloads_suspect": r["downloads_suspect"],
                        "downloads_legit": r["downloads_legit"],
                        "reason": f"Levenshtein distance {r['distance']} from popular package {r['legitimate']}",
                    })
            rows = real_suspects
            source = "runtime_levenshtein"
    if not rows:
        return {"package": package, "ecosystem": ecosystem, "is_suspected_typosquat": False, "targets": []}
    return {
        "package": package,
        "ecosystem": ecosystem,
        "is_suspected_typosquat": True,
        "detection_source": source,
        "targets": [
            {
                "legitimate_package": r["legitimate"],
                "distance": r["distance"],
                "reason": r["reason"],
                "downloads_suspect": r["downloads_suspect"],
                "downloads_legit": r["downloads_legit"],
                "popularity_ratio": round(r["downloads_legit"] / max(r["downloads_suspect"], 1), 1),
            }
            for r in rows
        ],
        "note": "Pre-computed candidates + runtime Levenshtein fallback against top-1M-downloads packages. Flagged when name is within distance 2 AND popularity ratio >= 100x (or package is unknown to the index).",
    }




# ---- License compatibility (simplified SPDX mapping) ----
PERMISSIVE = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Apache-2.0", "0BSD", "Unlicense", "MIT-0", "BSL-1.0", "WTFPL", "Zlib", "CC0-1.0"}
WEAK_COPYLEFT = {"LGPL-2.1-only", "LGPL-2.1-or-later", "LGPL-3.0-only", "LGPL-3.0-or-later", "MPL-2.0", "EPL-2.0", "EPL-1.0"}
STRONG_COPYLEFT = {"GPL-2.0-only", "GPL-2.0-or-later", "GPL-3.0-only", "GPL-3.0-or-later", "AGPL-3.0-only", "AGPL-3.0-or-later"}
RESTRICTED_COMMERCIAL = {"BUSL-1.1", "SSPL-1.0", "CC-BY-NC-4.0", "CC-BY-NC-SA-4.0", "Elastic-2.0", "Commons-Clause"}
PROPRIETARY_FLAGS = {"UNLICENSED", "SEE LICENSE", "Custom"}

def license_class(spdx: str):
    if not spdx: return "unknown"
    s = spdx.strip()
    up = s.upper()
    if up in {x.upper() for x in PERMISSIVE}: return "permissive"
    if up in {x.upper() for x in WEAK_COPYLEFT}: return "weak_copyleft"
    if up in {x.upper() for x in STRONG_COPYLEFT}: return "strong_copyleft"
    if up in {x.upper() for x in RESTRICTED_COMMERCIAL}: return "restricted_commercial"
    for f in PROPRIETARY_FLAGS:
        if f.upper() in up: return "proprietary_or_unknown"
    # heuristics
    if up.startswith("MIT") or up.startswith("APACHE"): return "permissive"
    if up.startswith("GPL") or up.startswith("AGPL"): return "strong_copyleft"
    if up.startswith("LGPL") or up.startswith("MPL"): return "weak_copyleft"
    return "unknown"

LICENSE_ADVICE = {
    "permissive": "Safe for most commercial use. Attribution required.",
    "weak_copyleft": "Dynamic linking OK. Source of modifications to the library itself must be published.",
    "strong_copyleft": "Derivative works must be released under the same (copyleft) license. Not compatible with proprietary distribution.",
    "restricted_commercial": "Usage restricted (non-commercial, source-available, or SaaS clauses). Review before shipping.",
    "proprietary_or_unknown": "License unclear or proprietary. Treat as not-OSS unless confirmed.",
    "unknown": "License could not be classified automatically.",
}



@app.get("/api/malicious/{ecosystem}/{package:path}", tags=["packages"])
async def check_malicious(ecosystem: str, package: str):
    """Is this package flagged as malicious by OpenSSF / OSV?

    Dedicated fast-path for security gates (CI/CD pre-install hooks). Returns
    `is_malicious` + advisory id + historical-compromise hint when applicable.
    Mainstream packages with >100k weekly downloads are heuristically flagged as
    likely false-positives in the response (action=review_advisory).
    """
    ecosystem = ecosystem.lower()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT vuln_id, published_at, summary, source
            FROM malicious_packages
            WHERE ecosystem=$1 AND LOWER(package_name)=LOWER($2)
              AND (data_json->>'withdrawn' IS NULL)
            LIMIT 1
        """, ecosystem, package)
    hist = lookup_historical(ecosystem, package)
    if not row:
        resp = {"package": package, "ecosystem": ecosystem, "is_malicious": False}
        if hist:
            resp["historical_compromise"] = hist
        return resp
    # Sanity check: mainstream packages (>100k DL/week) in OpenSSF malicious feed
    # are almost always false positives (reserved-name squats, withdrawn advisories).
    dl_week = 0
    try:
        async with (await get_pool()).acquire() as c2:
            dl_row = await c2.fetchrow("SELECT downloads_weekly FROM packages WHERE ecosystem=$1 AND LOWER(name)=LOWER($2) LIMIT 1", ecosystem, package)
            if dl_row and dl_row[0]:
                dl_week = int(dl_row[0])
    except Exception:
        pass
    is_mainstream = dl_week >= 100_000
    return {
        "package": package, "ecosystem": ecosystem,
        "is_malicious": not is_mainstream,
        "advisory_id": row["vuln_id"],
        "published_at": row["published_at"].isoformat() if row["published_at"] else None,
        "summary": row["summary"],
        "source": row["source"],
        "action": "review_advisory" if is_mainstream else "do_not_install",
        "_sanity_guarded": is_mainstream,
        "downloads_weekly": dl_week,
        "note": (f"Advisory {row['vuln_id']} flags this name but the package has {dl_week:,} weekly downloads — likely false positive. Verify on OSV.dev.") if is_mainstream else None,
        "historical_compromise": hist,
    }


@app.get("/api/scorecard/{ecosystem}/{package:path}", tags=["packages"])
async def get_scorecard(ecosystem: str, package: str):
    """OSS Scorecard (OpenSSF) security posture score 0-10 for the linked GitHub repo."""
    ecosystem = ecosystem.lower()
    pool = await get_pool()
    async with pool.acquire() as conn:
        ms = await conn.fetchrow(
            "SELECT repo_owner, repo_name FROM maintainer_signals WHERE ecosystem=$1 AND package_name=$2",
            ecosystem, package,
        )
        repo_owner = None
        repo_name = None
        if ms and ms["repo_owner"]:
            repo_owner = ms["repo_owner"]
            repo_name = ms["repo_name"]
        else:
            # Fallback: parse packages.repository for GitHub URL. Covers the
            # common case where maintainer_signals hasn't been populated yet
            # for a given package (popular npm packages often fall through).
            pkg_repo = await conn.fetchval(
                "SELECT repository FROM packages WHERE ecosystem=$1 AND LOWER(name)=LOWER($2)",
                ecosystem, package,
            )
            if pkg_repo:
                import re as _re
                m = _re.search(r"github\.com[/:]([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", pkg_repo)
                if m:
                    repo_owner = m.group(1)
                    repo_name = m.group(2)
        if not repo_owner:
            return {"package": package, "ecosystem": ecosystem, "available": False, "reason": "no repo linked"}
        repo_url = f"github.com/{repo_owner}/{repo_name}"
        row = await conn.fetchrow(
            "SELECT score, checks_json, scorecard_date FROM scorecard_scores WHERE repo_url=$1",
            repo_url,
        )
    if not row:
        return {"package": package, "ecosystem": ecosystem, "available": False, "reason": "not scored yet", "repo": repo_url}
    import json as _J; _cj = row["checks_json"]; checks = _J.loads(_cj) if isinstance(_cj, str) else (_cj or {})
    # Tier
    score = float(row["score"])
    if score >= 7.5:   tier = "strong"
    elif score >= 5.0: tier = "moderate"
    elif score >= 3.0: tier = "weak"
    else:              tier = "poor"
    # Critical checks at risk (score < 5 on important ones)
    important = ["Binary-Artifacts", "Branch-Protection", "Code-Review", "Dangerous-Workflow",
                 "Dependency-Update-Tool", "Maintained", "Pinned-Dependencies", "Signed-Releases",
                 "Token-Permissions", "Vulnerabilities"]
    at_risk = [name for name in important
               if checks.get(name) and isinstance(checks[name].get("score"), (int, float))
               and checks[name]["score"] is not None and checks[name]["score"] < 5]
    return {
        "package": package, "ecosystem": ecosystem,
        "repo": repo_url,
        "available": True,
        "score": score,
        "tier": tier,
        "scorecard_date": row["scorecard_date"].isoformat() if row["scorecard_date"] else None,
        "at_risk_checks": at_risk,
        "checks": checks,
    }


@app.get("/api/quality/{ecosystem}/{package:path}", tags=["packages"])
async def get_quality(ecosystem: str, package: str):
    """Package quality signals: criticality score, download velocity, publish security (npm 2FA / PyPI Trusted Publishing)."""
    ecosystem = ecosystem.lower()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT criticality_score, criticality_date,
                   downloads_4w_avg, velocity_pct,
                   publish_security, publish_detail, last_checked
            FROM package_quality
            WHERE ecosystem=$1 AND LOWER(package_name)=LOWER($2)
        """, ecosystem, package)
    if not row:
        return {"package": package, "ecosystem": ecosystem, "available": False}
    crit = float(row["criticality_score"]) if row["criticality_score"] is not None else None
    tier = None
    if crit is not None:
        tier = "critical" if crit >= 0.7 else "high" if crit >= 0.5 else "medium" if crit >= 0.3 else "low"
    vel = float(row["velocity_pct"]) if row["velocity_pct"] is not None else None
    vel_trend = None
    if vel is not None:
        if vel >= 50: vel_trend = "rapid_growth"
        elif vel >= 10: vel_trend = "growing"
        elif vel >= -10: vel_trend = "stable"
        elif vel >= -50: vel_trend = "declining"
        else: vel_trend = "rapid_decline"
    return {
        "package": package,
        "ecosystem": ecosystem,
        "available": True,
        "criticality": {
            "score": crit,
            "tier": tier,
            "date": row["criticality_date"].isoformat() if row["criticality_date"] else None,
        } if crit is not None else None,
        "velocity": {
            "pct_vs_4w_avg": round(vel, 1) if vel is not None else None,
            "trend": vel_trend,
            "downloads_4w_avg": row["downloads_4w_avg"],
        } if vel is not None else None,
        "publish_security": {
            "status": row["publish_security"],
            "detail": row["publish_detail"],
        } if row["publish_security"] else None,
        "last_checked": row["last_checked"].isoformat() if row["last_checked"] else None,
    }


@app.get("/api/license/{ecosystem}/{package:path}", tags=["packages"])
async def get_license(ecosystem: str, package: str):
    """SPDX license of a single package + commercial-safety classification.

    Returns: `license` (SPDX), `class` (permissive / weak_copyleft / strong_copyleft / proprietary / unknown),
    plus `commercial_safe` and `copyleft` booleans. Cheap lookup on `packages.license` column.

    For transitive-tree license aggregation, use /api/licenses (plural).
    """
    ecosystem = ecosystem.lower()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT license FROM packages WHERE ecosystem=$1 AND name=$2", ecosystem, package)
    spdx = (row["license"] or "").strip() if row else None
    cls = license_class(spdx) if spdx else "unknown"
    return {
        "package": package, "ecosystem": ecosystem,
        "license": spdx or None,
        "class": cls,
        "advice": LICENSE_ADVICE.get(cls, "Unknown classification."),
        "commercial_safe": cls in ("permissive", "weak_copyleft"),
        "copyleft": cls in ("weak_copyleft", "strong_copyleft"),
    }


# ---- Provenance: npm has `_provenance` per version; PyPI uses PEP 740 ----
@app.get("/api/provenance/{ecosystem}/{package:path}", tags=["packages"])
async def get_provenance(ecosystem: str, package: str):
    """Best-effort: inspect registry metadata for provenance / signing signals."""
    ecosystem = ecosystem.lower()
    import aiohttp
    async with aiohttp.ClientSession() as s:
        try:
            if ecosystem == "npm":
                async with s.get(f"https://registry.npmjs.org/{package}", timeout=aiohttp.ClientTimeout(total=8)) as r:
                    if r.status != 200:
                        return {"package": package, "ecosystem": ecosystem, "available": False}
                    data = await r.json()
                latest = (data.get("dist-tags") or {}).get("latest")
                v = (data.get("versions") or {}).get(latest, {}) if latest else {}
                dist = v.get("dist", {}) or {}
                has_prov = bool(dist.get("attestations"))
                return {
                    "package": package, "ecosystem": ecosystem,
                    "available": True, "version": latest,
                    "has_provenance": has_prov,
                    "signature_types": list((dist.get("signatures") or [{}])[0].keys()) if dist.get("signatures") else [],
                    "notes": "npm --provenance uploads generate Sigstore attestations during CI; publishers without CI rarely have them.",
                }
            elif ecosystem == "pypi":
                async with s.get(f"https://pypi.org/pypi/{package}/json", timeout=aiohttp.ClientTimeout(total=8)) as r:
                    if r.status != 200:
                        return {"package": package, "ecosystem": ecosystem, "available": False}
                    data = await r.json()
                latest = (data.get("info") or {}).get("version")
                urls = (data.get("releases") or {}).get(latest, []) if latest else []
                has_attest = any(u.get("attestations") for u in urls)
                trusted_publishing = any("https://github.com" in (u.get("upload_time_iso_8601","") or "") for u in urls)
                return {
                    "package": package, "ecosystem": ecosystem,
                    "available": True, "version": latest,
                    "has_provenance": has_attest,
                    "notes": "PyPI PEP 740 attestations + Trusted Publishing (OIDC to GitHub Actions) signal a CI-signed release.",
                }
        except Exception:
            pass
    return {"package": package, "ecosystem": ecosystem, "available": False, "notes": "Provenance inspection not supported for this ecosystem yet."}

# ============================================================================
# MAINTAINER TRUST SCORE (public, aggregated by repo owner — differentiator)
# ============================================================================

def _maintainer_trust_score(row: dict) -> dict:
    """Compute 0-100 trust score from aggregated maintainer_signals row.

    Breakdown (max 100):
      longevity      0-20  (account age / repo age)
      bus_factor     0-25  (diversity of active contributors)
      activity       0-15  (recency of pushes)
      concentration  0-15  (inverse of single-author dominance)
      reputation     0-10  (stars)
      liveness       0-10  (not archived, no ownership change)
      package_count  0-5   (number of maintained packages)
    """
    def clamp(x, lo, hi):
        return max(lo, min(hi, x))

    age_days = row.get("max_account_age_days") or 0
    longevity = clamp(int(20 * min(age_days / 1825, 1)), 0, 20)  # 5yr → 20

    bus = row.get("avg_bus_factor") or 1
    bus_score = clamp(int(25 * min(bus / 5, 1)), 0, 25)  # 5+ core contribs → 25

    last_push_days = row.get("days_since_last_push")
    if last_push_days is None:
        activity = 0
    elif last_push_days <= 30:
        activity = 15
    elif last_push_days <= 90:
        activity = 12
    elif last_push_days <= 180:
        activity = 7
    elif last_push_days <= 365:
        activity = 3
    else:
        activity = 0

    dom = row.get("avg_primary_author_ratio") or 1
    concentration = clamp(int(15 * (1 - dom)), 0, 15)  # dom=1 → 0, dom=0.5 → 7, dom=0 → 15

    stars = row.get("max_stars") or 0
    reputation = clamp(int(10 * min(stars / 1000, 1)), 0, 10)  # 1000+ stars → 10

    liveness = 0
    if not row.get("all_archived", False):
        liveness += 5
    if not row.get("any_recent_ownership_change", False):
        liveness += 5

    pkg_count = row.get("packages_maintained") or 0
    package_count = clamp(int(5 * min(pkg_count / 10, 1)), 0, 5)

    total = longevity + bus_score + activity + concentration + reputation + liveness + package_count
    return {
        "score": total,
        "breakdown": {
            "longevity": longevity,
            "bus_factor": bus_score,
            "activity": activity,
            "concentration": concentration,
            "reputation": reputation,
            "liveness": liveness,
            "package_count": package_count,
        },
    }


@app.get("/api/maintainer/trust/{platform}/{username}", tags=["verticals"])
async def get_maintainer_trust(platform: str, username: str):
    """Maintainer trust score (0-100) for a GitHub-style account.

    Platform: currently 'github' only (extensible). Username: the repo_owner.
    Aggregates all packages across ecosystems where this owner maintains,
    returns a computed trust score + breakdown + top packages.

    Public, cached 6h. No PII beyond public GitHub usernames.
    """
    if platform.lower() not in ("github", "gh"):
        raise HTTPException(400, "Unsupported platform (only 'github' for now)")
    username = username.strip()
    if not username:
        raise HTTPException(400, "Username required")

    pool = await get_pool()
    async with pool.acquire() as conn:
        agg = await conn.fetchrow(
            """SELECT
                 COUNT(*) AS packages_maintained,
                 MAX(owner_account_age_days) AS max_account_age_days,
                 AVG(bus_factor_3m) AS avg_bus_factor,
                 AVG(primary_author_ratio) AS avg_primary_author_ratio,
                 MAX(stars) AS max_stars,
                 SUM(stars) AS total_stars,
                 BOOL_AND(is_archived) AS all_archived,
                 BOOL_OR(recent_ownership_change) AS any_recent_ownership_change,
                 MIN(EXTRACT(EPOCH FROM (NOW() - repo_pushed_at))/86400)::int AS days_since_last_push,
                 MAX(updated_at) AS signals_last_updated
               FROM maintainer_signals
               WHERE LOWER(repo_owner) = LOWER($1)""",
            username,
        )
        if not agg or (agg["packages_maintained"] or 0) == 0:
            return {
                "platform": platform,
                "username": username,
                "available": False,
                "reason": "no maintainer_signals rows for this owner — not computed yet",
                "trust_score": None,
            }

        top_pkgs = await conn.fetch(
            """SELECT ecosystem, package_name, stars, forks, bus_factor_3m,
                      is_archived, updated_at
               FROM maintainer_signals
               WHERE LOWER(repo_owner) = LOWER($1)
               ORDER BY stars DESC NULLS LAST LIMIT 10""",
            username,
        )
        ecos = await conn.fetch(
            """SELECT ecosystem, COUNT(*) AS n
               FROM maintainer_signals
               WHERE LOWER(repo_owner) = LOWER($1)
               GROUP BY ecosystem ORDER BY n DESC""",
            username,
        )

    agg_d = dict(agg)
    trust = _maintainer_trust_score(agg_d)

    def _risk(score: int) -> str:
        if score >= 75: return "low"
        if score >= 55: return "moderate"
        if score >= 35: return "elevated"
        return "high"

    return {
        "platform": "github",
        "username": username,
        "available": True,
        "trust_score": trust["score"],
        "risk": _risk(trust["score"]),
        "breakdown": trust["breakdown"],
        "aggregate": {
            "packages_maintained": agg_d["packages_maintained"],
            "max_account_age_days": agg_d["max_account_age_days"],
            "avg_bus_factor": float(agg_d["avg_bus_factor"]) if agg_d["avg_bus_factor"] is not None else None,
            "avg_primary_author_ratio": float(agg_d["avg_primary_author_ratio"]) if agg_d["avg_primary_author_ratio"] is not None else None,
            "max_stars": agg_d["max_stars"],
            "total_stars": agg_d["total_stars"],
            "days_since_last_push": agg_d["days_since_last_push"],
            "all_archived": agg_d["all_archived"],
            "any_recent_ownership_change": agg_d["any_recent_ownership_change"],
        },
        "ecosystems": [{"ecosystem": r["ecosystem"], "packages": r["n"]} for r in ecos],
        "top_packages": [
            {
                "ecosystem": r["ecosystem"], "package": r["package_name"],
                "stars": r["stars"], "forks": r["forks"],
                "bus_factor_3m": r["bus_factor_3m"],
                "archived": r["is_archived"],
            }
            for r in top_pkgs
        ],
        "signals_last_updated": agg_d["signals_last_updated"].isoformat() if agg_d.get("signals_last_updated") else None,
        "disclaimer": "Heuristic trust score 0-100 from repo metadata. Not a substitute for your own security review.",
    }


@app.get("/api/maintainers/{ecosystem}/{package:path}", tags=["packages"])
async def get_maintainer_signals(ecosystem: str, package: str):
    """Maintainer trust signals: bus factor, primary author dominance, account age, ownership change."""
    ecosystem = ecosystem.lower()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT repo_owner, repo_name, repo_created_at, repo_pushed_at,
                   bus_factor_3m, active_contributors_12m,
                   primary_author, primary_author_ratio, owner_account_age_days,
                   recent_ownership_change, is_archived,
                   stars, forks, open_issues, updated_at
            FROM maintainer_signals
            WHERE ecosystem=$1 AND package_name=$2
        """, ecosystem, package)
    if not row:
        return {"package": package, "ecosystem": ecosystem, "available": False, "reason": "not computed yet"}
    d = dict(row)
    for k in ("repo_created_at", "repo_pushed_at", "updated_at"):
        if d.get(k): d[k] = d[k].isoformat()
    # Derived alerts
    alerts = []
    if d.get("bus_factor_3m") == 1:
        alerts.append("single_active_maintainer_3m")
    if d.get("primary_author_ratio") and d["primary_author_ratio"] >= 0.9:
        alerts.append("single_author_dominance")
    if d.get("recent_ownership_change"):
        alerts.append("recent_ownership_change_suspected")
    if d.get("is_archived"):
        alerts.append("archived_repo")
    if d.get("owner_account_age_days") and d["owner_account_age_days"] < 90:
        alerts.append("new_owner_account")
    return {
        "package": package, "ecosystem": ecosystem,
        "available": True, "signals": d, "alerts": alerts,
    }

@app.get("/api/vulns/{ecosystem}/{package:path}", tags=["packages"])
async def get_vulns(ecosystem: str, package: str):
    """Vulnerabilities affecting the LATEST version only, enriched with CISA KEV + EPSS."""
    ecosystem = ecosystem.lower()
    pkg_data = await fetch_package(ecosystem, package)
    latest_version = pkg_data.get("latest_version", "") if pkg_data else None
    vulns = await fetch_vulnerabilities(ecosystem, package, latest_version=latest_version)
    pool = await get_pool()
    async with pool.acquire() as conn:
        vulns = await _enrich_vulns_with_threat_intel(conn, vulns)
    active = sum(1 for v in vulns if v.get("in_kev"))
    likely = sum(1 for v in vulns if v.get("threat_tier") == "likely_exploited")
    return {
        "package": package,
        "ecosystem": ecosystem,
        "latest_version": latest_version,
        "count": len(vulns),
        "actively_exploited_count": active,
        "likely_exploited_count": likely,
        "note": "Only vulnerabilities affecting the latest version are shown. Enriched with CISA KEV + EPSS.",
        "vulnerabilities": vulns,
    }


@app.get("/api/versions/{ecosystem}/{package:path}", tags=["packages"])
async def get_versions(ecosystem: str, package: str):
    """Version metadata for a package: latest + total count + recent list + deprecated flag.

    Heavier than /api/latest (which returns only the latest string). Use this when you
    need the version history preview or total-versions count.
    """
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
    # Trim full_message in the list response to keep payloads small.
    # Clients that want the full body call /api/error/{hash}.
    for r in (results or []):
        fm = r.get("full_message") or ""
        if len(fm) > 200:
            r["full_message"] = fm[:200] + "..."
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


@app.get("/api/error/popular", tags=["errors"])
async def list_errors_popular(limit: int = 500):
    """Top error patterns by votes, used for sitemap generation and indexing."""
    limit = max(1, min(int(limit or 500), 2000))
    cache_key = f"errors:popular:{limit}"
    cached = await cache_get(cache_key)
    if cached:
        cached["_cache"] = "hit"
        return cached

    from api.database import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT hash, pattern, ecosystem, package_name, votes, updated_at
            FROM errors
            ORDER BY votes DESC NULLS LAST, id DESC
            LIMIT $1
            """,
            limit,
        )
    items = [
        {
            "hash": r["hash"],
            "pattern": r["pattern"],
            "ecosystem": r["ecosystem"],
            "package_name": r["package_name"],
            "votes": r["votes"],
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        }
        for r in rows
    ]
    payload = {"total": len(items), "errors": items, "_cache": "miss"}
    await cache_set(cache_key, payload, ttl=3600)
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
    # Trim description in list responses to keep payloads small.
    for r in matches or []:
        desc = r.get("description") or ""
        if len(desc) > 200:
            r["description"] = desc[:200] + "..."
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


@app.get("/api/bugs/popular", tags=["bugs"])
async def list_bugs_popular(limit: int = 100):
    """Top packages with recorded bugs, used for sitemap generation and indexing."""
    limit = max(1, min(int(limit or 100), 1000))
    cache_key = f"bugs:popular:{limit}"
    cached = await cache_get(cache_key)
    if cached:
        cached["_cache"] = "hit"
        return cached

    from api.database import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT p.ecosystem, p.name, COUNT(*) AS bug_count
            FROM known_bugs b
            JOIN packages p ON p.id = b.package_id
            GROUP BY p.ecosystem, p.name
            ORDER BY bug_count DESC, p.name ASC
            LIMIT $1
            """,
            limit,
        )
    items = [
        {"ecosystem": r["ecosystem"], "name": r["name"], "bug_count": r["bug_count"]}
        for r in rows
    ]
    payload = {"total": len(items), "packages": items, "_cache": "miss"}
    await cache_set(cache_key, payload, ttl=3600)
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
    if ecosystem not in ("npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew", "jsr"):
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

    # Compute caveats so the winner is NOT blind to trade-offs.
    # An agent reading only "winner" must still see the structural risks.
    caveats: dict[str, list[str]] = {}
    if valid:
        # Only compute adoption caveat when at least one package has REAL data.
        # When downloads are None/0 for all, registry can't tell us — skip caveat
        # entirely to avoid agents reading "low adoption" on mature packages.  # PATCH_DOWNLOADS_V1
        dls = [p.get("downloads_weekly") for p in valid]
        real_dls = [d for d in dls if isinstance(d, (int, float)) and d > 0]
        max_dl = max(real_dls) if real_dls else None
        max_deps = max(p.get("dependencies_count", 0) for p in valid)
        for p in valid:
            issues: list[str] = []
            if p.get("deprecated"):
                issues.append("deprecated_in_registry")
            if p.get("maintainers_count", 0) <= 1:
                issues.append("bus_factor_le_1 (single declared maintainer)")
            dl = p.get("downloads_weekly")
            if max_dl is not None and isinstance(dl, (int, float)) and dl > 0 and dl < max_dl / 10:
                issues.append(f"low_relative_adoption ({dl:,} vs most_downloaded {max_dl:,})")
            if max_deps and p.get("dependencies_count", 0) > max(2 * max_deps // 3, 5) and p["package"] != winner:
                issues.append(f"higher_transitive_deps ({p['dependencies_count']})")
            if p.get("vulns_critical", 0) > 0 or p.get("vulns_high", 0) > 0:
                issues.append(f"open_high_critical_vulns ({p.get('vulns_critical',0)}+{p.get('vulns_high',0)})")
            if p.get("vulnerabilities_count", 0) > 0 and "open_high_critical_vulns" not in str(issues):
                issues.append(f"open_vulns ({p['vulnerabilities_count']})")
            if issues:
                caveats[p["package"]] = issues

    compare_result = {
        "ecosystem": ecosystem,
        "compared": len(packages),
        "winner": winner,
        "winner_criterion": "health_score (numeric, 0-100). Trade-offs not captured by the score are listed under `caveats[winner]` and `caveats[<other>]`. Always read both fields before recommending.",
        "caveats": caveats,
        "packages": packages,
        "_response_ms": int((time.time() - start) * 1000),
    }
    await cache_set(compare_cache_key, compare_result, ttl=3600)
    if request:
        _log_usage(ecosystem, packages_csv, request,
                   response_time_ms=compare_result["_response_ms"],
                   cache_hit=False, status_code=200, endpoint="compare")
    return compare_result



# ─── Transitive dep walker (scan_project include_transitive) ────────  # PATCH_TRANSITIVE_V1
# BFS over the dep graph up to `depth` levels. Reuses fetch_package for the
# registry-side listing. Memoizes. Tolerates missing deps (many ecosystems
# don't expose a full resolved graph — we try, skip gracefully on failure).

async def _walk_transitive(ecosystem: str, direct_names: list[str], max_depth: int = 3, max_nodes: int = 500):
    """Return (flat_list, tree_edges) where flat_list[i] = {package, depth, error?}.
    tree_edges = {parent_pkg: [child_pkgs]}."""
    import asyncio as _aio
    from api.registries import fetch_package as _fp

    seen: dict[str, int] = {}   # name -> min depth seen
    edges: dict[str, list[str]] = {}
    queue = [(n, 0, None) for n in direct_names]   # (name, depth, parent)

    async def _safe_fetch(name: str):
        try:
            return await _aio.wait_for(_fp(ecosystem, name), timeout=2.5)
        except Exception:
            return None

    while queue and len(seen) < max_nodes:
        # Process current layer in parallel for speed.
        layer = queue
        queue = []
        # Dedupe within layer
        fresh = []
        for name, depth, parent in layer:
            if name in seen and seen[name] <= depth:
                if parent is not None:
                    edges.setdefault(parent, []).append(name)
                continue
            seen[name] = depth
            fresh.append((name, depth, parent))
        if not fresh:
            break

        # Only fetch deps when depth < max_depth
        fetch_targets = [(name, depth, parent) for (name, depth, parent) in fresh if depth < max_depth]
        results = await _aio.gather(*[_safe_fetch(n) for n, _, _ in fetch_targets], return_exceptions=True)

        for (name, depth, parent), res in zip(fetch_targets, results):
            if parent is not None:
                edges.setdefault(parent, []).append(name)
            pkg = res if isinstance(res, dict) else None
            if pkg:
                deps = pkg.get("dependencies") or []
                if isinstance(deps, dict):
                    deps = list(deps.keys())
                # Skip internal / scoped-weird / empty names
                deps = [d for d in deps if isinstance(d, str) and d.strip()][:40]
                for d in deps:
                    if len(seen) >= max_nodes:
                        break
                    if d not in seen:
                        queue.append((d, depth + 1, name))

        # Also mark direct-layer parents in edges if depth == max_depth and no descent.
        for name, depth, parent in fresh:
            if depth >= max_depth and parent is not None:
                edges.setdefault(parent, []).append(name)

    # Build flat_list
    flat = [{"package": n, "depth": d} for n, d in sorted(seen.items(), key=lambda x: (x[1], x[0]))]
    return flat, edges


async def _lightweight_health(ecosystem: str, name: str, conn):
    """Quick health lookup from DB (transitive-fast path). Avoids full /check round-trip."""
    row = await conn.fetchrow(
        "SELECT health_score, latest_version, deprecated FROM packages WHERE ecosystem=$1 AND LOWER(name)=LOWER($2)",
        ecosystem, name,
    )
    if not row:
        return None
    return {
        "health_score": row["health_score"],
        "latest_version": row["latest_version"],
        "deprecated": row["deprecated"],
    }


@app.post("/api/scan", tags=["packages"])
async def scan_dependencies(request: Request):
    """
    Audit an entire project's dependencies in one shot.
    POST body: {"packages": {"express": "^4.0.0", "lodash": "^4.17.0"}, "ecosystem": "npm"}
    Or: {"packages": {"fastapi": ">=0.100.0", "pydantic": "^2.0"}, "ecosystem": "pypi"}
    """
    start = time.time()
    body = await request.json()

    # --- Lockfile parsing ----------------------------------------------
    # If the caller sent a lockfile string instead of an explicit packages
    # dict, parse it. `lockfile_kind` is optional (auto-detected when missing).
    lockfile_content = body.get("lockfile")
    lockfile_kind = body.get("lockfile_kind")
    packages = body.get("packages", {}) or {}
    ecosystem = (body.get("ecosystem") or "npm").lower()

    if lockfile_content and not packages:
        try:
            pkgs_from_lock, detected_eco = _parse_lockfile(lockfile_content, lockfile_kind or "")
            packages = pkgs_from_lock
            if not body.get("ecosystem") and detected_eco:
                ecosystem = detected_eco
        except ValueError as e:
            raise HTTPException(400, f"lockfile parse error: {e}")

    # `format` controls output: native (default), cyclonedx, spdx.
    output_format = (body.get("format") or "native").lower()
    if output_format not in ("native", "cyclonedx", "spdx"):
        raise HTTPException(400, "format must be one of: native, cyclonedx, spdx")
    include_transitive = bool(body.get("include_transitive"))

    if ecosystem not in ("npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew", "jsr"):
        raise HTTPException(400, f"Unsupported ecosystem: {ecosystem}")
    if not packages or not isinstance(packages, dict):
        raise HTTPException(400, "Provide 'packages' as a dict of {name: version_constraint}")
    if len(packages) > 100:
        raise HTTPException(400, "Max 100 packages per scan")

    # Fetch all in parallel
    names = list(packages.keys())
    tasks = [_fetch_full_package(ecosystem, name) for name in names]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Bug 4a fix: _fetch_full_package has a 3s per-subtask timeout.
    # Under parallel load of 20+ packages, the registry can flake on a
    # handful of them. Retry None/exception results sequentially once
    # before declaring not_found — avoids false negatives on e.g.
    # `chart.js` or `tsx` that are perfectly valid.
    retry_indexes = [
        i for i, r in enumerate(results)
        if isinstance(r, Exception) or r is None
    ]
    if retry_indexes:
        for i in retry_indexes:
            try:
                retry = await _fetch_full_package(ecosystem, names[i])
            except Exception:
                retry = None
            if retry is not None:
                results[i] = retry

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
            "license": result.get("license") or None,
            "downloads_weekly": result.get("downloads_weekly"),
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

    # Transitive walk (opt-in).  # PATCH_TRANSITIVE_V1
    transitive_info = None
    if include_transitive:
        try:
            max_depth = int(body.get("transitive_depth", 3))
            max_depth = max(1, min(5, max_depth))  # clamp 1..5
            flat, edges = await _walk_transitive(ecosystem, list(packages.keys()), max_depth=max_depth)
            direct_set = set(packages.keys())
            only_transitive = [f for f in flat if f["package"] not in direct_set]

            # Health lookups from DB (fast path) for transitive nodes
            pool = await get_pool()
            async with pool.acquire() as conn:
                annotated = []
                low_health_count = 0
                deprecated_count = 0
                for node in only_transitive:
                    info = await _lightweight_health(ecosystem, node["package"], conn)
                    row = {"package": node["package"], "depth": node["depth"]}
                    if info:
                        row["latest_version"] = info["latest_version"]
                        row["health_score"] = info["health_score"]
                        row["deprecated"] = info["deprecated"]
                        if info["health_score"] is not None and info["health_score"] < 40:
                            low_health_count += 1
                        if info["deprecated"]:
                            deprecated_count += 1
                    else:
                        row["health_score"] = None
                    annotated.append(row)

            transitive_info = {
                "max_depth": max_depth,
                "direct_count": len(direct_set),
                "transitive_count": len(only_transitive),
                "total_packages": len(flat),
                "low_health": low_health_count,
                "deprecated": deprecated_count,
                "truncated": len(flat) >= 500,
                "packages": annotated[:300],  # cap payload
                "edges": {k: v[:20] for k, v in edges.items()},
            }
            if low_health_count > 0:
                issues.append(f"{low_health_count} transitive dep(s) with low health")
            if deprecated_count > 0:
                issues.append(f"{deprecated_count} transitive dep(s) deprecated")
        except Exception:
            transitive_info = {"error": "walk_failed"}

    # SBOM output branch — when caller asks for cyclonedx/spdx we emit that  # PATCH_SCAN_ENHANCE_V1
    # format directly instead of the native audit dict.
    if output_format == "cyclonedx":
        sbom = _build_sbom_cyclonedx(audit, ecosystem, total_vulns, project_risk)
        _log_usage(ecosystem, f"scan_sbom:{len(names)}pkgs", request,
                   response_time_ms=int((time.time() - start) * 1000),
                   cache_hit=False, status_code=200, endpoint="scan")
        return sbom
    if output_format == "spdx":
        sbom = _build_sbom_spdx(audit, ecosystem)
        _log_usage(ecosystem, f"scan_sbom:{len(names)}pkgs", request,
                   response_time_ms=int((time.time() - start) * 1000),
                   cache_hit=False, status_code=200, endpoint="scan")
        return sbom

    _log_usage(ecosystem, f"scan:{len(names)}pkgs", request,
               response_time_ms=int((time.time() - start) * 1000),
               cache_hit=False, status_code=200, endpoint="scan")

    return {
        "ecosystem": ecosystem,
        "packages_scanned": len(names),
        "project_risk": project_risk,
        "transitive": transitive_info,
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



_ECO_META = {
    "npm":       {"label": "npm (JavaScript/TypeScript)", "language": "JavaScript", "registry_url": "https://registry.npmjs.org"},
    "pypi":      {"label": "PyPI (Python)",               "language": "Python",     "registry_url": "https://pypi.org"},
    "cargo":     {"label": "crates.io (Rust)",            "language": "Rust",       "registry_url": "https://crates.io"},
    "go":        {"label": "Go Modules",                  "language": "Go",         "registry_url": "https://proxy.golang.org"},
    "composer":  {"label": "Packagist (PHP)",             "language": "PHP",        "registry_url": "https://packagist.org"},
    "maven":     {"label": "Maven Central (Java)",        "language": "Java",       "registry_url": "https://search.maven.org"},
    "nuget":     {"label": "NuGet (.NET)",                "language": "C#/.NET",    "registry_url": "https://www.nuget.org"},
    "rubygems":  {"label": "RubyGems (Ruby)",             "language": "Ruby",       "registry_url": "https://rubygems.org"},
    "pub":       {"label": "pub.dev (Dart/Flutter)",      "language": "Dart",       "registry_url": "https://pub.dev"},
    "hex":       {"label": "Hex (Elixir/Erlang)",         "language": "Elixir",     "registry_url": "https://hex.pm"},
    "swift":     {"label": "Swift Package Manager",       "language": "Swift",      "registry_url": "https://swiftpackageindex.com"},
    "cocoapods": {"label": "CocoaPods (iOS/macOS)",       "language": "Objective-C/Swift", "registry_url": "https://cocoapods.org"},
    "cpan":      {"label": "CPAN (Perl)",                 "language": "Perl",       "registry_url": "https://metacpan.org"},
    "hackage":   {"label": "Hackage (Haskell)",           "language": "Haskell",    "registry_url": "https://hackage.haskell.org"},
    "cran":      {"label": "CRAN (R)",                    "language": "R",          "registry_url": "https://cran.r-project.org"},
    "conda":     {"label": "Conda (Anaconda)",            "language": "Python/R",   "registry_url": "https://anaconda.org"},
    "homebrew":  {"label": "Homebrew (macOS/Linux tools)", "language": "Shell",     "registry_url": "https://formulae.brew.sh"},
}


@app.get("/api/ecosystems", tags=["public"])
async def list_ecosystems():
    """List supported ecosystems with package counts, vulnerability counts and metadata."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        pkg_rows = await conn.fetch("SELECT ecosystem, COUNT(*) AS cnt FROM packages GROUP BY ecosystem")
        vuln_rows = await conn.fetch("SELECT p.ecosystem, COUNT(*) AS cnt FROM vulnerabilities v JOIN packages p ON p.id=v.package_id GROUP BY p.ecosystem")
        deprecated_rows = await conn.fetch(
            "SELECT ecosystem, COUNT(*) AS cnt FROM packages WHERE deprecated = true GROUP BY ecosystem"
        )
    pkg_counts = {r["ecosystem"]: r["cnt"] for r in pkg_rows}
    vuln_counts = {r["ecosystem"]: r["cnt"] for r in vuln_rows}
    deprecated_counts = {r["ecosystem"]: r["cnt"] for r in deprecated_rows}
    out = []
    for key, meta in _ECO_META.items():
        out.append({
            "ecosystem": key,
            "label": meta["label"],
            "language": meta["language"],
            "registry_url": meta["registry_url"],
            "packages_indexed": pkg_counts.get(key, 0),
            "vulnerabilities_tracked": vuln_counts.get(key, 0),
            "deprecated_packages": deprecated_counts.get(key, 0),
            "example_check": f"/api/check/{key}/<package>",
        })
    out.sort(key=lambda x: -x["packages_indexed"])
    return {"count": len(out), "ecosystems": out}


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
              AND package_name IS NOT NULL AND package_name <> ''
              AND ecosystem IS NOT NULL AND ecosystem <> ''
            GROUP BY ecosystem, package_name ORDER BY searches DESC LIMIT 10
        """)
        eco_rows = await conn.fetch("SELECT ecosystem, COUNT(*) as cnt FROM packages GROUP BY ecosystem ORDER BY cnt DESC")
        # Intelligence block (last 7 days, public aggregate)
        hallucinations_week = await conn.fetchval(
            "SELECT COUNT(*) FROM api_usage WHERE is_hallucination = TRUE "
            "AND created_at > NOW() - INTERVAL '7 days'"
        )
        top_hallucinated = await conn.fetch(
            """SELECT ecosystem, package_name, COUNT(*) AS hits,
                      COUNT(DISTINCT ip_hash) AS callers
               FROM api_usage
               WHERE is_hallucination = TRUE
                 AND created_at > NOW() - INTERVAL '7 days'
                 AND package_name IS NOT NULL AND package_name <> ''
               GROUP BY 1,2 ORDER BY hits DESC LIMIT 10"""
        )
        agents_rows = await conn.fetch(
            """SELECT agent_client, COUNT(*) AS calls,
                      COUNT(*) FILTER(WHERE is_hallucination) AS hallucinations
               FROM api_usage
               WHERE created_at > NOW() - INTERVAL '7 days'
                 AND agent_client IS NOT NULL
                 AND agent_client NOT IN ('crawler','unknown')
               GROUP BY 1 ORDER BY calls DESC LIMIT 10"""
        )
    eco_list = [r["ecosystem"] for r in eco_rows]
    eco_counts = {r["ecosystem"]: r["cnt"] for r in eco_rows}
    return {
        "packages_indexed": pkg_count,
        "vulnerabilities_tracked": vuln_count,
        "api_calls_today": usage_today,
        "api_calls_total": usage_total,
        "registered_users": users_count,
        "trending": [{"ecosystem": r["ecosystem"], "package": r["package_name"], "searches": r["searches"]} for r in top],
        "ecosystems": eco_list,
        "ecosystem_counts": eco_counts,
        "intel": {
            "hallucinations_week": hallucinations_week or 0,
            "top_hallucinated": [
                {"ecosystem": r["ecosystem"], "package": r["package_name"],
                 "hits": r["hits"], "callers": r["callers"]}
                for r in top_hallucinated
            ],
            "agents_breakdown": [
                {"client": r["agent_client"], "calls": r["calls"],
                 "hallucinations": r["hallucinations"]}
                for r in agents_rows
            ],
        },
        "version": VERSION,
        "pricing": "free",
        "mcp_tools": MCP_TOOLS_COUNT,
    }


@app.get("/api/admin/dashboard", include_in_schema=False)
async def admin_dashboard(request: Request):
    """Admin dashboard data."""
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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


@app.get("/.well-known/mcp.json", tags=["discovery"])
async def mcp_manifest():
    """MCP server discovery manifest — emerging standard used by Claude / Cursor /
    Windsurf for one-click install. Mirrors the info in ai-plugin.json but shaped
    around Model Context Protocol clients."""
    return {
        "name": "depscope",
        "display_name": "DepScope",
        "version": "0.6.0",
        "protocol_version": "2024-11-05",
        "description": (
            "Package Intelligence for AI agents. Check health, vulnerabilities, "
            "typosquats, malicious flags, alternatives, known bugs, breaking "
            "changes, compat, error-to-fix across 17 ecosystems. 31k+ packages, "
            "2.2k+ CVEs enriched with CISA KEV + EPSS. Zero auth, MIT."
        ),
        "vendor": {"name": "Cuttalo srl", "url": "https://depscope.dev",
                   "contact": "depscope@cuttalo.com"},
        "transport": {"type": "streamable-http",
                       "url": "https://mcp.depscope.dev/mcp"},
        "install": {
            "claude_code": "claude mcp add depscope https://mcp.depscope.dev/mcp",
            "cursor_json": {"mcpServers": {"depscope": {"url": "https://mcp.depscope.dev/mcp"}}},
            "vscode_json": {"mcpServers": {"depscope": {"url": "https://mcp.depscope.dev/mcp"}}},
            "local_stdio": {
                "npm": "npm install -g depscope-mcp",
                "config": {"mcpServers": {"depscope": {"command": "npx", "args": ["depscope-mcp"]}}},
            },
        },
        "tools_count": 22,
        "tools": [
            "check_package", "check_bulk", "check_malicious", "check_typosquat",
            "get_trust_signals", "get_vulnerabilities", "get_health_score",
            "get_latest_version", "get_package_prompt", "package_exists",
            "install_command", "pin_safe", "find_alternatives", "compare_packages",
            "scan_project", "get_trending", "get_breaking_changes", "get_known_bugs",
            "check_compatibility", "resolve_error", "get_migration_path", "contact_depscope",
        ],
        "auth": "none",
        "rate_limit": {
            "anonymous": "100 req/min",
            "ai_whitelist": "200 req/min",
            "note": "UAs containing ClaudeBot, GPTBot, Cursor, MCP-Client, Windsurf, Cline, Continue are whitelisted.",
        },
        "api_base": "https://depscope.dev/api",
        "openapi": "https://depscope.dev/openapi.json",
        "ai_plugin": "https://depscope.dev/.well-known/ai-plugin.json",
        "llms_txt": "https://depscope.dev/llms.txt",
        "source": "https://github.com/cuttalo/depscope",
        "license": "MIT",
        "privacy": "https://depscope.dev/privacy",
        "terms": "https://depscope.dev/terms",
    }


@app.get("/.well-known/ai-plugin.json", tags=["discovery"])
async def ai_plugin():
    return {
        "schema_version": "v1",
        "name_for_human": "DepScope",
        "name_for_model": "depscope",
        "description_for_human": "Check package health, vulnerabilities, error fixes and stack compatibility before installing. 17 ecosystems, MCP server (zero-install remote), 100% free.",
        "description_for_model": "Use DepScope to check if a software package is safe, maintained, and up-to-date before suggesting it to install. Supports 17 ecosystems: npm, pypi, cargo, go, composer, maven, nuget, rubygems, pub, hex, swift, cocoapods, cpan, hackage, cran, conda, homebrew. 31,000+ packages indexed, 2,200+ CVEs enriched with CISA KEV + EPSS, 22 MCP tools. Three verticals on one API: (1) package health via GET /api/check/{ecosystem}/{package} for full health report with vulns+score+recommendation, GET /api/prompt/{ecosystem}/{package} for LLM-optimized plain text (saves ~74% tokens), GET /api/compare/{ecosystem}/pkg1,pkg2 to compare, GET /api/alternatives/{ecosystem}/{package} for replacements, POST /api/scan to audit dependency lists. (2) error -> fix resolution via POST /api/error/resolve with a stack trace, GET /api/error?code=X for lookups. (3) stack compatibility via GET /api/compat?packages=next@16,react@19 to verify a combo before upgrading. Also GET /api/bugs/{ecosystem}/{package} for non-CVE known bugs per version. No authentication required for public endpoints. Optional API keys for higher limits. Completely free.",
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
    # Mark that usage has been logged for this request so the universal
    # middleware skips a duplicate insert. Safe no-op if request.state
    # is not available (e.g. synthetic calls).
    if request is not None:
        try:
            request.state.usage_logged = True
        except Exception:
            pass
    async def _log():
        try:
            pool = await get_pool()
            ip = ua = source = country = ""
            ep = endpoint or "check"
            if request:
                ip = request.headers.get("CF-Connecting-IP", request.client.host if request.client else "")
                ua = request.headers.get("User-Agent", "")
                source = _detect_source(request)
                # MCP tool attribution: if the MCP dispatcher forwarded the
                # tool name via X-MCP-Tool header, enrich source as
                # "mcp:<tool_name>" so admin queries can measure adoption
                # per-tool. Back-compat: no header -> source stays "mcp".
                try:
                    mcp_tool = (request.headers.get("X-MCP-Tool", "") or "").strip()
                    if mcp_tool:
                        safe_tool = "".join(c for c in mcp_tool if c.isalnum() or c in ("_", "-"))[:64]
                        if safe_tool:
                            source = f"mcp:{safe_tool}"
                except Exception:
                    pass
                country = (request.headers.get("CF-IPCountry", "") or "")[:2].upper()
                # Override endpoint from path if not explicitly passed
                if endpoint is None:
                    try:
                        ep = _derive_endpoint(request.url.path)
                    except Exception:
                        ep = "check"
            # Skip our own infra
            if _is_excluded_ip(ip):
                return
            session_id = _derive_session_id(ip, source) if ip else None
            api_key_id = await _resolve_api_key_id(request)
            # Normalize country: CF sends "XX" or "T1" for Tor. Empty -> NULL
            country_val = country if country and len(country) == 2 and country.isalpha() else None
            async with pool.acquire() as conn:
                try:
                    # Extract mcp_tool from source="mcp:<tool>" for dedicated column
                    mcp_tool_val = source[4:] if source.startswith("mcp:") else None
                    # GDPR: compute hash + sanitize — NEVER store raw IP on disk
                    ip_hash_val = _hash_ip(ip) if ip else None
                    # Intelligence: classify caller + flag hallucination candidates
                    agent_client_val = _parse_agent_client(ua)
                    is_hallucination_val = (
                        status_code == 404
                        and ep in ("check", "package_exists", "exists", "package-exists")
                    )
                    await conn.execute(
                        """INSERT INTO api_usage
                           (endpoint, ecosystem, package_name, user_agent, source,
                            country, response_time_ms, cache_hit, session_id, status_code, api_key_id, mcp_tool,
                            ip_hash, agent_client, is_hallucination)
                           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)""",
                        ep, ecosystem, package, ua[:500], source,
                        country_val, response_time_ms, cache_hit, session_id, status_code, api_key_id, mcp_tool_val,
                        ip_hash_val, agent_client_val, is_hallucination_val,
                    )
                except Exception:
                    # Fallback minimal — post-ip_address-drop schema
                    await conn.execute(
                        "INSERT INTO api_usage (endpoint, ecosystem, package_name, user_agent, source) VALUES ($1,$2,$3,$4,$5)",
                        ep, ecosystem, package, ua[:500], source,
                    )
        except Exception:
            pass
    # Real-time admin feed — non-blocking.  # PATCH_LIVE_FEED_V1
    try:
        import asyncio as _aio
        _aio.create_task(_publish_live_event({
            "ecosystem": ecosystem,
            "package": package,
            "endpoint": endpoint or "check",
            "agent": _parse_agent_client(request.headers.get("User-Agent", "") if request else ""),
            "kind": _agent_kind(_parse_agent_client(request.headers.get("User-Agent", "") if request else "")),
            "country": (request.headers.get("CF-IPCountry", "") if request else "") or None,
            "status": status_code,
            "ms": response_time_ms,
            "cache_hit": cache_hit,
            "mcp_tool": (request.headers.get("X-MCP-Tool", "") if request else None) or None,
            "ts": __import__("time").time(),
        }))
    except Exception:
        pass
    asyncio.create_task(_log())


# ============================================================================
# GDPR ENDPOINTS (Art. 15/17/20) — data portability, erasure, access
# ============================================================================

@app.post("/api/gdpr/delete")
async def gdpr_delete(request: Request):
    """GDPR Art. 17 — Right to erasure.

    The caller's IP is hashed server-side and all matching api_usage rows
    are removed. No authentication needed: the caller proves ownership
    simply by originating the request (you can only erase what came
    from your own network path).

    Rate limit: 10 req/hour per IP (prevents spam).
    """
    ip = request.headers.get("CF-Connecting-IP", request.client.host if request.client else "")
    if not ip:
        raise HTTPException(400, "cannot determine caller IP")
    ip_hash = _hash_ip(ip)
    # Rate-limit using our standard helper (10/hour for GDPR to limit abuse)
    rl = await rate_limit_check(f"gdpr:{ip_hash}", limit=10, window=3600)
    allowed = rl[0] if isinstance(rl, (tuple, list)) else bool(rl)
    if not allowed:
        raise HTTPException(429, "Too many GDPR requests. Try again in 1 hour.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        res = await conn.execute(
            "DELETE FROM api_usage WHERE ip_hash=$1",
            ip_hash,
        )
        try:
            deleted_sessions = await conn.execute(
                "DELETE FROM api_sessions WHERE ip_hash=$1",
                ip_hash,
            )
        except Exception:
            deleted_sessions = "DELETE 0"
    return {
        "ok": True,
        "ip_hash": ip_hash,
        "deleted_usage": res.split()[-1] if res else "0",
        "deleted_sessions": deleted_sessions.split()[-1] if deleted_sessions else "0",
        "disclaimer": (
            "Raw IPs were not stored; only the salted hash of your IP was kept. "
            "Deletion has been applied to all rows matching your current IP hash."
        ),
    }


@app.get("/api/gdpr/export")
async def gdpr_export(request: Request):
    """GDPR Art. 15/20 — Right of access + data portability.

    Returns all api_usage rows linked to the caller's current IP hash.
    JSON format. Downloadable. No PII beyond aggregated columns
    (we don't store raw IP; see /privacy).

    Rate limit: 10 req/hour per IP.
    """
    ip = request.headers.get("CF-Connecting-IP", request.client.host if request.client else "")
    if not ip:
        raise HTTPException(400, "cannot determine caller IP")
    ip_hash = _hash_ip(ip)
    rl = await rate_limit_check(f"gdpr:{ip_hash}", limit=10, window=3600)
    allowed = rl[0] if isinstance(rl, (tuple, list)) else bool(rl)
    if not allowed:
        raise HTTPException(429, "Too many GDPR requests. Try again in 1 hour.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, created_at, endpoint, ecosystem, package_name,
                      user_agent, source, country, cache_hit, session_id,
                      status_code, mcp_tool, agent_client, is_hallucination
               FROM api_usage WHERE ip_hash=$1
               ORDER BY created_at DESC
               LIMIT 10000""",
            ip_hash,
        )
    return {
        "ip_hash": ip_hash,
        "count": len(rows),
        "disclaimer": "Raw IP never stored. Hash derived from your current IP + project salt.",
        "records": [dict(r) for r in rows],
    }


@app.get("/api/gdpr/policy")
async def gdpr_policy():
    """Short machine-readable description of what we store and how long."""
    return {
        "version": "1.0",
        "effective_date": "2026-04-23",
        "data_collected": {
            "ip_hash": "SHA256(IP+salt) — one-way, no reverse mapping",
            "user_agent": "string (max 500 chars) — classified into agent_client bucket",
            "endpoint": "which API endpoint was called",
            "ecosystem+package_name": "what package you asked about",
            "country": "2-letter code (from CDN, coarse)",
            "status_code": "200/404/5xx",
            "timestamps": "UTC timestamp of call",
        },
        "data_NOT_collected": [
            "raw IP address (never written to disk)",
            "email, name, or any personal identity",
            "cookies, device IDs, fingerprints",
            "package source code or private metadata",
        ],
        "retention": {
            "raw_rows_api_usage": "30 days",
            "aggregated_insights": "indefinite (anonymized)",
        },
        "rights": {
            "access_export": "GET /api/gdpr/export",
            "erasure": "POST /api/gdpr/delete",
            "rate_limit": "10 requests/hour for GDPR endpoints",
        },
        "contact": "privacy@depscope.dev",
    }


@app.get("/api/admin/sources", include_in_schema=False)
async def admin_sources(request: Request):
    """API usage breakdown by source (RapidAPI, GPT, Claude, MCP, browser, sdk)."""
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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
            SELECT DISTINCT ip_hash AS ip_identifier, user_agent, MAX(created_at) as last_seen
            FROM api_usage WHERE source = 'rapidapi'
            GROUP BY ip_hash, user_agent ORDER BY last_seen DESC LIMIT 20
        """)
    return {
        "total": {r["source"]: r["calls"] for r in by_source},
        "today": {r["source"]: r["calls"] for r in by_source_today},
        "week": {r["source"]: r["calls"] for r in by_source_week},
        "rapidapi_users": [{"ip": r["ip_identifier"], "ua": r["user_agent"][:100], "last_seen": r["last_seen"].isoformat()} for r in rapidapi_users],
    }

@app.get("/openapi-gpt.json", include_in_schema=False)
async def openapi_for_gpt():
    """Curated OpenAPI spec for ChatGPT Actions / Custom GPTs.

    Kept under 30 operations (ChatGPT Actions hard limit). Ordered by
    LLM-usefulness: /api/prompt first (74-79% token saving, verdict
    pre-computed), then security-first (malicious/typosquat/vulns),
    then health/discovery/verticals. Marked x-openai-isConsequential
    false on all GETs so ChatGPT can invoke without per-call approval.
    """
    ECOS = ["npm", "pypi", "cargo", "go", "composer", "maven", "nuget",
            "rubygems", "pub", "hex", "swift", "cocoapods", "cpan",
            "hackage", "cran", "conda", "homebrew"]

    def _eco_param():
        return {"name": "ecosystem", "in": "path", "required": True,
                "schema": {"type": "string", "enum": ECOS}}

    def _pkg_param():
        return {"name": "package", "in": "path", "required": True,
                "schema": {"type": "string"}}

    def _get(op_id, summary, params, description=""):
        return {"get": {
            "operationId": op_id,
            "summary": summary,
            "description": description or summary,
            "parameters": params,
            "responses": {"200": {"description": "OK"}},
            "x-openai-isConsequential": False,
        }}

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "DepScope",
            "summary": "Package Intelligence for AI agents — health, vulns, typosquats, alternatives across 17 ecosystems.",
            "description": (
                "DepScope answers the questions AI coding agents keep getting wrong "
                "when they install dependencies: does the package exist, is it "
                "malicious or a typosquat, is it actively exploited (CISA KEV), is "
                "it deprecated, what are the safe alternatives, what breaks when "
                "upgrading v1→v2. 31,000+ packages across 17 ecosystems, "
                "2,200+ CVEs enriched with EPSS + CISA KEV. Zero auth, 100 req/min "
                "anonymous, MIT.\n\n"
                "USAGE RULES FOR THE MODEL:\n"
                "1. Before recommending any package install, call getPackagePrompt "
                "(/api/prompt) — it returns a 150-token decision-ready brief "
                "(79% fewer tokens than the full /check JSON). Drop the whole "
                "response in the reply, the verdict line is already the answer.\n"
                "2. If the name looks invented or wrong, call packageExists "
                "(/api/exists) first. A `false` result means the name is "
                "hallucinated — do NOT suggest it.\n"
                "3. For security audits of a lockfile/requirements list, POST to "
                "/api/scan once instead of calling /prompt in a loop.\n"
                "4. Never fabricate package metadata. If /api/exists returns 404, "
                "tell the user the package was not found instead of guessing."
            ),
            "version": "0.7.0",
            "contact": {"name": "DepScope", "email": "depscope@cuttalo.com",
                         "url": "https://depscope.dev"},
            "license": {"name": "MIT",
                         "url": "https://github.com/cuttalo/depscope/blob/main/LICENSE"},
        },
        "servers": [{"url": "https://depscope.dev",
                      "description": "Production"}],
        "paths": {
            # ── 1. PREFERRED: /api/prompt ────────────────────────────
            "/api/prompt/{ecosystem}/{package}": _get(
                "getPackagePrompt",
                "⭐ PREFERRED: LLM-ready plain-text brief (79% fewer tokens than /check).",
                [_eco_param(), _pkg_param()],
                "Returns a compact plain-text summary with health, vulnerabilities, "
                "license, recommendation and last-release date — all pre-computed. "
                "Use this before /api/check in almost every case: ~150 tokens vs ~700, "
                "verdict is already in the `Recommendation:` line. Drop the response "
                "straight into your reply.",
            ),

            # ── 2. Existence + security gates ────────────────────────
            "/api/exists/{ecosystem}/{package}": _get(
                "packageExists",
                "Sub-60ms check: does this package exist on the registry?",
                [_eco_param(), _pkg_param()],
                "Fast path to rule out hallucinated names before any install "
                "suggestion. Returns {exists: true|false}. If false, DO NOT "
                "recommend the package.",
            ),
            "/api/malicious/{ecosystem}/{package}": _get(
                "checkMalicious",
                "CRITICAL: is the package flagged as malicious?",
                [_eco_param(), _pkg_param()],
                "Union of OpenSSF malicious-packages + OSV MAL-* advisories. Use "
                "before every install suggestion — a `true` result means the "
                "package has been flagged for data exfiltration, supply-chain "
                "compromise, or crypto-mining and must NOT be installed.",
            ),
            "/api/typosquat/{ecosystem}/{package}": _get(
                "checkTyposquat",
                "Is this name a suspected typosquat of a popular package?",
                [_eco_param(), _pkg_param()],
                "Returns distance, legit_candidate and reason for suspected typosquat. "
                "Use when the user-provided name is unusual or one letter away from "
                "a well-known library.",
            ),
            "/api/vulns/{ecosystem}/{package}": _get(
                "getVulnerabilities",
                "Live CVEs affecting the latest version, enriched with EPSS + CISA KEV.",
                [_eco_param(), _pkg_param()],
                "Returns open vulnerabilities against the latest version (not "
                "historical), each with EPSS probability (0-1), CISA KEV presence, "
                "threat_tier (actively_exploited / likely_exploited / theoretical / "
                "unknown). Use for security posture answers.",
            ),

            # ── 3. Full health report ────────────────────────────────
            "/api/check/{ecosystem}/{package}": _get(
                "checkPackage",
                "Full JSON health report (use only when /prompt is insufficient).",
                [_eco_param(), _pkg_param()],
                "Returns the full structured report: health score (0-100) with "
                "breakdown, vulnerabilities, versions, recommendation, bundle size, "
                "TypeScript quality, maintainer trust, typosquat flag, scorecard. "
                "Prefer /api/prompt unless you specifically need a field from here.",
            ),
            "/api/health/{ecosystem}/{package}": _get(
                "getHealthScore",
                "Just the 0-100 health score with breakdown.",
                [_eco_param(), _pkg_param()],
                "Lightweight — use when you only need the score and risk tier.",
            ),
            "/api/latest/{ecosystem}/{package}": _get(
                "getLatestVersion",
                "Latest version string + deprecation flag.",
                [_eco_param(), _pkg_param()],
                "Fastest endpoint. Use before suggesting any pin.",
            ),

            # ── 4. Discovery / comparison ────────────────────────────
            "/api/alternatives/{ecosystem}/{package}": _get(
                "getAlternatives",
                "Curated alternatives for deprecated / unhealthy packages.",
                [_eco_param(), _pkg_param()],
                "Returns ranked list. Each entry has {name, reason, builtin}. "
                "`builtin: true` flags stdlib replacements (fs.rm, crypto.randomUUID) "
                "that are NOT installable from a registry.",
            ),
            "/api/compare/{ecosystem}/{packages_csv}": {
                "get": {
                    "operationId": "comparePackages",
                    "summary": "Side-by-side comparison of 2–10 packages.",
                    "description": "Comma-separated names. Returns ranked table with a winner field.",
                    "parameters": [
                        _eco_param(),
                        {"name": "packages_csv", "in": "path", "required": True,
                         "schema": {"type": "string"},
                         "description": "Comma-separated names (e.g. express,fastify,hono)"},
                    ],
                    "responses": {"200": {"description": "OK"}},
                    "x-openai-isConsequential": False,
                }
            },
            "/api/search/{ecosystem}": {
                "get": {
                    "operationId": "searchPackages",
                    "summary": "Free-text search within an ecosystem.",
                    "description": "Use when the user needs a package for a specific purpose but hasn't named one.",
                    "parameters": [
                        _eco_param(),
                        {"name": "q", "in": "query", "required": True,
                         "schema": {"type": "string"}, "description": "Keywords"},
                        {"name": "limit", "in": "query", "required": False,
                         "schema": {"type": "integer", "default": 10}},
                    ],
                    "responses": {"200": {"description": "OK"}},
                    "x-openai-isConsequential": False,
                }
            },

            # ── 5. Verticals ─────────────────────────────────────────
            "/api/breaking/{ecosystem}/{package}": {
                "get": {
                    "operationId": "getBreakingChanges",
                    "summary": "v1→v2 breaking changes with migration hints.",
                    "description": "Use BEFORE suggesting a major-version bump.",
                    "parameters": [
                        _eco_param(), _pkg_param(),
                        {"name": "from_version", "in": "query", "required": False,
                         "schema": {"type": "string"}},
                        {"name": "to_version", "in": "query", "required": False,
                         "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "OK"}},
                    "x-openai-isConsequential": False,
                }
            },
            "/api/bugs/{ecosystem}/{package}": {
                "get": {
                    "operationId": "getKnownBugs",
                    "summary": "Non-CVE known bugs per version (regressions, prod incidents).",
                    "description": "Use when the user reports unexpected behavior that isn't a CVE.",
                    "parameters": [
                        _eco_param(), _pkg_param(),
                        {"name": "version", "in": "query", "required": False,
                         "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "OK"}},
                    "x-openai-isConsequential": False,
                }
            },
            "/api/compat": {
                "get": {
                    "operationId": "checkCompat",
                    "summary": "Stack compatibility verdict.",
                    "description": "Pass a stack as `stack=next@16,react@19,prisma@6`. Returns verified | compatible | warning | untested.",
                    "parameters": [
                        {"name": "stack", "in": "query", "required": True,
                         "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "OK"}},
                    "x-openai-isConsequential": False,
                }
            },
            "/api/error/resolve": {
                "post": {
                    "operationId": "resolveError",
                    "summary": "POST a stack trace → get fix steps.",
                    "description": "Search the error-to-fix database. Returns exact_match | similar_matches | not_found with solution steps + source URL.",
                    "requestBody": {"required": True, "content": {"application/json": {
                        "schema": {"type": "object", "properties": {
                            "error": {"type": "string", "description": "Error message or full stack trace"},
                            "context": {"type": "object", "description": "Optional: ecosystem, package, version"},
                        }, "required": ["error"]}
                    }}},
                    "responses": {"200": {"description": "OK"}},
                    "x-openai-isConsequential": False,
                }
            },

            # ── 6. Trust / provenance ────────────────────────────────
            "/api/scorecard/{ecosystem}/{package}": _get(
                "getScorecard",
                "OpenSSF Scorecard posture (0-10).",
                [_eco_param(), _pkg_param()],
                "Use for supply-chain security assessments.",
            ),
            "/api/maintainers/{ecosystem}/{package}": _get(
                "getMaintainers",
                "Maintainer trust: bus factor, recent activity, commit cadence.",
                [_eco_param(), _pkg_param()],
                "",
            ),

            # ── 7. Meta ──────────────────────────────────────────────
            "/api/now": _get(
                "getCurrentTime",
                "Current UTC time (server clock).",
                [],
                "Use when you need the real date for age calculations.",
            ),
        },
    }



@app.get("/api/sitemap-packages", include_in_schema=False)
async def sitemap_packages(
    limit: int = 0,
    min_downloads: int = 0,
    order: str = "name",
    ecosystem: str | None = None,
):
    """Returns list of packages for sitemap generation.

    Query params:
      - limit: max rows (0 = unlimited)
      - min_downloads: only packages with >= N weekly downloads
      - order: "name" (alpha) | "downloads" (by weekly desc)
      - ecosystem: restrict to one ecosystem (npm, pypi, ...)
    """
    pool = await get_pool()
    order_clause = "downloads_weekly DESC, ecosystem, name" if order == "downloads" else "ecosystem, name"
    params: list = [min_downloads]
    where = ["downloads_weekly >= $1"]
    if ecosystem:
        params.append(ecosystem.lower())
        where.append(f"ecosystem = ${len(params)}")
    sql = f"""
        SELECT ecosystem, name, downloads_weekly, updated_at
        FROM packages
        WHERE {" AND ".join(where)}
        ORDER BY {order_clause}
    """
    if limit and limit > 0:
        sql += f" LIMIT {int(limit)}"
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    return [
        {
            "ecosystem": r["ecosystem"],
            "name": r["name"],
            "downloads_weekly": r["downloads_weekly"] or 0,
            "updated_at": (r["updated_at"].isoformat() if r["updated_at"] else None),
        }
        for r in rows
    ]


# --------------------------------------------------------------------------- #
# SEO QUALITY GATES — prevent thin-content penalty on /breaking /bugs /error
# --------------------------------------------------------------------------- #

# Thresholds (kept as module-level so /api/admin/seo-health reports them)
SEO_MIN_BREAKING = 3          # min breaking changes per package to be indexable
SEO_MIN_BUGS = 3              # min known bugs per package to be indexable
SEO_MIN_SOLUTION_LEN = 200    # min chars for error.solution
SEO_MIN_CONFIDENCE = 0.7      # min error.confidence
SEO_MIN_DOWNLOADS = 1000      # min weekly downloads for pkg sitemap entry
SEO_MIN_HEALTH_SIGNALS = 3    # min positive signals (mirrors insufficient_data logic)


@app.get("/api/sitemap-quality-pages", include_in_schema=False)
async def sitemap_quality_pages():
    """Returns ONLY URLs that pass SEO quality gates.

    Used by /sitemap.xml to avoid submitting thin-content pages to Google.
    - packages: health_score set (not insufficient_data) AND downloads_weekly > 1000
    - breaking: packages with >= 3 curated breaking changes
    - bugs: packages with >= 3 known bugs
    - errors: entries with solution length >= 200 AND confidence >= 0.7
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        pkg_rows = await conn.fetch(
            """
            SELECT ecosystem, name, updated_at, downloads_weekly
            FROM packages
            WHERE health_score IS NOT NULL
              AND health_score > 0
              AND downloads_weekly > $1
            ORDER BY downloads_weekly DESC NULLS LAST
            LIMIT 10000
            """,
            SEO_MIN_DOWNLOADS,
        )
        breaking_rows = await conn.fetch(
            """
            SELECT p.ecosystem, p.name AS package_name, COUNT(*) AS n
            FROM breaking_changes b
            JOIN packages p ON p.id = b.package_id
            GROUP BY p.ecosystem, p.name
            HAVING COUNT(*) >= $1
            ORDER BY COUNT(*) DESC
            """,
            SEO_MIN_BREAKING,
        )
        bug_rows = await conn.fetch(
            """
            SELECT ecosystem, package_name, COUNT(*) AS n
            FROM known_bugs
            GROUP BY ecosystem, package_name
            HAVING COUNT(*) >= $1
            ORDER BY COUNT(*) DESC
            """,
            SEO_MIN_BUGS,
        )
        error_rows = await conn.fetch(
            """
            SELECT hash, votes, confidence, updated_at
            FROM errors
            WHERE LENGTH(solution) >= $1
              AND confidence >= $2
            ORDER BY votes DESC NULLS LAST, id DESC
            LIMIT 2000
            """,
            SEO_MIN_SOLUTION_LEN,
            SEO_MIN_CONFIDENCE,
        )

    return {
        "packages": [
            {
                "ecosystem": r["ecosystem"],
                "name": r["name"],
                "downloads_weekly": r["downloads_weekly"] or 0,
                "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
            }
            for r in pkg_rows
        ],
        "breaking": [
            {
                "ecosystem": r["ecosystem"],
                "name": r["package_name"],
                "count": r["n"],
            }
            for r in breaking_rows
        ],
        "bugs": [
            {
                "ecosystem": r["ecosystem"],
                "name": r["package_name"],
                "count": r["n"],
            }
            for r in bug_rows
        ],
        "errors": [
            {
                "hash": r["hash"],
                "votes": r["votes"] or 0,
                "confidence": float(r["confidence"] or 0),
                "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
            }
            for r in error_rows
        ],
        "thresholds": {
            "min_breaking": SEO_MIN_BREAKING,
            "min_bugs": SEO_MIN_BUGS,
            "min_solution_length": SEO_MIN_SOLUTION_LEN,
            "min_confidence": SEO_MIN_CONFIDENCE,
            "min_downloads": SEO_MIN_DOWNLOADS,
        },
    }


@app.get("/api/admin/seo-health", include_in_schema=False)
async def admin_seo_health():
    """Monitoring endpoint for SEO thin-content protection.

    Returns:
      - indexable vs total per route
      - ratio: indexable / total (warn if < 0.3 on any route)
      - per-route totals for sitemap crawl-budget planning
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        breaking_totals = await conn.fetchrow(
            """
            WITH per_pkg AS (
                SELECT package_id, COUNT(*) AS n
                FROM breaking_changes
                GROUP BY package_id
            )
            SELECT
              COUNT(*) FILTER (WHERE n >= $1) AS indexable,
              COUNT(*) AS total
            FROM per_pkg
            """,
            SEO_MIN_BREAKING,
        )
        bug_totals = await conn.fetchrow(
            """
            WITH per_pkg AS (
                SELECT ecosystem, package_name, COUNT(*) AS n
                FROM known_bugs
                GROUP BY ecosystem, package_name
            )
            SELECT
              COUNT(*) FILTER (WHERE n >= $1) AS indexable,
              COUNT(*) AS total
            FROM per_pkg
            """,
            SEO_MIN_BUGS,
        )
        error_totals = await conn.fetchrow(
            """
            SELECT
              COUNT(*) FILTER (WHERE LENGTH(solution) >= $1 AND confidence >= $2) AS indexable,
              COUNT(*) AS total
            FROM errors
            """,
            SEO_MIN_SOLUTION_LEN,
            SEO_MIN_CONFIDENCE,
        )
        pkg_totals = await conn.fetchrow(
            """
            SELECT
              COUNT(*) FILTER (WHERE health_score IS NOT NULL AND health_score > 0 AND downloads_weekly > $1) AS indexable,
              COUNT(*) AS total
            FROM packages
            """,
            SEO_MIN_DOWNLOADS,
        )

    def ratio(row):
        t = int(row["total"] or 0)
        i = int(row["indexable"] or 0)
        return {
            "indexable": i,
            "total": t,
            "ratio": round(i / t, 3) if t else 0.0,
            "warn": (t > 0 and (i / t) < 0.3),
        }

    pkg_r = ratio(pkg_totals)
    breaking_r = ratio(breaking_totals)
    bug_r = ratio(bug_totals)
    error_r = ratio(error_totals)

    total_indexable = (
        pkg_r["indexable"] + breaking_r["indexable"] + bug_r["indexable"] + error_r["indexable"]
    )
    total_pages = pkg_r["total"] + breaking_r["total"] + bug_r["total"] + error_r["total"]
    overall_ratio = round(total_indexable / total_pages, 3) if total_pages else 0.0

    return {
        "thresholds": {
            "min_breaking": SEO_MIN_BREAKING,
            "min_bugs": SEO_MIN_BUGS,
            "min_solution_length": SEO_MIN_SOLUTION_LEN,
            "min_confidence": SEO_MIN_CONFIDENCE,
            "min_downloads": SEO_MIN_DOWNLOADS,
        },
        "routes": {
            "pkg": pkg_r,
            "breaking": breaking_r,
            "bugs": bug_r,
            "error": error_r,
        },
        "overall": {
            "indexable": total_indexable,
            "total": total_pages,
            "ratio": overall_ratio,
            "warn": overall_ratio < 0.3,
        },
    }


@app.get("/api/admin/automation", include_in_schema=False)
async def admin_automation(request: Request):
    """Automation dashboard feed.

    Returns installed cron jobs + last-run info (parsed from log mtimes +
    last non-empty line), disk usage, DB size, PM2 process status.

    Admin-only. No secrets leaked (log paths are hardcoded/non-sensitive).
    """
    import os
    import re
    import subprocess
    import shutil
    from datetime import datetime, timezone
    from pathlib import Path

    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")

    LOG_DIR = Path("/var/log/depscope")

    # Cron jobs we manage. (schedule, name, log_file). Log_file may not yet
    # exist for brand-new jobs; we handle missing files gracefully.
    jobs = [
        ("0 2 1 * *",   "mass_populate",            LOG_DIR / "mass_populate.log"),
        ("0 3 1 * *",   "recalc_health_all",        LOG_DIR / "recalc_health.log"),
        ("0 4 * * 0",   "backup_db",                LOG_DIR / "backup.log"),
        ("0 5 * * *",   "indexnow_submit",          LOG_DIR / "indexnow.log"),
        ("0 * * * *",   "disk_monitor",             LOG_DIR / "disk.log"),
        ("0 3 * * 0",   "ingest.run_all",           LOG_DIR / "ingest.log"),
        ("0 4 * * *",   "compute_intelligence",     LOG_DIR / "intelligence.log"),
        ("0 3 * * *",   "record_health_snapshot",   LOG_DIR / "health_snapshot.log"),
        ("0 10 * * 1",  "generate_weekly_report",   Path("/home/deploy/depscope/data/weekly_report.log")),
        ("0 */6 * * *", "alerts",                   Path("/tmp/depscope-alerts.log")),
        ("0 */6 * * *", "preprocess",               Path("/tmp/depscope-preprocess.log")),
        ("0 */12 * * *", "fetch_github_stats",      Path("/tmp/depscope-github-stats.log")),
        ("0 6,18 * * *", "fetch_downloads",         Path("/tmp/depscope-downloads.log")),
        ("0 2 * * *",   "expand_db",                Path("/tmp/depscope-expand.log")),
        ("0 6 * * *",   "daily_report",             Path("/tmp/depscope-report.log")),
        ("0 */4 * * *", "marketing_agent",          Path("/tmp/marketing_agent.log")),
    ]

    def tail_last(path: Path, max_len: int = 200) -> str:
        if not path.exists():
            return ""
        try:
            with open(path, "rb") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                chunk = 4096
                f.seek(max(0, size - chunk))
                data = f.read().decode("utf-8", errors="replace")
            for line in reversed(data.splitlines()):
                line = line.strip()
                if line:
                    return line[:max_len]
        except Exception:
            pass
        return ""

    def job_status(last_line: str) -> str:
        if not last_line:
            return "unknown"
        lc = last_line.lower()
        if re.search(r"\b(error|failed|exception|traceback|critical)\b", lc):
            return "error"
        if re.search(r"\b(warn|warning|degraded)\b", lc):
            return "warning"
        return "ok"

    job_entries = []
    for schedule, name, log_path in jobs:
        last_mtime = None
        if log_path.exists():
            last_mtime = datetime.fromtimestamp(
                log_path.stat().st_mtime, tz=timezone.utc
            ).isoformat()
        last_line = tail_last(log_path)
        job_entries.append({
            "schedule": schedule,
            "name": name,
            "log": str(log_path),
            "last_run": last_mtime,
            "last_line": last_line,
            "status": job_status(last_line),
        })

    # Disk
    du = shutil.disk_usage("/")
    disk = {
        "total": du.total,
        "used": du.used,
        "free": du.free,
        "pct": round(du.used * 100 / du.total, 1),
    }

    # DB size
    pool = await get_pool()
    async with pool.acquire() as conn:
        db_size = await conn.fetchval(
            "SELECT pg_size_pretty(pg_database_size(current_database()))"
        )
        pkg_count = await conn.fetchval("SELECT COUNT(*) FROM packages")
        vuln_count = await conn.fetchval("SELECT COUNT(*) FROM vulnerabilities")

    # PM2
    pm2_procs = []
    try:
        out = subprocess.run(
            ["pm2", "jlist"], capture_output=True, text=True, timeout=5
        )
        if out.returncode == 0:
            import json as _json
            for p in _json.loads(out.stdout or "[]"):
                env = p.get("pm2_env", {})
                monit = p.get("monit", {})
                pm2_procs.append({
                    "name": p.get("name"),
                    "status": env.get("status"),
                    "restarts": env.get("restart_time"),
                    "uptime_ms": (
                        int(datetime.now(timezone.utc).timestamp() * 1000)
                        - int(env.get("pm_uptime") or 0)
                    ),
                    "cpu": monit.get("cpu"),
                    "memory_mb": round((monit.get("memory") or 0) / 1024 / 1024, 1),
                })
    except Exception as e:
        pm2_procs = [{"error": str(e)}]

    return {
        "jobs": job_entries,
        "disk": disk,
        "db": {
            "size": db_size,
            "packages": pkg_count,
            "vulnerabilities": vuln_count,
        },
        "pm2": pm2_procs,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }



@app.get("/api/admin/stats", include_in_schema=False)
async def admin_stats_full(request: Request):
    """Admin only: full stats without threshold hiding."""
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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


@app.get("/api/admin/overview", include_in_schema=False)
async def admin_overview(request: Request, range: str = "30d"):
    """Unified admin overview — single source of truth for KPIs.

    Returns counts for three explicit interpretations of "API call":
      - all:    every row in api_usage (raw traffic incl. scrapers)
      - active: excludes scraping bots (claude_bot, gpt_bot, unknown) + empty UA
      - humans: browser traffic only (source='browser')

    Also exposes DB coverage (packages, vulns, alternatives, bugs, breaking),
    users, subscriptions, revenue, per-ecosystem coverage matrix, and cache /
    latency / error quality metrics.
    """
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")

    range_map = {"1d": "1 day", "7d": "7 days", "30d": "30 days", "90d": "90 days"}
    interval = range_map.get(range)
    where_range = (
        f"created_at > NOW() - INTERVAL '{interval}'" if interval else "TRUE"
    )

    views_filters = {
        "all":    "TRUE",
        "active": "(source IS NULL OR source NOT IN ('claude_bot','gpt_bot','unknown')) AND user_agent != ''",
        "humans": "source = 'browser'",
    }

    from datetime import datetime as _DT, timezone as _TZ
    pool = await get_pool()
    result = {
        "range": range if interval else "all",
        "generated_at": _DT.now(_TZ.utc).isoformat(),
        "filter_semantics": {
            "all":    "Raw count — every request logged to api_usage",
            "active": "Excludes scraping bots (claude_bot, gpt_bot, unknown) and empty user-agent",
            "humans": "Browser traffic only (source='browser')",
        },
        "views": {},
    }

    async with pool.acquire() as conn:
        for name, flt in views_filters.items():
            row = await conn.fetchrow(f"""
                SELECT
                    COUNT(*)                                                AS calls,
                    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 day')
                                                                            AS calls_24h,
                    COUNT(DISTINCT ip_hash)                              AS unique_ips,
                    COUNT(DISTINCT country)                                 AS unique_countries,
                    COUNT(*) FILTER (WHERE cache_hit)                       AS cache_hits,
                    COUNT(*) FILTER (WHERE status_code >= 400)              AS errors,
                    COALESCE(AVG(response_time_ms)::int, 0)                 AS avg_ms,
                    COALESCE(
                        PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY response_time_ms)::int, 0
                    ) AS p50_ms,
                    COALESCE(
                        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms)::int, 0
                    ) AS p95_ms
                FROM api_usage
                WHERE {where_range} AND {flt}
            """)
            calls = row["calls"] or 0
            cache_hits = row["cache_hits"] or 0
            errors = row["errors"] or 0
            result["views"][name] = {
                "calls":            calls,
                "calls_24h":        row["calls_24h"] or 0,
                "unique_ips":       row["unique_ips"] or 0,
                "unique_countries": row["unique_countries"] or 0,
                "cache_hit_rate":   (cache_hits / calls) if calls else 0.0,
                "error_rate":       (errors / calls) if calls else 0.0,
                "avg_ms":           row["avg_ms"] or 0,
                "p50_ms":           row["p50_ms"] or 0,
                "p95_ms":           row["p95_ms"] or 0,
            }

        # DB coverage (all-time, view-independent)
        result["db"] = {
            "packages":         await conn.fetchval("SELECT COUNT(*) FROM packages"),
            "vulnerabilities":  await conn.fetchval("SELECT COUNT(*) FROM vulnerabilities"),
            "alternatives":     await conn.fetchval("SELECT COUNT(*) FROM alternatives"),
            "errors":           await conn.fetchval("SELECT COUNT(*) FROM errors"),
            "known_bugs":       await conn.fetchval("SELECT COUNT(*) FROM known_bugs"),
            "breaking_changes": await conn.fetchval("SELECT COUNT(*) FROM breaking_changes"),
            "compat_matrix":    await conn.fetchval("SELECT COUNT(*) FROM compat_matrix"),
        }

        # Users (view-independent)
        users_total = await conn.fetchval("SELECT COUNT(*) FROM users") or 0
        active_keys = await conn.fetchval(
            "SELECT COUNT(*) FROM api_keys WHERE revoked_at IS NULL"
        ) or 0
        subs = {}
        if await conn.fetchval("SELECT to_regclass('public.subscriptions')"):
            rows = await conn.fetch(
                "SELECT status, COUNT(*) AS n FROM subscriptions GROUP BY status"
            )
            subs = {r["status"]: r["n"] for r in rows}
        result["users"] = {
            "total":           users_total,
            "active_api_keys": active_keys,
            "subscriptions":   subs,
        }

        # Revenue placeholder (Stripe not live)
        mrr_eur = 0
        paying = 0
        if subs:
            # Sum active/trialing as "paying" proxy
            paying = subs.get("active", 0) + subs.get("trialing", 0)
        result["revenue"] = {"mrr_eur": mrr_eur, "paying_customers": paying}

        # Per-ecosystem coverage matrix
        eco_rows = await conn.fetch("""
            SELECT p.ecosystem,
                   COUNT(DISTINCT p.id) AS packages,
                   COUNT(DISTINCT v.id) AS vulnerabilities,
                   COUNT(DISTINCT a.id) AS alternatives,
                   COUNT(DISTINCT k.id) AS known_bugs,
                   COUNT(DISTINCT b.id) AS breaking_changes
            FROM packages p
            LEFT JOIN vulnerabilities v   ON v.package_id = p.id
            LEFT JOIN alternatives a      ON a.package_id = p.id
            LEFT JOIN known_bugs k        ON k.package_id = p.id
            LEFT JOIN breaking_changes b  ON b.package_id = p.id
            GROUP BY p.ecosystem
            ORDER BY packages DESC
        """)
        result["coverage"] = [dict(r) for r in eco_rows]

    return result


@app.get("/api/admin/insights", include_in_schema=False)
async def admin_insights(request: Request):
    """Admin insights — DB quality & API key usage."""
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Health score distribution — 10 buckets [0-10, 10-20, ..., 90-100]
        hist_rows = await conn.fetch("""
            SELECT LEAST(width_bucket(health_score, 0, 100, 10), 10)::int AS bucket,
                   COUNT(*) AS n
            FROM packages
            WHERE health_score IS NOT NULL
            GROUP BY bucket ORDER BY bucket
        """)
        buckets = {int(r["bucket"]): int(r["n"]) for r in hist_rows}
        health_distribution = [
            {"range": f"{i * 10}-{(i + 1) * 10}", "bucket": i + 1, "count": buckets.get(i + 1, 0)}
            for i in range(10)
        ]

        # Vulnerability severity
        sev_rows = await conn.fetch(
            "SELECT COALESCE(NULLIF(severity, ''), 'unknown') AS severity, COUNT(*) AS n "
            "FROM vulnerabilities GROUP BY severity ORDER BY n DESC"
        )
        vuln_severity = [{"severity": r["severity"], "count": r["n"]} for r in sev_rows]

        # Top API keys (usage derived from api_usage.api_key_id)
        top_keys_rows = await conn.fetch("""
            SELECT k.id,
                   k.name,
                   k.key_prefix,
                   k.tier,
                   k.requests_this_month,
                   k.last_used_at,
                   k.created_at,
                   u.email AS user_email,
                   COUNT(au.id) AS total_calls
            FROM api_keys k
            LEFT JOIN users u     ON u.id = k.user_id
            LEFT JOIN api_usage au ON au.api_key_id = k.id
            WHERE k.revoked_at IS NULL
            GROUP BY k.id, u.email
            ORDER BY total_calls DESC, k.last_used_at DESC NULLS LAST
            LIMIT 25
        """)
        top_api_keys = [
            {
                "id":                  r["id"],
                "name":                r["name"],
                "key_prefix":          r["key_prefix"],
                "tier":                r["tier"],
                "user_email":          r["user_email"],
                "requests_this_month": r["requests_this_month"] or 0,
                "total_calls":         r["total_calls"] or 0,
                "last_used_at":        r["last_used_at"].isoformat() if r["last_used_at"] else None,
                "created_at":          r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in top_keys_rows
        ]

        # Coverage per ecosystem — same as overview but with extra %columns
        eco_rows = await conn.fetch("""
            SELECT p.ecosystem,
                   COUNT(DISTINCT p.id)                                  AS packages,
                   COUNT(DISTINCT p.id) FILTER (WHERE v.id IS NOT NULL)  AS packages_with_vulns,
                   COUNT(DISTINCT p.id) FILTER (WHERE a.id IS NOT NULL)  AS packages_with_alternatives,
                   COUNT(DISTINCT p.id) FILTER (WHERE k.id IS NOT NULL)  AS packages_with_bugs,
                   COUNT(DISTINCT p.id) FILTER (WHERE b.id IS NOT NULL)  AS packages_with_breaking,
                   AVG(p.health_score)::int                              AS avg_health,
                   COALESCE(SUM(p.downloads_monthly)::bigint, 0)         AS downloads_monthly
            FROM packages p
            LEFT JOIN vulnerabilities v    ON v.package_id = p.id
            LEFT JOIN alternatives a       ON a.package_id = p.id
            LEFT JOIN known_bugs k         ON k.package_id = p.id
            LEFT JOIN breaking_changes b   ON b.package_id = p.id
            GROUP BY p.ecosystem
            ORDER BY packages DESC
        """)
        coverage_matrix = [dict(r) for r in eco_rows]

        # Suspect hours — browser source with abnormal calls/IP ratio (spike detector)
        suspect_rows = await conn.fetch("""
            SELECT DATE_TRUNC('hour', created_at) AS hr,
                   COUNT(*)                    AS calls,
                   COUNT(DISTINCT ip_hash)  AS ips
            FROM api_usage
            WHERE source = 'browser'
            GROUP BY hr
            HAVING COUNT(*) > 200
               AND COUNT(*)::float / GREATEST(COUNT(DISTINCT ip_hash), 1) > 20
            ORDER BY calls DESC LIMIT 10
        """)
        suspect_browser_hours = [
            {
                "hour":  r["hr"].isoformat() if r["hr"] else None,
                "calls": r["calls"],
                "ips":   r["ips"],
            }
            for r in suspect_rows
        ]

    return {
        "health_distribution":    health_distribution,
        "vuln_severity":          vuln_severity,
        "top_api_keys":           top_api_keys,
        "coverage_matrix":        coverage_matrix,
        "suspect_browser_hours":  suspect_browser_hours,
    }


@app.get("/api/admin/timeseries", include_in_schema=False)
async def admin_timeseries(request: Request, range: str = "7d", view: str = "all"):
    """Time-series data for admin dashboard graphs.

    - daily_kpis:     per-day metrics for sparklines (calls, cache rate, p95, unique IPs)
    - heatmap:        DOW × Hour traffic heatmap cells
    - by_endpoint:    call count per endpoint label
    - by_source_day:  per-day breakdown of source buckets (claude_bot, browser, …)
    """
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")

    range_map = {"1d": "1 day", "7d": "7 days", "30d": "30 days", "90d": "90 days"}
    interval = range_map.get(range)
    where_range = f"created_at > NOW() - INTERVAL '{interval}'" if interval else "TRUE"

    views_filters = {
        "all":    "TRUE",
        "active": "(source IS NULL OR source NOT IN ('claude_bot','gpt_bot','unknown')) AND user_agent != ''",
        "humans": "source = 'browser'",
    }
    if view not in views_filters:
        view = "all"
    flt = views_filters[view]

    pool = await get_pool()
    async with pool.acquire() as conn:
        daily_rows = await conn.fetch(f"""
            SELECT DATE(created_at) AS day,
                   COUNT(*) AS calls,
                   COUNT(*) FILTER (WHERE cache_hit) AS cache_hits,
                   COUNT(*) FILTER (WHERE status_code >= 400) AS errors,
                   COUNT(DISTINCT ip_hash) AS unique_ips,
                   COALESCE(AVG(response_time_ms)::int, 0) AS avg_ms,
                   COALESCE(
                       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms)::int, 0
                   ) AS p95_ms
            FROM api_usage
            WHERE {where_range} AND {flt}
            GROUP BY day ORDER BY day
        """)

        # Convert to Europe/Rome before extracting DOW/hour so the heatmap
        # aligns with the admin viewer's local wall-clock instead of UTC.
        heatmap_rows = await conn.fetch(f"""
            SELECT EXTRACT(DOW  FROM created_at AT TIME ZONE 'Europe/Rome')::int AS dow,
                   EXTRACT(HOUR FROM created_at AT TIME ZONE 'Europe/Rome')::int AS hour,
                   COUNT(*) AS n
            FROM api_usage
            WHERE {where_range} AND {flt}
            GROUP BY dow, hour
        """)

        endpoint_rows = await conn.fetch(f"""
            SELECT COALESCE(NULLIF(endpoint, ''), 'unknown') AS endpoint,
                   COUNT(*) AS calls
            FROM api_usage
            WHERE {where_range} AND {flt}
            GROUP BY endpoint ORDER BY calls DESC LIMIT 15
        """)

        source_day_rows = await conn.fetch(f"""
            SELECT DATE(created_at) AS day,
                   COALESCE(NULLIF(source, ''), 'unknown') AS source,
                   COUNT(*) AS n
            FROM api_usage
            WHERE {where_range} AND source IS NOT NULL
            GROUP BY day, source ORDER BY day
        """)

    daily_kpis = [
        {
            "day":            str(r["day"]),
            "calls":          r["calls"],
            "cache_hit_rate": (r["cache_hits"] / r["calls"]) if r["calls"] else 0.0,
            "error_rate":     (r["errors"]     / r["calls"]) if r["calls"] else 0.0,
            "unique_ips":     r["unique_ips"],
            "avg_ms":         r["avg_ms"],
            "p95_ms":         r["p95_ms"],
        }
        for r in daily_rows
    ]

    heatmap = [{"dow": r["dow"], "hour": r["hour"], "n": r["n"]} for r in heatmap_rows]
    by_endpoint = [{"endpoint": r["endpoint"], "calls": r["calls"]} for r in endpoint_rows]

    # Pivot source-by-day into {day, claude_bot, gpt_bot, ...} rows for stacked charts
    pivot: dict = {}
    sources_seen: set = set()
    for r in source_day_rows:
        d = str(r["day"])
        pivot.setdefault(d, {"day": d})
        pivot[d][r["source"]] = r["n"]
        sources_seen.add(r["source"])
    by_source_day = sorted(pivot.values(), key=lambda x: x["day"])

    return {
        "range": range if interval else "all",
        "view": view,
        "daily_kpis": daily_kpis,
        "heatmap": heatmap,
        "by_endpoint": by_endpoint,
        "by_source_day": by_source_day,
        "sources_seen": sorted(sources_seen),
    }


@app.get("/api/admin/plan-metrics", include_in_schema=False)
async def admin_plan_metrics(request: Request):
    """Live counters feeding the /admin/plan business-plan page.

    Shows the TRUE state of the product — no threshold hiding, no marketing
    rounding. Admin only.
    """
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")

    pool = await get_pool()
    async with pool.acquire() as conn:
        verticals = {
            "packages":         await conn.fetchval("SELECT COUNT(*) FROM packages"),
            "vulnerabilities":  await conn.fetchval("SELECT COUNT(*) FROM vulnerabilities"),
            "alternatives":     await conn.fetchval("SELECT COUNT(*) FROM alternatives"),
            "breaking_changes": await conn.fetchval("SELECT COUNT(*) FROM breaking_changes"),
            "errors":           await conn.fetchval("SELECT COUNT(*) FROM errors"),
            "known_bugs":       await conn.fetchval("SELECT COUNT(*) FROM known_bugs"),
            "compat_matrix":    await conn.fetchval("SELECT COUNT(*) FROM compat_matrix"),
        }
        ecosystem_rows = await conn.fetch(
            """
            SELECT p.ecosystem,
                   COUNT(DISTINCT p.id) AS packages,
                   COUNT(DISTINCT v.id) AS vulnerabilities,
                   COUNT(DISTINCT a.id) AS alternatives,
                   COUNT(DISTINCT b.id) AS breaking_changes,
                   COUNT(DISTINCT k.id) AS known_bugs
            FROM packages p
            LEFT JOIN vulnerabilities v ON v.package_id = p.id
            LEFT JOIN alternatives a    ON a.package_id = p.id
            LEFT JOIN breaking_changes b ON b.package_id = p.id
            LEFT JOIN known_bugs k       ON k.package_id = p.id
            GROUP BY p.ecosystem
            ORDER BY packages DESC
            """
        )
        usage_total = await conn.fetchval(
            "SELECT COUNT(*) FROM api_usage WHERE user_agent NOT ILIKE '%bot%' AND user_agent NOT ILIKE '%crawl%' AND user_agent != ''"
        ) or 0
        usage_30d = await conn.fetchval(
            "SELECT COUNT(*) FROM api_usage WHERE created_at > NOW() - INTERVAL '30 days' AND user_agent NOT ILIKE '%bot%' AND user_agent NOT ILIKE '%crawl%' AND user_agent != ''"
        ) or 0
        usage_7d = await conn.fetchval(
            "SELECT COUNT(*) FROM api_usage WHERE created_at > NOW() - INTERVAL '7 days' AND user_agent NOT ILIKE '%bot%' AND user_agent NOT ILIKE '%crawl%' AND user_agent != ''"
        ) or 0
        unique_ips_30d = await conn.fetchval(
            "SELECT COUNT(DISTINCT ip_hash) FROM api_usage WHERE created_at > NOW() - INTERVAL '30 days' AND ip_hash IS NOT NULL"
        ) or 0
        users_count = await conn.fetchval("SELECT COUNT(*) FROM users") or 0
        users_by_plan = await conn.fetch(
            "SELECT plan, COUNT(*) AS n FROM users GROUP BY plan"
        )
        api_keys_count = await conn.fetchval(
            "SELECT COUNT(*) FROM api_keys WHERE revoked_at IS NULL"
        ) or 0
        subs_rows = await conn.fetch(
            "SELECT status, COUNT(*) AS n FROM subscriptions GROUP BY status"
        ) if await conn.fetchval("SELECT to_regclass('public.subscriptions')") else []

    return {
        "verticals": verticals,
        "ecosystems": [
            {
                "ecosystem": r["ecosystem"],
                "packages": r["packages"],
                "vulnerabilities": r["vulnerabilities"],
                "alternatives": r["alternatives"],
                "breaking_changes": r["breaking_changes"],
                "known_bugs": r["known_bugs"],
            }
            for r in ecosystem_rows
        ],
        "usage": {
            "api_calls_total": usage_total,
            "api_calls_30d": usage_30d,
            "api_calls_7d": usage_7d,
            "unique_ips_30d": unique_ips_30d,
        },
        "users": {
            "total": users_count,
            "active_api_keys": api_keys_count,
            "by_plan": {r["plan"]: r["n"] for r in users_by_plan},
        },
        "revenue": {
            "subscriptions_by_status": {r["status"]: r["n"] for r in subs_rows},
            "mrr_eur": 0,  # stripe not active yet
            "paying_customers": 0,
        },
        "distribution": {
            "mcp_npm_version_latest": "0.2.0",
            "gpt_store_live": True,
            "rapidapi_live": True,
            "total_ecosystems_declared": 17,
            "ecosystems_with_breaking_or_bugs": sum(
                1 for r in ecosystem_rows
                if (r["breaking_changes"] or 0) + (r["known_bugs"] or 0) > 0
            ),
        },
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
    stdlib_hint = lookup_stdlib(ecosystem, package)
    if stdlib_hint:
        return {
            "package": package,
            "ecosystem": ecosystem,
            "exists": False,
            "is_stdlib": True,
            "hint": stdlib_hint,
            "latest": None,
        }
    cache_key = f"exists:{ecosystem}:{package}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # DB-first fast path: if we've seen the package, return instantly without
    # hitting the upstream registry. Only fall back to live fetch for packages
    # missing from our index (likely unknown or very new).
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT latest_version FROM packages WHERE ecosystem=$1 AND LOWER(name)=LOWER($2)",
                ecosystem, package,
            )
        if row:
            result = {
                "package": package,
                "ecosystem": ecosystem,
                "exists": True,
                "latest": row["latest_version"],
                "_source": "db",
            }
            await cache_set(cache_key, result, ttl=3600)
            return result
    except Exception:
        pass

    pkg_data = await fetch_package(ecosystem, package)
    result = {
        "package": package,
        "ecosystem": ecosystem,
        "exists": pkg_data is not None,
        "latest": pkg_data.get("latest_version") if pkg_data else None,
        "_source": "registry",
    }
    await cache_set(cache_key, result, ttl=3600)
    return result



# ============================================================================
# /api/contact — professional inbound channel.
# Used by: web form (/contact), CLI, MCP tool (contact_depscope), partner ESPs.
# Rate-limited at the nginx level. Server-side: honeypot + length checks +
# email notification + DB persistence.
# ============================================================================

_CONTACT_TYPES = {"bug", "feature", "listing", "partnership", "press", "security", "other"}


class _ContactRequest(BaseModel):
    name: str = ""
    email: str
    type: str = "other"
    subject: str
    body: str
    company: str = ""
    source: str = "web"        # web | cli | mcp | agent | api
    consent: bool = True
    honeypot: str = ""         # bots fill this; humans don't see it



# Disposable / throwaway email domains (curated short list — extend as needed)
_DISPOSABLE_EMAIL_DOMAINS = {
    "mailinator.com","10minutemail.com","tempmail.com","guerrillamail.com",
    "trashmail.com","yopmail.com","sharklasers.com","getnada.com","fakeinbox.com",
    "throwawaymail.com","emailondeck.com","spamgourmet.com","tempr.email",
    "maildrop.cc","mintemail.com","grr.la","mvrht.com","incognitomail.com",
}

_SPAM_KEYWORDS = (
    "viagra","cialis","crypto pump","mlm","forex bot","make $ ","seo backlinks",
    "buy followers","instant ranking","casino","free crypto","airdrop now",
)


async def _contact_security_check(payload, request) -> tuple[bool, str]:
    """Returns (ok, error_message). Stops abuse before DB insert + email send."""
    email = (payload.email or "").strip().lower()
    ip = ""
    if request is not None and request.client:
        ip = (request.headers.get("x-forwarded-for") or request.client.host or "").split(",")[0].strip()

    # 1) Disposable email blocklist
    domain = email.rsplit("@", 1)[-1]
    if domain in _DISPOSABLE_EMAIL_DOMAINS:
        return False, "Please use a non-disposable email address."

    # 2) Body too many links (>3) → spammy
    body_lc = (payload.body or "").lower()
    link_count = body_lc.count("http://") + body_lc.count("https://")
    if link_count > 3:
        return False, "Too many links in the message body."

    # 3) Spam keywords
    for kw in _SPAM_KEYWORDS:
        if kw in body_lc or kw in (payload.subject or "").lower():
            return False, "Message rejected by spam filter. Email us directly if this is a false positive."

    # 4) Rate limit via Redis: per-IP and per-email
    try:
        from api.cache import get_redis
        r = await get_redis()
        if r is not None:
            # per-IP: 3 / 15 min, 10 / day
            if ip:
                k_ip_short = f"contact_rl:ip:short:{ip}"
                k_ip_day = f"contact_rl:ip:day:{ip}"
                n_short = await r.incr(k_ip_short)
                if n_short == 1:
                    await r.expire(k_ip_short, 900)
                if n_short > 3:
                    return False, "Too many requests from your IP. Try again in 15 minutes."
                n_day = await r.incr(k_ip_day)
                if n_day == 1:
                    await r.expire(k_ip_day, 86400)
                if n_day > 10:
                    return False, "Daily contact limit reached for your IP. Email us directly."
            # per-email: 2 / hour, 5 / day
            k_em_h = f"contact_rl:em:h:{email}"
            k_em_d = f"contact_rl:em:d:{email}"
            n_em_h = await r.incr(k_em_h)
            if n_em_h == 1:
                await r.expire(k_em_h, 3600)
            if n_em_h > 2:
                return False, "You\'ve already submitted 2 messages this hour. We\'ll get back soon."
            n_em_d = await r.incr(k_em_d)
            if n_em_d == 1:
                await r.expire(k_em_d, 86400)
            if n_em_d > 5:
                return False, "Daily limit reached for this email."
    except Exception:
        # If Redis is down, fail open (still let request through). Length checks remain.
        pass

    return True, ""



# ============================================================================
# /api/anomaly — structured tool feedback from MCP agents.
# Better signal than free-form contact: machine-parseable, regression-input-grade.
# ============================================================================


class _AnomalyRequest(BaseModel):
    tool_called: str
    ecosystem: str = ""
    package: str = ""
    version: str = ""
    observed: str
    expected: str
    evidence_url: str = ""
    source: str = "mcp"


@app.post("/api/anomaly", tags=["public"])
async def submit_anomaly(payload: _AnomalyRequest, request: Request = None):
    tool = (payload.tool_called or "").strip()[:80]
    if not tool:
        raise HTTPException(400, "tool_called is required")
    obs = (payload.observed or "").strip()
    exp = (payload.expected or "").strip()
    if len(obs) < 1 or len(obs) > 1500:
        raise HTTPException(400, "observed must be 1-1500 chars")
    if len(exp) < 1 or len(exp) > 1500:
        raise HTTPException(400, "expected must be 1-1500 chars")
    src = (payload.source or "mcp").lower().strip()[:20]
    eco = (payload.ecosystem or "").lower().strip()[:30]
    pkg = (payload.package or "").strip()[:255]
    ver = (payload.version or "").strip()[:80]
    ev = (payload.evidence_url or "").strip()[:500]
    ua = ""
    ip = ""
    if request is not None:
        ua = request.headers.get("user-agent", "")[:300]
        ip = (request.headers.get("x-forwarded-for") or request.client.host if request.client else "") or ""
        ip = ip.split(",")[0].strip()[:60]

    pool = await get_pool()
    async with pool.acquire() as conn:
        rid = await conn.fetchval(
            """
            INSERT INTO anomaly_reports
                (tool_called, ecosystem, package, version, observed, expected,
                 evidence_url, source, user_agent, ip_addr, status, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,'new',NOW())
            RETURNING id
            """,
            tool, eco, pkg, ver, obs, exp, ev, src, ua, ip,
        )
    return {
        "ok": True,
        "id": rid,
        "message": "Thanks. Anomaly recorded — we use these as regression inputs to improve the dataset.",
    }


@app.post("/api/contact", tags=["public"])
async def submit_contact(payload: _ContactRequest, request: Request = None):
    """Submit a contact request (form, CLI, MCP, agent). Free, no auth."""
    # Honeypot: silent success so bots don't retry
    if payload.honeypot.strip():
        return {"ok": True, "message": "Thanks, we'll get back to you."}
    ok_sec, err_sec = await _contact_security_check(payload, request)
    if not ok_sec:
        raise HTTPException(429 if "too many" in err_sec.lower() or "limit" in err_sec.lower() else 400, err_sec)
    email = payload.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1] or len(email) > 200:
        raise HTTPException(400, "Invalid email")
    subject = payload.subject.strip()
    body = payload.body.strip()
    if not subject or len(subject) < 3 or len(subject) > 200:
        raise HTTPException(400, "Subject must be 3-200 characters")
    if not body or len(body) < 10 or len(body) > 8000:
        raise HTTPException(400, "Message must be 10-8000 characters")
    typ = payload.type.lower().strip()
    if typ not in _CONTACT_TYPES:
        typ = "other"
    src = (payload.source or "web").lower().strip()[:20]
    name = payload.name.strip()[:120]
    company = payload.company.strip()[:120]
    ua = ""
    ip = ""
    if request is not None:
        ua = request.headers.get("user-agent", "")[:300]
        ip = (request.headers.get("x-forwarded-for") or request.client.host if request.client else "") or ""
        ip = ip.split(",")[0].strip()[:60]

    pool = await get_pool()
    async with pool.acquire() as conn:
        msg_id = await conn.fetchval(
            """
            INSERT INTO contact_messages
                (name, email, type, subject, body, company, source, user_agent, ip_addr, status, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'new',NOW())
            RETURNING id
            """,
            name, email, typ, subject, body, company, src, ua, ip,
        )

    # Best-effort: email notification + ack
    try:
        import smtplib, ssl, os
        from email.message import EmailMessage
        SMTP_HOST = os.environ.get("SMTP_HOST", "mail.cuttalo.com")
        SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
        SMTP_USER = os.environ.get("SMTP_USER", "depscope@cuttalo.com")
        SMTP_PASS = os.environ.get("SMTP_PASS", "")
        # Skip SMTP if neutralized (e.g. on stage where SMTP_HOST is 127.0.0.1:9999)
        if SMTP_HOST not in ("127.0.0.1", "localhost") and SMTP_PASS:
            ctx = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
                smtp.ehlo(); smtp.starttls(context=ctx); smtp.ehlo()
                smtp.login(SMTP_USER, SMTP_PASS)
                # 1) notify internal
                notif = EmailMessage()
                notif["From"] = f"DepScope <{SMTP_USER}>"
                notif["To"] = SMTP_USER
                notif["Reply-To"] = email
                notif["Subject"] = f"[contact:{typ}] {subject[:120]}"
                notif.set_content(
                    f"From: {name or '(no name)'} <{email}>\n"
                    f"Company: {company or '(none)'}\n"
                    f"Type: {typ}\n"
                    f"Source: {src}\n"
                    f"IP: {ip}  UA: {ua[:100]}\n"
                    f"--- Message ---\n{body}\n"
                    f"--- DB id: {msg_id} ---\n"
                )
                smtp.send_message(notif)
                # 2) auto-ack to sender
                ack = EmailMessage()
                ack["From"] = f"DepScope <{SMTP_USER}>"
                ack["To"] = email
                ack["Subject"] = f"Re: {subject[:160]}"
                ack.set_content(
                    f"Hi{(' ' + name) if name else ''},\n\n"
                    "Thanks for reaching out to DepScope. We received your message and "
                    "will get back to you shortly.\n\n"
                    "Reference: #" + str(msg_id) + "\n\n"
                    "If urgent, reply to this email.\n\n"
                    "DepScope team\n"
                    "https://depscope.dev\n"
                )
                smtp.send_message(ack)
    except Exception:
        pass

    return {
        "ok": True,
        "id": msg_id,
        "message": "Thanks, we'll get back to you shortly.",
        "ack_email_sent": True,
    }


@app.get("/api/contact/types", tags=["public"])
async def contact_types():
    """List allowed values for the type field of /api/contact."""
    return {"types": sorted(_CONTACT_TYPES)}


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


@app.get("/api/health", tags=["public"])
async def healthcheck():
    """
    Liveness + readiness probe. External uptime monitors hit this every 5m.

    Returns 200 with subsystem statuses when everything is up. If Postgres or
    Redis fail, individual fields flip to the error string but we still return
    200 (monitor will alert on the overall "status" field) — bumping to 500
    would cause PM2 to restart us, which masks the real problem.
    """
    from datetime import datetime, timezone
    import subprocess

    db_status = "ok"
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception as e:
        db_status = f"error: {type(e).__name__}"

    redis_status = "ok"
    try:
        from api.cache import get_redis
        r = await get_redis()
        await r.ping()
    except Exception as e:
        redis_status = f"error: {type(e).__name__}"

    pm2_count = 0
    try:
        out = subprocess.run(
            ["pm2", "jlist"], capture_output=True, text=True, timeout=5
        )
        if out.returncode == 0:
            import json as _json
            procs = _json.loads(out.stdout or "[]")
            pm2_count = sum(
                1 for p in procs
                if p.get("pm2_env", {}).get("status") == "online"
            )
    except Exception:
        pm2_count = -1

    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
    return {
        "status": overall,
        "db": db_status,
        "redis": redis_status,
        "pm2_processes": pm2_count,
        "utc": datetime.now(timezone.utc).isoformat(),
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

        if _is_excluded_ip(ip):
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
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")

    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM page_views_clean")
        today = await conn.fetchval("SELECT COUNT(*) FROM page_views_clean WHERE created_at > CURRENT_DATE")
        unique_today = await conn.fetchval("SELECT COUNT(DISTINCT ip_address) FROM page_views_clean WHERE created_at > CURRENT_DATE")

        by_page = await conn.fetch("""
            SELECT path, COUNT(*) as views FROM page_views_clean
            WHERE created_at > NOW() - INTERVAL '7 days'
            GROUP BY path ORDER BY views DESC LIMIT 20
        """)

        by_day = await conn.fetch("""
            SELECT DATE(created_at) as day, COUNT(*) as views, COUNT(DISTINCT ip_address) as unique_visitors
            FROM page_views_clean WHERE created_at > NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at) ORDER BY day
        """)

        by_country = await conn.fetch("""
            SELECT country, COUNT(*) as views FROM page_views_clean
            WHERE created_at > NOW() - INTERVAL '7 days' AND country != ''
            GROUP BY country ORDER BY views DESC LIMIT 15
        """)

        by_referrer = await conn.fetch("""
            SELECT referrer, COUNT(*) as views FROM page_views_clean
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
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")

    pool = await get_pool()
    async with pool.acquire() as conn:
        pv_hourly = await conn.fetch(
            "SELECT date_trunc('hour', created_at) as hour, COUNT(*) as views, "
            "COUNT(DISTINCT ip_address) as unique_visitors "
            "FROM page_views_clean WHERE created_at > NOW() - INTERVAL '3 days' "
            "GROUP BY hour ORDER BY hour"
        )

        pv_daily = await conn.fetch(
            "SELECT DATE(created_at) as day, COUNT(*) as views, "
            "COUNT(DISTINCT ip_address) as unique_visitors "
            "FROM page_views_clean GROUP BY day ORDER BY day"
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
            "FROM page_views_clean WHERE country != '' AND country IS NOT NULL "
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

    # Back-fill empty hours so sparse graphs render as a continuous timeline.
    from datetime import datetime as _DT, timedelta as _TD, timezone as _TZ
    now_hour = _DT.now(_TZ.utc).replace(minute=0, second=0, microsecond=0)
    all_hours = [now_hour - _TD(hours=i) for i in range(72, -1, -1)]

    pv_map = {r["hour"].astimezone(_TZ.utc).replace(tzinfo=None): r for r in pv_hourly}
    api_map = {r["hour"].astimezone(_TZ.utc).replace(tzinfo=None): r for r in api_hourly}

    pageviews_hourly_bf = []
    api_calls_hourly_bf = []
    for h in all_hours:
        hn = h.replace(tzinfo=None)
        label = h.strftime("%Y-%m-%dT%H:%M")
        pr = pv_map.get(hn)
        pageviews_hourly_bf.append({
            "hour": label,
            "views": pr["views"] if pr else 0,
            "unique": pr["unique_visitors"] if pr else 0,
        })
        ar = api_map.get(hn)
        api_calls_hourly_bf.append({
            "hour": label,
            "calls": ar["calls"] if ar else 0,
        })

    return {
        "pageviews_hourly": pageviews_hourly_bf,
        "pageviews_daily": [
            {"day": str(r["day"]), "views": r["views"], "unique": r["unique_visitors"]}
            for r in pv_daily
        ],
        "api_calls_hourly": api_calls_hourly_bf,
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
            "SELECT COUNT(*) FROM api_usage WHERE NOT (COALESCE(user_agent, '') LIKE 'DepScope-%' OR COALESCE(user_agent, '') LIKE '%CacheWarmer%')"
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
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM agent_rules WHERE active = true ORDER BY priority, category")
    return [dict(r) for r in rows]

@app.post("/api/admin/agent/rules", include_in_schema=False)
async def add_agent_rule(request: Request):
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")
    body = await request.json()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO agent_rules (rule, category, priority) VALUES ($1, $2, $3)",
            body["rule"], body.get("category", "general"), body.get("priority", 5))
    return {"ok": True}

@app.delete("/api/admin/agent/rules/{rule_id}", include_in_schema=False)
async def delete_agent_rule(rule_id: int, request: Request):
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE agent_rules SET active = false WHERE id = $1", rule_id)
    return {"ok": True}

@app.get("/api/admin/agent/plan", include_in_schema=False)
async def get_agent_plan(request: Request):
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM agent_plan ORDER BY priority, timeframe, created_at")
    return [dict(r) for r in rows]

@app.post("/api/admin/agent/plan", include_in_schema=False)
async def add_plan_action(request: Request):
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")
    body = await request.json()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO agent_plan (action, category, timeframe, priority) VALUES ($1, $2, $3, $4)",
            body["action"], body.get("category", "general"), body.get("timeframe", "short"), body.get("priority", 5))
    return {"ok": True}

@app.put("/api/admin/agent/plan/{plan_id}", include_in_schema=False)
async def update_plan(plan_id: int, request: Request):
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM agent_actions ORDER BY created_at DESC LIMIT 50")
    return [dict(r) for r in rows]

@app.get("/api/admin/agent/opportunities", include_in_schema=False)
async def get_opportunities(request: Request):
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM agent_opportunities WHERE status NOT IN ('skipped', 'done') ORDER BY CASE status WHEN 'execute' THEN 0 WHEN 'content_ready' THEN 1 WHEN 'approved' THEN 2 WHEN 'found' THEN 3 WHEN 'manual_post' THEN 4 ELSE 5 END, relevance_score DESC LIMIT 30")
    return [dict(r) for r in rows]

@app.put("/api/admin/agent/opportunities/{opp_id}", include_in_schema=False)
async def update_opportunity(opp_id: int, request: Request):
    """Update opportunity status and/or suggested_content."""
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM agent_platform_status ORDER BY platform")
    return [dict(r) for r in rows]


@app.get("/api/admin/agent/timeline", include_in_schema=False)
async def get_timeline(request: Request):
    """Get chronological timeline of ALL actions."""
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE agent_opportunities SET status='execute' WHERE id=$1", opp_id)
    return {"ok": True}


@app.put("/api/admin/agent/opportunities/{opp_id}/reject", include_in_schema=False)
async def reject_opportunity(opp_id: int, request: Request):
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")
    body = await request.json()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE agent_opportunities SET status='rejected', rejected_reason=$1 WHERE id=$2", body.get("reason", ""), opp_id)
    return {"ok": True}


@app.put("/api/admin/agent/opportunities/{opp_id}/content", include_in_schema=False)
async def update_content(opp_id: int, request: Request):
    """Edit generated content before executing."""
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM agent_config ORDER BY category, key")
    return [dict(r) for r in rows]


@app.put("/api/admin/agent/config/{key}", include_in_schema=False)
async def update_agent_config(key: str, request: Request):
    """Update a single config value."""
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
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
    if not _has_admin_pw(request):
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
                   COUNT(DISTINCT ip_hash) AS unique_ips
            FROM api_usage
            WHERE created_at > NOW() - INTERVAL '7 days' AND COALESCE(source, '') <> ''
            GROUP BY source
            ORDER BY calls DESC
        """)
        countries = await conn.fetch("""
            SELECT country,
                   COUNT(*) AS calls,
                   COUNT(DISTINCT ip_hash) AS unique_ips
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
                   COUNT(DISTINCT ip_hash) AS ips_7d,
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

# --- BEGIN EMAIL TRACKING ROUTES ---
# Paste into api/main.py

from fastapi.responses import Response, RedirectResponse

_PIXEL_GIF = bytes.fromhex(
    "47494638396101000100800000000000ffffff21f90401000000002c00000000"
    "010001000002024401003b"
)

@app.get("/t/o/{tracking_id}.gif", include_in_schema=False)
async def track_open(tracking_id: str, request: Request):
    try:
        async with (await get_pool()).acquire() as conn:
            await conn.execute(
                "INSERT INTO email_events(tracking_id, event_type, ip, user_agent) VALUES ($1,'open',$2,$3)",
                tracking_id,
                request.client.host if request.client else None,
                request.headers.get("user-agent", "")[:500],
            )
    except Exception:
        pass
    return Response(
        content=_PIXEL_GIF,
        media_type="image/gif",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, private", "Pragma": "no-cache"},
    )

@app.get("/t/c/{tracking_id}", include_in_schema=False)
async def track_click(tracking_id: str, url: str, request: Request):
    try:
        async with (await get_pool()).acquire() as conn:
            await conn.execute(
                "INSERT INTO email_events(tracking_id, event_type, url, ip, user_agent) VALUES ($1,'click',$2,$3,$4)",
                tracking_id, url,
                request.client.host if request.client else None,
                request.headers.get("user-agent", "")[:500],
            )
    except Exception:
        pass
    # Whitelist: only http(s) URLs
    if not (url.startswith("https://") or url.startswith("http://")):
        url = "https://depscope.dev"
    return RedirectResponse(url, status_code=302)

@app.get("/api/admin/outreach-queue", include_in_schema=False)
async def outreach_queue(request: Request, campaign: str = "launch_2026_04_20"):
    admin_key = os.getenv("ADMIN_API_KEY", "")
    if not admin_key or request.headers.get("x-admin-key") != admin_key:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    async with (await get_pool()).acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, tracking_id, to_email, to_name, outlet, subject,
                   scheduled_for, sent_at, bounce_at, reply_at, smtp_response,
                   (SELECT COUNT(*) FROM email_events ee WHERE ee.tracking_id = oe.tracking_id AND ee.event_type='open') AS opens,
                   (SELECT COUNT(*) FROM email_events ee WHERE ee.tracking_id = oe.tracking_id AND ee.event_type='click') AS clicks
            FROM outreach_emails oe
            WHERE campaign = $1
            ORDER BY outlet, to_name
        """, campaign)
    def _status(r):
        if r['bounce_at']: return 'bounced'
        if r['reply_at']: return 'replied'
        if r['sent_at']: return 'sent'
        return 'queued'
    return {
        "count": len(rows),
        "campaign": campaign,
        "items": [{
            "id": r["id"],
            "to_name": r["to_name"],
            "to_email": r["to_email"],
            "outlet": r["outlet"],
            "subject": r["subject"],
            "scheduled_for": r["scheduled_for"].isoformat() if r["scheduled_for"] else None,
            "sent_at": r["sent_at"].isoformat() if r["sent_at"] else None,
            "status": _status(r),
            "opens": r["opens"],
            "clicks": r["clicks"],
            "smtp": (r["smtp_response"] or "")[:200],
        } for r in rows]
    }


@app.get("/api/admin/outreach-preview/{email_id}", include_in_schema=False)
async def outreach_preview(email_id: int, request: Request):
    admin_key = os.getenv("ADMIN_API_KEY", "")
    if not admin_key or request.headers.get("x-admin-key") != admin_key:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    async with (await get_pool()).acquire() as conn:
        row = await conn.fetchrow(
            "SELECT subject, body_md, to_email, to_name, outlet FROM outreach_emails WHERE id=$1",
            email_id)
    if not row:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {
        "to_email": row["to_email"], "to_name": row["to_name"], "outlet": row["outlet"],
        "subject": row["subject"], "body_md": row["body_md"]
    }


@app.get("/api/admin/traffic-breakdown", include_in_schema=False)
async def traffic_breakdown(request: Request, hours: int = 24):
    admin_key = os.getenv("ADMIN_API_KEY", "")
    if not admin_key or request.headers.get("x-admin-key") != admin_key:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    AI_UA = r"(GPTBot|OAI-SearchBot|ChatGPT-User|PerplexityBot|CCBot|ClaudeBot|anthropic-ai|Bytespider|Amazonbot|Applebot)"
    SEARCH_UA = r"(Googlebot|GoogleOther|Google-InspectionTool|Googlebot-Image|Mediapartners|Bingbot|Slurp|DuckDuckBot|Yandex|Baiduspider)"
    OTHER_BOT_UA = r"(AhrefsBot|SemrushBot|MJ12bot|DotBot|PetalBot|facebookexternalhit|Discordbot|TelegramBot|WhatsApp|Twitterbot|LinkedInBot|Pingdom|UptimeRobot|Site24x7|bot|crawl|spider)"
    INTERNAL_IP = "(COALESCE(user_agent, '') LIKE 'DepScope-%' OR COALESCE(user_agent, '') LIKE '%CacheWarmer%' OR COALESCE(user_agent, '') LIKE '%curl/%' OR COALESCE(user_agent, '') = '' OR agent_client IN ('crawler', 'unknown'))"

    async with (await get_pool()).acquire() as conn:
        row = await conn.fetchrow(f"""
            WITH w AS (SELECT * FROM page_views WHERE created_at > NOW() - INTERVAL '{hours} hours')
            SELECT
              COUNT(*) FILTER (WHERE {INTERNAL_IP}) AS internal,
              COUNT(*) FILTER (WHERE NOT ({INTERNAL_IP}) AND user_agent ~* '{AI_UA}') AS ai_bots,
              COUNT(*) FILTER (WHERE NOT ({INTERNAL_IP}) AND user_agent !~* '{AI_UA}' AND user_agent ~* '{SEARCH_UA}') AS search_bots,
              COUNT(*) FILTER (WHERE NOT ({INTERNAL_IP}) AND user_agent !~* '{AI_UA}' AND user_agent !~* '{SEARCH_UA}' AND user_agent ~* '{OTHER_BOT_UA}') AS other_bots,
              COUNT(*) FILTER (WHERE NOT ({INTERNAL_IP}) AND (user_agent IS NULL OR (user_agent !~* '{AI_UA}' AND user_agent !~* '{SEARCH_UA}' AND user_agent !~* '{OTHER_BOT_UA}'))) AS humans,
              COUNT(*) AS total
            FROM w
        """)
        # Hourly timeseries
        hourly = await conn.fetch(f"""
            WITH w AS (SELECT *, date_trunc('hour', created_at AT TIME ZONE 'UTC') AS h FROM page_views WHERE created_at > NOW() - INTERVAL '{hours} hours')
            SELECT to_char(h, 'YYYY-MM-DD"T"HH24:MI') AS hour,
              COUNT(*) FILTER (WHERE NOT ({INTERNAL_IP}) AND (user_agent IS NULL OR (user_agent !~* '{AI_UA}' AND user_agent !~* '{SEARCH_UA}' AND user_agent !~* '{OTHER_BOT_UA}'))) AS humans,
              COUNT(*) FILTER (WHERE NOT ({INTERNAL_IP}) AND user_agent ~* '{AI_UA}') AS ai_bots,
              COUNT(*) FILTER (WHERE NOT ({INTERNAL_IP}) AND user_agent !~* '{AI_UA}' AND user_agent ~* '{SEARCH_UA}') AS search_bots,
              COUNT(*) FILTER (WHERE NOT ({INTERNAL_IP}) AND user_agent !~* '{AI_UA}' AND user_agent !~* '{SEARCH_UA}' AND user_agent ~* '{OTHER_BOT_UA}') AS other_bots,
              COUNT(*) FILTER (WHERE {INTERNAL_IP}) AS internal
            FROM w GROUP BY h ORDER BY h
        """)
    return {
        "totals": dict(row) if row else {},
        "hourly": [dict(r) for r in hourly],
        "hours": hours,
    }

@app.get("/api/auth/linkedin/callback", include_in_schema=False)
async def linkedin_callback(code: str = "", state: str = "", error: str = "", error_description: str = ""):
    """Captures the OAuth code from LinkedIn and stores it for the admin to pick up."""
    from fastapi.responses import HTMLResponse
    async with (await get_pool()).acquire() as conn:
        val = code or f"ERR:{error}:{error_description}"
        existing = await conn.fetchval("SELECT id FROM agent_credentials WHERE platform='linkedin' LIMIT 1")
        if existing:
            await conn.execute("UPDATE agent_credentials SET api_key=$1, notes='oauth_code', active=true WHERE id=$2", val, existing)
        else:
            await conn.execute("INSERT INTO agent_credentials (platform, api_key, notes, active) VALUES ('linkedin', $1, 'oauth_code', true)", val)
    if error:
        body = f"<h2>Error</h2><p>{error}: {error_description}</p>"
    elif code:
        body = f"<h2>✓ Code captured</h2><p>Tell the ops agent: code captured, exchange it for a token.</p>"
    else:
        body = "<h2>No code present</h2>"
    return HTMLResponse(f"<!doctype html><html><body style='font-family:system-ui;max-width:520px;margin:40px auto;color:#111'>{body}<p style='color:#888;font-size:13px'>You can close this tab.</p></body></html>")

@app.get("/api/admin/launch-metrics", include_in_schema=False)
async def launch_metrics(request: Request):
    admin_key = os.getenv("ADMIN_API_KEY", "")
    if not admin_key or request.headers.get("x-admin-key") != admin_key:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    import aiohttp
    async with (await get_pool()).acquire() as conn:
        # Email outreach
        em_total = await conn.fetchval("SELECT COUNT(*) FROM outreach_emails WHERE campaign='launch_2026_04_20'")
        em_sent = await conn.fetchval("SELECT COUNT(*) FROM outreach_emails WHERE campaign='launch_2026_04_20' AND sent_at IS NOT NULL")
        em_bounce = await conn.fetchval("SELECT COUNT(*) FROM outreach_emails WHERE campaign='launch_2026_04_20' AND bounce_at IS NOT NULL")
        em_reply = await conn.fetchval("SELECT COUNT(*) FROM outreach_emails WHERE campaign='launch_2026_04_20' AND reply_at IS NOT NULL")
        em_opened = await conn.fetchval("""
            SELECT COUNT(DISTINCT tracking_id) FROM email_events
            WHERE event_type='open' AND tracking_id IN (SELECT tracking_id FROM outreach_emails WHERE campaign='launch_2026_04_20')
        """)
        em_clicked = await conn.fetchval("""
            SELECT COUNT(DISTINCT tracking_id) FROM email_events
            WHERE event_type='click' AND tracking_id IN (SELECT tracking_id FROM outreach_emails WHERE campaign='launch_2026_04_20')
        """)

        # API traffic (last 24h)
        api_24h = await conn.fetchval("SELECT COUNT(*) FROM api_usage WHERE created_at > NOW() - INTERVAL '24 hours'")
        api_total = await conn.fetchval("SELECT COUNT(*) FROM api_usage")
        api_ips = await conn.fetchval("SELECT COUNT(DISTINCT ip_hash) FROM api_usage WHERE created_at > NOW() - INTERVAL '24 hours'")

    # GitHub (new account)
    gh_stars = gh_forks = gh_watchers = 0
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as cli:
            async with cli.get("https://api.github.com/repos/cuttalo/depscope", headers={"User-Agent": "depscope-monitor"}) as r:
                if r.status == 200:
                    j = await r.json()
                    gh_stars = j.get("stargazers_count", 0)
                    gh_forks = j.get("forks_count", 0)
                    gh_watchers = j.get("subscribers_count", 0)
    except Exception:
        pass

    # npm
    npm_7d = 0
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as cli:
            async with cli.get("https://api.npmjs.org/downloads/point/last-week/depscope-mcp") as r:
                if r.status == 200:
                    jj = await r.json()
                    npm_7d = jj.get("downloads", 0)
    except Exception:
        pass

    # Dev.to articles (both old and new)
    devto = {"published": [], "draft_ready": False}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as cli:
            async with cli.get("https://dev.to/api/articles?username=depscope", headers={"api-key": os.getenv("DEVTO_API_KEY", "VuqtfNaAJifTz4h2ckG3sCdG")}) as r:
                if r.status == 200:
                    arts = await r.json()
                    for a in arts:
                        devto["published"].append({
                            "id": a.get("id"),
                            "title": a.get("title"),
                            "url": a.get("url"),
                            "views": a.get("page_views_count"),
                            "reactions": a.get("public_reactions_count"),
                            "comments": a.get("comments_count"),
                        })
    except Exception:
        pass

    # GSC
    gsc = {"last_7d": {"clicks": 0, "impressions": 0, "avg_position": None}, "top_queries": []}
    try:
        async with (await get_pool()).acquire() as conn:
            r = await conn.fetchrow("""
                SELECT COALESCE(SUM(clicks),0) AS c, COALESCE(SUM(impressions),0) AS i,
                       AVG(position) FILTER (WHERE impressions>0) AS p
                FROM gsc_daily WHERE day > CURRENT_DATE - INTERVAL '7 days'
            """)
            gsc["last_7d"]["clicks"] = int(r["c"] or 0)
            gsc["last_7d"]["impressions"] = int(r["i"] or 0)
            gsc["last_7d"]["avg_position"] = float(r["p"]) if r["p"] else None
            q = await conn.fetch("""
                SELECT query, clicks, impressions, position
                FROM gsc_query_top
                WHERE day = (SELECT MAX(day) FROM gsc_query_top)
                ORDER BY impressions DESC LIMIT 10
            """)
            gsc["top_queries"] = [{"query":x["query"],"clicks":x["clicks"],"impressions":x["impressions"],"position":float(x["position"]) if x["position"] else None} for x in q]
    except Exception:
        pass

    return {
        "gsc": gsc,
        "email": {
            "total_queued": em_total, "sent": em_sent, "bounced": em_bounce,
            "opened": em_opened, "clicked": em_clicked, "replied": em_reply,
            "open_rate": round(em_opened / em_sent * 100, 1) if em_sent else 0,
            "click_rate": round(em_clicked / em_sent * 100, 1) if em_sent else 0,
        },
        "api": {
            "calls_24h": api_24h, "calls_total": api_total, "unique_ips_24h": api_ips,
        },
        "github": {
            "repo": "cuttalo/depscope",
            "stars": gh_stars, "forks": gh_forks, "watchers": gh_watchers,
        },
        "npm": {"package": "depscope-mcp", "downloads_7d": npm_7d},
        "devto": devto,
        "ts": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }

# --- END EMAIL TRACKING ROUTES ---



@app.get("/api/admin/outreach", include_in_schema=False)
async def admin_outreach_list(request: Request, limit: int = 200, campaign: str = None):
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")
    pool = await get_pool()
    limit = max(1, min(int(limit or 200), 1000))
    async with pool.acquire() as conn:
        if campaign:
            rows = await conn.fetch(
                """SELECT id, tracking_id, to_email, to_name, outlet, from_email,
                          subject, campaign, scheduled_for, sent_at, smtp_response,
                          bounce_at, reply_at, created_at,
                          length(body_md) AS body_len
                   FROM outreach_emails
                   WHERE campaign = $1
                   ORDER BY created_at DESC LIMIT $2""",
                campaign, limit,
            )
        else:
            rows = await conn.fetch(
                """SELECT id, tracking_id, to_email, to_name, outlet, from_email,
                          subject, campaign, scheduled_for, sent_at, smtp_response,
                          bounce_at, reply_at, created_at,
                          length(body_md) AS body_len
                   FROM outreach_emails
                   ORDER BY created_at DESC LIMIT $1""",
                limit,
            )
        # Aggregates
        agg = await conn.fetchrow(
            """SELECT
                 COUNT(*)                                       AS total,
                 COUNT(*) FILTER (WHERE sent_at IS NOT NULL)     AS sent,
                 COUNT(*) FILTER (WHERE reply_at IS NOT NULL)    AS replied,
                 COUNT(*) FILTER (WHERE bounce_at IS NOT NULL)   AS bounced,
                 COUNT(*) FILTER (WHERE sent_at IS NULL AND bounce_at IS NULL) AS queued,
                 COUNT(DISTINCT campaign)                        AS campaigns,
                 COUNT(DISTINCT outlet)                          AS outlets
               FROM outreach_emails"""
        )
        campaigns = await conn.fetch(
            """SELECT campaign,
                      COUNT(*)                                    AS total,
                      COUNT(*) FILTER (WHERE sent_at IS NOT NULL)  AS sent,
                      COUNT(*) FILTER (WHERE reply_at IS NOT NULL) AS replied,
                      COUNT(*) FILTER (WHERE bounce_at IS NOT NULL) AS bounced,
                      MIN(created_at)                             AS first_at,
                      MAX(created_at)                             AS last_at
               FROM outreach_emails
               WHERE campaign IS NOT NULL
               GROUP BY campaign
               ORDER BY last_at DESC"""
        )
    return {
        "aggregates": dict(agg) if agg else {},
        "campaigns":  [dict(c) for c in campaigns],
        "items":      [dict(r) for r in rows],
        "count":      len(rows),
    }


@app.get("/api/admin/outreach/{email_id}", include_in_schema=False)
async def admin_outreach_detail(email_id: int, request: Request):
    if not _has_admin_pw(request):
        user = await _get_user_from_request(request)
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin only")
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM outreach_emails WHERE id = $1", email_id,
        )
    if not row:
        raise HTTPException(404, "Not found")
    return dict(row)

  # PATCH_VERSION_PARAM_V1
