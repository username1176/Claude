"""AI chatbot endpoints (premium-only).

Endpoints:
  POST /api/v1/chat/message      — Send a message and get AI response
  GET  /api/v1/chat/history      — Get conversation history for a session
  DELETE /api/v1/chat/session     — Clear a chat session
"""

import json
import logging
import uuid

from flask import Blueprint, g, jsonify, request

from app.extensions import db
from app.models.audit import AuditLog
from app.models.subscription import ChatMessage
from app.api.decorators import login_required, premium_required

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__, url_prefix="/api/v1/chat")


def _audit(action: str, user_id: str | None = None, **kwargs):
    log = AuditLog(
        user_id=user_id,
        action=action,
        ip_address=request.remote_addr,
        details_json=json.dumps(kwargs) if kwargs else None,
    )
    db.session.add(log)


@chat_bp.route("/message", methods=["POST"])
@login_required
@premium_required
def send_message():
    """Send a message to the AI chatbot.

    Body: {
        "message": "What does my cholesterol level mean?",
        "session_id": "optional-uuid"  (creates new session if omitted)
    }
    """
    from app.utils.chatbot import get_chat_response

    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400
    if len(message) > 2000:
        return jsonify({"error": "Message too long (max 2000 chars)"}), 400

    session_id = data.get("session_id") or str(uuid.uuid4())
    user_id = g.current_user.id

    # Load conversation history for this session
    history_records = (
        ChatMessage.query
        .filter_by(user_id=user_id, session_id=session_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(40)
        .all()
    )
    conversation_history = [
        {"role": r.role, "content": r.content} for r in history_records
    ]

    # Get AI response
    response = get_chat_response(
        user_id=user_id,
        message=message,
        conversation_history=conversation_history,
    )

    # Save user message
    user_msg = ChatMessage(
        user_id=user_id,
        session_id=session_id,
        role="user",
        content=message,
    )
    db.session.add(user_msg)

    # Save assistant response
    assistant_msg = ChatMessage(
        user_id=user_id,
        session_id=session_id,
        role="assistant",
        content=response.content,
        tokens_used=response.tokens_used,
    )
    db.session.add(assistant_msg)

    _audit("chat.message", user_id, session_id=session_id)
    db.session.commit()

    return jsonify({
        "session_id": session_id,
        "response": response.content,
        "tokens_used": response.tokens_used,
        "model": response.model,
    })


@chat_bp.route("/history", methods=["GET"])
@login_required
@premium_required
def get_history():
    """Get conversation history for a session.

    Query params: session_id (required)
    """
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    messages = (
        ChatMessage.query
        .filter_by(user_id=g.current_user.id, session_id=session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return jsonify({
        "session_id": session_id,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    })


@chat_bp.route("/sessions", methods=["GET"])
@login_required
@premium_required
def list_sessions():
    """List all chat sessions for the current user."""
    sessions = (
        db.session.query(
            ChatMessage.session_id,
            db.func.min(ChatMessage.created_at).label("started_at"),
            db.func.max(ChatMessage.created_at).label("last_message_at"),
            db.func.count(ChatMessage.id).label("message_count"),
        )
        .filter_by(user_id=g.current_user.id)
        .group_by(ChatMessage.session_id)
        .order_by(db.func.max(ChatMessage.created_at).desc())
        .limit(50)
        .all()
    )

    return jsonify({
        "sessions": [
            {
                "session_id": s.session_id,
                "started_at": s.started_at.isoformat(),
                "last_message_at": s.last_message_at.isoformat(),
                "message_count": s.message_count,
            }
            for s in sessions
        ],
    })


@chat_bp.route("/session", methods=["DELETE"])
@login_required
@premium_required
def delete_session():
    """Delete all messages in a chat session.

    Body: {"session_id": "..."}
    """
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    deleted = ChatMessage.query.filter_by(
        user_id=g.current_user.id, session_id=session_id
    ).delete()

    _audit("chat.session_deleted", g.current_user.id, session_id=session_id)
    db.session.commit()

    return jsonify({"deleted": deleted})
