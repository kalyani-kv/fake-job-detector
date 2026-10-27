"""Flask application: routes only. The logic lives in src/."""

import logging

from flask import Flask, jsonify, render_template, request

from config import rules, settings
from src.predictor import load_model, predict_fraud_probability
from src.risk_engine import analyze_job
from src.scoring import combine_results
from src.utils import validate_job_input

logger = logging.getLogger(__name__)

LEVEL_CSS_CLASSES = {
    rules.LEVEL_LOW: "low",
    rules.LEVEL_SUSPICIOUS: "medium",
    rules.LEVEL_HIGH: "high",
}


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = settings.MAX_REQUEST_BYTES
    app.config["MODEL"] = load_model(settings.MODEL_PATH)
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


def register_routes(app):
    @app.get("/")
    def home():
        return render_template("index.html", form={}, errors={})

    @app.get("/about")
    def about():
        return render_template("about.html", rules=rules)

    @app.post("/analyze")
    def analyze_page():
        cleaned, errors = validate_job_input(request.form)
        if errors:
            return render_template(
                "index.html", form=request.form, errors=errors), 400

        result, ml_info = run_analysis(app.config["MODEL"], cleaned)
        return render_template(
            "result.html",
            result=result,
            ml=ml_info,
            level_class=LEVEL_CSS_CLASSES[result["level"]],
            disclaimer=rules.DISCLAIMER,
            job_title=cleaned["job_title"],
            company_name=cleaned["company_name"],
        )

    @app.get("/health")
    def health():
        return jsonify(status="ok", ml_model_loaded=app.config["MODEL"] is not None)

    @app.post("/api/analyze")
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
    app.run(debug=settings.DEBUG)