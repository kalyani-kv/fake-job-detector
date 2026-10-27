"""Temporary script: try the API without starting a server."""

from app import create_app

client = create_app().test_client()

GOOD_TEXT = (
    "Acme Technologies Pvt Ltd is hiring a Python intern. Responsibilities: "
    "build features and write tests. Eligibility: final-year CSE students."
)
SCAM_TEXT = (
    "Urgent hiring! Pay a refundable registration fee of Rs. 999. "
    "100% placement guaranteed. Share OTP to verify."
)


def check(title, payload):
    response = client.post("/api/analyze", json=payload)
    body = response.get_json()
    print(f"{title:<22} -> HTTP {response.status_code}", end="  ")
    if response.status_code == 200:
        print(f"rule score {body['rules']['score']} ({body['rules']['level']}), "
              f"ML: {body['ml']}")
    else:
        print(body.get("fields") or body.get("error"))


print("Health:", client.get("/health").get_json())
check("Normal posting", {"description": GOOD_TEXT, "company_name": "Acme"})
check("Scam-style posting", {"description": SCAM_TEXT})
check("Empty description", {"description": "   "})
check("Very long input", {"description": "a " * 10_000})
check("Invalid email", {"description": GOOD_TEXT, "recruiter_email": "not-an-email"})
check("Invalid URL", {"description": GOOD_TEXT, "company_website": "javascript:alert(1)"})
check("Missing fields", {})
print("Wrong method:", client.get("/api/analyze").status_code)