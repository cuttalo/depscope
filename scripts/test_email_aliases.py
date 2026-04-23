#!/usr/bin/env python3
"""Send a test message to each depscope.dev alias and verify arrival in
depscope@cuttalo.com inbox via IMAP.

Aliases tested: privacy, security, legal, takedown, abuse, postmaster,
                info, admin, hello, contact (+ one catch-all edge case).
"""
import asyncio
import imaplib
import email
import os
import ssl
import smtplib
import sys
import time
import uuid
from email.mime.text import MIMEText

SMTP_HOST = os.environ.get("SMTP_HOST", "mail.cuttalo.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "depscope@cuttalo.com")
SMTP_PASS = os.environ["SMTP_PASS"]

IMAP_HOST = os.environ.get("IMAP_HOST", "mail.cuttalo.com")
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))
IMAP_USER = SMTP_USER
IMAP_PASS = SMTP_PASS

ALIASES = [
    "privacy@depscope.dev",
    "security@depscope.dev",
    "legal@depscope.dev",
    "takedown@depscope.dev",
    "abuse@depscope.dev",
    "postmaster@depscope.dev",
    "info@depscope.dev",
    "admin@depscope.dev",
    "hello@depscope.dev",
    "contact@depscope.dev",
    # catch-all smoke test
    "random-nonexistent-alias@depscope.dev",
]


def send(to_addr: str, marker: str):
    msg = MIMEText(
        f"DepScope alias smoke test\n"
        f"to: {to_addr}\n"
        f"marker: {marker}\n"
        f"ts: {int(time.time())}\n",
        _charset="utf-8",
    )
    msg["Subject"] = f"[DepScope alias test] {to_addr} :: {marker}"
    msg["From"] = f"DepScope Bot <{SMTP_USER}>"
    msg["To"] = to_addr
    msg["X-DepScope-Test-Marker"] = marker

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)


def check_inbox(markers: dict[str, str]) -> dict[str, bool]:
    """For each (marker, alias) check INBOX. Returns dict alias->bool delivered."""
    delivered: dict[str, bool] = {a: False for a in markers.values()}
    ctx = ssl.create_default_context()
    M = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=ctx)
    M.login(IMAP_USER, IMAP_PASS)
    M.select("INBOX")
    # Search last 200 recent messages
    _, data = M.search(None, "ALL")
    ids = data[0].split()
    recent = ids[-200:] if len(ids) > 200 else ids
    for mid in reversed(recent):
        _, msg_data = M.fetch(mid, "(RFC822.HEADER)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        m = msg.get("X-DepScope-Test-Marker", "")
        if m and m in markers:
            delivered[markers[m]] = True
    M.close()
    M.logout()
    return delivered


def main():
    markers: dict[str, str] = {}
    print(f"[*] Sending to {len(ALIASES)} aliases via {SMTP_HOST}:{SMTP_PORT}...")
    for a in ALIASES:
        marker = uuid.uuid4().hex[:16]
        markers[marker] = a
        try:
            send(a, marker)
            print(f"  sent -> {a:<45s} marker={marker}")
        except Exception as e:
            print(f"  FAILED {a}: {e}", file=sys.stderr)

    print("\n[*] Waiting 60s for delivery...")
    time.sleep(60)

    print(f"[*] Checking INBOX of {IMAP_USER}...")
    delivered = check_inbox(markers)

    ok = sum(1 for v in delivered.values() if v)
    print(f"\n=== Result: {ok}/{len(delivered)} delivered ===")
    for a, d in delivered.items():
        print(f"  {'✓' if d else '✗'}  {a}")

    sys.exit(0 if ok == len(delivered) else 1)


if __name__ == "__main__":
    main()
