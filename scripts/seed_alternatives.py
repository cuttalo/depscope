"""Seed 200+ cross-package alternatives based on known deprecations / recommendations.

Idempotent: ON CONFLICT DO NOTHING on unique (package_id, alternative_name).
"""
import asyncio
import os
import sys

sys.path.insert(0, "/home/deploy/depscope")


# Format: (ecosystem, from_pkg, [(alt_name, reason, score, alt_eco_optional), ...])
# Score: 100 = perfect drop-in, 90 = strong, 80 = good alternative
ALTERNATIVES = [
    # --- NPM deprecated/legacy ---
    ("npm", "bower", [("npm", "Bower is deprecated; use npm / yarn / pnpm", 100),
                      ("yarn", "Fast Facebook-backed package manager", 90)]),
    ("npm", "grunt", [("webpack", "Industry-standard module bundler", 90),
                      ("vite", "Next-gen build tool, fast HMR", 100),
                      ("gulp", "Streaming task runner", 80)]),
    ("npm", "gulp", [("vite", "Modern build tool", 90),
                     ("esbuild", "Extremely fast JS bundler", 85)]),
    ("npm", "tslint", [("eslint", "TSLint was deprecated in favor of ESLint + typescript-eslint", 100)]),
    ("npm", "protractor", [("cypress", "Modern E2E test framework", 100),
                            ("playwright", "Microsoft E2E framework, multi-browser", 95)]),
    ("npm", "nyc", [("c8", "Native V8 coverage, faster", 95),
                    ("vitest", "Built-in coverage via v8", 90)]),
    ("npm", "mocha", [("vitest", "Vite-native, fast, Jest-compatible", 95),
                      ("jest", "De-facto standard test runner", 90)]),
    ("npm", "chai", [("vitest", "Built-in assertions", 90),
                     ("jest", "Built-in expect assertions", 90)]),
    ("npm", "browserify", [("webpack", "Industry standard", 90),
                            ("vite", "Faster, modern", 100),
                            ("esbuild", "Extremely fast", 95)]),
    ("npm", "node-sass", [("sass", "Pure JS Dart Sass, official replacement", 100)]),
    ("npm", "phantomjs-prebuilt", [("puppeteer", "Chrome headless by Google", 100),
                                     ("playwright", "Multi-browser headless", 95)]),
    ("npm", "bcrypt", [("bcryptjs", "Pure JS, no native deps", 85),
                       ("argon2", "More secure modern alternative", 90)]),
    ("npm", "left-pad", [("string.prototype.padstart", "Native JS method", 100)]),
    ("npm", "uglify-js", [("terser", "ES6+ support, actively maintained", 100)]),
    ("npm", "babel-preset-es2015", [("@babel/preset-env", "Smart preset, Babel 7+", 100)]),
    ("npm", "gitbook", [("docusaurus", "React-powered docs", 95),
                         ("mkdocs", "Python-based, simpler", 80)]),
    ("npm", "connect", [("express", "Full framework including connect middleware", 100),
                         ("koa", "Modern, async/await-first", 90)]),
    ("npm", "forever", [("pm2", "Feature-rich process manager", 100),
                         ("nodemon", "Development auto-restart", 70)]),
    ("npm", "node-gyp", [("prebuildify", "Ship prebuilt binaries, skip gyp", 80)]),
    ("npm", "cheerio", [("jsdom", "Full DOM implementation", 85),
                         ("parse5", "HTML parser used by jsdom", 70)]),
    ("npm", "react-router-dom", [("next/router", "Built into Next.js", 80),
                                   ("tanstack-router", "Type-safe routing", 90)]),
    ("npm", "redux", [("zustand", "Simpler, smaller, same patterns", 95),
                       ("jotai", "Atomic state, fine-grained", 90),
                       ("@tanstack/react-query", "For server state", 85)]),
    ("npm", "enzyme", [("@testing-library/react", "Official recommended testing", 100)]),
    ("npm", "create-react-app", [("vite", "Faster dev server & builds", 100),
                                   ("next", "Full React framework", 95)]),

    # --- PyPI ---
    ("pypi", "urllib3", []),  # not deprecated, skip
    ("pypi", "pillow", []),   # active
    ("pypi", "nose", [("pytest", "pytest is the de-facto standard", 100),
                      ("unittest", "Standard library", 60)]),
    ("pypi", "nose2", [("pytest", "More features, larger ecosystem", 95)]),
    ("pypi", "pycrypto", [("cryptography", "Modern, audited, recommended", 100),
                           ("pycryptodome", "Drop-in pycrypto replacement", 95)]),
    ("pypi", "crypto", [("cryptography", "Industry standard", 100)]),
    ("pypi", "mysqldb", [("mysqlclient", "Maintained MySQLdb fork", 100),
                          ("pymysql", "Pure Python MySQL driver", 80)]),
    ("pypi", "distribute", [("setuptools", "Distribute was merged back", 100)]),
    ("pypi", "imp", [("importlib", "imp deprecated since Python 3.4", 100)]),
    ("pypi", "nose", [("pytest", "Industry standard test runner", 100)]),
    ("pypi", "yaml", [("pyyaml", "Correct package name is pyyaml", 100)]),
    ("pypi", "simplejson", [("json", "Standard library JSON is sufficient", 80),
                             ("orjson", "Fastest JSON for Python, C extension", 95)]),
    ("pypi", "mock", [("unittest.mock", "Built into Python 3.3+ stdlib", 100)]),
    ("pypi", "funcsigs", [("inspect", "Built into Python 3 stdlib", 100)]),
    ("pypi", "pathlib", [("pathlib", "Built into Python 3.4+ stdlib", 100)]),
    ("pypi", "pytz", [("zoneinfo", "Built into Python 3.9+ stdlib", 90),
                      ("dateutil", "Rich date utilities", 80)]),
    ("pypi", "optparse", [("argparse", "argparse superseded optparse in Python 2.7+", 100),
                           ("click", "High-level CLI framework", 90),
                           ("typer", "Type-hint based CLI", 90)]),
    ("pypi", "requests-oauthlib", [("authlib", "Modern, more OAuth providers", 85)]),
    ("pypi", "sqlalchemy-migrate", [("alembic", "Official SQLAlchemy migration tool", 100)]),
    ("pypi", "south", [("django.db.migrations", "Built into Django 1.7+", 100)]),
    ("pypi", "django-south", [("django.db.migrations", "Built into Django 1.7+", 100)]),
    ("pypi", "fabric3", [("fabric", "Fabric 2.x+ supports Python 3 natively", 100),
                          ("invoke", "Generic task runner from same author", 85)]),
    ("pypi", "raven", [("sentry-sdk", "Official replacement, Raven is deprecated", 100)]),
    ("pypi", "pkg_resources", [("importlib.metadata", "Stdlib equivalent in Python 3.8+", 100)]),
    ("pypi", "tox", [("nox", "Python-configured testing automation", 85)]),
    ("pypi", "flake8", [("ruff", "10-100x faster, covers flake8 + isort + pyupgrade", 100)]),
    ("pypi", "pylint", [("ruff", "Faster, overlapping rules", 90)]),
    ("pypi", "isort", [("ruff", "Ruff implements isort rules natively", 100)]),
    ("pypi", "pyupgrade", [("ruff", "Ruff includes pyupgrade rules", 100)]),
    ("pypi", "black", [("ruff format", "Ruff formatter is black-compatible, faster", 95)]),
    ("pypi", "yapf", [("ruff format", "Faster modern formatter", 90),
                       ("black", "Opinionated, stable", 85)]),
    ("pypi", "autopep8", [("ruff", "Faster and covers more rules", 95)]),
    ("pypi", "pip-tools", [("uv", "10-100x faster pip/pip-tools replacement", 100),
                            ("poetry", "Full dependency manager", 90)]),
    ("pypi", "pipenv", [("poetry", "More maintained, better dependency resolution", 90),
                         ("uv", "Faster, modern", 95)]),
    ("pypi", "virtualenv", [("venv", "Built into Python 3.3+ stdlib", 90),
                             ("uv", "Creates venvs faster", 95)]),

    # --- Cargo ---
    ("cargo", "failure", [("anyhow", "Modern, widely adopted error handling", 100),
                           ("thiserror", "For library error types", 90)]),
    ("cargo", "error-chain", [("anyhow", "Modern replacement", 100),
                                ("thiserror", "For library error types", 90)]),
    ("cargo", "openssl", [("rustls", "Pure Rust TLS, no C deps", 90),
                           ("native-tls", "Uses platform TLS", 80)]),
    ("cargo", "time", [("chrono", "More features, wider adoption", 85),
                        ("time", "Newer 0.3+ is good; use if minimal", 90)]),
    ("cargo", "rustc-serialize", [("serde", "De-facto standard, vastly better", 100)]),
    ("cargo", "rand_core", [("rand", "Full rand crate re-exports rand_core", 95)]),

    # --- Ruby ---
    ("rubygems", "rails-4", [("rails", "Upgrade to Rails 7/8 LTS", 90)]),
    ("rubygems", "paperclip", [("active_storage", "Built into Rails 5.2+", 100),
                                ("shrine", "Flexible file uploads", 85)]),
    ("rubygems", "delayed_job", [("sidekiq", "Redis-based, multi-threaded", 95),
                                   ("good_job", "PostgreSQL-based, multi-threaded", 90)]),
    ("rubygems", "resque", [("sidekiq", "Multi-threaded, more efficient", 95)]),
    ("rubygems", "unicorn", [("puma", "Thread-safe, default in Rails 5+", 100)]),
    ("rubygems", "passenger", [("puma", "Rails default", 90)]),
    ("rubygems", "thin", [("puma", "Modern default", 95)]),
    ("rubygems", "mongoid", [("activerecord", "If moving to SQL", 70)]),
    ("rubygems", "cancan", [("cancancan", "Maintained fork of cancan", 100),
                              ("pundit", "Simpler, policy-based authorization", 90)]),
    ("rubygems", "devise", [("rodauth-rails", "More modern, testable auth", 80)]),
    ("rubygems", "rspec", [("minitest", "Rails default, simpler", 80)]),
    ("rubygems", "spring", [("bootsnap", "Active, used by Rails by default", 90)]),

    # --- Go ---
    ("go", "github.com/dgrijalva/jwt-go", [("github.com/golang-jwt/jwt", "Maintained fork after dgrijalva archived", 100)]),
    ("go", "github.com/gorilla/mux", [("github.com/go-chi/chi", "Active, idiomatic", 90),
                                        ("net/http", "stdlib with ServeMux in 1.22+", 85)]),
    ("go", "github.com/pkg/errors", [("errors", "Go 1.13+ stdlib has errors.Is/As/%w", 100)]),
    ("go", "github.com/sirupsen/logrus", [("log/slog", "Stdlib structured logging in Go 1.21+", 100),
                                            ("github.com/rs/zerolog", "Faster, zero-alloc", 90),
                                            ("github.com/uber-go/zap", "Structured, very fast", 90)]),
    ("go", "github.com/golang/mock", [("go.uber.org/mock", "Maintained fork after golang/mock archived", 100)]),
    ("go", "github.com/google/uuid", []),
    ("go", "github.com/fiber/fiber", [("github.com/gofiber/fiber", "Correct canonical import path", 100)]),
    ("go", "github.com/gorilla/websocket", [("github.com/coder/websocket", "Modern, context-aware", 85),
                                              ("nhooyr.io/websocket", "Simpler, context-aware", 85)]),
    ("go", "github.com/satori/go.uuid", [("github.com/google/uuid", "Well-maintained alternative", 100),
                                           ("github.com/gofrs/uuid", "Maintained fork of satori", 95)]),

    # --- Maven ---
    ("maven", "com.sun.mail:javax.mail", [("org.eclipse.angus:jakarta.mail", "Jakarta EE namespace migration", 100)]),
    ("maven", "javax.servlet:servlet-api", [("jakarta.servlet:jakarta.servlet-api", "Jakarta EE replacement", 100)]),
    ("maven", "commons-logging:commons-logging", [("org.slf4j:slf4j-api", "Industry standard facade", 100)]),
    ("maven", "log4j:log4j", [("org.apache.logging.log4j:log4j-core", "Log4j 2.x is the replacement", 100),
                                ("ch.qos.logback:logback-classic", "Logback is a successor", 95)]),
    ("maven", "junit:junit", [("org.junit.jupiter:junit-jupiter", "JUnit 5", 100)]),
    ("maven", "mysql:mysql-connector-java", [("com.mysql:mysql-connector-j", "Renamed coordinates", 100)]),
    ("maven", "joda-time:joda-time", [("java.time", "Built into Java 8+ (JSR-310)", 100)]),

    # --- NuGet ---
    ("nuget", "Newtonsoft.Json", [("System.Text.Json", "Microsoft recommended, faster, built-in", 95)]),
    ("nuget", "Microsoft.AspNet.WebApi", [("Microsoft.AspNetCore.Mvc", "ASP.NET Core is the successor", 100)]),
    ("nuget", "EntityFramework", [("Microsoft.EntityFrameworkCore", "EF Core is the modern version", 100)]),
    ("nuget", "Microsoft.Bcl.AsyncInterfaces", [("System.Threading.Tasks", "Built into modern .NET", 85)]),
    ("nuget", "Enums.NET", [("System.Enum", "Modern .NET adds EnumPolyfill", 80)]),
    ("nuget", "Autofac", [("Microsoft.Extensions.DependencyInjection", "Built-in DI container", 85)]),
    ("nuget", "IdentityServer4", [("Duende.IdentityServer", "IdentityServer4 is EOL, Duende is the successor", 100)]),

    # --- Composer/PHP ---
    ("composer", "twitter/bootstrap", [("twbs/bootstrap", "Correct vendor name is twbs", 100)]),
    ("composer", "zendframework/zend-framework", [("laminas/laminas-mvc", "Zend was renamed to Laminas", 100)]),
    ("composer", "zendframework/zend-diactoros", [("laminas/laminas-diactoros", "Laminas fork", 100)]),
    ("composer", "zendframework/zend-stratigility", [("laminas/laminas-stratigility", "Laminas fork", 100)]),
    ("composer", "guzzlehttp/guzzle", []),  # active
    ("composer", "symfony/event-dispatcher", []),
    ("composer", "phpunit/phpunit", [("pestphp/pest", "Modern DX, built on PHPUnit", 85)]),
    ("composer", "codeception/codeception", [("pestphp/pest", "Simpler for unit+integration", 80)]),
    ("composer", "mockery/mockery", [("phpunit/phpunit", "Use PHPUnit mocks for simplicity", 70)]),
    ("composer", "swiftmailer/swiftmailer", [("symfony/mailer", "Symfony Mailer is the modern successor", 100)]),
    ("composer", "phpmyadmin/phpmyadmin", []),

    # --- Pub / Flutter ---
    ("pub", "flutter_flux", [("flutter_bloc", "De-facto standard for state management", 95),
                               ("provider", "Simpler, official-ish", 90),
                               ("riverpod", "Modern successor to provider", 100)]),
    ("pub", "scoped_model", [("provider", "Official successor", 100)]),
    ("pub", "flutter_redux", [("flutter_bloc", "More popular alternative", 90),
                                ("riverpod", "Modern state management", 95)]),
    ("pub", "mobx", [("riverpod", "Compile-time safe, idiomatic Dart", 90)]),

    # --- Hex / Elixir ---
    ("hex", "httpoison", [("req", "Modern HTTP client, built on Finch, Jose Valim endorsed", 100),
                           ("finch", "Lower-level, fast", 85)]),
    ("hex", "tesla", [("req", "Simpler API, official direction", 90)]),
    ("hex", "poison", [("jason", "Significantly faster, Ecto default", 100)]),
    ("hex", "cowboy", [("bandit", "Pure Elixir, faster, Phoenix 1.7+ default", 95)]),
    ("hex", "exq", [("oban", "Postgres-backed, feature-rich, de-facto standard", 95),
                     ("broadway", "For data pipelines", 80)]),
    ("hex", "comeonin", [("argon2_elixir", "Argon2 direct, Comeonin is wrapper", 90),
                           ("bcrypt_elixir", "BCrypt direct", 85)]),
    ("hex", "guardian", [("pow", "Full auth solution", 80),
                          ("phx.gen.auth", "Phoenix built-in generator", 95)]),

    # --- Hackage / Haskell ---
    ("hackage", "string", [("text", "UTF-8, efficient, de-facto standard", 100),
                             ("bytestring", "For binary data", 80)]),
    ("hackage", "HTTP", [("http-client", "Modern, widely used", 100),
                           ("wreq", "High-level, lens-based", 85),
                           ("req", "Type-safe, modern", 90)]),
    ("hackage", "parsec", [("megaparsec", "Better errors, wider features", 95),
                             ("attoparsec", "For bytestring/speed", 85)]),
    ("hackage", "old-time", [("time", "Modern time library", 100)]),
    ("hackage", "old-locale", [("time", "Merged into time", 100)]),

    # --- CocoaPods / Swift ---
    ("cocoapods", "AFNetworking", [("Alamofire", "Swift-first successor, same author, still Obj-C friendly", 95),
                                     ("URLSession", "Apple's native API", 80)]),
    ("cocoapods", "MBProgressHUD", [("JGProgressHUD", "Swift-first, actively maintained", 85),
                                      ("SVProgressHUD", "Simpler API", 80)]),
    ("cocoapods", "Parse", [("Firebase", "Google's BaaS replacement", 90)]),
    ("cocoapods", "Masonry", [("SnapKit", "Swift-first version of Masonry", 100)]),
    ("cocoapods", "Fabric", [("Firebase Crashlytics", "Crashlytics migrated to Firebase", 100)]),
    ("cocoapods", "Crashlytics", [("Firebase/Crashlytics", "Crashlytics is now part of Firebase", 100)]),
    ("cocoapods", "ReactiveCocoa", [("ReactiveSwift", "Swift-native successor", 95),
                                      ("RxSwift", "Alternative reactive framework", 85)]),
    ("cocoapods", "PromiseKit", [("swift-async", "Swift concurrency (async/await)", 100)]),

    ("swift", "PromiseKit", [("swift-async", "Use Swift 5.5+ async/await", 100)]),
    ("swift", "Alamofire", [("URLSession", "Apple's built-in HTTP client", 80)]),
    ("swift", "RxSwift", [("Combine", "Apple's native reactive framework", 90),
                            ("swift-async-algorithms", "Apple official async sequences", 85)]),

    # --- CPAN / Perl ---
    ("cpan", "Class-DBI", [("DBIx-Class", "Modern, well-maintained ORM", 100)]),
    ("cpan", "CGI", [("Plack", "PSGI is modern Perl web standard", 100),
                      ("Mojolicious", "Full web framework", 90)]),
    ("cpan", "Net-SMTP", [("Email-Sender", "Modern email sending toolkit", 90)]),
    ("cpan", "JSON", [("JSON-XS", "Fastest JSON for Perl", 95),
                       ("Cpanel-JSON-XS", "Maintained XS fork", 90)]),
    ("cpan", "YAML", [("YAML-XS", "Fast C-based YAML", 95)]),
    ("cpan", "LWP-UserAgent", [("HTTP-Tiny", "Minimal HTTP client in stdlib", 85),
                                 ("Furl", "Faster than LWP", 90)]),

    # --- CRAN / R ---
    ("cran", "plyr", [("dplyr", "Hadley's modern successor to plyr", 100),
                       ("purrr", "Functional iteration", 85)]),
    ("cran", "reshape", [("tidyr", "Modern successor by Hadley", 100)]),
    ("cran", "reshape2", [("tidyr", "Modern successor", 100)]),
    ("cran", "doMC", [("doParallel", "Cross-platform, works on Windows", 95)]),
    ("cran", "RJSONIO", [("jsonlite", "Faster and more maintained", 95)]),
    ("cran", "RCurl", [("curl", "Modern, maintained", 90),
                        ("httr", "High-level HTTP", 85)]),
    ("cran", "gdata", [("openxlsx", "Read/write xlsx without Java", 90),
                        ("readxl", "tidyverse xlsx reader", 85)]),
    ("cran", "XLConnect", [("openxlsx", "No Java required", 95)]),

    # --- Conda / Python ---
    ("conda", "tensorflow-gpu", [("tensorflow", "TF 2.x+ includes GPU support", 100)]),
    ("conda", "pytorch", []),
    ("conda", "mongo-python-driver", [("pymongo", "Correct package name", 100)]),

    # --- Homebrew ---
    ("homebrew", "node", []),
    ("homebrew", "python", [("python@3.12", "Specific version recommended for stability", 80)]),
    ("homebrew", "mongodb", [("mongodb-community", "MongoDB Inc moved formula", 100)]),
    ("homebrew", "docker", [("docker-compose", "Include docker-compose separately", 80),
                              ("colima", "Open-source Docker Desktop alternative", 85)]),
    ("homebrew", "php", [("php@8.3", "Pin to a specific version for stability", 80)]),
    ("homebrew", "youtube-dl", [("yt-dlp", "Actively maintained fork with more features", 100)]),
    ("homebrew", "apache-spark", []),
    ("homebrew", "gcc", []),
    ("homebrew", "ruby", [("rbenv", "Use rbenv for version management", 80)]),
]


async def seed():
    import asyncpg
    db_url = os.environ.get("DATABASE_URL") or os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)

    added = 0
    skipped = 0
    missing_source = 0
    for (eco, pkg_name, alts) in ALTERNATIVES:
        if not alts:
            continue
        # Find source package
        pkg_row = await conn.fetchrow("SELECT id FROM packages WHERE ecosystem=$1 AND name=$2", eco, pkg_name)
        if not pkg_row:
            missing_source += 1
            print(f"  SKIP source not in DB: {eco}/{pkg_name}")
            continue
        pkg_id = pkg_row["id"]

        for alt in alts:
            if len(alt) == 3:
                alt_name, reason, score = alt
            elif len(alt) == 4:
                alt_name, reason, score, _ = alt
            else:
                continue

            # Look up alternative_package_id (optional)
            alt_row = await conn.fetchrow("SELECT id FROM packages WHERE ecosystem=$1 AND name=$2", eco, alt_name)
            alt_pkg_id = alt_row["id"] if alt_row else None

            try:
                r = await conn.execute("""
                    INSERT INTO alternatives (package_id, alternative_package_id, alternative_name, reason, score)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (package_id, alternative_name) DO UPDATE SET
                        reason = EXCLUDED.reason,
                        score = EXCLUDED.score,
                        alternative_package_id = EXCLUDED.alternative_package_id
                """, pkg_id, alt_pkg_id, alt_name, reason, score)
                if "INSERT 0 1" in r:
                    added += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"  ERR {eco}/{pkg_name} -> {alt_name}: {e}")

    total = await conn.fetchval("SELECT COUNT(*) FROM alternatives")
    await conn.close()
    print(f"Added new: {added}")
    print(f"Updated (already existed): {skipped}")
    print(f"Missing source package: {missing_source}")
    print(f"Total alternatives now: {total}")


if __name__ == "__main__":
    asyncio.run(seed())
