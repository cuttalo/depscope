# DepScope

**Package Intelligence for AI Agents.** Stops AI coding agents (Claude, ChatGPT, Cursor, Windsurf, Copilot, Cline) from installing **hallucinated**, **deprecated**, or **malicious** packages across **19 ecosystems**.

→ **Live at [depscope.dev](https://depscope.dev)** · 8.4M+ packages · 42K+ vulnerabilities (99% EPSS-enriched) · zero auth · free

---

## Quick start (MCP)

### Claude Desktop / Cursor / Windsurf — remote

```json
{
  "mcpServers": {
    "depscope": {
      "url": "https://mcp.depscope.dev/mcp"
    }
  }
}
```

### Claude Code / local — stdio

```json
{
  "mcpServers": {
    "depscope": {
      "command": "npx",
      "args": ["-y", "depscope-mcp"]
    }
  }
}
```

The MCP server source is at **[cuttalo/depscope-mcp](https://github.com/cuttalo/depscope-mcp)** (AGPL-3.0).

---

## What it does

22 MCP tools across 19 package ecosystems:

`npm` · `pypi` · `cargo` · `go` · `composer` · `maven` · `nuget` · `rubygems` · `pub` · `hex` · `swift` · `cocoapods` · `cpan` · `hackage` · `cran` · `conda` · `homebrew` · `jsr` · `julia`

| Tool | Purpose |
|---|---|
| `check_package` | Full safety check: deprecation · vulnerabilities · health · recommendation |
| `check_malicious` | Malicious-package detector |
| `check_typosquat` | Typosquat detection vs popular names |
| `package_exists` | Hallucination detector (404 = LLM invented it) |
| `get_health_score` | 0–100 health score with breakdown |
| `get_vulnerabilities` | Vulnerabilities + severity scoring |
| `find_alternatives` | Suggested alternatives for deprecated/abandoned packages |
| `get_breaking_changes` | Major-version migration notes |
| `get_known_bugs` | Known issues for a package |
| `compare_packages` | Side-by-side comparison |
| `check_compatibility` | Stack-level compatibility check |
| `resolve_error` | Error message → likely cause + fix |
| `install_command` | Verified install command for the target ecosystem |
| `get_latest_version` | Latest stable version + maturity signal |
| `pin_safe` | Suggested safe version pin |
| `get_trust_signals` | Multi-signal trust score |
| `get_migration_path` | Step-by-step upgrade plan |
| `scan_project` | Bulk scan of dependency manifests |
| `check_bulk` | Fast pre-flight filter for batches |
| `get_trending` | Trending packages by ecosystem |
| `get_package_prompt` | Compact LLM-friendly summary |
| `contact_depscope` | Report a missing package or false positive |

---

## REST API

Same data, plain HTTPS — no MCP client needed.

```bash
curl https://depscope.dev/api/check/npm/lodash
curl https://depscope.dev/api/check/pypi/requests
curl https://depscope.dev/api/check/cargo/serde
```

Full reference: **[depscope.dev/integrate](https://depscope.dev/integrate)**

---

## Why

LLMs frequently invent package names that look real but don't exist (`fastapi-turbo`, `lodahs`, `tokio-stream-extras`). When an agent tries to install one, it can hit an attacker's typosquat. **DepScope verifies every package before install.**

Read more: **[depscope.dev/why](https://depscope.dev/why)**

---

## Pricing

**Free.** No auth required. Generous rate limits.

If you need higher quotas, SLA, or on-prem deployment, contact us at **depscope@cuttalo.com**.

---

## Open source vs proprietary

This repository is a **landing page** with documentation only.

- **MCP server (client SDK)** — open source, AGPL-3.0:
  → [cuttalo/depscope-mcp](https://github.com/cuttalo/depscope-mcp)
  → [npm: depscope-mcp](https://www.npmjs.com/package/depscope-mcp)

- **Backend (API + intelligence layer)** — proprietary, hosted at `depscope.dev`.

This split lets us keep the client free, auditable, and community-extensible while sustaining the infrastructure that powers it.

---

## Links

- **Homepage** · [depscope.dev](https://depscope.dev)
- **API docs** · [depscope.dev/integrate](https://depscope.dev/integrate)
- **MCP server source** · [cuttalo/depscope-mcp](https://github.com/cuttalo/depscope-mcp)
- **npm** · [depscope-mcp](https://www.npmjs.com/package/depscope-mcp)
- **Glama listing** · [glama.ai/mcp/servers/cuttalo/depscope](https://glama.ai/mcp/servers/cuttalo/depscope)
- **Awesome MCP** · [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers)

---

## License

This README and accompanying landing files: **CC-BY-4.0**.
MCP client SDK: AGPL-3.0 (see [cuttalo/depscope-mcp](https://github.com/cuttalo/depscope-mcp)).
Backend service: proprietary.

---

Built by **[Cuttalo srl](https://cuttalo.com)** · Italy 🇮🇹
