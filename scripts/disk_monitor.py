"""Disk watchdog for DepScope VM.

Hourly cron. Triggers tiered response based on / filesystem usage:
  < 80%  : silent (just log)
  >= 80% : cleanup pass (old logs >7d, .bak dirs >3d, __pycache__)
  >= 90% : cleanup + urgent email to depscope@cuttalo.com
  >= 95% : cleanup + email + pm2 stop depscope-web (keep API alive)

Idempotent. Never deletes anything under /home/deploy/depscope/backups or the
Postgres data dir — those are sacred.
"""
from __future__ import annotations
import os
import shutil
import smtplib
import subprocess
import sys
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

ROOT = Path("/home/deploy/depscope")
PROTECTED = {
    ROOT / "backups",
    ROOT / ".venv",
    Path("/var/lib/postgresql"),
}

ALERT_EMAIL = os.environ.get("DEPSCOPE_ALERT_EMAIL", "depscope@cuttalo.com")
HOST_TAG = os.environ.get("HOSTNAME", "vm140-depscope")


def usage_pct(path: str = "/") -> int:
    st = shutil.disk_usage(path)
    return int(st.used * 100 / st.total)


def human(n: int) -> str:
    for unit in ("B", "K", "M", "G", "T"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}P"


def is_protected(p: Path) -> bool:
    try:
        rp = p.resolve()
    except Exception:
        return True
    for guard in PROTECTED:
        try:
            rp.relative_to(guard)
            return True
        except ValueError:
            continue
    return False


def clean_old_logs(days: int = 7) -> int:
    """Delete regular files under /var/log/depscope older than N days. Never
    deletes directories or symlinks."""
    cutoff = time.time() - days * 86400
    log_dir = Path("/var/log/depscope")
    freed = 0
    if not log_dir.exists():
        return 0
    for f in log_dir.iterdir():
        if not f.is_file():
            continue
        try:
            if f.stat().st_mtime < cutoff:
                sz = f.stat().st_size
                f.unlink()
                freed += sz
        except Exception as e:
            print(f"  skip {f}: {e}")
    return freed


def clean_bak_dirs(days: int = 3) -> int:
    """Remove .bak directories (Next.js build backups, python .bak_* leftovers)
    older than N days under /home/deploy/depscope."""
    cutoff = time.time() - days * 86400
    freed = 0
    for bak in ROOT.rglob("*.bak*"):
        if is_protected(bak):
            continue
        try:
            if bak.stat().st_mtime >= cutoff:
                continue
            if bak.is_dir():
                sz = sum(f.stat().st_size for f in bak.rglob("*") if f.is_file())
                shutil.rmtree(bak, ignore_errors=True)
            else:
                sz = bak.stat().st_size
                bak.unlink()
            freed += sz
        except Exception as e:
            print(f"  skip {bak}: {e}")
    return freed


def clean_pycache() -> int:
    freed = 0
    for pyc in ROOT.rglob("__pycache__"):
        if is_protected(pyc):
            continue
        try:
            sz = sum(f.stat().st_size for f in pyc.rglob("*") if f.is_file())
            shutil.rmtree(pyc, ignore_errors=True)
            freed += sz
        except Exception as e:
            print(f"  skip {pyc}: {e}")
    return freed


def clean_next_caches() -> int:
    """Remove .next/cache entries older than 7 days (large, regenerated on build)."""
    freed = 0
    cache = ROOT / "frontend" / ".next" / "cache"
    if not cache.exists():
        return 0
    cutoff = time.time() - 7 * 86400
    for f in cache.rglob("*"):
        if not f.is_file():
            continue
        try:
            if f.stat().st_mtime < cutoff:
                sz = f.stat().st_size
                f.unlink()
                freed += sz
        except Exception:
            pass
    return freed


def send_alert(level: str, pct: int, details: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = f"[DepScope][{level}] Disk {pct}% on {HOST_TAG}"
    msg["From"] = f"depscope-monitor@{HOST_TAG}"
    msg["To"] = ALERT_EMAIL
    msg.set_content(
        f"Disk usage on {HOST_TAG} hit {pct}% ({level}).\n\n"
        f"Host: {HOST_TAG}\nTime: {datetime.now(timezone.utc).isoformat()}\n\n"
        f"Details:\n{details}\n"
    )
    try:
        with smtplib.SMTP("localhost", 25, timeout=10) as s:
            s.send_message(msg)
        print(f"  alert email sent to {ALERT_EMAIL}")
    except Exception as e:
        # No local MTA is normal on VM 140. Fallback: write alert file so
        # external monitor or operator sees it.
        alert_path = Path("/var/log/depscope/ALERT_DISK.txt")
        alert_path.write_text(
            f"{datetime.now(timezone.utc).isoformat()} {level} {pct}% "
            f"on {HOST_TAG}\n{details}\n(email send failed: {e})\n"
        )
        print(f"  alert email FAILED ({e}); wrote {alert_path}")


def pm2_stop_web() -> str:
    try:
        out = subprocess.run(
            ["pm2", "stop", "depscope-web"],
            capture_output=True, text=True, timeout=30,
        )
        return f"pm2 stop depscope-web rc={out.returncode} {out.stdout.strip()} {out.stderr.strip()}"
    except Exception as e:
        return f"pm2 stop failed: {e}"


def main() -> int:
    pct = usage_pct("/")
    ts = datetime.now(timezone.utc).isoformat()
    print(f"[{ts}] disk usage: {pct}%")

    if pct < 80:
        return 0

    freed_total = 0
    report = [f"usage={pct}%"]

    f = clean_old_logs(days=7)
    report.append(f"logs>7d: freed {human(f)}")
    freed_total += f

    f = clean_bak_dirs(days=3)
    report.append(f"*.bak>3d: freed {human(f)}")
    freed_total += f

    f = clean_pycache()
    report.append(f"__pycache__: freed {human(f)}")
    freed_total += f

    f = clean_next_caches()
    report.append(f".next/cache>7d: freed {human(f)}")
    freed_total += f

    new_pct = usage_pct("/")
    report.append(f"usage_after={new_pct}%  freed_total={human(freed_total)}")
    summary = "\n  ".join(report)
    print(f"  {summary}")

    if pct >= 95:
        send_alert("CRITICAL", pct, summary)
        print("  " + pm2_stop_web())
    elif pct >= 90:
        send_alert("WARNING", pct, summary)

    return 0


if __name__ == "__main__":
    sys.exit(main())
