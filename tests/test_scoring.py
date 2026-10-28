"""Tests for hybrid scoring."""

import pytest

from config import rules
from src.scoring import calculate_ml_points, combine_results


@pytest.mark.parametrize("probability, expected", [
    (None, 0), (0.0, 0), (0.5, 0), (0.75, 15), (1.0, 30),
])
def test_ml_points(probability, expected):
    assert calculate_ml_points(probability) == expected


def test_ml_cannot_lower_rule_score():
    rule_result = {"score": 40, "warnings": [], "positive_reduction": 0}
    assert combine_results(rule_result, 0.01)["score"] == 40


def test_combined_score_is_capped():
    rule_result = {"score": 95, "warnings": [], "positive_reduction": 0}
    assert combine_results(rule_result, 1.0)["score"] == rules.MAX_SCORE