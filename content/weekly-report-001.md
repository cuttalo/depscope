---
title: "The State of Package Health: What We Learned Indexing 14,812 Packages Across 17 Ecosystems"
slug: weekly-report-001
date: 2026-04-19
author: DepScope
tags: [package-health, supply-chain, npm, pypi, cargo, weekly-report]
description: "Real numbers from DepScope's package intelligence database — vulnerabilities in popular packages, deprecated zombies still pulling hundreds of millions of downloads, and how ecosystems stack up on health."
og_image: /og/weekly-report-001.png
---

# The State of Package Health: What We Learned Indexing 14,812 Packages Across 17 Ecosystems

> **Pillow alone accounts for 106 million weekly downloads. It ships with 3 unpatched vulnerabilities in our index. `path-is-absolute` has a health score of 20 out of 100, is officially deprecated, and is downloaded 76 million times per week.**

Those two facts are not outliers. They are representative. We've spent the last several months indexing **14,812 packages across 17 ecosystems** (npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems, Composer, Pub, Hex, Swift, CocoaPods, CPAN, Hackage, CRAN, Conda, Homebrew) and running the same health pipeline against each one. This is a report on what the data actually says — not marketing.

## Methodology

For every package in our index we fetch, on a rolling schedule:

- **Registry metadata** — versions, maintainers, license, publish dates, deprecation flags.
- **Weekly/monthly downloads** — from the native registry where exposed (npm, PyPI BigQuery, etc.).
- **Vulnerabilities** — from [OSV.dev](https://osv.dev), mapped to affected version ranges.
- **Repository stats** — GitHub stars, open issues, last commit, bus factor proxy.
- **Breaking changes** — curated migration notes between major versions.

A `health_score` (0–100) is computed from maintenance cadence, vulnerability count/severity, deprecation status, license clarity, and repository vitality. Scores below 40 are **critical**, 40–59 **poor**, 60–79 **fair**, 80+ **good**.

No secret sauce, no proprietary opacity. If you want to replicate it, the inputs are open.

## The Numbers

Across the 14,812 packages currently tracked:

| Bucket | Count | % of total |
|---|---:|---:|
| Critical (< 40) | 1,980 | 13.4% |
| Poor (40–59) | 6,353 | 42.9% |
| Fair (60–79) | 4,743 | 32.0% |
| Good (80+) | 1,680 | 11.3% |
| Unknown / unscored | 56 | 0.4% |

**More than half the packages we index score below 60.** These are not obscure libraries. Our crawler prioritises popularity — to be in this index a package generally had to clear a download threshold or appear as a dependency of a popular one.

We also track **400 vulnerabilities** against **72 packages with more than 1,000,000 weekly downloads**. Severity breakdown:

- Medium: 221
- Unknown / unclassified by source: 179

(We conservatively surface OSV records even when severity is not filled in by the upstream advisory. Absence of severity is not absence of exploitability.)

## Popular But Vulnerable

The packages below all ship more than 100,000 downloads per week **and** have at least one open advisory in our index:

| Ecosystem | Package | Vulns | Weekly downloads |
|---|---|---:|---:|
| npm | `next` | 5 | 35,930,460 |
| pypi | `Pillow` | 3 | 106,391,425 |
| pypi | `pip` | 2 | 127,105,550 |
| pypi | `nltk` | 3 | 13,395,750 |
| pypi | `opencv-python` | 2 | 10,926,573 |
| npm | `sequelize` | 2 | 2,798,158 |
| pypi | `pycrypto` | 2 | 1,994,633 |
| pypi | `opencv-contrib-python-headless` | 2 | 959,622 |
| pypi | `lmdb` | 5 | 893,100 |
| npm | `angular` | 9 | 524,366 |
| pypi | `paddlepaddle` | 5 | 370,918 |
| npm | `oauth2-server` | 2 | 240,495 |
| cargo | `rust-crypto` | 3 | 216,521 |

A few of these are well-known and tracked (`next`, `Pillow`, `pip`). A few are quietly dangerous: `rust-crypto` has been unmaintained for years, `pycrypto` is effectively abandoned in favor of `pycryptodome`, and `oauth2-server` — which, yes, handles your auth flow — has open advisories and minimal upstream activity.

## Zombie Packages

This is the category that makes seasoned engineers wince. Below are packages that registries have **officially marked deprecated** but that continue to ship tens to hundreds of millions of weekly downloads:

| Package | Weekly downloads | Why it's deprecated |
|---|---:|---|
| `mimic-fn` | 104,431,747 | Renamed to `mimic-function` |
| `pkg-dir` | 78,705,523 | Renamed to `package-directory` |
| `path-is-absolute` | 76,082,652 | No longer relevant — Node.js 0.12 is unmaintained |
| `find-cache-dir` | 42,672,386 | Renamed to `find-cache-directory` |
| `read-pkg-up` | 36,291,504 | Renamed to `read-package-up` |
| `node-domexception` | 35,167,032 | Use the platform's native `DOMException` |
| `no-case` | 34,918,820 | Use `change-case` |
| `p-finally` | 29,798,243 | Deprecated |
| `camel-case` | 28,182,607 | Use `change-case` |
| `param-case` | 27,221,685 | Use `change-case` |
| `snake-case` | 20,292,295 | Use `change-case` |
| `lodash.isequal` | 19,136,778 | Use `require('node:util').isDeepStrictEqual` |
| `lodash.get` | 17,431,501 | Use the optional chaining (`?.`) operator |
| `querystring` | 16,287,294 | Legacy — use `URLSearchParams` |
| `prebuild-install` | 15,998,022 | No longer maintained |

**Fifty packages in our index are deprecated and still pull more than 1M weekly downloads. Summed, that's roughly 740 million weekly downloads of code that the authors themselves say you should stop using.** Most of the traffic is transitive — a dependency of a dependency of a dependency — which is the entire reason package intelligence needs to be programmatic. No one is auditing `camel-case` by hand in 2026.

## Worst-Scoring Popular Packages

Filtering by weekly downloads > 500,000 and sorting by `health_score` ascending:

| Package | Health | Weekly downloads |
|---|---:|---:|
| `angular` (npm, legacy AngularJS) | 8 | 524,366 |
| `trim-right` | 15 | 3,089,154 |
| `level-concat-iterator` | 16 | 571,283 |
| `crypto` (npm shim) | 17 | 1,537,680 |
| `scmp` | 20 | 3,747,349 |
| `bin-version-check` | 20 | 4,092,095 |
| `path-is-absolute` | 20 | 76,082,652 |
| `p-finally` | 20 | 29,798,243 |
| `querystring` | 21 | 16,287,294 |
| `header-case` | 23 | 12,020,838 |

Note `angular` at **8/100 with half a million weekly downloads** — that's AngularJS 1.x, EOL since 2022, still installed somewhere new every few seconds.

## Breaking Changes in the Wild

Seventy-nine curated breaking changes are tracked across popular packages. A sample of what's actively biting upgrade PRs this quarter:

- **`pydantic` v1 → v2** — core rewritten in Rust, up to 100x faster, but `@validator` becomes `@field_validator` (and must be a classmethod). `class Config` is replaced by `model_config: ConfigDict`.
- **`numpy` 1 → 2** (released 2024) — cleaned namespace, many aliases removed, tightened mixed-type promotion rules (NEP 50).
- **`pandas` 1 → 2** — PyArrow-backed dtypes, copy-on-write opt-in (default in 3.0), nullable dtypes default.
- **`react` 18 → 19** — `ref` is now a regular prop; `forwardRef` no longer required for most function components. String refs removed. `useFormState` renamed to `useActionState`.
- **`eslint` 8 → 9** — flat config (`eslint.config.js`) is the default, legacy `.eslintrc.*` no longer read. Many formatting rules removed. Node 18.18+ required.
- **`typescript` 4.9 → 5.0** — Node 12.20+ required, stage-3 decorators replace experimental ones.
- **`tokio` 0.2 → 1** — stable API, feature flags reorganized.

These are the ones agents get wrong. An LLM trained before 2023 will happily write you a `@validator` on a Pydantic 2 model and waste half an hour of your day.

## Ecosystem Comparison

Average `health_score` by ecosystem, for packages where a score was computed:

| Ecosystem | Packages scored | Avg health | Deprecated |
|---|---:|---:|---:|
| Composer | 484 | 67.6 | 21 |
| npm | 8,645 | 59.4 | 115 |
| NuGet | 300 | 58.5 | 6 |
| PyPI | 3,282 | 57.1 | 0 |
| Cargo | 1,219 | 50.7 | 0 |
| RubyGems | 493 | 50.5 | 0 |
| Go | 73 | 50.3 | 0 |
| Maven | 242 | 39.3 | 0 |

(Hex, Swift, Conda, CRAN, CocoaPods, CPAN, Hackage, Pub, Homebrew are included in the index but have too few scored entries to be meaningful here.)

Two things jump out:

1. **Composer (PHP) leads.** Surprising to anyone who hasn't touched PHP since 2012 — the modern Composer ecosystem is small, curated, and actively maintained.
2. **Maven trails significantly.** The Java ecosystem has a long tail of ancient artifacts still pulled transitively by enterprise stacks. Many score poorly not because they're buggy but because "maintained" means a commit in 2017.

npm, despite dominating in absolute vulnerability count, is not the worst on a per-package basis. It's just the biggest — any per-package pathology is magnified by sheer volume.

## What This Means for AI Agents

If an AI coding agent suggests `lodash.get` in new code, or imports `pycrypto` because that's what its 2022 training data remembers, the resulting code review burden falls on **you**. The agent doesn't know `path-is-absolute` was deprecated. It doesn't know `pandas` 2 shipped copy-on-write. It doesn't know `next` has 5 open advisories today.

This is the gap DepScope is built to close. Every package recommendation an agent makes should be checked against live data: current version, current health, current vulnerabilities, current deprecation status. Not once. Every call.

## Try It Yourself

All of the data above is queryable without auth:

```bash
# Health snapshot for a package
curl -s https://depscope.dev/api/check/npm/next | jq '.health_score, .vulnerabilities | length'

# Is it deprecated?
curl -s https://depscope.dev/api/check/npm/path-is-absolute | jq '.deprecated, .deprecated_message'

# Compare alternatives
curl -s https://depscope.dev/api/compare/pypi/pycrypto,pycryptodome | jq '.recommendation'

# Recent breaking changes for a package
curl -s https://depscope.dev/api/breaking/pypi/pydantic | jq '.changes[]'
```

MCP tools are available for Claude Code and Cursor — the agent gets the data without you having to paste it in.

## Next Report

This report is generated weekly from live database snapshots. Numbers will shift as the index grows and vulnerabilities are published. Report #002 lands next Monday.

If you want the raw data behind any figure above, every number in this article is a single query away in the public API.
