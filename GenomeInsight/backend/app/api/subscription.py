"""Stripe subscription management endpoints.

Endpoints:
  POST /api/v1/subscription/create-checkout   — Create a Stripe Checkout session
  POST /api/v1/subscription/create-portal      — Create a Stripe billing portal session
  POST /api/v1/subscription/webhook            — Stripe webhook handler
  GET  /api/v1/subscription/status             — Get current subscription status
"""

import json
import logging
import os
from datetime import datetime, timezone

import stripe
from flask import Blueprint, g, jsonify, request

from app.extensions import db
from app.models.audit import AuditLog
from app.models.subscription import Subscription
from app.api.decorators import login_required

logger = logging.getLogger(__name__)

subscription_bp = Blueprint(
    "subscription", __name__, url_prefix="/api/v1/subscription"
)

# Stripe price IDs (set via env vars)
PRICE_IDS = {
    "basic": os.environ.get("STRIPE_PRICE_BASIC", ""),
    "premium": os.environ.get("STRIPE_PRICE_PREMIUM", ""),
}

STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")


def _audit(action: str, user_id: str | None = None, **kwargs):
    log = AuditLog(
        user_id=user_id,
        action=action,
        ip_address=request.remote_addr,
        details_json=json.dumps(kwargs) if kwargs else None,
    )
    db.session.add(log)


def _get_or_create_subscription(user_id: str) -> Subscription:
    sub = Subscription.query.filter_by(user_id=user_id).first()
    if not sub:
        sub = Subscription(user_id=user_id, tier="free", status="active")
        db.session.add(sub)
        db.session.flush()
    return sub


@subscription_bp.route("/status", methods=["GET"])
@login_required
def get_status():
    """Return current subscription tier and status."""
    sub = _get_or_create_subscription(g.current_user.id)
    db.session.commit()
    return jsonify({
        "tier": sub.tier,
        "status": sub.status,
        "is_premium": sub.is_premium,
        "is_active": sub.is_active,
        "cancel_at_period_end": sub.cancel_at_period_end,
        "current_period_end": (
            sub.current_period_end.isoformat() if sub.current_period_end else None
        ),
    })


@subscription_bp.route("/create-checkout", methods=["POST"])
@login_required
def create_checkout():
    """Create a Stripe Checkout Session for upgrading subscription.

    Body: {"tier": "basic" | "premium", "success_url": "...", "cancel_url": "..."}
    """
    data = request.get_json(silent=True) or {}
    tier = data.get("tier", "premium")
    success_url = data.get("success_url", os.environ.get("FRONTEND_URL", "http://localhost:3000") + "/subscription/success")
    cancel_url = data.get("cancel_url", os.environ.get("FRONTEND_URL", "http://localhost:3000") + "/subscription/cancel")

    if tier not in PRICE_IDS or not PRICE_IDS[tier]:
        return jsonify({"error": f"Invalid or unconfigured tier: {tier}"}), 400

    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe.api_key:
        return jsonify({"error": "Stripe not configured"}), 503

    sub = _get_or_create_subscription(g.current_user.id)

    # Create or retrieve Stripe customer
    if not sub.stripe_customer_id:
        customer = stripe.Customer.create(
            email=g.current_user.email,
            metadata={"user_id": g.current_user.id},
        )
        sub.stripe_customer_id = customer.id
        db.session.commit()

    try:
        session = stripe.checkout.Session.create(
            customer=sub.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{"price": PRICE_IDS[tier], "quantity": 1}],
            mode="subscription",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={"user_id": g.current_user.id, "tier": tier},
        )
    except stripe.error.StripeError as e:
        logger.exception("Stripe checkout creation failed")
        return jsonify({"error": str(e)}), 502

    _audit("subscription.checkout_created", g.current_user.id, tier=tier)
    db.session.commit()

    return jsonify({"checkout_url": session.url, "session_id": session.id})


@subscription_bp.route("/create-portal", methods=["POST"])
@login_required
def create_portal():
    """Create a Stripe billing portal session for managing subscription."""
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe.api_key:
        return jsonify({"error": "Stripe not configured"}), 503

    sub = Subscription.query.filter_by(user_id=g.current_user.id).first()
    if not sub or not sub.stripe_customer_id:
        return jsonify({"error": "No subscription found"}), 404

    return_url = request.get_json(silent=True) or {}
    return_url = return_url.get(
        "return_url",
        os.environ.get("FRONTEND_URL", "http://localhost:3000") + "/settings",
    )

    try:
        session = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=return_url,
        )
    except stripe.error.StripeError as e:
        logger.exception("Stripe portal creation failed")
        return jsonify({"error": str(e)}), 502

    return jsonify({"portal_url": session.url})


@subscription_bp.route("/webhook", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhook events.

    Events handled:
      - checkout.session.completed
      - customer.subscription.updated
      - customer.subscription.deleted
      - invoice.payment_failed
    """
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("Stripe-Signature", "")

    if STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            logger.warning("Stripe webhook signature verification failed")
            return jsonify({"error": "Invalid signature"}), 400
    else:
        try:
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
        except Exception:
            return jsonify({"error": "Invalid payload"}), 400

    event_type = event["type"]
    data_obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data_obj)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data_obj)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data_obj)
    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(data_obj)

    return jsonify({"status": "ok"})


def _handle_checkout_completed(session_obj):
    """Activate subscription after successful checkout."""
    user_id = session_obj.get("metadata", {}).get("user_id")
    tier = session_obj.get("metadata", {}).get("tier", "premium")
    stripe_sub_id = session_obj.get("subscription")

    if not user_id:
        logger.warning("Checkout completed without user_id in metadata")
        return

    sub = _get_or_create_subscription(user_id)
    sub.tier = tier
    sub.status = "active"
    sub.stripe_subscription_id = stripe_sub_id
    sub.stripe_customer_id = session_obj.get("customer")

    # Fetch subscription details for period info
    if stripe_sub_id:
        try:
            stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
            sub.stripe_price_id = stripe_sub["items"]["data"][0]["price"]["id"]
            sub.current_period_start = datetime.fromtimestamp(
                stripe_sub["current_period_start"], tz=timezone.utc
            )
            sub.current_period_end = datetime.fromtimestamp(
                stripe_sub["current_period_end"], tz=timezone.utc
            )
        except Exception:
            logger.exception("Failed to fetch Stripe subscription details")

    _audit("subscription.activated", user_id, tier=tier)
    db.session.commit()
    logger.info("Subscription activated for user %s: tier=%s", user_id, tier)


def _handle_subscription_updated(sub_obj):
    """Update subscription status/period from Stripe."""
    stripe_sub_id = sub_obj.get("id")
    sub = Subscription.query.filter_by(stripe_subscription_id=stripe_sub_id).first()
    if not sub:
        return

    sub.status = sub_obj.get("status", sub.status)
    sub.cancel_at_period_end = sub_obj.get("cancel_at_period_end", False)

    if sub_obj.get("current_period_start"):
        sub.current_period_start = datetime.fromtimestamp(
            sub_obj["current_period_start"], tz=timezone.utc
        )
    if sub_obj.get("current_period_end"):
        sub.current_period_end = datetime.fromtimestamp(
            sub_obj["current_period_end"], tz=timezone.utc
        )

    # Update tier based on price
    items = sub_obj.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id")
        sub.stripe_price_id = price_id
        for tier, pid in PRICE_IDS.items():
            if pid == price_id:
                sub.tier = tier
                break

    _audit("subscription.updated", sub.user_id, status=sub.status, tier=sub.tier)
    db.session.commit()


def _handle_subscription_deleted(sub_obj):
    """Downgrade user to free tier when subscription is canceled."""
    stripe_sub_id = sub_obj.get("id")
    sub = Subscription.query.filter_by(stripe_subscription_id=stripe_sub_id).first()
    if not sub:
        return

    sub.tier = "free"
    sub.status = "canceled"
    _audit("subscription.canceled", sub.user_id)
    db.session.commit()
    logger.info("Subscription canceled for user %s", sub.user_id)


def _handle_payment_failed(invoice_obj):
    """Mark subscription as past_due on payment failure."""
    stripe_sub_id = invoice_obj.get("subscription")
    if not stripe_sub_id:
        return

    sub = Subscription.query.filter_by(stripe_subscription_id=stripe_sub_id).first()
    if sub:
        sub.status = "past_due"
        _audit("subscription.payment_failed", sub.user_id)
        db.session.commit()
        logger.warning("Payment failed for user %s", sub.user_id)
