"""Tests for hybrid scoring and the web routes."""

import pytest

from app import create_app
from config import rules
from src.scoring import calculate_ml_points, combine_results

SCAM_FORM = {
    "description": (
        "Urgent hiring! Pay a refundable registration fee of Rs. 999. "
        "100% placement guaranteed. Share OTP to verify."
    ),
    "company_name": "Test Co",
}
GOOD_TEXT = (
    "Acme Technologies Pvt Ltd is hiring a Python intern. Responsibilities: "
    "build features and write tests. Eligibility: final-year CSE students."
)


@pytest.fixture
def client():
    return create_app().test_client()


@pytest.mark.parametrize("probability, expected", [
    (None, 0), (0.0, 0), (0.5, 0), (0.75, 15), (1.0, 30),
])
def test_ml_points(probability, expected):
    assert calculate_ml_points(probability) == expected


def test_ml_cannot_lower_rule_score():
    rule_result = {"score": 40, "warnings": [], "positive_reduction": 0}
    combined = combine_results(rule_result, 0.01)
    assert combined["score"] == 40


def test_combined_score_is_capped():
    rule_result = {"score": 95, "warnings": [], "positive_reduction": 0}
    assert combine_results(rule_result, 1.0)["score"] == rules.MAX_SCORE


def test_empty_form_shows_error(client):
    response = client.post("/analyze", data={"description": ""})
    assert response.status_code == 400
    assert b"Please paste the job description" in response.data


def test_invalid_email_form(client):
    response = client.post(
        "/analyze", data={"description": GOOD_TEXT, "recruiter_email": "bad"})
    assert response.status_code == 400


def test_invalid_url_form(client):
    response = client.post(
        "/analyze", data={"description": GOOD_TEXT, "company_website": "javascript:alert(1)"})
    assert response.status_code == 400


def test_very_long_input(client):
    response = client.post("/analyze", data={"description": "a " * 10_000})
    assert response.status_code == 400


def test_normal_posting_shows_result(client):
    response = client.post("/analyze", data={"description": GOOD_TEXT})
    assert response.status_code == 200
    assert b"Risk score" in response.data


def test_scam_posting_is_high_risk(client):
    response = client.post("/analyze", data=SCAM_FORM)
    assert response.status_code == 200
    assert b"HIGH RISK" in response.data


def test_script_tag_is_escaped(client):
    form = dict(SCAM_FORM, company_name="<script>alert('xss')</script>")
    response = client.post("/analyze", data=form)
    assert b"<script>alert" not in response.data
    assert b"&lt;script&gt;" in response.data