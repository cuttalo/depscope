#!/usr/bin/env python3
"""DepScope Marketing Agent — Orchestrator.

Coordinates all sub-agents in the correct order:
1. SCOUT -> discover opportunities
2. ANALYST -> collect metrics
3. WRITER -> generate content for approved items
4. PUBLISHER -> post/publish confirmed items
5. MAILER -> check inbox + send approved emails

Reads schedule config from agent_config DB table.

Runs every 4 hours via cron:
    0 */4 * * * cd /home/deploy/depscope && .venv/bin/python -m scripts.agents.orchestrator >> /tmp/marketing_agent.log 2>&1
"""

import asyncio
import sys
import os
import traceback
from datetime import datetime, timezone

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.agents.common import get_pool, log_action, load_rules, get_config, get_config_int
from scripts.agents import scout, writer, mailer, publisher, analyst


async def main():
    start = datetime.now(timezone.utc)
    print(f"\n{'='*60}")
    print(f"DepScope Marketing Agent (Multi-Agent) — {start.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")

    pool = await get_pool()

    try:
        # Check active hours from config
        active_start = await get_config_int("active_hours_start", 7)
        active_end = await get_config_int("active_hours_end", 23)
        current_hour = datetime.now(timezone.utc).hour
        if current_hour < active_start or current_hour > active_end:
            print(f"[ORCHESTRATOR] Outside active hours ({active_start}-{active_end} UTC, now {current_hour} UTC), skipping")
            await log_action(pool, "orchestrator", "internal", content=f"Skipped: outside active hours ({current_hour} UTC)", status="skipped")
            return

        # Check active days from config
        active_days_str = await get_config("active_days", "1,2,3,4,5")
        active_days = [int(d.strip()) for d in active_days_str.split(",") if d.strip().isdigit()]
        current_day = datetime.now(timezone.utc).isoweekday()  # 1=Mon, 7=Sun
        if active_days and current_day not in active_days:
            print(f"[ORCHESTRATOR] Day {current_day} not in active days {active_days}, skipping")
            await log_action(pool, "orchestrator", "internal", content=f"Skipped: day {current_day} not active", status="skipped")
            return

        results = {}

        # 0. Load rules
        rules = await load_rules(pool)
        print(f"[ORCHESTRATOR] Loaded {len(rules)} active rules")

        # 1. SCOUT — discover opportunities
        print(f"\n--- PHASE 1: SCOUT ---")
        try:
            results["scout"] = await scout.run(pool)
        except Exception as e:
            print(f"[ORCHESTRATOR] Scout failed: {e}")
            traceback.print_exc()
            results["scout"] = {"error": str(e)}

        # 2. ANALYST — collect metrics
        print(f"\n--- PHASE 2: ANALYST ---")
        try:
            results["analyst"] = await analyst.run(pool)
        except Exception as e:
            print(f"[ORCHESTRATOR] Analyst failed: {e}")
            traceback.print_exc()
            results["analyst"] = {"error": str(e)}

        # 3. WRITER — generate content for approved items
        print(f"\n--- PHASE 3: WRITER ---")
        try:
            results["writer"] = await writer.run(pool)
        except Exception as e:
            print(f"[ORCHESTRATOR] Writer failed: {e}")
            traceback.print_exc()
            results["writer"] = {"error": str(e)}

        # 4. PUBLISHER — post/execute confirmed items
        print(f"\n--- PHASE 4: PUBLISHER ---")
        try:
            results["publisher"] = await publisher.run(pool)
        except Exception as e:
            print(f"[ORCHESTRATOR] Publisher failed: {e}")
            traceback.print_exc()
            results["publisher"] = {"error": str(e)}

        # 5. MAILER — check inbox + send approved emails
        print(f"\n--- PHASE 5: MAILER ---")
        try:
            results["mailer"] = await mailer.run(pool)
        except Exception as e:
            print(f"[ORCHESTRATOR] Mailer failed: {e}")
            traceback.print_exc()
            results["mailer"] = {"error": str(e)}

        # 6. Summary
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()

        # Pipeline status
        async with pool.acquire() as conn:
            pipeline = await conn.fetch(
                "SELECT status, COUNT(*) as count FROM agent_opportunities WHERE status NOT IN ('skipped') GROUP BY status"
            )
            planned = await conn.fetch(
                "SELECT * FROM agent_plan WHERE status IN ('planned', 'in_progress') ORDER BY priority LIMIT 5"
            )

        pipeline_str = ", ".join(f"{r['status']}={r['count']}" for r in pipeline)

        summary = f"Orchestrator complete in {elapsed:.1f}s. Pipeline: {pipeline_str}"
        await log_action(pool, "orchestrator", "internal", content=summary, status="executed")

        print(f"\n{'='*60}")
        print(f"[ORCHESTRATOR] {summary}")
        if planned:
            print(f"\n[PLAN] Top {len(planned)} planned actions:")
            for p in planned:
                print(f"  - [{p['priority']}] [{p['status']}] {p['action'][:80]}")
        print(f"[DONE] {datetime.now(timezone.utc).strftime('%H:%M UTC')}")

    except Exception as e:
        print(f"[ORCHESTRATOR] FATAL: {e}")
        traceback.print_exc()
        try:
            await log_action(pool, "orchestrator", "internal", content=f"FATAL: {e}", status="failed")
        except Exception:
            pass

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
