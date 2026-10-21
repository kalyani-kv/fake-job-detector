"""Tests for the rule-based risk engine."""

import pytest

from config import rules
from src.risk_engine import analyze_job, classify_risk

LEGIT_POSTING = (
    "Acme Technologies Pvt Ltd is hiring a Software Engineering Intern for "
    "our Bengaluru office. Key responsibilities: develop and test features "
    "in Python and Flask, write unit tests, fix bugs reported by the team, "
    "and document your work for code reviews. Eligibility: final-year B.Tech "
    "or B.E. students in CSE or IT with knowledge of Python, SQL and Git. "
    "Selection process: an online assessment, a technical interview and an "
    "HR round. We never charge any fee at any stage of the hiring process. "
    "Stipend: Rs. 25,000 per month. Send your resume to "
    "careers@acme-example.com."
)

SCAM_POSTING = (
    "URGENT HIRING! Work from home data entry internship. "
    "Earn Rs. 50,000 per week. 100% placement guaranteed. "
    "Pay a refundable registration fee of Rs. 999 to confirm your seat. "
    "Limited seats, apply immediately. Contact us on WhatsApp. "
    "Share OTP to verify your profile."
)


def warning_ids(result):
    """Return the set of warning IDs found in a result."""
    return {warning["id"] for warning in result["warnings"]}


# ---- Legitimate postings ------------------------------------------------

def test_legitimate_posting_is_low_risk():
    result = analyze_job(
        LEGIT_POSTING,
        company_name="Acme Technologies Pvt Ltd",
        company_website="https://www.acme-example.com",
        recruiter_email="careers@acme-example.com",
    )
    positive_ids = {positive["id"] for positive in result["positives"]}

    assert result["score"] == 0
    assert result["level"] == rules.LEVEL_LOW
    assert result["warnings"] == []
    assert "email_matches_website" in positive_ids


def test_negated_fee_is_not_flagged():
    text = (
        "Acme Technologies Pvt Ltd is hiring an analyst. "
        "We never charge a registration fee at any stage."
    )
    result = analyze_job(text, company_name="Acme Technologies Pvt Ltd")

    assert "financial_request" not in warning_ids(result)
    assert result["score"] == 0


# ---- Single-signal scams ------------------------------------------------

def test_registration_fee_scam():
    text = "Software trainee required. Pay a registration fee of Rs. 500 to confirm your slot."
    result = analyze_job(text, company_name="ABC Pvt Ltd")

    assert "financial_request" in warning_ids(result)
    assert result["score"] == 35
    assert result["level"] == rules.LEVEL_SUSPICIOUS


def test_guaranteed_job_scam():
    text = "Acme Technologies Pvt Ltd offers 100% placement guaranteed after our course. Join now."
    result = analyze_job(text, company_name="Acme Technologies Pvt Ltd")

    assert "guaranteed_job_claim" in warning_ids(result)
    assert result["score"] == 20


def test_sensitive_information_scam():
    text = "Share your OTP and UPI PIN to complete verification."
    result = analyze_job(text, company_name="ABC Pvt Ltd")

    assert "sensitive_info_request" in warning_ids(result)
    assert result["score"] == 35
    assert result["level"] == rules.LEVEL_SUSPICIOUS


def test_urgency_scam():
    text = "Urgent hiring! Apply immediately, limited seats."
    result = analyze_job(text, company_name="ABC Pvt Ltd")

    assert "urgency_language" in warning_ids(result)
    assert result["score"] == 10


# ---- Combinations -------------------------------------------------------

def test_multiple_warning_signs_reach_high_risk():
    text = (
        "Guaranteed job for all. Pay a processing fee of Rs. 1000. "
        "Apply immediately."
    )
    result = analyze_job(text, company_name="ABC Pvt Ltd")

    assert warning_ids(result) == {
        "financial_request", "guaranteed_job_claim", "urgency_language"
    }
    assert result["score"] == 65
    assert result["level"] == rules.LEVEL_HIGH


def test_all_signals_score_is_capped_at_100():
    result = analyze_job(SCAM_POSTING)

    expected = {
        "financial_request", "sensitive_info_request", "guaranteed_job_claim",
        "urgency_language", "suspicious_contact_method",
    }
    assert expected <= warning_ids(result)
    assert result["score"] == rules.MAX_SCORE
    assert result["level"] == rules.LEVEL_HIGH


# ---- Design rules from Step 3 -------------------------------------------

def test_positive_signals_do_not_excuse_a_fee():
    text = LEGIT_POSTING + " A refundable registration fee of Rs. 2000 must be paid before joining."
    result = analyze_job(
        text,
        company_name="Acme Technologies Pvt Ltd",
        company_website="https://www.acme-example.com",
        recruiter_email="careers@acme-example.com",
    )

    assert "financial_request" in warning_ids(result)
    assert result["positive_reduction"] == 0
    assert result["score"] == 35


def test_repeated_keyword_counts_once():
    text = "Registration fee is required. " * 5
    result = analyze_job(text, company_name="ABC Pvt Ltd")

    financial = [w for w in result["warnings"] if w["id"] == "financial_request"]
    assert len(financial) == 1
    assert result["score"] == 35


def test_free_email_domain_is_flagged():
    result = analyze_job(
        "Marketing intern needed for our team.",
        company_name="Acme",
        recruiter_email="hr.jobs@gmail.com",
    )

    assert "free_email_domain" in warning_ids(result)
    assert result["score"] == 8


def test_high_pay_for_entry_level_role_is_flagged():
    text = "Data entry intern wanted. Earn Rs. 1,50,000 per month from home."
    result = analyze_job(text, company_name="ABC Pvt Ltd")

    assert "suspicious_salary" in warning_ids(result)
    assert result["score"] == 10


def test_high_pay_for_senior_role_is_not_flagged():
    text = "Senior software architect with 10 years of experience. Salary Rs. 2,00,000 per month."
    result = analyze_job(text, company_name="ABC Pvt Ltd")

    assert "suspicious_salary" not in warning_ids(result)


def test_missing_company_info_is_flagged():
    result = analyze_job("Need staff for data entry work. Join our team.")

    assert "missing_company_info" in warning_ids(result)
    assert result["score"] == 10


# ---- Input handling and output shape ------------------------------------

@pytest.mark.parametrize("bad_input", ["", "   ", None])
def test_empty_description_raises_error(bad_input):
    with pytest.raises(ValueError):
        analyze_job(bad_input)


def test_result_has_expected_structure():
    result = analyze_job(SCAM_POSTING)
    expected_keys = {
        "score", "level", "warnings", "positives",
        "explanation", "recommendations",
    }

    assert expected_keys <= set(result)
    assert "not proof" in result["explanation"]
    assert len(result["recommendations"]) >= 3


@pytest.mark.parametrize("score, expected_level", [
    (0, rules.LEVEL_LOW),
    (29, rules.LEVEL_LOW),
    (30, rules.LEVEL_SUSPICIOUS),
    (59, rules.LEVEL_SUSPICIOUS),
    (60, rules.LEVEL_HIGH),
    (100, rules.LEVEL_HIGH),
])
def test_risk_level_boundaries(score, expected_level):
    assert classify_risk(score) == expected_level