# Press Pitch — DepScope Package Health Report

## Email Template

---

**To:** [editor email]
**Subject:** 35% of popular packages have health issues — new data from 14,700+ package analysis

---

Hi [Name],

We analyzed the health of 14,700+ packages across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems and 10 more) and found that **35% fall into "caution" or "critical" health categories**. The worst part: deprecated packages like `request` (deprecated since 2020) still get 16 million downloads every week, and `pkg-dir` hits 80 million — because they're buried in dependency trees nobody audits.

We published the full findings here: **https://depscope.dev/report.md**

A few data points your readers might find interesting:

- **`ms`**, a 50-line npm package, gets **412 million downloads/week** and hasn't been updated in over a year. If a vulnerability were found tomorrow, the blast radius would cover half the Node.js ecosystem.
- **`mlflow`** (the most popular ML experiment tracker) carries **18 known vulnerabilities**. `gradio` has 11. AI/ML tooling has the worst security profile in our dataset.
- **`annotated-types`**, a core Pydantic dependency, scores just **36/100** despite 160 million weekly downloads — it's in virtually every modern Python web app.

DepScope is an open package health intelligence platform built by Cuttalo srl. We score packages on maintenance, vulnerabilities, community health, and deprecation status.

Happy to provide additional data, custom analysis, or an interview. We also have the full dataset available for independent verification.

Best,
[Your Name]
Cuttalo srl
info@cuttalo.com
https://depscope.dev

---

## Subject Line Alternatives

1. "35% of popular packages have health issues — new data from 14,700+ package analysis"
2. "A deprecated npm package still gets 80M downloads/week. Here's what else we found."
3. "mlflow has 18 known vulnerabilities. The state of package health in 2026."
4. "412M downloads/week, no update in a year: the stale package crisis"
5. "New research: 1 in 3 popular open-source packages scores 'caution' or worse"

---

## Outlet-Specific Notes

**The Register / DevClass** — Lead with the deprecated packages angle. Their readers are skeptical senior devs who will appreciate the "nobody audits transitive deps" framing.

**BleepingComputer / The Hacker News** — Lead with the vulnerability angle (mlflow 18 vulns, gradio 11). Security is their beat.

**InfoQ** — Lead with the ecosystem comparison (Cargo 74.5 vs PyPI 61.5). Their audience cares about engineering culture and practices.

**TechCrunch** — Lead with the AI angle (AI assistants suggest deprecated packages). It's the most newsworthy hook for a general tech audience.
