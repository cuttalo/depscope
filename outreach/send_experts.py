"""Personalized emails to supply chain security experts"""
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

SMTP_HOST = "10.10.0.130"
SMTP_PORT = 25
FROM = "depscope@cuttalo.com"
DEVTO = "https://dev.to/depscope/i-built-a-free-api-that-checks-package-health-for-ai-agents-3ip8"
REPORT = "https://depscope.dev/report.md"
SITE = "https://depscope.dev"

EMAILS = [
    {
        "to": "liran@lirantal.com",
        "subject": "Your awesome-nodejs-security list inspired this — 14,700+ packages analyzed",
        "body": f"""Hi Liran,

Your awesome-nodejs-security list and your work on npm supply chain security at Snyk have been a big reference for me.

I built DepScope — a free API that scores package health across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems and 10 more). We analyzed 14,700+ packages and found some data that confirms what you've been saying for years:

- request (deprecated since 2020): still 16M downloads/week
- pkg-dir (deprecated): 80M downloads/week, health 37/100
- ms: 412M downloads/week, no update in over a year

The worst part: AI coding agents (Claude, ChatGPT, Cursor) actively suggest these packages because they rely on training data.

Full analysis: {DEVTO}
API (free, no auth): {SITE}/api/check/npm/express

Would love your feedback on the health scoring methodology. And if it fits, would be great to be included in your awesome-nodejs-security list.

Best,
Vincenzo Rubino
Cuttalo srl"""
    },
    {
        "to": "feross@socket.dev",
        "subject": "DepScope health data complements Socket's supply chain work — 14,700+ packages",
        "body": f"""Hi Feross,

Huge fan of Socket.dev and your Stanford CS 253 course. What you're doing for supply chain security is exactly what the ecosystem needs.

I built DepScope as a complement to what Socket does — while you focus on malware detection and deep analysis, we provide a quick health score (0-100) that AI coding agents can call before suggesting any install.

Our data from 14,700+ packages: {REPORT}

Key finding that might interest you: the AI/ML corner of PyPI has the worst security profile — mlflow 18 CVEs, gradio 11. As AI adoption grows, the tools used to build AI have the weakest security.

The API is free and open: {SITE}/api/check/npm/express

Would love to explore if there's a way our data could complement Socket's analysis, or if you have feedback on our approach.

Vincenzo Rubino
Cuttalo srl — {SITE}"""
    },
    {
        "to": "seth@python.org",
        "subject": "PyPI security data: avg health 61.5/100 among 17 ecosystems (14,700+ packages analyzed)",
        "body": f"""Hi Seth,

Given your role as PSF Security Developer-in-Residence, I thought you'd want to see this: we analyzed 14,700+ packages across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems and 10 more). PyPI has the lowest average health score at 61.5/100, compared to npm (70) and Cargo (74.5).

The AI/ML packages are the worst offenders:
- mlflow: 18 known CVEs
- gradio: 11 CVEs
- annotated-types: 160M weekly downloads, health 36/100

Full data: {REPORT}

We built DepScope ({SITE}) as a free API to score package health. It uses OSV data filtered to only show vulns affecting the latest version — not historical noise. Django went from 272 reported vulns to just 1 that actually matters.

Would love your input on how this could be useful for the Python security ecosystem.

Vincenzo Rubino
Cuttalo srl"""
    },
    {
        "to": "ietf@filippo.io",
        "subject": "Cargo leads in package health (74.5/100) — data from 14,700+ packages",
        "body": f"""Hi Filippo,

Given your work on Go security and the Go Vulnerability Database, I thought you'd find this interesting: we analyzed 14,700+ packages across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems and 10 more).

Cargo leads at 74.5/100 average health score, npm at 70, PyPI at 61.5. The Go ecosystem isn't in our dataset yet but it's next on the list.

The methodology uses OSV data, maintenance signals, and community health. Full analysis: {REPORT}

DepScope ({SITE}) is a free API for checking package health — designed for AI coding agents. Your feedback on extending it to Go modules would be invaluable.

Vincenzo Rubino
Cuttalo srl"""
    },
    {
        "to": "william@trailofbits.com",
        "subject": "pip-audit data in context: PyPI health scores across 14,700+ packages",
        "body": f"""Hi William,

As the creator of pip-audit, you probably see this daily — but we now have data at scale: PyPI averages 61.5/100 in our health scoring, the lowest of 17 ecosystems.

We built DepScope ({SITE}), a free API that scores packages using OSV data (same source as pip-audit) plus maintenance, popularity, and community signals.

The key difference from pip-audit: we filter vulnerabilities to only show those affecting the latest version. This reduces noise massively — Django goes from 272 to 1.

Full report: {REPORT}

Would love your thoughts on the methodology.

Vincenzo Rubino
Cuttalo srl"""
    },
    {
        "to": "myles.borins@gmail.com",
        "subject": "npm ecosystem data: 412M weekly downloads to stale packages",
        "body": f"""Hi Myles,

Given your history with npm and Node.js, I thought you'd want to see this: we analyzed the health of 14,700+ packages and found that foundational npm packages have a maintenance problem.

- ms: 412M downloads/week, no update in 1+ year
- readable-stream: 273M/week, stale
- escape-string-regexp: 263M/week, stale
- safe-buffer: 231M/week, stale

These aren't abandoned projects — they're deeply embedded in every Node.js app. If a vulnerability were found in ms tomorrow, the blast radius covers half the ecosystem.

Full analysis: {REPORT}
Free API: {SITE}/api/check/npm/ms

Vincenzo Rubino
Cuttalo srl"""
    },
    {
        "to": "di@python.org",
        "subject": "PyPI health data: AI/ML packages have worst security profile",
        "body": f"""Hi Dustin,

As a PyPI maintainer and someone working on open source security at Google, I thought you'd be interested in our analysis of 14,700+ packages:

PyPI averages 61.5/100 health — the lowest of the three ecosystems we track (npm 70, Cargo 74.5). The worst offenders are in AI/ML:
- mlflow: 18 active CVEs
- gradio: 11 CVEs
- annotated-types: 160M downloads/week, health 36/100

Ironic that the tools used to build AI have the weakest security posture.

Full data: {REPORT}
Free API: {SITE}/api/check/pypi/mlflow

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
    print(f"=== Expert Outreach — {datetime.now().strftime('%H:%M')} — {len(EMAILS)} emails ===")
    for i, e in enumerate(EMAILS):
        print(f"[{i+1}/{len(EMAILS)}] {e['to']}")
        if send(e['to'], e['subject'], e['body']):
            print("  SENT")
        with open("/home/deploy/depscope/outreach/sent_log.txt", "a") as f:
            f.write(f"{datetime.now().isoformat()} | {e['to']} | {e['subject']}\n")
        if i < len(EMAILS) - 1:
            print("  Waiting 6 min...")
            time.sleep(360)
    print("=== Expert batch done ===")
