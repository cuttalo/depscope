<div align="center">

# DepScope

**Package Intelligence for AI Agents**

Check health, vulnerabilities, and versions before installing. One API call for 17 ecosystems. Free, no auth.

Save tokens. Save energy. Ship safer code.

[![API Status](https://img.shields.io/badge/API-live-brightgreen)](https://depscope.dev)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Ecosystems](https://img.shields.io/badge/ecosystems-17-cyan)](https://depscope.dev/api-docs)
[![Packages](https://img.shields.io/badge/indexed-14.7k%2B-orange)](https://depscope.dev/stats)
[![MCP Tools](https://img.shields.io/badge/MCP%20tools-12-purple)](https://www.npmjs.com/package/depscope-mcp)

[Website](https://depscope.dev) | [API Docs](https://depscope.dev/api-docs) | [Swagger](https://depscope.dev/docs) | [GPT Store](https://chatgpt.com/g/g-69e02d12226c8191a7f24f3a8481bc4e-depscope) | [RapidAPI](https://rapidapi.com/depscope/api/depscope)

</div>

---

## Why DepScope?

AI coding agents (Claude, ChatGPT, Cursor, Copilot, Aider, Windsurf) suggest packages every day. But they:

- Hallucinate package names that don't exist
- Suggest deprecated packages (143 indexed in our DB are still being recommended)
- Have no idea about vulnerabilities
- Guess version numbers from stale training data
- Re-search the same runtime errors millions of times
- Bump versions without knowing if the combo has ever worked

**They also make the same calls independently**, over and over — millions of redundant requests to npm, PyPI, OSV for the exact same data. Wasted bandwidth, tokens, and energy.

DepScope is the shared infrastructure fix: one service fetches the data, caches it, serves every agent instantly.

## Three verticals, one API

| Vertical | Endpoint | What it answers |
|----------|----------|-----------------|
| **Package health** | `/api/check/{eco}/{pkg}` | Is this package safe, maintained, up-to-date? |
| **Error -> Fix DB** | `/api/error/resolve` (POST) | I just hit this stack trace. What's the verified fix? |
| **Compatibility Matrix** | `/api/compat?packages=...` | Is `Next 16 + React 19 + Prisma 6` a verified combo? |

Same free API. Same 200 req/min. Same shared-infrastructure philosophy.

## 17 Ecosystems. One Endpoint.

```bash
curl https://depscope.dev/api/check/{ecosystem}/{package}
```

| Language | Ecosystem | Example |
|----------|-----------|---------|
| JavaScript/Node | `npm` | `/api/check/npm/express` |
| Python | `pypi` | `/api/check/pypi/django` |
| Rust | `cargo` | `/api/check/cargo/tokio` |
| Go | `go` | `/api/check/go/github.com/gin-gonic/gin` |
| PHP | `composer` | `/api/check/composer/laravel/framework` |
| Java/Kotlin | `maven` | `/api/check/maven/org.springframework.boot/spring-boot-starter` |
| .NET/C# | `nuget` | `/api/check/nuget/Newtonsoft.Json` |
| Ruby | `rubygems` | `/api/check/rubygems/rails` |
| Dart/Flutter | `pub` | `/api/check/pub/http` |
| Elixir | `hex` | `/api/check/hex/ecto` |
| Swift | `swift` | `/api/check/swift/vapor` |
| iOS | `cocoapods` | `/api/check/cocoapods/AFNetworking` |
| Perl | `cpan` | `/api/check/cpan/DateTime` |
| Haskell | `hackage` | `/api/check/hackage/lens` |
| R | `cran` | `/api/check/cran/dplyr` |
| Data Science | `conda` | `/api/check/conda/scipy` |
| macOS CLI | `homebrew` | `/api/check/homebrew/git` |

## Quick Start

```bash
# Full health check
curl https://depscope.dev/api/check/npm/express

# LLM-optimized plain text (saves ~74% tokens vs JSON)
curl https://depscope.dev/api/prompt/npm/express

# Just the latest version (use before any install)
curl https://depscope.dev/api/latest/npm/react

# Does this package exist?
curl https://depscope.dev/api/exists/npm/my-package

# Find alternatives when deprecated
curl https://depscope.dev/api/alternatives/npm/request

# Compare packages
curl https://depscope.dev/api/compare/npm/express,fastify,hono

# Scan entire project
curl -X POST https://depscope.dev/api/scan \
  -H "Content-Type: application/json" \
  -d '{"ecosystem":"npm","packages":{"express":"*","lodash":"*"}}'

# Resolve a runtime error to a verified fix
curl -X POST https://depscope.dev/api/error/resolve \
  -H "Content-Type: application/json" \
  -d '{"error":"ERR_PACKAGE_PATH_NOT_EXPORTED","ecosystem":"npm","package":"next"}'

# Check a stack compatibility
curl "https://depscope.dev/api/compat?packages=next@16,react@19,prisma@6"

# Known bugs for a version (non-CVE)
curl https://depscope.dev/api/bugs/npm/next

# What's trending right now
curl https://depscope.dev/api/trending
```

No auth. No signup. No API key required. 200 req/min free tier.

Optional auth via magic-link login gives you `ds_live_xxx` / `ds_test_xxx` keys for higher limits and usage analytics.

## Add to your AI agent (one line)

**Claude Code** — in `CLAUDE.md`:
```
## DEPSCOPE — Before any install: curl depscope.dev/api/check/{eco}/{pkg}
```

**Cursor** — in `.cursorrules`:
```
Before any install: curl depscope.dev/api/check/{eco}/{pkg} — no auth, free
```

**Windsurf, Copilot, Aider** — same pattern, one line in your agent's rule file.

**ChatGPT** — search "DepScope" in the GPT Store.

**MCP (12 tools)** — `npm install -g depscope-mcp` and add to your MCP config. Tools: `check_package`, `get_latest_version`, `package_exists`, `search_packages`, `find_alternatives`, `compare_packages`, `get_vulnerabilities`, `scan_project`, `get_health_score`, `resolve_error`, `check_compat`, `get_bugs`.

## Endpoints

### Package health
| Endpoint | What it does | When to use |
|----------|-------------|-------------|
| `GET /api/check/{eco}/{pkg}` | Full health report | "Is this package safe?" |
| `GET /api/prompt/{eco}/{pkg}` | LLM-optimized plain text (~74% token reduction) | Feeding result into an LLM context |
| `GET /api/latest/{eco}/{pkg}` | Just the version | Before any install |
| `GET /api/exists/{eco}/{pkg}` | Exists yes/no | Before suggesting a package |
| `GET /api/search/{eco}?q=...` | Search by keyword | "I need a library for X" |
| `GET /api/alternatives/{eco}/{pkg}` | Replacement suggestions | When package is deprecated |
| `GET /api/compare/{eco}/{a},{b},{c}` | Side-by-side comparison | "Express vs Fastify?" |
| `GET /api/vulns/{eco}/{pkg}` | Vulnerability list | Security audit |
| `GET /api/health/{eco}/{pkg}` | Quick score (0-100) | Fast check |
| `GET /api/history/{eco}/{pkg}` | 90-day health trend | Tracking regressions |
| `GET /api/tree/{eco}/{pkg}` | Transitive deps with health | Dependency audit |
| `GET /api/bundle/{eco}/{pkg}` | Min+gzip bundle size | Frontend budget |
| `GET /api/types/{eco}/{pkg}` | TypeScript quality | Typing coverage |
| `GET /api/licenses/{eco}/{pkg}` | License audit | Compliance check |
| `POST /api/scan` | Audit all deps at once | Project-wide audit |
| `GET /api/trending` | Trending packages | What the ecosystem is installing |
| `GET /api/now` | Current UTC time | Agents need this |

### Error -> Fix DB
| Endpoint | What it does |
|----------|-------------|
| `GET /api/error?code=X` | Lookup a known error code |
| `POST /api/error/resolve` | POST a stack trace, get verified fixes with package+version context |

### Compatibility Matrix & Known Bugs
| Endpoint | What it does |
|----------|-------------|
| `GET /api/compat?packages=...` | Is this combo a verified working stack? |
| `GET /api/bugs/{eco}/{pkg}` | Non-CVE known bugs affecting specific versions |

## Health Score

The score (0-100) is calculated algorithmically from 5 signals. No LLM, pure math, runs in milliseconds:

| Signal | Max | Source |
|--------|:---:|--------|
| Maintenance | 25 | Days since last release |
| Security | 25 | CVEs from OSV, filtered to latest version |
| Popularity | 20 | Weekly downloads from registry |
| Maturity | 15 | Total version count |
| Community | 15 | Maintainers + GitHub stars |

**Key innovation**: we only show vulnerabilities that affect the latest version. Django went from 272 historical "vulnerabilities" to just 1 that matters today. 402 vulnerabilities tracked across the whole index.

## Example Response

```json
{
  "package": "express",
  "ecosystem": "npm",
  "latest_version": "5.2.1",
  "health": {
    "score": 85,
    "risk": "low",
    "breakdown": {
      "maintenance": 25,
      "security": 25,
      "popularity": 20,
      "maturity": 15,
      "community": 10
    }
  },
  "vulnerabilities": { "count": 0 },
  "recommendation": {
    "action": "safe_to_use",
    "summary": "express@5.2.1 is safe to use (health: 85/100)"
  }
}
```

## Free Because It Should Be

Package metadata is infrastructure, not a premium feature. The marginal cost of serving the 1,000,000th request for `express` is zero — Redis cache handles it in milliseconds.

Running this once for everyone is cheaper than having millions of AI agents do it independently. Less waste on public registries, less energy, fewer tokens burned re-processing identical JSON.

- **Free tier**: 200 req/min, no auth, full data on every endpoint
- **Cache TTL**: 1 hour for metadata, 6 hours for vulnerabilities
- **Coverage**: 14,700+ packages pre-indexed across 17 ecosystems, any package fetched on-demand
- **Vulnerabilities**: 402 tracked (latest-version-filtered, not historical noise)
- **MCP**: 12 tools covering all three verticals

## Ecosystem

- **MCP Server** (12 tools): [depscope-mcp](https://www.npmjs.com/package/depscope-mcp) — `npm install -g depscope-mcp`
- **ChatGPT GPT**: search "DepScope" in GPT Store
- **RapidAPI**: [hub listing](https://rapidapi.com/depscope/api/depscope)
- **OpenAPI Spec**: [depscope.dev/openapi.json](https://depscope.dev/openapi.json)
- **AI Plugin Manifest**: [depscope.dev/.well-known/ai-plugin.json](https://depscope.dev/.well-known/ai-plugin.json)
- **llms.txt**: [depscope.dev/llms.txt](https://depscope.dev/llms.txt)

## Built With

FastAPI · PostgreSQL 17 · Redis · Next.js 16

Operated by [Cuttalo srl](https://cuttalo.com). Feedback at depscope@cuttalo.com.

## License

MIT — see [LICENSE](LICENSE).
