# I built a free API that checks if your npm/PyPI/Cargo packages are healthy before you install them

Hey everyone,

I got tired of AI coding assistants suggesting deprecated or vulnerable packages, so I built **DepScope** — a free API that checks package health.

## Try it:

```
curl https://depscope.dev/api/check/npm/express
```

## What it returns:
- **Health score** (0-100)
- **Vulnerabilities** (filtered to latest version only, not historical noise)
- **Version info**
- **Recommendation**: safe_to_use, update_required, or do_not_use

## More endpoints:
- **Compare packages**: `/api/compare/npm/express,fastify,hono`
- **Scan a project**: `POST /api/scan` with your package.json deps
- **Search packages**: `/api/search/npm?q=http+client`
- **Find alternatives**: `/api/alternatives/npm/request` → suggests axios, got, node-fetch
- **Latest version**: `/api/latest/npm/react` (use before any install)
- **Does it exist?**: `/api/exists/npm/my-package`

No auth needed. No signup. Free. 200 req/min.

## Why I built it

AI agents hit npm/PyPI/OSV independently millions of times for the same data. We do the heavy lifting once, cache it, and serve instant answers to everyone.

Also available as a **ChatGPT GPT** in the GPT Store — search "DepScope".

**Try it**: [depscope.dev](https://depscope.dev)
**API docs**: [depscope.dev/api-docs](https://depscope.dev/api-docs)

Built with FastAPI + PostgreSQL + Redis + Next.js.

What do you think? What would you want a package checker to do that it doesn't already?
