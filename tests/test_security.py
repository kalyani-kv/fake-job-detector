"""Security regression tests."""

from tests.test_web import GOOD_FORM


def test_security_headers_present(client):
    response = client.get("/login")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "object-src 'none'" in csp


def test_logged_in_pages_are_not_cached(logged_in_client):
    response = logged_in_client.get("/dashboard")
    assert response.headers["Cache-Control"] == "no-store"


def test_session_cookie_flags(client):
    client.post("/register", data={
        "email": "cookie@example.com",
        "password": "Str0ng!Pass-Word",
        "confirm_password": "Str0ng!Pass-Word",
    })
    cookie = client.get_cookie("session")
    assert cookie is not None
    assert cookie.http_only is True
    assert cookie.same_site == "Lax"


def test_no_stack_trace_on_unknown_page(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert b"Traceback" not in response.data


def test_sql_injection_text_is_stored_harmlessly(logged_in_client, app):
    payload = "x'); DROP TABLE users;--"
    response = logged_in_client.post("/analyze", data={**GOOD_FORM, "job_title": payload})
    assert response.status_code == 200
    assert logged_in_client.get("/dashboard").status_code == 200


def test_pasted_html_is_not_rendered(logged_in_client):
    form = {**GOOD_FORM, "description": GOOD_FORM["description"] + " <img src=x onerror=alert(1)>"}
    response = logged_in_client.post("/analyze", data=form)
    assert b"<img src=x" not in response.data