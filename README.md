# Fake Job / Internship Detector

A Flask web application that analyzes a job or internship posting and estimates
whether it looks **safe, suspicious or high risk**, using transparent rules
combined with a lightweight machine-learning model.

> **Important:** This is a risk-assessment tool, not proof. A low score does not
> prove a job is genuine and a high score does not prove it is fake. Always
> verify a company independently.

## Problem statement

Students and fresh graduates are frequent targets of fake job offers that ask
for registration fees, "security deposits", OTPs or banking details. These
postings share recognizable patterns, but they are hard to spot under pressure.

## Motivation

I built this to give job seekers a quick, explainable second opinion before
they apply or pay anything. Every score comes with the exact reasons behind it.

## Features

- Rule-based detection of financial requests, sensitive-information requests,
  guaranteed-job claims, urgency language, WhatsApp/Telegram recruitment,
  free-email recruiters, missing company information and unrealistic
  entry-level pay
- Negation handling ("we never charge a registration fee" is not flagged)
- TF-IDF + Logistic Regression text model as a second signal
- Hybrid score with a full breakdown shown on the result page
- Warning signs, positive signals, explanation and recommended actions
- Registration and login with hashed passwords, lockout and CSRF protection
- Per-user history saved in SQLite and a dashboard with counts and charts
- Required source and posting link, stored as text and never opened

## System architecture

```
Browser -> Flask (app.py: routes only)
              |-> utils.py        input validation and sanitizing
              |-> risk_engine.py  configurable rules -> rule score (0-100)
              |-> predictor.py    TF-IDF + Logistic Regression -> probability
              |-> scoring.py      hybrid score
              |-> storage.py      SQLite (users, analyses)
              -> Jinja templates  result page, dashboard
```

Rule definitions and weights live in `config/rules.py`, so they can be tuned
without changing any logic.

## Technologies

Python, Flask, scikit-learn, pandas, numpy, SQLite, HTML, CSS, JavaScript,
pytest.

## Dataset

- **Source:** EMSCAD, distributed on Kaggle as "Real / Fake Job Posting
  Prediction" (`fake_job_postings.csv`). The file is not included in this
  repository because of its license terms. Download it and place it in `data/`.
- **Rows:** 17,880 postings (17,014 real, 866 fraudulent)
- **Fraudulent share:** 4.8%
- **Duplicates removed:** 2,008 exact-text duplicates (15,872 rows used for
  modelling), so the same posting cannot appear in both train and test
- **Target:** `fraudulent` (1 = fake)
- **Text columns used:** title, company_profile, description, requirements,
  benefits
- **Missing values:** common in structured columns such as `required_education`
  (8,105 missing) and `required_experience` (7,050 missing), so the model uses
  only the text columns
- **Split:** 80/20, stratified, fixed random seed (3,175 test postings, 143
  fraudulent)

The dataset is mostly English-language postings and is heavily imbalanced. It
does not capture many India-specific scam patterns (UPI, WhatsApp hiring), which
is why the rule engine is the core of the system.

## Machine learning approach

TF-IDF (unigrams and bigrams) feeding a Logistic Regression classifier with
`class_weight="balanced"` to handle class imbalance. Logistic Regression was
chosen because it is fast, interpretable and easy to explain. Accuracy alone is
misleading on imbalanced data, so precision, recall and F1 are reported.

| Metric (test set, threshold 0.5) | Value |
|---|---|
| Baseline accuracy (always "real") | 0.955 |
| Accuracy | 0.978 |
| Precision (fraudulent) | 0.712 |
| Recall (fraudulent) | 0.846 |
| F1 (fraudulent) | 0.773 |
| PR-AUC | 0.867 |
| ROC-AUC | 0.973 |

Confusion matrix on the held-out test set of 3,175 postings:

| | Predicted real | Predicted fake |
|---|---|---|
| Actually real | 2983 | 49 |
| Actually fake | 22 | 121 |

The model's precision rises from 0.71 at threshold 0.5 to 0.89 at 0.7, with
recall falling from 0.85 to 0.73.

These figures describe EMSCAD-style postings only. They do not show how well the
model handles Indian-style scams.

## Risk-scoring methodology

```
rule score  = sum of weights of triggered warning categories (each counts once)
              minus positive signals (max 15; not applied if a payment or
              sensitive-information request was found)
ML points   = 0 if probability <= 0.5, else (p - 0.5) / 0.5 x 30
final score = min(rule score + ML points, 100)
```

| Category | Points |
|---|---|
| Payment or fee requested | 35 |
| Sensitive information requested | 35 |
| Guaranteed job claim | 20 |
| WhatsApp/Telegram recruitment | 15 |
| Urgency language | 10 |
| No company information | 10 |
| Unrealistic entry-level pay | 10 |
| Free personal email | 8 |

Levels: 0-29 Low risk, 30-59 Suspicious, 60-100 High risk.

The ML model can only add points, never remove them, because it has weak
evidence on the scam styles this tool targets. Even at probability 0.9 it adds
only 24 points, so it cannot flag a posting as high risk on its own.

## Security

CSRF tokens, PBKDF2-SHA256 password hashing, account lockout, generic login
errors, parameterized SQL, auto-escaped templates, Content-Security-Policy,
URL validation (http/https only), request size limits, no stack traces shown to
users. Links are never opened or fetched.

## Screenshots

<!-- Add: home form, result page, dashboard -->

## Installation

```powershell
git clone <your-repo-url>
cd fake-job-detector
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## How to run

1. Download `fake_job_postings.csv` from Kaggle into `data/`.
2. Train and evaluate:
   ```powershell
   python train_model.py
   python evaluate_model.py
   ```
3. Start the app:
   ```powershell
   python app.py
   ```
4. Open http://127.0.0.1:5000/ and create an account.
5. Run the tests: `python -m pytest -v` (79 tests pass).

## Example

Input: "Urgent hiring! Pay a refundable registration fee of Rs. 999. 100%
placement guaranteed. Share OTP to verify."

Output: **HIGH RISK**, with warnings for payment request, sensitive-information
request, guaranteed-job claim and urgency, plus recommended actions such as
"do not pay any fee".

## Limitations

- Only reads pasted text; it does not verify websites, emails or companies
- Scammers change wording, so new tricks may be missed
- Genuine postings can be flagged, and some scams can score low
- The ML model was trained on an English-language academic dataset and has not
  been evaluated on Indian-style scams
- No two-factor authentication, password reset or IP-based rate limiting
- Flask's development server is not for production use
- SQLite on free hosting may not persist between deployments

## Future improvements

- Two-factor authentication and password reset
- Evaluate on a labeled set of Indian-style postings
- Multilingual support (Hindi, Telugu)
- Browser extension and URL/domain-age checks
- PostgreSQL for production deployment
- Admin tools to tune rules from user feedback