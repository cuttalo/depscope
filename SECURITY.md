# Security Policy — DepScope

## Reporting a Vulnerability

Please report security issues privately to **security@depscope.dev**.
We commit to:
- Acknowledge within 48 hours
- Publish an initial assessment within 5 business days
- Coordinate disclosure timing with the reporter

Please **do not** create public GitHub issues for security reports.

## Scope

In scope for reports:
- `depscope.dev` production endpoints (API, MCP, web UI)
- `api.depscope.dev`, `mcp.depscope.dev`
- Issues in this repository that could affect production

Out of scope:
- Denial of service without code-level flaw
- Social engineering attempts
- Physical attacks
- Issues in third-party dependencies we consume (please report upstream)

## Hall of Fame

We publicly thank researchers who help harden DepScope. Opt-in via your report.

## Data Handling

See [PRIVACY.md](./PRIVACY.md) for what we collect, how long we keep it, and your rights (GDPR Art. 15, 17, 20 supported).

## Infrastructure

- TLS 1.2+ only (Cloudflare-terminated)
- PostgreSQL with hashed-only PII (`ip_hash`, never raw IP)
- Secrets rotated on exposure; GitHub push-protection + GitGuardian monitoring
- Automated dependency scanning (via DepScope itself — we dogfood)
- Rate limits on all public endpoints
- `fail2ban` + PVE firewall on infrastructure hosts

## Threat Model

DepScope is a **read-only intelligence service** — we don't run user code and don't accept uploads.
The main attack surface is the HTTP API. We treat:
- Agent-submitted data (package names) as untrusted input (parameterized queries only)
- Upstream registry responses as untrusted (schemas validated, JSON sanitized)
- Admin endpoints as crown jewels (separate auth path, IP allowlist)

## Dependencies

We pin and review our own dependencies through DepScope's own tools weekly.
