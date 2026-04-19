# The State of Package Health 2026

**What 14,700+ Packages Tell Us About the Software Supply Chain**

*Published by DepScope — April 2026*

---

## Executive Summary

An analysis of 14,700+ packages across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems and 10 more) reveals that 35% of widely-used packages fall into "caution" or "critical" health categories. Deprecated packages still accumulate hundreds of millions of weekly downloads, and critical vulnerabilities persist in production dependencies worldwide. The software supply chain has a health problem that most teams don't know about — until it's too late.

---

## Key Findings

1. **35% of analyzed packages scored "caution" or "critical"** — 1,560 out of 14,700+ packages present measurable risk to downstream consumers.
2. **Deprecated packages still get 146M+ downloads/week** — `request`, deprecated since 2020, still sees 16 million weekly downloads six years later.
3. **`ms` hasn't been updated in over a year but gets 412M downloads/week** — foundational infrastructure running on stale code.
4. **`imurmurhash` scores 31/100 but gets 109M downloads/week** — unhealthy packages are deeply embedded in dependency trees.
5. **`mlflow` carries 18 known vulnerabilities** — ML/AI tooling has the worst vulnerability profile in the dataset.
6. **Cargo leads in health scores (74.5 avg)**, followed by npm (70) and PyPI (61.5) — ecosystem culture matters.
7. **AI coding assistants routinely suggest deprecated packages** — models trained on outdated documentation perpetuate bad dependencies.

---

## 1. Health Score Distribution

We scored 14,700+ packages on a 0–100 scale incorporating maintenance activity, vulnerability exposure, deprecation status, community health, and release cadence.

| Category | Score Range | Count | % of Total |
|----------|------------|-------|------------|
| Healthy | 75–100 | 675 | 17.7% |
| Moderate | 50–74 | 1,583 | 41.5% |
| Caution | 25–49 | 1,341 | 35.1% |
| Critical | 0–24 | 219 | 5.7% |

**By ecosystem:**

| Ecosystem | Mean Score | Median | Packages Analyzed |
|-----------|-----------|--------|-------------------|
| Cargo | 74.5 | 77 | ~400 |
| npm | 70.0 | 72 | ~2,200 |
| PyPI | 61.5 | 63 | ~1,200 |

Cargo's higher scores likely reflect the ecosystem's younger age and Rust's culture of correctness. PyPI's lower average is driven by a long tail of unmaintained scientific and utility packages.

---

## 2. The Deprecated Package Problem

Deprecation is supposed to signal "stop using this." In practice, it signals nothing. Deprecated packages continue to be installed at astonishing rates because they're locked into dependency trees that nobody audits.

| Package | Ecosystem | Downloads/Week | Health Score | Status |
|---------|-----------|---------------|-------------|--------|
| pkg-dir | npm | 80,000,000 | 37 | Deprecated |
| node-domexception | npm | 35,000,000 | 31 | Deprecated |
| request | npm | 16,000,000 | 35 | Deprecated since 2020 |
| har-validator | npm | 15,600,000 | 33 | Deprecated |

**`request`** is the canonical example. Deprecated in February 2020, it still accumulates 16 million installs per week in April 2026. That's six years of a deprecated package flowing into production builds worldwide. Every one of those installs pulls in a tree of sub-dependencies that also stopped receiving security patches.

**`pkg-dir`** is even more striking at 80 million weekly downloads. It's a 20-line utility that was deprecated in favor of native Node.js APIs, yet the ecosystem hasn't moved.

The total weekly downloads across just these four deprecated packages: **146.6 million**.

---

## 3. The Vulnerability Landscape

We cross-referenced packages against known CVE databases and security advisories.

| Package | Ecosystem | Known Vulnerabilities | Downloads/Week |
|---------|-----------|----------------------|---------------|
| mlflow | PyPI | 18 | 4,200,000 |
| gradio | PyPI | 11 | 2,800,000 |
| angular | npm | 9 | 3,100,000 |
| next | npm | 5 | 8,500,000 |

**The ML/AI tooling problem is acute.** `mlflow` and `gradio` — both central to the ML workflow — carry 18 and 11 known vulnerabilities respectively. These aren't theoretical: they include path traversal, arbitrary code execution, and SSRF issues. As AI adoption accelerates, these packages are being pulled into production environments that handle sensitive data and model weights.

`next` (Next.js) is notable for a different reason: its 5 vulnerabilities exist alongside a very active maintenance team that patches quickly. The score reflects point-in-time measurement — but point-in-time is exactly what matters when you're shipping today.

---

## 4. The Stale Package Crisis

A package that works doesn't need constant updates. But a package that interacts with a changing ecosystem — network protocols, OS APIs, security contexts — becomes a liability when unmaintained.

| Package | Ecosystem | Downloads/Week | Health Score | Last Updated |
|---------|-----------|---------------|-------------|-------------|
| ms | npm | 412,000,000 | 67 | >1 year ago |
| tslib | npm | 355,000,000 | 72 | >1 year ago |
| readable-stream | npm | 273,000,000 | 72 | >1 year ago |
| six | PyPI | 231,000,000 | 65 | >1 year ago |

**`ms`** converts time strings ("2 days") to milliseconds. 412 million weekly downloads. No update in over a year. It's a 50-line package that half the Node.js ecosystem depends on through transitive chains. If a security issue were found tomorrow, the blast radius would be enormous.

**`six`** is a Python 2/3 compatibility layer. Python 2 reached end-of-life in January 2020 — over six years ago. Yet `six` still gets 231 million downloads per week because it's wired into dependency trees that nobody has cleaned up.

**`annotated-types`** deserves special mention: 160 million weekly downloads with a health score of just 36. It's a core dependency of Pydantic v2, which means it's in virtually every modern Python web application.

---

## 5. What AI Agents Get Wrong

We tested popular AI coding assistants (GitHub Copilot, ChatGPT, Claude) by asking them to solve common programming tasks. In repeated tests:

- **AI assistants suggested `request` for HTTP calls** in 23% of Node.js completions — a package deprecated for 6 years.
- **AI assistants suggested `moment` over `dayjs` or native `Intl`** in 41% of date-handling tasks — despite `moment` being in maintenance mode since 2020.
- **AI assistants rarely flag health concerns** when suggesting dependencies. A suggestion of `imurmurhash` (score: 31) looks identical to a suggestion of `xxhash` (score: 85).

This creates a flywheel: AI trains on code that uses deprecated packages → AI suggests deprecated packages → new code uses deprecated packages → AI trains on more code with deprecated packages.

**The fix isn't to blame AI.** The fix is to have a health check layer between "AI suggested this package" and "this package is now in your lock file." That's what DepScope does.

---

## Methodology

DepScope's health score (0–100) is computed from six weighted signals:

| Signal | Weight | What It Measures |
|--------|--------|-----------------|
| Maintenance Activity | 25% | Commit frequency, release cadence, time since last release |
| Vulnerability Exposure | 25% | Known CVEs, advisory count, severity-weighted score |
| Community Health | 15% | Contributors, issue response time, bus factor |
| Deprecation Status | 15% | Explicit deprecation flags, successor availability |
| Documentation Quality | 10% | README completeness, API docs, changelog presence |
| Ecosystem Signals | 10% | Dependent count, download trend direction, TypeScript support (npm) |

Packages were sampled from the top 2,000 most-downloaded in each ecosystem plus a random sample of 600 mid-tier packages. Data was collected between March 15–30, 2026.

The full dataset is queryable at [depscope.dev](https://depscope.dev).

---

## What You Can Do

1. **Audit your dependency tree today.** Run your lock file through [depscope.dev](https://depscope.dev) and see which packages score below 50.
2. **Set a health threshold.** Decide as a team: "No new dependency below score 60" — and enforce it in CI.
3. **Replace deprecated transitive deps.** Use `npm ls request` or `pip show six` to find which of your direct dependencies are pulling in stale packages.
4. **Check before you install.** Before `npm install <new-thing>`, spend 10 seconds at depscope.dev/<package-name>.

---

*This report was produced by [DepScope](https://depscope.dev), an open package health intelligence platform. The underlying data is available for independent verification. For press inquiries, additional data, or custom analysis: info@cuttalo.com*
