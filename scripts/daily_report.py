"""DepScope Daily Report — email summary of activity"""
import sys
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

sys.path.insert(0, "/home/deploy/depscope")

RECIPIENTS = ["vincenzo@cuttalo.com", "arch.vincenzo.rubino@gmail.com"]
FROM_EMAIL = "depscope@cuttalo.com"
SMTP_HOST = "10.10.0.130"
SMTP_PORT = 25


async def gather_stats():
    import asyncpg
    conn = await asyncpg.connect("postgresql://depscope:${DB_PASSWORD}@localhost:5432/depscope", timeout=5)

    # Totali
    total_calls = await conn.fetchval("SELECT COUNT(*) FROM api_usage")
    total_packages = await conn.fetchval("SELECT COUNT(*) FROM packages")
    total_users = await conn.fetchval("SELECT COUNT(*) FROM users")

    # Oggi
    today_calls = await conn.fetchval("""
        SELECT COUNT(*) FROM api_usage WHERE created_at > CURRENT_DATE
    """)

    # Ieri (per confronto)
    yesterday_calls = await conn.fetchval("""
        SELECT COUNT(*) FROM api_usage
        WHERE created_at BETWEEN CURRENT_DATE - INTERVAL '1 day' AND CURRENT_DATE
    """)

    # Ultimi 7 giorni
    week_calls = await conn.fetchval("""
        SELECT COUNT(*) FROM api_usage WHERE created_at > NOW() - INTERVAL '7 days'
    """)

    # Chiamate per giorno (ultimi 7)
    daily = await conn.fetch("""
        SELECT DATE(created_at) as day, COUNT(*) as calls
        FROM api_usage WHERE created_at > NOW() - INTERVAL '7 days'
        GROUP BY DATE(created_at) ORDER BY day
    """)

    # Top 15 pacchetti cercati oggi
    top_today = await conn.fetch("""
        SELECT ecosystem, package_name, COUNT(*) as cnt
        FROM api_usage WHERE created_at > CURRENT_DATE
        GROUP BY ecosystem, package_name ORDER BY cnt DESC LIMIT 15
    """)

    # Top 15 pacchetti cercati settimana
    top_week = await conn.fetch("""
        SELECT ecosystem, package_name, COUNT(*) as cnt
        FROM api_usage WHERE created_at > NOW() - INTERVAL '7 days'
        GROUP BY ecosystem, package_name ORDER BY cnt DESC LIMIT 15
    """)

    # Per ecosistema
    by_eco = await conn.fetch("""
        SELECT ecosystem, COUNT(*) as cnt
        FROM api_usage WHERE created_at > CURRENT_DATE
        GROUP BY ecosystem ORDER BY cnt DESC
    """)

    # AI Agents (User-Agent analysis)
    agents = await conn.fetch("""
        SELECT
            CASE
                WHEN user_agent LIKE '%Claude%' THEN 'Claude'
                WHEN user_agent LIKE '%ChatGPT%' OR user_agent LIKE '%OpenAI%' THEN 'ChatGPT'
                WHEN user_agent LIKE '%Cursor%' THEN 'Cursor'
                WHEN user_agent LIKE '%Windsurf%' THEN 'Windsurf'
                WHEN user_agent LIKE '%DepScope-MCP%' THEN 'MCP Server'
                WHEN user_agent LIKE '%curl%' THEN 'curl'
                WHEN user_agent LIKE '%python%' OR user_agent LIKE '%Python%' THEN 'Python'
                WHEN user_agent LIKE '%node%' OR user_agent LIKE '%Node%' THEN 'Node.js'
                WHEN user_agent LIKE '%Mozilla%' THEN 'Browser'
                ELSE 'Other'
            END as agent,
            COUNT(*) as calls
        FROM api_usage WHERE created_at > NOW() - INTERVAL '7 days'
        GROUP BY agent ORDER BY calls DESC
    """)

    # Nuovi utenti oggi
    new_users = await conn.fetch("""
        SELECT email, created_at FROM users
        WHERE created_at > CURRENT_DATE ORDER BY created_at DESC
    """)

    # Top IP (possibili abusi)
    top_ips = await conn.fetch("""
        SELECT ip_address, COUNT(*) as cnt
        FROM api_usage WHERE created_at > CURRENT_DATE
        GROUP BY ip_address ORDER BY cnt DESC LIMIT 5
    """)

    # Unique IPs today
    unique_ips = await conn.fetchval("""
        SELECT COUNT(DISTINCT ip_address) FROM api_usage WHERE created_at > CURRENT_DATE
    """)

    await conn.close()

    return {
        "total_calls": total_calls,
        "total_packages": total_packages,
        "total_users": total_users,
        "today_calls": today_calls,
        "yesterday_calls": yesterday_calls,
        "week_calls": week_calls,
        "daily": daily,
        "top_today": top_today,
        "top_week": top_week,
        "by_eco": by_eco,
        "agents": agents,
        "new_users": new_users,
        "top_ips": top_ips,
        "unique_ips": unique_ips,
    }


def build_html(s):
    # Trend arrow
    if s["yesterday_calls"] > 0:
        change = ((s["today_calls"] - s["yesterday_calls"]) / s["yesterday_calls"]) * 100
        trend = f'{"+" if change > 0 else ""}{change:.0f}% vs ieri'
        trend_color = "#22c55e" if change >= 0 else "#ef4444"
    else:
        trend = "primo giorno con dati ieri"
        trend_color = "#94a3b8"

    # Daily chart (ASCII bars)
    daily_rows = ""
    max_calls = max((d["calls"] for d in s["daily"]), default=1)
    for d in s["daily"]:
        bar_len = int((d["calls"] / max_calls) * 30) if max_calls > 0 else 0
        bar = "█" * bar_len
        daily_rows += f'<tr><td style="padding:2px 8px;color:#94a3b8;font-size:12px;">{d["day"]}</td><td style="padding:2px 8px;color:#22d3ee;font-family:monospace;font-size:12px;">{bar}</td><td style="padding:2px 8px;color:#e2e8f0;font-size:12px;text-align:right;">{d["calls"]}</td></tr>'

    # Top packages today
    top_today_rows = ""
    for p in s["top_today"]:
        top_today_rows += f'<tr><td style="padding:2px 8px;color:#22d3ee;font-size:12px;">{p["ecosystem"]}</td><td style="padding:2px 8px;color:#e2e8f0;font-size:12px;">{p["package_name"]}</td><td style="padding:2px 8px;color:#94a3b8;font-size:12px;text-align:right;">{p["cnt"]}x</td></tr>'

    # Agents
    agents_rows = ""
    for a in s["agents"]:
        agents_rows += f'<tr><td style="padding:2px 8px;color:#e2e8f0;font-size:12px;">{a["agent"]}</td><td style="padding:2px 8px;color:#94a3b8;font-size:12px;text-align:right;">{a["calls"]}</td></tr>'

    # Eco breakdown
    eco_rows = ""
    for e in s["by_eco"]:
        eco_rows += f'{e["ecosystem"]}: {e["cnt"]}  '

    # New users
    new_users_html = ""
    if s["new_users"]:
        for u in s["new_users"]:
            new_users_html += f'<div style="color:#22c55e;font-size:13px;">+ {u["email"]}</div>'
    else:
        new_users_html = '<div style="color:#94a3b8;font-size:13px;">Nessun nuovo utente oggi</div>'

    # Top IPs
    ips_rows = ""
    for ip in s["top_ips"]:
        ips_rows += f'<tr><td style="padding:2px 8px;color:#94a3b8;font-size:12px;font-family:monospace;">{ip["ip_address"]}</td><td style="padding:2px 8px;color:#e2e8f0;font-size:12px;text-align:right;">{ip["cnt"]}</td></tr>'

    return f"""
    <div style="font-family:system-ui;max-width:700px;margin:0 auto;padding:20px;background:#0a0a0f;color:#e2e8f0;">
        <h1 style="background:linear-gradient(135deg,#22d3ee,#a78bfa,#f472b6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:24px;margin-bottom:5px;">DepScope Daily Report</h1>
        <p style="color:#94a3b8;font-size:13px;margin-top:0;">{datetime.now(timezone.utc).strftime('%A %d %B %Y')}</p>

        <!-- KPI -->
        <table style="width:100%;border-collapse:collapse;margin:20px 0;">
            <tr>
                <td style="background:#12121a;border:1px solid #1e1e2e;border-radius:8px;padding:15px;text-align:center;width:25%;">
                    <div style="font-size:28px;font-weight:bold;color:#22d3ee;">{s['today_calls']}</div>
                    <div style="font-size:11px;color:#94a3b8;">Oggi</div>
                    <div style="font-size:11px;color:{trend_color};">{trend}</div>
                </td>
                <td style="background:#12121a;border:1px solid #1e1e2e;border-radius:8px;padding:15px;text-align:center;width:25%;">
                    <div style="font-size:28px;font-weight:bold;color:#22c55e;">{s['week_calls']}</div>
                    <div style="font-size:11px;color:#94a3b8;">7 giorni</div>
                </td>
                <td style="background:#12121a;border:1px solid #1e1e2e;border-radius:8px;padding:15px;text-align:center;width:25%;">
                    <div style="font-size:28px;font-weight:bold;color:#eab308;">{s['total_calls']}</div>
                    <div style="font-size:11px;color:#94a3b8;">Totali</div>
                </td>
                <td style="background:#12121a;border:1px solid #1e1e2e;border-radius:8px;padding:15px;text-align:center;width:25%;">
                    <div style="font-size:28px;font-weight:bold;color:#f97316;">{s['unique_ips']}</div>
                    <div style="font-size:11px;color:#94a3b8;">IP unici oggi</div>
                </td>
            </tr>
        </table>

        <!-- Stats secondari -->
        <div style="background:#12121a;border:1px solid #1e1e2e;border-radius:8px;padding:12px 15px;margin:10px 0;font-size:13px;color:#94a3b8;">
            Utenti: <strong style="color:#e2e8f0;">{s['total_users']}</strong> | Pacchetti DB: <strong style="color:#e2e8f0;">{s['total_packages']}</strong> | Ecosistemi oggi: {eco_rows}
        </div>

        <!-- Chart giornaliero -->
        <div style="background:#12121a;border:1px solid #1e1e2e;border-radius:8px;padding:15px;margin:15px 0;">
            <h3 style="margin:0 0 10px 0;font-size:14px;">Chiamate API (7 giorni)</h3>
            <table style="width:100%;border-collapse:collapse;">{daily_rows}</table>
        </div>

        <!-- AI Agents -->
        <div style="background:#12121a;border:1px solid #1e1e2e;border-radius:8px;padding:15px;margin:15px 0;">
            <h3 style="margin:0 0 10px 0;font-size:14px;">AI Agents che ci usano</h3>
            <table style="width:100%;border-collapse:collapse;">{agents_rows}</table>
        </div>

        <!-- Top pacchetti -->
        <div style="background:#12121a;border:1px solid #1e1e2e;border-radius:8px;padding:15px;margin:15px 0;">
            <h3 style="margin:0 0 10px 0;font-size:14px;">Top pacchetti oggi</h3>
            <table style="width:100%;border-collapse:collapse;">{top_today_rows}</table>
        </div>

        <!-- Nuovi utenti -->
        <div style="background:#12121a;border:1px solid #1e1e2e;border-radius:8px;padding:15px;margin:15px 0;">
            <h3 style="margin:0 0 10px 0;font-size:14px;">Nuovi utenti</h3>
            {new_users_html}
        </div>

        <!-- Top IPs -->
        <div style="background:#12121a;border:1px solid #1e1e2e;border-radius:8px;padding:15px;margin:15px 0;">
            <h3 style="margin:0 0 10px 0;font-size:14px;">Top IP (monitoraggio abuse)</h3>
            <table style="width:100%;border-collapse:collapse;">{ips_rows}</table>
        </div>

        <!-- Footer -->
        <div style="text-align:center;padding:15px 0;border-top:1px solid #1e1e2e;margin-top:20px;">
            <a href="https://depscope.dev/admin" style="color:#22d3ee;text-decoration:none;font-size:13px;">Apri Dashboard Admin</a>
            <span style="color:#1e1e2e;"> | </span>
            <a href="https://depscope.dev/stats" style="color:#94a3b8;text-decoration:none;font-size:13px;">Stats pubbliche</a>
        </div>
    </div>
    """


def send_report(html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"DepScope Report — {datetime.now(timezone.utc).strftime('%d %b %Y')}"
    msg["From"] = FROM_EMAIL
    msg["To"] = ", ".join(RECIPIENTS)
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
        server.sendmail(FROM_EMAIL, RECIPIENTS, msg.as_string())
    print("Report sent!")


async def main():
    print(f"Generating daily report...")
    stats = await gather_stats()
    html = build_html(stats)
    send_report(html)
    print(f"Done. Today: {stats['today_calls']} calls, {stats['unique_ips']} unique IPs")


if __name__ == "__main__":
    asyncio.run(main())
