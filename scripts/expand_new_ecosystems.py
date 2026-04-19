"""Expand database with Go, Composer, Maven, NuGet, RubyGems packages"""
import asyncio
import aiohttp
import sys
import time

sys.path.insert(0, "/home/deploy/depscope")
from api.registries import fetch_package, fetch_vulnerabilities, save_package_to_db
from api.health import calculate_health_score
from api.cache import cache_set


# ═══════════════════════════════════════════════════
# TOP PACKAGES PER ECOSYSTEM
# ═══════════════════════════════════════════════════

# Go — top modules by popularity
GO_PACKAGES = [
    "github.com/gin-gonic/gin", "github.com/gorilla/mux", "github.com/go-chi/chi",
    "github.com/labstack/echo", "github.com/fiber/fiber", "github.com/gofiber/fiber",
    "github.com/stretchr/testify", "github.com/sirupsen/logrus", "github.com/uber-go/zap",
    "github.com/spf13/cobra", "github.com/spf13/viper", "github.com/urfave/cli",
    "github.com/go-gorm/gorm", "github.com/jmoiron/sqlx", "github.com/jackc/pgx",
    "github.com/go-redis/redis", "github.com/redis/go-redis",
    "github.com/golang-jwt/jwt", "github.com/dgrijalva/jwt-go",
    "github.com/grpc/grpc-go", "google.golang.org/grpc", "google.golang.org/protobuf",
    "github.com/prometheus/client_golang", "github.com/prometheus/prometheus",
    "github.com/docker/docker", "github.com/docker/compose",
    "github.com/kubernetes/kubernetes", "k8s.io/client-go", "k8s.io/apimachinery",
    "github.com/hashicorp/terraform", "github.com/hashicorp/consul", "github.com/hashicorp/vault",
    "github.com/aws/aws-sdk-go-v2", "github.com/aws/aws-lambda-go",
    "github.com/gorilla/websocket", "github.com/coder/websocket",
    "github.com/go-playground/validator", "github.com/go-chi/cors",
    "github.com/rs/zerolog", "github.com/charmbracelet/bubbletea",
    "github.com/charmbracelet/lipgloss", "github.com/charmbracelet/log",
    "github.com/tidwall/gjson", "github.com/tidwall/sjson",
    "github.com/mitchellh/mapstructure", "github.com/pelletier/go-toml",
    "github.com/fatih/color", "github.com/briandowns/spinner",
    "golang.org/x/crypto", "golang.org/x/net", "golang.org/x/text",
    "golang.org/x/sync", "golang.org/x/sys", "golang.org/x/tools",
    "golang.org/x/oauth2", "golang.org/x/time",
    "github.com/openai/openai-go",
    "github.com/sashabaranov/go-openai",
    "github.com/go-sql-driver/mysql", "github.com/mattn/go-sqlite3",
    "github.com/lib/pq", "github.com/jackc/pgx/v5",
    "github.com/nats-io/nats.go", "github.com/rabbitmq/amqp091-go",
    "github.com/segmentio/kafka-go",
    "github.com/elastic/go-elasticsearch",
    "github.com/minio/minio-go",
    "github.com/go-resty/resty", "github.com/valyala/fasthttp",
    "github.com/gohugoio/hugo", "github.com/traefik/traefik",
    "github.com/etcd-io/etcd", "github.com/cockroachdb/cockroach",
    "github.com/influxdata/influxdb", "github.com/grafana/grafana",
]

# Composer/PHP — top packages
COMPOSER_PACKAGES = [
    "laravel/framework", "laravel/laravel", "laravel/sanctum", "laravel/breeze",
    "laravel/jetstream", "laravel/horizon", "laravel/telescope", "laravel/cashier",
    "symfony/symfony", "symfony/console", "symfony/http-foundation", "symfony/routing",
    "symfony/event-dispatcher", "symfony/yaml", "symfony/process", "symfony/finder",
    "symfony/filesystem", "symfony/dotenv", "symfony/mailer", "symfony/security-bundle",
    "guzzlehttp/guzzle", "guzzlehttp/psr7", "guzzlehttp/promises",
    "monolog/monolog", "psr/log", "psr/http-message", "psr/container",
    "phpunit/phpunit", "phpunit/php-code-coverage", "pestphp/pest",
    "doctrine/orm", "doctrine/dbal", "doctrine/migrations",
    "filament/filament", "livewire/livewire",
    "spatie/laravel-permission", "spatie/laravel-medialibrary", "spatie/laravel-backup",
    "barryvdh/laravel-debugbar", "barryvdh/laravel-ide-helper",
    "league/flysystem", "league/oauth2-client", "league/csv",
    "vlucas/phpdotenv", "ramsey/uuid", "nesbot/carbon",
    "fakerphp/faker", "mockery/mockery",
    "nikic/php-parser", "phpstan/phpstan", "vimeo/psalm",
    "composer/composer", "composer/semver",
    "firebase/php-jwt", "lcobucci/jwt",
    "aws/aws-sdk-php", "google/cloud",
    "predis/predis", "phpredis/phpredis",
    "maatwebsite/excel", "mpdf/mpdf", "dompdf/dompdf",
    "intervention/image", "league/glide",
    "tymon/jwt-auth", "laravel/passport", "laravel/socialite",
    "inertiajs/inertia-laravel",
    "nwidart/laravel-modules", "beyondcode/laravel-websockets",
]

# Maven/Java — groupId:artifactId format
MAVEN_PACKAGES = [
    "org.springframework.boot:spring-boot-starter", "org.springframework.boot:spring-boot-starter-web",
    "org.springframework.boot:spring-boot-starter-data-jpa", "org.springframework.boot:spring-boot-starter-security",
    "org.springframework.boot:spring-boot-starter-test", "org.springframework.boot:spring-boot-starter-actuator",
    "org.springframework:spring-core", "org.springframework:spring-context",
    "org.springframework:spring-web", "org.springframework:spring-webmvc",
    "com.google.guava:guava", "com.google.code.gson:gson", "com.google.protobuf:protobuf-java",
    "org.apache.commons:commons-lang3", "commons-io:commons-io", "org.apache.commons:commons-collections4",
    "org.apache.httpcomponents.client5:httpclient5", "org.apache.httpcomponents:httpclient",
    "com.fasterxml.jackson.core:jackson-databind", "com.fasterxml.jackson.core:jackson-core",
    "com.fasterxml.jackson.core:jackson-annotations",
    "org.slf4j:slf4j-api", "ch.qos.logback:logback-classic", "org.apache.logging.log4j:log4j-core",
    "junit:junit", "org.junit.jupiter:junit-jupiter", "org.mockito:mockito-core",
    "org.assertj:assertj-core", "org.hamcrest:hamcrest",
    "org.projectlombok:lombok", "org.mapstruct:mapstruct",
    "io.netty:netty-all", "io.grpc:grpc-core",
    "org.apache.kafka:kafka-clients", "org.apache.kafka:kafka-streams",
    "com.squareup.okhttp3:okhttp", "com.squareup.retrofit2:retrofit",
    "org.hibernate.orm:hibernate-core", "org.mybatis:mybatis",
    "com.zaxxer:HikariCP", "org.flywaydb:flyway-core", "org.liquibase:liquibase-core",
    "io.springfox:springfox-boot-starter", "org.springdoc:springdoc-openapi-starter-webmvc-ui",
    "software.amazon.awssdk:s3", "software.amazon.awssdk:dynamodb",
    "com.amazonaws:aws-java-sdk-core",
    "io.jsonwebtoken:jjwt-api", "com.auth0:java-jwt",
    "org.elasticsearch.client:elasticsearch-rest-high-level-client",
    "redis.clients:jedis", "io.lettuce:lettuce-core",
    "org.apache.maven:maven-core", "org.apache.maven.plugins:maven-compiler-plugin",
    "io.quarkus:quarkus-core", "io.micronaut:micronaut-core",
    "org.jetbrains.kotlin:kotlin-stdlib",
]

# NuGet/.NET — package names
NUGET_PACKAGES = [
    "Newtonsoft.Json", "System.Text.Json",
    "Microsoft.Extensions.DependencyInjection", "Microsoft.Extensions.Logging",
    "Microsoft.Extensions.Configuration", "Microsoft.Extensions.Hosting",
    "Microsoft.Extensions.Http", "Microsoft.Extensions.Caching.Memory",
    "Microsoft.EntityFrameworkCore", "Microsoft.EntityFrameworkCore.SqlServer",
    "Microsoft.EntityFrameworkCore.Sqlite", "Npgsql.EntityFrameworkCore.PostgreSQL",
    "Microsoft.AspNetCore.Authentication.JwtBearer", "Microsoft.AspNetCore.Identity",
    "Microsoft.AspNetCore.Mvc.NewtonsoftJson",
    "AutoMapper", "MediatR", "FluentValidation",
    "Serilog", "Serilog.Sinks.Console", "Serilog.Sinks.File", "NLog",
    "xunit", "NUnit", "MSTest.TestFramework", "Moq", "FluentAssertions",
    "Dapper", "StackExchange.Redis", "MongoDB.Driver",
    "AWSSDK.S3", "AWSSDK.Core", "Azure.Storage.Blobs",
    "Polly", "RestSharp", "Refit",
    "Swashbuckle.AspNetCore", "NSwag.AspNetCore",
    "MassTransit", "RabbitMQ.Client",
    "Hangfire.Core", "Quartz",
    "CsvHelper", "EPPlus", "ClosedXML",
    "HtmlAgilityPack", "AngleSharp",
    "MailKit", "MimeKit",
    "Humanizer.Core", "Bogus",
    "Grpc.Net.Client", "Google.Protobuf",
    "Microsoft.ML", "Microsoft.SemanticKernel",
    "OpenTelemetry", "Prometheus-net",
    "IdentityServer4", "Duende.IdentityServer",
    "SignalR", "Microsoft.AspNetCore.SignalR",
    "Docker.DotNet", "Elastic.Clients.Elasticsearch",
]

# RubyGems — gem names
RUBYGEMS_PACKAGES = [
    "rails", "rack", "sinatra", "hanami",
    "bundler", "rake", "thor",
    "rspec", "rspec-rails", "minitest", "capybara", "factory_bot",
    "devise", "omniauth", "jwt", "bcrypt",
    "puma", "unicorn", "passenger",
    "pg", "mysql2", "sqlite3", "redis", "mongoid",
    "activerecord", "sequel", "rom-rb",
    "sidekiq", "resque", "delayed_job", "good_job",
    "nokogiri", "faraday", "httparty", "rest-client", "typhoeus",
    "rubocop", "rubocop-rails", "rubocop-rspec", "standard",
    "pry", "byebug", "debug",
    "dotenv", "figaro",
    "pundit", "cancancan",
    "aws-sdk-s3", "aws-sdk-core", "fog-aws",
    "stripe", "braintree",
    "paperclip", "carrierwave", "active_storage",
    "kaminari", "pagy", "will_paginate",
    "slim", "haml", "erb",
    "jbuilder", "active_model_serializers", "jsonapi-serializer",
    "letter_opener", "action_mailer",
    "whenever", "clockwork",
    "chartkick", "groupdate",
    "turbo-rails", "stimulus-rails", "importmap-rails",
    "tailwindcss-rails", "bootstrap",
    "sorbet", "steep",
    "dry-rb", "dry-validation", "dry-types",
    "graphql", "graphql-ruby",
    "elasticsearch-ruby", "searchkick",
]


async def process_package(eco, name, processed):
    """Fetch, score, and save a single package."""
    key = f"{eco}:{name}"
    if key in processed:
        return False
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

        processed.add(key)
        return True
    except Exception as e:
        return False


async def search_go_packages():
    """Search pkg.go.dev for popular Go modules."""
    # Go proxy doesn't have search — we use our curated list + fetch from pkg.go.dev index
    return GO_PACKAGES


async def search_composer_packages(keyword, size=50):
    """Search packagist.org for PHP packages."""
    url = f"https://packagist.org/search.json?q={keyword}&per_page={size}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return [p["name"] for p in data.get("results", [])]
    except:
        return []


async def search_maven_packages(keyword, size=20):
    """Search Maven Central for Java packages."""
    url = f"https://search.maven.org/solrsearch/select?q={keyword}&rows={size}&wt=json"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return [f"{d['g']}:{d['a']}" for d in data.get("response", {}).get("docs", [])]
    except:
        return []


async def search_nuget_packages(keyword, size=20):
    """Search NuGet for .NET packages."""
    url = f"https://azuresearch-usnc.nuget.org/query?q={keyword}&take={size}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return [p["id"] for p in data.get("data", [])]
    except:
        return []


async def search_rubygems_packages(keyword, size=30):
    """Search RubyGems."""
    url = f"https://rubygems.org/api/v1/search.json?query={keyword}&page=1"
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "DepScope/0.1"}
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return [g["name"] for g in data[:size]]
    except:
        return []


COMPOSER_KEYWORDS = [
    "laravel", "symfony", "wordpress", "http", "database", "auth",
    "testing", "logging", "queue", "cache", "image", "pdf",
    "api", "graphql", "security", "payment", "mail",
]

MAVEN_KEYWORDS = [
    "spring", "jackson", "guava", "apache commons", "logging",
    "testing", "database", "http", "security", "json",
    "grpc", "kafka", "redis", "aws", "cloud",
]

NUGET_KEYWORDS = [
    "aspnetcore", "entityframework", "logging", "authentication",
    "testing", "database", "http", "json", "redis", "aws",
    "grpc", "messaging", "caching", "validation",
]

RUBYGEMS_KEYWORDS = [
    "rails", "web", "testing", "database", "authentication",
    "http", "json", "redis", "aws", "background",
    "api", "security", "search", "monitoring",
]


async def main():
    processed = set()
    total_new = 0
    start = time.time()

    # Load existing packages
    import asyncpg
    conn = await asyncpg.connect("postgresql://depscope:${DB_PASSWORD}@localhost:5432/depscope")
    rows = await conn.fetch("SELECT ecosystem, name FROM packages")
    for r in rows:
        processed.add(f"{r['ecosystem']}:{r['name']}")
    await conn.close()

    print(f"Existing: {len(processed)} packages\n")

    # ═══ GO ═══
    print(f"=== GO ({len(GO_PACKAGES)} packages) ===")
    new_go = [n for n in GO_PACKAGES if f"go:{n}" not in processed]
    print(f"  New: {len(new_go)}")
    for i, name in enumerate(new_go):
        ok = await process_package("go", name, processed)
        if ok:
            total_new += 1
            print(f"  ✓ {name}")
        else:
            print(f"  ✗ {name}")
        await asyncio.sleep(0.3)
    print(f"  Go done: {total_new} new\n")

    # ═══ COMPOSER ═══
    go_count = total_new
    print(f"=== COMPOSER (curated + search) ===")
    composer_names = set(COMPOSER_PACKAGES)
    for kw in COMPOSER_KEYWORDS:
        found = await search_composer_packages(kw, size=30)
        composer_names.update(found)
        await asyncio.sleep(0.5)
    print(f"  Total unique: {len(composer_names)}")
    new_composer = [n for n in composer_names if f"composer:{n}" not in processed]
    print(f"  New: {len(new_composer)}")
    for i, name in enumerate(new_composer):
        ok = await process_package("composer", name, processed)
        if ok:
            total_new += 1
        if (i + 1) % 20 == 0:
            print(f"  Processed {i+1}/{len(new_composer)}, +{total_new - go_count} composer")
        await asyncio.sleep(0.3)
    print(f"  Composer done: +{total_new - go_count}\n")

    # ═══ MAVEN ═══
    pre_maven = total_new
    print(f"=== MAVEN (curated + search) ===")
    maven_names = set(MAVEN_PACKAGES)
    for kw in MAVEN_KEYWORDS:
        found = await search_maven_packages(kw, size=20)
        maven_names.update(found)
        await asyncio.sleep(0.5)
    print(f"  Total unique: {len(maven_names)}")
    new_maven = [n for n in maven_names if f"maven:{n}" not in processed]
    print(f"  New: {len(new_maven)}")
    for i, name in enumerate(new_maven):
        ok = await process_package("maven", name, processed)
        if ok:
            total_new += 1
        if (i + 1) % 20 == 0:
            print(f"  Processed {i+1}/{len(new_maven)}, +{total_new - pre_maven} maven")
        await asyncio.sleep(0.5)  # Maven has stricter rate limits
    print(f"  Maven done: +{total_new - pre_maven}\n")

    # ═══ NUGET ═══
    pre_nuget = total_new
    print(f"=== NUGET (curated + search) ===")
    nuget_names = set(NUGET_PACKAGES)
    for kw in NUGET_KEYWORDS:
        found = await search_nuget_packages(kw, size=20)
        nuget_names.update(found)
        await asyncio.sleep(0.5)
    print(f"  Total unique: {len(nuget_names)}")
    new_nuget = [n for n in nuget_names if f"nuget:{n}" not in processed]
    print(f"  New: {len(new_nuget)}")
    for i, name in enumerate(new_nuget):
        ok = await process_package("nuget", name, processed)
        if ok:
            total_new += 1
        if (i + 1) % 20 == 0:
            print(f"  Processed {i+1}/{len(new_nuget)}, +{total_new - pre_nuget} nuget")
        await asyncio.sleep(0.3)
    print(f"  NuGet done: +{total_new - pre_nuget}\n")

    # ═══ RUBYGEMS ═══
    pre_ruby = total_new
    print(f"=== RUBYGEMS (curated + search) ===")
    ruby_names = set(RUBYGEMS_PACKAGES)
    for kw in RUBYGEMS_KEYWORDS:
        found = await search_rubygems_packages(kw, size=30)
        ruby_names.update(found)
        await asyncio.sleep(1)  # RubyGems rate limit is strict
    print(f"  Total unique: {len(ruby_names)}")
    new_ruby = [n for n in ruby_names if f"rubygems:{n}" not in processed]
    print(f"  New: {len(new_ruby)}")
    for i, name in enumerate(new_ruby):
        ok = await process_package("rubygems", name, processed)
        if ok:
            total_new += 1
        if (i + 1) % 20 == 0:
            print(f"  Processed {i+1}/{len(new_ruby)}, +{total_new - pre_ruby} rubygems")
        await asyncio.sleep(0.5)
    print(f"  RubyGems done: +{total_new - pre_ruby}\n")

    elapsed = int(time.time() - start)
    print(f"=== DONE: {total_new} new packages added in {elapsed}s ===")
    print(f"  Go: {go_count}, Composer: {pre_maven - go_count}, Maven: {pre_nuget - pre_maven}, NuGet: {pre_ruby - pre_nuget}, RubyGems: {total_new - pre_ruby}")


asyncio.run(main())
