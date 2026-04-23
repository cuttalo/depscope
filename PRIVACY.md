# Privacy Policy — DepScope

**Effective date:** 2026-04-23
**Contact:** privacy@depscope.dev

## Who we are

DepScope is a free, zero-auth API + MCP server that helps AI coding agents verify package metadata (existence, vulnerabilities, health, alternatives). The operator is **SPI Operations Ltd / DepScope.dev**.

## What we collect

For every API call we keep a row in `api_usage` with:

- `endpoint` — which API endpoint was called (e.g. `check`, `licenses`)
- `ecosystem` + `package_name` — what package the call was about
- `ip_hash` — **SHA-256(your_IP + project_salt)**. One-way hash. Never the raw IP.
- `user_agent` — request User-Agent header (max 500 chars). Used to classify the caller into `agent_client` buckets (`claude-code`, `cursor`, `windsurf`, `crawler`, …)
- `country` — 2-letter ISO code derived from Cloudflare's coarse geolocation
- `status_code`, `cache_hit`, `response_time_ms`, `session_id` (hashed) — operational telemetry
- `mcp_tool` — the MCP tool name, when the call came from an MCP client
- `agent_client` — derived bucket classification
- `is_hallucination` — boolean set when the call was a package-existence check that returned 404 (i.e. the agent asked about a package that does not exist)

## What we DON'T collect

- Raw IP addresses (they are hashed in-memory at request time and never written to disk)
- Email addresses, names, device IDs, advertising identifiers
- Cookies, local-storage tokens, browser fingerprints
- Your code, project files, or anything that identifies a specific user or organisation
- Payment data (there is no paid tier)

## Why we collect it

1. **Operate the service** — rate-limit abusers, detect outages, size infrastructure
2. **Improve accuracy** — a 404 that 20 different agents hit this week is a signal that many LLMs are hallucinating the same fake package; we use that to prioritize what we ingest next
3. **Publish aggregate intelligence** — we plan to ship anonymised trend reports showing what packages AI agents query (see our roadmap at [depscope.dev/intel](https://depscope.dev))

## How long we keep it

- **Raw rows in `api_usage`: 30 days.** After that, rows are permanently deleted by a daily job.
- **Aggregates** (hourly/daily roll-ups, trend snapshots, co-occurrence pairs): kept indefinitely. Aggregates contain no per-row data and cannot be reversed.
- **Session IDs** (`api_sessions`): 90 days, then deleted.
- **Backups** of `api_usage` containing raw IPs (pre–April 2026) have been purged or re-written with `ip_address = NULL`.

## Your rights (GDPR Art. 15, 17, 20)

Because we never store your raw IP we can't identify you by name. We can still let you exercise your rights based on your *current* IP hash:

- **Access / portability** — `GET https://api.depscope.dev/api/gdpr/export` returns every `api_usage` row tied to your current IP hash, as JSON.
- **Erasure** — `POST https://api.depscope.dev/api/gdpr/delete` deletes every row tied to your current IP hash.

Both endpoints are rate-limited to 10 requests/hour per IP hash. Use them from the network you want to clear.

A machine-readable summary of this policy is at [`/api/gdpr/policy`](https://api.depscope.dev/api/gdpr/policy).

## Third parties

- **Cloudflare** terminates TLS and provides the `CF-IPCountry`, `CF-Connecting-IP` headers we consume. See [Cloudflare's privacy policy](https://www.cloudflare.com/privacypolicy/).
- **OVH** hosts our infrastructure (Roubaix RBX6 / RBX8 data centres, EU).
- No analytics vendors, ad networks, or fingerprinting services are in the request path.

## Legal basis

Processing is based on **legitimate interest** (operating a public free service and preventing abuse) as defined in GDPR Art. 6(1)(f). A detailed Legitimate Interest Assessment is available on request.

## Changes to this policy

We will update the `effective_date` above and publish the diff in the commit history of this file. Material changes will also be announced on [`depscope.dev`](https://depscope.dev).

## Contact

**privacy@depscope.dev** for data-protection questions.
**security@depscope.dev** for vulnerability reports ([SECURITY.md](./SECURITY.md)).
