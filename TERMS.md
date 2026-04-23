# Terms of Service — DepScope

**Effective date:** 2026-04-23
**Operator:** SPI Operations Ltd / DepScope.dev

## 1. Service

DepScope is a free, best-effort public API that returns package metadata (existence, vulnerabilities, health, alternatives) for open-source software packages. No account is required. No payment is required.

## 2. Use

You may call our API from any software you control — AI agents, IDE extensions, CLIs, CI pipelines, research scripts, etc. You may cache responses. You may redistribute aggregated insights.

You must not:

- Attempt to degrade service availability for other users
- Use the service to enumerate or stockpile our full dataset for commercial re-sale
- Bypass rate limits through techniques we have not approved
- Use the service for anything prohibited by applicable law (export controls, targeting sanctioned entities, etc.)

## 3. No warranty

The service is provided **"as is"**, without any express or implied warranty. We do our best to keep the data fresh and accurate, but:

- Vulnerability data comes from upstream sources (OSV, CISA KEV, GitHub Advisory). We may miss or be late on individual findings.
- Health scores are heuristic and not a substitute for your own security review.
- A 200 response does not guarantee a package is safe to install; a 404 does not guarantee it does not exist.

**You are responsible for the decisions you make based on our output.** If you are building an agent that auto-installs dependencies, run your own final gate.

## 4. Liability

To the maximum extent permitted by law, our liability for any claim arising from the use of the service is limited to zero (the price you paid). This does not exclude liability that cannot be excluded by law.

## 5. Privacy

See [PRIVACY.md](./PRIVACY.md). In short: we hash IPs, keep raw logs 30 days, publish only anonymised aggregates.

## 6. Takedown / package maintainers

If you maintain a package and want its metadata to be re-fetched or flagged, email **takedown@depscope.dev** with the ecosystem+name. We process requests within 5 business days. We will not remove factual vulnerability findings from public datasets.

## 7. Changes

We may update these Terms at any time. The `effective_date` above marks the current version; material changes will be announced on [`depscope.dev`](https://depscope.dev).

## 8. Governing law

These Terms are governed by the laws of the United Kingdom. Venue for any dispute is the courts of England and Wales.

## 9. Contact

**legal@depscope.dev** for contractual questions.
**security@depscope.dev** for vulnerability reports.
**privacy@depscope.dev** for GDPR requests.
