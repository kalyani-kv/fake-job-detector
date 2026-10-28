"""Authentication: passwords, login, lockout, CSRF and login_required."""

import hmac
import os
import re
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import abort, current_app, jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import settings
from src.database import get_connection

PASSWORD_HASH_METHOD = "pbkdf2:sha256:600000"
_DUMMY_HASH = generate_password_hash("not-a-real-password", method=PASSWORD_HASH_METHOD)
_WEAK_PARTS = ("password", "qwerty", "123456", "letmein", "welcome", "admin")
LOCKED_MESSAGE = "Too many failed attempts. Please try again in a few minutes."
GENERIC_LOGIN_ERROR = "Incorrect email or password."


class EmailAlreadyRegistered(Exception):
    pass


# ---- Secret key --------------------------------------------------------

def load_secret_key():
    """Use SECRET_KEY from the environment, else a key saved on first run."""
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key
    path = settings.SECRET_KEY_PATH
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_hex(32)
    path.write_text(key, encoding="utf-8")
    return key


# ---- Passwords ---------------------------------------------------------

def validate_password(password, email=""):
    """Return a list of problems (an empty list means the password is fine)."""
    problems = []
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        problems.append(f"Use at least {settings.MIN_PASSWORD_LENGTH} characters.")
    if len(password) > settings.MAX_PASSWORD_LENGTH:
        problems.append(f"Use at most {settings.MAX_PASSWORD_LENGTH} characters.")
    if not re.search(r"[A-Z]", password):
        problems.append("Add an uppercase letter.")
    if not re.search(r"[a-z]", password):
        problems.append("Add a lowercase letter.")
    if not re.search(r"\d", password):
        problems.append("Add a digit.")
    if not re.search(r"[^A-Za-z0-9]", password):
        problems.append("Add a symbol such as ! or @.")

    lowered = password.lower()
    if any(part in lowered for part in _WEAK_PARTS):
        problems.append("Avoid common words like 'password' or '123456'.")
    name_part = email.split("@")[0].lower() if "@" in email else ""
    if len(name_part) >= 3 and name_part in lowered:
        problems.append("Do not include your email name in the password.")
    return problems


# ---- Users -------------------------------------------------------------

def create_user(db_path, email, password):
    password_hash = generate_password_hash(password, method=PASSWORD_HASH_METHOD)
    created_at = datetime.now(timezone.utc).isoformat()
    try:
        with closing(get_connection(db_path)) as connection:
            with connection:
                cursor = connection.execute(
                    "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                    (email, password_hash, created_at),
                )
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise EmailAlreadyRegistered from None


def authenticate(db_path, email, password):
    """Check credentials. Returns (user_dict, "") or (None, error_message)."""
    now = datetime.now(timezone.utc)
    with closing(get_connection(db_path)) as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        too_long = len(password) > settings.MAX_PASSWORD_LENGTH
        if user is None or too_long:
            # Do the same amount of work so timing does not reveal valid emails
            check_password_hash(_DUMMY_HASH, password[:settings.MAX_PASSWORD_LENGTH])
            return None, GENERIC_LOGIN_ERROR

        if user["locked_until"] and datetime.fromisoformat(user["locked_until"]) > now:
            return None, LOCKED_MESSAGE

        if check_password_hash(user["password_hash"], password):
            with connection:
                connection.execute(
                    "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?",
                    (user["id"],))
            return dict(user), ""

        attempts = user["failed_attempts"] + 1
        locked_until = None
        if attempts >= settings.MAX_FAILED_LOGINS:
            locked_until = (now + timedelta(minutes=settings.LOCKOUT_MINUTES)).isoformat()
            attempts = 0
        with connection:
            connection.execute(
                "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?",
                (attempts, locked_until, user["id"]))
        return None, GENERIC_LOGIN_ERROR


# ---- Sessions ----------------------------------------------------------

def log_in(user_id, email):
    session.clear()              # discard any old session data
    session["user_id"] = user_id
    session["user_email"] = email
    session.permanent = True


def log_out():
    session.clear()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify(error="Please log in first."), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


# ---- CSRF --------------------------------------------------------------

def get_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def verify_csrf():
    """Abort with 400 if the submitted token does not match the session's."""
    if not current_app.config["CSRF_ENABLED"]:
        return
    sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
    expected = session.get("csrf_token", "")
    if not expected or not hmac.compare_digest(sent, expected):
        abort(400)