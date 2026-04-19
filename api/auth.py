"""Authentication - Magic Link + API Keys

Endpoints:
- POST /auth/magic-link/request   (send magic link by email)
- POST /auth/magic-link/verify    (exchange token for session)
- GET  /auth/verify               (legacy GET verify: sets cookie + redirects)
- POST /auth/logout
- GET  /auth/me
- GET  /auth/usage
- POST /auth/keys
- GET  /auth/keys
- DELETE /auth/keys/{id}
"""
import os
import secrets
import hashlib
import asyncio
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import RedirectResponse, JSONResponse

from api.database import get_pool
from api import email_templates
from api.mailer import send_email

router = APIRouter(prefix="/api/auth", tags=["auth"])

MAGIC_LINK_EXPIRY = timedelta(minutes=15)
SESSION_EXPIRY = timedelta(days=30)
SITE_URL = os.getenv("DEPSCOPE_SITE_URL", "https://depscope.dev")

# Admin key: set via env in production, falls back to the value referenced in CLAUDE.md
ADMIN_API_KEY = os.getenv("DEPSCOPE_ADMIN_KEY", "")

# Tier rate limits (per minute). Used by the middleware in cache.py / main.py.
TIER_LIMITS = {
    "admin": 0,          # unlimited
    "team": 30000,
    "pro": 10000,
    "free": 1000,
}
ANON_LIMIT = 200


# ---------------------------------------------------------------------------
# Magic link
# ---------------------------------------------------------------------------

@router.post("/magic-link/request")
@router.post("/magic-link")  # legacy alias
async def send_magic_link(request: Request):
    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "Valid email required")

    token = secrets.token_urlsafe(48)
    expires = datetime.now(timezone.utc) + MAGIC_LINK_EXPIRY

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (email) VALUES ($1) ON CONFLICT (email) DO NOTHING",
            email,
        )
        await conn.execute(
            "INSERT INTO magic_tokens (email, token, expires_at) VALUES ($1, $2, $3)",
            email, token, expires,
        )

    link = f"{SITE_URL}/auth/verify?token={token}"
    ip = request.headers.get("CF-Connecting-IP") or (request.client.host if request.client else None)
    try:
        subject, html, plain = email_templates.magic_link_email(email, link, ip=ip)
        # Fire-and-forget so the API response is snappy even while SMTP relays.
        asyncio.create_task(_send_email_async(email, subject, html, plain))
    except Exception as exc:
        print(f"[auth] magic-link send failed: {exc}")

    return {"sent": True, "ok": True, "message": "Check your email for the sign-in link"}


@router.post("/magic-link/verify")
async def magic_link_verify_post(request: Request, response: Response):
    body = await request.json()
    token = (body.get("token") or "").strip()
    if not token:
        raise HTTPException(400, "Missing token")
    session_token, user_row = await _consume_magic_token(token)
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=int(SESSION_EXPIRY.total_seconds()),
        path="/",
    )
    return {
        "ok": True,
        "email": user_row["email"],
        "plan": user_row.get("plan", "free"),
    }


@router.get("/verify")
async def verify_magic_link(token: str):
    """Legacy GET verify: sets cookie and redirects to /dashboard."""
    session_token, _user = await _consume_magic_token(token)
    resp = RedirectResponse(url="/dashboard", status_code=302)
    resp.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=int(SESSION_EXPIRY.total_seconds()),
        path="/",
    )
    return resp


async def _consume_magic_token(token: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT email, used, expires_at FROM magic_tokens WHERE token = $1",
            token,
        )
        if not row:
            raise HTTPException(400, "Invalid or expired link")
        if row["used"]:
            raise HTTPException(400, "Link already used")
        if row["expires_at"] < datetime.now(timezone.utc):
            raise HTTPException(400, "Link expired")

        await conn.execute("UPDATE magic_tokens SET used = TRUE WHERE token = $1", token)

        user = await conn.fetchrow(
            "SELECT id, email, role, plan FROM users WHERE email = $1",
            row["email"],
        )

        # Count prior sessions BEFORE we insert the new one so we can detect
        # first-login-ever for the welcome email.
        prior_sessions = await conn.fetchval(
            "SELECT COUNT(*) FROM sessions WHERE user_id = $1",
            user["id"],
        )

        session_token = secrets.token_urlsafe(48)
        expires = datetime.now(timezone.utc) + SESSION_EXPIRY
        await conn.execute(
            "INSERT INTO sessions (user_id, token, expires_at) VALUES ($1, $2, $3)",
            user["id"], session_token, expires,
        )

    # Fire a welcome email the first time this user ever logs in.
    if (prior_sessions or 0) == 0:
        try:
            subject, html, plain = email_templates.welcome_email(user["email"])
            asyncio.create_task(_send_email_async(user["email"], subject, html, plain))
        except Exception as exc:
            print(f"[auth] welcome email scheduling failed: {exc}")

    return session_token, dict(user)


async def _send_email_async(to: str, subject: str, html: str, plain: str) -> None:
    """Offload blocking SMTP + SSH calls to a worker thread."""
    try:
        await asyncio.to_thread(send_email, to, subject, html, plain)
    except Exception as exc:
        print(f"[auth] async email to={to} subject={subject!r} failed: {exc}")


# ---------------------------------------------------------------------------
# Session introspection
# ---------------------------------------------------------------------------

@router.get("/me")
async def get_me(request: Request):
    user = await _get_user_from_request(request)
    if not user:
        raise HTTPException(401, "Not logged in")
    return {
        "email": user.get("email"),
        "role": user.get("role", "user"),
        "plan": user.get("plan", "free"),
    }


@router.post("/logout")
async def logout(request: Request):
    session_token = request.cookies.get("session")
    if session_token:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM sessions WHERE token = $1", session_token)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("session", path="/")
    return resp


@router.get("/usage")
async def get_usage(request: Request):
    user = await _get_user_from_request(request)
    if not user:
        raise HTTPException(401, "Not logged in")
    uid = user.get("id") or user.get("user_id")
    if not uid:
        return {"total": 0, "by_day": []}
    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COALESCE(SUM(requests_this_month), 0) FROM api_keys WHERE user_id = $1 AND revoked_at IS NULL",
            uid,
        )
        by_day = await conn.fetch(
            """
            SELECT DATE(au.created_at) AS day, COUNT(*) AS calls
            FROM api_usage au
            JOIN api_keys ak ON au.api_key_id = ak.id
            WHERE ak.user_id = $1 AND au.created_at > NOW() - INTERVAL '30 days'
            GROUP BY day ORDER BY day
            """,
            uid,
        )
    return {
        "total": int(total or 0),
        "by_day": [{"day": r["day"].isoformat(), "calls": r["calls"]} for r in by_day],
    }


# ---------------------------------------------------------------------------
# API key management
# ---------------------------------------------------------------------------

@router.post("/keys")
async def create_api_key(request: Request):
    user = await _get_user_from_request(request)
    if not user:
        raise HTTPException(401, "Login required")
    uid = user.get("id") or user.get("user_id")
    if not uid:
        raise HTTPException(403, "Admin tokens cannot create user keys")

    body = await request.json()
    name = (body.get("name") or "API Key")[:100]
    is_test = bool(body.get("test", False))

    suffix = "test" if is_test else "live"
    raw = secrets.token_hex(16)
    full_key = f"ds_{suffix}_{raw}"
    prefix = full_key[:12]
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO api_keys (user_id, key_prefix, key_hash, name, is_test, tier)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, created_at
            """,
            uid, prefix, key_hash, name, is_test, user.get("plan", "free"),
        )

    # Notify the user. Failure to send the email is logged but never blocks
    # the API response -- the key has already been created.
    user_email = user.get("email")
    if user_email:
        try:
            subject, html, plain = email_templates.api_key_created_email(
                user_email, name, prefix, is_test,
            )
            asyncio.create_task(_send_email_async(user_email, subject, html, plain))
        except Exception as exc:
            print(f"[auth] api_key_created email scheduling failed: {exc}")

    return {
        "id": row["id"],
        "key": full_key,
        "prefix": prefix,
        "name": name,
        "is_test": is_test,
        "tier": user.get("plan", "free"),
        "created_at": row["created_at"].isoformat(),
        "warning": "Save this key now. It will not be shown again.",
    }


@router.get("/keys")
async def list_api_keys(request: Request):
    user = await _get_user_from_request(request)
    if not user:
        raise HTTPException(401, "Login required")
    uid = user.get("id") or user.get("user_id")
    if not uid:
        return {"keys": []}
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, key_prefix, name, tier, is_test, last_used_at, last_used_ip,
                   requests_this_month, created_at, expires_at
            FROM api_keys
            WHERE user_id = $1 AND revoked_at IS NULL
            ORDER BY created_at DESC
            """,
            uid,
        )
    out = []
    for r in rows:
        d = dict(r)
        for k in ("last_used_at", "created_at", "expires_at"):
            if d.get(k):
                d[k] = d[k].isoformat()
        out.append(d)
    return {"keys": out}


@router.delete("/keys/{key_id}")
async def revoke_api_key(key_id: int, request: Request):
    user = await _get_user_from_request(request)
    if not user:
        raise HTTPException(401, "Login required")
    uid = user.get("id") or user.get("user_id")
    if not uid:
        raise HTTPException(403, "Admin tokens cannot revoke user keys")
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE api_keys SET revoked_at = NOW() WHERE id = $1 AND user_id = $2 AND revoked_at IS NULL",
            key_id, uid,
        )
    if result.endswith(" 0"):
        raise HTTPException(404, "Key not found")
    return {"revoked": True}


# ---------------------------------------------------------------------------
# Auth helpers (exported)
# ---------------------------------------------------------------------------

async def _get_user_from_api_key(request: Request):
    """Check Authorization: Bearer ds_... header against api_keys table."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    key = auth[7:].strip()
    if not key.startswith("ds_") or key.startswith("ds_admin_"):
        return None
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT ak.id AS api_key_id, ak.user_id, ak.tier, ak.is_test, ak.name,
                   u.id AS user_id_u, u.email, u.role, u.plan
            FROM api_keys ak
            JOIN users u ON u.id = ak.user_id
            WHERE ak.key_hash = $1 AND ak.revoked_at IS NULL
              AND (ak.expires_at IS NULL OR ak.expires_at > NOW())
            """,
            key_hash,
        )
    if not row:
        return None
    data = dict(row)
    data["id"] = data["user_id_u"]
    data["auth_source"] = "api_key"
    # Fire-and-forget usage update
    try:
        asyncio.create_task(_update_key_usage(data["api_key_id"], request))
    except RuntimeError:
        pass
    return data


async def _update_key_usage(key_id: int, request: Request):
    try:
        ip = request.headers.get("CF-Connecting-IP", "") or (request.client.host if request.client else "")
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE api_keys
                SET last_used_at = NOW(),
                    last_used_ip = $1,
                    requests_this_month = requests_this_month + 1
                WHERE id = $2
                """,
                ip[:45], key_id,
            )
    except Exception:
        pass


async def _get_user_from_request(request: Request):
    """Extract user from: API key (Bearer) - admin header - legacy api_key column - session cookie."""
    # 1) Bearer ds_live_/ds_test_ against api_keys table
    user = await _get_user_from_api_key(request)
    if user:
        return user

    # 2) Admin bypass (X-API-Key or Bearer ds_admin_...)
    admin_hdr = request.headers.get("X-API-Key", "")
    auth_hdr = request.headers.get("Authorization", "")
    if admin_hdr == ADMIN_API_KEY or auth_hdr == f"Bearer {ADMIN_API_KEY}":
        return {"role": "admin", "plan": "admin", "email": "admin@depscope", "auth_source": "admin"}

    # 3) Legacy users.api_key support (old ds_<hex> column)
    legacy = admin_hdr or (auth_hdr[7:] if auth_hdr.startswith("Bearer ") else "")
    if legacy and legacy.startswith("ds_") and not legacy.startswith(("ds_live_", "ds_test_", "ds_admin_")):
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE api_key = $1", legacy)
        if row:
            d = dict(row)
            d["auth_source"] = "legacy_api_key"
            return d

    # 4) Session cookie
    session_token = request.cookies.get("session")
    if not session_token:
        return None
    pool = await get_pool()
    async with pool.acquire() as conn:
        sess = await conn.fetchrow(
            "SELECT user_id FROM sessions WHERE token = $1 AND expires_at > NOW()",
            session_token,
        )
        if not sess:
            return None
        row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", sess["user_id"])
    if not row:
        return None
    d = dict(row)
    d["auth_source"] = "session"
    return d
