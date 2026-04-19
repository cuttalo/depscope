"""DepScope MCP Streamable HTTP endpoint — JSON-RPC 2.0 over HTTP POST.

Exposes POST /mcp and GET /mcp. Bridges MCP tool calls to the existing
DepScope REST API. No state, no sessions, just request/response.
"""
import json
import aiohttp
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from api.config import VERSION

mcp_router = APIRouter()

MCP_PROTOCOL_VERSION = "2025-06-18"
MCP_SERVER_NAME = "depscope"
MCP_SERVER_VERSION = VERSION
API_BASE = "http://127.0.0.1:8000"

ECOSYSTEMS = [
    "npm", "pypi", "cargo", "go", "composer", "maven", "nuget",
    "rubygems", "pub", "hex", "swift", "cocoapods", "cpan",
    "hackage", "cran", "conda", "homebrew",
]

TOOLS = [
    {
        "name": "check_package",
        "description": (
            "Full health check for a package: score, vulnerabilities, latest version, "
            "deprecation status, dependencies and a use/avoid recommendation. "
            "Call this BEFORE suggesting any package install."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ecosystem": {"type": "string", "enum": ECOSYSTEMS, "description": "Package ecosystem"},
                "package": {"type": "string", "description": "Package name (e.g. 'express', 'fastapi', 'serde')"},
                "version": {"type": "string", "description": "Specific version to check (optional, defaults to latest)"},
            },
            "required": ["ecosystem", "package"],
        },
    },
    {
        "name": "get_health_score",
        "description": "Return just the health score (0-100) for a package. Fast quick-check.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ecosystem": {"type": "string", "enum": ECOSYSTEMS},
                "package": {"type": "string"},
            },
            "required": ["ecosystem", "package"],
        },
    },
    {
        "name": "get_vulnerabilities",
        "description": "List known vulnerabilities affecting the latest version of a package.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ecosystem": {"type": "string", "enum": ECOSYSTEMS},
                "package": {"type": "string"},
            },
            "required": ["ecosystem", "package"],
        },
    },
    {
        "name": "get_latest_version",
        "description": "Return just the latest version string for a package. Fastest response.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ecosystem": {"type": "string", "enum": ECOSYSTEMS},
                "package": {"type": "string"},
            },
            "required": ["ecosystem", "package"],
        },
    },
    {
        "name": "package_exists",
        "description": "Does this package exist in the given ecosystem? Use before suggesting installs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ecosystem": {"type": "string", "enum": ECOSYSTEMS},
                "package": {"type": "string"},
            },
            "required": ["ecosystem", "package"],
        },
    },
    {
        "name": "search_packages",
        "description": "Search packages by keyword. Avoids hallucinated package names.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ecosystem": {"type": "string", "enum": ECOSYSTEMS},
                "query": {"type": "string", "description": "Search keyword"},
                "limit": {"type": "integer", "description": "Max results (default 10, max 30)", "default": 10},
            },
            "required": ["ecosystem", "query"],
        },
    },
    {
        "name": "compare_packages",
        "description": "Compare 2-5 packages side by side on health, vulns, downloads and recommendation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ecosystem": {"type": "string", "enum": ECOSYSTEMS},
                "packages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 5,
                    "description": "List of package names to compare",
                },
            },
            "required": ["ecosystem", "packages"],
        },
    },
    {
        "name": "find_alternatives",
        "description": "Get maintained alternatives for a deprecated or unhealthy package.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ecosystem": {"type": "string", "enum": ECOSYSTEMS},
                "package": {"type": "string"},
            },
            "required": ["ecosystem", "package"],
        },
    },
    {
        "name": "current_time",
        "description": "Current UTC time with day of week and unix timestamp. Agents often don't know what day it is.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "resolve_error",
        "description": (
            "Match a stack trace or error message against DepScope's error "
            "database and return a step-by-step fix. Use this whenever you "
            "see an unfamiliar runtime error before guessing a solution."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "error_text": {"type": "string", "description": "Raw error / stack trace"},
                "context": {
                    "type": "object",
                    "description": "Optional context: ecosystem, package, version",
                    "properties": {
                        "ecosystem": {"type": "string"},
                        "package": {"type": "string"},
                        "version": {"type": "string"},
                    },
                },
            },
            "required": ["error_text"],
        },
    },
    {
        "name": "check_compat",
        "description": (
            "Check whether a combination of packages is known to work together "
            "(e.g. Next.js 16 + React 19 + Prisma 6). Returns verified / broken "
            "/ untested plus notes and sources."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "stack": {
                    "type": "object",
                    "description": "Map of package name -> version, e.g. {\"next\":\"16\",\"react\":\"19\"}",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["stack"],
        },
    },
    {
        "name": "get_bugs",
        "description": (
            "List known non-CVE bugs for a package (optionally filtered by "
            "version). Complements get_vulnerabilities for regressions, "
            "performance issues and behavioural bugs."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ecosystem": {"type": "string", "enum": ECOSYSTEMS},
                "package": {"type": "string"},
                "version": {"type": "string", "description": "Optional version to filter"},
            },
            "required": ["ecosystem", "package"],
        },
    },
    {
        "name": "get_breaking_changes",
        "description": (
            "Verified breaking changes between two major versions of a package, "
            "with migration hints (codemod commands, config diffs). Covers React, "
            "Next.js, Prisma, Express, Node, TypeScript, ESLint, Tailwind, Vite, "
            "Pydantic, SQLAlchemy, Django, Python, Rust edition, and more. "
            "Call BEFORE suggesting a major-version bump."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ecosystem": {"type": "string", "enum": ECOSYSTEMS},
                "package": {"type": "string"},
                "from_version": {"type": "string", "description": "Optional: starting major (e.g. '18', '14', '1')."},
                "to_version": {"type": "string", "description": "Optional: target major (e.g. '19', '15', '2')."},
            },
            "required": ["ecosystem", "package"],
        },
    },
    {
        "name": "search_errors",
        "description": (
            "Free-text search across the error-fix knowledge base. Use when you "
            "want to explore what errors we have fixes for around a topic "
            "(e.g. 'CORS', 'prisma', 'hydration')."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
            },
            "required": ["query"],
        },
    },
]


def _jsonrpc_error(req_id, code: int, message: str, data=None):
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


def _jsonrpc_result(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _tool_text_result(req_id, payload, is_error: bool = False):
    text = json.dumps(payload, indent=2, default=str) if not isinstance(payload, str) else payload
    result = {"content": [{"type": "text", "text": text}]}
    if is_error:
        result["isError"] = True
    return _jsonrpc_result(req_id, result)


async def _http_get(session: aiohttp.ClientSession, path: str):
    async with session.get(f"{API_BASE}{path}", timeout=aiohttp.ClientTimeout(total=30)) as resp:
        status = resp.status
        try:
            data = await resp.json()
        except Exception:
            data = {"error": await resp.text()}
        return status, data


async def _http_post(session: aiohttp.ClientSession, path: str, payload: dict):
    async with session.post(
        f"{API_BASE}{path}",
        json=payload,
        timeout=aiohttp.ClientTimeout(total=30),
    ) as resp:
        status = resp.status
        try:
            data = await resp.json()
        except Exception:
            data = {"error": await resp.text()}
        return status, data


async def _call_tool(name: str, args: dict, req_id):
    if name == "current_time":
        now = datetime.now(timezone.utc)
        return _tool_text_result(req_id, {
            "utc": now.isoformat(),
            "unix": int(now.timestamp()),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day": now.strftime("%A"),
            "timezone": "UTC",
        })

    # Verticals that don't need package+ecosystem in args
    if name == "resolve_error":
        error_text = (args or {}).get("error_text", "")
        if not error_text:
            return _tool_text_result(req_id, {"error": "Missing required argument: error_text"}, is_error=True)
        ctx = (args or {}).get("context") or {}
        async with aiohttp.ClientSession() as session:
            status, data = await _http_post(
                session,
                "/api/error/resolve",
                {"error": error_text, "context": ctx},
            )
        if status >= 400:
            return _tool_text_result(req_id, data, is_error=True)
        return _tool_text_result(req_id, data)

    if name == "check_compat":
        stack = (args or {}).get("stack") or {}
        if not isinstance(stack, dict) or not stack:
            return _tool_text_result(req_id, {"error": "'stack' must be a non-empty object"}, is_error=True)
        async with aiohttp.ClientSession() as session:
            status, data = await _http_post(session, "/api/compat", {"packages": stack})
        if status >= 400:
            return _tool_text_result(req_id, data, is_error=True)
        return _tool_text_result(req_id, data)

    if name == "get_bugs":
        eco = (args or {}).get("ecosystem", "").lower()
        pkg = (args or {}).get("package", "")
        if not eco or not pkg:
            return _tool_text_result(req_id, {"error": "Missing required arguments: ecosystem, package"}, is_error=True)
        if eco not in ECOSYSTEMS:
            return _tool_text_result(req_id, {"error": f"Unsupported ecosystem '{eco}'. Allowed: {ECOSYSTEMS}"}, is_error=True)
        version = (args or {}).get("version")
        path = f"/api/bugs/{eco}/{pkg}"
        if version:
            path += f"?version={version}"
        async with aiohttp.ClientSession() as session:
            status, data = await _http_get(session, path)
        if status >= 400:
            return _tool_text_result(req_id, data, is_error=True)
        return _tool_text_result(req_id, data)

    if name == "get_breaking_changes":
        eco = (args or {}).get("ecosystem", "").lower()
        pkg = (args or {}).get("package", "")
        if not eco or not pkg:
            return _tool_text_result(req_id, {"error": "Missing required arguments: ecosystem, package"}, is_error=True)
        if eco not in ECOSYSTEMS:
            return _tool_text_result(req_id, {"error": f"Unsupported ecosystem '{eco}'. Allowed: {ECOSYSTEMS}"}, is_error=True)
        from_v = (args or {}).get("from_version")
        to_v = (args or {}).get("to_version")
        qs = []
        if from_v:
            qs.append(f"from_version={from_v}")
        if to_v:
            qs.append(f"to_version={to_v}")
        suffix = ("?" + "&".join(qs)) if qs else ""
        path = f"/api/breaking/{eco}/{pkg}{suffix}"
        async with aiohttp.ClientSession() as session:
            status, data = await _http_get(session, path)
        if status >= 400:
            return _tool_text_result(req_id, data, is_error=True)
        return _tool_text_result(req_id, data)

    if name == "search_errors":
        query = (args or {}).get("query", "")
        if not query:
            return _tool_text_result(req_id, {"error": "Missing required argument: query"}, is_error=True)
        limit = (args or {}).get("limit", 10)
        try:
            limit = max(1, min(int(limit), 20))
        except Exception:
            limit = 10
        path = f"/api/error?q={query}&limit={limit}"
        async with aiohttp.ClientSession() as session:
            status, data = await _http_get(session, path)
        if status >= 400:
            return _tool_text_result(req_id, data, is_error=True)
        return _tool_text_result(req_id, data)

    ecosystem = (args or {}).get("ecosystem", "").lower()
    if name not in ("search_packages", "compare_packages", "current_time"):
        package = (args or {}).get("package", "")
        if not ecosystem or not package:
            return _tool_text_result(req_id, {"error": "Missing required arguments: ecosystem, package"}, is_error=True)
    if name in ("check_package", "get_health_score", "get_vulnerabilities",
                 "get_latest_version", "package_exists", "find_alternatives",
                 "search_packages", "compare_packages") and ecosystem not in ECOSYSTEMS:
        return _tool_text_result(req_id, {"error": f"Unsupported ecosystem '{ecosystem}'. Allowed: {ECOSYSTEMS}"}, is_error=True)

    async with aiohttp.ClientSession() as session:
        if name == "check_package":
            path = f"/api/check/{ecosystem}/{args['package']}"
            version = args.get("version")
            if version:
                path += f"?version={version}"
            status, data = await _http_get(session, path)
        elif name == "get_health_score":
            status, data = await _http_get(session, f"/api/health/{ecosystem}/{args['package']}")
        elif name == "get_vulnerabilities":
            status, data = await _http_get(session, f"/api/vulns/{ecosystem}/{args['package']}")
        elif name == "get_latest_version":
            status, data = await _http_get(session, f"/api/latest/{ecosystem}/{args['package']}")
        elif name == "package_exists":
            status, data = await _http_get(session, f"/api/exists/{ecosystem}/{args['package']}")
        elif name == "find_alternatives":
            status, data = await _http_get(session, f"/api/alternatives/{ecosystem}/{args['package']}")
        elif name == "search_packages":
            query = args.get("query", "")
            limit = args.get("limit", 10)
            if not query:
                return _tool_text_result(req_id, {"error": "Missing required argument: query"}, is_error=True)
            status, data = await _http_get(session, f"/api/search/{ecosystem}?q={query}&limit={limit}")
        elif name == "compare_packages":
            pkgs = args.get("packages") or []
            if not isinstance(pkgs, list) or len(pkgs) < 2:
                return _tool_text_result(req_id, {"error": "'packages' must be an array of at least 2 names"}, is_error=True)
            if len(pkgs) > 5:
                return _tool_text_result(req_id, {"error": "Max 5 packages per comparison"}, is_error=True)
            csv = ",".join(pkgs)
            status, data = await _http_get(session, f"/api/compare/{ecosystem}/{csv}")
        else:
            return _jsonrpc_error(req_id, -32601, f"Unknown tool: {name}")

    if status >= 400:
        return _tool_text_result(req_id, data, is_error=True)
    return _tool_text_result(req_id, data)


async def _dispatch(message: dict):
    req_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}

    if method == "initialize":
        return _jsonrpc_result(req_id, {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": MCP_SERVER_NAME, "version": MCP_SERVER_VERSION},
        })
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return _jsonrpc_result(req_id, {})
    if method == "tools/list":
        return _jsonrpc_result(req_id, {"tools": TOOLS})
    if method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments") or {}
        if not tool_name:
            return _jsonrpc_error(req_id, -32602, "Missing tool name")
        try:
            return await _call_tool(tool_name, tool_args, req_id)
        except Exception as e:
            return _tool_text_result(req_id, {"error": str(e)}, is_error=True)
    return _jsonrpc_error(req_id, -32601, f"Method not found: {method}")


@mcp_router.get("/mcp", tags=["mcp"])
async def mcp_info():
    return {
        "name": MCP_SERVER_NAME,
        "version": MCP_SERVER_VERSION,
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "transport": "streamable-http",
        "endpoint": "/mcp",
        "methods": ["initialize", "tools/list", "tools/call", "ping"],
        "tools": [t["name"] for t in TOOLS],
    }


@mcp_router.post("/mcp", tags=["mcp"])
async def mcp_endpoint(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "id": None,
                     "error": {"code": -32700, "message": "Parse error"}},
        )

    if isinstance(body, list):
        responses = []
        for msg in body:
            r = await _dispatch(msg)
            if r is not None:
                responses.append(r)
        if not responses:
            return JSONResponse(status_code=202, content=None)
        return JSONResponse(content=responses)

    if not isinstance(body, dict):
        return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "id": None,
                     "error": {"code": -32600, "message": "Invalid Request"}},
        )

    response = await _dispatch(body)
    if response is None:
        return JSONResponse(status_code=202, content=None)
    return JSONResponse(content=response)
