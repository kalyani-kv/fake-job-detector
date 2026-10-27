"""Combines the rule-based result with the ML probability."""

from config import rules
from src.risk_engine import build_explanation, classify_risk


def calculate_ml_points(probability):
    """Convert an ML fraud probability (0-1) into extra risk points."""
    if probability is None or probability <= rules.ML_START_PROBABILITY:
        return 0
    share = (probability - rules.ML_START_PROBABILITY) / (1 - rules.ML_START_PROBABILITY)
    return round(share * rules.ML_MAX_POINTS)


def combine_results(rule_result, probability):
    """Return the rule result updated with ML points and the final score."""
    ml_points = calculate_ml_points(probability)
    final_score = min(rule_result["score"] + ml_points, rules.MAX_SCORE)
    level = classify_risk(final_score)

    combined = dict(rule_result)
    combined.update(
        rule_score=rule_result["score"],
        ml_points=ml_points,
        score=final_score,
        level=level,
        explanation=build_explanation(
            level, rule_result["warnings"], rule_result["positive_reduction"]),
    )
    return combined