"""Expand PyPI and Cargo massively"""
import asyncio
import aiohttp
import sys
import time

sys.path.insert(0, "/home/deploy/depscope")
from api.registries import fetch_package, fetch_vulnerabilities, save_package_to_db
from api.health import calculate_health_score
from api.cache import cache_set

# Top PyPI packages by category — comprehensive list
PYPI_PACKAGES = [
    # Web frameworks
    "django", "flask", "fastapi", "tornado", "bottle", "pyramid", "falcon", "starlette", "sanic", "aiohttp",
    "django-rest-framework", "django-ninja", "flask-restful", "connexion", "responder",
    # Data science
    "numpy", "pandas", "scipy", "matplotlib", "seaborn", "plotly", "bokeh", "altair",
    "scikit-learn", "xgboost", "lightgbm", "catboost", "statsmodels",
    "jupyter", "notebook", "jupyterlab", "ipython", "nbconvert",
    # AI/ML
    "tensorflow", "torch", "keras", "transformers", "datasets", "tokenizers",
    "openai", "anthropic", "langchain", "langchain-core", "langchain-community",
    "llama-index", "chromadb", "pinecone-client", "weaviate-client",
    "diffusers", "accelerate", "peft", "trl", "bitsandbytes",
    "mlflow", "wandb", "optuna", "ray", "dask",
    "huggingface-hub", "safetensors", "sentencepiece", "tiktoken",
    "gradio", "streamlit", "panel", "voila",
    # HTTP/Networking
    "requests", "httpx", "urllib3", "aiohttp", "httplib2", "treq",
    "grpcio", "protobuf", "thrift", "zeromq", "pyzmq",
    "websockets", "websocket-client", "socketio",
    # Database
    "sqlalchemy", "psycopg2-binary", "pymongo", "redis", "motor",
    "asyncpg", "aiomysql", "aiosqlite", "databases",
    "peewee", "tortoise-orm", "mongoengine", "pymysql",
    "alembic", "migrate", "prisma",
    "elasticsearch", "opensearch-py",
    # DevOps/Cloud
    "boto3", "botocore", "google-cloud-storage", "azure-storage-blob",
    "docker", "kubernetes", "ansible", "fabric", "paramiko",
    "terraform-provider", "pulumi",
    # CLI
    "click", "typer", "argparse", "fire", "docopt", "cement",
    "rich", "tqdm", "colorama", "blessed", "prompt-toolkit",
    # Testing
    "pytest", "unittest2", "nose2", "coverage", "pytest-cov",
    "pytest-asyncio", "pytest-mock", "pytest-xdist", "hypothesis",
    "mock", "responses", "vcrpy", "factory-boy", "faker",
    "selenium", "playwright", "pyppeteer",
    # Linting/Formatting
    "ruff", "black", "flake8", "pylint", "mypy", "pyright",
    "isort", "autopep8", "yapf", "bandit", "safety",
    # Serialization
    "pydantic", "marshmallow", "attrs", "dataclasses-json", "cattrs",
    "orjson", "ujson", "msgpack", "avro", "fastavro",
    "pyyaml", "toml", "tomli", "configparser",
    # Auth/Security
    "cryptography", "pyjwt", "passlib", "bcrypt", "python-jose",
    "authlib", "oauthlib", "python-social-auth",
    "certifi", "ssl", "pyopenssl",
    # Task queues
    "celery", "dramatiq", "huey", "arq", "rq",
    "kombu", "vine", "billiard",
    # Image/Media
    "pillow", "opencv-python", "scikit-image", "imageio",
    "ffmpeg-python", "moviepy", "pydub",
    # PDF/Docs
    "reportlab", "pypdf", "pdfplumber", "python-docx", "openpyxl",
    "xlsxwriter", "tabulate", "jinja2", "mako",
    # Scraping
    "beautifulsoup4", "scrapy", "lxml", "parsel", "selectolax",
    "playwright", "selenium", "httpx",
    # Async
    "asyncio", "anyio", "trio", "uvloop", "aiofiles",
    "aiocache", "aioredis", "aiobotocore",
    # Logging/Monitoring
    "loguru", "structlog", "python-json-logger",
    "sentry-sdk", "newrelic", "datadog", "prometheus-client",
    # Utils
    "python-dotenv", "python-decouple", "environs",
    "arrow", "pendulum", "python-dateutil", "pytz",
    "pathlib2", "more-itertools", "toolz", "funcy",
    "tenacity", "backoff", "retrying",
    "cachetools", "diskcache", "dogpile.cache",
    "regex", "chardet", "charset-normalizer",
    "packaging", "setuptools", "wheel", "pip", "pipx",
    "poetry", "pdm", "hatch", "flit",
    "virtualenv", "tox", "nox",
    # Types
    "typing-extensions", "types-requests", "types-pyyaml",
    "mypy-extensions", "typeguard",
]

# Comprehensive Cargo crates
CARGO_CRATES = [
    # Async runtime
    "tokio", "async-std", "smol", "futures", "futures-util",
    # Web frameworks
    "actix-web", "axum", "rocket", "warp", "tide", "poem", "salvo",
    "hyper", "tower", "tower-http",
    # Serialization
    "serde", "serde_json", "serde_yaml", "toml", "ron",
    "bincode", "postcard", "ciborium", "rmp-serde",
    # CLI
    "clap", "structopt", "argh", "pico-args",
    "indicatif", "dialoguer", "console", "colored", "termcolor",
    # Error handling
    "anyhow", "thiserror", "eyre", "color-eyre", "miette",
    # Logging
    "log", "env_logger", "tracing", "tracing-subscriber", "slog",
    # Database
    "sqlx", "diesel", "sea-orm", "rusqlite", "deadpool",
    "redis", "mongodb", "elasticsearch",
    # HTTP client
    "reqwest", "ureq", "isahc", "surf",
    # Crypto
    "ring", "rustls", "openssl", "sha2", "aes", "rand",
    "argon2", "bcrypt", "ed25519-dalek",
    # Parsing
    "regex", "nom", "pest", "lalrpop", "tree-sitter",
    # File/IO
    "tokio-fs", "walkdir", "globset", "notify", "tempfile",
    "zip", "tar", "flate2", "zstd", "lz4",
    # Data structures
    "bytes", "smallvec", "arrayvec", "indexmap", "dashmap",
    "crossbeam", "rayon", "parking_lot",
    # Config
    "config", "figment", "dotenvy",
    # Testing
    "proptest", "quickcheck", "mockall", "wiremock", "httpmock",
    # UUID/Time
    "uuid", "chrono", "time",
    # Encoding
    "base64", "hex", "url", "percent-encoding",
    # System
    "nix", "libc", "winapi", "sysinfo", "num_cpus",
    # Networking
    "tonic", "prost", "tarpc", "capnp",
    "socket2", "trust-dns", "hickory-dns",
    # TLS
    "native-tls", "rustls", "rustls-pemfile", "webpki",
    # Template
    "tera", "askama", "handlebars", "minijinja",
    # Macros
    "proc-macro2", "syn", "quote", "darling",
    # Utils
    "once_cell", "lazy_static", "strum", "derive_more", "itertools",
    "semver", "bitflags", "either", "num", "ordered-float",
    "memmap2", "memchr", "aho-corasick",
]

async def process(eco, name, processed):
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
        return True
    except:
        return False

async def main():
    import asyncpg
    conn = await asyncpg.connect("postgresql://depscope:${DB_PASSWORD}@localhost:5432/depscope")
    rows = await conn.fetch("SELECT ecosystem, name FROM packages")
    processed = set(f"{r['ecosystem']}:{r['name']}" for r in rows)
    await conn.close()
    
    print(f"Existing: {len(processed)}")
    total = 0
    
    # PyPI
    new_pypi = [p for p in PYPI_PACKAGES if f"pypi:{p}" not in processed]
    print(f"\nPyPI: {len(new_pypi)} new to add")
    for i, name in enumerate(new_pypi):
        ok = await process("pypi", name, processed)
        if ok: total += 1
        if (i+1) % 20 == 0:
            print(f"  PyPI {i+1}/{len(new_pypi)}, +{total}")
        await asyncio.sleep(0.5)
    
    # Cargo
    new_cargo = [c for c in CARGO_CRATES if f"cargo:{c}" not in processed]
    print(f"\nCargo: {len(new_cargo)} new to add")
    for i, name in enumerate(new_cargo):
        ok = await process("cargo", name, processed)
        if ok: total += 1
        if (i+1) % 20 == 0:
            print(f"  Cargo {i+1}/{len(new_cargo)}, +{total}")
        await asyncio.sleep(1)
    
    print(f"\nDone: +{total} packages added")

asyncio.run(main())
