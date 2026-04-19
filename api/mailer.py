"""SMTP + Sent-folder helper used by all DepScope transactional email.

Emails are relayed through the central mail VM (10.10.0.130) on port 25 and a
copy is persisted to the sender's IMAP ``Sent`` folder via ``doveadm save``
over SSH. Saving to the Sent folder is a hard requirement coming from the
``feedback_save_sent_emails`` rule: without it, messages disappear for the
human operator who reads the depscope@cuttalo.com mailbox through Roundcube.
"""
from __future__ import annotations

import os
import smtplib
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from typing import Optional


SMTP_HOST = os.getenv("DEPSCOPE_SMTP_HOST", "10.10.0.130")
SMTP_PORT = int(os.getenv("DEPSCOPE_SMTP_PORT", "25"))
SMTP_FROM_EMAIL = os.getenv("DEPSCOPE_SMTP_FROM", "depscope@cuttalo.com")
SMTP_FROM_NAME = os.getenv("DEPSCOPE_SMTP_FROM_NAME", "DepScope")

# SSH host + account used to reach Dovecot on the mail VM.
MAIL_SSH_HOST = os.getenv("DEPSCOPE_MAIL_SSH_HOST", "deploy@10.10.0.130")
MAIL_SSH_TIMEOUT = int(os.getenv("DEPSCOPE_MAIL_SSH_TIMEOUT", "8"))


def _build_message(
    to: str,
    subject: str,
    html: str,
    plain: str,
    in_reply_to: Optional[str] = None,
) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = make_msgid(domain="depscope.dev")
    msg["Reply-To"] = SMTP_FROM_EMAIL
    msg["List-Unsubscribe"] = f"<mailto:{SMTP_FROM_EMAIL}?subject=unsubscribe>"
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    msg["Auto-Submitted"] = "auto-generated"
    msg["X-Mailer"] = "DepScope"
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to

    # RFC-2046 says the last part is the preferred one, so HTML goes last.
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def send_email(
    to: str,
    subject: str,
    html: str,
    plain: str,
    in_reply_to: Optional[str] = None,
) -> bool:
    """Send a multipart HTML+plain email and save a copy in Sent.

    Returns ``True`` when SMTP relay succeeded. Failure to save a copy in the
    Sent folder is logged but does not flip the return value &mdash; the
    outbound message has already been accepted by the relay at that point.
    """
    msg = _build_message(to, subject, html, plain, in_reply_to=in_reply_to)
    raw = msg.as_string()
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as s:
            s.sendmail(SMTP_FROM_EMAIL, [to], raw)
    except Exception as exc:  # pragma: no cover - relay handles most problems
        print(f"[mailer] SMTP send failed to={to!r} subject={subject!r}: {exc}")
        return False

    # Best-effort: persist to the sender's Sent mailbox via doveadm.
    try:
        _save_to_sent(SMTP_FROM_EMAIL, raw)
    except Exception as exc:  # pragma: no cover
        print(f"[mailer] save_to_sent failed: {exc}")
    return True


def _save_to_sent(account_email: str, raw_message: str) -> None:
    """Append ``raw_message`` to ``account_email``'s Sent folder via SSH.

    We pipe the raw RFC-822 bytes through ``ssh deploy@vm130 sudo doveadm save
    -u <account> -m Sent`` which delegates to Dovecot so the message ends up
    both on disk (Maildir) and in the index &mdash; Roundcube sees it at once.
    After saving, we flag the message as ``\\Seen`` so it shows up under
    "Sent" instead of as an unread item.
    """
    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=no",
        "-o", f"ConnectTimeout={MAIL_SSH_TIMEOUT}",
        MAIL_SSH_HOST,
        f"sudo -n doveadm save -u {account_email} -m Sent",
    ]
    proc = subprocess.run(
        cmd,
        input=raw_message.encode("utf-8"),
        capture_output=True,
        timeout=MAIL_SSH_TIMEOUT + 2,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"doveadm save rc={proc.returncode} err={proc.stderr.decode('utf-8', 'replace')[:200]}"
        )

    # Mark the newly-saved message as Seen so Roundcube displays it in Sent
    # rather than as "unread". We flag the highest UID we can find.
    flag_cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=no",
        "-o", f"ConnectTimeout={MAIL_SSH_TIMEOUT}",
        MAIL_SSH_HOST,
        (
            f"sudo -n doveadm flags add -u {account_email} '\\Seen' "
            f"mailbox Sent SAVEDSINCE 5s"
        ),
    ]
    subprocess.run(flag_cmd, capture_output=True, timeout=MAIL_SSH_TIMEOUT + 2)
