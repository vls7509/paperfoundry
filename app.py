from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from jinja2 import Template
import tempfile
from weasyprint import HTML
import resend
from urllib.parse import quote, unquote

app = FastAPI()

# configure email
resend.api_key = "YOUR_RESEND_API_KEY"


# ---------- SIMPLE TRAIT ENGINE ----------
def evaluate_profile(answers):

    analytical = 0
    people = 0
    creative = 0
    structured = 0

    for value in answers.values():
        v = str(value).lower()

        if "data" in v or "pattern" in v or "analyze" in v:
            analytical += 2

        if "help" in v or "people" in v or "guide" in v:
            people += 2

        if "design" in v or "create" in v or "idea" in v:
            creative += 2

        if "plan" in v or "organize" in v or "schedule" in v:
            structured += 2

    scores = {
        "analytical": analytical,
        "people": people,
        "creative": creative,
        "structured": structured
    }

    top = max(scores, key=scores.get)

    mapping = {
        "analytical": (
            "Structured Analytical Work",
            ["Data Science","Actuarial Science","Research"],
            "Computing & Data"
        ),
        "people": (
            "Guidance & Support Work",
            ["Therapy","Coaching","Education"],
            "Health & Human Development"
        ),
        "creative": (
            "Creative Production Work",
            ["Design","Media","Architecture"],
            "Design & Creative Arts"
        ),
        "structured": (
            "Coordination & Operations Work",
            ["Project Management","Operations","Logistics"],
            "Business & Operations"
        )
    }

    return mapping[top]


# ---------- WEBHOOK ENDPOINT ----------
@app.post("/submit")
async def submit(request: Request):

    data = await request.json()

    # Extract answers from Tally payload
    answers = {}
    for f in data.get("data", {}).get("fields", []):
        answers[f.get("key")] = f.get("value")

    workstyle, careers, major = evaluate_profile(answers)

    # render HTML report
    with open("report.html") as f:
        template = Template(f.read())

    html_out = template.render(
        workstyle=workstyle,
        careers=careers,
        major=major
    )

    # create PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        HTML(string=html_out).write_pdf(tmp.name)
        pdf_path = tmp.name

    # send email (if provided)
    email = data.get("data", {}).get("respondent", {}).get("email")
    if email:
        resend.Emails.send({
            "from": "PaperFoundry <results@paperfoundry.ai>",
            "to": [email],
            "subject": "Your Career Discovery Report",
            "html": "<p>Your report is attached.</p>",
            "attachments": [{
                "filename": "career_report.pdf",
                "content": open(pdf_path, "rb").read()
            }]
        })

    # IMPORTANT: redirect user to results page
    safe_style = quote(workstyle)
    return {
        "redirect": f"https://paperfoundry.onrender.com/result?style={safe_style}"
    }


# ---------- RESULT PAGE ----------
@app.get("/result", response_class=HTMLResponse)
def result(style: str = "Unknown"):
