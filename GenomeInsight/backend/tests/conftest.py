"""Shared pytest fixtures for GenomeInsight backend tests."""

import pytest

from app import create_app
from app.extensions import db as _db


@pytest.fixture()
def app():
    """Create a fresh application and database for each test."""
    flask_app = create_app("testing")

    with flask_app.app_context():
        _db.create_all()

    yield flask_app

    with flask_app.app_context():
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()
