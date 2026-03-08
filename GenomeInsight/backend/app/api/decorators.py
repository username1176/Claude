"""Shared API decorators (authentication, subscription gating, etc.)."""

from functools import wraps

import jwt as pyjwt
from flask import g, jsonify, request

from app.extensions import db
from app.models.user import User
from app.services.auth import decode_token


def login_required(f):
    """Require a valid JWT access token in the Authorization header.

    On success, sets ``g.current_user`` to the authenticated :class:`User`.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or malformed Authorization header"}), 401

        token = auth_header[7:]
        try:
            payload = decode_token(token)
        except pyjwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except pyjwt.PyJWTError:
            return jsonify({"error": "Invalid token"}), 401

        if payload.get("type") != "access":
            return jsonify({"error": "Invalid token type"}), 401

        user = db.session.get(User, payload["sub"])
        if user is None:
            return jsonify({"error": "User not found"}), 401

        g.current_user = user
        return f(*args, **kwargs)

    return decorated


def _get_subscription():
    """Retrieve the current user's subscription (lazy import to avoid cycles)."""
    from app.models.subscription import Subscription

    return Subscription.query.filter_by(user_id=g.current_user.id).first()


def premium_required(f):
    """Require an active premium subscription.

    Must be used AFTER ``@login_required`` so ``g.current_user`` is set.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        sub = _get_subscription()
        if not sub or not sub.is_premium:
            return jsonify({
                "error": "Premium subscription required",
                "upgrade_url": "/api/v1/subscription/create-checkout",
            }), 403
        return f(*args, **kwargs)

    return decorated


def basic_required(f):
    """Require at least a basic (or premium) subscription.

    Must be used AFTER ``@login_required`` so ``g.current_user`` is set.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        sub = _get_subscription()
        if not sub or not sub.is_basic_or_above:
            return jsonify({
                "error": "Basic or Premium subscription required",
                "upgrade_url": "/api/v1/subscription/create-checkout",
            }), 403
        return f(*args, **kwargs)

    return decorated
