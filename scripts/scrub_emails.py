#!/usr/bin/env python3
"""Scrub maintainer emails from packages.data_json.

Rationale: registries expose author emails publicly, but re-publishing them
via DepScope turns us into an email-harvest target. Privacy-by-default:
we replace anything matching a standard email regex with '[email-redacted]'
both in data_json AND (for safety) in related fields.

Idempotent. Runs in batches. Updates only rows that still have emails.
"""
import asyncio
import json
import os
import re
import sys

sys.path.insert(0, "/home/deploy/depscope")

import asyncpg

from api.config import DATABASE_URL

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
REDACTED = "[email-redacted]"


def scrub(value):
    """Recursively scrub emails from any string inside a dict/list/primitive."""
    if isinstance(value, str):
        return EMAIL_RE.sub(REDACTED, value)
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    return value


async def main():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM packages WHERE data_json::text ~ $1",
            EMAIL_RE.pattern,
        )
        print(f"Rows with emails in data_json: {total}")
        if total == 0:
            print("Nothing to scrub.")
            return

        processed = 0
        batch_size = 200
        while True:
            rows = await conn.fetch(
                "SELECT id, data_json FROM packages WHERE data_json::text ~ $1 LIMIT $2",
                EMAIL_RE.pattern,
                batch_size,
            )
            if not rows:
                break
            updates = []
            for r in rows:
                dj = r["data_json"]
                if isinstance(dj, str):
                    try:
                        dj = json.loads(dj)
                    except Exception:
                        # fall back to regex-only on raw text
                        txt = EMAIL_RE.sub(REDACTED, r["data_json"])
                        updates.append((txt, r["id"]))
                        continue
                cleaned = scrub(dj)
                safe = json.dumps(cleaned, default=str, ensure_ascii=False)
                safe = safe.replace("\\u0000", "").replace("\x00", "")
                updates.append((safe, r["id"]))
            await conn.executemany(
                "UPDATE packages SET data_json = $1::jsonb WHERE id = $2",
                updates,
            )
            processed += len(rows)
            print(f"  processed: {processed}/{total}")

        # Final check
        remaining = await conn.fetchval(
            "SELECT COUNT(*) FROM packages WHERE data_json::text ~ $1",
            EMAIL_RE.pattern,
        )
        print(f"Rows still with emails (should be 0): {remaining}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
