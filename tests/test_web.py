"""Tests for the analysis form."""

import pytest

GOOD_TEXT = (
    "Acme Technologies Pvt Ltd is hiring a Python intern. Responsibilities: "
    "build features and write tests. Eligibility: final-year CSE students."
)
SCAM_TEXT = (
    "Urgent hiring! Pay a refundable registration fee of Rs. 999. "
    "100% placement guaranteed. Share OTP to verify."
)
GOOD_FORM = {
    "description": GOOD_TEXT,
    "job_title": "Python Intern",
    "company_name": "Acme Technologies Pvt Ltd",
    "company_website": "acme-example.com",
    "recruiter_email": "careers@acme-example.com",
    "source": "LinkedIn",
    "posting_url": "https://www.linkedin.com/jobs/view/12345",
}


def post_form(client, **changes):
    return client.post("/analyze", data={**GOOD_FORM, **changes})


def test_empty_form_shows_all_required_errors(logged_in_client):
    response = logged_in_client.post("/analyze", data={})
    assert response.status_code == 400
    assert b"Please paste the job description" in response.data
    assert b"Please enter the company website" in response.data
    assert b"Please tell us where you saw this posting" in response.data
    assert b"Please paste the link to the posting" in response.data


@pytest.mark.parametrize("field", [
    "job_title", "company_name", "company_website",
    "recruiter_email", "source", "posting_url",
])
def test_each_required_field_is_enforced(logged_in_client, field):
    response = post_form(logged_in_client, **{field: ""})
    assert response.status_code == 400


def test_salary_is_optional(logged_in_client):
    assert post_form(logged_in_client, salary="").status_code == 200


def test_invalid_email(logged_in_client):
    assert post_form(logged_in_client, recruiter_email="bad").status_code == 400


def test_invalid_company_url(logged_in_client):
    assert post_form(logged_in_client, company_website="javascript:alert(1)").status_code == 400


def test_invalid_posting_url(logged_in_client):
    assert post_form(logged_in_client, posting_url="not a link").status_code == 400


def test_unknown_source_rejected(logged_in_client):
    assert post_form(logged_in_client, source="Hacked").status_code == 400


def test_very_long_input(logged_in_client):
    assert post_form(logged_in_client, description="a " * 10_000).status_code == 400


def test_normal_posting_shows_result_and_source(logged_in_client):
    response = post_form(logged_in_client)
    assert response.status_code == 200
    assert b"Risk score" in response.data
    assert b"LinkedIn" in response.data
    assert b"linkedin.com/jobs/view/12345" in response.data


def test_scam_posting_is_high_risk(logged_in_client):
    response = post_form(logged_in_client, description=SCAM_TEXT)
    assert response.status_code == 200
    assert b"HIGH RISK" in response.data


def test_script_tag_is_escaped(logged_in_client):
    response = post_form(logged_in_client, company_name="<script>alert('xss')</script>")
    assert b"<script>alert" not in response.data
    assert b"&lt;script&gt;" in response.data