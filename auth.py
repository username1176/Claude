"""ZeroTax AI — Authentication helpers (SQLite + bcrypt)."""

import hashlib
import hmac
import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from database import get_db


def _hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return salt.hex() + ":" + key.hex()


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, key_hex = stored.split(":")
        salt = bytes.fromhex(salt_hex)
        key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
        return hmac.compare_digest(key, new_key)
    except Exception:
        return False


def register_user(email: str, password: str, full_name: str = "") -> tuple[bool, str]:
    """Register a new user. Returns (success, error_message)."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    email = email.strip().lower()
    if not email or "@" not in email:
        return False, "Invalid email address."

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        return False, "An account with this email already exists."

    user_id = str(uuid.uuid4())
    pw_hash = _hash_password(password)
    db.execute(
        "INSERT INTO users (id, email, password_hash, full_name, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, email, pw_hash, full_name.strip(), datetime.utcnow().isoformat()),
    )
    db.commit()
    return True, ""


def login_user(email: str, password: str) -> tuple[bool, str, dict]:
    """Authenticate user. Returns (success, error_message, user_dict)."""
    email = email.strip().lower()
    db = get_db()
    row = db.execute(
        "SELECT id, email, password_hash, full_name, created_at FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    if not row:
        return False, "Invalid email or password.", {}
    if not _verify_password(password, row["password_hash"]):
        return False, "Invalid email or password.", {}

    user = {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "created_at": row["created_at"],
    }
    # Update last login
    db.execute(
        "UPDATE users SET last_login = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), row["id"]),
    )
    db.commit()
    return True, "", user


def change_password(user_id: str, old_password: str, new_password: str) -> tuple[bool, str]:
    if len(new_password) < 8:
        return False, "New password must be at least 8 characters."
    db = get_db()
    row = db.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row or not _verify_password(old_password, row["password_hash"]):
        return False, "Current password is incorrect."
    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (_hash_password(new_password), user_id),
    )
    db.commit()
    return True, ""


def delete_account(user_id: str) -> None:
    db = get_db()
    db.execute("DELETE FROM tax_plans WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
