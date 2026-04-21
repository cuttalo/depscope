import os
"""
Follow-up for opened-but-not-replied after 72h.
Run daily via cron. Only sends 1 follow-up per recipient (tracked by campaign='launch_2026_04_20_followup').
"""
import asyncio, asyncpg, smtplib, secrets, random, re
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
BASE = "https://depscope.dev"
CAMPAIGN_ORIG = "launch_2026_04_20"
CAMPAIGN_FU = "launch_2026_04_20_followup"

MIN_DELAY = 90
MAX_DELAY = 210

ITALIAN_OUTLETS_FRAGMENT = (
    "Sole", "Repubblica", "Corriere", "Hardware Upgrade",
    "Wired Italia", "La Stampa", "Punto Informatico", "Tom's Italia",
)


def is_italian(outlet):
    if not outlet: return False
    return any(f.lower() in outlet.lower() for f in ITALIAN_OUTLETS_FRAGMENT)


def body_en(first, tid):
    pixel = f"{BASE}/t/o/{tid}.gif"
    link = f"{BASE}/t/c/{tid}?url=https%3A%2F%2Fdepscope.dev"
    return f"""Hi {first},

Quick follow-up. I saw you opened my note on [depscope.dev]({link}) but I know inboxes are busy.

If the AI-agent-hammering-the-registries angle matters for what you cover, I can send whatever's most useful on your side: architecture notes, OSV ingestion diffs, MCP tool list.

If it's not a fit, ignore this too — no follow-up on the follow-up.

Vincenzo Rubino — Cuttalo srl
depscope.dev

<img src="{pixel}" width="1" height="1" alt="" style="display:none" />
"""


def body_it(first, tid):
    pixel = f"{BASE}/t/o/{tid}.gif"
    link = f"{BASE}/t/c/{tid}?url=https%3A%2F%2Fdepscope.dev"
    return f"""Ciao {first},

Un follow-up breve. Ho visto che hai aperto il messaggio su [depscope.dev]({link}), so che le inbox sono piene.

Se l'angolo "AI agent che martellano le registry" ti interessa per quello che segui tu, ti mando quello che ti è più utile: note sull'architettura, diff di ingestion OSV, lista di tool MCP.

Se non è rilevante per te, ignora anche questo — non continuerò.

Vincenzo Rubino — Cuttalo srl
depscope.dev

<img src="{pixel}" width="1" height="1" alt="" style="display:none" />
"""


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
    return md.strip()


def send_one(row, body_md, subject):
    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr((FROM_NAME, FROM))
    msg["To"] = row["to_email"] if not row["to_name"] else formataddr((row["to_name"], row["to_email"]))
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="cuttalo.com")
    msg["Reply-To"] = FROM
    msg["List-Unsubscribe"] = f"<mailto:{FROM}?subject=unsubscribe>"
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

    # Candidates: original launch emails sent ≥72h ago, opened (at least 1 event), not yet replied,
    # and NOT already in follow-up campaign.
    rows = await conn.fetch("""
        SELECT oe.id, oe.to_email, oe.to_name, oe.outlet
        FROM outreach_emails oe
        WHERE oe.campaign = $1
          AND oe.sent_at IS NOT NULL
          AND oe.sent_at < NOW() - INTERVAL '72 hours'
          AND oe.reply_at IS NULL
          AND oe.bounce_at IS NULL
          AND EXISTS (
              SELECT 1 FROM email_events ee
              WHERE ee.tracking_id = oe.tracking_id AND ee.event_type='open'
          )
          AND NOT EXISTS (
              SELECT 1 FROM outreach_emails fu
              WHERE fu.campaign = $2 AND fu.to_email = oe.to_email
          )
        ORDER BY oe.id
    """, CAMPAIGN_ORIG, CAMPAIGN_FU)

    print(f"[{datetime.now(timezone.utc).isoformat()}] follow-up candidates: {len(rows)}")
    if not rows:
        await conn.close()
        return

    for i, r in enumerate(rows, 1):
        first = (r["to_name"] or "").split(" ")[0] or "there"
        tid = secrets.token_urlsafe(16)
        italian = is_italian(r["outlet"])
        if italian:
            subject = "RE: " + "milioni di AI coding agent e npm / PyPI — follow-up veloce"
            body = body_it(first, tid)
        else:
            subject = "RE: the AI agent / registry angle — quick follow-up"
            body = body_en(first, tid)

        try:
            send_one(r, body, subject)
            await conn.execute("""
                INSERT INTO outreach_emails
                    (tracking_id, to_email, to_name, outlet, subject, body_md, campaign, sent_at, smtp_response)
                VALUES ($1,$2,$3,$4,$5,$6,$7,NOW(),'250 OK')
            """, tid, r["to_email"], r["to_name"], r["outlet"], subject, body, CAMPAIGN_FU)
            print(f"  [{i}/{len(rows)}] follow-up -> {r['to_email']}")
        except Exception as e:
            print(f"  [{i}/{len(rows)}] ERR {r['to_email']}: {str(e)[:120]}")
        if i < len(rows):
            await asyncio.sleep(random.randint(MIN_DELAY, MAX_DELAY))

    await conn.close()
    print(f"[{datetime.now(timezone.utc).isoformat()}] follow-up done")


if __name__ == "__main__":
    asyncio.run(main())
