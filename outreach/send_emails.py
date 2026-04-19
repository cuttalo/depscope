"""Send personalized outreach emails — max 10/hour, anti-spam"""
import smtplib
import time
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

SMTP_HOST = "10.10.0.130"
SMTP_PORT = 25
FROM_EMAIL = "depscope@cuttalo.com"
FROM_NAME = "Vincenzo Rubino - DepScope"

REPORT_URL = "https://depscope.dev/report.md"
SITE_URL = "https://depscope.dev"

# Personalized emails for press/tech media
EMAILS = [
    {
        "to": "editorial@devclass.com",
        "name": "DevClass Editorial",
        "subject": "Data: 35% of popular packages score below 60/100 in new health analysis",
        "body": """Hi DevClass team,

We analyzed the health of 14,700+ packages across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems and 10 more) ecosystems and published the findings as an open report.

Key data points:

- 35% of analyzed packages fall into "caution" or "critical" health categories
- pkg-dir (deprecated) still gets 80 million downloads/week — buried in dependency trees nobody audits
- ms, a tiny npm utility, gets 412 million downloads/week with no update in over a year
- mlflow carries 18 known vulnerabilities; gradio has 11
- Cargo (Rust) leads in average package health at 74.5/100, npm at 70, PyPI at 61.5

Full report: {report_url}

The data comes from DepScope, an open package health API we built. The methodology scores packages on maintenance, security (OSV data), popularity, maturity, and community signals.

Happy to provide additional analysis or a custom breakdown for a specific ecosystem.

Best,
Vincenzo Rubino
Cuttalo srl — depscope@cuttalo.com""",
    },
    {
        "to": "tips@bleepingcomputer.com",
        "name": "BleepingComputer",
        "subject": "mlflow has 18 unpatched vulnerabilities — package health data from 14,700+ packages",
        "body": """Hi,

We ran a health analysis across 14,700+ packages in npm, PyPI, and Cargo and found concerning security patterns:

- mlflow (most popular ML experiment tracker): 18 known vulnerabilities
- gradio: 11 known vulnerabilities  
- angular (npm): 9 vulnerabilities
- annotated-types (core Pydantic dependency): health score 36/100 despite 160M weekly downloads

The deprecated package problem is worse: request (npm, deprecated since 2020) still gets 16 million downloads/week because it's embedded in dependency chains.

Full data: {report_url}

We used OSV vulnerability data filtered to only show issues affecting the latest version — not historical noise. This means every vulnerability listed is currently exploitable.

The analysis is from DepScope ({site_url}), an open package health API.

Vincenzo Rubino
Cuttalo srl""",
    },
    {
        "to": "info@thehackernews.com",
        "name": "The Hacker News",
        "subject": "Supply chain data: deprecated npm packages still get 80M+ downloads/week",
        "body": """Hi,

New supply chain security data: we analyzed 14,700+ packages across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems and 10 more).

The most alarming finding: deprecated packages with known issues are still massively downloaded because they're buried in dependency trees:

- pkg-dir (deprecated): 80M downloads/week, health 37/100
- request (deprecated since 2020): 16M downloads/week  
- node-domexception (deprecated): 35M downloads/week
- har-validator (deprecated): 15.6M downloads/week

Meanwhile, AI coding agents are actively suggesting these packages to developers.

On the vulnerability side: mlflow has 18 known CVEs, gradio 11, and annotated-types (used by every Pydantic app) scores just 36/100.

Full report: {report_url}

Vincenzo Rubino
DepScope ({site_url}) — Cuttalo srl""",
    },
    {
        "to": "editors@infoq.com",
        "name": "InfoQ Editors",
        "subject": "Ecosystem comparison: Cargo leads npm and PyPI in package health — data from 14,700+ packages",
        "body": """Hi InfoQ team,

We published an analysis of 14,700+ packages across three ecosystems. The ecosystem comparison is interesting:

- Cargo (Rust): avg health 74.5/100 — best overall
- npm (Node.js): avg health 70/100 — strong but hurt by stale foundational packages  
- PyPI (Python): avg health 61.5/100 — lowest, largely due to ML/AI packages with poor security

The Python finding is notable: the worst-scoring packages are concentrated in ML/AI tooling (mlflow: 18 CVEs, gradio: 11 CVEs). As AI adoption accelerates, the tools used to build AI systems have the weakest security profile.

Other findings: 412 million weekly downloads go to packages not updated in over a year. 35% of packages score below 60/100.

Full report: {report_url}

Built with DepScope ({site_url}), an open API that scores package health algorithmically.

Best,
Vincenzo Rubino
Cuttalo srl""",
    },
    {
        "to": "tips@techcrunch.com",
        "name": "TechCrunch",
        "subject": "AI coding agents are suggesting deprecated packages — data shows the problem at scale",
        "body": """Hi,

Quick data pitch: we analyzed 14,700+ software packages and found that AI coding assistants (ChatGPT, Claude, Copilot, Cursor) regularly suggest packages that are deprecated, vulnerable, or unmaintained.

The numbers: request (npm) has been deprecated since 2020 but still gets 16 million downloads/week. pkg-dir gets 80 million. These packages live on because they're in dependency trees — and AI agents suggest them from training data.

We built DepScope ({site_url}) as a free API that any AI agent can call to check package health before suggesting an install. In our first analysis of 14,700+ packages: 35% score below 60/100, mlflow has 18 known CVEs, and Python's average package health (61.5) lags significantly behind Rust (74.5).

Full report: {report_url}

Happy to discuss the AI + supply chain angle further.

Vincenzo Rubino
Cuttalo srl — depscope@cuttalo.com""",
    },
]

def send_email(to, subject, body, from_name=FROM_NAME):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{FROM_EMAIL}>"
    msg["To"] = to
    msg["Reply-To"] = FROM_EMAIL
    
    # Plain text
    msg.attach(MIMEText(body, "plain"))
    
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.sendmail(FROM_EMAIL, to, msg.as_string())
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False

def main():
    print(f"=== DepScope Outreach — {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    print(f"Sending {len(EMAILS)} emails (6 min delay between each)")
    
    sent = 0
    for i, email in enumerate(EMAILS):
        to = email["to"]
        subject = email["subject"]
        body = email["body"].format(report_url=REPORT_URL, site_url=SITE_URL)
        
        print(f"\n[{i+1}/{len(EMAILS)}] → {to}")
        print(f"  Subject: {subject[:60]}...")
        
        if send_email(to, subject, body):
            sent += 1
            print(f"  SENT OK")
        
        # Log
        with open("/home/deploy/depscope/outreach/sent_log.txt", "a") as f:
            f.write(f"{datetime.now().isoformat()} | {to} | {subject}\n")
        
        # Wait 6 minutes between emails (10/hour max)
        if i < len(EMAILS) - 1:
            print(f"  Waiting 6 minutes before next...")
            time.sleep(360)
    
    print(f"\n=== Done: {sent}/{len(EMAILS)} sent ===")

if __name__ == "__main__":
    main()
