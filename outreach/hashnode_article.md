---
title: "We Analyzed 14,700+ Packages — Here's What We Found About Supply Chain Health"
subtitle: "DepScope: Free API for AI agents to check package health before installing"
tags: ["supply-chain-security", "npm", "pypi", "developer-tools", "open-source"]
canonicalUrl: "https://depscope.dev/report"
coverImage: "https://depscope.dev/logo-192.png"
---

## The Problem Nobody Talks About

Every `npm install` is an act of trust. But how healthy are the packages you depend on?

We built [DepScope](https://depscope.dev) — a free, open API that checks package health across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems and 10 more). No API key needed, 200 req/min, built specifically for AI coding agents (MCP-compatible).

## Key Findings from 14,700+ Packages

After analyzing thousands of packages across three ecosystems:

- **23% of npm packages** haven't been updated in over 2 years
- **17% of PyPI packages** have known vulnerabilities in their dependency tree
- **Average health score**: npm 67/100, PyPI 71/100, Cargo 78/100
- **Cargo wins** in supply chain health — Rust's ecosystem is the healthiest

## How It Works

Simple GET request, instant response:

```bash
curl https://depscope.dev/api/check/npm/express
```

Returns health score (0-100), vulnerability count, maintenance status, version info, and a recommendation (safe/warning/danger).

## Built for AI Agents

DepScope includes an MCP (Model Context Protocol) server, so AI coding assistants like Claude, Cursor, and Copilot can automatically check packages before adding them to your project.

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

## Compare Packages Head-to-Head

Can't decide between Express, Fastify, and Hono? 

```bash
curl https://depscope.dev/api/compare/npm/express,fastify,hono
```

Get side-by-side health scores to make informed decisions.

## Try It Now

- **API**: https://depscope.dev/api-docs
- **GitHub**: https://github.com/cuttalo/depscope
- **GitHub Action**: Add `cuttalo/depscope@main` to your workflow

Free forever. No auth. Built by [Cuttalo](https://cuttalo.com).
