"""Real-time agent runner — trova opportunita e le pusha come notifiche."""
import asyncio
import aiohttp
import imaplib
import email
import sys
import os

sys.path.insert(0, "/home/deploy/depscope")

from scripts.agents.common import (
    DEVTO_TAGS, DEVTO_KEYWORDS, HN_QUERIES,
    IMAP_HOST, IMAP_PORT, EMAIL_USER, EMAIL_PASS,
    score_text,
)

NOTIFY_URL = "http://localhost:8000/api/admin/agent/notify"
ADMIN_KEY = os.getenv("DS_ADMIN_KEY", "")
SCAN_INTERVAL = 300  # 5 minutes


async def notify(data: dict):
    """Push notifica al frontend via API interna."""
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                NOTIFY_URL,
                json=data,
                headers={"X-API-Key": ADMIN_KEY},
                timeout=aiohttp.ClientTimeout(total=5),
            )
    except Exception as e:
        print(f"[notify] error: {e}")


async def check_agent_active() -> bool:
    """Controlla se l'agente e' ancora attivo."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:8000/api/admin/agent/state",
                headers={"X-API-Key": ADMIN_KEY},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("active", False)
    except Exception:
        pass
    return False


async def scan_devto():
    """Scansiona Dev.to per articoli freschi rilevanti."""
    async with aiohttp.ClientSession() as session:
        for tag in DEVTO_TAGS[:6]:
            try:
                async with session.get(
                    f"https://dev.to/api/articles?tag={tag}&top=1&per_page=3",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        articles = await resp.json()
                        for a in articles:
                            title = a.get("title", "")
                            score = score_text(title, DEVTO_KEYWORDS)
                            if score >= 4:
                                await notify({
                                    "type": "opportunity",
                                    "platform": "devto",
                                    "title": title,
                                    "url": a.get("url", ""),
                                    "relevance": min(score, 10),
                                    "author": a.get("user", {}).get("username", ""),
                                    "reactions": a.get("public_reactions_count", 0),
                                    "suggested_action": "comment",
                                    "article_id": a.get("id"),
                                })
            except Exception as e:
                print(f"[devto:{tag}] error: {e}")
            await asyncio.sleep(1)


async def scan_hn():
    """Scansiona HN per discussioni rilevanti."""
    async with aiohttp.ClientSession() as session:
        for query in HN_QUERIES[:3]:
            try:
                async with session.get(
                    f"https://hn.algolia.com/api/v1/search_by_date?query={query}&tags=story&hitsPerPage=3",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for hit in data.get("hits", []):
                            title = hit.get("title", "")
                            if not title:
                                continue
                            await notify({
                                "type": "opportunity",
                                "platform": "hackernews",
                                "title": title,
                                "url": f"https://news.ycombinator.com/item?id={hit['objectID']}",
                                "relevance": 6,
                                "author": hit.get("author", ""),
                                "reactions": hit.get("points", 0),
                                "suggested_action": "manual_post",
                            })
            except Exception as e:
                print(f"[hn:{query}] error: {e}")
            await asyncio.sleep(1)


async def check_email():
    """Controlla inbox per nuove email."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("INBOX")
        _, msgs = mail.search(None, "UNSEEN")
        ids = msgs[0].split() if msgs[0] else []
        for msg_id in ids[:5]:
            _, data = mail.fetch(msg_id, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            subj = str(msg.get("Subject", ""))
            fr = str(msg.get("From", ""))
            if "Undelivered" not in subj and "Failure" not in subj:
                await notify({
                    "type": "email",
                    "platform": "email",
                    "title": f"From: {fr[:40]} — {subj[:50]}",
                    "url": fr,
                    "relevance": 8,
                    "suggested_action": "reply",
                })
        mail.logout()
    except Exception as e:
        print(f"[email] error: {e}")


async def main():
    """Loop principale — gira finche' l'agente e' attivo."""
    await notify({"type": "status", "message": "Agent started — scanning..."})

    while True:
        try:
            # Controlla se ancora attivo
            if not await check_agent_active():
                await notify({"type": "status", "message": "Agent stopped."})
                break

            await notify({"type": "status", "message": "Scanning Dev.to..."})
            await scan_devto()

            await notify({"type": "status", "message": "Scanning HN..."})
            await scan_hn()

            await notify({"type": "status", "message": "Checking email..."})
            await check_email()

            await notify({"type": "status", "message": f"Scan complete. Next in {SCAN_INTERVAL // 60}m..."})

            # Aspetta, controllando ogni 30s se ancora attivo
            for _ in range(SCAN_INTERVAL // 30):
                await asyncio.sleep(30)
                if not await check_agent_active():
                    await notify({"type": "status", "message": "Agent stopped."})
                    return

        except Exception as e:
            await notify({"type": "error", "message": str(e)})
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
