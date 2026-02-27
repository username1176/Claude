"""Flask application factory for GenomeInsight."""

import os
from pathlib import Path

from flask import Flask, jsonify

from app.config import ProductionConfig, config_by_name
from app.extensions import cors, db, limiter


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        config_name: One of "development", "testing", "production".
                     Defaults to the ``FLASK_ENV`` environment variable,
                     falling back to ``"development"``.
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    config_cls = config_by_name[config_name]
    if config_cls is ProductionConfig:
        config_cls.validate()

    flask_app = Flask(__name__)
    flask_app.config.from_object(config_cls)

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
    cors.init_app(flask_app, resources={r"/api/*": {"origins": "*"}})

    # Register blueprints
    from app.api.auth import auth_bp
    from app.api.genome import genome_bp
    from app.api.blood import blood_bp

    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(genome_bp)
    flask_app.register_blueprint(blood_bp)

    # Create tables (use Alembic migrations in production instead)
    with flask_app.app_context():
        from app import models as _models  # noqa: F401
        db.create_all()

    # Global error handlers
    @flask_app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "Resource not found."}), 404

    @flask_app.errorhandler(405)
    def method_not_allowed(_e):
        return jsonify({"error": "Method not allowed."}), 405

    @flask_app.errorhandler(429)
    def rate_limited(_e):
        return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429

    @flask_app.errorhandler(500)
    def internal_error(_e):
        return jsonify({"error": "Internal server error."}), 500

    # Health check
    @flask_app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return flask_app
