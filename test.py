"""Temporary script to try the risk engine by hand."""

from src.risk_engine import analyze_job

SCAM_POSTING = (
    "URGENT HIRING! Work from home data entry internship. "
    "Earn Rs. 50,000 per week. 100% placement guaranteed. "
    "Pay a refundable registration fee of Rs. 999 to confirm your seat. "
    "Limited seats, apply immediately. Contact us on WhatsApp. "
    "Share OTP to verify your profile."
)

LEGIT_POSTING = (
    "Acme Technologies Pvt Ltd is hiring a Software Engineering Intern for "
    "our Bengaluru office. Key responsibilities: develop and test features "
    "in Python and Flask, write unit tests, fix bugs reported by the team, "
    "and document your work for code reviews. Eligibility: final-year B.Tech "
    "or B.E. students in CSE or IT with knowledge of Python, SQL and Git. "
    "Selection process: an online assessment, a technical interview and an "
    "HR round. We never charge any fee at any stage of the hiring process. "
    "Stipend: Rs. 25,000 per month. Send your resume to "
    "careers@acme-example.com."
)


def show(title, result):
    print("=" * 60)
    print(title)
    print(f"RISK SCORE: {result['score']}/100  ->  {result['level']}")
    print("Warning signs:")
    for warning in result["warnings"]:
        print(f"  [!] {warning['label']} (+{warning['weight']})"
              f"  <- matched: {warning['evidence']}")
    print("Positive signals:")
    for positive in result["positives"]:
        print(f"  [+] {positive['label']} (-{positive['weight']})")
    print("Explanation:", result["explanation"])
    print()


show("SCAM-STYLE POSTING", analyze_job(SCAM_POSTING))
show("LEGITIMATE-STYLE POSTING", analyze_job(
    LEGIT_POSTING,
    company_name="Acme Technologies Pvt Ltd",
    company_website="https://www.acme-example.com",
    recruiter_email="careers@acme-example.com",
))