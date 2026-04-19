# Influencer Outreach — DepScope Package Health Report

---

## Tweet Thread (post from @depscope or personal account)

**Tweet 1:**
We analyzed the health of 14,700+ packages across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems and 10 more).

35% scored "caution" or "critical."

Here's what we found. A thread. 🧵

**Tweet 2:**
The deprecated package problem is worse than you think.

`request` — deprecated since Feb 2020 — still gets 16M downloads/week.
`pkg-dir` — deprecated — gets 80M downloads/week.

Combined, just 4 deprecated packages account for 146M weekly installs.

**Tweet 3:**
AI/ML tooling has the worst security profile in our dataset.

- mlflow: 18 known vulnerabilities
- gradio: 11 known vulnerabilities

These packages handle model weights and sensitive data in production. And they're full of path traversal and SSRF issues.

**Tweet 4:**
The stale infrastructure nobody talks about:

- `ms`: 412M downloads/week, no update in >1 year
- `tslib`: 355M/week, same
- `readable-stream`: 273M/week, same
- `six`: 231M/week — a Python 2 compat layer, 6 years after Py2 EOL

**Tweet 5:**
We also tested AI coding assistants.

23% of the time, they suggest `request` for HTTP calls. A package deprecated for 6 years.

AI trains on old code → suggests old packages → creates new code with old packages → cycle repeats.

**Tweet 6:**
Full report with methodology and all the data:
https://depscope.dev/report.md

You can check any package's health score at https://depscope.dev

Built by @caboricmaps. Data is open for verification.

---

## DM Templates

### @simonw (Simon Willison)

Hi Simon — we built DepScope (depscope.dev), a package health scoring tool, and just published our first analysis of 14,700+ packages. Found some interesting things: mlflow has 18 known vulns, `six` still gets 231M downloads/week 6 years after Python 2 EOL, and AI assistants suggest deprecated packages 23% of the time. Thought you might find the data interesting: depscope.dev/report.md. No pressure at all — just sharing because you tend to surface this kind of thing.

### @swyx (Shawn Wang)

Hey Shawn — we analyzed 14,700+ packages across 17 ecosystems for health signals. 35% scored caution or critical. The AI angle might interest you: coding assistants suggest deprecated packages like `request` in 23% of completions, creating a feedback loop. Full report at depscope.dev/report.md. The tool is free at depscope.dev.

### @levelsio (Pieter Levels)

Hey Pieter — built depscope.dev as a solo/small-team project. Just shipped our first data report: analyzed 14,700+ packages, 35% have health issues. One stat: deprecated npm packages still get 146M combined downloads/week. Full numbers at depscope.dev/report.md.

### @t3dotgg (Theo Browne)

Hey Theo — we scored 2,200+ npm packages on health (0-100). Some wild findings: `pkg-dir` (deprecated) gets 80M downloads/week, `ms` gets 412M/week with no update in over a year, and `imurmurhash` scores 31/100 but gets 109M/week. You might find the data interesting for a video — full report at depscope.dev/report.md.

---

## Timing Notes

- Post the thread Tuesday–Thursday, 9–11am ET (peak dev Twitter engagement)
- Send DMs 1–2 days after posting the thread (so they can see engagement)
- Don't send all DMs on the same day — space them out
- Follow up once after 5–7 days if no response, then drop it
