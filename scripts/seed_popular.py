"""Seed popular packages into the database for faster first-hit responses"""
import asyncio
import sys
sys.path.insert(0, "/home/deploy/depscope")

from api.registries import fetch_package, fetch_vulnerabilities
from api.health import calculate_health_score
from api.cache import cache_set
import json

POPULAR_NPM = [
    "react", "express", "next", "typescript", "lodash", "axios",
    "vue", "angular", "svelte", "webpack", "vite", "esbuild",
    "tailwindcss", "prisma", "zod", "fastify", "hono", "drizzle-orm",
    "jest", "vitest", "eslint", "prettier", "nodemon", "pm2",
    "socket.io", "redis", "pg", "mongoose", "jsonwebtoken", "bcrypt",
    "dotenv", "cors", "helmet", "morgan", "multer", "uuid",
    "date-fns", "dayjs", "moment", "chalk", "commander", "inquirer",
    "react-query", "swr", "zustand", "jotai", "framer-motion",
]

POPULAR_PYPI = [
    "fastapi", "django", "flask", "requests", "numpy", "pandas",
    "pydantic", "sqlalchemy", "celery", "redis", "httpx", "uvicorn",
    "pytest", "black", "ruff", "mypy", "pillow", "boto3",
    "scikit-learn", "tensorflow", "pytorch", "transformers",
    "anthropic", "openai", "langchain", "beautifulsoup4", "scrapy",
    "click", "typer", "rich", "aiohttp", "asyncpg",
]

POPULAR_CARGO = [
    "serde", "tokio", "reqwest", "clap", "actix-web", "axum",
    "tracing", "anyhow", "thiserror", "rand", "regex", "chrono",
    "uuid", "sqlx", "diesel", "rocket",
]


async def seed():
    total = 0
    for name in POPULAR_NPM:
        try:
            pkg = await fetch_package("npm", name)
            if pkg:
                vulns = await fetch_vulnerabilities("npm", name)
                health = calculate_health_score(pkg, vulns)
                result = {
                    "package": name, "ecosystem": "npm",
                    "latest_version": pkg.get("latest_version"),
                    "health": health,
                    "vulnerabilities": {"count": len(vulns)},
                }
                await cache_set(f"check:npm:{name}", result, ttl=86400)
                total += 1
                print(f"  npm/{name}: {health['score']}/100")
        except Exception as e:
            print(f"  npm/{name}: ERROR {e}")

    for name in POPULAR_PYPI:
        try:
            pkg = await fetch_package("pypi", name)
            if pkg:
                vulns = await fetch_vulnerabilities("pypi", name)
                health = calculate_health_score(pkg, vulns)
                await cache_set(f"check:pypi:{name}", {"package": name, "ecosystem": "pypi", "latest_version": pkg.get("latest_version"), "health": health, "vulnerabilities": {"count": len(vulns)}}, ttl=86400)
                total += 1
                print(f"  pypi/{name}: {health['score']}/100")
        except Exception as e:
            print(f"  pypi/{name}: ERROR {e}")

    for name in POPULAR_CARGO:
        try:
            pkg = await fetch_package("cargo", name)
            if pkg:
                vulns = await fetch_vulnerabilities("cargo", name)
                health = calculate_health_score(pkg, vulns)
                await cache_set(f"check:cargo:{name}", {"package": name, "ecosystem": "cargo", "latest_version": pkg.get("latest_version"), "health": health, "vulnerabilities": {"count": len(vulns)}}, ttl=86400)
                total += 1
                print(f"  cargo/{name}: {health['score']}/100")
        except Exception as e:
            print(f"  cargo/{name}: ERROR {e}")

    print(f"\nSeeded {total} packages")


if __name__ == "__main__":
    asyncio.run(seed())
