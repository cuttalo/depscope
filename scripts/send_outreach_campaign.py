import os
"""
Send outreach campaign with anti-burst throttling + proper markdown rendering.
Run at 2026-04-20 12:00 UTC via cron.
"""
import asyncio, asyncpg, random, smtplib, re, sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid, formatdate
from datetime import datetime, timezone

SMTP_USER = "depscope@cuttalo.com"
SMTP_PASS = os.environ.get("SMTP_PASS", "")

DB_URL = os.environ["DATABASE_URL"]
SMTP_HOST = "mail.cuttalo.com"
SMTP_PORT = 587
FROM = "depscope@cuttalo.com"
FROM_NAME = "Vincenzo Rubino — Cuttalo srl"
CAMPAIGN = "launch_2026_04_20"

MIN_DELAY = 90
MAX_DELAY = 210


def md_to_html(md: str) -> str:
    preserved = {}
    def _preserve(m):
        key = f"__IMG{len(preserved)}__"
        preserved[key] = m.group(0)
        return key
    md = re.sub(r"<img[^>]+>", _preserve, md)
    md = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                r'<a href="\2" style="color:#0b73e3;text-decoration:underline">\1</a>', md)
    md = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", md)
    md = re.sub(r"`([^`]+)`",
                r'<code style="background:#f3f3f3;padding:1px 5px;border-radius:3px;font-family:ui-monospace,Menlo,monospace;font-size:90%">\1</code>', md)
    lines = md.split("\n")
    out, buf = [], []
    def flush():
        if buf:
            out.append("<p style='margin:0 0 14px 0'>" + "<br/>".join(buf) + "</p>")
            buf.clear()
    for line in lines:
        if not line.strip(): flush()
        else: buf.append(line)
    flush()
    html = "\n".join(out)
    for k, v in preserved.items():
        html = html.replace(k, v)
    return ("<!doctype html><html><body style=\"font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;"
            "max-width:640px;color:#111;line-height:1.55;font-size:15px\">" + html + "</body></html>")


def plain_text(md: str) -> str:
    md = re.sub(r"<img[^>]+>", "", md)
    md = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", md)
    md = re.sub(r"\*\*(.+?)\*\*", r"\1", md)
    md = re.sub(r"`([^`]+)`", r"\1", md)
    return md.strip()


def send_one(row):
    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr((FROM_NAME, FROM))
    msg["To"] = row["to_email"] if not row["to_name"] else formataddr((row["to_name"], row["to_email"]))
    msg["Subject"] = row["subject"]
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="cuttalo.com")
    msg["Reply-To"] = FROM
    msg["List-Unsubscribe"] = f"<mailto:{FROM}?subject=unsubscribe>"
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    body_md = row["body_md"]
    msg.attach(MIMEText(plain_text(body_md), "plain", "utf-8"))
    msg.attach(MIMEText(md_to_html(body_md), "html", "utf-8"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(FROM, [row["to_email"]], msg.as_string())


async def main():
    conn = await asyncpg.connect(DB_URL)
    rows = await conn.fetch("""
        SELECT id, tracking_id, to_email, to_name, outlet, subject, body_md
        FROM outreach_emails
        WHERE campaign=$1 AND sent_at IS NULL AND bounce_at IS NULL AND scheduled_for <= NOW()
        ORDER BY id
    """, CAMPAIGN)
    print(f"[{datetime.now(timezone.utc).isoformat()}] sending {len(rows)} emails "
          f"(delays {MIN_DELAY}-{MAX_DELAY}s)")

    for i, r in enumerate(rows, 1):
        try:
            send_one(r)
            await conn.execute(
                "UPDATE outreach_emails SET sent_at=NOW(), smtp_response='250 OK' WHERE id=$1",
                r["id"])
            print(f"  [{i}/{len(rows)}] sent to {r['to_email']} ({r['outlet']})")
        except Exception as e:
            err = str(e)[:500]
            await conn.execute(
                "UPDATE outreach_emails SET smtp_response=$1 WHERE id=$2",
                err, r["id"])
            print(f"  [{i}/{len(rows)}] ERR {r['to_email']}: {err}")
        if i < len(rows):
            delay = random.randint(MIN_DELAY, MAX_DELAY)
            await asyncio.sleep(delay)

    await conn.close()
    print(f"[{datetime.now(timezone.utc).isoformat()}] done")


if __name__ == "__main__":
    asyncio.run(main())
