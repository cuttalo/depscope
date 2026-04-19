# DepScope Python Client

Python client for [DepScope](https://depscope.dev) — Package Intelligence for AI Agents.

Check health scores, vulnerabilities, and versions for npm, PyPI, and Cargo packages.

## Install

```bash
pip install depscope
```

## Quick Start

```python
from depscope import DepScope

ds = DepScope()

# Full package check
result = ds.check("npm", "express")
print(f"Health: {result[health][score]}/100")
print(f"Vulnerabilities: {result[vulnerabilities][count]}")

# Just the latest version
version = ds.latest("pypi", "fastapi")
print(f"Latest: {version}")

# Check if a package exists
exists = ds.exists("cargo", "serde")

# Health score only
health = ds.health("npm", "lodash")
print(f"Score: {health[score]}, Risk: {health[risk]}")

# Vulnerabilities
vulns = ds.vulns("pypi", "mlflow")
for v in vulns:
    print(f"  {v[severity]}: {v[vuln_id]}")

# Compare packages
comparison = ds.compare("npm", "express", "fastify", "hono")

# Scan a project
scan = ds.scan("npm", {
    "express": "^4.18",
    "lodash": "*",
    "moment": "^2.29"
})
for pkg, data in scan.items():
    print(f"{pkg}: {data.get(health, {}).get(score, N/A)}/100")

# Find alternatives
alts = ds.alternatives("npm", "request")
for alt in alts:
    print(f"  {alt[package]}: {alt.get(score, N/A)}/100")
```

## Context Manager

```python
with DepScope() as ds:
    result = ds.check("npm", "express")
```

## API Key (optional)

The free tier requires no authentication (200 req/min). If you have an API key:

```python
ds = DepScope(api_key="your-key")
```

## Links

- [DepScope](https://depscope.dev)
- [API Documentation](https://depscope.dev/api-docs)
