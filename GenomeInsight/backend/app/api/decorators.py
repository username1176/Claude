"""Shared API decorators (authentication, etc.)."""

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
