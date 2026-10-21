"""Helpers that pull structured features (domains, salary) out of text."""

import re
from urllib.parse import urlparse

_NUMBER = r"(\d[\d,]*(?:\.\d+)?)"
_MULTIPLIER = r"(?:\s*(lakhs?|lacs?|lpa|k)\b)?"
_PERIOD = r"(?:\s*(?:/|per\s+|a\s+)\s*(hour|hr|day|week|month|annum|year|pm)\b)?"
_CURRENCY = r"(?<![a-z])(?:rs\.?|inr|₹)\s*"

# Amount that appears near words like "salary" or "earn"
_CONTEXT_AMOUNT = re.compile(
    r"(?:salary|stipend|earn(?:ings?)?|income|ctc|package)\D{0,30}?"
    + _CURRENCY + _NUMBER + _MULTIPLIER + _PERIOD
)
# Amount inside the dedicated salary field (currency symbol optional)
_FIELD_AMOUNT = re.compile("(?:" + _CURRENCY + ")?" + _NUMBER + _MULTIPLIER + _PERIOD)
_FOREIGN_CURRENCY = re.compile(r"[$€£]|\b(?:usd|eur|gbp)\b")

_MULTIPLIER_VALUES = {
    "lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000,
    "lpa": 100_000, "k": 1_000,
}
_PERIOD_TO_MONTHLY = {
    "hour": 160, "hr": 160, "day": 26, "week": 4, "month": 1, "pm": 1,
    "annum": 1 / 12, "year": 1 / 12,
}
_ENTRY_LEVEL_PATTERN = re.compile(
    r"\b(?:intern(?:ship)?|freshers?|entry[\s-]level|trainee|"
    r"no\s+experience|any\s+graduate)\b"
)


def extract_domain(url):
    """Return the host of a URL without 'www.', or '' if it can't be parsed."""
    if not url or not url.strip():
        return ""
    candidate = url.strip().lower()
    if "://" not in candidate:
        candidate = "http://" + candidate
    try:
        host = urlparse(candidate).hostname or ""
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def get_email_domain(email):
    """Return the domain part of an email address, or '' if there is none."""
    if not email or "@" not in email:
        return ""
    return email.rsplit("@", 1)[1].strip().lower()


def domains_match(domain_a, domain_b):
    """True if two domains are equal or one is a subdomain of the other."""
    if not domain_a or not domain_b:
        return False
    return (
        domain_a == domain_b
        or domain_a.endswith("." + domain_b)
        or domain_b.endswith("." + domain_a)
    )


def is_entry_level(text):
    """True if the text describes an internship / fresher style role."""
    return bool(_ENTRY_LEVEL_PATTERN.search(text))


def _to_monthly(number_text, multiplier, period):
    try:
        amount = float(number_text.replace(",", ""))
    except ValueError:
        return None
    amount *= _MULTIPLIER_VALUES.get(multiplier, 1)
    if period is None:
        period = "year" if multiplier == "lpa" else "month"
    return amount * _PERIOD_TO_MONTHLY[period]


def estimate_monthly_salary_inr(salary_field, text):
    """Return the highest pay figure found, converted to INR per month.

    Looks in the salary field and in salary-like phrases inside the text.
    Returns None if nothing can be parsed. Assumes Indian rupees.
    """
    values = []
    field = (salary_field or "").lower()
    if field and not _FOREIGN_CURRENCY.search(field):
        for match in _FIELD_AMOUNT.finditer(field):
            values.append(_to_monthly(*match.groups()))
    for match in _CONTEXT_AMOUNT.finditer(text):
        values.append(_to_monthly(*match.groups()))
    values = [value for value in values if value is not None]
    return max(values) if values else None