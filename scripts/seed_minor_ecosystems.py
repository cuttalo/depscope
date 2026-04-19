"""Seed top packages for minor ecosystems:
pub, hex, swift, cocoapods, cpan, hackage, cran, conda, homebrew.

Idempotent: ON CONFLICT DO UPDATE. Graceful fail per package.
Rate limit: 1s sleep between calls.

Run from /home/deploy/depscope with:
    .venv/bin/python scripts/seed_minor_ecosystems.py
"""
import asyncio
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, "/home/deploy/depscope")

from api.registries import fetch_package, fetch_vulnerabilities, save_package_to_db
from api.health import calculate_health_score
from api.cache import cache_set


LOG_FILE = "/var/log/depscope/enrich_minor.log"


def log(msg: str):
    line = f"[{datetime.utcnow().isoformat()}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


# Top packages per ecosystem (curated from registry stats + GitHub stars)

TOP_PACKAGES = {
    # Dart/Flutter - top 100 from pub.dev (stars + downloads)
    "pub": [
        "http", "provider", "shared_preferences", "path", "dio", "bloc",
        "flutter_bloc", "get", "intl", "cupertino_icons", "go_router",
        "url_launcher", "image_picker", "cached_network_image", "riverpod",
        "flutter_riverpod", "hooks_riverpod", "flutter_hooks", "path_provider",
        "firebase_core", "firebase_auth", "cloud_firestore", "firebase_storage",
        "firebase_messaging", "firebase_analytics", "flutter_local_notifications",
        "connectivity_plus", "permission_handler", "sqflite", "hive",
        "hive_flutter", "flutter_secure_storage", "shared_preferences_web",
        "equatable", "freezed", "freezed_annotation", "json_annotation",
        "json_serializable", "build_runner", "flutter_dotenv", "logger",
        "fluttertoast", "flutter_svg", "webview_flutter", "video_player",
        "chewie", "file_picker", "image_cropper", "photo_view",
        "carousel_slider", "flutter_spinkit", "shimmer", "lottie",
        "animations", "flutter_animate", "stream_chat_flutter",
        "getx", "mobx", "flutter_mobx", "injectable", "get_it",
        "auto_route", "flutter_native_splash", "package_info_plus",
        "device_info_plus", "battery_plus", "geolocator", "google_maps_flutter",
        "flutter_polyline_points", "table_calendar", "syncfusion_flutter_charts",
        "fl_chart", "charts_flutter", "pdf", "printing", "share_plus",
        "flutter_inappwebview", "in_app_purchase", "google_sign_in",
        "sign_in_with_apple", "flutter_facebook_auth", "crypto",
        "pointycastle", "encrypt", "rxdart", "stream_transform",
        "async", "collection", "meta", "vector_math", "ffi",
        "dart_style", "analyzer", "source_gen", "build",
        "flutter_launcher_icons", "flutter_tts", "speech_to_text",
        "camera", "qr_code_scanner", "mobile_scanner", "local_auth",
    ],

    # Elixir/Hex - top 100 from hex.pm
    "hex": [
        "ecto", "phoenix", "plug", "absinthe", "phoenix_live_view",
        "phoenix_html", "phoenix_pubsub", "phoenix_ecto", "telemetry",
        "jason", "tesla", "httpoison", "poison", "cowboy", "ranch",
        "gettext", "gen_stage", "flow", "broadway", "oban",
        "quantum", "tzdata", "timex", "decimal", "nimble_parsec",
        "earmark", "ex_doc", "credo", "dialyxir", "sobelow",
        "bcrypt_elixir", "argon2_elixir", "guardian", "comeonin",
        "pow", "phoenix_swoosh", "swoosh", "bamboo", "redix",
        "cachex", "con_cache", "mongodb_driver", "postgrex", "myxql",
        "ex_machina", "mock", "mox", "mimic", "stream_data",
        "wallaby", "hound", "phoenix_live_reload", "phoenix_live_dashboard",
        "phoenix_view", "phoenix_template", "floki", "html_entities",
        "scrivener_ecto", "scrivener_html", "ex_aws", "ex_aws_s3",
        "ex_aws_sqs", "ex_aws_lambda", "ex_aws_ses", "hackney",
        "finch", "mint", "castore", "req", "certifi",
        "ssl_verify_fun", "idna", "telemetry_metrics", "telemetry_poller",
        "prometheus_ex", "prometheus_phoenix", "logger_file_backend",
        "logger_json", "sentry", "appsignal", "new_relic_agent",
        "kafka_ex", "amqp", "exq", "que", "toniq",
        "nebulex", "ecto_sql", "ecto_psql_extras", "surface",
        "live_select", "live_view_native", "makeup", "makeup_elixir",
        "earmark_parser", "esbuild", "tailwind", "phoenix_live_react",
    ],

    # Swift - top packages from GitHub (swift language + stars)
    "swift": [
        "Alamofire", "SwiftyJSON", "SnapKit", "Kingfisher", "SDWebImage",
        "Charts", "RxSwift", "realm-swift", "SwiftLint", "Vapor",
        "swift-nio", "swift-package-manager", "swift-syntax", "swift-format",
        "swift-argument-parser", "swift-log", "swift-collections",
        "swift-algorithms", "swift-numerics", "swift-crypto", "swift-system",
        "swift-metrics", "swift-async-algorithms", "swift-distributed-actors",
        "swift-foundation", "swift-http-types", "swift-openapi-generator",
        "swift-openapi-runtime", "swift-atomics", "swift-markdown",
        "SwiftyStoreKit", "SwiftUIX", "CombineExt", "swift-composable-architecture",
        "TCA", "Moya", "Texture", "IQKeyboardManager", "SwiftMessages",
        "SkeletonView", "Hero", "lottie-ios", "Nuke", "DeviceKit",
        "SwifterSwift", "BetterSegmentedControl", "MBProgressHUD",
        "SVProgressHUD", "NVActivityIndicatorView", "KeychainAccess",
        "CryptoSwift", "TrustKit", "ReachabilitySwift", "Reachability",
        "Socket.IO-Client-Swift", "Starscream", "SwiftWebSocket",
        "SwiftProtobuf", "grpc-swift", "SwiftGRPC", "Eureka",
        "Mockingjay", "OHHTTPStubs", "Quick", "Nimble", "Cuckoo",
        "swift-snapshot-testing", "SnapshotTesting", "Rainbow",
        "swift-tools-support-core", "Yams", "SwiftShell", "swift-sh",
        "Files", "PathKit", "Stencil", "Rswift", "SwiftGen",
        "Sourcery", "Mockolo", "ReactiveCocoa", "ReactiveSwift",
        "PromiseKit", "BrightFutures", "Hydra", "Then",
        "Swinject", "Resolver", "Needle", "GameCenterKit",
        "StripeSdk", "FirebaseiOSSDK", "realm-cocoa", "GRDB.swift",
        "SQLite.swift", "FMDB", "CouchbaseLite", "ObjectMapper",
        "HandyJSON", "Pantomime", "Swiftz", "Bow",
    ],

    # CocoaPods - top by popularity
    "cocoapods": [
        "AFNetworking", "SDWebImage", "SnapKit", "MBProgressHUD", "Alamofire",
        "Realm", "SVProgressHUD", "Kingfisher", "IQKeyboardManager",
        "Masonry", "YYKit", "YYModel", "YYText", "YYImage", "YYCache",
        "FMDB", "AsyncDisplayKit", "Texture", "TTTAttributedLabel",
        "pop", "XLForm", "SwiftyJSON", "Reachability", "GoogleAnalytics",
        "Firebase", "FirebaseCore", "FirebaseAuth", "FirebaseFirestore",
        "FirebaseStorage", "FirebaseMessaging", "FirebaseAnalytics",
        "Crashlytics", "Fabric", "Mantle", "Nimbus", "Parse",
        "MagicalRecord", "PubNub", "SocketRocket", "GPUImage",
        "PromiseKit", "BoltsSwift", "Bolts", "RestKit", "MMKV",
        "AppAuth", "JSONKit", "OpenSSL-Universal", "GRDB.swift",
        "SQLite.swift", "RxSwift", "RxCocoa", "ReactiveCocoa",
        "Quick", "Nimble", "OCMock", "OHHTTPStubs", "Moya",
        "Charts", "pop", "ChameleonFramework", "Hero", "lottie-ios",
        "FSCalendar", "IGListKit", "DZNEmptyDataSet", "PullToRefreshKit",
        "MJRefresh", "PKHUD", "JGProgressHUD", "NVActivityIndicatorView",
        "ProgressHUD", "SwiftMessages", "Toast-Swift", "CryptoSwift",
        "KeychainAccess", "SSKeychain", "MaterialComponents",
        "Stripe", "Braintree", "PayPal-iOS-SDK", "GoogleMaps",
        "MapKit", "CoreLocation", "GoogleSignIn", "FacebookSDK",
        "TwitterKit", "BranchSDK", "Mixpanel", "Amplitude",
        "Segment", "Intercom", "Instabug", "Sentry",
        "AppsFlyerFramework", "Adjust", "ZendeskSDK", "LaunchDarkly",
        "GoogleUtilities", "OneSignal", "HockeySDK", "Appirater",
        "Bugsnag", "Branch", "Lookback", "Reveal-iOS-SDK",
    ],

    # CPAN - top Perl modules
    "cpan": [
        "DateTime", "Moose", "Moo", "DBI", "DBD-mysql", "DBD-Pg", "DBD-SQLite",
        "Mojolicious", "Dancer", "Dancer2", "Catalyst-Runtime", "Plack",
        "HTTP-Tiny", "LWP", "libwww-perl", "HTTP-Request", "HTTP-Response",
        "Try-Tiny", "Scalar-Util", "List-Util", "JSON", "JSON-XS",
        "JSON-PP", "YAML", "YAML-XS", "YAML-Tiny", "XML-Simple",
        "XML-Parser", "XML-LibXML", "Text-CSV", "Text-CSV_XS",
        "File-Slurp", "Path-Tiny", "File-Find-Rule", "File-Temp",
        "Cwd", "File-Spec", "File-Basename", "File-Copy", "File-Path",
        "Template", "Template-Toolkit", "HTML-Template", "Mason",
        "Email-Sender", "Email-MIME", "MIME-Lite", "Net-SMTP",
        "DBIx-Class", "DBIx-Class-Schema-Loader", "Rose-DB-Object",
        "SQL-Abstract", "DBD-ODBC", "Redis", "CHI",
        "Cache-Memcached", "Cache-Memcached-Fast",
        "Log-Dispatch", "Log-Log4perl", "Log-Any",
        "Config-Tiny", "Config-General", "Config-Any",
        "Getopt-Long", "Getopt-Long-Descriptive", "App-Cmd",
        "Test-More", "Test-Simple", "Test-Deep", "Test-Exception",
        "Test-MockObject", "Test-Pod", "Test-Pod-Coverage",
        "Devel-NYTProf", "Devel-Cover", "Devel-REPL",
        "Term-ReadLine", "Term-ANSIColor", "Term-ProgressBar",
        "IO-All", "IO-Socket-SSL", "IO-Socket-INET6",
        "Net-SSH2", "Net-SSH-Perl", "Net-FTP",
        "Crypt-SSLeay", "Digest-MD5", "Digest-SHA", "Digest-HMAC",
        "Encode", "Unicode-String", "Unicode-Collate",
        "Class-Accessor", "Class-Method-Modifiers", "MooX-Options",
        "Role-Tiny", "Sub-Name", "Sub-Identify",
        "Data-Dumper", "Data-Dump", "Data-Printer",
        "Storable", "Sereal", "CBOR-XS",
        "Parallel-ForkManager", "Parallel-MCE",
        "POE", "AnyEvent", "Future",
        "Readonly", "Const-Fast",
        "HTML-Parser", "HTML-TreeBuilder",
        "WWW-Mechanize", "HTTP-Cookies", "URI",
        "Archive-Tar", "Archive-Zip", "Compress-Zlib",
        "Net-DNS", "Net-IP", "Net-Ping",
    ],

    # Hackage - top Haskell packages
    "hackage": [
        "lens", "aeson", "text", "containers", "bytestring", "mtl",
        "transformers", "vector", "unordered-containers", "hashable",
        "time", "directory", "filepath", "process", "async",
        "stm", "parallel", "split", "parsec", "megaparsec",
        "attoparsec", "pandoc", "happy", "alex", "haskell-src",
        "haskell-src-exts", "cabal-install", "stack", "hlint",
        "hspec", "tasty", "tasty-hunit", "QuickCheck", "HUnit",
        "criterion", "gauge", "deepseq", "primitive", "array",
        "random", "free", "mono-traversable", "profunctors",
        "bifunctors", "contravariant", "comonad", "adjunctions",
        "kan-extensions", "distributive", "semigroupoids", "reflection",
        "tagged", "void", "base-compat", "dlist", "hashtables",
        "psqueues", "fgl", "vector-algorithms", "statistics",
        "matrix", "linear", "hmatrix", "ad", "numeric-prelude",
        "wreq", "http-client", "http-client-tls", "http-types",
        "wai", "wai-extra", "warp", "scotty", "servant",
        "servant-server", "servant-client", "yesod", "yesod-core",
        "snap", "snap-core", "happstack", "miku", "websockets",
        "persistent", "persistent-postgresql", "persistent-sqlite",
        "postgresql-simple", "sqlite-simple", "mysql-simple",
        "mongoDB", "redis", "amqp", "kafka-client",
        "cryptohash", "cryptonite", "uuid", "monad-logger",
        "fast-logger", "katip", "co-log", "log-warper",
        "bytestring-builder", "conduit", "streaming", "pipes",
        "pipes-bytestring", "conduit-extra", "resourcet", "safe",
        "safe-exceptions", "exceptions", "unliftio", "unliftio-core",
    ],

    # CRAN - top R packages
    "cran": [
        "dplyr", "ggplot2", "tidyr", "stringr", "purrr", "readr",
        "tibble", "lubridate", "forcats", "tidyverse", "magrittr",
        "rlang", "vctrs", "cli", "glue", "pillar", "lifecycle",
        "withr", "fs", "here", "knitr", "rmarkdown", "bookdown",
        "shiny", "shinydashboard", "DT", "plotly", "leaflet",
        "htmltools", "htmlwidgets", "jsonlite", "httr", "curl",
        "xml2", "rvest", "data.table", "Rcpp", "devtools",
        "usethis", "roxygen2", "testthat", "covr", "pkgdown",
        "remotes", "pak", "renv", "packrat", "credentials",
        "gert", "gh", "git2r", "R6", "digest",
        "crayon", "sys", "processx", "ps", "callr",
        "desc", "rprojroot", "pkgload", "pkgbuild", "pkgconfig",
        "rstudioapi", "reticulate", "rJava", "ROCR", "survival",
        "MASS", "lattice", "Matrix", "nnet", "rpart",
        "randomForest", "caret", "e1071", "ranger", "xgboost",
        "lightgbm", "glmnet", "mgcv", "nlme", "lme4",
        "lmerTest", "car", "rstatix", "broom", "emmeans",
        "afex", "ez", "psych", "lavaan", "brms",
        "rstan", "rstanarm", "tidymodels", "parsnip", "recipes",
        "rsample", "yardstick", "workflows", "dials", "tune",
        "tictoc", "microbenchmark", "profvis", "bench", "progress",
        "furrr", "future", "parallelly", "multidplyr", "snow",
        "foreach", "iterators", "doParallel", "doMC", "doSNOW",
        "stringi", "stringdist", "fuzzyjoin", "janitor", "skimr",
    ],

    # Conda-forge - top packages
    "conda": [
        "numpy", "pandas", "scipy", "matplotlib", "scikit-learn",
        "seaborn", "statsmodels", "sympy", "networkx", "nltk",
        "tensorflow", "pytorch", "torch", "torchvision", "transformers",
        "huggingface_hub", "datasets", "accelerate", "sentencepiece",
        "xgboost", "lightgbm", "catboost", "prophet", "dask",
        "ray", "joblib", "numba", "cython", "pybind11",
        "jupyter", "jupyterlab", "ipykernel", "ipython", "notebook",
        "nbconvert", "voila", "papermill", "streamlit", "bokeh",
        "plotly", "altair", "holoviews", "datashader", "panel",
        "flask", "django", "fastapi", "starlette", "uvicorn",
        "gunicorn", "requests", "urllib3", "aiohttp", "httpx",
        "beautifulsoup4", "lxml", "selenium", "scrapy", "playwright",
        "pytest", "mock", "tox", "black", "flake8",
        "mypy", "ruff", "pre-commit", "isort", "pylint",
        "sqlalchemy", "psycopg2", "pymongo", "redis-py", "elasticsearch",
        "pydantic", "marshmallow", "attrs", "dataclasses-json",
        "click", "typer", "rich", "textual", "tqdm",
        "python-dotenv", "pyyaml", "toml", "tomli", "pytomlpp",
        "pillow", "opencv", "imageio", "scikit-image", "pycocotools",
        "openai", "anthropic", "langchain", "llama-index", "chromadb",
        "faiss-cpu", "faiss-gpu", "sentence-transformers", "spacy",
        "gensim", "wordcloud", "textblob", "polyglot",
        "boto3", "google-cloud-storage", "azure-storage-blob",
        "paramiko", "fabric", "ansible", "salt", "terraform",
        "conda", "mamba", "pip", "setuptools", "wheel",
    ],

    # Homebrew - top formulae
    "homebrew": [
        "git", "node", "python", "postgresql", "redis", "mongodb-community",
        "nginx", "httpd", "openssl", "curl", "wget", "jq", "yq",
        "htop", "tmux", "vim", "neovim", "emacs", "fish", "zsh",
        "bash", "gnu-sed", "gnu-tar", "coreutils", "findutils",
        "grep", "ripgrep", "fd", "bat", "eza", "fzf", "zoxide",
        "go", "rust", "ruby", "php", "perl", "lua", "elixir",
        "erlang", "scala", "kotlin", "swift", "haskell-stack",
        "gcc", "llvm", "cmake", "make", "automake", "autoconf",
        "pkg-config", "libtool", "ninja", "meson", "bazel",
        "docker", "docker-compose", "kubernetes-cli", "kubectl",
        "helm", "terraform", "terragrunt", "packer", "vault",
        "consul", "nomad", "ansible", "saltstack", "puppet",
        "awscli", "azure-cli", "gcloud", "doctl", "heroku",
        "mysql", "mariadb", "sqlite", "duckdb", "clickhouse",
        "memcached", "rabbitmq", "kafka", "zookeeper", "nats-server",
        "ffmpeg", "imagemagick", "graphicsmagick", "exiftool", "pandoc",
        "tesseract", "leptonica", "opencv", "poppler", "qpdf",
        "node@18", "node@20", "python@3.11", "python@3.12", "python@3.13",
        "openjdk", "openjdk@11", "openjdk@17", "openjdk@21",
        "ruby@3.2", "ruby@3.3",
        "gh", "glab", "hub", "git-lfs", "git-flow",
        "gpg", "gnupg", "pinentry", "pinentry-mac",
        "tree", "watch", "screen", "telnet", "netcat",
        "nmap", "socat", "iperf3", "mtr", "tcpdump",
        "speedtest-cli", "youtube-dl", "yt-dlp", "aria2",
        "rclone", "rsync", "unison", "syncthing", "restic",
        "mas", "mackup", "dockutil", "duti", "fswatch",
        "nvm", "pyenv", "rbenv", "rustup", "volta",
        "direnv", "starship", "powerlevel10k", "oh-my-zsh",
    ],
}


async def process_one(eco: str, name: str, processed: set) -> tuple[bool, str]:
    """Fetch+save a single package. Return (ok, reason)."""
    key = f"{eco}:{name}"
    try:
        pkg = await fetch_package(eco, name)
        if not pkg:
            return (False, "fetch_none")
        latest = pkg.get("latest_version", "") or ""
        vulns = await fetch_vulnerabilities(eco, name, latest_version=latest)
        health = calculate_health_score(pkg, vulns)
        await save_package_to_db(pkg, health["score"], vulns)
        await cache_set(f"check:{eco}:{name}", {
            "package": name,
            "ecosystem": eco,
            "latest_version": latest,
            "health": health,
            "vulnerabilities": {"count": len(vulns)},
        }, ttl=86400)
        processed.add(key)
        return (True, f"score={health['score']}")
    except Exception as e:
        return (False, f"err:{type(e).__name__}:{str(e)[:60]}")


async def main():
    log("=" * 70)
    log("START seed_minor_ecosystems")
    start = time.time()

    # Load existing packages
    import asyncpg
    db_url = os.environ.get("DATABASE_URL") or "postgresql://depscope:depscope2026@localhost:5432/depscope"
    conn = await asyncpg.connect(db_url)
    rows = await conn.fetch("SELECT ecosystem, name FROM packages")
    processed = {f"{r['ecosystem']}:{r['name']}" for r in rows}
    await conn.close()
    log(f"Existing packages in DB: {len(processed)}")

    grand_total_new = 0
    summary = {}

    for eco, names in TOP_PACKAGES.items():
        eco_start = time.time()
        log(f"--- {eco.upper()} ({len(names)} targets) ---")
        eco_new = 0
        eco_errors = 0
        for i, name in enumerate(names):
            key = f"{eco}:{name}"
            if key in processed:
                # Already present — refresh anyway to update data
                pass
            ok, reason = await process_one(eco, name, processed)
            if ok:
                eco_new += 1
                grand_total_new += 1
                if (i + 1) % 10 == 0:
                    log(f"  [{eco}] {i+1}/{len(names)} ok last={name} {reason}")
            else:
                eco_errors += 1
                log(f"  [{eco}] FAIL {name} {reason}")
            await asyncio.sleep(1.0)  # rate limit
        elapsed = time.time() - eco_start
        summary[eco] = {"ok": eco_new, "err": eco_errors, "sec": round(elapsed, 1)}
        log(f"=== {eco.upper()} done: ok={eco_new} err={eco_errors} time={elapsed:.1f}s ===")

    total_elapsed = time.time() - start
    log("=" * 70)
    log("SUMMARY")
    for eco, s in summary.items():
        log(f"  {eco:12s} ok={s['ok']:4d}  err={s['err']:3d}  time={s['sec']}s")
    log(f"TOTAL packages processed OK: {grand_total_new}")
    log(f"TOTAL time: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")
    log("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
