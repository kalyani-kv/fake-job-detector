"""Saving and reading analyses. Every query is scoped to one user."""

import json
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone

from config import rules
from src.database import get_connection

TOP_WARNINGS_COUNT = 5


def save_analysis(db_path, user_id, details, result, ml_info):
    """Store one analysis and return its id."""
    warning_labels = [warning["label"] for warning in result["warnings"]]
    with closing(get_connection(db_path)) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO analyses (
                    user_id, job_title, company_name, description, source,
                    posting_url, risk_score, risk_level, warning_signs,
                    ml_prediction, analyzed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    details["job_title"],
                    details["company_name"],
                    details["description"],
                    details["source"],
                    details["posting_url"],
                    result["score"],
                    result["level"],
                    json.dumps(warning_labels),
                    ml_info["fraud_probability"],
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return cursor.lastrowid


def get_recent_analyses(db_path, user_id, limit=20):
    """Return the user's most recent analyses, newest first."""
    with closing(get_connection(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT id, job_title, company_name, risk_score, risk_level,
                   source, analyzed_at
            FROM analyses
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def get_dashboard_stats(db_path, user_id):
    """Return totals, risk-level counts and the most common warning signs."""
    with closing(get_connection(db_path)) as connection:
        level_rows = connection.execute(
            "SELECT risk_level, COUNT(*) AS total FROM analyses "
            "WHERE user_id = ? GROUP BY risk_level",
            (user_id,),
        ).fetchall()
        warning_rows = connection.execute(
            "SELECT warning_signs FROM analyses WHERE user_id = ?",
            (user_id,),
        ).fetchall()

    level_counts = {row["risk_level"]: row["total"] for row in level_rows}

    warning_counter = Counter()
    for row in warning_rows:
        try:
            warning_counter.update(json.loads(row["warning_signs"]))
        except (TypeError, ValueError):
            continue  # skip a damaged row instead of breaking the page

    return {
        "total": sum(level_counts.values()),
        "high": level_counts.get(rules.LEVEL_HIGH, 0),
        "suspicious": level_counts.get(rules.LEVEL_SUSPICIOUS, 0),
        "low": level_counts.get(rules.LEVEL_LOW, 0),
        "top_warnings": warning_counter.most_common(TOP_WARNINGS_COUNT),
    }