"""Input validation helpers. All user input is treated as untrusted."""

import re
from urllib.parse import urlparse

from config import settings

_EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+$"
)
_HOSTNAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9.\-]*[a-z0-9])?$")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize(value):
    """Convert to text, drop control characters and trim whitespace."""
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n")
    return _CONTROL_CHARS.sub("", text).strip()


def is_valid_email(email):
    return len(email) <= settings.MAX_EMAIL_LENGTH and bool(_EMAIL_PATTERN.match(email))


def normalize_url(url):
    """Return a safe http(s) URL, or None if it is not a plausible web address.

    Only checks the shape. It never visits the URL.
    """
    if len(url) > settings.MAX_URL_LENGTH or " " in url:
        return None
    candidate = url if "://" in url else "https://" + url
    try:
        parsed = urlparse(candidate)
        host = (parsed.hostname or "").lower()
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https"):
        return None
    if "." not in host or not _HOSTNAME_PATTERN.match(host):
        return None
    return candidate


def validate_job_input(raw):
    """Validate form/JSON data. Returns (cleaned_values, errors).

    `errors` maps a field name to a message the user can understand.
    """
    errors = {}
    cleaned = {
        "description": sanitize(raw.get("description")),
        "company_name": sanitize(raw.get("company_name")),
        "company_website": sanitize(raw.get("company_website")),
        "recruiter_email": sanitize(raw.get("recruiter_email")),
        "job_title": sanitize(raw.get("job_title")),
        "salary": sanitize(raw.get("salary")),
    }

    description = cleaned["description"]
    if not description:
        errors["description"] = "Please paste the job description."
    elif len(description) < settings.MIN_DESCRIPTION_LENGTH:
        errors["description"] = (
            f"The description is too short to analyze "
            f"(minimum {settings.MIN_DESCRIPTION_LENGTH} characters)."
        )
    elif len(description) > settings.MAX_DESCRIPTION_LENGTH:
        errors["description"] = (
            f"The description is too long "
            f"(maximum {settings.MAX_DESCRIPTION_LENGTH} characters)."
        )

    for field in ("company_name", "job_title"):
        if len(cleaned[field]) > settings.MAX_SHORT_FIELD_LENGTH:
            errors[field] = (
                f"Please keep this under {settings.MAX_SHORT_FIELD_LENGTH} characters."
            )

    if len(cleaned["salary"]) > settings.MAX_SALARY_LENGTH:
        errors["salary"] = (
            f"Please keep this under {settings.MAX_SALARY_LENGTH} characters."
        )

    if cleaned["recruiter_email"] and not is_valid_email(cleaned["recruiter_email"]):
        errors["recruiter_email"] = "Please enter a valid email address."

    if cleaned["company_website"]:
        normalized = normalize_url(cleaned["company_website"])
        if normalized is None:
            errors["company_website"] = "Please enter a valid website address."
        else:
            cleaned["company_website"] = normalized

    return cleaned, errors