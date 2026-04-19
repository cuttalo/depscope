"""Follow-up to newsletters with Dev.to article link"""
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

SMTP_HOST = "10.10.0.130"
SMTP_PORT = 25
FROM = "depscope@cuttalo.com"
DEVTO = "https://dev.to/depscope/i-built-a-free-api-that-checks-package-health-for-ai-agents-3ip8"
REDDIT = "https://www.reddit.com/r/SideProject/comments/1smqk5q/"

EMAILS = [
    {
        "to": "tyler@ui.dev",
        "subject": "Article: Free API that checks package health for AI agents (npm focus)",
        "body": f"""Hi Tyler,

Quick share for Bytes.dev — I published an article about a free API I built for checking 17 ecosystems package health:

{DEVTO}

The interesting angle for your JS audience: ms gets 412M downloads/week with no updates in over a year. pkg-dir (deprecated) gets 80M. These packages persist in dependency trees because nobody audits them.

The API is free, no auth: curl https://depscope.dev/api/check/npm/express

Thought your readers might find it useful.

Vincenzo
depscope@cuttalo.com"""
    },
    {
        "to": "contact@talkpython.fm",
        "subject": "Article: PyPI packages have worst health scores — data from 14,700+ packages",
        "body": f"""Hi Michael,

I published findings from analyzing 14,700+ packages — PyPI has the lowest average health score (61.5/100) compared to npm (70) and Cargo (74.5). The AI/ML corner is the worst: mlflow 18 CVEs, gradio 11.

Full article: {DEVTO}

The API is free for anyone to use: curl https://depscope.dev/api/check/pypi/django

Thought this could be interesting for Talk Python — the intersection of AI tools and supply chain security.

Vincenzo
depscope@cuttalo.com"""
    },
    {
        "to": "yo@dev.to",
        "subject": "New article on Dev.to: package health data for 14,700+ packages across 17 ecosystems",
        "body": f"""Hi Dev.to team,

Just published my first article on Dev.to:
{DEVTO}

It covers a free API I built (DepScope) that checks package health for AI coding agents — with data from analyzing 14,700+ packages. Would love any visibility boost if it fits your editorial picks.

Thanks!
Vincenzo"""
    },
    {
        "to": "hello@hashnode.com",
        "subject": "Cross-posting: Package health analysis article (14,700+ packages analyzed)",
        "body": f"""Hi Hashnode team,

I published an article analyzing the health of 14,700+ packages across 17 ecosystems:
{DEVTO}

Key finding: 35% score below 60/100, deprecated packages get 80M+ downloads/week.

Would love to cross-post on Hashnode. Is there a way to get it featured?

Vincenzo — depscope@cuttalo.com"""
    },
    {
        "to": "content@dzone.com",
        "subject": "Article submission: Package health data — 35% of popular packages need attention",
        "body": f"""Hi DZone,

Submitting an article about software supply chain health based on analyzing 14,700+ packages:

{DEVTO}

Key findings:
- 35% of packages score below 60/100
- Deprecated packages like request still get 16M downloads/week
- AI/ML tooling (mlflow, gradio) has worst security profile
- Cargo ecosystem healthiest, PyPI lowest

Happy to adapt for DZone format.

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
    print(f"=== Follow-up batch — {datetime.now().strftime('%H:%M')} ===")
    for i, e in enumerate(EMAILS):
        print(f"[{i+1}/{len(EMAILS)}] {e['to']}")
        if send(e['to'], e['subject'], e['body']):
            print("  SENT")
        with open("/home/deploy/depscope/outreach/sent_log.txt", "a") as f:
            f.write(f"{datetime.now().isoformat()} | {e['to']} | {e['subject']}\n")
        if i < len(EMAILS) - 1:
            print("  Waiting 6 min...")
            time.sleep(360)
    print("=== Done ===")
