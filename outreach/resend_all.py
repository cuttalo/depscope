"""RESEND ALL — tutte le email con From header fixato"""
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

SMTP_HOST = "10.10.0.130"
SMTP_PORT = 25
FROM = "depscope@cuttalo.com"
FROM_NAME = "Vincenzo Rubino - DepScope"
DEVTO = "https://dev.to/depscope/i-built-a-free-api-that-checks-package-health-for-ai-agents-3ip8"
REPORT = "https://depscope.dev/report.md"
SITE = "https://depscope.dev"
NPM = "https://www.npmjs.com/package/depscope-mcp"

# Leggi sent_log per avere la lista email da ri-inviare
import os
sent = set()
log_path = "/home/deploy/depscope/outreach/sent_log.txt"
if os.path.exists(log_path):
    with open(log_path) as f:
        for line in f:
            parts = line.strip().split(" | ")
            if len(parts) >= 3:
                sent.add(parts[1].strip())

print(f"Email precedentemente inviate (bounced): {len(sent)}")
for e in sorted(sent):
    print(f"  {e}")

# Tutte le email da inviare con body personalizzato
EMAILS = []

# Helper
def add(to, subject, body):
    EMAILS.append({"to": to, "subject": subject, "body": body})

# === TESTATE TECH ===
add("editorial@devclass.com", "Data: 35% of popular packages score below 60/100 in new health analysis",
    f"Hi DevClass team,\n\nWe analyzed 14,700+ packages across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems and 10 more). 35% fall into caution or critical health categories.\n\nKey findings: pkg-dir (deprecated) gets 80M downloads/week, ms gets 412M/week with no updates, mlflow carries 18 CVEs.\n\nFull article: {DEVTO}\nReport data: {REPORT}\n\nVincenzo Rubino\nCuttalo srl - {SITE}")

add("tips@bleepingcomputer.com", "mlflow has 18 unpatched vulnerabilities - package health data from 14,700+ packages",
    f"Hi,\n\nNew supply chain data: mlflow (most popular ML tracker) has 18 active CVEs. gradio has 11. annotated-types (core Pydantic dep) scores 36/100 despite 160M weekly downloads.\n\nFull analysis: {DEVTO}\n\nVincenzo Rubino\nDepScope ({SITE})")

add("info@thehackernews.com", "Supply chain data: deprecated npm packages still get 80M+ downloads/week",
    f"Hi,\n\nDeprecated packages with known issues are still massively downloaded: pkg-dir 80M/week (health 37), request 16M/week (deprecated since 2020).\n\nFull article: {DEVTO}\n\nVincenzo Rubino\nDepScope ({SITE})")

add("editors@infoq.com", "Ecosystem comparison: Cargo leads npm and PyPI in package health",
    f"Hi InfoQ,\n\nCargo (Rust) leads at 74.5/100 avg health, npm at 70, PyPI at 61.5. The Python finding: AI/ML packages have the worst security profile.\n\nFull article: {DEVTO}\n\nVincenzo Rubino\nCuttalo srl")

add("tips@techcrunch.com", "AI coding agents are suggesting deprecated packages - data at scale",
    f"Hi,\n\nAI coding assistants suggest packages from training data without checking. request (deprecated since 2020) still gets 16M downloads/week.\n\nWe built a free API for agents to check before suggesting: {SITE}\nFull story: {DEVTO}\n\nVincenzo Rubino\nCuttalo srl")

# === SECURITY ===
add("press@socket.dev", "Package health data: 14,700+ packages analyzed - findings overlap with your work",
    f"Hi Socket team,\n\n35% of packages score below 60/100. AI/ML packages have worst security. mlflow 18 CVEs, gradio 11.\n\nFull article: {DEVTO}\nFree API: {SITE}/api/check/npm/express\n\nVincenzo Rubino\nCuttalo srl")

add("press@snyk.io", "New data: AI/ML packages have worst security profile - 14,700+ packages",
    f"Hi Snyk team,\n\nPyPI averages 61.5/100 health vs npm 70 and Cargo 74.5. mlflow 18 CVEs, gradio 11.\n\nArticle: {DEVTO}\nReport: {REPORT}\n\nVincenzo Rubino\nCuttalo srl")

add("pr@jfrog.com", "Package supply chain data: 80M weekly downloads to deprecated npm packages",
    f"Hi JFrog,\n\nDeprecated packages embedded deep in dependency trees get 80M+ downloads/week. Article: {DEVTO}\n\nVincenzo Rubino\nCuttalo srl")

add("DarkReadingNews@darkreading.com", "Data: deprecated npm packages with 80M+ weekly downloads persist in supply chains",
    f"Hi Dark Reading,\n\npkg-dir (deprecated): 80M downloads/week. request (deprecated since 2020): 16M/week. AI agents compound the problem.\n\nFull data: {DEVTO}\n\nVincenzo Rubino\nDepScope ({SITE})")

add("press@securityweek.com", "Research: AI/ML packages show worst vulnerability profile in 14,700+ package (17 ecosystems) analysis",
    f"Hi SecurityWeek,\n\nmlflow 18 CVEs, gradio 11. PyPI avg health 61.5/100 (lowest). Cargo leads at 74.5.\n\nArticle: {DEVTO}\n\nVincenzo Rubino\nDepScope ({SITE})")

# === AI COMPANIES ===
add("mcp@anthropic.com", "MCP server for package health - built for Claude Code agents",
    f"Hi Anthropic MCP team,\n\nWe built DepScope - free API + MCP server ({NPM}) for package health. 10 endpoints, no auth.\n\nArticle: {DEVTO}\nAPI: {SITE}/api/check/npm/express\n\nVincenzo Rubino\nCuttalo srl")

add("partnerships@anthropic.com", "Free package intelligence API for Claude coding agents",
    f"Hi Anthropic,\n\nDepScope ({SITE}) - free API for checking package health. MCP server on npm ({NPM}). Article: {DEVTO}\n\nVincenzo Rubino\nCuttalo srl")

add("partnerships@openai.com", "Package health API for ChatGPT - free, already in GPT Store",
    f"Hi OpenAI,\n\nDepScope GPT is live in the GPT Store. Free API, no auth. Article: {DEVTO}\nOpenAPI: {SITE}/openapi-gpt.json\n\nVincenzo Rubino\nCuttalo srl")

add("hi@cursor.com", "Free MCP server for package health - built for Cursor",
    f"Hi Cursor team,\n\nMCP server: npx depscope-mcp. 10 endpoints. Free. Article: {DEVTO}\n\nVincenzo Rubino\nCuttalo srl")

add("support@codeium.com", "Package health MCP server for Windsurf",
    f"Hi Windsurf team,\n\nFree MCP server for package health: npx depscope-mcp. Article: {DEVTO}\n\nVincenzo Rubino")

add("hi@sourcegraph.com", "Package health API for Cody",
    f"Hi Sourcegraph,\n\nFree API for package health. Article: {DEVTO}\nAPI: {SITE}\n\nVincenzo Rubino")

add("hi@continue.dev", "Free package health tool for Continue",
    f"Hi Continue team,\n\nFree API + MCP server for package health. Article: {DEVTO}\n\nVincenzo Rubino")

add("partnerships@replit.com", "Free package health API for Replit Agent",
    f"Hi Replit,\n\nDepScope provides real-time package health. Article: {DEVTO}\nAPI: {SITE}\n\nVincenzo Rubino")

# === NEWSLETTER ===
add("editor@cooperpress.com", "For JS/Node Weekly: npm package health analysis",
    f"Hi Peter,\n\nArticle for consideration: {DEVTO}\n\nnpm findings: ms 412M downloads/week with no updates, pkg-dir 80M/week deprecated.\nFree API: {SITE}/api/check/npm/express\n\nVincenzo Rubino")

add("hello@console.dev", "Dev tool submission: DepScope - free package health API",
    f"Hi Console,\n\nSubmitting DepScope: free API for package health (17 ecosystems). Article: {DEVTO}\nTry: curl {SITE}/api/check/npm/express\n\nVincenzo Rubino")

add("editors@changelog.com", "Package health data: 35% of popular packages need attention",
    f"Hi Changelog,\n\nArticle: {DEVTO}\n35% of 14,700+ packages score below 60/100. AI/ML has worst security. Free API at {SITE}.\n\nVincenzo Rubino")

add("stories@hackernoon.com", "Article: The State of Package Health 2026 - 14,700+ packages",
    f"Hi HackerNoon,\n\nSubmitting: {DEVTO}\n\nKey findings: 35% packages need attention, deprecated packages get 80M+ downloads/week.\n\nVincenzo Rubino")

# === EXPERTS ===
add("liran@lirantal.com", "Your awesome-nodejs-security list inspired this - 14,700+ packages analyzed",
    f"Hi Liran,\n\nYour work on npm supply chain security inspired DepScope. We analyzed 14,700+ packages.\n\nrequest: still 16M downloads/week. pkg-dir: 80M/week, health 37.\n\nArticle: {DEVTO}\nFree API: {SITE}/api/check/npm/express\n\nVincenzo Rubino\nCuttalo srl")

add("feross@socket.dev", "DepScope health data complements Socket's work - 14,700+ packages",
    f"Hi Feross,\n\nWhile Socket focuses on malware detection, DepScope provides quick health scores for AI agents. AI/ML corner of PyPI has worst security: mlflow 18 CVEs.\n\nArticle: {DEVTO}\nAPI: {SITE}\n\nVincenzo Rubino")

add("seth@python.org", "PyPI security data: avg health 61.5/100 among 17 ecosystems (14,700+ packages analyzed)",
    f"Hi Seth,\n\nPyPI has the lowest health score (61.5/100) vs npm (70) and Cargo (74.5). mlflow 18 CVEs, gradio 11.\n\nArticle: {DEVTO}\n\nVincenzo Rubino\nCuttalo srl")

add("william@trailofbits.com", "pip-audit data in context: PyPI health across 14,700+ packages",
    f"Hi William,\n\nPyPI averages 61.5/100 health. We filter vulns to latest version only - Django goes from 272 to 1.\n\nArticle: {DEVTO}\n\nVincenzo Rubino")

add("di@python.org", "PyPI health: AI/ML packages have worst security profile",
    f"Hi Dustin,\n\nmlflow 18 CVEs, gradio 11, annotated-types 160M downloads/week health 36. Ironic: tools to build AI have weakest security.\n\nArticle: {DEVTO}\n\nVincenzo Rubino")

add("myles.borins@gmail.com", "npm data: 412M weekly downloads to stale packages",
    f"Hi Myles,\n\nms: 412M/week no update in 1+ year. readable-stream: 273M/week stale. These are embedded in every Node.js app.\n\nArticle: {DEVTO}\n\nVincenzo Rubino")

def send(to, subject, body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{FROM_NAME} <{FROM}>"
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
    print(f"\n=== RESEND ALL - {datetime.now().strftime('%H:%M')} - {len(EMAILS)} emails ===")
    ok = 0
    for i, e in enumerate(EMAILS):
        print(f"[{i+1}/{len(EMAILS)}] {e['to']}")
        if send(e['to'], e['subject'], e['body']):
            ok += 1
            print("  SENT")
        with open("/home/deploy/depscope/outreach/resent_log.txt", "a") as f:
            f.write(f"{datetime.now().isoformat()} | {e['to']} | {e['subject']}\n")
        if i < len(EMAILS) - 1:
            time.sleep(360)  # 6 min
    print(f"\n=== Done: {ok}/{len(EMAILS)} sent ===")
