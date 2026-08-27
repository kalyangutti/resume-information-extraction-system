# Approach, Assumptions & Limitations

---

## Approach

This project is a FastAPI-based REST API that accepts a PDF or DOCX resume file and returns structured JSON containing the candidate's name, email, phone, skills, education, work experience, LinkedIn, GitHub, and total years of experience.

All extraction is done locally using Python — no AI, no LLM, no external API calls. The approach uses:

---

### 1. File Parsing & Hyperlinks

- **PyMuPDF (fitz)** is used to read PDF files. It provides:
  - Plain text extraction (`get_text("text")`)
  - Positional text blocks with `(x, y)` coordinates (`get_text("blocks")`)
  - Target URIs from PDF link annotations (`page.get_links()`), ensuring hyperlinked text (like `linkedin` or `github`) extracts the full URL.
- **python-docx** is used to read DOCX files. Paragraphs and tables are read separately since table content is not included in `doc.paragraphs` automatically.
- All file processing is done **in memory** — no temp files are saved to disk.

---

### 2. Text Cleaning

Raw PDF/DOCX text is normalised before extraction. The `clean_text()` utility handles:

- Ligatures (`ﬁ → fi`, `ﬂ → fl`)
- Em-dashes and en-dashes (`— → -`, `– → -`)
- Bullet symbols (`•`, `▪`, `►` → `-`)
- Extra whitespace and non-breaking spaces
- Multiple blank lines collapsed to one

---

### 3. Extraction Pipeline

| Field | How it is extracted |
|-------|-------------------|
| **Name** | Reads first 5 lines, skips emails/URLs/titles, supports single-letter initials (e.g. `G B Harsha Vardhan`), returns the first 2–4 word name line |
| **Email** | Regex finds a candidate string, then `email-validator` library validates it (RFC 5322 compliant) |
| **Phone** | Two-pass regex (structured + fallback), filters out false positives like year ranges (e.g. 2020–2024) |
| **Skills** | Keyword scan against a 500+ entry `skills.json` file with aliases (e.g. `js/JS/javascript → JavaScript`) |
| **LinkedIn / GitHub** | Pattern matching on text + target URIs extracted from PDF link annotations |
| **Education** | Three complementary strategies — see below |
| **Experience** | Section heading detection, job block splitting, extraction of title, company, and duration |
| **Total Experience** | Date ranges parsed, overlapping intervals merged, total days divided by 365.25 |

#### Education — Three Strategies

- **(A) DOCX Tables** — table rows parsed cell-by-cell, each row treated as one education entry
- **(B) PDF Positional Blocks** — text blocks grouped by `y-coordinate` into clusters, then parsed using boundary triggers to handle multi-entry column layouts
- **(C) Plain Text Parsing** — section-based parsing with 4 boundary triggers to handle compact formats that have no blank lines between entries

All three run and results are combined and deduplicated. `_clean_degree()` strips empty parentheses `()` left behind by date range removal, while `_clean_institution()` strips trailing CGPA/Percentage suffixes (`CGPA: 9.2`).

---

### 4. Validation

- Response models use **SQLModel** (Pydantic V2 compatible) with `Field` constraints (`min_length`, `max_length`, `ge`, `le`)
- `field_validator` used for custom cleanup — empty string → `None`, split on newline, cap max string length, lowercase email, deduplicate skills, round experience to 1 decimal
- `EmailStr` from `email-validator` ensures proper email validation instead of relying on regex alone

---

## Assumptions

- The resume is written in **English**
- The candidate's name appears within the **first 5 lines** of the resume
- The education section has a recognisable heading such as `EDUCATION`, `Academic Background`, `Qualifications`, etc.
- Experience durations are in a standard format such as `Jan 2022 - Jun 2023` or `2020 - Present`
- The resume is a **text-based PDF** (not a scanned image)
- Only `.pdf` and `.docx` formats are submitted (max **10 MB**)
- Skills in the resume match at least one alias in `skills.json`
- If a degree is found but no institution (or vice versa), the missing field is returned as `null` — nothing is guessed or invented

---

## Limitations

- **Scanned PDFs** — image-only PDFs cannot be parsed, no OCR is implemented
- **Name extraction** — can fail if the resume starts with a photo credit, address, or logo text instead of the candidate's name
- **Education** — may miss uncommon or unofficial degree abbreviations not covered in `DEGREE_PATTERN`
- **Experience** — may not correctly separate job title from company name in every possible resume format
- **Skills list is static** — new technologies must be added manually to `skills.json`
- **Password-protected PDFs** — rejected with a 400 error
- **Language** — only English-language resumes are supported
- **Free-text experience** — total experience calculation depends on duration being in a parseable date format; free-text like `"2 years"` is not handled
