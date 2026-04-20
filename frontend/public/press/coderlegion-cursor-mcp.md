# Adding DepScope as an MCP tool inside Cursor in under 5 minutes

Your AI assistant in Cursor is great at writing code. It's less great at knowing which packages are actually safe to install right now. Suggestions come from training data 6-12 months stale, so recent CVEs are invisible, deprecated libraries get recommended with enthusiasm, and sometimes the model just hallucinates a package name that never existed.

[DepScope](https://depscope.dev) fixes that with a shared-cache API. It also ships an MCP (Model Context Protocol) server so Cursor can call it automatically, in-context, every time it's about to suggest a dependency.

Here's the full setup in under 5 minutes.

---

## Step 1 — pick a transport

**Option A — Remote MCP (recommended, zero install).** If your client supports remote MCP (Claude Desktop, Cursor recent, Windsurf), skip install and use the URL directly in the next step:

```
https://mcp.depscope.dev/mcp
```

**Option B — Local stdio (legacy clients).** If your client only supports stdio transport, install the npm package:

```bash
npm install -g depscope-mcp
```

No API key, no signup, no config file in either case.

## Step 2 — register it with Cursor

Open Cursor's MCP config. On macOS:

```bash
~/.cursor/mcp.json
```

(Or `Settings → MCP → Edit Config` from the command palette.)

Add the DepScope server:

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

Save. Restart Cursor (the MCP servers are loaded on startup).

## Step 3 — verify

Open a new chat in Cursor and ask something that would normally make the model guess:

> Should I install `request` or `axios` for HTTP in my Node project?

Cursor will now call the DepScope `check_package` and `find_alternatives` tools before answering. You'll see the tool invocations in the chat:

```
→ Calling depscope / check_package
   { ecosystem: "npm", package: "request" }
← { action: "avoid", reason: "deprecated since 2020",
    alternatives: ["axios", "node-fetch", "undici"] }
```

The answer you get back is based on *live* registry data plus OSV + GitHub Advisory Database lookups, not the model's stale training.

---

## What you actually get

Fourteen MCP tools registered automatically. The ones that matter in day-to-day dev work:

| Tool | When Cursor calls it |
|---|---|
| `check_package` | "Should I install X?" |
| `get_vulnerabilities` | "Are there any known CVEs in Y?" |
| `get_latest_version` | "What's the current stable version?" |
| `package_exists` | Safety-check before suggesting anything (anti-hallucination) |
| `find_alternatives` | "This is deprecated — what do I use instead?" |
| `compare_packages` | "Express vs Fastify vs Hono?" |
| `resolve_error` | "I got this `ModuleNotFoundError` — how do I fix it?" |
| `check_compat` | "Is Next 15 compatible with React 19?" |
| `search_packages` | "I need a library for X" |
| `scan_project` | Audit all deps in one shot |

Works across **17 ecosystems**: npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems, Composer, Pub, Hex, Swift, CocoaPods, CPAN, Hackage, CRAN, Conda, Homebrew.

---

## Token efficiency note

If you care about input-token cost, DepScope has a dedicated `/api/prompt/{ecosystem}/{package}` endpoint that returns a compact natural-language string instead of raw registry JSON. For the same install decision it's roughly **74% smaller** than the raw registry response — less input for the model to parse, fewer tokens on your Claude / OpenAI bill per query.

The MCP server uses this endpoint by default when the tool call doesn't need full structured data.

---

## Wrap-up

After this setup, every time Cursor is about to suggest a dependency, it gets validated against live vulnerability data — no more suggestions from 2024, no more hallucinated packages, no more silently pulling in deprecated libraries.

Links:

- Website: [depscope.dev](https://depscope.dev)
- All integrations (Claude Code, Windsurf, Copilot, Aider, raw HTTP): [depscope.dev/agent-setup](https://depscope.dev/agent-setup)
- Source: [github.com/cuttalo/depscope](https://github.com/cuttalo/depscope) — MIT
- API docs: [depscope.dev/api-docs](https://depscope.dev/api-docs)

Open infrastructure, MIT, EU-hosted. Built solo by Vincenzo Rubino at [Cuttalo srl](https://cuttalo.com).
