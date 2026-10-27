"""Configuration for the rule-based risk engine.

To tune the engine, edit the values in this file. No logic lives here.
"""

# ---- Score thresholds --------------------------------------------------
MAX_SCORE = 100
SUSPICIOUS_THRESHOLD = 30   # score >= 30 -> SUSPICIOUS
HIGH_RISK_THRESHOLD = 60    # score >= 60 -> HIGH RISK

LEVEL_LOW = "LOW RISK"
LEVEL_SUSPICIOUS = "SUSPICIOUS"
LEVEL_HIGH = "HIGH RISK"

# ---- Negation handling -------------------------------------------------
# A match is ignored if one of these words appears shortly before it,
# in the same sentence ("we never charge a registration fee").
NEGATION_WINDOW = 40
NEGATION_PATTERN = r"\b(?:no|never|not|without|zero|nor)\b|n't|free\s+of"

# ---- Rules that search the posting text --------------------------------
# Each category fires at most once. "severe" categories also stop
# positive signals from lowering the score.
TEXT_RULES = [
    {
        "id": "financial_request",
        "label": "Payment or fee requested",
        "weight": 35,
        "severe": True,
        "patterns": [
            r"registration\s+(?:fees?|charges?|amount)",
            r"processing\s+fees?",
            r"security\s+deposit",
            r"training\s+fees?",
            r"pay\s+to\s+apply",
            r"payment\s+(?:is\s+)?required",
            r"refundable\s+(?:fee|deposit|amount)",
            r"deposit\s+(?:some\s+)?money",
            r"(?:joining|admission|application|kit|uniform|verification)\s+fees?",
            r"pay\s+(?:rs\.?|inr|₹)\s*\d[\d,]*",
        ],
        "advice": "Do not pay any registration, training or security fee. "
                  "Genuine employers do not charge candidates to hire them.",
    },
    {
        "id": "sensitive_info_request",
        "label": "Request for sensitive information",
        "weight": 35,
        "severe": True,
        "patterns": [
            r"\botp\b",
            r"bank\s+password",
            r"upi\s+pin",
            r"atm\s+pin",
            r"\bcvv\b",
            r"(?:credit|debit)\s+card\s+(?:details|number)",
            r"login\s+credentials",
            r"net\s*banking\s+(?:password|details|credentials)",
        ],
        "advice": "Never share OTPs, UPI/ATM PINs, passwords or card details. "
                  "No genuine recruiter needs them.",
    },
    {
        "id": "guaranteed_job_claim",
        "label": "Guaranteed job or placement claim",
        "weight": 20,
        "severe": False,
        "patterns": [
            r"guaranteed\s+(?:job|placement|selection|internship)",
            r"100\s*%\s+(?:job\s+)?(?:placement|guarantee(?:d)?)",
            r"(?:job|placement|selection)\s+guaranteed",
            r"assured\s+(?:placement|job|selection)",
        ],
        "advice": "Be careful with 'guaranteed job' promises. "
                  "Real hiring always involves an evaluation.",
    },
    {
        "id": "urgency_language",
        "label": "Urgency or pressure language",
        "weight": 10,
        "severe": False,
        "patterns": [
            r"apply\s+immediately",
            r"limited\s+(?:seats?|slots?|vacanc(?:y|ies))",
            r"urgent(?:ly)?\s+hiring",
            r"act\s+now",
            r"today\s+only",
            r"hurry\s+up",
            r"offer\s+(?:expires|ends)",
        ],
        "advice": "Do not let urgency rush you. Take time to verify the offer.",
    },
    {
        "id": "suspicious_contact_method",
        "label": "WhatsApp/Telegram-based recruitment",
        "weight": 15,
        "severe": False,
        "patterns": [
            r"(?:contact|message|join|apply\s+(?:via|on|through))\s+(?:us\s+)?"
            r"(?:on\s+|via\s+|through\s+)?(?:telegram|whatsapp)",
            r"whatsapp\s+(?:only|number|no\.?)",
            r"telegram\s+(?:channel|group|only|id)",
        ],
        "advice": "Be cautious when recruitment happens only on WhatsApp or "
                  "Telegram. Ask for an official company email.",
    },
]

# ---- Rules that use the optional form fields ----------------------------
FIELD_RULES = {
    "free_email_domain": {
        "label": "Recruiter uses a free personal email address",
        "weight": 8,
        "severe": False,
        "advice": "Prefer recruiters who email from the company's own domain.",
    },
    "missing_company_info": {
        "label": "No clear company information",
        "weight": 10,
        "severe": False,
        "advice": "Look up the company independently: website, LinkedIn page "
                  "and reviews.",
    },
    "suspicious_salary": {
        "label": "Unrealistic pay for an entry-level role",
        "weight": 10,
        "severe": False,
        "advice": "Compare the pay with typical stipends for similar roles.",
    },
}

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.co.in", "outlook.com", "hotmail.com",
    "rediffmail.com", "ymail.com", "proton.me", "protonmail.com",
    "live.com", "aol.com",
}

# Words that suggest the text names a real company (used only as a hint)
COMPANY_HINT_PATTERN = (
    r"\b(?:pvt\.?\s*ltd|private\s+limited|ltd|llp|inc\.?|llc|"
    r"corporation|technologies|solutions)\b"
)

# Entry-level roles paying more than this per month look suspicious (INR)
ENTRY_LEVEL_MONTHLY_LIMIT_INR = 100_000

# ---- Positive signals ---------------------------------------------------
POSITIVE_TEXT_SIGNALS = [
    {
        "id": "detailed_responsibilities",
        "label": "Detailed job responsibilities",
        "weight": 5,
        "min_words": 80,
        "patterns": [r"responsibilit"],
    },
    {
        "id": "qualifications_listed",
        "label": "Qualifications or eligibility listed",
        "weight": 3,
        "patterns": [r"\b(?:qualifications?|eligibility|requirements?|skills\s+required)\b"],
    },
    {
        "id": "selection_process",
        "label": "Selection process described",
        "weight": 3,
        "patterns": [
            r"\b(?:interview|online\s+assessment|technical\s+round|hr\s+round|aptitude\s+test)\b"
        ],
    },
]

POSITIVE_FIELD_SIGNALS = {
    "company_website_provided": {
        "label": "Company website provided (not verified)",
        "weight": 3,
    },
    "email_matches_website": {
        "label": "Recruiter email matches the company website domain",
        "weight": 5,
    },
}

# Positive signals can lower the score by at most this many points
MAX_POSITIVE_REDUCTION = 15

# ---- Text shown to the user ---------------------------------------------
LEVEL_SUMMARIES = {
    LEVEL_LOW: "This posting shows few of the common warning signs.",
    LEVEL_SUSPICIOUS: "This posting has some warning signs, so treat it "
                      "carefully until you verify it.",
    LEVEL_HIGH: "This posting matches several patterns commonly seen in "
                "fake job offers.",
}

DISCLAIMER = (
    "This score is a risk indicator based on detected signals. It is not "
    "proof that a job is real or fake."
)

BASE_RECOMMENDATIONS = [
    "Verify the company independently through its official website.",
    "Contact the company through official channels, not only the contact "
    "given in the posting.",
    "Do not share OTPs, UPI PINs, passwords or banking credentials.",
]
# ---- Hybrid scoring (rules + machine learning) ---------------------------
# ML adds points only when its fraud probability is above ML_START_PROBABILITY.
# At probability 1.0 it adds ML_MAX_POINTS. It never lowers the rule score.
ML_START_PROBABILITY = 0.5
ML_MAX_POINTS = 30