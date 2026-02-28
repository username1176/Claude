"""Wearable connection, data, and daily insight endpoints."""

import json
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, current_app, g, jsonify, request

from app.extensions import db, limiter
from app.models.audit import AuditLog
from app.models.wearable import (
    DailyInsight,
    DailyWearableData,
    WearableConnection,
)
from app.api.decorators import login_required
from app.utils.wearable_client import (
    SUPPORTED_PROVIDERS,
    WEARABLE_DATA_TYPES,
    encrypt_token,
    exchange_terra_token,
    generate_terra_auth_url,
    revoke_terra_connection,
)

wearables_bp = Blueprint(
    "wearables", __name__, url_prefix="/api/v1/wearables"
)
insights_bp = Blueprint(
    "insights", __name__, url_prefix="/api/v1/insights"
)


def _audit(action: str, **kwargs):
    log = AuditLog(
        user_id=g.current_user.id,
        action=action,
        ip_address=request.remote_addr,
        **kwargs,
    )
    db.session.add(log)


# ══════════════════════════════════════════════════════════════════════════════
# Wearable endpoints
# ══════════════════════════════════════════════════════════════════════════════


# ── List providers ──────────────────────────────────────────────────────────


@wearables_bp.route("/providers", methods=["GET"])
@login_required
def list_providers():
    """Return the list of supported wearable providers."""
    # Check which providers the user already has connected
    user_connections = (
        WearableConnection.query
        .filter_by(user_id=g.current_user.id)
        .filter(WearableConnection.status.in_(["active", "expired"]))
        .all()
    )
    connected = {c.provider for c in user_connections}

    providers = []
    for p in sorted(SUPPORTED_PROVIDERS):
        providers.append({
            "provider": p,
            "display_name": p.replace("_", " ").title(),
            "connected": p in connected,
        })
    return jsonify({"providers": providers})


# ── Initiate OAuth connection ───────────────────────────────────────────────


@wearables_bp.route("/connect", methods=["POST"])
@limiter.limit("10 per hour")
@login_required
def connect_wearable():
    """Initiate OAuth2 flow for a wearable provider via Terra."""
    data = request.get_json(silent=True) or {}
    provider = data.get("provider", "").lower()

    if provider not in SUPPORTED_PROVIDERS:
        return (
            jsonify({
                "error": f"Unsupported provider '{provider}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_PROVIDERS))}",
            }),
            400,
        )

    # Check for existing connection
    existing = WearableConnection.query.filter_by(
        user_id=g.current_user.id, provider=provider
    ).first()
    if existing and existing.status == "active":
        return (
            jsonify({
                "error": f"Already connected to {provider}.",
                "connection_id": existing.id,
            }),
            409,
        )

    terra_api_key = current_app.config.get("TERRA_API_KEY", "")
    redirect_uri = current_app.config.get(
        "TERRA_REDIRECT_URI",
        request.host_url.rstrip("/") + "/api/v1/wearables/callback",
    )

    auth_result = generate_terra_auth_url(
        provider=provider,
        terra_api_key=terra_api_key,
        redirect_uri=redirect_uri,
    )

    # Store the state token temporarily for validation on callback
    # In production, use a Redis cache with TTL. Here we use the session/DB.
    if existing:
        existing.status = "pending"
        db.session.commit()

    _audit("initiate_wearable_connect", resource_type="WearableConnection",
           detail=json.dumps({"provider": provider}))
    db.session.commit()

    return jsonify({
        "auth_url": auth_result.auth_url,
        "state": auth_result.state,
        "provider": auth_result.provider,
        "message": "Redirect user to auth_url to complete connection.",
    })


# ── OAuth callback ──────────────────────────────────────────────────────────


@wearables_bp.route("/callback", methods=["POST"])
@login_required
def oauth_callback():
    """Handle OAuth2 callback after user authorizes the wearable provider.

    Expects JSON body with code, provider, and optionally state for CSRF
    validation.  In a real deployment the Terra widget posts directly to
    this endpoint or the frontend relays the code.
    """
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")
    provider = data.get("provider", "").lower()

    if not code:
        return jsonify({"error": "Missing authorization code."}), 400
    if provider not in SUPPORTED_PROVIDERS:
        return jsonify({"error": "Invalid provider."}), 400

    terra_api_key = current_app.config.get("TERRA_API_KEY", "")
    terra_dev_id = current_app.config.get("TERRA_DEV_ID", "")

    try:
        tokens = exchange_terra_token(
            code=code,
            terra_api_key=terra_api_key,
            terra_dev_id=terra_dev_id,
        )
    except Exception as exc:
        return jsonify({"error": f"Token exchange failed: {exc}"}), 502

    user = g.current_user
    master_key = current_app.config["MASTER_ENCRYPTION_KEY"]

    from app.services.encryption import decrypt_dek
    dek = decrypt_dek(user.data_encryption_key_enc, master_key)

    # Encrypt tokens before storing
    access_enc = encrypt_token(tokens.access_token, dek) if tokens.access_token else None
    refresh_enc = encrypt_token(tokens.refresh_token, dek) if tokens.refresh_token else None

    # Upsert connection
    connection = WearableConnection.query.filter_by(
        user_id=user.id, provider=provider
    ).first()

    if connection:
        connection.terra_user_id = tokens.terra_user_id
        connection.access_token_enc = access_enc
        connection.refresh_token_enc = refresh_enc
        connection.token_expires_at = tokens.expires_at
        connection.scopes = tokens.scopes
        connection.status = "active"
        connection.connected_at = datetime.now(timezone.utc)
    else:
        connection = WearableConnection(
            user_id=user.id,
            provider=provider,
            terra_user_id=tokens.terra_user_id,
            access_token_enc=access_enc,
            refresh_token_enc=refresh_enc,
            token_expires_at=tokens.expires_at,
            scopes=tokens.scopes,
            status="active",
        )
        db.session.add(connection)

    _audit("wearable_connected", resource_type="WearableConnection",
           detail=json.dumps({"provider": provider}))
    db.session.commit()

    # Dispatch initial sync
    celery_task_id = None
    try:
        from app.tasks.wearable_tasks import sync_wearable_connection
        task = sync_wearable_connection.delay(connection.id)
        celery_task_id = task.id
    except Exception:
        pass

    return jsonify({
        "connection_id": connection.id,
        "provider": provider,
        "status": connection.status,
        "task_id": celery_task_id,
        "message": f"Successfully connected to {provider}.",
    })


# ── List connections ────────────────────────────────────────────────────────


@wearables_bp.route("/connections", methods=["GET"])
@login_required
def list_connections():
    """Return the user's wearable connections."""
    connections = (
        WearableConnection.query
        .filter_by(user_id=g.current_user.id)
        .order_by(WearableConnection.connected_at.desc())
        .all()
    )
    return jsonify([
        {
            "id": c.id,
            "provider": c.provider,
            "status": c.status,
            "connected_at": c.connected_at.isoformat(),
            "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
            "scopes": c.scopes,
        }
        for c in connections
    ])


# ── Disconnect ──────────────────────────────────────────────────────────────


@wearables_bp.route("/connections/<connection_id>", methods=["DELETE"])
@login_required
def disconnect_wearable(connection_id: str):
    """Disconnect a wearable provider and revoke tokens."""
    connection = WearableConnection.query.filter_by(
        id=connection_id, user_id=g.current_user.id
    ).first()
    if not connection:
        return jsonify({"error": "Wearable connection not found."}), 404

    # Revoke with Terra
    terra_api_key = current_app.config.get("TERRA_API_KEY", "")
    terra_dev_id = current_app.config.get("TERRA_DEV_ID", "")
    if connection.terra_user_id:
        revoke_terra_connection(
            connection.terra_user_id, terra_api_key, terra_dev_id
        )

    connection.status = "revoked"
    connection.access_token_enc = None
    connection.refresh_token_enc = None

    _audit("wearable_disconnected", resource_type="WearableConnection",
           resource_id=connection.id)
    db.session.commit()

    return jsonify({"message": f"Disconnected from {connection.provider}."})


# ── Manual sync ─────────────────────────────────────────────────────────────


@wearables_bp.route("/connections/<connection_id>/sync", methods=["POST"])
@limiter.limit("5 per hour")
@login_required
def trigger_sync(connection_id: str):
    """Manually trigger a data sync for a connection."""
    connection = WearableConnection.query.filter_by(
        id=connection_id, user_id=g.current_user.id
    ).first()
    if not connection:
        return jsonify({"error": "Wearable connection not found."}), 404

    if connection.status != "active":
        return (
            jsonify({
                "error": f"Connection is {connection.status}. Cannot sync.",
            }),
            409,
        )

    celery_task_id = None
    try:
        from app.tasks.wearable_tasks import sync_wearable_connection
        task = sync_wearable_connection.delay(connection.id)
        celery_task_id = task.id
    except Exception:
        pass

    _audit("trigger_wearable_sync", resource_type="WearableConnection",
           resource_id=connection.id)
    db.session.commit()

    return jsonify({
        "connection_id": connection.id,
        "status": "sync_queued",
        "task_id": celery_task_id,
        "message": "Wearable data sync queued.",
    })


# ── Query wearable data ────────────────────────────────────────────────────


@wearables_bp.route("/data", methods=["GET"])
@login_required
def get_wearable_data():
    """Return wearable data filtered by type and date range."""
    data_type = request.args.get("type")
    from_date_str = request.args.get("from_date")
    to_date_str = request.args.get("to_date")

    query = DailyWearableData.query.filter_by(user_id=g.current_user.id)

    if data_type:
        if data_type not in WEARABLE_DATA_TYPES:
            return (
                jsonify({
                    "error": f"Invalid type. Must be one of: {', '.join(sorted(WEARABLE_DATA_TYPES))}",
                }),
                400,
            )
        query = query.filter_by(data_type=data_type)

    if from_date_str:
        try:
            from_d = date.fromisoformat(from_date_str)
            query = query.filter(DailyWearableData.date >= from_d)
        except ValueError:
            return jsonify({"error": "Invalid from_date format. Use YYYY-MM-DD."}), 400

    if to_date_str:
        try:
            to_d = date.fromisoformat(to_date_str)
            query = query.filter(DailyWearableData.date <= to_d)
        except ValueError:
            return jsonify({"error": "Invalid to_date format. Use YYYY-MM-DD."}), 400

    records = query.order_by(DailyWearableData.date.desc()).limit(200).all()

    data = []
    for r in records:
        summary = {}
        if r.summary_json:
            try:
                summary = json.loads(r.summary_json)
            except (json.JSONDecodeError, TypeError):
                pass

        data.append({
            "date": r.date.isoformat(),
            "type": r.data_type,
            "provider": r.connection.provider if r.connection else None,
            "summary": summary,
        })

    return jsonify({"data": data})


# ── Latest day's data ──────────────────────────────────────────────────────


@wearables_bp.route("/data/latest", methods=["GET"])
@login_required
def get_latest_data():
    """Return the most recent day's wearable data."""
    latest = (
        DailyWearableData.query
        .filter_by(user_id=g.current_user.id)
        .order_by(DailyWearableData.date.desc())
        .first()
    )
    if not latest:
        return jsonify({"data": [], "date": None})

    latest_date = latest.date
    records = (
        DailyWearableData.query
        .filter_by(user_id=g.current_user.id, date=latest_date)
        .all()
    )

    data = []
    for r in records:
        summary = {}
        if r.summary_json:
            try:
                summary = json.loads(r.summary_json)
            except (json.JSONDecodeError, TypeError):
                pass

        data.append({
            "date": r.date.isoformat(),
            "type": r.data_type,
            "provider": r.connection.provider if r.connection else None,
            "summary": summary,
        })

    return jsonify({"data": data, "date": latest_date.isoformat()})


# ══════════════════════════════════════════════════════════════════════════════
# Insights endpoints
# ══════════════════════════════════════════════════════════════════════════════


# ── Daily insights ──────────────────────────────────────────────────────────


@insights_bp.route("/daily", methods=["GET"])
@login_required
def get_daily_insights():
    """Return today's cross-domain insights."""
    today = date.today()

    insights = (
        DailyInsight.query
        .filter_by(user_id=g.current_user.id, date=today)
        .order_by(DailyInsight.generated_at.desc())
        .all()
    )

    result = []
    for i in insights:
        sources = []
        if i.data_sources_json:
            try:
                sources = json.loads(i.data_sources_json)
            except (json.JSONDecodeError, TypeError):
                pass

        result.append({
            "id": i.id,
            "type": i.insight_type,
            "title": i.title,
            "body": i.body,
            "data_sources": sources,
            "confidence": i.confidence,
            "generated_at": i.generated_at.isoformat(),
        })

    return jsonify({
        "date": today.isoformat(),
        "insights": result,
        "disclaimer": (
            "These insights are based on observational correlations between "
            "your wearable data and genetic/blood/epigenetic information. "
            "They are NOT medical advice. Consult a healthcare professional "
            "for medical decisions."
        ),
    })


# ── Insight history ─────────────────────────────────────────────────────────


@insights_bp.route("/history", methods=["GET"])
@login_required
def get_insight_history():
    """Return paginated insight history."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    insight_type = request.args.get("type")

    query = DailyInsight.query.filter_by(user_id=g.current_user.id)

    if insight_type:
        query = query.filter_by(insight_type=insight_type)

    query = query.order_by(DailyInsight.date.desc(), DailyInsight.generated_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for i in pagination.items:
        sources = []
        if i.data_sources_json:
            try:
                sources = json.loads(i.data_sources_json)
            except (json.JSONDecodeError, TypeError):
                pass

        items.append({
            "id": i.id,
            "date": i.date.isoformat(),
            "type": i.insight_type,
            "title": i.title,
            "body": i.body,
            "data_sources": sources,
            "confidence": i.confidence,
            "generated_at": i.generated_at.isoformat(),
        })

    return jsonify({
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "insights": items,
    })


# ── Force insight generation ────────────────────────────────────────────────


@insights_bp.route("/generate", methods=["POST"])
@limiter.limit("5 per hour")
@login_required
def trigger_insight_generation():
    """Force re-generation of today's daily insights."""
    celery_task_id = None
    try:
        from app.tasks.wearable_tasks import generate_daily_insights
        task = generate_daily_insights.delay(g.current_user.id)
        celery_task_id = task.id
    except Exception:
        pass

    _audit("trigger_daily_insights", resource_type="DailyInsight")
    db.session.commit()

    return jsonify({
        "status": "queued",
        "task_id": celery_task_id,
        "message": "Daily insight generation queued.",
    })
