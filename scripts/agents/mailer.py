#!/usr/bin/env python3
"""MAILER Agent — Email Management via IMAP/SMTP.

Monitors inbox, categorizes emails, creates opportunities.
Manages threads (links replies to originals).
Sends approved email replies.
"""

import asyncio
import imaplib
import email as email_lib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
import hashlib

from .common import (
    get_pool, log_action, update_platform_status,
    IMAP_HOST, IMAP_PORT, SMTP_HOST, SMTP_PORT,
    EMAIL_USER, EMAIL_PASS, EMAIL_FROM_NAME,
)


def _make_thread_id(sender: str, subject: str) -> str:
    """Generate a thread ID from sender + cleaned subject."""
    clean_subject = subject.lower()
    for prefix in ["re:", "fwd:", "fw:"]:
        while clean_subject.startswith(prefix):
            clean_subject = clean_subject[len(prefix):].strip()
    key = f"{sender.lower().strip()}:{clean_subject.strip()}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


async def check_inbox(pool) -> dict:
    """Check IMAP inbox for new emails, save as opportunities."""
    print("[MAILER] Checking inbox...")
    found = 0
    replies = 0

    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("INBOX")

        status, data = mail.search(None, "UNSEEN")
        if status != "OK" or not data[0]:
            print("  [MAILER] No new messages")
            mail.logout()
            return {"found": 0, "replies": 0}

        # Get existing URLs to avoid duplicates
        async with pool.acquire() as conn:
            existing = set(r["url"] for r in await conn.fetch("SELECT url FROM agent_opportunities WHERE platform = 'email'"))

        msg_ids = data[0].split()
        for msg_id in msg_ids[:10]:
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue
            msg = email_lib.message_from_bytes(msg_data[0][1])
            subject = str(email_lib.header.decode_header(msg["Subject"])[0][0] or "")
            if isinstance(subject, bytes):
                subject = subject.decode("utf-8", errors="replace")
            sender = msg["From"] or ""
            msg_date = msg["Date"] or ""

            # Skip bounces and auto-replies
            if any(kw in subject.lower() for kw in ["bounce", "undeliverable", "auto-reply", "out of office", "mailer-daemon"]):
                continue
            if any(kw in sender.lower() for kw in ["mailer-daemon", "postmaster"]):
                continue

            # Get body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")[:1000]
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")[:1000]

            email_url = f"email://{sender}/{msg_id.decode()}"
            if email_url in existing:
                continue

            thread_id = _make_thread_id(sender, subject)
            is_reply = subject.lower().startswith("re:")

            if is_reply:
                suggested_action = "reply"
                replies += 1
            else:
                suggested_action = "Reply to email with Claude-generated response"

            title = f"Email da {sender}: {subject}"
            extra = f"From: {sender}\nDate: {msg_date}\n\n{body[:500]}"

            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO agent_opportunities (platform, url, title, relevance_score, suggested_action, suggested_content, status, platform_icon) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                    "email", email_url, title[:200], 7, suggested_action, extra, "found", "\U0001f4e7"
                )

            # Log as action with thread tracking
            await log_action(
                pool, "email_received", "email", sender, 
                f"Subject: {subject}\n{body[:300]}", 
                "executed", thread_id=thread_id
            )

            found += 1
            print(f"  [+] Email from {sender[:40]}: {subject[:50]}")

        mail.logout()
    except Exception as e:
        print(f"  [WARN] Email check failed: {e}")

    print(f"[MAILER] Found {found} new emails ({replies} replies)")
    return {"found": found, "replies": replies}


async def send_approved_emails(pool) -> dict:
    """Send emails for opportunities with status='execute' and platform='email'."""
    print("[MAILER] Sending approved emails...")
    
    async with pool.acquire() as conn:
        to_send = await conn.fetch(
            "SELECT * FROM agent_opportunities WHERE status = 'execute' AND platform = 'email' ORDER BY created_at LIMIT 5"
        )
    
    if not to_send:
        print("  No emails to send")
        return {"sent": 0}

    sent = 0
    for opp in to_send:
        opp = dict(opp)
        content = opp.get("suggested_content", "")
        if not content:
            continue

        try:
            sender_email = opp["url"].replace("email://", "").split("/")[0]
            subject_match = opp["title"].replace("Email da ", "").split(": ", 1)
            subject = f"Re: {subject_match[1]}" if len(subject_match) > 1 else "Re: your message"

            thread_id = _make_thread_id(sender_email, subject.replace("Re: ", ""))

            msg = MIMEMultipart()
            msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_USER}>"
            msg["To"] = sender_email
            msg["Subject"] = subject
            msg.attach(MIMEText(content, "plain"))

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.sendmail(EMAIL_USER, [sender_email], msg.as_string())

            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE agent_opportunities SET status = 'done', executed_at = NOW() WHERE id = $1",
                    opp["id"]
                )
            
            await log_action(
                pool, "send_email", "email", sender_email, 
                content[:200], "executed", thread_id=thread_id
            )
            await update_platform_status(pool, "email", last_action=True)
            
            sent += 1
            print(f"  [OK] Sent email reply to {sender_email}")

        except Exception as e:
            print(f"  [ERR] Email send failed: {e}")
            await log_action(pool, "send_email", "email", opp["url"], content[:200], "failed", str(e)[:200])

    print(f"[MAILER] Sent {sent} emails")
    return {"sent": sent}


async def run(pool) -> dict:
    """Main mailer entry point."""
    inbox = await check_inbox(pool)
    sends = await send_approved_emails(pool)
    return {**inbox, **sends}


if __name__ == "__main__":
    async def _main():
        pool = await get_pool()
        try:
            await run(pool)
        finally:
            await pool.close()
    asyncio.run(_main())
