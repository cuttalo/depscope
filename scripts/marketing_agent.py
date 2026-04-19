#!/usr/bin/env python3
"""DepScope Marketing Agent — Full Agentic Marketing System.

Runs every 4 hours via cron:
    0 */4 * * * cd /home/deploy/depscope && .venv/bin/python scripts/marketing_agent.py >> /tmp/marketing_agent.log 2>&1

Phases:
1. Load rules from DB
2. Discover opportunities (Dev.to, Reddit, HN, Cursor Forum)
3. Monitor email inbox (IMAP)
4. Process approved opportunities (generate content via Claude CLI)
5. Execute confirmed actions (post comments, send emails)
6. Publish articles for content plan items
7. Collect and save daily metrics
"""

import asyncio
import json
import sys
import os
import subprocess
import imaplib
import email as email_lib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timezone
from urllib.request import urlopen, Request as URLRequest
from urllib.error import URLError
from urllib.parse import quote

import asyncpg

DB_URL = os.getenv("DATABASE_URL", "postgresql://depscope:${DB_PASSWORD}@localhost:5432/depscope")

# ── Discovery config ──
DEVTO_API = "https://dev.to/api"
DEVTO_TAGS = ["npm", "pypi", "security", "ai", "python", "javascript", "cargo", "dependencies", "opensource", "webdev"]
DEVTO_KEYWORDS = ["dependency", "dependencies", "package", "npm", "pypi", "cargo", "vulnerability", "supply chain", "mcp", "ai agent", "security audit"]

REDDIT_SUBS = ["programming", "webdev", "node", "python", "SideProject"]
REDDIT_KEYWORDS = ["package", "deprecated", "vulnerability", "npm", "pip", "dependency", "dependencies", "security", "supply chain"]

HN_QUERIES = ["npm+security", "dependency+vulnerability", "package+deprecated", "supply+chain+attack"]

# ── Email config ──
IMAP_HOST = "10.10.0.130"
IMAP_PORT = 993
SMTP_HOST = "10.10.0.130"
SMTP_PORT = 25
EMAIL_USER = "depscope@cuttalo.com"
EMAIL_PASS = os.getenv("EMAIL_PASSWORD", "")
EMAIL_FROM_NAME = "Vincenzo Rubino - DepScope"

# ── Dev.to API key ──
DEVTO_API_KEY = "VuqtfNaAJifTz4h2ckG3sCdG"


async def get_pool():
    return await asyncpg.create_pool(DB_URL, min_size=1, max_size=3)


async def load_rules(pool) -> list[dict]:
    """Load all active rules."""
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM agent_rules WHERE active = true ORDER BY priority")
    return [dict(r) for r in rows]


async def log_action(pool, action_type: str, platform: str, target_url: str = "", content: str = "", status: str = "executed", response: str = ""):
    """Log an action to the database."""
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO agent_actions (action_type, platform, target_url, content, status, response) VALUES ($1, $2, $3, $4, $5, $6)",
            action_type, platform, target_url, content, status, response
        )


def fetch_json(url: str, headers: dict | None = None) -> dict | list | None:
    """Simple HTTP GET returning JSON."""
    try:
        req = URLRequest(url, headers=headers or {})
        req.add_header("User-Agent", "DepScope-Agent/1.0")
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except (URLError, json.JSONDecodeError, Exception) as e:
        print(f"  [WARN] fetch {url[:80]}: {e}")
        return None


def score_text(text: str, keywords: list[str]) -> int:
    """Score relevance of text against keywords."""
    text_lower = text.lower()
    score = 0
    for kw in keywords:
        if kw in text_lower:
            score += 2
    return score


# ═══════════════════════════════════════════════════
# PHASE 1: DISCOVERY — Multi-Platform
# ═══════════════════════════════════════════════════

async def get_existing_urls(pool) -> set:
    """Get all existing opportunity URLs to avoid duplicates."""
    async with pool.acquire() as conn:
        return set(r["url"] for r in await conn.fetch("SELECT url FROM agent_opportunities"))


async def save_opportunity(pool, platform: str, url: str, title: str, score: int, action: str, extra: str, existing: set):
    """Save a discovered opportunity if not duplicate and score >= threshold."""
    if url in existing or score < 3:
        return False
    score = min(score, 10)
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO agent_opportunities (platform, url, title, relevance_score, suggested_action, suggested_content, status) VALUES ($1, $2, $3, $4, $5, $6, $7)",
            platform, url, title[:200], score, action, extra, "found"
        )
    existing.add(url)
    return True


async def discover_devto(pool, existing: set) -> int:
    """Find relevant Dev.to articles."""
    print("[DISCOVER] Scanning Dev.to...")
    found = 0
    for tag in DEVTO_TAGS[:6]:
        url = f"{DEVTO_API}/articles?tag={tag}&per_page=10&top=7"
        articles = fetch_json(url)
        if not articles:
            continue
        for art in articles:
            art_url = art.get("url", "")
            if not art_url:
                continue
            title = art.get("title", "")
            desc = art.get("description", "")
            text = f"{title} {desc}"
            score = score_text(text, DEVTO_KEYWORDS)
            reactions = art.get("positive_reactions_count", 0)
            comments = art.get("comments_count", 0)
            if reactions > 20: score += 1
            if reactions > 50: score += 1
            if comments < 10: score += 1

            text_lower = text.lower()
            if any(kw in text_lower for kw in ["vulnerability", "security", "supply chain"]):
                action = "Comment with security analysis expertise"
            elif any(kw in text_lower for kw in ["npm", "pypi", "cargo", "dependency", "dependencies"]):
                action = "Comment with package management insight"
            elif any(kw in text_lower for kw in ["mcp", "ai agent"]):
                action = "Comment about AI tooling for developers"
            else:
                action = "Comment with relevant technical insight"

            extra = f"By {art.get('user', {}).get('username', '?')} | {reactions}r, {comments}c | Tags: {', '.join(art.get('tag_list', []))}"
            if await save_opportunity(pool, "devto", art_url, title, score, action, extra, existing):
                found += 1
                print(f"  [+] Score {min(score,10)}: {title[:60]}")
    return found


async def discover_reddit(pool, existing: set) -> int:
    """Find relevant Reddit posts."""
    print("[DISCOVER] Scanning Reddit...")
    found = 0
    for sub in REDDIT_SUBS:
        url = f"https://old.reddit.com/r/{sub}/new.json?limit=15"
        data = fetch_json(url, headers={"User-Agent": "DepScope-Agent/1.0 (depscope.dev)"})
        if not data or "data" not in data:
            continue
        for post in data["data"].get("children", []):
            pd = post.get("data", {})
            post_url = f"https://reddit.com{pd.get('permalink', '')}"
            title = pd.get("title", "")
            selftext = pd.get("selftext", "")[:500]
            text = f"{title} {selftext}"
            score = score_text(text, REDDIT_KEYWORDS)
            ups = pd.get("ups", 0)
            num_comments = pd.get("num_comments", 0)
            if ups > 10: score += 1
            if ups > 50: score += 1
            if num_comments < 20: score += 1

            action = "Comment with relevant developer insight (manual post required unless r/SideProject)"
            extra = f"r/{sub} | {ups} upvotes, {num_comments} comments"
            if await save_opportunity(pool, "reddit", post_url, title, score, action, extra, existing):
                found += 1
                print(f"  [+] Score {min(score,10)}: r/{sub} — {title[:50]}")
    return found


async def discover_hn(pool, existing: set) -> int:
    """Find relevant Hacker News posts."""
    print("[DISCOVER] Scanning Hacker News...")
    found = 0
    for query in HN_QUERIES:
        url = f"https://hn.algolia.com/api/v1/search_by_date?query={query}&tags=story&hitsPerPage=10"
        data = fetch_json(url)
        if not data or "hits" not in data:
            continue
        for hit in data["hits"]:
            hn_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
            title = hit.get("title", "")
            score_val = score_text(title, DEVTO_KEYWORDS)
            points = hit.get("points", 0) or 0
            num_comments = hit.get("num_comments", 0) or 0
            if points > 10: score_val += 1
            if points > 50: score_val += 2
            if num_comments < 20: score_val += 1

            action = "Comment on HN (manual post — admin from browser)"
            extra = f"HN | {points} points, {num_comments} comments"
            if await save_opportunity(pool, "hn", hn_url, title, score_val, action, extra, existing):
                found += 1
                print(f"  [+] Score {min(score_val,10)}: HN — {title[:50]}")
    return found


async def discover_cursor_forum(pool, existing: set) -> int:
    """Find relevant Cursor Forum topics."""
    print("[DISCOVER] Scanning Cursor Forum...")
    found = 0
    data = fetch_json("https://forum.cursor.com/latest.json")
    if not data or "topic_list" not in data:
        return 0
    for topic in data["topic_list"].get("topics", [])[:15]:
        topic_url = f"https://forum.cursor.com/t/{topic.get('slug', '')}/{topic.get('id', '')}"
        title = topic.get("title", "")
        score_val = score_text(title, ["mcp", "package", "dependency", "npm", "pip", "security", "api", "tool", "agent"])
        views = topic.get("views", 0)
        reply_count = topic.get("reply_count", 0)
        if views > 100: score_val += 1
        if views > 500: score_val += 1
        if reply_count < 10: score_val += 1

        action = "Comment on Cursor Forum (manual post — admin from browser)"
        extra = f"Cursor Forum | {views} views, {reply_count} replies"
        if await save_opportunity(pool, "cursor", topic_url, title, score_val, action, extra, existing):
            found += 1
            print(f"  [+] Score {min(score_val,10)}: Cursor — {title[:50]}")
    return found


# ═══════════════════════════════════════════════════
# PHASE 2: EMAIL MONITORING
# ═══════════════════════════════════════════════════

async def check_email_inbox(pool, existing: set) -> int:
    """Check IMAP inbox for new non-bounce emails, save as opportunities."""
    print("[EMAIL] Checking inbox...")
    found = 0
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("INBOX")
        # Search for unseen messages
        status, data = mail.search(None, "UNSEEN")
        if status != "OK" or not data[0]:
            print("  [EMAIL] No new messages")
            mail.logout()
            return 0

        msg_ids = data[0].split()
        for msg_id in msg_ids[:10]:  # Max 10 per run
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
            title = f"Email da {sender}: {subject}"
            action = "Reply to email with Claude-generated response"
            extra = f"From: {sender}\nDate: {msg_date}\n\n{body[:500]}"

            if await save_opportunity(pool, "email", email_url, title, 7, action, extra, existing):
                found += 1
                print(f"  [+] Email from {sender[:40]}: {subject[:50]}")

        mail.logout()
    except Exception as e:
        print(f"  [WARN] Email check failed: {e}")
    return found


# ═══════════════════════════════════════════════════
# PHASE 3: AUTO-SKIP LOW RELEVANCE
# ═══════════════════════════════════════════════════

async def auto_skip_low_relevance(pool) -> int:
    """Auto-skip opportunities with relevance < 5."""
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE agent_opportunities SET status = 'skipped' WHERE status = 'found' AND relevance_score < 5"
        )
        count = int(result.split()[-1]) if result else 0
    if count:
        print(f"[AUTO-SKIP] Skipped {count} low-relevance opportunities (score < 5)")
    return count


# ═══════════════════════════════════════════════════
# PHASE 4: CONTENT GENERATION (Claude CLI)
# ═══════════════════════════════════════════════════

async def generate_content_for_approved(pool) -> int:
    """Generate content via Claude CLI for approved opportunities."""
    print("[CONTENT] Processing approved opportunities...")
    async with pool.acquire() as conn:
        approved = await conn.fetch(
            "SELECT * FROM agent_opportunities WHERE status = 'approved' ORDER BY relevance_score DESC LIMIT 3"
        )
    if not approved:
        print("  No approved opportunities to process")
        return 0

    processed = 0
    for opp in approved:
        opp = dict(opp)
        platform = opp["platform"]
        title = opp["title"]
        url = opp["url"]
        extra = opp.get("suggested_content", "")

        print(f"  Generating for: {title[:50]}...")

        if platform == "email":
            prompt = f"""You are Vincenzo Rubino, founder of DepScope (depscope.dev), a free package health API for AI agents.
Write a reply to this email. Be brief (3-5 lines), professional, friendly.
Sign as "Vincenzo".

EMAIL CONTEXT:
{extra}

Write ONLY the email reply body, nothing else."""
        else:
            prompt = f"""You are a knowledgeable developer commenting on a technical article/post.

OPPORTUNITY:
Platform: {platform}
Title: {title}
URL: {url}
Context: {extra}

RULES:
- NEVER include links to any product
- NEVER mention DepScope by name
- Be genuinely helpful and add value
- Use real data: 14,700+ packages analyzed across 17 ecosystems, 8,300+ score below 60/100, 402 vulnerabilities tracked, 12 MCP tools
- Specific data points: ms gets 414M downloads/week with no updates, request deprecated since 2020 still 16M/week
- Keep it short (max 4 lines)
- Sound like a knowledgeable developer, not a marketer
- Be specific to the article topic

Write ONLY the comment text, nothing else."""

        try:
            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True, text=True, timeout=60,
                cwd="/home/deploy/depscope"
            )
            if result.returncode == 0 and result.stdout.strip():
                content = result.stdout.strip()
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE agent_opportunities SET suggested_content = $1, status = 'content_ready' WHERE id = $2",
                        content, opp["id"]
                    )
                await log_action(pool, "generate_content", platform, url, content[:200], "executed")
                processed += 1
                print(f"    Generated ({len(content)} chars)")
            else:
                err = result.stderr[:200] if result.stderr else "No output"
                print(f"    [WARN] Claude CLI failed: {err}")
                await log_action(pool, "generate_content", platform, url, f"Error: {err}", "failed")
        except subprocess.TimeoutExpired:
            print(f"    [WARN] Claude CLI timeout")
            await log_action(pool, "generate_content", platform, url, "Timeout", "failed")
        except FileNotFoundError:
            print(f"    [WARN] Claude CLI not found, skipping content generation")
            break
        except Exception as e:
            print(f"    [WARN] Error: {e}")
            await log_action(pool, "generate_content", platform, url, str(e)[:200], "failed")

    return processed


# ═══════════════════════════════════════════════════
# PHASE 5: EXECUTION (Posting)
# ═══════════════════════════════════════════════════

async def execute_confirmed(pool) -> int:
    """Execute confirmed actions (status='execute')."""
    print("[EXECUTE] Processing confirmed actions...")
    async with pool.acquire() as conn:
        to_execute = await conn.fetch(
            "SELECT * FROM agent_opportunities WHERE status = 'execute' ORDER BY created_at LIMIT 5"
        )
    if not to_execute:
        print("  No actions to execute")
        return 0

    executed = 0
    for opp in to_execute:
        opp = dict(opp)
        platform = opp["platform"]
        content = opp.get("suggested_content", "")
        url = opp["url"]

        if not content:
            print(f"  [SKIP] No content for {opp['title'][:40]}")
            continue

        if platform == "devto":
            # Post comment via Dev.to API
            # Extract article ID from URL
            success = await post_devto_comment(pool, opp, content)
            if success:
                executed += 1

        elif platform == "email":
            # Send email reply
            success = await send_email_reply(pool, opp, content)
            if success:
                executed += 1

        else:
            # Reddit, HN, Cursor — manual post
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE agent_opportunities SET status = 'manual_post' WHERE id = $1", opp["id"]
                )
            await log_action(
                pool, "manual_post", platform, url,
                f"MANUAL POST REQUIRED:\n\nURL: {url}\n\nContent:\n{content}",
                "pending"
            )
            print(f"  [MANUAL] {platform}: {opp['title'][:40]} — admin must post from browser")
            executed += 1

    return executed


async def post_devto_comment(pool, opp: dict, content: str) -> bool:
    """Post a comment on Dev.to article."""
    url = opp["url"]
    # Get article ID from Dev.to API
    try:
        # Fetch article by URL path
        path = url.replace("https://dev.to/", "")
        article_data = fetch_json(f"{DEVTO_API}/articles/{path}")
        if not article_data or "id" not in article_data:
            print(f"  [WARN] Could not get Dev.to article ID for {url[:60]}")
            return False

        article_id = article_data["id"]

        # POST comment
        import urllib.request
        comment_data = json.dumps({"comment": {"body_markdown": content}}).encode()
        req = urllib.request.Request(
            f"{DEVTO_API}/comments",
            data=comment_data,
            headers={
                "api-key": DEVTO_API_KEY,
                "Content-Type": "application/json",
                "User-Agent": "DepScope-Agent/1.0",
            },
            method="POST"
        )
        # Add article_id as a_id parameter
        comment_payload = json.dumps({
            "comment": {
                "body_markdown": content,
                "commentable_id": article_id,
                "commentable_type": "Article"
            }
        }).encode()
        req = urllib.request.Request(
            f"{DEVTO_API}/comments",
            data=comment_payload,
            headers={
                "api-key": DEVTO_API_KEY,
                "Content-Type": "application/json",
                "User-Agent": "DepScope-Agent/1.0",
            },
            method="POST"
        )
        with urlopen(req, timeout=15) as resp:
            resp_data = json.loads(resp.read().decode())

        async with pool.acquire() as conn:
            await conn.execute("UPDATE agent_opportunities SET status = 'done' WHERE id = $1", opp["id"])
        await log_action(pool, "post_comment", "devto", url, content[:200], "executed", json.dumps(resp_data)[:500])
        print(f"  [OK] Posted comment on Dev.to: {opp['title'][:40]}")
        return True

    except Exception as e:
        print(f"  [ERR] Dev.to comment failed: {e}")
        await log_action(pool, "post_comment", "devto", url, content[:200], "failed", str(e)[:200])
        return False


async def send_email_reply(pool, opp: dict, content: str) -> bool:
    """Send email reply via SMTP."""
    try:
        # Parse sender from extra info
        extra = opp.get("suggested_content", "") or ""
        # Original sender is in the URL: email://sender/id
        sender_email = opp["url"].replace("email://", "").split("/")[0]
        subject_match = opp["title"].replace("Email da ", "").split(": ", 1)
        subject = f"Re: {subject_match[1]}" if len(subject_match) > 1 else "Re: your message"

        msg = MIMEMultipart()
        msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_USER}>"
        msg["To"] = sender_email
        msg["Subject"] = subject
        msg.attach(MIMEText(content, "plain"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.sendmail(EMAIL_USER, [sender_email], msg.as_string())

        async with pool.acquire() as conn:
            await conn.execute("UPDATE agent_opportunities SET status = 'done' WHERE id = $1", opp["id"])
        await log_action(pool, "send_email", "email", sender_email, content[:200], "executed")
        print(f"  [OK] Sent email reply to {sender_email}")
        return True

    except Exception as e:
        print(f"  [ERR] Email send failed: {e}")
        await log_action(pool, "send_email", "email", opp["url"], content[:200], "failed", str(e)[:200])
        return False


# ═══════════════════════════════════════════════════
# PHASE 6: ARTICLE PUBLISHING
# ═══════════════════════════════════════════════════

async def publish_articles(pool) -> int:
    """Generate and publish articles for content plan items."""
    print("[ARTICLES] Checking content plan...")
    async with pool.acquire() as conn:
        content_items = await conn.fetch(
            "SELECT * FROM agent_plan WHERE category = 'content' AND status = 'in_progress' LIMIT 2"
        )
    if not content_items:
        print("  No content items in progress")
        return 0

    published = 0
    for item in content_items:
        item = dict(item)
        print(f"  Generating article: {item['action'][:50]}...")

        prompt = f"""You are a technical writer for DepScope (depscope.dev), a free package health API for AI agents.

Write a technical article about:
{item['action']}

RULES:
- At least 800 words
- Include real data: 14,700+ packages indexed across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, RubyGems + 10 more), 8,300+ score below 60/100, 402 vulnerabilities tracked, 12 MCP tools, 3 verticals (package health + error->fix + compat matrix)
- Use specific examples: ms (414M/week, no updates), request (deprecated 2020, 16M/week)
- Technical, informative, developer audience
- Include code examples where relevant
- Mention depscope.dev naturally (max 2 times)
- Use markdown formatting
- Include relevant tags suggestion at the end (comma-separated)

Write the article in markdown. End with a line: TAGS: tag1, tag2, tag3"""

        try:
            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True, text=True, timeout=120,
                cwd="/home/deploy/depscope"
            )
            if result.returncode != 0 or not result.stdout.strip():
                print(f"    [WARN] Claude CLI failed for article")
                continue

            article_text = result.stdout.strip()
            # Extract tags
            tags = ["depscope", "security", "npm"]
            lines = article_text.split("\n")
            for line in lines[-5:]:
                if line.strip().startswith("TAGS:"):
                    tags = [t.strip().lower().replace(" ", "") for t in line.replace("TAGS:", "").split(",")][:4]
                    article_text = "\n".join(lines[:lines.index(line)])
                    break

            # Extract title (first # heading)
            title = item["action"][:100]
            for line in lines[:5]:
                if line.startswith("# "):
                    title = line[2:].strip()
                    break

            # Publish to Dev.to
            import urllib.request
            article_payload = json.dumps({
                "article": {
                    "title": title,
                    "body_markdown": article_text,
                    "published": True,
                    "tags": tags,
                }
            }).encode()
            req = urllib.request.Request(
                f"{DEVTO_API}/articles",
                data=article_payload,
                headers={
                    "api-key": DEVTO_API_KEY,
                    "Content-Type": "application/json",
                },
                method="POST"
            )
            with urlopen(req, timeout=30) as resp:
                resp_data = json.loads(resp.read().decode())

            article_url = resp_data.get("url", "")
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE agent_plan SET status = 'completed', result = $1, completed_at = NOW() WHERE id = $2",
                    f"Published: {article_url}", item["id"]
                )
            await log_action(pool, "publish_article", "devto", article_url, title, "executed")
            print(f"    [OK] Published: {article_url}")
            published += 1

        except FileNotFoundError:
            print(f"    [WARN] Claude CLI not found")
            break
        except Exception as e:
            print(f"    [ERR] Article publish failed: {e}")
            await log_action(pool, "publish_article", "devto", "", item["action"][:100], "failed", str(e)[:200])

    return published


# ═══════════════════════════════════════════════════
# PHASE 7: METRICS COLLECTION
# ═══════════════════════════════════════════════════

async def collect_metrics(pool):
    """Collect and save daily metrics."""
    print("[METRICS] Collecting daily metrics...")
    today = date.today()

    async with pool.acquire() as conn:
        pv = await conn.fetchval(
            "SELECT COUNT(*) FROM page_views WHERE DATE(created_at) = $1 AND ip_address NOT IN ('127.0.0.1','::1','10.10.0.140','10.10.0.1','91.134.4.25')",
            today
        ) or 0

        uv = await conn.fetchval(
            "SELECT COUNT(DISTINCT ip_address) FROM page_views WHERE DATE(created_at) = $1 AND ip_address NOT IN ('127.0.0.1','::1','10.10.0.140','10.10.0.1','91.134.4.25')",
            today
        ) or 0

        api = await conn.fetchval(
            "SELECT COUNT(*) FROM api_usage WHERE DATE(created_at) = $1 AND ip_address NOT IN ('127.0.0.1','::1','10.10.0.140','10.10.0.1','91.134.4.25')",
            today
        ) or 0

        countries = await conn.fetchval(
            "SELECT COUNT(DISTINCT country) FROM page_views WHERE DATE(created_at) = $1 AND country IS NOT NULL AND ip_address NOT IN ('127.0.0.1','::1','10.10.0.140','10.10.0.1','91.134.4.25')",
            today
        ) or 0

        pkgs = await conn.fetchval("SELECT COUNT(*) FROM packages") or 0

        # Dev.to stats
        devto_views = 0
        devto_reactions = 0
        cred = await conn.fetchrow("SELECT api_key FROM agent_credentials WHERE platform = 'devto' AND active = true")
        if cred:
            articles = fetch_json(f"{DEVTO_API}/articles/me/published?per_page=100", headers={"api-key": cred["api_key"]})
            if articles:
                for art in articles:
                    devto_views += art.get("page_views_count", 0)
                    devto_reactions += art.get("positive_reactions_count", 0)

        # Email responses count
        email_responses = await conn.fetchval(
            "SELECT COUNT(*) FROM agent_actions WHERE action_type = 'send_email' AND status = 'executed' AND DATE(created_at) = $1",
            today
        ) or 0

        await conn.execute("""
            INSERT INTO agent_metrics (date, page_views, unique_visitors, api_calls, countries, db_packages, devto_views, devto_reactions, email_responses)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (date) DO UPDATE SET
                page_views = $2, unique_visitors = $3, api_calls = $4, countries = $5,
                db_packages = $6, devto_views = $7, devto_reactions = $8, email_responses = $9
        """, today, pv, uv, api, countries, pkgs, devto_views, devto_reactions, email_responses)

    await log_action(pool, "metrics", "internal", content=f"Metrics {today}: {pv}v, {uv}u, {api}api, {countries}c, {pkgs}pkg, devto:{devto_views}v/{devto_reactions}r", status="executed")
    print(f"[METRICS] {pv}v, {uv}u, {api}api, {countries}c, {pkgs}pkg, Dev.to: {devto_views}v/{devto_reactions}r")


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════

async def main():
    print(f"\n{'='*60}")
    print(f"DepScope Marketing Agent — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")

    pool = await get_pool()

    try:
        # 1. Load rules
        rules = await load_rules(pool)
        print(f"[RULES] Loaded {len(rules)} active rules")

        # 2. Discovery — multi-platform
        existing = await get_existing_urls(pool)
        devto_found = await discover_devto(pool, existing)
        reddit_found = await discover_reddit(pool, existing)
        hn_found = await discover_hn(pool, existing)
        cursor_found = await discover_cursor_forum(pool, existing)
        total_found = devto_found + reddit_found + hn_found + cursor_found
        await log_action(pool, "discovery", "all", content=f"Found {total_found}: devto={devto_found}, reddit={reddit_found}, hn={hn_found}, cursor={cursor_found}", status="executed")
        print(f"[DISCOVER] Total found: {total_found}")

        # 3. Email monitoring
        email_found = await check_email_inbox(pool, existing)
        if email_found:
            print(f"[EMAIL] Found {email_found} new emails")

        # 4. Auto-skip low relevance
        await auto_skip_low_relevance(pool)

        # 5. Generate content for approved opportunities
        generated = await generate_content_for_approved(pool)
        if generated:
            print(f"[CONTENT] Generated content for {generated} opportunities")

        # 6. Execute confirmed actions
        executed = await execute_confirmed(pool)
        if executed:
            print(f"[EXECUTE] Executed {executed} actions")

        # 7. Publish articles
        published = await publish_articles(pool)
        if published:
            print(f"[ARTICLES] Published {published} articles")

        # 8. Collect metrics
        await collect_metrics(pool)

        # 9. Report planned actions
        async with pool.acquire() as conn:
            planned = await conn.fetch("SELECT * FROM agent_plan WHERE status IN ('planned', 'in_progress') ORDER BY priority LIMIT 5")
            pending_opps = await conn.fetchval("SELECT COUNT(*) FROM agent_opportunities WHERE status IN ('found', 'approved', 'content_ready', 'execute')")
        if planned:
            print(f"\n[PLAN] Top {len(planned)} planned actions:")
            for p in planned:
                print(f"  - [{p['priority']}] [{p['status']}] {p['action'][:80]}")
        print(f"[QUEUE] {pending_opps} opportunities in pipeline")

        print(f"\n[DONE] Agent cycle complete at {datetime.now(timezone.utc).strftime('%H:%M UTC')}")

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
