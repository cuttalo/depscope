"""Email to AI companies that build coding agents — the most important outreach"""
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
NPM = "https://www.npmjs.com/package/depscope-mcp"

EMAILS = [
    # ANTHROPIC — they build Claude Code, MCP is THEIR protocol
    {
        "to": "mcp@anthropic.com",
        "subject": "MCP server for package health — built for Claude Code agents",
        "body": f"""Hi Anthropic MCP team,

We built DepScope, a free package health API designed specifically for AI coding agents.

The problem: Claude Code (and other agents) suggest packages from training data without knowing if they're deprecated, vulnerable, or unmaintained. We analyzed 14,700+ packages and found 35% score below 60/100 on our health index.

What we built:
- Free API: {SITE}/api/check/npm/express (no auth, 200 req/min)
- MCP server: {NPM} (npx depscope-mcp)
- 10 endpoints: check, latest, exists, search, alternatives, compare, scan, vulns, health, now
- ChatGPT GPT already live in GPT Store

The API is designed for the exact use case MCP was built for: giving agents access to real-time data they can't get from training.

Data highlights from our report ({REPORT}):
- request (deprecated since 2020): still 16M downloads/week
- mlflow: 18 active CVEs
- ms: 412M downloads/week, no update in 1+ year
- PyPI avg health 61.5 vs Cargo 74.5

We'd love for DepScope to be considered for the MCP server registry or as a recommended tool for Claude Code users.

Happy to discuss integration, custom endpoints, or anything that helps agents make better package decisions.

Best,
Vincenzo Rubino
Cuttalo srl — depscope@cuttalo.com
{SITE}"""
    },
    {
        "to": "partnerships@anthropic.com",
        "subject": "Free package intelligence API for Claude coding agents — DepScope",
        "body": f"""Hi Anthropic team,

Quick intro: we built DepScope ({SITE}), a free API that checks package health for npm, PyPI, and Cargo. It's designed for AI coding agents.

Why it matters: AI agents suggest deprecated and vulnerable packages because they rely on training data. DepScope provides real-time verification — health score, vulnerabilities, versions, alternatives.

We already have an MCP server on npm ({NPM}) and a ChatGPT GPT in the GPT Store.

Would love to explore how DepScope could be useful for Claude Code users, either as a recommended MCP server or as a built-in capability.

Our report analyzing 14,700+ packages: {REPORT}

Best,
Vincenzo Rubino
Cuttalo srl"""
    },
    # OPENAI
    {
        "to": "partnerships@openai.com",
        "subject": "Package health API for Codex/ChatGPT coding — free, no auth, already in GPT Store",
        "body": f"""Hi OpenAI team,

We built DepScope, a free package health API designed for AI coding agents. We already have a GPT in the GPT Store ("DepScope") that calls our API to verify packages before suggesting installs.

The problem it solves: coding agents suggest deprecated, vulnerable, or unmaintained packages from training data. DepScope provides real-time data — health scores, CVEs, version info, alternatives.

Stats from our analysis of 14,700+ packages:
- 35% score below 60/100 health
- Deprecated packages like request still get 16M downloads/week
- AI/ML packages (mlflow, gradio) have the worst security profile

API: {SITE} — free, no auth, 200 req/min
OpenAPI spec: {SITE}/openapi-gpt.json
Report: {REPORT}

Would love to discuss deeper integration with Codex, ChatGPT, or the GPT Store.

Vincenzo Rubino
Cuttalo srl"""
    },
    # CURSOR
    {
        "to": "hi@cursor.com",
        "subject": "Free MCP server for package health checks — built for Cursor agents",
        "body": f"""Hi Cursor team,

We built DepScope — a free API + MCP server that checks package health before installation. It's specifically designed for AI coding agents like Cursor.

How it helps Cursor users:
- Agent checks if a package is safe before suggesting `npm install X`
- Verifies the version is correct (not hallucinated)
- Warns about deprecated packages
- Suggests alternatives when needed

MCP server: npx depscope-mcp (on npm: {NPM})
API: {SITE}/api/check/npm/express (no auth)
10 endpoints: check, latest, exists, search, alternatives, compare, scan, vulns, health, now

Our data ({REPORT}): 35% of 14,700+ packages score below 60/100. AI agents compound the problem.

Would love DepScope to be a recommended MCP server for Cursor, or integrated as a default tool.

Best,
Vincenzo Rubino
Cuttalo srl"""
    },
    # CODEIUM/WINDSURF
    {
        "to": "support@codeium.com",
        "subject": "Package health MCP server for Windsurf — free, 10 endpoints",
        "body": f"""Hi Windsurf/Codeium team,

Built a free MCP server for package health checks: DepScope ({SITE}).

Your agents can call it to verify packages before suggesting installs — health score, vulnerabilities, version check, alternatives for deprecated packages.

MCP: npx depscope-mcp
API: no auth, 200 req/min
Ecosystems: npm, PyPI, Cargo

Data: we analyzed 14,700+ packages, 35% have health issues. Report: {REPORT}

Happy to discuss integration.

Vincenzo Rubino - depscope@cuttalo.com"""
    },
    # SOURCEGRAPH / CODY
    {
        "to": "hi@sourcegraph.com",
        "subject": "Package health API for Cody — free dependency intelligence",
        "body": f"""Hi Sourcegraph team,

DepScope ({SITE}) is a free API that provides package health intelligence — health scores, vulnerabilities, version checks, alternatives for deprecated packages.

Could be useful for Cody to verify packages before suggesting them. We support npm, PyPI, Cargo with 10 endpoints and an MCP server.

Report on 14,700+ packages analyzed: {REPORT}

Vincenzo Rubino
Cuttalo srl"""
    },
    # CONTINUE.DEV
    {
        "to": "hi@continue.dev",
        "subject": "Free package health tool for Continue — MCP server + API",
        "body": f"""Hi Continue team,

DepScope ({SITE}) is a free package health API with an MCP server (npx depscope-mcp).

It helps AI coding agents verify packages before suggesting installs — health score, CVEs, versions, alternatives.

10 endpoints, no auth, 200 req/min. npm, PyPI, Cargo.

Would love to be listed as a recommended tool for Continue users.

Vincenzo Rubino - depscope@cuttalo.com"""
    },
    # REPLIT
    {
        "to": "partnerships@replit.com",
        "subject": "Free package health API for Replit Agent — verify before install",
        "body": f"""Hi Replit team,

DepScope ({SITE}) provides real-time package health data for 17 ecosystems. Replit Agent could call our API before suggesting package installs to avoid deprecated, vulnerable, or unmaintained packages.

Free, no auth, 200 req/min. 10 endpoints including check, search, compare, scan.

Data: 35% of 14,700+ packages score below 60/100. Report: {REPORT}

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
    print(f"=== AI Companies Batch — {datetime.now().strftime('%H:%M')} — {len(EMAILS)} emails ===")
    for i, e in enumerate(EMAILS):
        print(f"[{i+1}/{len(EMAILS)}] {e['to']}")
        if send(e['to'], e['subject'], e['body']):
            print("  SENT")
        with open("/home/deploy/depscope/outreach/sent_log.txt", "a") as f:
            f.write(f"{datetime.now().isoformat()} | {e['to']} | {e['subject']}\n")
        if i < len(EMAILS) - 1:
            print("  Waiting 6 min...")
            time.sleep(360)
    print("=== AI Companies batch done ===")
