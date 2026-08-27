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

---

## Setup

Make sure you have **Python 3.10+** installed.

**Step 1 — Clone or open the project folder**

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
| `http://localhost:8000/ui` | Web upload page (drag and drop) |
| `http://localhost:8000/docs` | Swagger UI — test the API in browser |
| `http://localhost:8000/api/v1/resume/extract` | API endpoint |

---

## How to Use

### Option 1 — Web UI

Open `http://localhost:8000/ui` in your browser, drag and drop a resume, and see the JSON output instantly.

---

### Option 2 — Postman

1. Open Postman
2. Set method to `POST`
3. URL: `http://localhost:8000/api/v1/resume/extract`
4. Go to **Body** → select **form-data**
5. Add a key named `file`, change type to **File**
6. Select your resume file (PDF or DOCX)
7. Click **Send**

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

If the resume does not have LinkedIn or GitHub, those fields return `null`. Education entries where only the institution is found (no degree detected) return `"degree": null`.

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

### Error Response — Wrong File Type

```json
{
  "detail": "Unsupported file type '.txt'. Only .pdf and .docx files are accepted."
}
```

### Error Response — Empty File

```json
{
  "detail": "The uploaded file is empty."
}
```

### Error Response — Scanned PDF (No Text)

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
│   │   ├── file_parser.py           # Reads PDF and DOCX files
│   │   ├── resume_extractor.py      # Main pipeline, calls all extractors
│   │   ├── education_extractor.py   # Extracts degree + institution
│   │   ├── experience_extractor.py  # Extracts job title, company, duration
│   │   ├── experience_calculator.py # Calculates total years of experience
│   │   └── skill_extractor.py       # Detects skills from skills.json
│   ├── utils/
│   │   ├── regex_patterns.py        # All regex patterns in one place
│   │   └── text_cleaner.py          # Cleans raw PDF/DOCX text
│   ├── data/
│   │   └── skills.json              # 500+ skills with aliases
│   └── static/
│       └── index.html               # Web upload UI
│
├── tests/
│   ├── test_api.py                  # API endpoint tests
│   └── test_resume_extractor.py     # Unit tests (114 tests)
│
├── requirements.txt
├── README.md
└── DOCUMENTATION.md                 # Detailed explanation of every function
```

---

## How Each Field is Extracted

| Field | Approach |
|-------|---------|
| **Name** | Reads first 5 lines, picks the first 2–4 word name-like line |
| **Email** | Regex to find candidate, then `email-validator` library for validation |
| **Phone** | Regex with country code support, filters out year-range false positives |
| **LinkedIn / GitHub** | URL pattern matching |
| **Skills** | Keyword scan against `skills.json` — case-insensitive, with aliases |
| **Education** | 3-strategy approach (DOCX tables, PDF layout blocks, plain text) |
| **Experience** | Section heading detection, splits into job blocks, extracts title/company/duration |
| **Total Experience** | Parses all date ranges, merges overlapping periods, returns total in years |

> No AI or LLM is used. Everything runs locally using Python regex and rule-based logic.

---

## Running Tests

```bash
# Run all 114 tests
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
| `PyMuPDF` | Reads PDF files |
| `python-docx` | Reads DOCX files |
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
