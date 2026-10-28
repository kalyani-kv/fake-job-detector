"""Shared test fixtures. Each test gets its own temporary database."""

import pytest

from app import create_app

STRONG_PASSWORD = "Str0ng!Pass-Word"
TEST_EMAIL = "student@example.com"


@pytest.fixture
def app(tmp_path):
    return create_app({
        "TESTING": True,
        "DATABASE_PATH": tmp_path / "test.db",
        "CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key",
    })


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def logged_in_client(client):
    client.post("/register", data={
        "email": TEST_EMAIL,
        "password": STRONG_PASSWORD,
        "confirm_password": STRONG_PASSWORD,
    })
    return client