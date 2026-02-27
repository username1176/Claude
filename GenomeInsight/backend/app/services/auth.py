"""JWT token creation and verification."""

from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    expires = current_app.config["JWT_ACCESS_TOKEN_EXPIRES_SECONDS"]
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(seconds=expires),
        "type": "access",
    }
    return jwt.encode(
        payload,
        current_app.config["SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )


def create_refresh_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    expires = current_app.config["JWT_REFRESH_TOKEN_EXPIRES_SECONDS"]
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(seconds=expires),
        "type": "refresh",
    }
    return jwt.encode(
        payload,
        current_app.config["SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )


def decode_token(token: str) -> dict:
    """Decode and verify a JWT.  Raises ``jwt.PyJWTError`` on failure."""
    return jwt.decode(
        token,
        current_app.config["SECRET_KEY"],
        algorithms=[current_app.config["JWT_ALGORITHM"]],
    )
