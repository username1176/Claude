"""Flask application factory for GenomeInsight.

Flask imports are deferred to ``create_app()`` so the ``app`` package can
be imported without Flask installed (e.g. by the Streamlit front-end that
only needs ``app.services``).
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def create_app(config_name: str | None = None):
    """Create and configure the Flask application.

    Args:
        config_name: One of "development", "testing", "production".
                     Defaults to the ``FLASK_ENV`` environment variable,
                     falling back to ``"development"``.
    """
    from flask import Flask, g, jsonify, request

    from app.config import ProductionConfig, config_by_name
    from app.extensions import cors, db, limiter

    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    config_cls = config_by_name[config_name]
    if config_cls is ProductionConfig:
        config_cls.validate()

    flask_app = Flask(__name__)
    flask_app.config.from_object(config_cls)

    # Flask request size limit (defense-in-depth before file_upload.py check)
    flask_app.config["MAX_CONTENT_LENGTH"] = flask_app.config["MAX_VCF_SIZE_BYTES"]

    # Ensure data directories exist
    upload_dir: Path = flask_app.config["UPLOAD_DIR"]
    (upload_dir / "tmp").mkdir(parents=True, exist_ok=True)
    (upload_dir / "enc").mkdir(parents=True, exist_ok=True)

    db_uri = flask_app.config["SQLALCHEMY_DATABASE_URI"]
    if db_uri.startswith("sqlite:///"):
        db_dir = Path(db_uri.replace("sqlite:///", "")).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    # Initialize extensions
    db.init_app(flask_app)
    limiter.init_app(flask_app)

    # CORS — allow the React frontend with credentials
    cors_origins = os.environ.get(
        "CORS_ORIGINS", "http://localhost:3000"
    ).split(",")
    cors.init_app(
        flask_app,
        resources={r"/api/*": {
            "origins": cors_origins,
            "supports_credentials": True,
            "allow_headers": ["Content-Type", "Authorization"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "max_age": 3600,
        }},
    )

    # Register blueprints
    from app.api.auth import auth_bp
    from app.api.genome import genome_bp
    from app.api.blood import blood_bp
    from app.api.epigenetics import epigenetics_bp
    from app.api.wearables import wearables_bp, insights_bp
    from app.api.microbiome import microbiome_bp
    from app.api.analysis import analysis_bp
    from app.api.wgs import wgs_bp
    from app.api.healthspan import healthspan_bp
    from app.api.subscription import subscription_bp
    from app.api.chat import chat_bp

    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(genome_bp)
    flask_app.register_blueprint(blood_bp)
    flask_app.register_blueprint(epigenetics_bp)
    flask_app.register_blueprint(wearables_bp)
    flask_app.register_blueprint(insights_bp)
    flask_app.register_blueprint(microbiome_bp)
    flask_app.register_blueprint(analysis_bp)
    flask_app.register_blueprint(wgs_bp)
    flask_app.register_blueprint(healthspan_bp)
    flask_app.register_blueprint(subscription_bp)
    flask_app.register_blueprint(chat_bp)

    # Create tables (use Alembic migrations in production instead)
    with flask_app.app_context():
        from app import models as _models  # noqa: F401
        db.create_all()

    # ── Security headers ─────────────────────────────────────────────────
    @flask_app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if config_name == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    # ── Request logging for 4xx/5xx ──────────────────────────────────────
    @flask_app.after_request
    def log_errors(response):
        if response.status_code >= 400:
            user = getattr(g, "current_user", None)
            uid = user.id if user else "anon"
            logger.warning(
                "%s %s -> %d (user=%s)",
                request.method, request.path, response.status_code, uid,
            )
        return response

    # ── Global error handlers ────────────────────────────────────────────
    @flask_app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "Resource not found."}), 404

    @flask_app.errorhandler(405)
    def method_not_allowed(_e):
        return jsonify({"error": "Method not allowed."}), 405

    @flask_app.errorhandler(413)
    def request_too_large(_e):
        return jsonify({"error": "File too large."}), 413

    @flask_app.errorhandler(429)
    def rate_limited(_e):
        return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429

    @flask_app.errorhandler(500)
    def internal_error(_e):
        return jsonify({"error": "Internal server error."}), 500

    # Health check — includes service connectivity status
    @flask_app.route("/health")
    def health():
        status = {"status": "ok", "services": {}}

        # Database
        try:
            db.session.execute(db.text("SELECT 1"))
            status["services"]["database"] = "ok"
        except Exception:
            status["services"]["database"] = "error"
            status["status"] = "degraded"

        # Redis / Celery broker (non-critical)
        import redis as redis_lib
        try:
            r = redis_lib.from_url(flask_app.config["CELERY_BROKER_URL"], socket_timeout=2)
            r.ping()
            status["services"]["redis"] = "ok"
        except Exception:
            status["services"]["redis"] = "unavailable"

        return jsonify(status)

    return flask_app


def init_celery(flask_app, celery_app):
    """Bind a Celery instance to the Flask application context.

    Call this from ``celery_worker.py`` so that every Celery task
    automatically has access to the Flask app context, database, etc.
    """
    celery_app.conf.update(
        broker_url=flask_app.config["CELERY_BROKER_URL"],
        result_backend=flask_app.config["CELERY_RESULT_BACKEND"],
    )

    class FlaskTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = FlaskTask
    return celery_app
