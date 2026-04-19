"""DepScope Alert System — monitors anomalies and emails admin"""
import sys
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/home/deploy/depscope")

ADMIN_EMAIL = ["vincenzo@cuttalo.com", "arch.vincenzo.rubino@gmail.com"]
FROM_EMAIL = "depscope@cuttalo.com"
SMTP_HOST = "10.10.0.130"
SMTP_PORT = 25

THRESHOLDS = {
    "error_rate_pct": 10,        # >10% errori nelle ultime 6h
    "api_down_minutes": 5,       # API non risponde da 5+ minuti
    "disk_usage_pct": 85,        # disco >85%
    "ram_usage_pct": 90,         # RAM >90%
    "zero_calls_hours": 6,       # 0 chiamate nelle ultime 6h (dopo lancio = anomalo)
    "spike_multiplier": 10,      # 10x più chiamate del solito (possibile abuse)
    "db_connection_fail": True,  # DB non connesso
    "pm2_crash_restarts": 10,     # PM2 ha restartato >5 volte
}


def send_alert(subject: str, body: str):
    """Send alert email to admin."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[DepScope Alert] {subject}"
        msg["From"] = FROM_EMAIL
        msg["To"] = ", ".join(ADMIN_EMAIL) if isinstance(ADMIN_EMAIL, list) else ADMIN_EMAIL

        html = f"""
        <div style="font-family:system-ui;max-width:600px;margin:0 auto;padding:20px;">
            <h2 style="color:#ef4444;margin-bottom:10px;">DepScope Alert</h2>
            <h3 style="color:#e2e8f0;">{subject}</h3>
            <div style="background:#12121a;border:1px solid #1e1e2e;border-radius:8px;padding:20px;margin:15px 0;">
                <pre style="color:#94a3b8;white-space:pre-wrap;margin:0;">{body}</pre>
            </div>
            <p style="color:#94a3b8;font-size:13px;">
                Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}<br>
                Dashboard: <a href="https://depscope.dev/admin" style="color:#22d3ee;">depscope.dev/admin</a>
            </p>
        </div>
        """
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.sendmail(FROM_EMAIL, ADMIN_EMAIL if isinstance(ADMIN_EMAIL, list) else [ADMIN_EMAIL], msg.as_string())
        print(f"  ALERT SENT: {subject}")
        return True
    except Exception as e:
        print(f"  ALERT FAILED: {e}")
        return False


async def check_api_health():
    """Check if API is responding."""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/api/stats", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    return False, f"API returned status {resp.status}"
                data = await resp.json()
                return True, data
    except Exception as e:
        return False, str(e)


async def check_db():
    """Check database connection."""
    import asyncpg
    try:
        conn = await asyncpg.connect("postgresql://depscope:${DB_PASSWORD}@localhost:5432/depscope", timeout=5)
        count = await conn.fetchval("SELECT COUNT(*) FROM api_usage")
        await conn.close()
        return True, count
    except Exception as e:
        return False, str(e)


def check_disk():
    """Check disk usage."""
    import shutil
    usage = shutil.disk_usage("/")
    pct = (usage.used / usage.total) * 100
    return pct < THRESHOLDS["disk_usage_pct"], pct


def check_ram():
    """Check RAM usage."""
    with open("/proc/meminfo") as f:
        lines = f.readlines()
    total = int([l for l in lines if "MemTotal" in l][0].split()[1])
    available = int([l for l in lines if "MemAvailable" in l][0].split()[1])
    pct = ((total - available) / total) * 100
    return pct < THRESHOLDS["ram_usage_pct"], pct


def check_pm2():
    """Check PM2 process status."""
    import subprocess
    try:
        result = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=10)
        import json
        processes = json.loads(result.stdout)
        issues = []
        for p in processes:
            name = p.get("name", "?")
            status = p.get("pm2_env", {}).get("status", "unknown")
            restarts = p.get("pm2_env", {}).get("restart_time", 0)
            if status != "online":
                issues.append(f"{name}: {status}")
            if restarts > THRESHOLDS["pm2_crash_restarts"]:
                issues.append(f"{name}: {restarts} restarts (possible crash loop)")
        return len(issues) == 0, issues
    except Exception as e:
        return False, [str(e)]


async def check_usage_anomalies():
    """Check for unusual usage patterns."""
    import asyncpg
    alerts = []
    try:
        conn = await asyncpg.connect("postgresql://depscope:${DB_PASSWORD}@localhost:5432/depscope", timeout=5)

        # Zero calls in last 6 hours (after launch, this is suspicious)
        recent = await conn.fetchval("""
            SELECT COUNT(*) FROM api_usage
            WHERE created_at > NOW() - INTERVAL '6 hours'
        """)
        total = await conn.fetchval("SELECT COUNT(*) FROM api_usage")

        if total > 1000 and recent == 0:  # Raised threshold during launch phase
            alerts.append(f"Zero API calls in last 6 hours (total: {total})")

        # Spike detection: compare last hour vs average
        last_hour = await conn.fetchval("""
            SELECT COUNT(*) FROM api_usage
            WHERE created_at > NOW() - INTERVAL '1 hour'
            AND user_agent NOT LIKE '%Node%'
            AND user_agent NOT LIKE '%python%'
        """)
        avg_hourly = await conn.fetchval("""
            SELECT COUNT(*) / GREATEST(EXTRACT(EPOCH FROM (NOW() - MIN(created_at))) / 3600, 1)
            FROM api_usage
            WHERE user_agent NOT LIKE '%Node%'
            AND user_agent NOT LIKE '%python%'
        """)

        if False and avg_hourly and avg_hourly > 0 and last_hour > avg_hourly * THRESHOLDS["spike_multiplier"]:  # Disabled during launch
            alerts.append(f"Traffic spike: {last_hour} calls last hour (avg: {avg_hourly:.0f}/hr)")

        # Top IP abuse detection
        top_ip = await conn.fetchrow("""
            SELECT ip_address, COUNT(*) as cnt FROM api_usage
            WHERE created_at > NOW() - INTERVAL '1 hour'
            AND ip_address NOT IN ('127.0.0.1', '::1', '10.10.0.140', '10.10.0.1', '91.134.4.25')
            GROUP BY ip_address ORDER BY cnt DESC LIMIT 1
        """)
        if top_ip and top_ip["cnt"] > 500:
            alerts.append(f"Possible abuse: IP {top_ip['ip_address']} made {top_ip['cnt']} calls in 1 hour")

        await conn.close()
    except Exception as e:
        alerts.append(f"DB check failed: {e}")

    return len(alerts) == 0, alerts


async def run_all_checks():
    """Run all checks and send alerts if needed."""
    print(f"=== DepScope Alert Check — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} ===")
    alerts = []

    # 1. API Health
    print("  Checking API...")
    ok, data = await check_api_health()
    if not ok:
        alerts.append(("API Down", f"API is not responding.\nError: {data}"))
    else:
        print(f"  API OK (calls today: {data.get('api_calls_today', '?')})")

    # 2. Database
    print("  Checking DB...")
    ok, data = await check_db()
    if not ok:
        alerts.append(("Database Error", f"Cannot connect to PostgreSQL.\nError: {data}"))
    else:
        print(f"  DB OK ({data} total records)")

    # 3. Disk
    print("  Checking disk...")
    ok, pct = check_disk()
    if not ok:
        alerts.append(("Disk Space Critical", f"Disk usage: {pct:.1f}% (threshold: {THRESHOLDS['disk_usage_pct']}%)"))
    else:
        print(f"  Disk OK ({pct:.1f}%)")

    # 4. RAM
    print("  Checking RAM...")
    ok, pct = check_ram()
    if not ok:
        alerts.append(("RAM Critical", f"RAM usage: {pct:.1f}% (threshold: {THRESHOLDS['ram_usage_pct']}%)"))
    else:
        print(f"  RAM OK ({pct:.1f}%)")

    # 5. PM2
    print("  Checking PM2...")
    ok, issues = check_pm2()
    if not ok:
        alerts.append(("PM2 Process Issue", "\n".join(issues)))
    else:
        print("  PM2 OK")

    # 6. Usage anomalies
    print("  Checking usage patterns...")
    ok, issues = await check_usage_anomalies()
    if not ok:
        for issue in issues:
            alerts.append(("Usage Anomaly", issue))
    else:
        print("  Usage OK")

    # Send alerts
    if alerts:
        print(f"\n  {len(alerts)} ALERT(S) DETECTED!")
        for subject, body in alerts:
            send_alert(subject, body)
    else:
        print("\n  All clear.")

    print(f"=== Done ===\n")


if __name__ == "__main__":
    asyncio.run(run_all_checks())
