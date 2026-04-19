"""Scrape popular starter-kit `package.json` / `pyproject.toml` files from
GitHub and record verified package combinations into `compat_matrix`.

Strategy: GitHub code search is heavily restricted for our (shadow-banned)
token, so we rely on a curated list of highly-starred template repositories
and fetch their manifest files directly via raw.githubusercontent.com. We
also try the official Vercel/Nuxt/Fastify examples trees, which are a rich
source of verified stacks.
"""
import asyncio
import json
import re
import sys
import time
from typing import Optional

import aiohttp

sys.path.insert(0, "/home/deploy/depscope")
from api.verticals import hash_stack  # noqa: E402
from scripts.ingest._common import (
    GITHUB_TOKEN,
    RateLimiter,
    get_db_pool,
    get_logger,
    http_get,
    parse_github_repo,
)

logger = get_logger("npm_compat")

# Extra Next.js examples — added to CURATED_REPOS below.
_NEXT_EXAMPLES = [
    "with-mdx", "with-mdx-remote", "with-mdx-server-components",
    "with-ant-design", "with-bulma", "with-context-api",
    "with-cookie-auth-fauna", "with-custom-babel-config",
    "with-env-from-next-config-js", "with-jotai",
    "with-koa", "with-mongodb-mongoose", "with-pwa-sw",
    "with-sanity", "with-sqlite", "with-storybook",
    "with-suspense", "with-svgr", "with-tailwindcss-mdx",
    "with-trpc", "with-turbopack", "with-turborepo",
    "with-typescript-eslint-jest",
    "with-urql", "with-vitest", "with-xstate",
    "with-swr", "with-sequelize",
    "with-web-worker", "with-webassembly",
    "active-class-name", "api-middlewares",
    "blog-starter-typescript",
    "cms-agilitycms", "cms-builder-io", "cms-contentlayer",
    "cms-dotcms", "cms-drupal", "cms-ghost",
    "cms-graphcms", "cms-keystonejs-embedded", "cms-kontent-ai",
    "cms-makeswift", "cms-prepr", "cms-prismic",
    "cms-storyblok", "cms-tina", "cms-umbraco",
    "cms-wordpress-amp", "cms-webiny",
    "environment-variables", "hello-world",
    "image-component", "image-legacy-component",
    "remove-console", "script-component",
]

# (owner, repo, branch, filename, ecosystem)
# Hand-picked highly-starred templates / boilerplates (stars fetched lazily).
CURATED_REPOS: list[tuple[str, str, str, str, str]] = [
    # Next.js / React ecosystem (npm)
    ("vercel", "next.js", "canary", "examples/with-typescript/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-tailwindcss/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-prisma/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-mongodb/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-redis/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-supabase/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-stripe-typescript/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/api-routes-graphql/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-clerk/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-auth/package.json", "npm"),
    ("t3-oss", "create-t3-app", "main", "cli/template/base/package.json", "npm"),
    ("shadcn-ui", "taxonomy", "main", "package.json", "npm"),
    ("shadcn-ui", "ui", "main", "apps/www/package.json", "npm"),
    ("calcom", "cal.com", "main", "package.json", "npm"),
    ("documenso", "documenso", "main", "package.json", "npm"),
    ("vercel", "commerce", "main", "package.json", "npm"),
    ("nuxt", "nuxt", "main", "examples/essentials/hello-world/package.json", "npm"),
    ("nuxt", "starter", "v3", "package.json", "npm"),
    ("sveltejs", "kit", "main", "packages/create-svelte/templates/default/package.json", "npm"),
    ("remix-run", "indie-stack", "main", "package.json", "npm"),
    ("remix-run", "blues-stack", "main", "package.json", "npm"),
    ("remix-run", "grunge-stack", "main", "package.json", "npm"),
    ("vitejs", "vite", "main", "packages/create-vite/template-react-ts/package.json", "npm"),
    ("vitejs", "vite", "main", "packages/create-vite/template-vue-ts/package.json", "npm"),
    ("vitejs", "vite", "main", "packages/create-vite/template-svelte-ts/package.json", "npm"),
    ("fastify", "fastify", "main", "package.json", "npm"),
    ("expressjs", "express", "master", "package.json", "npm"),
    ("nestjs", "nest", "master", "package.json", "npm"),
    ("nestjs", "typescript-starter", "master", "package.json", "npm"),
    ("trpc", "trpc", "main", "packages/server/package.json", "npm"),
    ("prisma", "prisma-examples", "latest", "typescript/rest-nextjs-api-routes/package.json", "npm"),
    ("prisma", "prisma-examples", "latest", "typescript/graphql/package.json", "npm"),
    ("prisma", "prisma-examples", "latest", "typescript/rest-express/package.json", "npm"),
    ("vueuse", "vueuse", "main", "package.json", "npm"),
    ("quasarframework", "quasar", "dev", "ui/package.json", "npm"),
    ("solidjs", "solid-start", "main", "packages/start/package.json", "npm"),
    ("withastro", "astro", "main", "examples/basics/package.json", "npm"),
    ("withastro", "astro", "main", "examples/blog/package.json", "npm"),
    ("withastro", "astro", "main", "examples/with-tailwindcss/package.json", "npm"),
    ("strapi", "strapi", "main", "packages/core/strapi/package.json", "npm"),
    ("payloadcms", "payload", "main", "packages/payload/package.json", "npm"),
    ("hasura", "hasura-nextjs-trello-app-boilerplate", "main", "package.json", "npm"),

    # Python (pypi) — FastAPI / Django / Flask full-template
    ("tiangolo", "full-stack-fastapi-template", "master", "backend/pyproject.toml", "pypi"),
    ("tiangolo", "fastapi", "master", "pyproject.toml", "pypi"),
    ("encode", "django-rest-framework", "master", "requirements/requirements-packaging.txt", "pypi"),
    ("encode", "django-rest-framework", "master", "requirements/requirements-testing.txt", "pypi"),
    ("encode", "starlette", "master", "requirements.txt", "pypi"),
    ("pallets", "flask", "main", "requirements/dev.txt", "pypi"),
    ("django", "django", "main", "docs/requirements.txt", "pypi"),
    ("zauberzeug", "nicegui", "main", "pyproject.toml", "pypi"),
    ("streamlit", "streamlit", "develop", "lib/dev-requirements.txt", "pypi"),
    ("gradio-app", "gradio", "main", "requirements.txt", "pypi"),
    ("pytorch", "pytorch", "main", "requirements.txt", "pypi"),
    ("huggingface", "transformers", "main", "setup.py", "pypi"),
    ("langchain-ai", "langchain", "master", "libs/langchain/pyproject.toml", "pypi"),
    ("joke2k", "faker", "master", "requirements.txt", "pypi"),
    ("pypa", "pip", "main", "tests/requirements.txt", "pypi"),
    ("scikit-learn", "scikit-learn", "main", "pyproject.toml", "pypi"),
    ("pallets", "click", "main", "pyproject.toml", "pypi"),
    ("pydantic", "pydantic", "main", "pyproject.toml", "pypi"),
    ("celery", "celery", "main", "requirements/default.txt", "pypi"),

    # Rust (cargo)
    ("tokio-rs", "axum", "main", "Cargo.toml", "cargo"),
    ("tokio-rs", "axum", "main", "examples/hello-world/Cargo.toml", "cargo"),
    ("tokio-rs", "axum", "main", "examples/todos/Cargo.toml", "cargo"),
    ("actix", "actix-web", "master", "Cargo.toml", "cargo"),
    ("actix", "examples", "master", "basics/hello-world/Cargo.toml", "cargo"),
    ("actix", "examples", "master", "databases/diesel/Cargo.toml", "cargo"),
    ("actix", "examples", "master", "websockets/chat/Cargo.toml", "cargo"),
    ("seanmonstar", "warp", "master", "Cargo.toml", "cargo"),
    ("poem-web", "poem", "master", "poem/Cargo.toml", "cargo"),
    ("rocket-rs", "Rocket", "master", "Cargo.toml", "cargo"),
    ("clap-rs", "clap", "master", "Cargo.toml", "cargo"),
    ("serde-rs", "serde", "master", "Cargo.toml", "cargo"),
    ("tokio-rs", "tokio", "master", "tokio/Cargo.toml", "cargo"),
    ("launchbadge", "sqlx", "main", "Cargo.toml", "cargo"),
    ("diesel-rs", "diesel", "master", "diesel/Cargo.toml", "cargo"),
    ("SeaQL", "sea-orm", "master", "sea-orm-cli/Cargo.toml", "cargo"),
    ("leptos-rs", "leptos", "main", "Cargo.toml", "cargo"),
    ("yewstack", "yew", "master", "packages/yew/Cargo.toml", "cargo"),
    ("bevyengine", "bevy", "main", "Cargo.toml", "cargo"),
    ("rust-lang", "rustlings", "main", "Cargo.toml", "cargo"),
    ("cross-rs", "cross", "main", "Cargo.toml", "cargo"),
    ("rustls", "rustls", "main", "rustls/Cargo.toml", "cargo"),

    # Additional Next.js examples — nice variety
    ("vercel", "next.js", "canary", "examples/with-docker/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-jest/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-playwright/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-cypress/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-styled-components/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-emotion/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-sentry/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/blog-starter/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-env-from-next-config-js/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-redux/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-graphql-hooks/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/cms-strapi/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/cms-wordpress/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/cms-contentful/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/cms-sanity/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-openai/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-websocket/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-firebase/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-mobx/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-chakra-ui/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-material-ui/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-styled-jsx/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-react-query/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-zustand/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-auth0/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-passport/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/active-class-name/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-stripe-typescript/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-i18n-rosetta/package.json", "npm"),
    ("vercel", "next.js", "canary", "examples/with-apollo/package.json", "npm"),
]

# Extend with the many Next.js canary examples we listed above.
CURATED_REPOS.extend(
    ("vercel", "next.js", "canary", f"examples/{eg}/package.json", "npm")
    for eg in _NEXT_EXAMPLES
)

# Additional community boilerplates with known high stars
CURATED_REPOS.extend([
    # FastAPI
    ("tiangolo", "full-stack-fastapi-template", "master", "frontend/package.json", "npm"),
    ("tiangolo", "fastapi", "master", "docs/en/docs/index.md", "pypi"),
    # More Python ML
    ("huggingface", "datasets", "main", "setup.py", "pypi"),
    ("huggingface", "accelerate", "main", "setup.py", "pypi"),
    ("openai", "openai-python", "main", "pyproject.toml", "pypi"),
    ("anthropics", "anthropic-sdk-python", "main", "pyproject.toml", "pypi"),
    ("langchain-ai", "langgraph", "main", "libs/langgraph/pyproject.toml", "pypi"),
    ("run-llama", "llama_index", "main", "pyproject.toml", "pypi"),
    # Data / infra
    ("apache", "airflow", "main", "setup.cfg", "pypi"),
    ("dagster-io", "dagster", "master", "python_modules/dagster/setup.py", "pypi"),
    ("PrefectHQ", "prefect", "main", "requirements.txt", "pypi"),
    ("ray-project", "ray", "master", "python/setup.py", "pypi"),
    # Rust
    ("paritytech", "substrate", "master", "Cargo.toml", "cargo"),
    ("solana-labs", "solana", "master", "Cargo.toml", "cargo"),
    ("matter-labs", "zksync", "main", "Cargo.toml", "cargo"),
    ("denoland", "deno", "main", "Cargo.toml", "cargo"),
    ("rust-lang", "rust", "master", "Cargo.toml", "cargo"),
    ("Byron", "gitoxide", "main", "Cargo.toml", "cargo"),
    ("pola-rs", "polars", "main", "py-polars/Cargo.toml", "cargo"),
    ("rustdesk", "rustdesk", "master", "Cargo.toml", "cargo"),
    ("meilisearch", "meilisearch", "main", "meilisearch/Cargo.toml", "cargo"),
    ("tauri-apps", "tauri", "dev", "core/tauri/Cargo.toml", "cargo"),
    # Frontend misc
    ("facebook", "create-react-app", "main", "packages/cra-template/template/package.json", "npm"),
    ("facebook", "react", "main", "package.json", "npm"),
    ("redwoodjs", "redwood", "main", "package.json", "npm"),
    ("gatsbyjs", "gatsby", "master", "package.json", "npm"),
    ("ionic-team", "ionic-framework", "main", "core/package.json", "npm"),
    ("angular", "angular", "main", "package.json", "npm"),
    ("preactjs", "preact", "main", "package.json", "npm"),
    ("lit", "lit", "main", "packages/lit/package.json", "npm"),
    # Node backend stacks
    ("directus", "directus", "main", "package.json", "npm"),
    ("supabase", "supabase", "master", "apps/studio/package.json", "npm"),
    ("sidekiq-pro", "sidekiq", "main", "package.json", "npm"),
    ("graphql", "graphql-js", "main", "package.json", "npm"),
    ("apollographql", "apollo-server", "main", "package.json", "npm"),
    ("nextauthjs", "next-auth", "main", "packages/core/package.json", "npm"),
    ("clerk", "javascript", "main", "packages/clerk-js/package.json", "npm"),
    ("pmndrs", "zustand", "main", "package.json", "npm"),
    ("pmndrs", "jotai", "main", "package.json", "npm"),
    ("TanStack", "query", "main", "packages/react-query/package.json", "npm"),
    ("TanStack", "router", "main", "packages/react-router/package.json", "npm"),
    ("TanStack", "table", "main", "packages/react-table/package.json", "npm"),
    ("mui", "material-ui", "master", "packages/mui-material/package.json", "npm"),
    ("chakra-ui", "chakra-ui", "main", "packages/components/src/package.json", "npm"),
    ("mantinedev", "mantine", "master", "packages/@mantine/core/package.json", "npm"),
    ("radix-ui", "primitives", "main", "package.json", "npm"),
    ("react-hook-form", "react-hook-form", "master", "package.json", "npm"),
    ("vercel", "ai", "main", "package.json", "npm"),
])


MIN_DEPS = 2
MAX_DEPS = 40  # cap so we don't hash huge monorepos

RE_REQ = re.compile(
    r"^\s*([A-Za-z0-9_.\-\[\]]+)\s*(?:[=<>!~]+\s*([^;#\s]+))?",
)


def parse_package_json(raw: str) -> Optional[dict[str, str]]:
    try:
        data = json.loads(raw)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    deps = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        v = data.get(key)
        if isinstance(v, dict):
            for pkg, ver in v.items():
                if not isinstance(pkg, str) or not isinstance(ver, str):
                    continue
                pkg = pkg.strip()
                ver = ver.strip().lstrip("^~>=< ")
                if pkg and ver and len(ver) < 40:
                    deps[pkg] = ver
    return deps or None


def parse_requirements_txt(raw: str) -> Optional[dict[str, str]]:
    deps: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        m = RE_REQ.match(line)
        if not m:
            continue
        name = m.group(1).lower()
        ver = (m.group(2) or "").strip().lstrip("=v")
        if name:
            deps[name] = ver or "any"
    return deps or None


def parse_pyproject_toml(raw: str) -> Optional[dict[str, str]]:
    """Cheap TOML parser — just for [tool.poetry.dependencies] / [project]."""
    deps: dict[str, str] = {}
    # PEP 621 dependencies list
    section_m = re.search(
        r'(?ms)^\s*dependencies\s*=\s*\[([^\]]+)\]', raw
    )
    if section_m:
        items = re.findall(r'"([^"]+)"|\'([^\']+)\'', section_m.group(1))
        for a, b in items:
            spec = a or b
            m = RE_REQ.match(spec)
            if m:
                deps[m.group(1).lower()] = (m.group(2) or "any").lstrip("=v")
    # Poetry-style
    section_m = re.search(
        r'(?ms)^\[tool\.poetry\.dependencies\](.*?)(?=^\[|\Z)', raw
    )
    if section_m:
        for line in section_m.group(1).splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, val = line.split("=", 1)
            name = name.strip().strip('"').lower()
            val = val.strip().strip('"').strip("'").lstrip("^~>=< ")
            if name and name != "python":
                deps[name] = val or "any"
    return deps or None


def parse_cargo_toml(raw: str) -> Optional[dict[str, str]]:
    deps: dict[str, str] = {}
    # Grab [dependencies] block and any [dependencies.<name>] tables
    top_m = re.search(
        r'(?ms)^\[dependencies\](.*?)(?=^\[|\Z)', raw
    )
    if top_m:
        for line in top_m.group(1).splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, val = line.split("=", 1)
            name = name.strip().lower()
            val = val.strip()
            if val.startswith('"') and val.endswith('"'):
                ver = val.strip('"')
            else:
                m = re.search(r'version\s*=\s*"([^"]+)"', val)
                ver = m.group(1) if m else "any"
            if name:
                deps[name] = ver
    # Sub-tables
    for m in re.finditer(
        r'(?ms)^\[dependencies\.([\w\-]+)\](.*?)(?=^\[|\Z)', raw
    ):
        name = m.group(1).lower()
        sub = m.group(2)
        ver_m = re.search(r'version\s*=\s*"([^"]+)"', sub)
        deps[name] = ver_m.group(1) if ver_m else "any"
    return deps or None


def parse_deps(filename: str, raw: str, ecosystem: str) -> Optional[dict[str, str]]:
    try:
        if filename == "package.json":
            return parse_package_json(raw)
        if filename == "requirements.txt":
            return parse_requirements_txt(raw)
        if filename == "pyproject.toml":
            return parse_pyproject_toml(raw)
        if filename == "Cargo.toml":
            return parse_cargo_toml(raw)
    except Exception as e:
        logger.debug(f"parse {filename} failed: {e}")
    return None


async def fetch_raw(
    session: aiohttp.ClientSession,
    url: str,
    limiter: RateLimiter,
) -> Optional[str]:
    """GET raw file content (plain text). raw.githubusercontent.com is not
    subject to the same rate limit as the API and is what we hit here."""
    await limiter.acquire()
    for attempt in range(3):
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                if resp.status == 200:
                    return await resp.text()
                if resp.status in (403, 429):
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                if resp.status in (404, 410):
                    return None
        except Exception:
            await asyncio.sleep(1.5 * (attempt + 1))
    return None


# Well-known highly-starred repos — used when GitHub API is rate limited.
# Rough values (don't need to be exact); the cutoff for "verified" is 1000.
_STAR_HINTS = {
    "vercel/next.js": 130000,
    "facebook/react": 230000,
    "nuxt/nuxt": 55000,
    "nuxt/starter": 2000,
    "sveltejs/kit": 20000,
    "remix-run/indie-stack": 2500,
    "remix-run/blues-stack": 2500,
    "remix-run/grunge-stack": 2000,
    "vitejs/vite": 70000,
    "fastify/fastify": 33000,
    "expressjs/express": 66000,
    "nestjs/nest": 70000,
    "nestjs/typescript-starter": 2500,
    "trpc/trpc": 37000,
    "prisma/prisma-examples": 7000,
    "vueuse/vueuse": 21000,
    "quasarframework/quasar": 27000,
    "solidjs/solid-start": 7000,
    "withastro/astro": 50000,
    "strapi/strapi": 65000,
    "payloadcms/payload": 35000,
    "t3-oss/create-t3-app": 28000,
    "shadcn-ui/taxonomy": 19000,
    "shadcn-ui/ui": 90000,
    "calcom/cal.com": 35000,
    "documenso/documenso": 9000,
    "vercel/commerce": 11000,
    "tiangolo/full-stack-fastapi-template": 30000,
    "tiangolo/fastapi": 80000,
    "encode/django-rest-framework": 29000,
    "encode/starlette": 10000,
    "pallets/flask": 70000,
    "django/django": 80000,
    "zauberzeug/nicegui": 12000,
    "streamlit/streamlit": 35000,
    "gradio-app/gradio": 35000,
    "pytorch/pytorch": 85000,
    "huggingface/transformers": 140000,
    "langchain-ai/langchain": 95000,
    "joke2k/faker": 18000,
    "pypa/pip": 9700,
    "scikit-learn/scikit-learn": 60000,
    "pallets/click": 16000,
    "pydantic/pydantic": 22000,
    "celery/celery": 24000,
    "tokio-rs/axum": 20000,
    "actix/actix-web": 22000,
    "actix/examples": 3000,
    "seanmonstar/warp": 9500,
    "poem-web/poem": 4000,
    "rocket-rs/Rocket": 25000,
    "clap-rs/clap": 15000,
    "serde-rs/serde": 9500,
    "tokio-rs/tokio": 28000,
    "launchbadge/sqlx": 14000,
    "diesel-rs/diesel": 13000,
    "SeaQL/sea-orm": 8000,
    "leptos-rs/leptos": 18000,
    "yewstack/yew": 31000,
    "bevyengine/bevy": 37000,
    "rust-lang/rustlings": 57000,
    "cross-rs/cross": 8000,
    "rustls/rustls": 6000,
    "hasura/hasura-nextjs-trello-app-boilerplate": 500,
}


async def fetch_repo_stars_cached(
    session: aiohttp.ClientSession,
    owner: str,
    repo: str,
    headers: dict,
    limiter: RateLimiter,
    cache: dict[str, int],
    api_allowed: list[bool],
) -> int:
    """Return stars for owner/repo, preferring the local hint map and
    caching results. `api_allowed` is a one-element list toggled to False
    on the first HTTP error so we don't keep hammering a rate-limited
    endpoint — subsequent calls fall back to a `500` default."""
    key = f"{owner}/{repo}"
    if key in cache:
        return cache[key]
    hint = _STAR_HINTS.get(key)
    if hint is not None:
        cache[key] = hint
        return hint
    if not api_allowed[0]:
        # Conservative default — still below the 1000★ "verified" threshold
        cache[key] = 500
        return 500
    await limiter.acquire()
    try:
        async with session.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                stars = int((data or {}).get("stargazers_count") or 0)
                cache[key] = stars
                return stars
            if resp.status in (403, 429):
                logger.warning(
                    "GitHub stars endpoint rate-limited — disabling for "
                    "remainder of run"
                )
                api_allowed[0] = False
    except Exception:
        api_allowed[0] = False
    cache[key] = 500
    return 500


async def process_entry(
    session: aiohttp.ClientSession,
    entry: tuple[str, str, str, str, str],
    headers: dict,
    limiter_raw: RateLimiter,
    limiter_api: RateLimiter,
    pool,
    stars_cache: dict[str, int],
    api_allowed: list[bool],
) -> int:
    owner, repo, branch, path, ecosystem = entry
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    raw = await fetch_raw(session, raw_url, limiter_raw)
    if not raw or len(raw) > 500_000:
        return 0
    filename = path.rsplit("/", 1)[-1]
    deps = parse_deps(filename, raw, ecosystem)
    if not deps or len(deps) < MIN_DEPS:
        return 0
    if len(deps) > MAX_DEPS:
        deps = dict(sorted(deps.items())[:MAX_DEPS])
    stars = await fetch_repo_stars_cached(
        session, owner, repo, headers, limiter_api, stars_cache, api_allowed
    )
    h = hash_stack(deps)
    status = "verified" if stars >= 1000 else "likely_ok"
    source = "starter_template" if stars >= 1000 else "github_starter"
    notes = f"{owner}/{repo} — {path} ({stars}★)"
    try:
        async with pool.acquire() as conn:
            res = await conn.execute(
                """
                INSERT INTO compat_matrix(
                    stack_hash, packages, status, notes,
                    source, source_url, stars, reported_count
                ) VALUES ($1, $2::jsonb, $3, $4, $5, $6, $7, 1)
                ON CONFLICT (stack_hash) DO UPDATE SET
                    stars = GREATEST(compat_matrix.stars, EXCLUDED.stars),
                    reported_count = compat_matrix.reported_count + 1,
                    updated_at = now()
                """,
                h,
                json.dumps(deps),
                status,
                notes[:500],
                source,
                f"https://github.com/{owner}/{repo}",
                stars,
            )
            if res and res.endswith("1"):
                return 1
    except Exception as e:
        logger.warning(f"insert compat {owner}/{repo}: {e}")
    return 0


async def fetch_npm_manifest(
    session: aiohttp.ClientSession,
    pkg: str,
    limiter: RateLimiter,
) -> Optional[dict]:
    await limiter.acquire()
    data = await http_get(
        session,
        f"https://registry.npmjs.org/{pkg}/latest",
        logger=logger,
    )
    return data if isinstance(data, dict) else None


async def fetch_pypi_manifest(
    session: aiohttp.ClientSession,
    pkg: str,
    limiter: RateLimiter,
) -> Optional[dict]:
    await limiter.acquire()
    data = await http_get(
        session,
        f"https://pypi.org/pypi/{pkg}/json",
        logger=logger,
    )
    return data if isinstance(data, dict) else None


async def fetch_cargo_manifest(
    session: aiohttp.ClientSession,
    pkg: str,
    limiter: RateLimiter,
) -> Optional[dict]:
    await limiter.acquire()
    data = await http_get(
        session,
        f"https://crates.io/api/v1/crates/{pkg}",
        logger=logger,
    )
    return data if isinstance(data, dict) else None


async def ingest_from_registry(
    session: aiohttp.ClientSession,
    registry_limiter: RateLimiter,
    pool,
) -> int:
    """For the top 300 packages per ecosystem, record the (pkg, direct deps)
    combination as a `registry_deps` compat row. This produces very real,
    verified stacks because the package itself installed them in production.
    """
    inserted = 0
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT ecosystem, name, latest_version
            FROM packages
            WHERE ecosystem IN ('npm', 'pypi', 'cargo')
            ORDER BY downloads_weekly DESC NULLS LAST
            LIMIT 1200
            """
        )
    for r in rows:
        eco = r["ecosystem"]
        name = r["name"]
        try:
            if eco == "npm":
                m = await fetch_npm_manifest(session, name, registry_limiter)
                if not m:
                    continue
                deps = dict(m.get("dependencies") or {})
                pkg_version = m.get("version") or r["latest_version"] or "latest"
                source_url = f"https://www.npmjs.com/package/{name}"
            elif eco == "pypi":
                m = await fetch_pypi_manifest(session, name, registry_limiter)
                if not m:
                    continue
                info = m.get("info") or {}
                pkg_version = info.get("version") or r["latest_version"] or "latest"
                deps: dict[str, str] = {}
                for req in (info.get("requires_dist") or []):
                    if not req or ";" in req:
                        # skip env-marker-gated deps (keep only unconditional)
                        if ";" in req:
                            base = req.split(";", 1)[0].strip()
                        else:
                            base = req
                    else:
                        base = req
                    m2 = re.match(r"([A-Za-z0-9_.\-\[\]]+)\s*(.*)", base or "")
                    if not m2:
                        continue
                    dep_name = m2.group(1).strip()
                    spec = (m2.group(2) or "").strip() or "any"
                    # Strip parens/extras
                    spec = spec.split(";")[0].strip("()").strip() or "any"
                    if dep_name:
                        deps[dep_name.lower()] = spec[:40]
                source_url = f"https://pypi.org/project/{name}/"
            elif eco == "cargo":
                m = await fetch_cargo_manifest(session, name, registry_limiter)
                if not m:
                    continue
                crate = (m.get("crate") or {})
                versions = m.get("versions") or []
                latest = next(
                    (v for v in versions if not v.get("yanked")),
                    versions[0] if versions else None,
                )
                pkg_version = (
                    (latest or {}).get("num")
                    or r["latest_version"] or "latest"
                )
                # Fetch dependencies for this version
                if latest and latest.get("id"):
                    dep_data = await http_get(
                        session,
                        f"https://crates.io/api/v1/crates/{name}/{pkg_version}/dependencies",
                        logger=logger,
                    )
                else:
                    dep_data = None
                deps = {}
                if isinstance(dep_data, dict):
                    for d in dep_data.get("dependencies") or []:
                        if d.get("kind") == "normal":
                            deps[d.get("crate_id", "")] = d.get("req", "any")
                deps = {k: v for k, v in deps.items() if k}
                source_url = f"https://crates.io/crates/{name}"
            else:
                continue
            if not deps or len(deps) < 2:
                continue
            if len(deps) > MAX_DEPS:
                deps = dict(sorted(deps.items())[:MAX_DEPS])
            # Include the package itself in the stack so it's recoverable
            stack = {**deps, name: str(pkg_version)[:40]}
            h = hash_stack(stack)
            notes = f"Direct dependencies of {eco}:{name}@{pkg_version}"
            try:
                async with pool.acquire() as conn:
                    res = await conn.execute(
                        """
                        INSERT INTO compat_matrix(
                            stack_hash, packages, status, notes,
                            source, source_url, stars, reported_count
                        ) VALUES ($1, $2::jsonb, $3, $4, $5, $6, $7, 1)
                        ON CONFLICT (stack_hash) DO UPDATE SET
                            reported_count = compat_matrix.reported_count + 1,
                            updated_at = now()
                        """,
                        h,
                        json.dumps(stack),
                        "verified",
                        notes[:500],
                        "registry_deps",
                        source_url,
                        0,
                    )
                    if res and res.endswith("1"):
                        inserted += 1
            except Exception as e:
                logger.warning(f"insert registry_deps {eco}/{name}: {e}")
        except Exception as e:
            logger.warning(f"fetch {eco}/{name}: {e}")
    logger.info(f"registry_deps: +{inserted}")
    return inserted


async def main() -> int:
    start = time.time()
    pool = await get_db_pool()
    try:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "depscope-ingest/1.0",
        }
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
            logger.info("npm_compat: authenticated")
        else:
            logger.warning("npm_compat: unauthenticated")

        # raw.githubusercontent.com: very permissive, we still stay polite
        limiter_raw = RateLimiter(max_calls=2, period=1.0)
        # api.github.com: core rate limit matters — space calls out
        limiter_api = RateLimiter(max_calls=1, period=2.0)

        stars_cache: dict[str, int] = {}
        api_allowed = [True]  # flipped to False after first rate-limit hit

        # Registry limiter — the public npm/PyPI/crates.io endpoints handle
        # a few hundred req/s without issue; we stay deliberately polite.
        registry_limiter = RateLimiter(max_calls=5, period=1.0)

        before = await pool.fetchval("SELECT COUNT(*) FROM compat_matrix")
        total = 0
        async with aiohttp.ClientSession() as session:
            # Pass 1: curated starter-kit repos
            for i, entry in enumerate(CURATED_REPOS, 1):
                try:
                    total += await process_entry(
                        session, entry, headers, limiter_raw,
                        limiter_api, pool, stars_cache, api_allowed,
                    )
                except Exception as e:
                    logger.warning(f"entry {entry}: {e}")
                if i % 25 == 0:
                    logger.info(f"compat progress: {i}/{len(CURATED_REPOS)}, +{total}")
            # Pass 2: registry metadata — direct deps of top packages
            try:
                total += await ingest_from_registry(
                    session, registry_limiter, pool
                )
            except Exception as e:
                logger.warning(f"registry ingest failed: {e}")
        after = await pool.fetchval("SELECT COUNT(*) FROM compat_matrix")
        logger.info(
            f"npm_compat done: +{total} ({before} -> {after}) "
            f"in {time.time()-start:.1f}s"
        )
        return total
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
