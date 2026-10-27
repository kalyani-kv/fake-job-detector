"""Flask application: routes only. The logic lives in src/."""

import logging

from flask import Flask, jsonify, render_template, request

from config import rules, settings
from src.predictor import load_model, predict_fraud_probability
from src.risk_engine import analyze_job
from src.utils import validate_job_input

logger = logging.getLogger(__name__)

LEVEL_CSS_CLASSES = {
    rules.LEVEL_LOW: "low",
    rules.LEVEL_SUSPICIOUS: "medium",
    rules.LEVEL_HIGH: "high",
}

PREVIEW_POSTING = (
    "URGENT HIRING! Work from home data entry internship. "
    "Earn Rs. 50,000 per week. 100% placement guaranteed. "
    "Pay a refundable registration fee of Rs. 999 to confirm your seat. "
    "Limited seats, apply immediately. Contact us on WhatsApp. "
    "Share OTP to verify your profile."
)


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


def register_routes(app):
    @app.get("/")
    def home():
        return render_template("index.html", form={}, errors={})

    @app.get("/about")
    def about():
        return render_template("about.html", rules=rules)

    @app.get("/preview")
    def preview():
        """TEMPORARY: shows the result page with a sample posting."""
        result = analyze_job(PREVIEW_POSTING)
        probability = predict_fraud_probability(app.config["MODEL"], PREVIEW_POSTING)
        ml = {"available": probability is not None, "fraud_probability": probability}
        return render_template(
            "result.html",
            result=result,
            ml=ml,
            level_class=LEVEL_CSS_CLASSES[result["level"]],
            disclaimer=rules.DISCLAIMER,
            job_title="Sample posting",
            company_name="",
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

        rule_result = analyze_job(
            cleaned["description"],
            company_name=cleaned["company_name"],
            company_website=cleaned["company_website"],
            recruiter_email=cleaned["recruiter_email"],
            job_title=cleaned["job_title"],
            salary=cleaned["salary"],
        )
        probability = predict_fraud_probability(
            app.config["MODEL"],
            cleaned["description"],
            cleaned["company_name"],
            cleaned["job_title"],
        )

        return jsonify(
            rules=rule_result,
            ml={
                "available": probability is not None,
                "fraud_probability": None if probability is None else round(probability, 3),
            },
        )


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