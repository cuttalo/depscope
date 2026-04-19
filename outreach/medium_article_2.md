# The npm Packages You Use Every Day Are Sicker Than You Think

I analyzed 14,700+ packages across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems and 10 more). 35% scored below 60/100 on our health index.

Here's what nobody is telling you about the packages in your node_modules.

## The Deprecated Package Problem

These packages are deprecated. They still get millions of downloads every week:

| Package | Status | Downloads/Week | Health Score |
|---------|--------|----------------|-------------|
| pkg-dir | Deprecated | 80,000,000 | 37/100 |
| node-domexception | Deprecated | 35,000,000 | 31/100 |
| request | Deprecated since 2020 | 16,000,000 | 35/100 |
| har-validator | Deprecated | 15,600,000 | 33/100 |

80 million downloads per week for a deprecated package. Why? Because it's buried deep in dependency trees that nobody audits.

## The Stale Package Crisis

These packages haven't been updated in over a year, but they're the foundation of the npm ecosystem:

| Package | Downloads/Week | Last Update | Health |
|---------|----------------|-------------|--------|
| ms | 412,000,000 | 1+ year ago | 67/100 |
| tslib | 355,000,000 | 1+ year ago | 72/100 |
| readable-stream | 273,000,000 | 1+ year ago | 72/100 |
| safe-buffer | 231,000,000 | 1+ year ago | 59/100 |

If a vulnerability were found in `ms` tomorrow, the blast radius would cover half the Node.js ecosystem.

## AI Makes It Worse

AI coding agents (ChatGPT, Claude, Cursor, Copilot) suggest packages from training data. They don't check if a package is deprecated, vulnerable, or abandoned. They just suggest what they've seen before.

That's why I built DepScope — a free API that any agent can call to verify a package before suggesting it:

```bash
curl https://depscope.dev/api/check/npm/request
# Returns: deprecated=true, action=find_alternative
# Alternatives: axios, got, node-fetch
```

## How to Protect Yourself

1. Run `curl https://depscope.dev/api/scan -d '{"ecosystem":"npm","packages":YOUR_DEPS}'` to audit your project
2. Add health badges to your README: `![health](https://depscope.dev/badge/npm/YOUR-PKG)`
3. If you use Claude Code, add to your CLAUDE.md: "Check packages with https://depscope.dev/api/check/{eco}/{pkg}"

## The Data

We scored 14,700+ packages on 5 signals:
- Maintenance (25 pts): days since last release
- Security (25 pts): CVEs from OSV database
- Popularity (20 pts): weekly downloads
- Maturity (15 pts): version count
- Community (15 pts): active maintainers

Everything is free and open: [depscope.dev](https://depscope.dev)

Full report: [depscope.dev/report](https://depscope.dev/report)

---
*Data from [DepScope](https://depscope.dev) — free package intelligence for AI agents. No auth, no signup.*
