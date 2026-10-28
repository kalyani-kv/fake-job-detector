"""Tests for the dashboard."""

from src import storage
from tests.conftest import STRONG_PASSWORD
from tests.test_web import GOOD_FORM, SCAM_TEXT


def test_dashboard_requires_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_empty_dashboard_shows_message(logged_in_client):
    response = logged_in_client.get("/dashboard")
    assert response.status_code == 200
    assert b"not analyzed any postings yet" in response.data


def test_dashboard_counts(app, logged_in_client):
    logged_in_client.post("/analyze", data=GOOD_FORM)
    logged_in_client.post("/analyze", data={**GOOD_FORM, "description": SCAM_TEXT})

    stats = storage.get_dashboard_stats(app.config["DATABASE_PATH"], 1)
    assert stats["total"] == 2
    assert stats["high"] == 1
    assert stats["low"] == 1
    assert stats["top_warnings"][0][1] >= 1

    page = logged_in_client.get("/dashboard")
    assert b"Jobs analyzed" in page.data
    assert b"Payment or fee requested" in page.data


def test_users_only_see_their_own_data(app, logged_in_client):
    logged_in_client.post("/analyze", data=GOOD_FORM)

    other = app.test_client()
    other.post("/register", data={
        "email": "other@example.com",
        "password": STRONG_PASSWORD,
        "confirm_password": STRONG_PASSWORD,
    })
    assert b"not analyzed any postings yet" in other.get("/dashboard").data


def test_dashboard_escapes_job_title(logged_in_client):
    logged_in_client.post(
        "/analyze", data={**GOOD_FORM, "job_title": "<script>alert(1)</script>"})
    page = logged_in_client.get("/dashboard")
    assert b"<script>alert" not in page.data
    assert b"&lt;script&gt;" in page.data