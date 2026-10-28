"""Application settings (limits and file paths)."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "model.pkl"
DATABASE_PATH = BASE_DIR / "database" / "app.db"

# Input limits
MIN_DESCRIPTION_LENGTH = 20
MAX_DESCRIPTION_LENGTH = 10_000
MAX_SHORT_FIELD_LENGTH = 100     # company name, job title
MAX_SALARY_LENGTH = 50
MAX_EMAIL_LENGTH = 254
MAX_URL_LENGTH = 200
MAX_REQUEST_BYTES = 100 * 1024   # reject requests larger than 100 KB

DEBUG = os.environ.get("FLASK_DEBUG") == "1"
# ---- Authentication and sessions -------------------------------------------
SECRET_KEY_PATH = BASE_DIR / "database" / "secret.key"
COOKIE_SECURE = os.environ.get("FLASK_COOKIE_SECURE") == "1"  # set to 1 on HTTPS
SESSION_HOURS = 8
MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15

POSTING_SOURCES = [
    "LinkedIn", "Naukri", "Indeed", "Internshala", "Company website",
    "College placement portal", "Instagram / Facebook", "WhatsApp",
    "Telegram", "Email / SMS", "Other",
]