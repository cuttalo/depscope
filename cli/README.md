# depscope-cli

**Check any package across 19 ecosystems before you install it.** Free, zero auth, agent-ready.

```bash
npx depscope-cli express            # quick check (defaults to npm)
npx depscope-cli check pypi/requests
npx depscope-cli scan package-lock.json
npx depscope-cli malicious --live   # real-time supply-chain stream
```

## What it does

Wraps [depscope.dev](https://depscope.dev) — a free public API for **package intelligence**: health scores, vulnerabilities (OSV + KEV + EPSS), typosquat detection, historical supply-chain compromise matches, license risk, and curated alternatives.

Covers:

- **npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems**
- **Composer, Pub, Hex, Swift, CocoaPods, CPAN**
- **Hackage, CRAN, Conda, Homebrew**
- **JSR, Julia** (new)

## Install

```bash
# one-shot
npx depscope-cli <pkg>

# or global
npm install -g depscope-cli
depscope <pkg>
```

No API key. No signup. No telemetry from this CLI.

## Commands

| Command | What |
|---|---|
| `depscope check <eco>/<pkg>` | Full JSON report (health, vulns, license_risk, historical_compromise) |
| `depscope prompt <eco>/<pkg>` | LLM-optimized ~500-token text brief — drop into system prompts |
| `depscope alt <eco>/<pkg>` | Curated alternatives (great for deprecated pkgs) |
| `depscope scan <lockfile>` | Audit a lockfile: package-lock, pnpm-lock, yarn.lock, poetry.lock, Pipfile.lock, composer.lock, Cargo.lock, requirements.txt, go.sum |
| `depscope sbom <lockfile>` | Emit CycloneDX SBOM from the lockfile |
| `depscope malicious --live` | Subscribe to the real-time SSE stream of new malicious advisories |

### Shortcuts

```bash
depscope express              # == depscope check npm/express
depscope pypi/requests        # == depscope check pypi/requests
```

## Examples

```bash
$ depscope check npm/request
npm/request @2.88.2
Simplified HTTP client

LEGACY BUT WORKING  request@2.88.2 — deprecated 2020, kept working for legacy projects
Health:     32/100 (critical)
Vulns:      1  (0 crit, 1 high)
License:    Apache-2.0  permissive
Alternatives: axios, got, node-fetch
https://depscope.dev/pkg/npm/request
```

```bash
$ depscope check npm/event-stream
npm/event-stream @4.0.1
Streaming made easier

SAFE TO USE  event-stream@4.0.1 is safe to use (health: 57/100)
⚠ 1 historical compromise incident(s) on record    # <- ALWAYS surfaces even for unpublished bad versions
...
```

```bash
$ depscope scan poetry.lock
Scan: poetry.lock
ecosystem: pypi  packages: 42
project_risk: low

  ✓ requests @2.31.0  safe_to_use
  ! urllib3 @2.0.7    update_required
  ✓ certifi @2023.11.17  safe_to_use
  ...
```

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Package safe / update-required / find-alternative |
| `1` | `do_not_use` or historical compromise match |
| `2` | Network error or package not found |
| `3` | Usage error |

CI-friendly: run `depscope scan package-lock.json` in a pre-commit or PR check.

## Use with AI coding agents

Add DepScope to your Claude Code / Cursor / Windsurf config — it's an MCP server:

```jsonc
{ "mcpServers": { "depscope": { "url": "https://mcp.depscope.dev/mcp" } } }
```

22 MCP tools auto-registered. See [depscope.dev/integrate](https://depscope.dev/integrate).

## License

MIT. The DepScope API itself is CC0/free-for-all.

## Links

- Website: https://depscope.dev
- API docs: https://depscope.dev/api-docs
- Hallucination Benchmark (CC0): https://depscope.dev/benchmark
- Open MCP: https://mcp.depscope.dev/mcp
