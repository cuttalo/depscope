"""Discover alternatives for deprecated packages.

Sources:
  1. `deprecated_message` from the registries themselves (npm and PyPI
     often point at the replacement directly).
  2. GitHub repo search: "successor of X" / "replacement for X".
  3. README of matching repos: look for sections like "Alternatives".

Insert into `alternatives` table, UPSERT on (package_id, alternative_name).
"""
import asyncio
import base64
import re
import time
from typing import Optional

import aiohttp

from scripts.ingest._common import (
    GITHUB_TOKEN,
    RateLimiter,
    get_db_pool,
    get_logger,
    http_get,
)

logger = get_logger("discover_alternatives")

MAX_ALT_PER_PACKAGE = 10
MIN_ALT_LEN = 2
MAX_ALT_LEN = 80

# `use PKG instead` / `migrate to PKG` etc.
_DEPRECATED_HINT_RES = [
    re.compile(r"use\s+`?([@\w\-./]+)`?\s+instead", re.I),
    re.compile(r"migrate\s+to\s+`?([@\w\-./]+)`?", re.I),
    re.compile(r"replaced?\s+by\s+`?([@\w\-./]+)`?", re.I),
    re.compile(r"superseded\s+by\s+`?([@\w\-./]+)`?", re.I),
    re.compile(r"switch\s+to\s+`?([@\w\-./]+)`?", re.I),
    re.compile(r"(?:renamed|moved)\s+to\s+`?([@\w\-./]+)`?", re.I),
    re.compile(r"now\s+available\s+at\s+`?([@\w\-./]+)`?", re.I),
    re.compile(r"has\s+moved\s+to\s+`?([@\w\-./]+)`?", re.I),
    re.compile(r"^([@\w\-./]+)$", re.M),  # bare package name on its own line
    # npm-deprecate messages often link directly: "Use X instead of Y"
    re.compile(r"install\s+(?:the\s+(?:latest\s+version\s+of)?\s+)?`?([@\w\-./]+)`?", re.I),
    re.compile(r"use\s+(?:the\s+)?`?([@\w\-./]+)`?\s+(?:package|module|library)", re.I),
    re.compile(r"see\s+(?:v\d+\+?\s+at\s+)?https?://[^\s]*?/(?:package|pkg)/([@\w\-./]+)", re.I),
    re.compile(r"npmjs\.com/(?:package|org|pkg)/(@?[@\w\-./]+)", re.I),
]

# Common stopwords we never want as "alternatives"
_BAD_NAMES = {
    "npm", "pip", "pypi", "git", "github", "node", "python", "rust",
    "go", "the", "this", "that", "here", "instead", "our", "their",
    "you", "your", "please", "thanks",
}


def extract_from_deprecated_msg(msg: str) -> list[str]:
    if not msg:
        return []
    out: list[str] = []
    for pat in _DEPRECATED_HINT_RES:
        for m in pat.finditer(msg):
            name = clean_name(m.group(1))
            if name:
                out.append(name)
    return list(dict.fromkeys(out))[:MAX_ALT_PER_PACKAGE]


def clean_name(n: str) -> Optional[str]:
    if not n:
        return None
    n = n.strip().strip(",.;:)(\"'`").lower()
    if not n or len(n) < MIN_ALT_LEN or len(n) > MAX_ALT_LEN:
        return None
    if n in _BAD_NAMES:
        return None
    # Must look like a package name
    if not re.match(r"^[@]?[a-z0-9][a-z0-9_\-./]*$", n):
        return None
    return n


def extract_from_readme(readme_text: str, source_pkg: str) -> list[str]:
    """Look for an `## Alternatives` section and list package names there."""
    if not readme_text:
        return []
    m = re.search(
        r"(?is)^\s*#+\s*(alternatives?|similar(?:\s+tools)?|related(?:\s+projects)?)\s*$(.*?)(?=^\s*#+\s|\Z)",
        readme_text,
        flags=re.M,
    )
    if not m:
        return []
    block = m.group(2)
    # Extract link labels & bare names
    names: list[str] = []
    for link in re.finditer(r"\[`?([@\w\-./]+)`?\]", block):
        name = clean_name(link.group(1))
        if name and name != source_pkg.lower():
            names.append(name)
    for inline in re.finditer(r"`([@\w\-./]+)`", block):
        name = clean_name(inline.group(1))
        if name and name != source_pkg.lower():
            names.append(name)
    return list(dict.fromkeys(names))[:MAX_ALT_PER_PACKAGE]


async def fetch_readme(
    session: aiohttp.ClientSession,
    owner: str,
    repo: str,
    headers: dict,
    limiter: RateLimiter,
) -> Optional[str]:
    await limiter.acquire()
    data = await http_get(
        session,
        f"https://api.github.com/repos/{owner}/{repo}/readme",
        headers=headers,
        logger=logger,
    )
    if not data or not isinstance(data, dict):
        return None
    content = data.get("content")
    if not content:
        return None
    try:
        return base64.b64decode(content.encode()).decode("utf-8", errors="ignore")
    except Exception:
        return None


async def github_search_repo(
    session: aiohttp.ClientSession,
    query: str,
    headers: dict,
    limiter: RateLimiter,
) -> list[dict]:
    await limiter.acquire()
    data = await http_get(
        session,
        "https://api.github.com/search/repositories",
        headers=headers,
        params={"q": query, "sort": "stars", "order": "desc", "per_page": 5},
        logger=logger,
    )
    if not data or not isinstance(data, dict):
        return []
    return data.get("items") or []


async def ensure_package(pool, ecosystem: str, name: str) -> Optional[int]:
    """Find or create a minimal package row so we can FK into alternatives."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM packages WHERE ecosystem=$1 AND name=$2",
            ecosystem,
            name,
        )
        if row:
            return row["id"]
        # Only create if it really looks legit; otherwise skip (FK optional)
        return None


async def insert_alternative(pool, pkg_id: int, alt_name: str, reason: str, score: int):
    async with pool.acquire() as conn:
        # Try to resolve alt_name to a known package id — optional.
        alt_row = await conn.fetchrow(
            "SELECT id FROM packages WHERE name=$1 ORDER BY downloads_weekly DESC NULLS LAST LIMIT 1",
            alt_name,
        )
        alt_pkg_id = alt_row["id"] if alt_row else None
        res = await conn.execute(
            """
            INSERT INTO alternatives(
                package_id, alternative_package_id, reason, score,
                alternative_name, alternative_is_builtin
            ) VALUES ($1, $2, $3, $4, $5, false)
            ON CONFLICT (package_id, alternative_name) DO UPDATE
              SET score = GREATEST(alternatives.score, EXCLUDED.score),
                  reason = COALESCE(EXCLUDED.reason, alternatives.reason)
            """,
            pkg_id,
            alt_pkg_id,
            reason[:500] if reason else None,
            max(0, min(100, score)),
            alt_name[:255],
        )
        return res and res.endswith("1")


async def process_package(
    session: aiohttp.ClientSession,
    pkg: dict,
    headers: dict,
    limiter: RateLimiter,
    pool,
) -> int:
    inserted = 0
    pkg_id = pkg["id"]
    pkg_name = pkg["name"]
    msg = pkg.get("deprecated_message") or ""

    # 1) From deprecated message
    for alt in extract_from_deprecated_msg(msg):
        if alt == pkg_name.lower():
            continue
        try:
            if await insert_alternative(
                pool, pkg_id, alt, f"Deprecation notice: use {alt}", 80
            ):
                inserted += 1
        except Exception as e:
            logger.warning(f"insert alt (dep) {pkg_name}->{alt}: {e}")

    # 2) GitHub search for successor / replacement
    queries = [
        f"replacement for {pkg_name}",
        f"successor of {pkg_name}",
        f"alternative to {pkg_name}",
    ]
    found_repos: list[tuple[str, str, int]] = []
    for q in queries:
        try:
            repos = await github_search_repo(session, q, headers, limiter)
        except Exception as e:
            logger.warning(f"repo search '{q}': {e}")
            continue
        for r in repos[:3]:
            full = r.get("full_name") or ""
            if "/" not in full:
                continue
            owner, repo = full.split("/", 1)
            if repo.lower() == pkg_name.lower():
                continue
            stars = int(r.get("stargazers_count") or 0)
            found_repos.append((owner, repo, stars))

    # 3) From top repos' README sections
    for owner, repo, stars in found_repos[:5]:
        readme = await fetch_readme(session, owner, repo, headers, limiter)
        names = extract_from_readme(readme or "", pkg_name)
        for alt in names:
            if alt == pkg_name.lower():
                continue
            score = min(90, 40 + stars // 200)
            try:
                if await insert_alternative(
                    pool,
                    pkg_id,
                    alt,
                    f"Mentioned as alternative in {owner}/{repo} README ({stars}★)",
                    score,
                ):
                    inserted += 1
            except Exception as e:
                logger.warning(f"insert alt (readme) {pkg_name}->{alt}: {e}")
        # Also: the repo itself is itself a candidate replacement
        repo_name = repo.lower()
        if (
            re.match(r"^[a-z0-9][a-z0-9_\-.]+$", repo_name)
            and repo_name != pkg_name.lower()
            and 2 <= len(repo_name) <= MAX_ALT_LEN
        ):
            score = min(85, 30 + stars // 500)
            try:
                if await insert_alternative(
                    pool,
                    pkg_id,
                    repo_name,
                    f"Suggested via GitHub search: {owner}/{repo} ({stars}★)",
                    score,
                ):
                    inserted += 1
            except Exception as e:
                logger.warning(f"insert alt (repo) {pkg_name}->{repo_name}: {e}")

    if inserted:
        logger.info(f"{pkg['ecosystem']}/{pkg_name}: +{inserted} alternatives")
    return inserted


async def load_deprecated_packages(pool) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, ecosystem, name, deprecated_message, downloads_weekly,
                   repository
            FROM packages
            WHERE deprecated = true
               OR deprecated_message IS NOT NULL
            ORDER BY downloads_weekly DESC NULLS LAST
            LIMIT 400
            """
        )
        return [dict(r) for r in rows]


# Awesome-lists shipped as markdown on raw.githubusercontent.com give us a
# rich source of `X is a replacement for Y` / `use X instead of Y`.
AWESOME_LISTS = [
    ("sindresorhus", "awesome-nodejs", "main", "readme.md"),
    ("vinta", "awesome-python", "master", "README.md"),
    ("rust-unofficial", "awesome-rust", "main", "README.md"),
    ("avelino", "awesome-go", "main", "README.md"),
    ("enaqx", "awesome-react", "master", "README.md"),
    ("vuejs", "awesome-vue", "master", "README.md"),
    ("sindresorhus", "awesome", "main", "readme.md"),
]

_AWESOME_REPLACEMENT_RES = [
    # "X is a modern alternative to Y"
    re.compile(r"\[`?([@\w\-./]+)`?\][^\n]{0,40}(?:alternative to|replacement for|successor of|replaces?)[^\n]{0,20}`?([@\w\-./]+)`?", re.I),
    # "Use X instead of Y"
    re.compile(r"use\s+`?([@\w\-./]+)`?\s+instead of\s+`?([@\w\-./]+)`?", re.I),
    # "X — a (drop-in) replacement for Y"
    re.compile(r"`([@\w\-./]+)`[^\n]{0,30}drop[- ]in replacement[^\n]{0,10}for\s+`?([@\w\-./]+)`?", re.I),
    # "Y has been deprecated — use X"
    re.compile(r"`?([@\w\-./]+)`?\s+(?:is|has been)\s+deprecated[^\n]{0,30}use\s+`?([@\w\-./]+)`?", re.I),
    # "Replaces Y"  (here order is swapped — first group is new, second old)
    re.compile(r"`([@\w\-./]+)`[^\n]{0,40}replaces?\s+`?([@\w\-./]+)`?", re.I),
]

# Well-known hand-curated replacement pairs. Strong signal, no parsing noise.
CURATED_PAIRS: list[tuple[str, str, str, str]] = [
    # (ecosystem, old_pkg, new_pkg, reason)
    ("npm", "request", "axios", "request is deprecated; axios is the modern drop-in"),
    ("npm", "request", "got", "request is deprecated; got is a popular successor"),
    ("npm", "request", "node-fetch", "request is deprecated; node-fetch for fetch-like API"),
    ("npm", "request-promise", "axios", "request-promise unmaintained"),
    ("npm", "body-parser", "express", "express >=4.16 has built-in body parsing"),
    ("npm", "tslint", "eslint", "tslint was deprecated in favour of eslint with @typescript-eslint"),
    ("npm", "node-sass", "sass", "node-sass deprecated; use Dart Sass"),
    ("npm", "istanbul", "nyc", "istanbul CLI moved to nyc"),
    ("npm", "gulp", "vite", "modern build pipelines use Vite / esbuild"),
    ("npm", "grunt", "vite", "Grunt largely superseded by Vite / esbuild"),
    ("npm", "bower", "npm", "Bower is retired; use npm"),
    ("npm", "moment", "dayjs", "moment is legacy; dayjs is smaller and API-compatible"),
    ("npm", "moment", "date-fns", "moment is legacy; date-fns is tree-shakable"),
    ("npm", "moment", "luxon", "moment is legacy; luxon from the same team"),
    ("npm", "lodash", "lodash-es", "prefer lodash-es for tree-shaking"),
    ("npm", "enzyme", "@testing-library/react", "enzyme abandoned; use Testing Library"),
    ("npm", "create-react-app", "vite", "create-react-app is unmaintained; Vite is the de-facto replacement"),
    ("npm", "mocha", "vitest", "vitest combines Jest-like DX with Vite speed"),
    ("npm", "redux", "@reduxjs/toolkit", "plain Redux replaced by Redux Toolkit"),
    ("npm", "react-redux", "@reduxjs/toolkit", "redux-toolkit ships the modern bindings"),
    ("npm", "gulp-uglify", "terser", "terser supports ES2015+ where uglify doesn't"),
    ("npm", "uglify-js", "terser", "terser supports ES2015+ where uglify doesn't"),
    ("npm", "deprecate", "util", "use util.deprecate from Node.js stdlib"),
    ("npm", "querystring", "url", "WHATWG URL + URLSearchParams in Node >= 10"),
    ("npm", "mkdirp", "fs", "fs.mkdir({recursive:true}) in Node >= 10"),
    ("npm", "rimraf", "fs", "fs.rm({recursive:true,force:true}) in Node >= 14"),
    ("npm", "xhr", "fetch", "fetch is standard since Node 18"),
    ("npm", "jsdom", "happy-dom", "happy-dom is faster for testing"),
    ("npm", "webpack", "vite", "Vite for dev speed and modern ESM"),
    ("npm", "webpack", "esbuild", "esbuild for raw build speed"),

    # pypi
    ("pypi", "distribute", "setuptools", "distribute merged back into setuptools"),
    ("pypi", "nose", "pytest", "nose is unmaintained; pytest is the de-facto replacement"),
    ("pypi", "nose2", "pytest", "pytest covers everything nose2 does"),
    ("pypi", "mock", "unittest.mock", "stdlib unittest.mock since Python 3.3"),
    ("pypi", "unittest2", "unittest", "backport unneeded since Python 3.5"),
    ("pypi", "enum34", "enum", "stdlib enum since Python 3.4"),
    ("pypi", "pathlib2", "pathlib", "stdlib pathlib since Python 3.4"),
    ("pypi", "configparser2", "configparser", "stdlib configparser"),
    ("pypi", "futures", "concurrent.futures", "stdlib since Python 3.2"),
    ("pypi", "ipaddress", "ipaddress", "stdlib since Python 3.3"),
    ("pypi", "dataclasses", "dataclasses", "stdlib since Python 3.7"),
    ("pypi", "importlib-metadata", "importlib.metadata", "stdlib since Python 3.8"),
    ("pypi", "typing-extensions", "typing", "most hints moved into stdlib typing"),
    ("pypi", "asyncio-nats-client", "nats-py", "renamed project"),
    ("pypi", "imp", "importlib", "imp removed in Python 3.12"),
    ("pypi", "cgi", "email.parser", "cgi removed in Python 3.13"),
    ("pypi", "django-rest-framework", "djangorestframework", "package is djangorestframework"),
    ("pypi", "PIL", "Pillow", "Pillow is the maintained fork of PIL"),
    ("pypi", "pillow-simd", "Pillow", "Pillow has SIMD since 9.2"),
    ("pypi", "pycrypto", "cryptography", "pycrypto is abandoned; use cryptography"),
    ("pypi", "pycrypto", "pycryptodome", "pycryptodome is the community fork"),
    ("pypi", "MySQL-python", "mysqlclient", "maintained successor"),
    ("pypi", "MySQL-python", "PyMySQL", "pure Python successor"),
    ("pypi", "psycopg2", "psycopg", "psycopg 3 is the current version"),
    ("pypi", "flask-restplus", "flask-restx", "maintained fork"),
    ("pypi", "requests-futures", "httpx", "httpx has native async"),
    ("pypi", "urllib3", "httpx", "httpx is higher-level"),
    ("pypi", "boto", "boto3", "boto is v1, use boto3"),
    ("pypi", "nose-exclude", "pytest", "use pytest collection filters"),
    ("pypi", "ipython-genutils", "jupyter-core", "upstream replacement"),
    ("pypi", "yaml", "PyYAML", "import name is yaml but package is PyYAML"),
    ("pypi", "google-cloud", "google-cloud-storage", "split packages per service"),
    ("pypi", "tqdm", "rich", "rich.progress also works and is more integrated"),
    ("pypi", "pylint", "ruff", "ruff is faster and covers most rules"),
    ("pypi", "flake8", "ruff", "ruff is faster and covers most rules"),
    ("pypi", "black", "ruff", "ruff format matches black formatting"),
    ("pypi", "isort", "ruff", "ruff handles import sorting"),

    # cargo
    ("cargo", "failure", "anyhow", "failure is unmaintained; anyhow is the successor"),
    ("cargo", "failure", "thiserror", "thiserror for libraries"),
    ("cargo", "error-chain", "anyhow", "error-chain is abandoned"),
    ("cargo", "rustc-serialize", "serde", "rustc-serialize is deprecated"),
    ("cargo", "time 0.1", "time", "time 0.3+ has sound API"),
    ("cargo", "time 0.1", "chrono", "chrono is a common alternative"),
    ("cargo", "reqwest-legacy", "reqwest", "use the current reqwest"),
    ("cargo", "futures 0.1", "futures", "futures 0.3 + async/await"),
    ("cargo", "tokio 0.1", "tokio", "tokio 1.x is the stable line"),
    ("cargo", "hyper 0.10", "hyper", "hyper 1.x"),
    ("cargo", "rust-openssl", "openssl", "current crate is openssl"),
    ("cargo", "rustls-native-certs", "rustls-platform-verifier", "platform-verifier is the modern choice"),
    ("cargo", "actix-web 1", "actix-web", "use actix-web 4"),
    ("cargo", "warp 0.2", "axum", "axum is the more idiomatic tokio framework today"),
    ("cargo", "rocket 0.4", "rocket", "rocket 0.5 stable"),

    # go
    ("go", "github.com/dgrijalva/jwt-go", "github.com/golang-jwt/jwt", "repo moved to golang-jwt org"),
    ("go", "github.com/pkg/errors", "errors", "stdlib errors since Go 1.13 supports wrapping"),
    ("go", "github.com/satori/go.uuid", "github.com/google/uuid", "go.uuid is unmaintained"),
    ("go", "github.com/dgraph-io/badger", "github.com/cockroachdb/pebble", "pebble is the modern KV"),
    ("go", "github.com/garyburd/redigo", "github.com/redis/go-redis", "redis/go-redis is the official client"),
    ("go", "github.com/go-redis/redis", "github.com/redis/go-redis", "project moved to redis org"),
    ("go", "github.com/sirupsen/logrus", "log/slog", "stdlib slog since Go 1.21"),
    ("go", "github.com/uber-go/zap", "log/slog", "stdlib slog since Go 1.21"),
    ("go", "github.com/lib/pq", "github.com/jackc/pgx", "pgx is more idiomatic"),
    ("go", "github.com/jinzhu/gorm", "gorm.io/gorm", "repo moved to gorm.io"),
    ("go", "github.com/BurntSushi/toml", "github.com/pelletier/go-toml", "pelletier is faster"),

    # npm — Hapi ecosystem migration (many "X is now @hapi/X" packages in DB)
    ("npm", "good-console", "@hapi/good-console", "moved under @hapi scope"),
    ("npm", "topo", "@hapi/topo", "moved under @hapi scope"),
    ("npm", "call", "@hapi/call", "moved under @hapi scope"),
    ("npm", "accept", "@hapi/accept", "moved under @hapi scope"),
    ("npm", "heavy", "@hapi/heavy", "moved under @hapi scope"),
    ("npm", "items", "@hapi/hoek", "replaced by hapi/hoek helpers"),
    ("npm", "hoek", "@hapi/hoek", "moved under @hapi scope"),
    ("npm", "joi", "@hapi/joi", "moved under @hapi scope"),
    ("npm", "boom", "@hapi/boom", "moved under @hapi scope"),
    ("npm", "catbox", "@hapi/catbox", "moved under @hapi scope"),
    ("npm", "podium", "@hapi/podium", "moved under @hapi scope"),
    ("npm", "subtext", "@hapi/subtext", "moved under @hapi scope"),
    ("npm", "nes", "@hapi/nes", "moved under @hapi scope"),
    ("npm", "wreck", "@hapi/wreck", "moved under @hapi scope"),
    ("npm", "good", "@hapi/good", "moved under @hapi scope"),
    ("npm", "lab", "@hapi/lab", "moved under @hapi scope"),

    # npm — lodash fragments replaced by optional chaining or stdlib
    ("npm", "lodash.get", "?.", "use optional chaining ?. (ES2020)"),
    ("npm", "lodash.set", "immer", "immer for immutable updates"),
    ("npm", "lodash.compose", "lodash.flowright", "renamed to flowright"),
    ("npm", "lodash.isequal", "fast-deep-equal", "smaller, faster"),
    ("npm", "lodash.merge", "deepmerge", "lighter alternative"),
    ("npm", "lodash.pick", "just-pick", "tree-shakable micro-package"),
    ("npm", "lodash.omit", "just-omit", "tree-shakable micro-package"),
    ("npm", "lodash.uniq", "Set", "use Array.from(new Set(x))"),

    # npm — renames / forks
    ("npm", "jade", "pug", "jade was renamed to pug"),
    ("npm", "node-uuid", "uuid", "node-uuid superseded by uuid"),
    ("npm", "pkg-conf", "package-config", "renamed"),
    ("npm", "bin-version-check", "binary-version-check", "renamed"),
    ("npm", "scmp", "crypto", "use crypto.timingSafeEqual"),
    ("npm", "node-domexception", "DOMException", "platform-native DOMException"),
    ("npm", "apollo-datasource", "@apollo/server", "Apollo Server v4"),
    ("npm", "apollo-server", "@apollo/server", "Apollo Server v4 rename"),
    ("npm", "apollo-server-express", "@apollo/server", "Apollo Server v4"),
    ("npm", "graphql-tools", "@graphql-tools/schema", "modular @graphql-tools"),
    ("npm", "graphql-import", "@graphql-tools/load", "deprecated, use @graphql-tools/load"),
    ("npm", "handlebars-helpers", "just-handlebars-helpers", "maintained fork"),
    ("npm", "react-native-image-resizer", "@bam.tech/react-native-image-resizer", "moved to @bam.tech"),
    ("npm", "request-promise-native", "axios", "request family deprecated"),
    ("npm", "request-promise-any", "axios", "request family deprecated"),
    ("npm", "@types/chalk", "chalk", "chalk ships its own types"),
    ("npm", "@types/prettier", "prettier", "prettier ships its own types"),
    ("npm", "stable", "Array.prototype.sort", "sort is stable since ES2019"),
    ("npm", "core-util-is", "util.types", "built-in util.types"),
    ("npm", "left-pad", "String.prototype.padStart", "native since ES2017"),
    ("npm", "object.assign", "Object.assign", "native since ES2015"),
    ("npm", "array-flatten", "Array.prototype.flat", "native since ES2019"),
    ("npm", "is-buffer", "Buffer.isBuffer", "use built-in Buffer.isBuffer"),
    ("npm", "assert-plus", "assert", "stdlib assert is fine"),
    ("npm", "formidable", "busboy", "busboy is the modern choice"),
    ("npm", "multer", "formidable", "alternative multipart parser"),
    ("npm", "connect", "express", "express ships the same middleware system"),
    ("npm", "har-validator", "ajv", "use ajv with the HAR schema"),
    ("npm", "debug", "pino", "pino has debug-style logging built-in"),
    ("npm", "winston", "pino", "pino is faster and JSON by default"),
    ("npm", "qs", "URLSearchParams", "native since Node 10"),
    ("npm", "querystring-es3", "URLSearchParams", "native since Node 10"),
    ("npm", "url-parse", "URL", "native WHATWG URL"),
    ("npm", "buffer", "Buffer", "stdlib Buffer"),
    ("npm", "stream-browserify", "readable-stream", "use readable-stream"),
    ("npm", "util-deprecate", "util", "util.deprecate is built-in"),
    ("npm", "es6-promise", "Promise", "Promise is native since ES2015"),
    ("npm", "native-promise-only", "Promise", "Promise is native since ES2015"),
    ("npm", "isarray", "Array.isArray", "native since ES5"),
    ("npm", "inherits", "util.inherits", "util.inherits is built-in"),
    ("npm", "process", "process", "global process object in Node"),
    ("npm", "core-js", "modern browsers", "most polyfills unnecessary in 2024"),
    ("npm", "babel-polyfill", "core-js/stable", "split into core-js/stable + regenerator-runtime"),
    ("npm", "regenerator-runtime", "async/await", "native async in Node 8+"),
    ("npm", "babel-preset-env", "@babel/preset-env", "moved under @babel scope"),
    ("npm", "babel-core", "@babel/core", "moved under @babel scope"),
    ("npm", "babel-preset-stage-0", "@babel/preset-env", "stage presets removed in Babel 7"),
    ("npm", "babel-preset-stage-1", "@babel/preset-env", "stage presets removed in Babel 7"),
    ("npm", "babel-preset-stage-2", "@babel/preset-env", "stage presets removed in Babel 7"),
    ("npm", "babel-preset-stage-3", "@babel/preset-env", "stage presets removed in Babel 7"),
    ("npm", "gulp-babel", "@babel/register", "run babel via Node directly"),
    ("npm", "eslint-config-airbnb-base", "@eslint/js", "flat config replacements"),
    ("npm", "jquery", "vanilla JS", "browser APIs cover most jQuery use cases"),
    ("npm", "zepto", "vanilla JS", "zepto is unmaintained"),
    ("npm", "backbone", "react", "modern framework"),
    ("npm", "ember", "react", "modern framework"),
    ("npm", "angular", "@angular/core", "AngularJS (1.x) is EOL; use modern Angular"),
    ("npm", "meteor", "next.js", "meteor community dwindled"),
    ("npm", "coffeescript", "typescript", "CoffeeScript is largely dormant"),
    ("npm", "bluebird", "Promise", "native Promises since Node 4"),
    ("npm", "q", "Promise", "native Promises since Node 4"),
    ("npm", "when", "Promise", "native Promises since Node 4"),
    ("npm", "async", "async/await", "native since Node 8"),

    # pypi — more replacements
    ("pypi", "MySQL-python", "mysqlclient", "maintained successor"),
    ("pypi", "South", "django.db.migrations", "stdlib Django migrations since 1.7"),
    ("pypi", "django-south", "django.db.migrations", "stdlib Django migrations since 1.7"),
    ("pypi", "raven", "sentry-sdk", "raven renamed sentry-sdk"),
    ("pypi", "airtable-python-wrapper", "pyairtable", "community-maintained fork"),
    ("pypi", "pymc3", "pymc", "project renamed pymc"),
    ("pypi", "tensorflow-gpu", "tensorflow", "tf 2.x auto-detects GPU"),
    ("pypi", "keras-contrib", "keras", "merged into keras"),
    ("pypi", "pillow-simd", "pillow", "upstream has SIMD since 9.2"),
    ("pypi", "fake-factory", "faker", "fake-factory renamed faker"),
    ("pypi", "python-magic", "filetype", "filetype is pure-Python"),
    ("pypi", "simplejson", "json", "stdlib json is fast enough"),
    ("pypi", "ujson", "orjson", "orjson is faster"),
    ("pypi", "ipy", "ipaddress", "stdlib ipaddress since Py 3.3"),
    ("pypi", "backports.ssl_match_hostname", "ssl", "stdlib ssl"),
    ("pypi", "python-dateutil", "datetime", "use datetime + zoneinfo for most cases"),
    ("pypi", "pytz", "zoneinfo", "stdlib zoneinfo since Py 3.9"),
    ("pypi", "pytz-deprecation-shim", "zoneinfo", "stdlib zoneinfo since Py 3.9"),
    ("pypi", "backports.zoneinfo", "zoneinfo", "stdlib since Py 3.9"),
    ("pypi", "backports.entry_points_selectable", "importlib.metadata", "stdlib since Py 3.10"),
    ("pypi", "toml", "tomllib", "tomllib in stdlib since Py 3.11"),
    ("pypi", "iso8601", "datetime", "datetime.fromisoformat in stdlib"),
    ("pypi", "crcmod", "zlib", "stdlib zlib.crc32"),
    ("pypi", "ordereddict", "dict", "dict preserves insertion order since Py 3.7"),
    ("pypi", "funcsigs", "inspect", "stdlib inspect.signature since Py 3.3"),
    ("pypi", "scandir", "os", "os.scandir in stdlib since Py 3.5"),
    ("pypi", "subprocess32", "subprocess", "stdlib since Py 3.2"),
    ("pypi", "statistics", "statistics", "stdlib since Py 3.4"),
    ("pypi", "coveragepy", "coverage", "project is just `coverage`"),
    ("pypi", "Flask-Script", "flask.cli", "Flask has a built-in CLI since 1.0"),
    ("pypi", "Flask-Security", "Flask-Security-Too", "maintained fork"),
    ("pypi", "Flask-OAuthlib", "authlib", "authlib is actively maintained"),
    ("pypi", "Flask-Admin", "Flask-AppBuilder", "richer alternative"),
    ("pypi", "pyOpenSSL", "cryptography", "cryptography replaces pyOpenSSL for new code"),
    ("pypi", "gevent", "asyncio", "asyncio is stdlib"),
    ("pypi", "eventlet", "asyncio", "asyncio is stdlib"),
    ("pypi", "Twisted", "asyncio", "asyncio is stdlib"),
    ("pypi", "rauth", "requests-oauthlib", "rauth unmaintained"),
    ("pypi", "suds", "zeep", "maintained SOAP client"),
    ("pypi", "paramiko", "asyncssh", "asyncssh has an async API"),
    ("pypi", "PyVirtualDisplay", "xvfb", "use Xvfb directly"),
    ("pypi", "python-binance", "binance-connector", "official client"),

    # cargo — more
    ("cargo", "stdweb", "wasm-bindgen", "stdweb unmaintained"),
    ("cargo", "quicli", "clap", "quicli sunset; clap is the standard"),
    ("cargo", "structopt", "clap", "structopt merged into clap 3"),
    ("cargo", "gotham", "axum", "gotham no longer maintained"),
    ("cargo", "iron", "axum", "iron no longer maintained"),
    ("cargo", "nickel", "axum", "nickel no longer maintained"),
    ("cargo", "openssl-probe", "rustls-platform-verifier", "modern replacement"),
    ("cargo", "lazy_static", "once_cell", "once_cell is canonical"),
    ("cargo", "once_cell", "std::sync::OnceLock", "stdlib since 1.70"),
    ("cargo", "crossbeam-channel", "std::sync::mpsc", "stdlib mpsc is enough for many cases"),
    ("cargo", "chrono-tz", "chrono", "chrono has limited tz support in later versions"),
    ("cargo", "hyper-tls", "rustls", "rustls is pure-Rust"),
    ("cargo", "native-tls", "rustls", "rustls is pure-Rust"),
    ("cargo", "futures-cpupool", "tokio::task", "tokio::task::spawn_blocking"),
    ("cargo", "futures-timer", "tokio::time", "tokio::time::sleep"),
    ("cargo", "tokio-rustls", "tokio-rustls", "current crate"),
    ("cargo", "tokio-io", "tokio::io", "merged into tokio"),
    ("cargo", "tokio-tcp", "tokio::net", "merged into tokio"),
    ("cargo", "tokio-process", "tokio::process", "merged into tokio"),
    ("cargo", "tokio-signal", "tokio::signal", "merged into tokio"),
    ("cargo", "tokio-fs", "tokio::fs", "merged into tokio"),
    ("cargo", "tokio-core", "tokio::runtime", "core merged into tokio"),
    ("cargo", "tokio-reactor", "tokio::runtime", "merged into tokio"),
    ("cargo", "tokio-timer", "tokio::time", "merged into tokio"),
    ("cargo", "tokio-executor", "tokio::runtime", "merged into tokio"),
    ("cargo", "tokio-codec", "tokio_util::codec", "moved to tokio_util"),
    ("cargo", "tokio-threadpool", "tokio::runtime", "merged into tokio"),
    ("cargo", "tokio-uds", "tokio::net::UnixStream", "merged into tokio"),
    ("cargo", "hyper-tls", "reqwest", "reqwest bundles TLS"),
    ("cargo", "hyper-openssl", "reqwest", "reqwest bundles TLS"),
    ("cargo", "rand_core 0.4", "rand", "rand 0.8 is the stable line"),
    ("cargo", "rand_xorshift", "rand_pcg", "pcg is the recommended fast PRNG"),
    ("cargo", "term", "termion", "termion is maintained"),
    ("cargo", "term", "crossterm", "crossterm is cross-platform"),
    ("cargo", "ncurses", "ratatui", "ratatui for TUIs"),
    ("cargo", "tui", "ratatui", "tui renamed to ratatui"),
    ("cargo", "rustc-hash", "ahash", "ahash for general hashing"),
    ("cargo", "fnv", "ahash", "ahash is often faster"),
    ("cargo", "siphasher", "ahash", "ahash is usually the right default"),
    ("cargo", "mio-extras", "mio", "merged upstream"),

    # go — more
    ("go", "github.com/kelseyhightower/envconfig", "github.com/caarlos0/env", "env is more active"),
    ("go", "github.com/spf13/viper", "github.com/knadh/koanf", "koanf is simpler"),
    ("go", "github.com/astaxie/beego", "github.com/gin-gonic/gin", "gin is modern and popular"),
    ("go", "github.com/revel/revel", "github.com/gin-gonic/gin", "revel is inactive"),
    ("go", "github.com/go-sql-driver/mysql", "github.com/jackc/pgx", "pgx if you migrate to Postgres"),
    ("go", "github.com/go-xorm/xorm", "gorm.io/gorm", "xorm renamed; gorm is more popular"),
    ("go", "github.com/codegangsta/negroni", "github.com/gorilla/mux", "mux/net/http is enough"),
    ("go", "github.com/gorilla/mux", "net/http.ServeMux", "ServeMux grew patterns in Go 1.22"),
    ("go", "github.com/pressly/goose", "github.com/golang-migrate/migrate", "migrate has broader driver support"),
    ("go", "github.com/rubenv/sql-migrate", "github.com/golang-migrate/migrate", "migrate is more active"),
    ("go", "github.com/spf13/cobra", "github.com/urfave/cli", "urfave/cli is simpler"),
    ("go", "github.com/kardianos/service", "github.com/judwhite/go-svc", "go-svc is cleaner"),
    ("go", "github.com/robfig/cron", "github.com/go-co-op/gocron", "gocron has better API"),
    ("go", "github.com/deckarep/golang-set", "map[T]struct{}", "idiomatic Go sets"),
    ("go", "github.com/huandu/xstrings", "strings", "stdlib strings has almost everything"),
    ("go", "github.com/leodido/go-urn", "net/url", "stdlib url parses URNs"),
    ("go", "github.com/google/uuid", "crypto/rand", "use crypto/rand for random bytes"),
    ("go", "github.com/dgrijalva/jwt-go/v4", "github.com/golang-jwt/jwt/v5", "repo moved and renamed"),
]


async def fetch_awesome_list(
    session: aiohttp.ClientSession,
    entry: tuple[str, str, str, str],
    raw_limiter: RateLimiter,
) -> Optional[str]:
    owner, repo, branch, path = entry
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    await raw_limiter.acquire()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=25)) as resp:
            if resp.status == 200:
                return await resp.text()
    except Exception as e:
        logger.warning(f"awesome fetch {owner}/{repo}: {e}")
    return None


async def _resolve_package_id(
    pool, ecosystem_hint: Optional[str], name: str
) -> Optional[int]:
    async with pool.acquire() as conn:
        if ecosystem_hint:
            row = await conn.fetchrow(
                "SELECT id FROM packages WHERE ecosystem=$1 AND name=$2",
                ecosystem_hint, name,
            )
            if row:
                return row["id"]
        row = await conn.fetchrow(
            "SELECT id FROM packages WHERE name=$1 "
            "ORDER BY downloads_weekly DESC NULLS LAST LIMIT 1",
            name,
        )
        return row["id"] if row else None


async def process_awesome_lists(
    session: aiohttp.ClientSession,
    raw_limiter: RateLimiter,
    pool,
) -> int:
    """Parse awesome-* curated lists for 'X replaces Y' patterns."""
    inserted = 0
    for entry in AWESOME_LISTS:
        text = await fetch_awesome_list(session, entry, raw_limiter)
        if not text:
            continue
        eco_hint = None
        repo_lower = entry[1].lower()
        if "python" in repo_lower:
            eco_hint = "pypi"
        elif "nodejs" in repo_lower or "react" in repo_lower or "vue" in repo_lower:
            eco_hint = "npm"
        elif "rust" in repo_lower:
            eco_hint = "cargo"
        elif "go" in repo_lower:
            eco_hint = "go"

        for pat in _AWESOME_REPLACEMENT_RES:
            for m in pat.finditer(text):
                new_name = clean_name(m.group(1))
                old_name = clean_name(m.group(2))
                if not new_name or not old_name or new_name == old_name:
                    continue
                old_id = await _resolve_package_id(pool, eco_hint, old_name)
                if not old_id:
                    continue
                try:
                    if await insert_alternative(
                        pool,
                        old_id,
                        new_name,
                        f"Listed as alternative in {entry[0]}/{entry[1]}",
                        70,
                    ):
                        inserted += 1
                except Exception as e:
                    logger.warning(f"insert awesome alt {old_name}->{new_name}: {e}")
    if inserted:
        logger.info(f"awesome-lists: +{inserted} alternatives")
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

        limiter = RateLimiter(max_calls=1, period=2.0)
        raw_limiter = RateLimiter(max_calls=2, period=1.0)

        before = await pool.fetchval("SELECT COUNT(*) FROM alternatives")
        total = 0

        # 1a) Curated pairs — strong ground truth, no network
        for eco, old_pkg, new_pkg, reason in CURATED_PAIRS:
            old_id = await _resolve_package_id(pool, eco, old_pkg)
            if not old_id:
                # Create a minimal package row so we can attach the alternative
                try:
                    async with pool.acquire() as conn:
                        row = await conn.fetchrow(
                            """
                            INSERT INTO packages(ecosystem, name, deprecated)
                            VALUES ($1, $2, true)
                            ON CONFLICT (ecosystem, name) DO UPDATE
                              SET deprecated = true
                            RETURNING id
                            """,
                            eco, old_pkg,
                        )
                        old_id = row["id"] if row else None
                except Exception as e:
                    logger.warning(f"create package {eco}/{old_pkg}: {e}")
                    continue
            try:
                if await insert_alternative(pool, old_id, new_pkg, reason, 90):
                    total += 1
            except Exception as e:
                logger.warning(
                    f"curated alt {old_pkg}->{new_pkg}: {e}"
                )

        async with aiohttp.ClientSession() as session:
            # 1b) Awesome lists (no GitHub API quota)
            try:
                total += await process_awesome_lists(session, raw_limiter, pool)
            except Exception as e:
                logger.warning(f"awesome lists failed: {e}")

            # 2) Check remaining GitHub quota before the expensive search path
            gh_remaining = 0
            gh_search_remaining = 0
            rl = await http_get(
                session, "https://api.github.com/rate_limit",
                headers=headers, logger=logger,
            )
            if isinstance(rl, dict):
                gh_remaining = int(
                    (rl.get("resources") or {}).get("core", {}).get("remaining") or 0
                )
                gh_search_remaining = int(
                    (rl.get("resources") or {}).get("search", {}).get("remaining") or 0
                )
            logger.info(
                f"discover_alternatives: core={gh_remaining} "
                f"search={gh_search_remaining}"
            )

            pkgs = await load_deprecated_packages(pool)
            logger.info(
                f"discover_alternatives: {len(pkgs)} deprecated candidates"
            )

            # 3) Deprecation-message-only extraction is always safe (no API)
            for pkg in pkgs:
                msg = pkg.get("deprecated_message") or ""
                for alt in extract_from_deprecated_msg(msg):
                    if alt == pkg["name"].lower():
                        continue
                    try:
                        if await insert_alternative(
                            pool, pkg["id"], alt,
                            f"Deprecation notice: use {alt}", 80,
                        ):
                            total += 1
                    except Exception as e:
                        logger.warning(
                            f"dep-msg alt {pkg['name']}->{alt}: {e}"
                        )

            # 4) GitHub search fallback — only if we have headroom
            if gh_search_remaining >= 3 and gh_remaining >= 5:
                budget_search = max(0, gh_search_remaining - 2)
                budget_core = max(0, gh_remaining - 5)
                for i, pkg in enumerate(pkgs, 1):
                    if budget_search < 3 or budget_core < 2:
                        logger.info(
                            "discover_alternatives: gh budget exhausted"
                        )
                        break
                    try:
                        delta = await process_package(
                            session, pkg, headers, limiter, pool
                        )
                        total += delta
                        budget_search -= 3
                        budget_core -= 5  # readme fetches per repo
                    except Exception as e:
                        logger.warning(f"search pkg {pkg.get('name')}: {e}")
                    if i % 20 == 0:
                        logger.info(
                            f"discover_alternatives progress: {i}/{len(pkgs)}, +{total}"
                        )

        after = await pool.fetchval("SELECT COUNT(*) FROM alternatives")
        logger.info(
            f"discover_alternatives done: +{total} ({before} -> {after}) "
            f"in {time.time()-start:.1f}s"
        )
        return total
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
