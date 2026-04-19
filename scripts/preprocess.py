"""Pre-process popular packages: fetch, score, cache in Redis + save to PostgreSQL.
Runs via cron every 6 hours. When an agent asks for a popular package, response is instant from cache.
"""
import asyncio
import sys
import time
import json
sys.path.insert(0, "/home/deploy/depscope")

import aiohttp
from api.registries import fetch_package, fetch_vulnerabilities, save_package_to_db, fetch_npm_downloads
from api.health import calculate_health_score
from api.cache import cache_set


# ─── TOP NPM: fetched dynamically from npm downloads API ───
FALLBACK_NPM = [
    "react", "next", "typescript", "lodash", "axios", "express", "vue",
    "webpack", "vite", "esbuild", "tailwindcss", "prisma", "zod", "fastify",
    "hono", "drizzle-orm", "jest", "vitest", "eslint", "prettier", "nodemon",
    "pm2", "socket.io", "redis", "pg", "mongoose", "jsonwebtoken", "bcrypt",
    "dotenv", "cors", "helmet", "morgan", "multer", "uuid", "date-fns",
    "dayjs", "moment", "chalk", "commander", "inquirer", "zustand", "jotai",
    "framer-motion", "swr", "react-dom", "react-router-dom", "angular",
    "svelte", "@types/node", "@types/react", "tslib", "rxjs", "debug",
    "semver", "glob", "minimatch", "yargs", "fs-extra", "cross-env",
    "rimraf", "concurrently", "http-proxy-middleware", "compression",
    "cookie-parser", "express-session", "passport", "jsonschema",
    "ajv", "joi", "yup", "class-validator", "bullmq", "ioredis",
    "knex", "sequelize", "typeorm", "mikro-orm", "better-sqlite3",
    "sharp", "puppeteer", "playwright", "cheerio", "node-fetch",
    "undici", "got", "superagent", "ws", "graphql", "apollo-server",
    "nexus", "trpc", "next-auth", "lucia", "passport-jwt",
    "bcryptjs", "argon2", "nanoid", "cuid", "ulid",
    "pino", "winston", "bunyan", "lru-cache", "p-queue",
    "ora", "listr2", "execa", "tsx", "jiti", "unbuild",
    "rollup", "turbo", "nx", "lerna", "changesets",
]

POPULAR_PYPI = [
    "requests", "numpy", "pandas", "fastapi", "django", "flask",
    "pydantic", "sqlalchemy", "celery", "redis", "httpx", "uvicorn",
    "pytest", "black", "ruff", "mypy", "pillow", "boto3",
    "scikit-learn", "tensorflow", "torch", "transformers",
    "anthropic", "openai", "langchain", "beautifulsoup4", "scrapy",
    "click", "typer", "rich", "aiohttp", "asyncpg", "psycopg2-binary",
    "gunicorn", "starlette", "alembic", "jinja2", "markupsafe",
    "cryptography", "pyjwt", "python-dotenv", "pyyaml", "toml",
    "tqdm", "colorama", "tabulate", "loguru", "structlog",
    "matplotlib", "seaborn", "plotly", "scipy", "sympy",
    "networkx", "nltk", "spacy", "gensim", "sentence-transformers",
    "opencv-python", "imageio", "albumentations",
    "dask", "polars", "pyarrow", "orjson", "ujson", "msgpack",
    "websockets", "grpcio", "protobuf", "pika", "aiokafka",
    "sentry-sdk", "prometheus-client", "datadog",
    "paramiko", "fabric", "invoke", "nox", "tox",
    "setuptools", "wheel", "poetry-core", "hatchling", "flit-core",
    "coverage", "hypothesis", "faker", "factory-boy",
    "pre-commit", "isort", "autopep8", "flake8", "pylint",
    "docker", "kubernetes", "ansible-core",
    "strawberry-graphql", "ariadne", "litestar",
    "tenacity", "backoff", "cachetools", "diskcache",
]

POPULAR_CARGO = [
    "serde", "tokio", "reqwest", "clap", "actix-web", "axum",
    "tracing", "anyhow", "thiserror", "rand", "regex", "chrono",
    "uuid", "sqlx", "diesel", "rocket", "serde_json", "log",
    "env_logger", "futures", "async-trait", "bytes", "hyper",
    "tower", "tonic", "prost", "rayon", "crossbeam", "parking_lot",
    "dashmap", "once_cell", "lazy_static", "itertools", "num",
    "base64", "sha2", "ring", "rustls", "native-tls",
    "tempfile", "walkdir", "globset", "notify", "toml",
    "config", "figment", "dotenvy", "tracing-subscriber",
    "color-eyre", "miette", "indicatif", "dialoguer", "comfy-table",
]


async def fetch_top_npm_names(limit: int = 200) -> list[str]:
    """Try to get top npm packages by downloads. Falls back to hardcoded list."""
    # npm doesn't have a "top packages" endpoint directly, but we can use
    # the bulk downloads endpoint for our known list + add any we discover
    # For now use our curated list which covers the top packages
    return FALLBACK_NPM[:limit]


async def process_package(ecosystem: str, name: str) -> dict | None:
    """Fetch a single package, calculate health, cache + save to DB."""
    try:
        pkg = await fetch_package(ecosystem, name)
        if not pkg:
            return None

        latest_version = pkg.get("latest_version", "")
        vulns = await fetch_vulnerabilities(ecosystem, name, latest_version=latest_version)
        health = calculate_health_score(pkg, vulns)

        # Build full result (same format as /api/check)
        result = {
            "package": name,
            "ecosystem": ecosystem,
            "latest_version": pkg.get("latest_version"),
            "description": pkg.get("description", ""),
            "license": pkg.get("license", ""),
            "homepage": pkg.get("homepage", ""),
            "repository": pkg.get("repository", ""),
            "downloads_weekly": pkg.get("downloads_weekly", 0),
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
                "latest": pkg.get("latest_version"),
                "total_count": pkg.get("all_version_count", 0),
                "recent": pkg.get("versions", []),
            },
            "metadata": {
                "deprecated": pkg.get("deprecated", False),
                "deprecated_message": pkg.get("deprecated_message"),
                "maintainers_count": pkg.get("maintainers_count", 0),
                "first_published": pkg.get("first_published"),
                "last_published": pkg.get("last_published"),
                "dependencies_count": len(pkg.get("dependencies", [])),
                "dependencies": pkg.get("dependencies", []),
            },
            "_preprocessed": True,
        }

        # Cache in Redis with 24h TTL
        await cache_set(f"check:{ecosystem}:{name}", result, ttl=86400)

        # Save to PostgreSQL
        await save_package_to_db(pkg, health["score"], vulns)

        return result
    except Exception as e:
        print(f"  ERROR {ecosystem}/{name}: {e}")
        return None


async def preprocess_ecosystem(ecosystem: str, names: list[str]) -> int:
    """Process all packages for an ecosystem with rate limiting."""
    success = 0
    for i, name in enumerate(names):
        result = await process_package(ecosystem, name)
        if result:
            score = result["health"]["score"]
            vulns = result["vulnerabilities"]["count"]
            downloads = result.get("downloads_weekly", 0)
            print(f"  {ecosystem}/{name}: health={score}/100, vulns={vulns}, downloads={downloads:,}")
            success += 1
        else:
            print(f"  {ecosystem}/{name}: FAILED")

        # Rate limit: small delay between requests to be polite to registries
        if (i + 1) % 10 == 0:
            await asyncio.sleep(1)

    return success


async def main():
    start = time.time()
    print(f"=== DepScope Pre-processor ===")
    print(f"Started at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Get npm top packages
    npm_names = await fetch_top_npm_names(200)
    print(f"--- NPM ({len(npm_names)} packages) ---")
    npm_ok = await preprocess_ecosystem("npm", npm_names)

    print(f"\n--- PyPI ({len(POPULAR_PYPI)} packages) ---")
    pypi_ok = await preprocess_ecosystem("pypi", POPULAR_PYPI)

    print(f"\n--- Cargo ({len(POPULAR_CARGO)} packages) ---")
    cargo_ok = await preprocess_ecosystem("cargo", POPULAR_CARGO)

    elapsed = time.time() - start
    total = npm_ok + pypi_ok + cargo_ok
    print(f"\n=== Done: {total} packages processed in {elapsed:.0f}s ===")
    print(f"  npm: {npm_ok}/{len(npm_names)}")
    print(f"  pypi: {pypi_ok}/{len(POPULAR_PYPI)}")
    print(f"  cargo: {cargo_ok}/{len(POPULAR_CARGO)}")


if __name__ == "__main__":
    asyncio.run(main())
