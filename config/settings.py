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