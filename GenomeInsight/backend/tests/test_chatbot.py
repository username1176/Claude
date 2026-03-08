"""Tests for AI chatbot utility and chat API routes."""

import json
from unittest.mock import patch, MagicMock
import pytest

from app import create_app
from app.extensions import db as _db
from app.models.user import User


@pytest.fixture()
def app():
    flask_app = create_app("testing")
    with flask_app.app_context():
        _db.create_all()
    yield flask_app
    with flask_app.app_context():
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_headers(app, client):
    """Register a user and return Authorization headers."""
    with app.app_context():
        client.post("/api/v1/auth/register", json={
            "email": "chattest@test.com",
            "password": "TestPass123!",
            "tos_accepted": True,
        })
        resp = client.post("/api/v1/auth/login", json={
            "email": "chattest@test.com",
            "password": "TestPass123!",
        })
        token = resp.get_json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


class TestChatbotContext:
    """Test the chatbot context builder."""

    def test_build_user_context_empty(self, app):
        from app.utils.chatbot import _build_user_context

        with app.app_context():
            ctx = _build_user_context("nonexistent-user-id")
            assert "No health data available" in ctx

    def test_build_user_context_with_innerage(self, app):
        from app.utils.chatbot import _build_user_context
        from app.models.healthspan import InnerAgeResult

        with app.app_context():
            user = User(email="ctx@test.com", password_hash="x")
            _db.session.add(user)
            _db.session.flush()

            ia = InnerAgeResult(
                user_id=user.id,
                chronological_age=40,
                biological_age=37.5,
                age_delta=-2.5,
                model_type="ensemble",
            )
            _db.session.add(ia)
            _db.session.commit()

            ctx = _build_user_context(user.id)
            assert "InnerAge" in ctx
            assert "37.5" in ctx


class TestChatResponse:
    """Test the chat response generation."""

    @patch("app.utils.chatbot.ChatOpenAI")
    def test_get_chat_response_mock(self, mock_llm_class, app):
        from app.utils.chatbot import get_chat_response

        with app.app_context():
            mock_response = MagicMock()
            mock_response.content = "Your cholesterol level of 200 mg/dL is borderline."
            mock_response.usage_metadata = {"total_tokens": 150}
            mock_llm_class.return_value.invoke.return_value = mock_response

            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                result = get_chat_response(
                    user_id="test-user",
                    message="What does my cholesterol mean?",
                )

            assert "cholesterol" in result.content.lower()
            assert result.tokens_used == 150

    def test_get_chat_response_no_api_key(self, app):
        from app.utils.chatbot import get_chat_response

        with app.app_context():
            with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
                result = get_chat_response(
                    user_id="test-user",
                    message="Hello",
                )
            assert "not configured" in result.content.lower()
            assert result.tokens_used == 0


class TestChatRoutes:
    """Test chat API endpoints."""

    def test_chat_requires_premium(self, client, auth_headers):
        """Chat endpoints should require premium subscription."""
        resp = client.post("/api/v1/chat/message",
            json={"message": "Hello"},
            headers=auth_headers,
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert "premium" in data["error"].lower()

    def test_chat_sessions_requires_premium(self, client, auth_headers):
        resp = client.get("/api/v1/chat/sessions", headers=auth_headers)
        assert resp.status_code == 403


class TestSubscriptionRoutes:
    """Test subscription API endpoints."""

    def test_get_status_default_free(self, client, auth_headers):
        resp = client.get("/api/v1/subscription/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["tier"] == "free"
        assert data["is_premium"] is False

    def test_create_checkout_no_stripe(self, client, auth_headers):
        """Without Stripe keys, should return 503."""
        resp = client.post("/api/v1/subscription/create-checkout",
            json={"tier": "premium"},
            headers=auth_headers,
        )
        assert resp.status_code in (400, 503)
