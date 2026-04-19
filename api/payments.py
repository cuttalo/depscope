"""Stripe payments and subscription management"""
import json
import stripe
from fastapi import APIRouter, Request, HTTPException
from api.database import get_pool
from api.auth import _get_user_from_request

router = APIRouter(prefix="/payments", tags=["payments"])

# Load Stripe config
with open("/home/deploy/depscope/config/stripe.json") as f:
    STRIPE_CONFIG = json.load(f)

stripe.api_key = STRIPE_CONFIG["secret_key"]

SITE_URL = "https://depscope.dev"

PLANS = {
    "plus_monthly": {
        "name": "DepScope Plus (Monthly)",
        "price_cents": 990,
        "interval": "month",
        "features": [
            "Unlimited API checks",
            "Deep analysis (alternatives, breaking changes)",
            "Priority API response",
            "Dedicated API key",
            "Email support",
        ],
    },
    "plus_yearly": {
        "name": "DepScope Plus (Yearly)",
        "price_cents": 7990,
        "interval": "year",
        "features": [
            "Everything in Monthly",
            "Save 33%",
            "Priority support",
        ],
    },
}


@router.get("/plans", include_in_schema=False)
async def get_plans():
    return {"plans": PLANS}


@router.post("/checkout", include_in_schema=False)
async def create_checkout(request: Request):
    """Create Stripe Checkout session for Plus subscription."""
    user = await _get_user_from_request(request)
    if not user:
        raise HTTPException(401, "Login required")

    body = await request.json()
    plan_id = body.get("plan", "plus_monthly")

    if plan_id not in PLANS:
        raise HTTPException(400, f"Invalid plan: {plan_id}")

    plan = PLANS[plan_id]

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription" if plan["interval"] else "payment",
            line_items=[{
                "price_data": {
                    "currency": "eur",
                    "unit_amount": plan["price_cents"],
                    "product_data": {"name": plan["name"]},
                    "recurring": {"interval": plan["interval"]} if plan["interval"] else None,
                },
                "quantity": 1,
            }],
            customer_email=user["email"],
            client_reference_id=str(user["id"]),
            metadata={"plan": plan_id, "user_id": str(user["id"])},
            success_url=f"{SITE_URL}/dashboard?payment=success",
            cancel_url=f"{SITE_URL}/pricing?payment=cancelled",
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except Exception as e:
        raise HTTPException(500, f"Payment error: {str(e)}")


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    webhook_secret = STRIPE_CONFIG.get("webhook_secret", "")

    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig, webhook_secret)
        else:
            event = json.loads(payload)
    except Exception:
        raise HTTPException(400, "Invalid webhook")

    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = int(session.get("metadata", {}).get("user_id", 0))
        plan_id = session.get("metadata", {}).get("plan", "plus_monthly")

        if user_id:
            pool = await get_pool()
            async with pool.acquire() as conn:
                # Update user plan
                await conn.execute(
                    "UPDATE users SET plan = 'plus', updated_at = NOW() WHERE id = $1",
                    user_id,
                )

                # Create subscription record
                await conn.execute("""
                    INSERT INTO subscriptions (user_id, plan, status, stripe_session_id)
                    VALUES ($1, $2, 'active', $3)
                """, user_id, plan_id, session.get("id"))

                # Create payment record
                await conn.execute("""
                    INSERT INTO payments (user_id, amount_cents, status, stripe_session_id, stripe_payment_intent)
                    VALUES ($1, $2, 'paid', $3, $4)
                """, user_id, session.get("amount_total", 0), session.get("id"), session.get("payment_intent"))

    elif event.get("type") == "customer.subscription.deleted":
        sub = event["data"]["object"]
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE subscriptions SET status = 'canceled', canceled_at = NOW()
                WHERE stripe_subscription_id = $1
            """, sub.get("id"))
            # Find user and downgrade
            row = await conn.fetchrow(
                "SELECT user_id FROM subscriptions WHERE stripe_subscription_id = $1",
                sub.get("id"),
            )
            if row:
                await conn.execute(
                    "UPDATE users SET plan = 'free' WHERE id = $1",
                    row["user_id"],
                )

    return {"ok": True}


@router.get("/subscription", include_in_schema=False)
async def get_subscription(request: Request):
    """Get current user's subscription."""
    user = await _get_user_from_request(request)
    if not user:
        raise HTTPException(401, "Login required")

    pool = await get_pool()
    async with pool.acquire() as conn:
        sub = await conn.fetchrow("""
            SELECT * FROM subscriptions
            WHERE user_id = $1 AND status = 'active'
            ORDER BY created_at DESC LIMIT 1
        """, user["id"])

    return {
        "plan": user["plan"],
        "subscription": dict(sub) if sub else None,
    }
