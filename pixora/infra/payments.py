"""Stripe payment processing — checkout, webhooks, subscription management.

Set PIXORA_STRIPE_SECRET_KEY to enable.
Create products in Stripe Dashboard, set PIXORA_STRIPE_PRICE_STARTER and PIXORA_STRIPE_PRICE_PRO.
"""
from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_stripe():
    from pixora.config.settings import settings
    if not settings.stripe_secret_key:
        return None
    try:
        import stripe
        stripe.api_key = settings.stripe_secret_key
        return stripe
    except ImportError:
        logger.debug("stripe package not installed")
        return None


async def create_checkout_session(
    plan: str,
    tenant_id: str,
    customer_email: str,
    success_url: str = "https://pixora.onrender.com/dashboard?checkout=success",
    cancel_url: str = "https://pixora.onrender.com/billing?checkout=cancelled",
) -> dict | None:
    stripe = get_stripe()
    if not stripe:
        return None

    from pixora.config.settings import settings
    price_map = {
        "starter": settings.stripe_price_starter,
        "pro": settings.stripe_price_pro,
    }
    price_id = price_map.get(plan)
    if not price_id:
        return None

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=customer_email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"tenant_id": tenant_id, "plan": plan},
        )
        return {"url": session.url, "session_id": session.id}
    except Exception as exc:
        logger.error("payments: checkout session failed: %s", exc)
        return None


async def handle_webhook(payload: bytes, sig_header: str) -> dict:
    stripe = get_stripe()
    if not stripe:
        return {"error": "stripe not configured"}

    from pixora.config.settings import settings
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except Exception as exc:
        return {"error": f"webhook verification failed: {exc}"}

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        tenant_id = data.get("metadata", {}).get("tenant_id", "")
        plan = data.get("metadata", {}).get("plan", "")
        customer_id = data.get("customer", "")
        subscription_id = data.get("subscription", "")
        logger.info("payments: checkout completed tenant=%s plan=%s", tenant_id, plan)
        return {
            "action": "upgrade",
            "tenant_id": tenant_id,
            "plan": plan,
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
        }

    if event_type == "customer.subscription.deleted":
        subscription_id = data.get("id", "")
        logger.info("payments: subscription cancelled %s", subscription_id)
        return {"action": "downgrade", "stripe_subscription_id": subscription_id}

    if event_type == "invoice.payment_failed":
        customer_id = data.get("customer", "")
        logger.warning("payments: payment failed customer=%s", customer_id)
        return {"action": "payment_failed", "stripe_customer_id": customer_id}

    return {"action": "ignored", "event_type": event_type}


def is_stripe_configured() -> bool:
    from pixora.config.settings import settings
    return bool(settings.stripe_secret_key)
