#!/usr/bin/env python3
"""WRITER Agent — Content Generation via Claude CLI.

Takes approved opportunities, generates platform-specific content.
Respects rules: no links, no DepScope mention, max length.
Uses config from agent_config DB table for model and prompt selection.
"""

import asyncio
import subprocess
from datetime import datetime, timezone

from .common import get_pool, log_action, get_config


async def run(pool) -> dict:
    """Generate content for approved opportunities via Claude CLI."""
    print("[WRITER] Processing approved opportunities...")

    async with pool.acquire() as conn:
        approved = await conn.fetch(
            "SELECT * FROM agent_opportunities WHERE status = 'approved' ORDER BY relevance_score DESC LIMIT 3"
        )

    if not approved:
        print("  No approved opportunities to process")
        return {"generated": 0}

    generated = 0
    for opp in approved:
        opp = dict(opp)
        platform = opp["platform"]
        title = opp["title"]
        url = opp["url"]
        extra = opp.get("suggested_content", "")

        print(f"  Generating for: {title[:50]}...")

        # Read model and prompt template from DB config
        if platform == "email":
            model = await get_config("claude_model_emails", "sonnet")
            prompt_template = await get_config(
                "prompt_email_reply",
                "You are Vincenzo Rubino replying to an email about DepScope. Be brief (3-5 lines), professional but warm. Sign as Vincenzo."
            )
            prompt = f"{prompt_template}\n\nEMAIL CONTEXT:\n{extra}\n\nWrite ONLY the email reply body, nothing else."
        elif platform == "devto":
            model = await get_config("claude_model_comments", "haiku")
            prompt_template = await get_config(
                "prompt_comment_devto",
                "You are a knowledgeable developer commenting on a Dev.to article. Be genuine, add value with real data. NEVER include links. NEVER mention DepScope by name. Keep it under 4 lines."
            )
            prompt = f"{prompt_template}\n\nARTICLE:\nTitle: {title}\nURL: {url}\nContext: {extra}\n\nWrite ONLY the comment text, nothing else."
        elif platform == "reddit":
            model = await get_config("claude_model_comments", "haiku")
            prompt_template = await get_config(
                "prompt_comment_reddit",
                "You are a developer responding to a Reddit discussion. Be direct, no fluff. Share specific data points. NEVER include links. NEVER self-promote. Max 3-4 sentences."
            )
            prompt = f"{prompt_template}\n\nPOST:\nTitle: {title}\nURL: {url}\nContext: {extra}\n\nWrite ONLY the comment text, nothing else."
        else:
            model = await get_config("claude_model_comments", "haiku")
            prompt_template = await get_config(
                "prompt_comment_devto",
                "You are a knowledgeable developer commenting on a technical post. Be genuine, add value. NEVER include links. Keep it short."
            )
            prompt = f"{prompt_template}\n\nOPPORTUNITY:\nPlatform: {platform}\nTitle: {title}\nURL: {url}\nContext: {extra}\n\nWrite ONLY the comment text, nothing else."

        try:
            result = subprocess.run(
                ["claude", "-p", "--model", model, prompt],
                capture_output=True, text=True, timeout=60,
                cwd="/home/deploy/depscope"
            )
            if result.returncode == 0 and result.stdout.strip():
                content = result.stdout.strip()
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE agent_opportunities SET suggested_content = $1, status = 'content_ready', generated_at = NOW() WHERE id = $2",
                        content, opp["id"]
                    )
                await log_action(pool, "generate_content", platform, url, content[:200], "executed")
                generated += 1
                print(f"    Generated ({len(content)} chars) [model={model}]")
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

    print(f"[WRITER] Generated content for {generated} opportunities")
    return {"generated": generated}


if __name__ == "__main__":
    async def _main():
        pool = await get_pool()
        try:
            await run(pool)
        finally:
            await pool.close()
    asyncio.run(_main())
