"""Rule-based risk engine: finds warning signs and positive signals."""

import re

from config import rules
from src.feature_extraction import (
    domains_match,
    estimate_monthly_salary_inr,
    extract_domain,
    get_email_domain,
    is_entry_level,
)
from src.preprocessing import clean_text

_SENTENCE_BREAKS = ".!?;•|"


def _is_negated(text, match_start):
    """True if a negation word precedes the match in the same sentence."""
    sentence_start = max(text.rfind(ch, 0, match_start) for ch in _SENTENCE_BREAKS) + 1
    window_start = max(sentence_start, match_start - rules.NEGATION_WINDOW)
    return bool(re.search(rules.NEGATION_PATTERN, text[window_start:match_start]))


def _find_first_match(text, patterns):
    """Return the first non-negated match for any pattern, else None."""
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            if not _is_negated(text, match.start()):
                return match.group(0)
    return None


def _matches_any(text, patterns):
    return any(re.search(pattern, text) for pattern in patterns)


def _make_warning(rule_id, rule, evidence):
    return {
        "id": rule_id,
        "label": rule["label"],
        "weight": rule["weight"],
        "severe": rule["severe"],
        "advice": rule["advice"],
        "evidence": evidence,
    }


def detect_text_warnings(text):
    """Check every text-based rule category once."""
    warnings = []
    for rule in rules.TEXT_RULES:
        evidence = _find_first_match(text, rule["patterns"])
        if evidence:
            warnings.append(_make_warning(rule["id"], rule, evidence))
    return warnings


def _is_company_info_missing(text, company_name, company_website):
    if company_name.strip() or extract_domain(company_website):
        return False
    return not re.search(rules.COMPANY_HINT_PATTERN, text)


def detect_field_warnings(text, company_name, company_website, recruiter_email, salary):
    """Check rules that depend on the optional form fields."""
    warnings = []

    email_domain = get_email_domain(recruiter_email)
    if email_domain in rules.FREE_EMAIL_DOMAINS:
        rule = rules.FIELD_RULES["free_email_domain"]
        warnings.append(_make_warning("free_email_domain", rule, email_domain))

    if _is_company_info_missing(text, company_name, company_website):
        rule = rules.FIELD_RULES["missing_company_info"]
        warnings.append(_make_warning(
            "missing_company_info", rule,
            "no company name, website or company details found"))

    monthly_salary = estimate_monthly_salary_inr(salary, text)
    if (
        monthly_salary
        and monthly_salary > rules.ENTRY_LEVEL_MONTHLY_LIMIT_INR
        and is_entry_level(text)
    ):
        rule = rules.FIELD_RULES["suspicious_salary"]
        warnings.append(_make_warning(
            "suspicious_salary", rule,
            f"about Rs. {monthly_salary:,.0f} per month for an entry-level role"))

    return warnings


def detect_positive_signals(text, company_website, recruiter_email):
    """Find signals that make a posting look more professional."""
    positives = []
    word_count = len(text.split())

    for signal in rules.POSITIVE_TEXT_SIGNALS:
        if word_count < signal.get("min_words", 0):
            continue
        if _matches_any(text, signal["patterns"]):
            positives.append({
                "id": signal["id"],
                "label": signal["label"],
                "weight": signal["weight"],
            })

    website_domain = extract_domain(company_website)
    email_domain = get_email_domain(recruiter_email)
    if website_domain and "." in website_domain:
        info = rules.POSITIVE_FIELD_SIGNALS["company_website_provided"]
        positives.append({"id": "company_website_provided", **info})
        if domains_match(website_domain, email_domain):
            info = rules.POSITIVE_FIELD_SIGNALS["email_matches_website"]
            positives.append({"id": "email_matches_website", **info})

    return positives


def calculate_score(warnings, positives):
    """Combine warnings and positives into a 0-100 score.

    Positive signals only lower the score when no severe warning exists.
    Returns (score, reduction_applied).
    """
    raw_score = sum(warning["weight"] for warning in warnings)
    reduction = 0
    if not any(warning["severe"] for warning in warnings):
        positive_total = sum(positive["weight"] for positive in positives)
        reduction = min(positive_total, rules.MAX_POSITIVE_REDUCTION)
    score = max(0, min(raw_score - reduction, rules.MAX_SCORE))
    return score, reduction


def classify_risk(score):
    if score >= rules.HIGH_RISK_THRESHOLD:
        return rules.LEVEL_HIGH
    if score >= rules.SUSPICIOUS_THRESHOLD:
        return rules.LEVEL_SUSPICIOUS
    return rules.LEVEL_LOW


def build_explanation(level, warnings, reduction):
    parts = [rules.LEVEL_SUMMARIES[level]]
    if warnings:
        top_warnings = sorted(warnings, key=lambda w: w["weight"], reverse=True)[:3]
        reasons = "; ".join(w["label"].lower() for w in top_warnings)
        parts.append(f"The score is mainly driven by: {reasons}.")
    if reduction:
        parts.append(f"Positive signals lowered the score by {reduction} points.")
    parts.append(rules.DISCLAIMER)
    return " ".join(parts)


def build_recommendations(warnings):
    """Specific advice for detected warnings first, then the general advice."""
    recommendations = []
    for warning in warnings:
        if warning["advice"] not in recommendations:
            recommendations.append(warning["advice"])
    for advice in rules.BASE_RECOMMENDATIONS:
        if advice not in recommendations:
            recommendations.append(advice)
    return recommendations


def analyze_job(description, company_name="", company_website="",
                recruiter_email="", job_title="", salary=""):
    """Analyze a job posting and return a dictionary describing the risk."""
    if not description or not str(description).strip():
        raise ValueError("Job description cannot be empty.")

    company_name = company_name or ""
    company_website = company_website or ""
    recruiter_email = recruiter_email or ""

    text = clean_text(f"{job_title or ''}. {description}")

    warnings = detect_text_warnings(text)
    warnings += detect_field_warnings(
        text, company_name, company_website, recruiter_email, salary or "")
    positives = detect_positive_signals(text, company_website, recruiter_email)

    score, reduction = calculate_score(warnings, positives)
    level = classify_risk(score)

    return {
        "score": score,
        "level": level,
        "warnings": warnings,
        "positives": positives,
        "positive_reduction": reduction,
        "explanation": build_explanation(level, warnings, reduction),
        "recommendations": build_recommendations(warnings),
    }