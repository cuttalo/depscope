"""Expand database massively — fetch top packages from registries"""
import asyncio
import aiohttp
import sys
import time

sys.path.insert(0, "/home/deploy/depscope")
from api.registries import fetch_package, fetch_vulnerabilities, save_package_to_db
from api.health import calculate_health_score
from api.cache import cache_set

# Top npm keywords to search — each returns 250 results
NPM_KEYWORDS = [
    "react", "vue", "angular", "svelte", "next", "express", "fastify",
    "webpack", "vite", "esbuild", "rollup", "babel", "typescript",
    "eslint", "prettier", "jest", "vitest", "mocha", "testing",
    "lodash", "axios", "fetch", "http", "request", "api",
    "database", "mongodb", "postgres", "mysql", "redis", "sqlite",
    "auth", "jwt", "oauth", "session", "passport",
    "css", "tailwind", "styled", "emotion", "sass",
    "cli", "commander", "yargs", "chalk", "ora",
    "fs", "path", "stream", "buffer", "crypto",
    "socket", "websocket", "graphql", "rest", "grpc",
    "docker", "kubernetes", "aws", "azure", "gcp",
    "logger", "winston", "pino", "morgan", "debug",
    "validation", "zod", "joi", "yup", "ajv",
    "orm", "prisma", "drizzle", "sequelize", "typeorm", "knex",
    "date", "dayjs", "moment", "luxon",
    "image", "sharp", "jimp", "canvas",
    "email", "nodemailer", "sendgrid",
    "queue", "bull", "bee-queue", "agenda",
    "cache", "node-cache", "lru-cache",
    "security", "helmet", "cors", "csrf", "rate-limit",
    "pdf", "puppeteer", "playwright",
    "ai", "openai", "anthropic", "langchain", "llm",
]

# Top cargo keywords
CARGO_KEYWORDS = [
    "async", "web", "http", "json", "cli", "database", "crypto",
    "serde", "tokio", "reqwest", "clap", "log", "error",
    "parser", "regex", "uuid", "time", "rand",
    "file", "io", "network", "tls", "compression",
]

async def fetch_npm_search(keyword, size=50):
    """Search npm registry for packages by keyword"""
    url = f"https://registry.npmjs.org/-/v1/search?text={keyword}&size={size}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [obj["package"]["name"] for obj in data.get("objects", [])]
    except:
        pass
    return []

async def fetch_cargo_search(keyword, size=50):
    """Search crates.io for packages by keyword"""
    url = f"https://crates.io/api/v1/crates?q={keyword}&per_page={size}"
    headers = {"User-Agent": "DepScope/0.1 (https://depscope.dev)"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [c["name"] for c in data.get("crates", [])]
    except:
        pass
    return []

async def process_package(eco, name, processed):
    """Fetch, score, and save a single package"""
    key = f"{eco}:{name}"
    if key in processed:
        return False
    processed.add(key)
    
    try:
        pkg = await fetch_package(eco, name)
        if not pkg:
            return False
        
        latest = pkg.get("latest_version", "")
        vulns = await fetch_vulnerabilities(eco, name, latest_version=latest)
        health = calculate_health_score(pkg, vulns)
        
        await save_package_to_db(pkg, health["score"], vulns)
        await cache_set(f"check:{eco}:{name}", {
            "package": name, "ecosystem": eco,
            "latest_version": pkg.get("latest_version"),
            "health": health,
            "vulnerabilities": {"count": len(vulns)},
        }, ttl=86400)
        
        return True
    except:
        return False

async def main():
    processed = set()
    total_new = 0
    
    # Load existing packages
    import asyncpg
    conn = await asyncpg.connect("postgresql://depscope:${DB_PASSWORD}@localhost:5432/depscope")
    rows = await conn.fetch("SELECT ecosystem, name FROM packages")
    for r in rows:
        processed.add(f"{r['ecosystem']}:{r['name']}")
    await conn.close()
    
    print(f"Existing: {len(processed)} packages")
    
    # npm expansion
    print(f"\n=== npm expansion ({len(NPM_KEYWORDS)} keywords) ===")
    npm_names = set()
    for i, kw in enumerate(NPM_KEYWORDS):
        names = await fetch_npm_search(kw, size=50)
        npm_names.update(names)
        if (i + 1) % 10 == 0:
            print(f"  Searched {i+1}/{len(NPM_KEYWORDS)} keywords, found {len(npm_names)} unique packages")
        await asyncio.sleep(0.5)  # rate limit
    
    print(f"  Total unique npm packages found: {len(npm_names)}")
    new_npm = [n for n in npm_names if f"npm:{n}" not in processed]
    print(f"  New (not in DB): {len(new_npm)}")
    
    # Process npm in batches
    for i, name in enumerate(new_npm):
        ok = await process_package("npm", name, processed)
        if ok:
            total_new += 1
        if (i + 1) % 50 == 0:
            print(f"  Processed {i+1}/{len(new_npm)} npm, {total_new} new")
        await asyncio.sleep(0.3)
    
    # Cargo expansion
    print(f"\n=== cargo expansion ({len(CARGO_KEYWORDS)} keywords) ===")
    cargo_names = set()
    for kw in CARGO_KEYWORDS:
        names = await fetch_cargo_search(kw, size=50)
        cargo_names.update(names)
        await asyncio.sleep(1)  # crates.io rate limit stricter
    
    print(f"  Total unique cargo crates found: {len(cargo_names)}")
    new_cargo = [n for n in cargo_names if f"cargo:{n}" not in processed]
    print(f"  New: {len(new_cargo)}")
    
    for i, name in enumerate(new_cargo):
        ok = await process_package("cargo", name, processed)
        if ok:
            total_new += 1
        if (i + 1) % 20 == 0:
            print(f"  Processed {i+1}/{len(new_cargo)} cargo, {total_new} new total")
        await asyncio.sleep(1)
    
    print(f"\n=== DONE: {total_new} new packages added ===")

asyncio.run(main())
