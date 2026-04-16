<div align="center">

# DepScope

**Package Intelligence for AI Agents**

Check health, vulnerabilities, and versions before installing. Free API, no auth.

[![API Status](https://img.shields.io/badge/API-live-brightgreen)](https://depscope.dev)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Ecosystems](https://img.shields.io/badge/ecosystems-npm%20%7C%20PyPI%20%7C%20Cargo-cyan)](https://depscope.dev/api-docs)

[Website](https://depscope.dev) | [API Docs](https://depscope.dev/api-docs) | [Swagger](https://depscope.dev/docs) | [GPT Store](https://chatgpt.com/g/g-depscope)

</div>

---

## Why DepScope?

AI coding agents (Claude, ChatGPT, Cursor, Copilot) suggest packages every day. But they:
- Hallucinate package names that don't exist
- Suggest deprecated packages
- Don't know about vulnerabilities
- Guess version numbers from training data

**DepScope fixes this.** We aggregate data from registries + vulnerability databases once, and serve it to any agent instantly.

## Quick Start

```bash
# Full health check
curl https://depscope.dev/api/check/npm/express

# Just the latest version (use before any install)
curl https://depscope.dev/api/latest/npm/react

# Does this package exist?
curl https://depscope.dev/api/exists/npm/my-package

# Search for packages
curl https://depscope.dev/api/search/npm?q=http+client

# Find alternatives to deprecated packages
curl https://depscope.dev/api/alternatives/npm/request

# Compare packages
curl https://depscope.dev/api/compare/npm/express,fastify,hono

# Scan entire project
curl -X POST https://depscope.dev/api/scan \
  -H "Content-Type: application/json" \
  -d '{"ecosystem":"npm","packages":{"express":"*","lodash":"*"}}'

# Current time (agents don't know what time it is)
curl https://depscope.dev/api/now
```

No auth. No signup. No API key. 200 req/min.

## Endpoints

| Endpoint | What it does | When to use |
|----------|-------------|-------------|
| `GET /api/check/{eco}/{pkg}` | Full health report | "Is this package safe?" |
| `GET /api/latest/{eco}/{pkg}` | Just the version | Before any `npm install` |
| `GET /api/exists/{eco}/{pkg}` | Exists yes/no | Before suggesting a package |
| `GET /api/search/{eco}?q=...` | Search by keyword | "I need a library for X" |
| `GET /api/alternatives/{eco}/{pkg}` | Replacement suggestions | When package is deprecated |
| `GET /api/compare/{eco}/{a},{b},{c}` | Side-by-side comparison | "Express vs Fastify?" |
| `GET /api/vulns/{eco}/{pkg}` | Vulnerability list | Security audit |
| `GET /api/health/{eco}/{pkg}` | Quick score (0-100) | Fast check |
| `POST /api/scan` | Audit all deps at once | Project-wide audit |
| `GET /api/now` | Current UTC time | Agents need this |

## Health Score

The score (0-100) is calculated algorithmically from 5 signals:

| Signal | Max | Source |
|--------|-----|--------|
| Maintenance | 25 | Days since last release |
| Security | 25 | Known CVEs (OSV database) |
| Popularity | 20 | Weekly downloads |
| Maturity | 15 | Version count |
| Community | 15 | Active maintainers |

No AI. No LLM. Pure algorithm. Runs in milliseconds.

## Integration

### Claude Code / Cursor / Windsurf (MCP)

```json
{
  "mcpServers": {
    "depscope": {
      "command": "npx",
      "args": ["depscope-mcp"]
    }
  }
}
```

### ChatGPT (GPT Store)

Search "DepScope" in the GPT Store, or use the OpenAPI spec:
```
https://depscope.dev/openapi-gpt.json
```

### Python

```python
import requests

# Check a package
r = requests.get("https://depscope.dev/api/check/pypi/django")
data = r.json()
print(f"Health: {data['health']['score']}/100")
print(f"Recommendation: {data['recommendation']['summary']}")
```

### JavaScript / Node.js

```javascript
const res = await fetch("https://depscope.dev/api/check/npm/express");
const data = await res.json();
console.log(`Health: ${data.health.score}/100`);
console.log(`Recommendation: ${data.recommendation.summary}`);
```

### GitHub Actions

```yaml
- name: Check dependencies health
  run: |
    curl -s -X POST https://depscope.dev/api/scan \
      -H "Content-Type: application/json" \
      -d "{\"ecosystem\":\"npm\",\"packages\":$(cat package.json | jq '.dependencies')}" \
      | jq '.project_risk'
```

### LangChain

```python
from langchain.tools import tool

@tool
def check_package(ecosystem: str, package: str) -> str:
    """Check if a software package is safe to install."""
    import requests
    r = requests.get(f"https://depscope.dev/api/check/{ecosystem}/{package}")
    return r.json()["recommendation"]["summary"]
```

## Supported Ecosystems

- **npm** — 2.5M+ packages
- **PyPI** — 500K+ packages
- **Cargo** — 150K+ crates

## AI Agent Discovery

| Protocol | URL |
|----------|-----|
| OpenAPI | `https://depscope.dev/openapi.json` |
| ChatGPT Actions | `https://depscope.dev/openapi-gpt.json` |
| AI Plugin | `https://depscope.dev/.well-known/ai-plugin.json` |
| LLMs.txt | `https://depscope.dev/llms.txt` |
| MCP Server | [depscope-mcp](https://github.com/vincenzorubino27031980/depscope-mcp) |

## Examples

```bash
# Express: safe to use?
$ curl -s depscope.dev/api/check/npm/express | jq '.recommendation.summary'
"express@5.2.1 is safe to use (health: 85/100)"

# Is this package real?
$ curl -s depscope.dev/api/exists/npm/super-magic-http | jq '.exists'
false

# What to use instead of moment?
$ curl -s depscope.dev/api/alternatives/npm/moment | jq '.alternatives[].name'
"dayjs"
"date-fns"
"luxon"

# Compare web frameworks
$ curl -s depscope.dev/api/compare/npm/express,fastify,hono | jq '.winner'
"fastify"
```

## Self-hosting

DepScope is free to use at `depscope.dev`. If you want to self-host:

- Backend: FastAPI + PostgreSQL + Redis
- Frontend: Next.js 16
- Requirements: 2 CPU, 4GB RAM minimum

Contact us for self-hosting support.

## License

MIT

## Contact

- Email: depscope@cuttalo.com
- Website: [depscope.dev](https://depscope.dev)
- Built by [Cuttalo srl](https://cuttalo.com), Grottaglie, Italy

---

<div align="center">
<i>We do the heavy lifting once, so every AI agent benefits.</i>
</div>
