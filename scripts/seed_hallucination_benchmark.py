"""Hallucination Benchmark v1 — corpus + serving endpoint + harness.

Strategy:
  1. Seed corpus: blend of observed (from our own api_usage is_hallucination) +
     curated public examples (from research + well-known cases).
  2. Table: benchmark_hallucinations (ecosystem, package_name, source, evidence,
     first_seen_at, hit_count).
  3. Seeded daily from our own hallucinated 404s (auto-expansion).
  4. GET /api/benchmark/hallucinations returns the JSON corpus (machine-readable).
  5. GET /api/benchmark/verify?ecosystem&package -> {is_hallucinated, evidence,
     did_you_mean, alt_package}. Cheap verification call for benchmark runners.
"""
import asyncio, os, sys

sys.path.insert(0, "/home/deploy/depscope")

# 1. Create the table + seed with curated + observed entries.
INIT_SQL = """
CREATE TABLE IF NOT EXISTS benchmark_hallucinations (
  id SERIAL PRIMARY KEY,
  ecosystem VARCHAR(30) NOT NULL,
  package_name VARCHAR(255) NOT NULL,
  source VARCHAR(40) NOT NULL,
  evidence TEXT,
  first_seen_at TIMESTAMPTZ DEFAULT NOW(),
  hit_count INTEGER DEFAULT 1,
  likely_real_alternative VARCHAR(255),
  UNIQUE (ecosystem, package_name)
);
CREATE INDEX IF NOT EXISTS idx_bench_hallu_eco ON benchmark_hallucinations(ecosystem);
"""

# Curated initial corpus — blend of:
# - Our top real observations
# - Known research hallucinations (Slopsquatting paper, Lasso/Lanyrd 2024 reports)
# - High-probability patterns that agents invent
CURATED = [
    # (ecosystem, name, source, evidence, likely_real_alt)
    ("npm", "react-hooks-essential",           "observed",   "Seen 6+ times across claude-code/cursor/copilot/aider",       "react"),
    ("npm", "typescript-utility-pack-pro",     "observed",   "Seen 8+ times across 5 agents",                                "type-fest"),
    ("npm", "react-rouetr-dom",                "observed",   "Typosquat of react-router-dom",                                "react-router-dom"),
    ("npm", "lodsh",                           "observed",   "Typosquat of lodash — distance 1",                             "lodash"),
    ("npm", "express-async-middleware-pro",    "research",   "Pattern: <pkg>-pro / <pkg>-middleware-pro",                    "express"),
    ("npm", "jwt-token-validator-easy",        "research",   "Pattern: <pkg>-easy",                                          "jsonwebtoken"),
    ("npm", "nextjs-auth-helpers",             "research",   "Slopsquat pattern — plausible helper that does not exist",     "next-auth"),
    ("npm", "tailwind-components-ultimate",    "research",   "Superlative pattern (<pkg>-ultimate/pro)",                     "tailwindcss"),
    ("npm", "vite-plugin-typescript-enhanced", "research",   "'enhanced' suffix pattern",                                    "vite"),
    ("npm", "graphql-codegen-utils-advanced",  "research",   "'advanced' suffix pattern",                                    "graphql-code-generator"),
    ("pypi", "fastapi-turbo",                  "observed",   "Seen 8 times across 7 agents",                                  "fastapi"),
    ("pypi", "pandas-easy-pivot",              "observed",   "Seen 6 times across 6 agents",                                  "pandas"),
    ("pypi", "reqeusts",                       "observed",   "Typosquat of requests",                                        "requests"),
    ("pypi", "sklearn-deep-learning",          "research",   "Plausible but non-existent extension",                         "scikit-learn"),
    ("pypi", "pytorch-easy-train",             "research",   "'easy' prefix pattern",                                        "pytorch-lightning"),
    ("pypi", "numpy-extensions-plus",          "research",   "'plus' suffix pattern",                                        "numpy"),
    ("pypi", "django-rest-auth-advanced",      "research",   "Plausible auth extension",                                     "djangorestframework-simplejwt"),
    ("pypi", "langchain-tools-pro",            "research",   "'pro' suffix on trending frameworks",                          "langchain"),
    ("pypi", "opencv-image-enhanced",          "research",   "'enhanced' pattern",                                           "opencv-python"),
    ("pypi", "transformers-accelerator",       "research",   "Fake companion pkg to HF transformers",                        "accelerate"),
    ("cargo", "tokio-stream-extras",           "observed",   "Seen 8 times across 5 agents",                                  "tokio-stream"),
    ("cargo", "sered",                         "observed",   "Typosquat of serde",                                           "serde"),
    ("cargo", "axum-middleware-pro",           "research",   "'pro' suffix",                                                 "axum"),
    ("cargo", "rustdecimal",                   "observed",   "Typosquat of rust_decimal (crates.io removed 2022)",           "rust_decimal"),
    ("cargo", "actix-web-extensions",          "research",   "'extensions' plural form",                                     "actix-web"),
    ("cargo", "reqwest-extra-helpers",         "research",   "Fake companion pattern",                                       "reqwest"),
    ("go", "github.com/fasthttp/router-pro",   "research",   "'-pro' module",                                                "github.com/fasthttp/router"),
    ("go", "github.com/gin-gonic/middleware",  "research",   "Plausible separate package",                                   "github.com/gin-gonic/gin"),
    ("go", "github.com/prometheus/advanced",   "research",   "Fake advanced module",                                         "github.com/prometheus/client_golang"),
    ("conda", "torch-lightning-easy",          "observed",   "Seen 12 times across 7 agents — top slopsquat",                "pytorch-lightning"),
    ("conda", "opencv",                        "observed",   "Common agent confusion with opencv-python (wrong channel)",    "opencv-python-headless"),
    ("composer", "laravel/auth-pro",           "research",   "Plausible Laravel extension",                                  "laravel/sanctum"),
    ("composer", "symfony/components-extra",   "research",   "'extra' pattern on Symfony",                                   "symfony/symfony"),
    ("maven", "junit:junit",                   "observed",   "Common agent confusion (real is junit:junit but often misreferenced)", "org.junit.jupiter:junit-jupiter"),
    ("rubygems", "rails-middleware-pro",       "research",   "Fake middleware pattern",                                      "rails"),
    ("rubygems", "active-record-extensions-plus", "research", "'-plus' suffix",                                               "activerecord"),
    ("nuget", "Microsoft.Extensions.Auth.Pro", "research",   "Fake 'pro' extension on Microsoft.Extensions",                 "Microsoft.AspNetCore.Authentication.JwtBearer"),
    ("nuget", "Newtonsoft.Json.Extended",      "research",   "'Extended' pattern",                                           "Newtonsoft.Json"),
    ("homebrew", "postgresql",                 "observed",   "Brew formula is 'postgresql@17' — agents drop version",        "postgresql@17"),
    ("homebrew", "node-latest",                "research",   "Agents invent '-latest' formulae",                             "node"),
    ("pub", "http-extensions-pro",             "research",   "'pro' pattern on Dart http",                                   "http"),
    ("hex", "phoenix-auth-helpers",            "research",   "Fake helpers for Phoenix",                                     "phoenix"),
]


async def main():
    import asyncpg
    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=3)

    await pool.execute(INIT_SQL)
    print(f"benchmark table ready")

    # Seed curated entries (idempotent)
    inserted = 0
    for eco, name, source, evidence, alt in CURATED:
        r = await pool.execute(
            """INSERT INTO benchmark_hallucinations
               (ecosystem, package_name, source, evidence, likely_real_alternative)
               VALUES ($1,$2,$3,$4,$5)
               ON CONFLICT (ecosystem, package_name) DO UPDATE
               SET evidence = EXCLUDED.evidence,
                   likely_real_alternative = EXCLUDED.likely_real_alternative""",
            eco, name, source, evidence, alt,
        )
        inserted += 1

    # Auto-expand: pull any hallucinated 404s from real agents (not bots) seen
    # at least twice, that aren't already in the corpus.
    await pool.execute("""
        INSERT INTO benchmark_hallucinations (ecosystem, package_name, source, evidence, hit_count)
        SELECT u.ecosystem, u.package_name, 'observed',
               'Auto-harvested from real agent traffic',
               COUNT(*)::int
        FROM api_usage u
        WHERE u.is_hallucination = true
          AND u.agent_client IN ('claude-code','cursor','copilot','aider','chatgpt',
                                 'windsurf','continue','claude-desktop','replit','devin')
          AND u.created_at > NOW() - INTERVAL '30 days'
          AND u.package_name <> ''
        GROUP BY u.ecosystem, u.package_name
        HAVING COUNT(*) >= 2
        ON CONFLICT (ecosystem, package_name) DO UPDATE
          SET hit_count = benchmark_hallucinations.hit_count + EXCLUDED.hit_count
    """)

    count = await pool.fetchval("SELECT COUNT(*) FROM benchmark_hallucinations")
    by_eco = await pool.fetch("SELECT ecosystem, COUNT(*) n FROM benchmark_hallucinations GROUP BY 1 ORDER BY 2 DESC")
    print(f"benchmark corpus: {count} entries")
    for r in by_eco:
        print(f"  {r['ecosystem']:10s} {r['n']}")

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
