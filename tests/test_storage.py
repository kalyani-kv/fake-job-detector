"""Tests for saving analyses."""

import json
import sqlite3

from tests.test_web import GOOD_FORM, SCAM_TEXT


def read_rows(app, query="SELECT * FROM analyses"):
    connection = sqlite3.connect(app.config["DATABASE_PATH"])
    connection.row_factory = sqlite3.Row
    rows = connection.execute(query).fetchall()
    connection.close()
    return rows


def test_analysis_is_saved(app, logged_in_client):
    logged_in_client.post("/analyze", data=GOOD_FORM)
    rows = read_rows(app)

    assert len(rows) == 1
    assert rows[0]["job_title"] == "Python Intern"
    assert rows[0]["source"] == "LinkedIn"
    assert rows[0]["user_id"] == 1


def test_warning_signs_saved_as_json(app, logged_in_client):
    logged_in_client.post("/analyze", data={**GOOD_FORM, "description": SCAM_TEXT})
    row = read_rows(app)[0]

    labels = json.loads(row["warning_signs"])
    assert "Payment or fee requested" in labels
    assert row["risk_level"] == "HIGH RISK"


def test_recruiter_email_is_not_stored(app, logged_in_client):
    logged_in_client.post("/analyze", data=GOOD_FORM)
    columns = [row["name"] for row in read_rows(app, "PRAGMA table_info(analyses)")]

    assert "recruiter_email" not in columns


def test_invalid_form_is_not_saved(app, logged_in_client):
    logged_in_client.post("/analyze", data={})
    assert read_rows(app) == []