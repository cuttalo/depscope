"""Batch 2: Security + Newsletter + Dev Media — 10 emails, 6min apart"""
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

SMTP_HOST = "10.10.0.130"
SMTP_PORT = 25
FROM = "depscope@cuttalo.com"
REPORT = "https://depscope.dev/report.md"
SITE = "https://depscope.dev"

EMAILS = [
    # Security companies — MOST relevant
    {
        "to": "press@socket.dev",
        "subject": "Package health data: 14,700+ packages analyzed across 17 ecosystems — findings overlap with your work",
        "body": f"""Hi Socket team,

We're fans of what you're doing with supply chain security. We recently completed a health analysis of 14,700+ packages across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems and 10 more), and thought the findings might interest you:

- 35% of packages score below 60/100 on our health index
- Deprecated packages like request (16M/week) and pkg-dir (80M/week) persist in dependency trees
- mlflow carries 18 known CVEs, gradio 11 — AI/ML tooling has the worst security profile
- Python ecosystem averages 61.5/100, significantly behind Cargo (74.5) and npm (70)

Full report: {REPORT}

The data comes from DepScope ({SITE}), an open API that scores packages on maintenance, security (OSV), popularity, maturity, and community. We built it specifically for AI coding agents to check before suggesting installs.

We'd love to hear your take on the findings, especially the deprecated-but-still-downloaded pattern.

Best,
Vincenzo Rubino
Cuttalo srl"""
    },
    {
        "to": "press@snyk.io",
        "subject": "New data: AI/ML packages have worst security profile — 14,700+ package health analysis",
        "body": f"""Hi Snyk team,

Given your annual State of Open Source Security report, we thought you'd be interested in our findings from analyzing 14,700+ packages:

The AI/ML corner of PyPI has alarming numbers:
- mlflow: 18 active CVEs
- gradio: 11 active CVEs
- PyPI overall: 61.5/100 avg health (vs npm 70, Cargo 74.5)

Meanwhile, foundational packages go unmaintained: ms (412M downloads/week, no update in 1+ year), annotated-types (160M/week, health 36/100).

Full data: {REPORT}

Source: DepScope ({SITE}) — open package health API using OSV vulnerability data filtered to latest versions only.

Vincenzo Rubino
Cuttalo srl — depscope@cuttalo.com"""
    },
    {
        "to": "pr@jfrog.com",
        "subject": "Package supply chain data: 80M weekly downloads to deprecated npm packages",
        "body": f"""Hi JFrog team,

We analyzed 14,700+ packages and found data relevant to your supply chain research:

Top finding: deprecated packages are downloaded hundreds of millions of times weekly because they're embedded deep in dependency trees that nobody audits. pkg-dir alone: 80M/week with a health score of 37/100.

Report: {REPORT}
Source: DepScope ({SITE})

Would love to compare notes with your security research team.

Vincenzo Rubino
Cuttalo srl"""
    },
    # Newsletter editors
    {
        "to": "editor@cooperpress.com",
        "subject": "For JavaScript/Node Weekly: npm packages health analysis — ms gets 412M/week with no updates",
        "body": f"""Hi Peter,

Quick submission for JavaScript Weekly and/or Node Weekly:

We analyzed 14,700+ packages and found that npm foundational packages have a maintenance problem:
- ms: 412M downloads/week, no update in 1+ year
- readable-stream: 273M/week, stale
- escape-string-regexp: 263M/week, stale
- request (deprecated): still 16M/week

Full report with npm-specific findings: {REPORT}

Also built a free API for checking any package: {SITE}/api/check/npm/express

Best,
Vincenzo Rubino"""
    },
    {
        "to": "hello@console.dev",
        "subject": "Dev tool submission: DepScope — free package health API for AI agents",
        "body": f"""Hi Console team,

Submitting DepScope for consideration in your weekly roundup:

What: Free API that checks package health, vulnerabilities, and versions for 17 ecosystems (17 ecosystems/Go/Maven/NuGet/RubyGems + 10 more)
Why: AI coding agents suggest deprecated/vulnerable packages. We do the check once, serve to all.
URL: {SITE}

Try: curl {SITE}/api/check/npm/express

No auth, 200 req/min, also available as ChatGPT GPT and npm MCP server.

We also published a report analyzing 14,700+ packages: {REPORT}

Best,
Vincenzo Rubino
Cuttalo srl"""
    },
    {
        "to": "editors@changelog.com",
        "subject": "Package health data: 35% of popular packages need attention — report + open API",
        "body": f"""Hi Changelog team,

We built DepScope, a free API that scores package health for 17 ecosystems (17 ecosystems/Go/Maven/NuGet/RubyGems + 10 more), and published our first analysis of 14,700+ packages:

Key: 35% score below 60/100. Deprecated packages get 80M+ downloads/week. AI/ML tooling (mlflow, gradio) has the worst vulnerability profile.

Report: {REPORT}
Tool: {SITE}

Thought this might be interesting for the newsletter or podcast — the intersection of AI coding agents and supply chain security is a growing blind spot.

Best,
Vincenzo Rubino
Cuttalo srl"""
    },
    # Security media
    {
        "to": "DarkReadingNews@darkreading.com",
        "subject": "Data: deprecated npm packages with 80M+ weekly downloads persist in supply chains",
        "body": f"""Hi Dark Reading team,

New supply chain security data from an analysis of 14,700+ packages:

- pkg-dir (deprecated): 80M downloads/week, health 37/100
- request (deprecated since 2020): 16M downloads/week
- mlflow: 18 active CVEs
- annotated-types: 160M PyPI downloads/week, health 36/100

These packages persist because they're buried in dependency trees. AI coding agents compound the problem by suggesting them from training data.

Full findings: {REPORT}

Vincenzo Rubino
DepScope ({SITE}) — Cuttalo srl"""
    },
    {
        "to": "press@securityweek.com",
        "subject": "Research: AI/ML packages show worst vulnerability profile in 14,700+ package (17 ecosystems) analysis",
        "body": f"""Hi SecurityWeek,

Sharing findings from our package health analysis — 14,700+ packages across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems and 10 more):

The AI/ML ecosystem has a security problem:
- mlflow: 18 known vulnerabilities
- gradio: 11 known vulnerabilities
- PyPI average health: 61.5/100 (one of the lowest across the 17 ecosystems we index)
- Cargo leads at 74.5/100

Full report: {REPORT}
Methodology uses OSV vulnerability data filtered to latest version only.

Vincenzo Rubino
DepScope ({SITE})"""
    },
    {
        "to": "admin@thehackernews.com",
        "subject": "Exclusive data: deprecated packages still get 80M downloads/week — 14,700+ package analysis across 17 ecosystems",
        "body": f"""Hi,

Exclusive supply chain data: we analyzed 14,700+ packages across 17 ecosystems and found deprecated packages are downloaded hundreds of millions of times weekly. The worst: pkg-dir at 80M/week (health 37/100), and request at 16M/week (deprecated since 2020).

AI coding agents make it worse — they suggest these packages from training data without checking.

We also found mlflow carries 18 active CVEs and gradio 11.

Full findings: {REPORT}

Source: DepScope ({SITE}), open package health API.

Vincenzo Rubino
Cuttalo srl"""
    },
    {
        "to": "stories@hackernoon.com",
        "subject": "Article submission: The State of Package Health 2026 — 14,700+ packages analyzed",
        "body": f"""Hi HackerNoon,

I'd like to submit an article based on our analysis of 14,700+ packages across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems and 10 more).

Title: "The State of Package Health 2026 — What 14,700+ Packages Tell Us"

Key findings:
- 35% of packages in caution/critical zone
- Deprecated packages still massively downloaded
- AI/ML tooling has worst security profile
- Cargo ecosystem healthiest, PyPI lowest

Full draft: {REPORT}

Happy to adapt format to HackerNoon style.

Vincenzo Rubino
Cuttalo srl"""
    },
]

def send(to, subject, body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Vincenzo Rubino - DepScope <{FROM}>"
    msg["To"] = to
    msg["Reply-To"] = FROM
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as s:
            s.sendmail(FROM, to, msg.as_string())
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

if __name__ == "__main__":
    print(f"=== Batch 2 — {datetime.now().strftime('%H:%M')} — {len(EMAILS)} emails ===")
    for i, e in enumerate(EMAILS):
        print(f"[{i+1}/{len(EMAILS)}] {e['to']}")
        if send(e['to'], e['subject'], e['body']):
            print("  SENT")
        with open("/home/deploy/depscope/outreach/sent_log.txt", "a") as f:
            f.write(f"{datetime.now().isoformat()} | {e['to']} | {e['subject']}\n")
        if i < len(EMAILS) - 1:
            print("  Waiting 6 min...")
            time.sleep(360)
    print("=== Batch 2 done ===")
