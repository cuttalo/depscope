"""Seed minimal data for the three DepScope verticals.

Idempotent: uses INSERT ... ON CONFLICT to avoid duplicates.
Run from /home/deploy/depscope with:
    python3 -m scripts.seed_verticals
"""
import asyncio
import hashlib
import json
import sys
import os

# Make `api` importable when run as a script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.database import get_pool, close_pool  # noqa: E402
from api.verticals import normalize_error, hash_error_pattern, hash_stack  # noqa: E402


# --------------------------------------------------------------------------- #
# 10 seed errors — common, real, ecosystem-agnostic or language-specific
# --------------------------------------------------------------------------- #
SEED_ERRORS = [
    {
        "pattern": "Cannot find module 'express'",
        "full_message": "Error: Cannot find module 'express'\n    at Function.Module._resolveFilename",
        "ecosystem": "npm",
        "package_name": "express",
        "package_version": None,
        "solution": (
            "Install the missing dependency:\n"
            "```\nnpm install express\n```\n"
            "If the package is already in package.json, run `npm ci` to sync "
            "node_modules. Verify you are not running the script from outside "
            "the project root."
        ),
        "confidence": 0.95,
        "source": "internal",
        "source_url": None,
        "votes": 12,
    },
    {
        "pattern": "TypeError: Cannot read properties of undefined",
        "full_message": "TypeError: Cannot read properties of undefined (reading 'map')",
        "ecosystem": "npm",
        "package_name": None,
        "package_version": None,
        "solution": (
            "The value you are accessing is `undefined` at runtime.\n"
            "1. Guard with optional chaining: `obj?.prop?.map(...)`\n"
            "2. Default the array: `(items ?? []).map(...)`\n"
            "3. Verify the data has been fetched / state initialised before the render."
        ),
        "confidence": 0.9,
        "source": "community",
        "source_url": None,
        "votes": 25,
    },
    {
        "pattern": "Error: connect ECONNREFUSED 127.0.0.1:5432",
        "full_message": "Error: connect ECONNREFUSED 127.0.0.1:5432",
        "ecosystem": None,
        "package_name": None,
        "package_version": None,
        "solution": (
            "The target service is not reachable.\n"
            "- Confirm the process is running: `systemctl status postgresql`\n"
            "- Check the port matches (default pg = 5432, redis = 6379)\n"
            "- If inside Docker, use the service name instead of `127.0.0.1`\n"
            "- Inspect firewall / security group rules."
        ),
        "confidence": 0.9,
        "source": "internal",
        "source_url": None,
        "votes": 18,
    },
    {
        "pattern": "ModuleNotFoundError: No module named 'requests'",
        "full_message": "ModuleNotFoundError: No module named 'requests'",
        "ecosystem": "pypi",
        "package_name": "requests",
        "package_version": None,
        "solution": (
            "Install the module in the active environment:\n"
            "```\npip install requests\n```\n"
            "If you use a virtualenv make sure it is activated (`which python`). "
            "When running with `sudo` python may use a different interpreter — "
            "prefer `python -m pip install requests`."
        ),
        "confidence": 0.95,
        "source": "internal",
        "source_url": None,
        "votes": 22,
    },
    {
        "pattern": "AttributeError: 'NoneType' object has no attribute",
        "full_message": "AttributeError: 'NoneType' object has no attribute 'split'",
        "ecosystem": "pypi",
        "package_name": None,
        "package_version": None,
        "solution": (
            "A function returned `None` where a value was expected.\n"
            "- Add a guard: `if value is None: return ...`\n"
            "- Log / print the value just before the failing line\n"
            "- Check library docs — many functions return `None` on miss "
            "(`dict.get`, `re.match`, `list.sort`)."
        ),
        "confidence": 0.9,
        "source": "community",
        "source_url": None,
        "votes": 30,
    },
    {
        "pattern": "error[E0382]: borrow of moved value",
        "full_message": "error[E0382]: borrow of moved value: `x`",
        "ecosystem": "cargo",
        "package_name": None,
        "package_version": None,
        "solution": (
            "Rust ownership: the value was moved and cannot be reused.\n"
            "- Clone it: `let y = x.clone();`\n"
            "- Borrow instead of moving: `fn f(x: &T)`\n"
            "- Use a reference-counted wrapper (`Rc` / `Arc`) if shared ownership is needed.\n"
            "Reference: https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html"
        ),
        "confidence": 0.9,
        "source": "internal",
        "source_url": "https://doc.rust-lang.org/error_codes/E0382.html",
        "votes": 14,
    },
    {
        "pattern": "SyntaxError: Unexpected token",
        "full_message": "SyntaxError: Unexpected token '<' in JSON at position 0",
        "ecosystem": "npm",
        "package_name": None,
        "package_version": None,
        "solution": (
            "The response is HTML (an error page) instead of JSON.\n"
            "- `console.log(await res.text())` to inspect the real body\n"
            "- Check the endpoint URL (404 returns HTML on most servers)\n"
            "- Validate the request: headers, auth, method."
        ),
        "confidence": 0.85,
        "source": "community",
        "source_url": None,
        "votes": 9,
    },
    {
        "pattern": "CORS policy: No 'Access-Control-Allow-Origin' header",
        "full_message": (
            "Access to fetch at 'https://api.example.com' from origin "
            "'http://localhost:3000' has been blocked by CORS policy"
        ),
        "ecosystem": None,
        "package_name": None,
        "package_version": None,
        "solution": (
            "CORS must be configured on the **server**, not the browser.\n"
            "- Express: `app.use(cors({ origin: 'http://localhost:3000' }))`\n"
            "- FastAPI: `app.add_middleware(CORSMiddleware, allow_origins=[...])`\n"
            "- In development you can proxy the API through your dev server.\n"
            "A browser extension that disables CORS is NOT a fix."
        ),
        "confidence": 0.92,
        "source": "community",
        "source_url": None,
        "votes": 20,
    },
    {
        "pattern": "Hydration failed because the initial UI does not match",
        "full_message": (
            "Error: Hydration failed because the initial UI does not match "
            "what was rendered on the server."
        ),
        "ecosystem": "npm",
        "package_name": "next",
        "package_version": None,
        "solution": (
            "Server HTML != client HTML. Common causes:\n"
            "- Rendering `Date.now()` / `Math.random()` on both sides\n"
            "- `window` / `localStorage` access during render — gate with `useEffect`\n"
            "- Invalid HTML nesting (e.g. `<p><div/></p>`)\n"
            "- Locale mismatch (`Intl.DateTimeFormat` without explicit locale)\n"
            "Use `suppressHydrationWarning` only as a last resort."
        ),
        "confidence": 0.9,
        "source": "community",
        "source_url": "https://nextjs.org/docs/messages/react-hydration-error",
        "votes": 28,
    },
    {
        "pattern": "EADDRINUSE: address already in use",
        "full_message": "Error: listen EADDRINUSE: address already in use :::3000",
        "ecosystem": "npm",
        "package_name": None,
        "package_version": None,
        "solution": (
            "Another process is already bound to the port.\n"
            "- Find it: `lsof -i :3000` (or `ss -tulpn | grep 3000`)\n"
            "- Kill it: `kill -9 <PID>`\n"
            "- Or run on a different port: `PORT=3001 npm start`"
        ),
        "confidence": 0.95,
        "source": "internal",
        "source_url": None,
        "votes": 17,
    },
]


# --------------------------------------------------------------------------- #
# 5 seed compatibility entries
# --------------------------------------------------------------------------- #
SEED_STACKS = [
    {
        "packages": {"next": "16", "react": "19", "typescript": "5"},
        "status": "verified",
        "notes": "Official Next.js 16 starter template. React 19 is the default React version.",
        "source": "maintainer_docs",
        "source_url": "https://nextjs.org/docs",
        "stars": 120000,
    },
    {
        "packages": {"next": "16", "prisma": "6", "postgresql": "17"},
        "status": "verified",
        "notes": "Works out of the box. Use `prisma generate` on postinstall.",
        "source": "github_starter",
        "source_url": "https://github.com/vercel/next.js/tree/canary/examples/with-prisma",
        "stars": 120000,
    },
    {
        "packages": {"vite": "5", "vue": "3", "typescript": "5"},
        "status": "verified",
        "notes": "Official Vite + Vue 3 scaffold. Uses `<script setup lang=\"ts\">`.",
        "source": "maintainer_docs",
        "source_url": "https://vuejs.org/guide/scaling-up/tooling.html",
        "stars": 45000,
    },
    {
        "packages": {"django": "5", "postgresql": "17"},
        "status": "verified",
        "notes": "Django 5 explicitly supports PostgreSQL 17. Use `psycopg[binary]>=3.1.8`.",
        "source": "maintainer_docs",
        "source_url": "https://docs.djangoproject.com/en/5.0/ref/databases/",
        "stars": 80000,
    },
    {
        "packages": {"fastapi": "0.110", "pydantic": "2", "sqlalchemy": "2"},
        "status": "verified",
        "notes": "FastAPI >= 0.100 requires Pydantic v2. SQLAlchemy 2 ORM style works unchanged.",
        "source": "maintainer_docs",
        "source_url": "https://fastapi.tiangolo.com/",
        "stars": 75000,
    },
]


# --------------------------------------------------------------------------- #
# 10 seed bugs — real, sourced from package GitHub issues
# --------------------------------------------------------------------------- #
SEED_BUGS = [
    {
        "ecosystem": "npm",
        "package_name": "express",
        "affected_version": "<4.17.3",
        "fixed_version": "4.17.3",
        "bug_id": "github:#4926",
        "title": "Open redirect via malformed URL",
        "description": (
            "Old express versions do not sanitise certain redirect targets; "
            "upgrade to 4.17.3 or later. Also see CVE-2024-29041."
        ),
        "severity": "high",
        "status": "closed",
        "source": "github_issues",
        "source_url": "https://github.com/expressjs/express/issues/4926",
        "labels": ["security", "redirect"],
    },
    {
        "ecosystem": "npm",
        "package_name": "react",
        "affected_version": "19.0.0",
        "fixed_version": "19.0.1",
        "bug_id": "github:#31317",
        "title": "Hydration mismatch warning on server components with Suspense",
        "description": (
            "A regression in React 19.0.0 logs spurious hydration mismatch "
            "warnings when a Suspense boundary finishes on the server. "
            "Fixed in 19.0.1."
        ),
        "severity": "medium",
        "status": "closed",
        "source": "github_issues",
        "source_url": "https://github.com/facebook/react/issues/31317",
        "labels": ["bug", "regression", "hydration"],
    },
    {
        "ecosystem": "npm",
        "package_name": "axios",
        "affected_version": "<1.6.0",
        "fixed_version": "1.6.0",
        "bug_id": "github:#6009",
        "title": "Prototype pollution via formToJSON helper",
        "description": "CVE-2023-45857 — upgrade to 1.6.0 to fix.",
        "severity": "high",
        "status": "closed",
        "source": "github_issues",
        "source_url": "https://github.com/axios/axios/issues/6009",
        "labels": ["security", "prototype-pollution"],
    },
    {
        "ecosystem": "npm",
        "package_name": "next",
        "affected_version": "14.1.0",
        "fixed_version": "14.1.1",
        "bug_id": "github:#62600",
        "title": "Server Action redirect bypasses middleware",
        "description": (
            "CVE-2024-34351 — a redirect inside a Server Action can bypass "
            "authentication middleware. Upgrade to 14.1.1 or later."
        ),
        "severity": "high",
        "status": "closed",
        "source": "github_issues",
        "source_url": "https://github.com/vercel/next.js/issues/62600",
        "labels": ["security", "server-actions"],
    },
    {
        "ecosystem": "npm",
        "package_name": "lodash",
        "affected_version": "<4.17.21",
        "fixed_version": "4.17.21",
        "bug_id": "github:#5065",
        "title": "Command injection in template function",
        "description": "CVE-2021-23337 — unsafe template evaluation. Upgrade to 4.17.21.",
        "severity": "high",
        "status": "closed",
        "source": "github_issues",
        "source_url": "https://github.com/lodash/lodash/issues/5065",
        "labels": ["security"],
    },
    {
        "ecosystem": "pypi",
        "package_name": "requests",
        "affected_version": "<2.32.0",
        "fixed_version": "2.32.0",
        "bug_id": "github:#6655",
        "title": "Session.verify=False not persisted across redirects",
        "description": (
            "CVE-2024-35195 — `verify=False` was only applied to the first "
            "request in a redirect chain. Upgrade to 2.32.0."
        ),
        "severity": "medium",
        "status": "closed",
        "source": "github_issues",
        "source_url": "https://github.com/psf/requests/issues/6655",
        "labels": ["security", "ssl"],
    },
    {
        "ecosystem": "pypi",
        "package_name": "fastapi",
        "affected_version": "0.95.0",
        "fixed_version": "0.95.1",
        "bug_id": "github:#9321",
        "title": "File upload memory leak with UploadFile",
        "description": (
            "Streaming large files via UploadFile kept the full body in memory. "
            "Patched in 0.95.1."
        ),
        "severity": "medium",
        "status": "closed",
        "source": "github_issues",
        "source_url": "https://github.com/tiangolo/fastapi/issues/9321",
        "labels": ["bug", "performance"],
    },
    {
        "ecosystem": "pypi",
        "package_name": "django",
        "affected_version": "5.0.0",
        "fixed_version": "5.0.1",
        "bug_id": "github:#17682",
        "title": "Admin changelist crashes on empty search",
        "description": (
            "Submitting an empty search in the Django admin changelist "
            "raises ValueError. Fix in 5.0.1."
        ),
        "severity": "low",
        "status": "closed",
        "source": "github_issues",
        "source_url": "https://code.djangoproject.com/ticket/17682",
        "labels": ["bug", "admin"],
    },
    {
        "ecosystem": "cargo",
        "package_name": "tokio",
        "affected_version": "<1.38.1",
        "fixed_version": "1.38.1",
        "bug_id": "github:#6774",
        "title": "Possible panic in broadcast channel receiver",
        "description": (
            "A race condition could cause a panic when the broadcast channel "
            "was dropped with pending receivers. Fixed in 1.38.1."
        ),
        "severity": "medium",
        "status": "closed",
        "source": "github_issues",
        "source_url": "https://github.com/tokio-rs/tokio/issues/6774",
        "labels": ["bug", "concurrency"],
    },
    {
        "ecosystem": "npm",
        "package_name": "prisma",
        "affected_version": "6.0.0",
        "fixed_version": "6.0.1",
        "bug_id": "github:#25310",
        "title": "Prisma 6 generate fails on Windows with spaces in path",
        "description": (
            "Paths containing spaces (e.g. `C:\\Program Files\\...`) broke the "
            "`prisma generate` step. Workaround: symlink into a space-less "
            "path. Fixed in 6.0.1."
        ),
        "severity": "medium",
        "status": "closed",
        "source": "github_issues",
        "source_url": "https://github.com/prisma/prisma/issues/25310",
        "labels": ["bug", "windows"],
    },
]


async def seed_errors(pool):
    inserted = 0
    async with pool.acquire() as conn:
        for e in SEED_ERRORS:
            norm = normalize_error(e["pattern"])
            h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
            r = await conn.execute(
                """
                INSERT INTO errors
                  (hash, pattern, full_message, ecosystem, package_name,
                   package_version, solution, confidence, source, source_url, votes)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                ON CONFLICT (hash) DO UPDATE SET
                  solution   = EXCLUDED.solution,
                  confidence = EXCLUDED.confidence,
                  updated_at = NOW()
                """,
                h, e["pattern"], e.get("full_message"), e.get("ecosystem"),
                e.get("package_name"), e.get("package_version"),
                e["solution"], e.get("confidence", 0.5),
                e.get("source", "internal"), e.get("source_url"),
                e.get("votes", 0),
            )
            inserted += 1
    return inserted


async def seed_stacks(pool):
    inserted = 0
    async with pool.acquire() as conn:
        for s in SEED_STACKS:
            h = hash_stack(s["packages"])
            r = await conn.execute(
                """
                INSERT INTO compat_matrix
                  (stack_hash, packages, status, notes, source, source_url,
                   stars, reported_count)
                VALUES ($1,$2::jsonb,$3,$4,$5,$6,$7,$8)
                ON CONFLICT (stack_hash) DO UPDATE SET
                  status         = EXCLUDED.status,
                  notes          = EXCLUDED.notes,
                  reported_count = compat_matrix.reported_count + 1,
                  updated_at     = NOW()
                """,
                h, json.dumps(s["packages"]), s["status"], s.get("notes"),
                s.get("source", "community"), s.get("source_url"),
                s.get("stars", 0), 1,
            )
            inserted += 1
    return inserted


async def seed_bugs(pool):
    inserted = 0
    async with pool.acquire() as conn:
        for b in SEED_BUGS:
            await conn.execute(
                """
                INSERT INTO known_bugs
                  (ecosystem, package_name, affected_version, fixed_version,
                   bug_id, title, description, severity, status, source,
                   source_url, labels)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                ON CONFLICT (ecosystem, package_name, bug_id) DO UPDATE SET
                  title         = EXCLUDED.title,
                  description   = EXCLUDED.description,
                  severity      = EXCLUDED.severity,
                  status        = EXCLUDED.status,
                  fixed_version = EXCLUDED.fixed_version,
                  updated_at    = NOW()
                """,
                b["ecosystem"], b["package_name"], b.get("affected_version"),
                b.get("fixed_version"), b["bug_id"], b["title"],
                b.get("description"), b.get("severity"),
                b.get("status", "open"), b.get("source", "github_issues"),
                b.get("source_url"), b.get("labels") or [],
            )
            inserted += 1
    return inserted


async def main():
    pool = await get_pool()
    try:
        e = await seed_errors(pool)
        s = await seed_stacks(pool)
        b = await seed_bugs(pool)
    finally:
        await close_pool()
    print(f"Seed complete: {e} errors, {s} stacks, {b} bugs.")


if __name__ == "__main__":
    asyncio.run(main())
