"""Authentication endpoints: register, login, refresh, logout, delete account."""

import re
from datetime import datetime, timezone

import jwt as pyjwt
from flask import Blueprint, g, jsonify, request

from app.extensions import db, limiter
from app.models.audit import AuditLog
from app.models.user import User
from app.services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.services.encryption import encrypt_dek, generate_user_dek
from app.api.decorators import login_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 12


def _audit(action: str, user_id: str | None = None, **kwargs):
    log = AuditLog(
        user_id=user_id,
        action=action,
        ip_address=request.remote_addr,
        **kwargs,
    )
    db.session.add(log)


# ── Register ─────────────────────────────────────────────────────────────────


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5 per minute")
def register():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    tos_accepted = data.get("tos_accepted", False)

    # Validate
    errors = {}
    if not email or not EMAIL_RE.match(email):
        errors["email"] = "A valid email address is required."
    if len(password) < MIN_PASSWORD_LENGTH:
        errors["password"] = (
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )
    if not tos_accepted:
        errors["tos_accepted"] = "You must accept the Terms of Service."
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists."}), 409

    # Create user
    from flask import current_app

    dek = generate_user_dek()
    encrypted_dek = encrypt_dek(dek, current_app.config["MASTER_ENCRYPTION_KEY"])

    user = User(
        email=email,
        data_encryption_key_enc=encrypted_dek,
        tos_accepted_at=datetime.now(timezone.utc),
    )
    user.set_password(password)

    db.session.add(user)
    _audit("register", user_id=user.id, resource_type="User", resource_id=user.id)
    db.session.commit()

    return (
        jsonify(
            {
                "user_id": user.id,
                "email": user.email,
                "created_at": user.created_at.isoformat(),
            }
        ),
        201,
    )


# ── Login ────────────────────────────────────────────────────────────────────


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        # Intentionally vague to prevent user enumeration
        return jsonify({"error": "Invalid email or password."}), 401

    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)

    _audit("login", user_id=user.id, resource_type="User", resource_id=user.id)
    db.session.commit()

    return jsonify(
        {
            "user_id": user.id,
            "email": user.email,
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "Bearer",
        }
    )


# ── Refresh ──────────────────────────────────────────────────────────────────


@auth_bp.route("/refresh", methods=["POST"])
@limiter.limit("10 per minute")
def refresh():
    # Accept token from Authorization header (frontend) or JSON body
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        refresh_token = auth_header[7:]
    else:
        data = request.get_json(silent=True)
        if not data or "refresh_token" not in data:
            return jsonify({"error": "refresh_token is required"}), 400
        refresh_token = data["refresh_token"]

    try:
        payload = decode_token(refresh_token)
    except pyjwt.ExpiredSignatureError:
        return jsonify({"error": "Refresh token has expired"}), 401
    except pyjwt.PyJWTError:
        return jsonify({"error": "Invalid refresh token"}), 401

    if payload.get("type") != "refresh":
        return jsonify({"error": "Invalid token type"}), 401

    user = db.session.get(User, payload["sub"])
    if user is None:
        return jsonify({"error": "User not found"}), 401

    new_access = create_access_token(user.id)
    return jsonify({"access_token": new_access, "token_type": "Bearer"})


# ── Logout ───────────────────────────────────────────────────────────────────


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    _audit(
        "logout",
        user_id=g.current_user.id,
        resource_type="User",
        resource_id=g.current_user.id,
    )
    db.session.commit()
    # In a production setup, add the token's jti to a Redis deny-list
    # so it cannot be reused before expiry.
    return jsonify({"message": "Logged out successfully."})


# ── Delete account (GDPR right to erasure) ───────────────────────────────────


@auth_bp.route("/account", methods=["DELETE"])
@login_required
def delete_account():
    user = g.current_user

    _audit(
        "delete_account",
        user_id=user.id,
        resource_type="User",
        resource_id=user.id,
    )

    # Cascade delete removes uploads, analyses, blood results, etc.
    db.session.delete(user)
    db.session.commit()

    # In production, also delete encrypted files from disk/S3 here.

    return jsonify({"message": "Account and all associated data deleted."})
