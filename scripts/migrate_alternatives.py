"""
Migra _PACKAGE_ALTERNATIVES dict -> tabella alternatives.

Idempotente: ON CONFLICT DO UPDATE per reason/score/builtin.
Detection builtin: se contiene '.', '::', ' ', o sta nella lista nota.
Package source + alt reali: upsert in packages se mancanti.
Builtin: solo alternative_name, FK NULL, is_builtin=TRUE.
Score: decrescente da 100 in base all'ordine nel dict (prima = migliore).

Uso: cd /home/deploy/depscope && .venv/bin/python scripts/migrate_alternatives.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncpg
from api.config import DATABASE_URL


# Nomi che non sono pacchetti installabili: stdlib, built-in lang, metodi, CLI flags.
_BUILTIN_EXACT: set[str] = {
    "URLSearchParams", "venv", "argparse", "unittest", "logging",
    "npm-scripts", "systemd", "beautifulsoup4",
}


def is_builtin(name: str) -> bool:
    """Un alternative e' 'builtin' se non e' un pacchetto installabile dal registry."""
    if not name:
        return False
    if name in _BUILTIN_EXACT:
        return True
    # metodi nativi / namespace (String.padStart, fs.rm, crypto.randomUUID, express.json, ruamel.yaml)
    # nota: ruamel.yaml e' pacchetto PyPI vero, gestito sotto
    if "." in name and name not in {"ruamel.yaml", "django-ninja"}:
        # euristica: se il primo segmento e' capitalizzato (classe) o sta in set globali -> builtin
        first = name.split(".")[0]
        if first and (first[0].isupper() or first in {"fs", "crypto", "express", "std", "os", "sys", "ruff"}):
            return True
    if "::" in name:
        return True
    if " " in name:  # "node --watch", "ruff format", "node --env-file"
        return True
    if name.startswith("native-"):
        return True
    if name.startswith("std::"):
        return True
    return False


# Source of truth: ricopiato da api/main.py _PACKAGE_ALTERNATIVES (1:1).
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


async def upsert_package(conn: asyncpg.Connection, ecosystem: str, name: str) -> int:
    """Restituisce l'id del pacchetto, inserendolo se manca. Idempotente."""
    row = await conn.fetchrow(
        """
        INSERT INTO packages (ecosystem, name) VALUES ($1, $2)
        ON CONFLICT (ecosystem, name) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
        """,
        ecosystem, name,
    )
    return row["id"]


async def main() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        stats = {"pairs": 0, "builtin": 0, "real_alt": 0, "new_packages": 0}
        packages_before = await conn.fetchval("SELECT COUNT(*) FROM packages")

        for eco, entries in _PACKAGE_ALTERNATIVES.items():
            for source_pkg, alts in entries.items():
                source_id = await upsert_package(conn, eco, source_pkg)

                for idx, alt in enumerate(alts):
                    alt_name = alt["name"]
                    reason = alt["reason"]
                    score = max(100 - idx * 10, 50)  # 100, 90, 80, ... min 50
                    builtin = is_builtin(alt_name)

                    if builtin:
                        alt_id = None
                        stats["builtin"] += 1
                    else:
                        alt_id = await upsert_package(conn, eco, alt_name)
                        stats["real_alt"] += 1

                    await conn.execute(
                        """
                        INSERT INTO alternatives
                          (package_id, alternative_package_id, alternative_name,
                           alternative_is_builtin, reason, score)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (package_id, alternative_name)
                        DO UPDATE SET
                          reason = EXCLUDED.reason,
                          score = EXCLUDED.score,
                          alternative_package_id = EXCLUDED.alternative_package_id,
                          alternative_is_builtin = EXCLUDED.alternative_is_builtin
                        """,
                        source_id, alt_id, alt_name, builtin, reason, score,
                    )
                    stats["pairs"] += 1

        packages_after = await conn.fetchval("SELECT COUNT(*) FROM packages")
        stats["new_packages"] = packages_after - packages_before
        alt_count = await conn.fetchval("SELECT COUNT(*) FROM alternatives")

        print(f"[OK] pairs inserted/updated: {stats['pairs']}")
        print(f"[OK] builtin alternatives:   {stats['builtin']}")
        print(f"[OK] real-package alts:      {stats['real_alt']}")
        print(f"[OK] new packages created:   {stats['new_packages']}")
        print(f"[OK] alternatives total now: {alt_count}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
