# Resume Information Extraction API

A FastAPI application that reads a PDF or DOCX resume and returns structured JSON — no AI or external service used, everything runs locally.

---

## Table of Contents

- [Setup](#setup)
- [Running the Server](#running-the-server)
- [How to Use](#how-to-use)
- [Sample Output](#sample-output)
- [Project Structure](#project-structure)
- [How Each Field is Extracted](#how-each-field-is-extracted)
- [Running Tests](#running-tests)
- [Dependencies](#dependencies)
- [Approach, Assumptions & Limitations](#approach-assumptions--limitations)

---

## Setup

Make sure you have **Python 3.10+** installed.

**Step 1 — Open the project folder**

```bash
cd resume-information-extractor
```

**Step 2 — Install dependencies**

```bash
pip install -r requirements.txt
```

That's it. No virtual environment needed, no API keys, no account setup.

---

## Running the Server

```bash
uvicorn app.main:app --reload
```

The server starts at `http://localhost:8000`

| URL | What it is |
|-----|-----------|
| `http://localhost:8000/docs` | Swagger UI — test the API in browser |
| `http://localhost:8000/redoc` | ReDoc API documentation |
| `http://localhost:8000/api/v1/resume/extract` | API endpoint |

---

## How to Use

### Option 1 — Postman

1. Open Postman
2. Set method to `POST`
3. URL: `http://localhost:8000/api/v1/resume/extract`
4. Go to **Body** → select **form-data**
5. Add a key named `file`, change type to **File**
6. Select your resume file (PDF or DOCX)
7. Click **Send**

---

### Option 2 — Swagger UI (`/docs`)

1. Open `http://localhost:8000/docs` in your browser
2. Expand `POST /api/v1/resume/extract`
3. Click **Try it out**
4. Choose a resume file (`.pdf` or `.docx`) and click **Execute**

---

### Option 3 — cURL

```bash
curl -X POST http://localhost:8000/api/v1/resume/extract \
     -F "file=@resume.pdf"
```

---

## Sample Output

### Successful Response — Full Resume

```json
{
  "name": "Kalyan Babu Gutti",
  "email": "kalyan@example.com",
  "phone": "+91 9014929583",
  "linkedin": "https://linkedin.com/in/kalyan-gutti",
  "github": "https://github.com/KalyanGutti",
  "skills": [
    "Python",
    "FastAPI",
    "SQL",
    "Machine Learning",
    "Git"
  ],
  "education": [
    {
      "degree": "B.Tech in Computer Science & Engineering",
      "institution": "Vel Tech Rangarajan Dr. Sagunthala R&D Institute of Science and Technology"
    },
    {
      "degree": "Intermediate (Class XII)",
      "institution": "Narayana Junior College"
    },
    {
      "degree": "10th",
      "institution": "St. Ann's School"
    }
  ],
  "experience": [
    {
      "job_title": "Software Engineer Intern",
      "company": "ABC Technologies",
      "duration": "Jan 2024 - Jun 2024"
    }
  ],
  "total_experience_years": 0.5
}
```

---

### Partial Response — Some Fields Missing

If the resume does not have LinkedIn or GitHub, those fields return `null`. Education entries where only the institution is found return `"degree": null`.

```json
{
  "name": "Jane Smith",
  "email": "jane.smith@gmail.com",
  "phone": null,
  "linkedin": null,
  "github": "https://github.com/janesmith",
  "skills": ["Java", "Spring Boot", "MySQL"],
  "education": [
    {
      "degree": "MBA",
      "institution": "IIM Bangalore"
    },
    {
      "degree": null,
      "institution": "Delhi Public School"
    }
  ],
  "experience": [],
  "total_experience_years": 0.0
}
```

---

### Error Responses

**Wrong file type:**
```json
{
  "detail": "Unsupported file type '.txt'. Only .pdf and .docx files are accepted."
}
```

**Empty file:**
```json
{
  "detail": "The uploaded file is empty."
}
```

**Scanned PDF with no text:**
```json
{
  "detail": "No text could be extracted from the PDF. It may be a scanned/image-only document."
}
```

---

## Project Structure

```
resume-information-extractor/
│
├── app/
│   ├── main.py                      # App entry point, routes
│   ├── routers/
│   │   └── resume.py                # POST /api/v1/resume/extract
│   ├── schemas/
│   │   └── resume.py                # Response models (SQLModel + Pydantic V2)
│   ├── services/
│   │   ├── file_parser.py           # Reads PDF and DOCX files + link annotations
│   │   ├── resume_extractor.py      # Main pipeline, calls all extractors
│   │   ├── education_extractor.py   # Multi-strategy degree + institution extraction
│   │   ├── experience_extractor.py  # Extracts job title, company, duration
│   │   ├── experience_calculator.py # Calculates total years of experience
│   │   └── skill_extractor.py       # Detects skills from skills.json
│   ├── utils/
│   │   ├── regex_patterns.py        # Centralised regex patterns (degree, phone, etc.)
│   │   └── text_cleaner.py          # Cleans raw PDF/DOCX text
│   └── data/
│       └── skills.json              # 500+ skills with aliases
│
├── tests/
│   ├── test_api.py                  # API endpoint tests
│   └── test_resume_extractor.py     # Unit tests (117 tests)
│
├── requirements.txt
├── README.md                        # Project documentation
├── NOTES.md                         # Approach, assumptions & limitations
└── DOCUMENTATION.md                 # Technical specification of every module
```

---

## How Each Field is Extracted

| Field | Approach |
|-------|---------|
| **Name** | Reads top lines, skips emails/URLs/titles, handles single-letter initials (e.g. G B Harsha) |
| **Email** | Regex to find candidate, validated with `email-validator` library (RFC 5322) |
| **Phone** | Two-pass regex (structured + fallback), filters out year-range false positives |
| **LinkedIn / GitHub** | Pattern matching on text + extracts target URIs from PDF link annotations |
| **Skills** | Keyword scan against `skills.json` — case-insensitive, with aliases |
| **Education** | 3-strategy approach (DOCX tables, PDF layout blocks with boundary triggers, plain text) |
| **Experience** | Section heading detection, splits into job blocks, extracts title/company/duration |
| **Total Experience** | Parses all date ranges, merges overlapping periods, returns total in years |

> No AI or LLM is used. Everything runs locally using Python regex and rule-based logic.

---

## Running Tests

```bash
# Run all 117 tests
python -m pytest tests/ -v
```

All tests should pass. The tests cover every extractor function individually as well as the full API endpoint.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn[standard]` | Server to run FastAPI |
| `python-multipart` | Required for file uploads |
| `PyMuPDF` | Reads PDF files + layout block coordinates + link annotations |
| `python-docx` | Reads DOCX files and tables |
| `sqlmodel` | Response schema models (Pydantic V2) |
| `email-validator` | Validates email addresses |
| `pytest` | Test runner |
| `httpx` | HTTP client used in API tests |

---

## Notes

- Only `.pdf` and `.docx` files are accepted
- Maximum file size is **10 MB**
- Scanned/image PDFs cannot be read (no OCR)
- Resume content stays local — nothing is sent to any external service
- For a detailed explanation of every function and design decision, see [DOCUMENTATION.md](DOCUMENTATION.md)

---

## Approach, Assumptions & Limitations

For a full write-up on how the extraction works, what assumptions were made, and the known limitations of this project, see:

👉 [NOTES.md](NOTES.md)
