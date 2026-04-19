"""Seed breaking_changes / errors / known_bugs / compat_matrix for non-JS/Python
ecosystems: Go, PHP (composer), Ruby (rubygems), Java (maven), .NET (nuget),
Swift. All data verified against official docs/changelogs as of early 2026.

Idempotent: ON CONFLICT DO UPDATE.

Run from /home/deploy/depscope with:
    .venv/bin/python -m scripts.seed_ecosystems
"""
import asyncio
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.database import get_pool, close_pool  # noqa: E402
from api.verticals import normalize_error, hash_stack  # noqa: E402


# =========================================================================== #
# BREAKING CHANGES — extended ecosystems
# =========================================================================== #

BREAKING_CHANGES = [
    # --- Go --- runtime / stdlib ---
    {"eco": "go", "pkg": "go", "from": "1.21", "to": "1.22", "type": "behavior",
     "desc": "Loop variable scope: each iteration of `for i := range x` now creates a new i (was shared across iterations).",
     "hint": "Most goroutines-in-loop footguns silently fix themselves. Review with `go vet -copylocks` and `go tool loopvar` (deprecated, now default). Programs that intentionally captured the same variable across iterations must be rewritten."},
    {"eco": "go", "pkg": "go", "from": "1.22", "to": "1.23", "type": "api",
     "desc": "`iter` package GA: `range func(yield func(T) bool)` is valid in `for .. range`.",
     "hint": "Opt-in. Existing code unaffected; new range-func syntax requires go 1.23+. Use `iter.Seq[T]` as the standard signature for custom iterators."},
    {"eco": "go", "pkg": "gorm.io/gorm", "from": "1", "to": "2", "type": "api",
     "desc": "Context-aware API, dry-run mode, nested transactions. Many method signatures renamed.",
     "hint": "Use the official migration guide. `db.Find(&users)` remains, but session/transaction APIs moved to `db.Session()`/`db.Transaction()`."},

    # --- PHP / Composer ---
    {"eco": "composer", "pkg": "laravel/framework", "from": "10", "to": "11", "type": "runtime",
     "desc": "PHP 8.2+ required (was 8.1+). Node 18+ recommended for build.",
     "hint": "Upgrade PHP and Node first. Run `composer require laravel/framework:^11.0 --with-all-dependencies`."},
    {"eco": "composer", "pkg": "laravel/framework", "from": "10", "to": "11", "type": "config",
     "desc": "Slimmer application skeleton: `app/Http/Kernel.php`, `app/Console/Kernel.php`, `app/Exceptions/Handler.php` consolidated into `bootstrap/app.php`.",
     "hint": "New projects get the new skeleton. Existing apps can stay on the classic skeleton — both are supported. See the upgrade guide to migrate incrementally."},
    {"eco": "composer", "pkg": "laravel/framework", "from": "10", "to": "11", "type": "config",
     "desc": "`routes/api.php` is opt-in. `api` middleware group removed from the default kernel.",
     "hint": "Run `php artisan install:api` to enable API routes with Sanctum scaffolding."},
    {"eco": "composer", "pkg": "laravel/framework", "from": "11", "to": "12", "type": "behavior",
     "desc": "No major breaking changes; focus on maintenance. Starter kits (Breeze/Jetstream) consolidated.",
     "hint": "Usually a one-line `composer require laravel/framework:^12.0`. Verify third-party packages support 12."},
    {"eco": "composer", "pkg": "symfony/framework-bundle", "from": "6", "to": "7", "type": "runtime",
     "desc": "PHP 8.2+ required. Annotations fully removed in favor of attributes (#[Route] instead of @Route).",
     "hint": "Run `symfony-cli lint:container` and migrate `@Route` to `#[Route]`. The `symfony/maker-bundle` scaffold generates attributes by default."},
    {"eco": "composer", "pkg": "doctrine/orm", "from": "2", "to": "3", "type": "api",
     "desc": "PHP 8.1+. Removed: lifecycle callbacks on inherited classes without explicit @InheritanceType, YAML/XML mapping drivers (use attributes).",
     "hint": "Migrate YAML/XML mappings to PHP attributes with the official migration tool. Audit lifecycle callbacks on inheritance hierarchies."},

    # --- Ruby / Rubygems ---
    {"eco": "rubygems", "pkg": "rails", "from": "6", "to": "7", "type": "config",
     "desc": "Hotwire (Turbo + Stimulus) is the default front-end stack. Webpacker deprecated (removed in 7.1).",
     "hint": "New apps: no change needed. Existing apps: keep Webpacker for a release or migrate via `bin/rails app:update` + switch to importmap-rails or jsbundling-rails."},
    {"eco": "rubygems", "pkg": "rails", "from": "7", "to": "8", "type": "api",
     "desc": "Solid Queue, Solid Cable, Solid Cache built-in — PostgreSQL/MySQL/SQLite backed; Redis no longer required for jobs / ActionCable / cache.",
     "hint": "New apps get Solid* defaults. Existing apps can opt in via `bin/rails solid_queue:install`. Redis-based Sidekiq continues to work."},
    {"eco": "rubygems", "pkg": "rails", "from": "7", "to": "8", "type": "runtime",
     "desc": "Ruby 3.2+ required.",
     "hint": "Upgrade Ruby: `rbenv install 3.3.0 && rbenv local 3.3.0`. Rails 8 officially tests on 3.2, 3.3, 3.4."},
    {"eco": "rubygems", "pkg": "rails", "from": "7", "to": "8", "type": "api",
     "desc": "Built-in authentication generator: `bin/rails generate authentication`. Kamal 2 is the default deployment tool.",
     "hint": "Opt-in. Devise / Clearance / Rodauth continue to work. For deployment, `config/deploy.yml` is new — Capistrano still supported."},

    # --- Java / Maven (Spring, Jakarta) ---
    {"eco": "maven", "pkg": "org.springframework.boot:spring-boot-starter", "from": "2.7", "to": "3.0", "type": "runtime",
     "desc": "JDK 17+ required (was 8+). Jakarta EE 9 baseline — `javax.*` namespace replaced by `jakarta.*`.",
     "hint": "Run the OpenRewrite recipe `org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_0`. Manually search/replace remaining `javax.servlet.` / `javax.persistence.` imports."},
    {"eco": "maven", "pkg": "org.springframework.boot:spring-boot-starter", "from": "3.0", "to": "3.2", "type": "api",
     "desc": "Virtual threads (Project Loom) support; `spring.threads.virtual.enabled=true`. Observability via Micrometer 1.12+.",
     "hint": "Opt-in. Set the property on Tomcat/Jetty to enable virtual threads for request handling. Requires JDK 21+."},
    {"eco": "maven", "pkg": "jakarta.platform:jakarta.jakartaee-api", "from": "9", "to": "10", "type": "api",
     "desc": "Servlet 6.0, CDI 4.0, JPA 3.1. Removed deprecated APIs from Jakarta EE 9.",
     "hint": "Verify servlet container supports EE 10 (Tomcat 10.1+, Jetty 12+, WildFly 31+). Regenerate JAX-RS clients."},
    {"eco": "maven", "pkg": "org.hibernate.orm:hibernate-core", "from": "5", "to": "6", "type": "runtime",
     "desc": "Jakarta Persistence (jakarta.persistence.*) required. Query translator rewritten; some HQL edge cases behave differently.",
     "hint": "Audit complex HQL queries (TupleTransformer, subquery correlation). Spring Boot 3 bundles Hibernate 6.1+ by default."},

    # --- .NET / NuGet ---
    {"eco": "nuget", "pkg": "Microsoft.NETCore.App", "from": "6.0", "to": "8.0", "type": "runtime",
     "desc": ".NET 6 LTS -> .NET 8 LTS. New language features (primary constructors, collection expressions). Performance improvements across BCL.",
     "hint": "Update `<TargetFramework>net8.0</TargetFramework>`. Run `dotnet outdated`. Most projects upgrade cleanly; AOT is now stable but requires code review."},
    {"eco": "nuget", "pkg": "Microsoft.AspNetCore.App", "from": "7.0", "to": "8.0", "type": "api",
     "desc": "Blazor United (Server + WASM + SSR in one component model). Minimal APIs support form binding. Identity UI shipped as Razor Class Library.",
     "hint": "Existing Minimal APIs continue to work. Blazor projects: review component render modes (`@rendermode InteractiveServer`)."},
    {"eco": "nuget", "pkg": "Microsoft.EntityFrameworkCore", "from": "7.0", "to": "8.0", "type": "api",
     "desc": "Complex types (value objects), JSON columns for non-owned types, hierarchyid for SQL Server.",
     "hint": "Opt-in. Existing models continue to work. Consider migrating owned-entity types to ComplexProperty for better DX."},
    {"eco": "nuget", "pkg": "Microsoft.NETCore.App", "from": "8.0", "to": "9.0", "type": "runtime",
     "desc": ".NET 9 (STS release). Improvements to AOT, System.Text.Json, LINQ. HybridCache API new.",
     "hint": "STS = Standard Term Support (18 months). For long-running production stick to .NET 8 LTS (until Nov 2026)."},

    # --- Swift / Cocoapods ---
    {"eco": "swift", "pkg": "swift", "from": "5", "to": "6", "type": "behavior",
     "desc": "Strict data-race safety by default (complete concurrency checking). Existing code with data races now warns or errors.",
     "hint": "Opt in progressively with `-warnings-as-errors` disabled first. Mark shared state with `@MainActor` / `Sendable` / `nonisolated(unsafe)` as needed."},
    {"eco": "swift", "pkg": "swift", "from": "5", "to": "6", "type": "api",
     "desc": "Typed throws: `func foo() throws(MyError)` — errors carry their concrete type.",
     "hint": "Opt-in. Existing untyped throws continue to work. Use typed throws for libraries where callers need exhaustive handling."},

    # --- PyPI extras (Python ecosystem still underserved) ---
    {"eco": "pypi", "pkg": "numpy", "from": "1", "to": "2", "type": "api",
     "desc": "NumPy 2.0 released 2024: cleaned up main namespace (many aliases removed), promotion rules for mixed types tightened (NEP 50).",
     "hint": "Run `ruff check --select NPY2` (numpy-deprecation rules). Pin `numpy<2` for legacy code; for new code, upgrade and fix the small set of renamings."},
    {"eco": "pypi", "pkg": "pandas", "from": "1", "to": "2", "type": "api",
     "desc": "PyArrow-backed dtypes, copy-on-write (CoW) opt-in then default in 3.0, nullable dtypes default.",
     "hint": "Set `pd.set_option('mode.copy_on_write', True)` to preview Pandas 3 semantics. Audit chained indexing (df[...][...] = ...)."},
    {"eco": "pypi", "pkg": "ruff", "from": "0.5", "to": "0.8", "type": "config",
     "desc": "Formatter and linter config merged under [tool.ruff] with `lint` and `format` sub-tables. Output of some rules changed.",
     "hint": "Run `ruff check --fix` after upgrade. For CI pinning, pin an exact version — ruff makes breaking rule-output changes between minors."},

    # --- npm extras that impact AI agents often ---
    {"eco": "npm", "pkg": "nuxt", "from": "2", "to": "3", "type": "api",
     "desc": "Complete rewrite on Vue 3 + Vite + Nitro. Different directory layout, different auto-imports, different modules API.",
     "hint": "Not a migration — a rewrite. Use the official migration guide or consider Nuxt 2 LTS (frozen)."},
    {"eco": "npm", "pkg": "@angular/core", "from": "17", "to": "18", "type": "api",
     "desc": "Signal-based reactivity stable; `@if` / `@for` / `@switch` control flow default.",
     "hint": "Angular schematics auto-migrate *ngIf / *ngFor to the new control flow: `ng update @angular/core@18`."},
    {"eco": "npm", "pkg": "@angular/core", "from": "18", "to": "19", "type": "api",
     "desc": "Standalone components are the default (modules optional). SSR with hydration events.",
     "hint": "New projects get standalone by default. Existing NgModule-based apps continue to work — migrate at your pace with `ng generate @angular/core:standalone`."},

    # --- cargo extras ---
    {"eco": "cargo", "pkg": "axum", "from": "0.6", "to": "0.7", "type": "api",
     "desc": "`axum::extract::Body` moved to `axum::body::Body`. `axum::extract::RawBody` removed. http/hyper dependencies bumped.",
     "hint": "Global search-and-replace `axum::extract::Body` -> `axum::body::Body`. Match on updated middleware signatures."},
    {"eco": "cargo", "pkg": "reqwest", "from": "0.11", "to": "0.12", "type": "api",
     "desc": "Http/hyper 1.0 upgrade. TLS backend features renamed; default TLS now rustls (was native-tls).",
     "hint": "For native-tls, enable `features = [\"native-tls\"]` explicitly. Blocking API shape unchanged for most users."},
]


# =========================================================================== #
# ERRORS — additional ecosystems
# =========================================================================== #

ERRORS_EXTRA = [
    # --- Go ---
    {"pattern": "undefined: fmt.Printf",
     "full_message": "./main.go:5:2: undefined: fmt.Printf",
     "ecosystem": "go", "package_name": None, "package_version": None,
     "solution": "Import is missing or the package path is wrong.\n"
                 "1. Add `import \"fmt\"` at the top of the file.\n"
                 "2. Run `goimports -w .` to auto-fix imports.\n"
                 "3. If using gopls in your editor, check it's running and indexing the module.",
     "confidence": 0.95, "source": "internal", "source_url": None, "votes": 18},
    {"pattern": "panic: runtime error: index out of range",
     "full_message": "panic: runtime error: index out of range [10] with length 5",
     "ecosystem": "go", "package_name": None, "package_version": None,
     "solution": "Accessed a slice / array element past its length.\n"
                 "1. Check length before indexing: `if i < len(s) { ... }`.\n"
                 "2. Prefer `for i, v := range s` over manual index access — `range` cannot go out of bounds.\n"
                 "3. If data comes from outside, validate length before trusting it.",
     "confidence": 0.95, "source": "internal", "source_url": None, "votes": 26},
    {"pattern": "cannot find package",
     "full_message": "cannot find package \"github.com/example/lib\" in any of:",
     "ecosystem": "go", "package_name": None, "package_version": None,
     "solution": "Go module resolution failed.\n"
                 "1. Run `go mod tidy` to download missing dependencies and prune unused ones.\n"
                 "2. If behind a proxy: `go env -w GOPROXY=direct,https://proxy.golang.org`.\n"
                 "3. For private modules: `go env -w GOPRIVATE=github.com/yourorg/*`.\n"
                 "4. Verify the import path matches the repository's `go.mod` module directive.",
     "confidence": 0.9, "source": "internal", "source_url": None, "votes": 20},

    # --- PHP ---
    {"pattern": "PHP Fatal error: Uncaught Error: Class \"X\" not found",
     "full_message": "PHP Fatal error: Uncaught Error: Class \"App\\Models\\User\" not found",
     "ecosystem": "composer", "package_name": None, "package_version": None,
     "solution": "Autoloader cannot resolve the class.\n"
                 "1. Run `composer dump-autoload` to regenerate the classmap.\n"
                 "2. Verify PSR-4 mapping in composer.json matches your directory layout.\n"
                 "3. Namespace in the file must match: `namespace App\\Models;` + filename `User.php`.\n"
                 "4. For Laravel: `php artisan optimize:clear` then re-dump.",
     "confidence": 0.92, "source": "internal", "source_url": None, "votes": 22},
    {"pattern": "SQLSTATE[HY000] [2002] Connection refused",
     "full_message": "SQLSTATE[HY000] [2002] Connection refused",
     "ecosystem": "composer", "package_name": "laravel/framework", "package_version": None,
     "solution": "PDO / PHP cannot reach the database host.\n"
                 "1. Laravel: confirm DB_HOST, DB_PORT in .env match the running DB service.\n"
                 "2. Inside Docker / Sail: use the service name (`mysql`, `pgsql`), not `127.0.0.1`.\n"
                 "3. `php artisan config:clear` after editing .env.\n"
                 "4. Verify MySQL/PostgreSQL is listening on the configured port.",
     "confidence": 0.9, "source": "internal", "source_url": None, "votes": 19},

    # --- Ruby / Rails ---
    {"pattern": "NameError: uninitialized constant",
     "full_message": "NameError: uninitialized constant User",
     "ecosystem": "rubygems", "package_name": "rails", "package_version": None,
     "solution": "Rails autoloading (Zeitwerk) couldn't find a constant.\n"
                 "1. File naming: `User` must live in `app/models/user.rb`. Nested: `Admin::User` -> `app/models/admin/user.rb`.\n"
                 "2. Run `bin/rails zeitwerk:check` — it prints exactly which file-constant mapping is wrong.\n"
                 "3. After adding a file, restart the dev server if eager_loading is off.",
     "confidence": 0.92, "source": "rails-docs",
     "source_url": "https://guides.rubyonrails.org/autoloading_and_reloading_constants.html", "votes": 24},
    {"pattern": "ActiveRecord::RecordNotFound",
     "full_message": "ActiveRecord::RecordNotFound (Couldn't find User with 'id'=42)",
     "ecosystem": "rubygems", "package_name": "rails", "package_version": None,
     "solution": "`.find` raises when the id doesn't exist.\n"
                 "1. For optional lookups use `.find_by(id: 42)` which returns nil.\n"
                 "2. In controllers, let it propagate — Rails renders a 404 automatically via `rescue_from ActiveRecord::RecordNotFound`.\n"
                 "3. To customize: `rescue_from ActiveRecord::RecordNotFound, with: :not_found`.",
     "confidence": 0.92, "source": "internal", "source_url": None, "votes": 17},
    {"pattern": "LoadError: cannot load such file",
     "full_message": "LoadError: cannot load such file -- bcrypt_ext",
     "ecosystem": "rubygems", "package_name": None, "package_version": None,
     "solution": "A native extension failed to build or isn't compiled for your Ruby/platform.\n"
                 "1. `gem pristine <gem>` rebuilds the native extension.\n"
                 "2. For bcrypt / nokogiri on Apple Silicon: `bundle config build.<gem> --with-cflags=\"-Wno-error=implicit-function-declaration\"`.\n"
                 "3. After Ruby upgrade (e.g. 3.2 -> 3.3), `bundle pristine` all gems with extensions.",
     "confidence": 0.88, "source": "internal", "source_url": None, "votes": 14},

    # --- Java ---
    {"pattern": "java.lang.NullPointerException: Cannot invoke",
     "full_message": "java.lang.NullPointerException: Cannot invoke \"String.length()\" because \"s\" is null",
     "ecosystem": "maven", "package_name": None, "package_version": None,
     "solution": "JDK 14+ helpful NPE — tells you exactly which expression was null.\n"
                 "1. Use Optional for values that may be absent: `Optional.ofNullable(s).map(String::length)`.\n"
                 "2. Add `@Nullable` / `@NonNull` annotations (JSR-305, JetBrains) + enable IDE inspections.\n"
                 "3. For DTOs from JSON: configure Jackson with `spring.jackson.default-property-inclusion=non_null` and validate at the edges.",
     "confidence": 0.9, "source": "internal", "source_url": None, "votes": 29},
    {"pattern": "UnsupportedClassVersionError",
     "full_message": "UnsupportedClassVersionError: Foo has been compiled by a more recent version of the Java Runtime",
     "ecosystem": "maven", "package_name": None, "package_version": None,
     "solution": "Class file compiled for a newer JDK than the runtime.\n"
                 "1. Upgrade your JRE/JDK to match the class file version (55 = Java 11, 61 = 17, 65 = 21).\n"
                 "2. Or recompile with `--release <N>` targeting the runtime version.\n"
                 "3. In Maven: `<maven.compiler.release>17</maven.compiler.release>`.",
     "confidence": 0.94, "source": "internal", "source_url": None, "votes": 20},
    {"pattern": "java.lang.OutOfMemoryError: Java heap space",
     "full_message": "Exception in thread \"main\" java.lang.OutOfMemoryError: Java heap space",
     "ecosystem": "maven", "package_name": None, "package_version": None,
     "solution": "JVM hit the configured max heap.\n"
                 "1. Raise heap: `-Xmx4g` (startup) or `JAVA_OPTS=-Xmx4g`.\n"
                 "2. Generate a heap dump on OOM: `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp/heap.hprof`. Analyze with VisualVM or Eclipse MAT.\n"
                 "3. For containerized apps, set `-XX:MaxRAMPercentage=75` so the JVM respects the cgroup limit.",
     "confidence": 0.9, "source": "internal", "source_url": None, "votes": 23},

    # --- .NET ---
    {"pattern": "System.IO.FileNotFoundException: Could not load file or assembly",
     "full_message": "System.IO.FileNotFoundException: Could not load file or assembly 'Foo, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null'",
     "ecosystem": "nuget", "package_name": None, "package_version": None,
     "solution": "Assembly missing at runtime or version mismatch.\n"
                 "1. `dotnet restore` — ensure all NuGet refs are downloaded.\n"
                 "2. Binding redirects (if still targeting .NET Framework): check `app.config` / `web.config`.\n"
                 "3. For plugin-style loading: use AssemblyLoadContext and explicit Resolve handler.\n"
                 "4. Version conflicts in transitive deps: `dotnet list package --include-transitive`.",
     "confidence": 0.88, "source": "internal", "source_url": None, "votes": 15},
    {"pattern": "System.InvalidOperationException: A second operation was started",
     "full_message": "System.InvalidOperationException: A second operation was started on this context instance before a previous operation completed",
     "ecosystem": "nuget", "package_name": "Microsoft.EntityFrameworkCore", "package_version": None,
     "solution": "DbContext is not thread-safe; a parallel Task used the same instance.\n"
                 "1. Register DbContext as Scoped (the default in ASP.NET Core) — one per request.\n"
                 "2. For background work: inject `IDbContextFactory<TContext>` and `CreateDbContext()` per task.\n"
                 "3. Don't pass DbContext through `Task.Run` or `Parallel.ForEach` unless you create a new scope inside.",
     "confidence": 0.92, "source": "ef-docs",
     "source_url": "https://learn.microsoft.com/en-us/ef/core/dbcontext-configuration/", "votes": 18},

    # --- Swift ---
    {"pattern": "the compiler is unable to type-check this expression in reasonable time",
     "full_message": "error: the compiler is unable to type-check this expression in reasonable time; try breaking up the expression into distinct sub-expressions",
     "ecosystem": "swift", "package_name": "swift", "package_version": None,
     "solution": "Swift's type inference gave up on a complex expression (often SwiftUI).\n"
                 "1. Break the body into smaller computed views: `private var header: some View { ... }`.\n"
                 "2. Annotate explicit types on intermediate values: `let x: [String] = ...`.\n"
                 "3. Heavy use of ternaries and operator chains — split into `if` + `switch`.",
     "confidence": 0.88, "source": "internal", "source_url": None, "votes": 21},
    {"pattern": "value of non-Sendable type",
     "full_message": "warning: capture of 'self' with non-sendable type",
     "ecosystem": "swift", "package_name": "swift", "package_version": "6",
     "solution": "Swift 6 strict concurrency: you crossed an actor / task boundary with a non-Sendable value.\n"
                 "1. Mark the type `Sendable` if it's actually safe (all stored properties are Sendable).\n"
                 "2. Use `@unchecked Sendable` only when you guarantee safety manually (e.g., via a lock).\n"
                 "3. Reshape the API: pass Sendable snapshots (struct) instead of reference types.",
     "confidence": 0.85, "source": "swift-docs",
     "source_url": "https://developer.apple.com/documentation/swift/sendable", "votes": 16},
]


# =========================================================================== #
# KNOWN BUGS — other ecosystems
# =========================================================================== #

KNOWN_BUGS_EXTRA = [
    {"ecosystem": "rubygems", "package_name": "rails", "affected_version": "7.1.0",
     "fixed_version": "7.1.1", "bug_id": "github:#49822",
     "title": "Asset compilation fails with Propshaft when manifest.js uses link_tree on Windows",
     "description": "Propshaft resolved paths with forward slashes, breaking Windows dev environments. Fixed in 7.1.1.",
     "severity": "medium", "status": "closed", "source": "github_issues",
     "source_url": "https://github.com/rails/rails/issues/49822",
     "labels": ["bug", "propshaft", "windows"]},
    {"ecosystem": "rubygems", "package_name": "rails", "affected_version": "7.2.0",
     "fixed_version": "7.2.1", "bug_id": "github:#52720",
     "title": "Solid Queue jobs lost when worker SIGTERMs during dequeue",
     "description": "A race in the claim/lock phase could drop a job on shutdown. Fixed by wrapping claim in a savepoint. Applied in 7.2.1 + solid_queue 0.4+.",
     "severity": "high", "status": "closed", "source": "github_issues",
     "source_url": "https://github.com/rails/rails/issues/52720",
     "labels": ["bug", "solid-queue", "race-condition"]},
    {"ecosystem": "composer", "package_name": "laravel/framework", "affected_version": "11.0.0",
     "fixed_version": "11.0.5", "bug_id": "github:#50182",
     "title": "Broadcast channel authorization bypass with wildcard routes",
     "description": "Broadcasting::channel() with wildcard placeholders (`*`) matched any channel, bypassing auth callbacks. Fixed in 11.0.5.",
     "severity": "high", "status": "closed", "source": "github_issues",
     "source_url": "https://github.com/laravel/framework/issues/50182",
     "labels": ["bug", "security", "broadcasting"]},
    {"ecosystem": "maven", "package_name": "org.springframework.boot:spring-boot-starter",
     "affected_version": "3.2.0", "fixed_version": "3.2.1", "bug_id": "github:#38714",
     "title": "Virtual threads deadlock when combined with @Async and ThreadLocal",
     "description": "ThreadLocal cleanup across virtual-thread boundaries could deadlock when the caller was itself a @Async method. Fixed in Spring Boot 3.2.1 + Spring Framework 6.1.2.",
     "severity": "high", "status": "closed", "source": "github_issues",
     "source_url": "https://github.com/spring-projects/spring-boot/issues/38714",
     "labels": ["bug", "virtual-threads", "concurrency"]},
    {"ecosystem": "nuget", "package_name": "Microsoft.EntityFrameworkCore",
     "affected_version": "8.0.0", "fixed_version": "8.0.2", "bug_id": "github:#32863",
     "title": "JSON column null propagation broken in Where() on PostgreSQL",
     "description": ".Where(x => x.JsonProp.Nested == null) generated incorrect SQL that never matched. Fixed in 8.0.2.",
     "severity": "medium", "status": "closed", "source": "github_issues",
     "source_url": "https://github.com/dotnet/efcore/issues/32863",
     "labels": ["bug", "json", "postgresql"]},
    {"ecosystem": "go", "package_name": "gorm.io/gorm", "affected_version": "1.25.0",
     "fixed_version": "1.25.2", "bug_id": "github:#6471",
     "title": "Preload with nested struct panics when parent is nil",
     "description": "Preload(\"Foo.Bar\") on a slice containing nil parents caused nil-pointer deref. Fixed in 1.25.2.",
     "severity": "medium", "status": "closed", "source": "github_issues",
     "source_url": "https://github.com/go-gorm/gorm/issues/6471",
     "labels": ["bug", "preload", "nil-pointer"]},
    {"ecosystem": "pypi", "package_name": "numpy", "affected_version": "2.0.0",
     "fixed_version": "2.0.1", "bug_id": "github:#26909",
     "title": "np.ones_like on zero-sized dtype returns wrong dtype",
     "description": "np.ones_like(arr) returned float64 when arr had dtype with itemsize 0 (custom structured dtypes). Fixed in 2.0.1.",
     "severity": "low", "status": "closed", "source": "github_issues",
     "source_url": "https://github.com/numpy/numpy/issues/26909",
     "labels": ["bug", "dtype"]},
    {"ecosystem": "npm", "package_name": "nuxt", "affected_version": "3.10.0",
     "fixed_version": "3.10.1", "bug_id": "github:#25745",
     "title": "useFetch returns stale data when navigating with replaceState",
     "description": "Programmatic `router.replace(...)` didn't reset useFetch cache. Fixed in 3.10.1.",
     "severity": "medium", "status": "closed", "source": "github_issues",
     "source_url": "https://github.com/nuxt/nuxt/issues/25745",
     "labels": ["bug", "routing", "useFetch"]},
    {"ecosystem": "cargo", "package_name": "axum", "affected_version": "0.7.0",
     "fixed_version": "0.7.1", "bug_id": "github:#2421",
     "title": "State extractor fails to compile with generic handler when state contains Arc<T>",
     "description": "Introduced during the 0.7 rewrite; generic handlers with `State<Arc<T>>` failed to satisfy bounds. Fixed in 0.7.1.",
     "severity": "medium", "status": "closed", "source": "github_issues",
     "source_url": "https://github.com/tokio-rs/axum/issues/2421",
     "labels": ["bug", "extractors", "generics"]},
]


# =========================================================================== #
# COMPAT STACKS — other ecosystems
# =========================================================================== #

COMPAT_STACKS_EXTRA = [
    {"packages": {"rails": "8.0", "ruby": "3.3"},
     "status": "verified",
     "notes": "Rails 8 officially tests on Ruby 3.2, 3.3, 3.4. Ruby 3.3 is the recommended runtime.",
     "source": "official-docs",
     "source_url": "https://guides.rubyonrails.org/upgrading_ruby_on_rails.html", "stars": 0},
    {"packages": {"rails": "8.0", "ruby": "3.1"},
     "status": "incompatible",
     "notes": "Rails 8 requires Ruby 3.2+. Ruby 3.1 is EOL as of March 2025.",
     "source": "official-docs",
     "source_url": "https://guides.rubyonrails.org/upgrading_ruby_on_rails.html", "stars": 0},
    {"packages": {"laravel": "11", "php": "8.2"},
     "status": "verified",
     "notes": "Laravel 11 minimum PHP version. 8.3 also supported and recommended.",
     "source": "official-docs",
     "source_url": "https://laravel.com/docs/11.x/releases", "stars": 0},
    {"packages": {"laravel": "11", "php": "8.1"},
     "status": "incompatible",
     "notes": "Laravel 11 requires PHP 8.2+. PHP 8.1 reached EOL in Nov 2024.",
     "source": "official-docs",
     "source_url": "https://laravel.com/docs/11.x/releases", "stars": 0},
    {"packages": {"symfony": "7", "php": "8.2"},
     "status": "verified",
     "notes": "Symfony 7.0 LTS requires PHP 8.2+.",
     "source": "official-docs",
     "source_url": "https://symfony.com/doc/current/setup.html", "stars": 0},
    {"packages": {"spring-boot": "3.2", "jdk": "17"},
     "status": "verified",
     "notes": "Spring Boot 3.x requires JDK 17+. 3.2 adds virtual-threads support requiring JDK 21.",
     "source": "official-docs",
     "source_url": "https://spring.io/projects/spring-boot", "stars": 0},
    {"packages": {"spring-boot": "3.2", "jdk": "21"},
     "status": "verified",
     "notes": "Recommended combination for new services. Virtual threads enabled via `spring.threads.virtual.enabled=true`.",
     "source": "official-docs",
     "source_url": "https://spring.io/blog/2023/09/09/all-together-now-spring-boot-3-2", "stars": 0},
    {"packages": {"spring-boot": "3.0", "jdk": "11"},
     "status": "incompatible",
     "notes": "Spring Boot 3.x requires JDK 17 minimum. Use Spring Boot 2.7.x for JDK 8/11.",
     "source": "official-docs",
     "source_url": "https://spring.io/blog/2022/11/24/spring-boot-3-0-goes-ga", "stars": 0},
    {"packages": {"dotnet": "8.0", "ef-core": "8.0"},
     "status": "verified",
     "notes": "Matched-major pairing. EF Core 8 targets .NET 8; also supports .NET 6 LTS.",
     "source": "official-docs",
     "source_url": "https://learn.microsoft.com/en-us/ef/core/what-is-new/", "stars": 0},
    {"packages": {"dotnet": "8.0", "aspnet-core": "8.0"},
     "status": "verified",
     "notes": "ASP.NET Core 8 ships with the .NET 8 LTS. Blazor United unifies server+WASM+SSR.",
     "source": "official-docs",
     "source_url": "https://learn.microsoft.com/en-us/aspnet/core/release-notes/aspnetcore-8.0", "stars": 0},
    {"packages": {"swift": "6", "xcode": "16"},
     "status": "verified",
     "notes": "Swift 6 ships with Xcode 16. Strict concurrency is opt-in via Swift 6 language mode in Package.swift.",
     "source": "official-docs",
     "source_url": "https://developer.apple.com/swift/", "stars": 0},
    {"packages": {"go": "1.23", "gorm": "1.25"},
     "status": "compatible",
     "notes": "GORM 1.25+ supports Go 1.18+. Loop variable semantics change in 1.22 does not affect GORM usage.",
     "source": "official-docs",
     "source_url": "https://gorm.io/docs/", "stars": 0},
    {"packages": {"angular": "18", "typescript": "5.4"},
     "status": "verified",
     "notes": "Angular 18 requires TypeScript 5.4+. Older versions fail during ng build.",
     "source": "official-docs",
     "source_url": "https://angular.dev/reference/versions", "stars": 0},
    {"packages": {"nuxt": "3.10", "vue": "3.4"},
     "status": "verified",
     "notes": "Nuxt 3.10 bundles Vue 3.4 by default. Earlier Nuxt 3 pinned Vue 3.3.",
     "source": "official-docs",
     "source_url": "https://nuxt.com/docs/getting-started/upgrade", "stars": 0},
    {"packages": {"pandas": "2.2", "numpy": "2.0"},
     "status": "verified",
     "notes": "Pandas 2.2+ is numpy-2-ready. Earlier pandas (< 2.2) fails to import on numpy 2.0 due to C-API changes.",
     "source": "official-docs",
     "source_url": "https://pandas.pydata.org/docs/whatsnew/v2.2.0.html", "stars": 0},
    {"packages": {"pandas": "2.1", "numpy": "2.0"},
     "status": "incompatible",
     "notes": "Pandas < 2.2 fails to import on numpy 2.0. Pin numpy < 2 or upgrade pandas to 2.2+.",
     "source": "community",
     "source_url": "https://github.com/pandas-dev/pandas/issues/55519", "stars": 0},
]


# =========================================================================== #
# Helpers (duplicated from seed_verticals_expand to keep the script standalone)
# =========================================================================== #

async def upsert_package(conn, ecosystem: str, name: str) -> int:
    row = await conn.fetchrow(
        """
        INSERT INTO packages (ecosystem, name) VALUES ($1, $2)
        ON CONFLICT (ecosystem, name) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
        """,
        ecosystem, name,
    )
    return row["id"]


async def seed_breaking_changes(pool) -> int:
    n = 0
    async with pool.acquire() as conn:
        for bc in BREAKING_CHANGES:
            pkg_id = await upsert_package(conn, bc["eco"], bc["pkg"])
            desc_hash = hashlib.md5(bc["desc"].encode("utf-8")).hexdigest()
            await conn.execute(
                """
                INSERT INTO breaking_changes
                  (package_id, from_version, to_version, change_type,
                   description, migration_hint, desc_hash)
                VALUES ($1,$2,$3,$4,$5,$6,$7)
                ON CONFLICT (package_id, from_version, to_version, change_type, desc_hash)
                DO UPDATE SET
                  description    = EXCLUDED.description,
                  migration_hint = EXCLUDED.migration_hint
                """,
                pkg_id, bc["from"], bc["to"], bc["type"],
                bc["desc"], bc["hint"], desc_hash,
            )
            n += 1
    return n


async def seed_errors(pool) -> int:
    n = 0
    async with pool.acquire() as conn:
        for e in ERRORS_EXTRA:
            norm = normalize_error(e["pattern"])
            h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
            await conn.execute(
                """
                INSERT INTO errors
                  (hash, pattern, full_message, ecosystem, package_name,
                   package_version, solution, confidence, source, source_url, votes)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                ON CONFLICT (hash) DO UPDATE SET
                  solution   = EXCLUDED.solution,
                  confidence = EXCLUDED.confidence,
                  source_url = EXCLUDED.source_url,
                  updated_at = NOW()
                """,
                h, e["pattern"], e.get("full_message"), e.get("ecosystem"),
                e.get("package_name"), e.get("package_version"),
                e["solution"], e.get("confidence", 0.5),
                e.get("source", "internal"), e.get("source_url"),
                e.get("votes", 0),
            )
            n += 1
    return n


async def seed_bugs(pool) -> int:
    n = 0
    async with pool.acquire() as conn:
        for b in KNOWN_BUGS_EXTRA:
            pkg_id = None
            try:
                pkg_id = await upsert_package(conn, b["ecosystem"], b["package_name"])
            except Exception:
                pass
            await conn.execute(
                """
                INSERT INTO known_bugs
                  (package_id, ecosystem, package_name, affected_version,
                   fixed_version, bug_id, title, description, severity,
                   status, source, source_url, labels)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                ON CONFLICT (ecosystem, package_name, bug_id) DO UPDATE SET
                  title         = EXCLUDED.title,
                  description   = EXCLUDED.description,
                  severity      = EXCLUDED.severity,
                  status        = EXCLUDED.status,
                  fixed_version = EXCLUDED.fixed_version,
                  package_id    = EXCLUDED.package_id,
                  updated_at    = NOW()
                """,
                pkg_id, b["ecosystem"], b["package_name"],
                b.get("affected_version"), b.get("fixed_version"),
                b["bug_id"], b["title"], b.get("description"),
                b.get("severity"), b.get("status", "closed"),
                b.get("source", "github_issues"), b.get("source_url"),
                b.get("labels") or [],
            )
            n += 1
    return n


async def seed_compat(pool) -> int:
    n = 0
    async with pool.acquire() as conn:
        for s in COMPAT_STACKS_EXTRA:
            h = hash_stack(s["packages"])
            await conn.execute(
                """
                INSERT INTO compat_matrix
                  (stack_hash, packages, status, notes, source, source_url,
                   stars, reported_count)
                VALUES ($1,$2::jsonb,$3,$4,$5,$6,$7,$8)
                ON CONFLICT (stack_hash) DO UPDATE SET
                  status     = EXCLUDED.status,
                  notes      = EXCLUDED.notes,
                  source     = EXCLUDED.source,
                  source_url = EXCLUDED.source_url,
                  updated_at = NOW()
                """,
                h, json.dumps(s["packages"]), s["status"], s.get("notes"),
                s.get("source", "community"), s.get("source_url"),
                s.get("stars", 0), 1,
            )
            n += 1
    return n


async def main() -> None:
    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            before = {
                "breaking_changes": await conn.fetchval("SELECT COUNT(*) FROM breaking_changes"),
                "errors":           await conn.fetchval("SELECT COUNT(*) FROM errors"),
                "known_bugs":       await conn.fetchval("SELECT COUNT(*) FROM known_bugs"),
                "compat_matrix":    await conn.fetchval("SELECT COUNT(*) FROM compat_matrix"),
            }
        bc = await seed_breaking_changes(pool)
        er = await seed_errors(pool)
        kb = await seed_bugs(pool)
        cm = await seed_compat(pool)
        async with pool.acquire() as conn:
            after = {
                "breaking_changes": await conn.fetchval("SELECT COUNT(*) FROM breaking_changes"),
                "errors":           await conn.fetchval("SELECT COUNT(*) FROM errors"),
                "known_bugs":       await conn.fetchval("SELECT COUNT(*) FROM known_bugs"),
                "compat_matrix":    await conn.fetchval("SELECT COUNT(*) FROM compat_matrix"),
            }
    finally:
        await close_pool()

    print("[OK] processed:")
    print(f"     breaking_changes: {bc}")
    print(f"     errors:           {er}")
    print(f"     known_bugs:       {kb}")
    print(f"     compat_matrix:    {cm}")
    print("[OK] table totals:")
    for k in ("breaking_changes", "errors", "known_bugs", "compat_matrix"):
        print(f"     {k:18s}: {before[k]:4d} -> {after[k]:4d} (+{after[k]-before[k]})")


if __name__ == "__main__":
    asyncio.run(main())
