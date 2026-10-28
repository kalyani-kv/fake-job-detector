"""Flask application: routes only. The logic lives in src/."""

import logging
from datetime import timedelta

from flask import (
    Flask, jsonify, redirect, render_template, request, session, url_for,
)

from config import rules, settings
from src import auth, storage
from src.database import init_db
from src.predictor import load_model, predict_fraud_probability
from src.risk_engine import analyze_job
from src.scoring import combine_results
from src.utils import is_valid_email, sanitize, validate_job_input

logger = logging.getLogger(__name__)

LEVEL_CSS_CLASSES = {
    rules.LEVEL_LOW: "low",
    rules.LEVEL_SUSPICIOUS: "medium",
    rules.LEVEL_HIGH: "high",
}


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=settings.MAX_REQUEST_BYTES,
        SECRET_KEY=auth.load_secret_key(),
        DATABASE_PATH=settings.DATABASE_PATH,
        CSRF_ENABLED=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=settings.COOKIE_SECURE,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=settings.SESSION_HOURS),
        MODEL=load_model(settings.MODEL_PATH),
    )
    if test_config:
        app.config.update(test_config)

    init_db(app.config["DATABASE_PATH"])
    register_hooks(app)
    register_routes(app)
    register_error_handlers(app)
    return app


def _read_request_data():
    """Accept JSON or normal form data. Returns a dict, or None if invalid."""
    if request.is_json:
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else None
    return request.form


def run_analysis(model, cleaned):
    """Run rules + ML on validated input. Returns (result, ml_info)."""
    rule_result = analyze_job(
        cleaned["description"],
        company_name=cleaned["company_name"],
        company_website=cleaned["company_website"],
        recruiter_email=cleaned["recruiter_email"],
        job_title=cleaned["job_title"],
        salary=cleaned["salary"],
    )
    probability = predict_fraud_probability(
        model, cleaned["description"], cleaned["company_name"], cleaned["job_title"])
    result = combine_results(rule_result, probability)
    ml_info = {
        "available": probability is not None,
        "fraud_probability": None if probability is None else round(probability, 3),
    }
    return result, ml_info


def render_form(form, errors, status=200):
    page = render_template(
        "index.html", form=form, errors=errors, sources=settings.POSTING_SOURCES)
    return page, status


def register_hooks(app):
    @app.context_processor
    def inject_template_values():
        return {
            "csrf_token": auth.get_csrf_token,
            "current_email": session.get("user_email"),
        }

    @app.before_request
    def protect_against_csrf():
        if request.method == "POST":
            auth.verify_csrf()

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; form-action 'self'; "
            "object-src 'none'; base-uri 'self'")
        if session.get("user_id"):
            response.headers["Cache-Control"] = "no-store"
        return response


def register_routes(app):
    db_path = lambda: app.config["DATABASE_PATH"]  # noqa: E731

    # ---- Account pages ---------------------------------------------------
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if session.get("user_id"):
            return redirect(url_for("home"))
        if request.method == "GET":
            return render_template("register.html", form={}, errors={})

        email = sanitize(request.form.get("email")).lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        errors = {}
        if not is_valid_email(email):
            errors["email"] = "Please enter a valid email address."
        problems = auth.validate_password(password, email)
        if problems:
            errors["password"] = " ".join(problems)
        elif password != confirm:
            errors["confirm_password"] = "The passwords do not match."

        if not errors:
            try:
                user_id = auth.create_user(db_path(), email, password)
            except auth.EmailAlreadyRegistered:
                errors["email"] = "Could not create the account. Try logging in instead."
            else:
                auth.log_in(user_id, email)
                return redirect(url_for("home"))
        return render_template("register.html", form={"email": email}, errors=errors), 400

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("user_id"):
            return redirect(url_for("home"))
        if request.method == "GET":
            return render_template("login.html", form={}, error="")

        email = sanitize(request.form.get("email")).lower()
        password = request.form.get("password", "")
        user, message = auth.authenticate(db_path(), email, password)
        if user is None:
            logger.warning("Failed login attempt from %s", request.remote_addr)
            return render_template("login.html", form={"email": email}, error=message), 401
        auth.log_in(user["id"], user["email"])
        return redirect(url_for("home"))

    @app.post("/logout")
    def logout():
        auth.log_out()
        return redirect(url_for("login"))

    # ---- Main pages (login required) ----------------------------------------
    @app.get("/")
    @auth.login_required
    def home():
        return render_form({}, {})

    @app.get("/about")
    def about():
        return render_template("about.html", rules=rules)

    @app.get("/dashboard")
    @auth.login_required
    def dashboard():
        stats = storage.get_dashboard_stats(db_path(), session["user_id"])
        recent = storage.get_recent_analyses(db_path(), session["user_id"], limit=10)
        return render_template("dashboard.html", stats=stats, recent=recent)

    @app.post("/analyze")
    @auth.login_required
    def analyze_page():
        cleaned, errors = validate_job_input(request.form)
        if errors:
            return render_form(request.form, errors, 400)

        result, ml_info = run_analysis(app.config["MODEL"], cleaned)
        try:
            storage.save_analysis(
                db_path(), session["user_id"], cleaned, result, ml_info)
        except Exception:  # saving must never break the result page
            logger.exception("Could not save the analysis")
        return render_template(
            "result.html",
            result=result,
            ml=ml_info,
            level_class=LEVEL_CSS_CLASSES[result["level"]],
            disclaimer=rules.DISCLAIMER,
            details=cleaned,
        )

    # ---- API -------------------------------------------------------------
    @app.get("/health")
    def health():
        return jsonify(status="ok", ml_model_loaded=app.config["MODEL"] is not None)

    @app.post("/api/analyze")
    @auth.login_required
    def api_analyze():
        raw = _read_request_data()
        if raw is None:
            return jsonify(error="Request body must be valid JSON or form data."), 400

        cleaned, errors = validate_job_input(raw)
        if errors:
            return jsonify(error="Invalid input.", fields=errors), 400

        result, ml_info = run_analysis(app.config["MODEL"], cleaned)
        return jsonify(result=result, ml=ml_info)


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(_error):
        return ("Security check failed or the request was invalid. "
                "Please go back, refresh the page and try again."), 400

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(error="Page not found."), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify(error="Method not allowed."), 405

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify(error="The submitted text is too large."), 413

    @app.errorhandler(500)
    def server_error(_error):
        logger.exception("Unhandled server error")
        return jsonify(error="Something went wrong. Please try again."), 500


app = create_app()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="127.0.0.1", debug=settings.DEBUG)