import os
"""Daily pull GSC data into DB — feed Launch Tracker."""
import asyncio, asyncpg, os, requests, sys, json
from datetime import datetime, date, timedelta, timezone
from urllib.parse import quote

DB_URL = os.environ["DATABASE_URL"]
CLIENT_ID = os.environ["GSC_CLIENT_ID"]
CLIENT_SECRET = os.environ["GSC_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["GSC_REFRESH_TOKEN"]
SITE = "https://depscope.dev/"


async def ensure_table(conn):
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS gsc_daily (
          day        DATE PRIMARY KEY,
          clicks     INT DEFAULT 0,
          impressions INT DEFAULT 0,
          ctr        NUMERIC,
          position   NUMERIC,
          updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS gsc_query_top (
          id         SERIAL PRIMARY KEY,
          day        DATE,
          query      TEXT,
          clicks     INT,
          impressions INT,
          ctr        NUMERIC,
          position   NUMERIC,
          UNIQUE (day, query)
        );
    """)


def token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN, "grant_type": "refresh_token",
    }, timeout=20)
    return r.json()["access_token"]


def query_gsc(tok, dims, start, end):
    url = f"https://www.googleapis.com/webmasters/v3/sites/{quote(SITE, safe='')}/searchAnalytics/query"
    r = requests.post(url, headers={"Authorization": f"Bearer {tok}"}, json={
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": dims,
        "rowLimit": 1000,
    }, timeout=30)
    if r.status_code != 200:
        print(f"  GSC query {dims}: HTTP {r.status_code} {r.text[:200]}")
        return []
    return r.json().get("rows", [])


async def main():
    conn = await asyncpg.connect(DB_URL)
    await ensure_table(conn)
    tok = token()

    end = date.today() - timedelta(days=3)   # GSC has ~3 day lag
    start = end - timedelta(days=30)

    # By day
    rows = query_gsc(tok, ["date"], start, end)
    for r in rows:
        d = date.fromisoformat(r["keys"][0])
        await conn.execute("""
            INSERT INTO gsc_daily(day, clicks, impressions, ctr, position, updated_at)
            VALUES ($1,$2,$3,$4,$5,NOW())
            ON CONFLICT (day) DO UPDATE SET
              clicks=EXCLUDED.clicks, impressions=EXCLUDED.impressions,
              ctr=EXCLUDED.ctr, position=EXCLUDED.position, updated_at=NOW()
        """, d, int(r.get("clicks",0)), int(r.get("impressions",0)),
             r.get("ctr",0), r.get("position",0))
    print(f"gsc_daily: {len(rows)} days")

    # Top queries last 7 days
    end7 = end
    start7 = end7 - timedelta(days=7)
    rows_q = query_gsc(tok, ["query"], start7, end7)
    # store snapshot under end7 date
    await conn.execute("DELETE FROM gsc_query_top WHERE day=$1", end7)
    for r in rows_q[:200]:
        q = r["keys"][0][:500]
        try:
            await conn.execute("""
                INSERT INTO gsc_query_top(day, query, clicks, impressions, ctr, position)
                VALUES ($1,$2,$3,$4,$5,$6)
                ON CONFLICT (day, query) DO NOTHING
            """, end7, q, int(r.get("clicks",0)), int(r.get("impressions",0)),
                 r.get("ctr",0), r.get("position",0))
        except Exception as e:
            pass
    print(f"gsc_query_top: {len(rows_q)} queries (snapshot day={end7})")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
