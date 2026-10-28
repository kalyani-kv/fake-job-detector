"""Tests for registration, login, lockout, logout and CSRF."""

import sqlite3

from app import create_app
from config import settings
from src.auth import validate_password
from tests.conftest import STRONG_PASSWORD, TEST_EMAIL


def register(client, email=TEST_EMAIL, password=STRONG_PASSWORD, confirm=None):
    return client.post("/register", data={
        "email": email,
        "password": password,
        "confirm_password": confirm if confirm is not None else password,
    })


def test_pages_require_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_analyze_requires_login(client):
    assert client.post("/analyze", data={"description": "x" * 50}).status_code == 302


def test_api_requires_login(client):
    assert client.post("/api/analyze", json={}).status_code == 401


def test_register_then_access_home(client):
    response = register(client)
    assert response.status_code == 302
    assert client.get("/").status_code == 200


def test_weak_password_rejected(client):
    response = register(client, password="short")
    assert response.status_code == 400


def test_password_containing_email_name_rejected():
    problems = validate_password("Student!2024xyz", "student@example.com")
    assert any("email" in problem for problem in problems)


def test_strong_password_accepted():
    assert validate_password(STRONG_PASSWORD, TEST_EMAIL) == []


def test_mismatched_confirmation_rejected(client):
    assert register(client, confirm="Different!Pass-1").status_code == 400


def test_duplicate_email_rejected(app, client):
    register(client)
    other_client = app.test_client()
    assert register(other_client).status_code == 400


def test_password_is_stored_hashed(app, client):
    register(client)
    connection = sqlite3.connect(app.config["DATABASE_PATH"])
    stored = connection.execute("SELECT password_hash FROM users").fetchone()[0]
    connection.close()
    assert STRONG_PASSWORD not in stored
    assert stored.startswith("pbkdf2:")


def test_login_with_correct_password(app, client):
    register(client)
    fresh_client = app.test_client()
    response = fresh_client.post(
        "/login", data={"email": TEST_EMAIL, "password": STRONG_PASSWORD})
    assert response.status_code == 302


def test_wrong_password_gives_generic_error(app, client):
    register(client)
    fresh_client = app.test_client()
    response = fresh_client.post(
        "/login", data={"email": TEST_EMAIL, "password": "Wrong!Pass-123"})
    assert response.status_code == 401
    assert b"Incorrect email or password" in response.data


def test_unknown_email_gives_same_error(client):
    response = client.post(
        "/login", data={"email": "nobody@example.com", "password": "Wrong!Pass-123"})
    assert response.status_code == 401
    assert b"Incorrect email or password" in response.data


def test_account_locks_after_repeated_failures(app, client):
    register(client)
    fresh_client = app.test_client()
    for _ in range(settings.MAX_FAILED_LOGINS):
        fresh_client.post("/login", data={"email": TEST_EMAIL, "password": "Wrong!Pass-123"})
    response = fresh_client.post(
        "/login", data={"email": TEST_EMAIL, "password": STRONG_PASSWORD})
    assert response.status_code == 401
    assert b"Too many failed attempts" in response.data


def test_logout_requires_post(logged_in_client):
    assert logged_in_client.get("/logout").status_code == 405


def test_logout_ends_session(logged_in_client):
    logged_in_client.post("/logout")
    assert logged_in_client.get("/").status_code == 302


def test_csrf_blocks_post_without_token(tmp_path):
    protected_app = create_app({
        "TESTING": True,
        "DATABASE_PATH": tmp_path / "csrf.db",
        "SECRET_KEY": "test-secret-key",
        "CSRF_ENABLED": True,
    })
    response = protected_app.test_client().post(
        "/login", data={"email": TEST_EMAIL, "password": STRONG_PASSWORD})
    assert response.status_code == 400