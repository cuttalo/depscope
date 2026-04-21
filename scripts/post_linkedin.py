import os
"""Post to LinkedIn via UGC Posts API.
Usage: python3 post_linkedin.py <content_file.txt>
"""
import asyncio, asyncpg, aiohttp, sys
from datetime import datetime, timezone

DB_URL = os.environ["DATABASE_URL"]


async def main(content_path: str):
    with open(content_path) as f:
        text = f.read().strip()
    print(f"[{datetime.now(timezone.utc).isoformat()}] posting {len(text)} chars from {content_path}")

    conn = await asyncpg.connect(DB_URL)
    row = await conn.fetchrow(
        "SELECT api_key, api_secret FROM agent_credentials WHERE platform='linkedin'"
    )
    if not row or not row["api_key"] or not row["api_secret"]:
        print("ERROR: no access_token / person_urn in DB")
        sys.exit(1)
    access_token = row["api_key"]
    person_urn = row["api_secret"]

    body = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as r:
            data = await r.json()
            if r.status in (200, 201):
                post_id = data.get("id") or r.headers.get("x-restli-id")
                print(f"✓ posted: {post_id}")
                await conn.execute(
                    "INSERT INTO agent_actions (platform, action_type, target_url, response, created_at) VALUES ('linkedin','post',$1,$2,NOW())",
                    content_path, f"OK:{post_id}",
                )
            else:
                print(f"ERROR {r.status}: {data}")
                sys.exit(1)
    await conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: post_linkedin.py <content_file.txt>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
