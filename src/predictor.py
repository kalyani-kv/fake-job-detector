"""Loads the trained model and returns a fraud probability."""

import logging
from pathlib import Path

import joblib

from src.preprocessing import clean_text

logger = logging.getLogger(__name__)


def load_model(path):
    """Load the saved model. Returns None if it is missing or unreadable."""
    path = Path(path)
    if not path.exists():
        logger.warning("Model file not found at %s. Running with rules only.", path)
        return None
    try:
        return joblib.load(path)
    except Exception:  # a corrupt or version-mismatched file must not crash the app
        logger.exception("Could not load model from %s. Running with rules only.", path)
        return None


def build_model_text(description, company_name="", job_title=""):
    """Combine the user's fields the way the training text was combined."""
    return clean_text(f"{job_title} . {company_name} . {description}")


def predict_fraud_probability(model, description, company_name="", job_title=""):
    """Return the model's probability (0-1) that the posting is fraudulent.

    Returns None when no model is available or prediction fails.
    """
    if model is None:
        return None
    text = build_model_text(description, company_name, job_title)
    try:
        return float(model.predict_proba([text])[0][1])
    except Exception:
        logger.exception("Prediction failed.")
        return None