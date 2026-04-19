"""Database connection pool"""
import asyncpg
from api.config import DATABASE_URL

pool = None

async def get_pool():
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    return pool

async def close_pool():
    global pool
    if pool:
        await pool.close()
        pool = None
