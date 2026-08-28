# Documentation — Resume Information Extraction System

This file explains every file, function, and design decision in the project. Written in plain language for easy understanding.

---

## Table of Contents

1. [app/main.py](#appmainpy)
2. [app/routers/resume.py](#approutersresumepy)
3. [app/schemas/resume.py](#appschemaresumepy)
4. [app/services/file_parser.py](#appservicesfile_parserpy)
5. [app/services/resume_extractor.py](#appservicesresume_extractorpy)
6. [app/services/education_extractor.py](#appserviceseducation_extractorpy)
7. [app/services/experience_extractor.py](#appservicesexperience_extractorpy)
8. [app/services/experience_calculator.py](#appservicesexperience_calculatorpy)
9. [app/services/skill_extractor.py](#appservicesskill_extractorpy)
10. [app/utils/regex_patterns.py](#apputilsregex_patternspy)
11. [app/utils/text_cleaner.py](#apputilstext_cleanerpy)
12. [app/data/skills.json](#appdataskillsjson)
13. [tests/](#tests)
14. [Request Flow](#request-flow)

---

## app/main.py

This is the entry point of the FastAPI application.

**What it does:**
- Creates the FastAPI app instance
- Registers the resume router under `/api/v1`
- CORS is open (`allow_origins=["*"]`) so any browser or Postman can call the API

There is no business logic here — it just wires everything together.

---

## app/routers/resume.py

Defines the one API endpoint in the project:

```
POST /api/v1/resume/extract
```

### Function: `extract_resume`

This function runs every time a resume is uploaded. Here is what it does step by step:

1. Checks that a filename was provided
2. Validates the file extension (only `.pdf` and `.docx` are allowed)
3. Reads the file bytes from the upload
4. Checks that the file is not empty
5. Checks that the file is not larger than 10 MB
6. Calls `extract_text_from_file()` to get plain text from the file
7. Calls `extract_resume_data_from_file()` to run all extractors
8. Returns the result as JSON (`ResumeResponse`)

**Error handling:**

| Situation | HTTP Status |
|-----------|------------|
| File type not supported | 400 |
| File is empty | 400 |
| File is corrupted or encrypted | 400 |
| `file` field missing in request | 422 |
| Any unexpected error | 500 |

---

## app/schemas/resume.py

Defines the data models for the API response using **SQLModel** (which is built on top of Pydantic V2).

### Why SQLModel?
SQLModel combines Pydantic and SQLAlchemy. For this project we only use it for validation (no database). If you want to save resume data to a database later, you can just add `table=True` and a primary key.

---

### Class: `Education`

```python
class Education(SQLModel):
    degree: Optional[str]       # e.g. "B.Tech", "10th", None
    institution: Optional[str]  # e.g. "IIT Bombay", None
```

**Validation:** Empty strings are automatically converted to `None` using a `field_validator`.

---

### Class: `Experience`

```python
class Experience(SQLModel):
    job_title: Optional[str]  # e.g. "Software Engineer Intern"
    company:   Optional[str]  # e.g. "TCS"
    duration:  Optional[str]  # e.g. "Jan 2024 - May 2024"
```

**Validation:** Same as Education — empty strings become `None`.

---

### Class: `ResumeResponse`

The main response model. Contains all extracted fields.

```python
class ResumeResponse(SQLModel):
    name:                   Optional[str]        # Candidate name
    email:                  Optional[EmailStr]   # Validated email
    phone:                  Optional[str]        # Phone number
    linkedin:               Optional[str]        # LinkedIn URL
    github:                 Optional[str]        # GitHub URL
    skills:                 list[str]            # Detected skills
    education:              list[Education]      # Education entries
    experience:             list[Experience]     # Work experience entries
    total_experience_years: float                # Total years (0.0 to 60.0)
```

**Field constraints using `Field()`:**

| Field | Constraint | Reason |
|-------|-----------|--------|
| `name` | min 2, max 100 chars | Avoid single-char or overly long names |
| `phone` | min 7, max 20 chars | Valid phone number length range |
| `linkedin`, `github` | min 10 chars | URLs are at least 10 chars |
| `total_experience_years` | 0.0 to 60.0 | Reasonable range for years of experience |

**Validators using `field_validator()`:**

| Validator | What it does |
|-----------|-------------|
| `clean_name` | Strips extra spaces from the name |
| `lowercase_email` | Converts email to lowercase before validation |
| `clean_phone` | Strips extra spaces from phone |
| `clean_url` | Strips spaces and trailing slashes from URLs |
| `deduplicate_skills` | Removes duplicate skills, keeps order |
| `round_experience` | Rounds total experience to 1 decimal place |

**Email validation:** Uses `EmailStr` from `email-validator` library — this gives proper RFC 5322 email validation instead of relying on regex alone.

---

## app/services/file_parser.py

Reads the uploaded file and converts it to text. This is the only file that uses PyMuPDF and python-docx directly.

### Custom exceptions

| Exception | When it is raised |
|-----------|------------------|
| `UnsupportedFileTypeError` | Extension is not `.pdf` or `.docx` |
| `EmptyFileError` | File has 0 bytes or produces no text |
| `CorruptedFileError` | File cannot be opened or is password-protected |

---

### `validate_file_extension(filename)`

Checks the file extension before doing anything else. If the extension is not `.pdf` or `.docx`, it raises `UnsupportedFileTypeError` immediately. This is a quick check at the start of the request.

---

### `extract_text_from_file(file_bytes, filename)`

Main function. Looks at the extension and calls either `_extract_pdf()` or `_extract_docx()`. Returns all text from the file as one string.

---

### `extract_pdf_education_blocks(file_bytes)`

This is a special function for education extraction from PDFs.

**Why it exists:** When you use PyMuPDF's normal text extraction, you lose position information. But for resumes with two columns (e.g., degree on the left, institution on the right), you need to know which text is on the same line or nearby.

This function uses PyMuPDF's block API (`page.get_text("blocks")`) which returns every text chunk along with its `(x, y)` coordinates. The result is a list of blocks sorted by position (top to bottom, left to right).

Each block has: `page`, `x0`, `y0`, `x1`, `y1`, `text`.

Returns an empty list if the file cannot be parsed (the extractor degrades gracefully).

---

### `extract_docx_education_tables(file_bytes)`

Extracts all tables from a DOCX file. Returns a nested list:
- Outer list = tables
- Middle list = rows
- Inner list = cells (as strings)

Handles merged cells (python-docx repeats merged cell text, this function deduplicates them).

---

## app/services/resume_extractor.py

This is the main pipeline. It calls all the individual extractors and puts the results together into a `ResumeResponse` object.

---

### `extract_resume_data(raw_text)`

Text-only mode. Used in unit tests where you just pass a string of text. Calls `_run_pipeline` without any PDF blocks or DOCX tables.

---

### `extract_resume_data_from_file(file_bytes, filename, raw_text)`

Full mode. Used by the API endpoint. It:
- If PDF → calls `extract_pdf_education_blocks()` to get layout blocks
- If DOCX → calls `extract_docx_education_tables()` to get table data
- Then calls `_run_pipeline()` with all available data

---

### `_run_pipeline(raw_text, pdf_blocks, docx_tables)`

Runs every extractor in order and builds the response:

| Step | Function called | Field filled |
|------|----------------|-------------|
| 1 | `clean_text(raw_text)` | Cleaned text for all extractors |
| 2 | `extract_name(text)` | `name` |
| 3 | `extract_email(text)` | `email` |
| 4 | `extract_phone(text)` | `phone` |
| 5 | `extract_skills(text)` | `skills` |
| 6 | `extract_linkedin(text)` | `linkedin` |
| 7 | `extract_github(text)` | `github` |
| 8 | `extract_education(text, pdf_blocks, docx_tables)` | `education` |
| 9 | `extract_experience(text)` | `experience` |
| 10 | `calculate_total_experience(experience)` | `total_experience_years` |

---

### Individual extractor functions (in resume_extractor.py)

#### `extract_name(text)`
- Looks at the first 5 lines of the resume
- Skips any line that contains `@`, `http`, only digits, or a section keyword like "EXPERIENCE"
- Returns the first line that looks like a 2–4 word name
- Returns `None` if nothing qualifies

#### `extract_email(text)`
- Uses `EMAIL_PATTERN` regex to find a candidate email in the text
- Passes it to `email_validator.validate_email()` for proper validation
- Returns the normalised lowercase email, or `None` if invalid/not found

#### `extract_phone(text)`
- First tries the structured `PHONE_PATTERN` (handles country codes, area codes)
- Falls back to `PHONE_SIMPLE_PATTERN` (any long digit sequence)
- Filters out false positives like year ranges (`2020-2024`)
- Returns the first valid match or `None`

#### `extract_linkedin(text)`
- Applies `LINKEDIN_PATTERN` to find `linkedin.com/in/...` URLs
- Works with or without `https://` or `www.`

#### `extract_github(text)`
- Same idea as LinkedIn but for `github.com/username`

---

## app/services/education_extractor.py

The most complex service in the project. Extracts degree and institution pairs from resumes that can have many different layouts.

---

### Public function: `extract_education(text, pdf_blocks, docx_tables)`

This is the only function called from outside. It runs up to 3 strategies and combines/deduplicates the results.

**Strategy order:**
1. DOCX table strategy (if DOCX tables are available)
2. PDF block strategy (if PDF blocks are available)
3. Plain text strategy (always runs as fallback)

Duplicates are removed (same degree or same institution seen twice → keep one).

---

### Strategy A — DOCX Tables (`_extract_from_docx_tables`)

Goes through each table in the DOCX file, row by row, cell by cell. Each cell is checked to see if it contains a degree keyword or an institution keyword. Returns one education entry per row.

Best for resumes that use a Word table for their education section (common in Indian CV formats).

---

### Strategy B — PDF Positional Blocks (`_extract_from_pdf_blocks`)

Uses the `(x, y)` coordinate data from PyMuPDF to handle side-by-side layouts.

**How it works:**
1. Finds the education section heading block by matching `EDUCATION_SECTION_PATTERN`
2. Collects all blocks after that heading until the next section
3. Groups blocks that have similar `y0` values (within 8 pixels) into the same row — this handles columns
4. Groups rows that are close together (gap ≤ 20 pixels) into one entry
5. Extracts degree + institution from each entry

This is why two-column PDFs work correctly — degree in column 1 and institution in column 2 end up in the same row group.

---

### Strategy C — Plain Text (`_extract_from_text`)

Works on plain text. Used as a universal fallback.

1. `_find_section_lines()` — scans for an "EDUCATION" heading and collects the lines under it
2. `_parse_blocks()` — splits those lines into per-entry groups
3. `_candidate_scan()` — full-document search if no heading was found

---

### `_parse_blocks(lines)` — key function

Takes a flat list of lines from the education section and splits them into per-entry groups.

There are **4 boundary triggers** that start a new entry:

| Trigger | When it fires |
|---------|--------------|
| 1 | A blank line is found |
| 2 | A second degree keyword appears in the current block |
| 3 | A new institution appears when the current block already has both degree and institution |
| 4 | A new institution appears when the current block has an institution but no degree yet |

Triggers 3 and 4 are important for compact resume formats where there are no blank lines between entries.

---

### `_extract_entry_from_lines(lines)` — core extraction

Takes a block of lines (one education entry) and extracts the degree and institution from it.

Priority order:
1. Check for `"B.Tech from Vel Tech"` format (splits on word `from`)
2. Check for inline split: `"B.Tech | CGPA: 9.2"` or `"10th, St. Ann's School"`
3. Look for a degree keyword in any line
4. Look for an institution keyword in any line
5. If nothing matched, treat the first 2+ word line as a possible institution

---

### Cleaning helpers

| Function | What it removes |
|----------|----------------|
| `_strip_bullet(line)` | Leading bullet symbols like `•`, `-`, `►` |
| `_clean_degree(line)` | Year ranges, `| CGPA: ...` suffix |
| `_clean_institution(line)` | Year ranges, standalone years at end |

---

### Detection patterns used

| Pattern | Purpose |
|---------|---------|
| `_INSTITUTION_KEYWORDS` | Words like University, College, School, IIT, NIT, BITS |
| `_NOISE_PATTERN` | Lines to skip like `CGPA: 9.2`, `Percentage: 85%` |
| `_YEAR_NOISE_RE` | Lines that are only a year range like `2020 - 2022` |
| `_BULLET_PREFIX` | Bullet characters to strip from line start |

---

## app/services/experience_extractor.py

### `extract_experience(text)`

Finds the work experience section and extracts job entries from it.

**How it works:**
1. Scans the text for an experience section heading (`Experience`, `Work Experience`, `Internship`, etc.)
2. Collects lines until the next major section heading
3. Groups those lines into per-job blocks (separated by blank lines or date lines)
4. For each block, extracts:
   - **Job title** — first non-date, non-company looking line
   - **Company** — second significant line
   - **Duration** — a line that matches a date range pattern like `Jan 2024 - Jun 2024`
   - **Description** — any bullet-point lines describing the work

Returns a list of dicts with keys: `job_title`, `company`, `duration`.

---

## app/services/experience_calculator.py

### `calculate_total_experience(experience_list)`

Takes the list of experience entries and returns the total years worked as a single number.

**Steps:**
1. Reads the `duration` field from each entry
2. Parses each duration string into a start and end date
3. Merges overlapping intervals (so two jobs at the same time are not counted twice)
4. Adds up all the days
5. Divides by 365.25 and rounds to 1 decimal place

Returns `0.0` if no parseable durations are found.

---

### `_parse_duration(duration_str)`

Splits a string like `"Jan 2022 - Jun 2023"` into a start part and an end part, then parses each into a Python `date` object.

**Supported formats:**

| Format | Example |
|--------|---------|
| Month + Year range | `Jan 2022 - Jun 2023` |
| Month + Year to Present | `March 2021 - Present` |
| Year range | `2022 - 2024` |
| Present / Current / Ongoing | Treated as today's date |

---

### `_merge_intervals(intervals)`

Sorts all date ranges by start date, then merges any overlapping ones.

Example:
```
Input:  [(2020-01, 2022-06), (2021-01, 2023-01)]
Output: [(2020-01, 2023-01)]   ← merged into one, 3 years not 4
```

This prevents double-counting when someone held two jobs at the same time.

---

## app/services/skill_extractor.py

### `extract_skills(text)`

Reads `app/data/skills.json` and checks if any of those skill keywords appear in the resume text.

**How it works:**
- Each skill in the JSON has a `name` (canonical name) and a list of `aliases` (other ways the skill might be written)
- The text is searched case-insensitively for each alias
- If found, the canonical `name` is added to the result list
- Duplicates are removed

**Examples:**

| Found in resume | Returned as |
|----------------|-------------|
| `js`, `JS`, `javascript` | `JavaScript` |
| `sklearn`, `scikit-learn` | `Scikit-learn` |
| `postgres`, `postgresql` | `PostgreSQL` |

Returns an empty list if the skills file is missing or the text has no matches.

---

## app/utils/regex_patterns.py

All regex patterns used in the project are defined in this one file. This makes it easy to find and update patterns without digging through multiple files.

### Patterns explained

**`EMAIL_PATTERN`**
Matches email addresses like `user@example.com`, `user+tag@sub.domain.org`.

**`PHONE_PATTERN`**
Structured pattern that handles:
- `+91 9876543210` (Indian with country code)
- `(555) 867-5309` (US format)
- `91-9876-543210`

**`PHONE_SIMPLE_PATTERN`**
Fallback for any sequence of 10+ digits with separators. Used when the structured pattern fails.

**`LINKEDIN_PATTERN`**
Matches `linkedin.com/in/username` — works with or without `https://` or `www.`.

**`GITHUB_PATTERN`**
Same idea for `github.com/username`.

**`YEAR_RANGE_PATTERN`**
Matches date ranges like `2020-2023` or `2019 to Present`. Used to strip these from degree or institution lines.

**`DEGREE_PATTERN`**
Large pattern covering every major degree type:
- School: `10th`, `12th`, `SSC`, `SSLC`, `HSC`, `Intermediate`
- Diploma: `Diploma in CSE`, `Polytechnic Diploma`
- Bachelor: `B.Tech`, `B.E`, `B.Sc`, `BCA`, `BBA`, `MBBS`, `LLB`
- Master: `M.Tech`, `M.E`, `MBA`, `MCA`, `M.Sc`
- Doctorate: `Ph.D`, `Doctor of Philosophy`

Supports optional `in [field]` suffix like `B.Tech in Computer Science`.

**`EDUCATION_SECTION_PATTERN`**
Matches education section headings like `EDUCATION`, `Educational Background`, `Academic Qualifications`, `Scholastic Details`, etc.

**`EXPERIENCE_SECTION_PATTERN`**
Matches experience section headings like `Experience`, `Work Experience`, `Internship`, `Employment History`, etc.

**`DATE_RANGE_PATTERN`**
Month-aware pattern for experience durations. Matches things like `Jan 2022 - Jun 2023` or `March 2021 - Present`.

---

## app/utils/text_cleaner.py

Cleans raw text extracted from PDF or DOCX before passing it to the extractors. PDFs especially can have messy text with ligatures, strange dashes, and extra whitespace.

### `clean_text(text)`

Runs these operations in order:

| Operation | What it fixes |
|-----------|--------------|
| Unicode normalisation (NFKD) | Special characters, non-breaking spaces |
| Ligature replacement | `ﬁ` → `fi`, `ﬂ` → `fl`, `ﬀ` → `ff` |
| Em/en-dash normalisation | `–`, `—` → `-` |
| Bullet normalisation | `•`, `▪`, `◦`, `►` → `-` |
| Extra whitespace | Multiple spaces → single space |
| Trailing spaces | Strips each line |
| Multiple blank lines | Collapses to one blank line |

---

### `get_lines(text)`

Splits text by newlines, strips each line, and removes blank lines.
Used when you want to iterate over lines of content.

---

### `get_first_lines(text, n=5)`

Returns only the first `n` non-empty lines. Used by `extract_name()` to limit the name search to the top of the resume.

---

## app/data/skills.json

A list of 500+ technical skills, each with a canonical name and a list of aliases.

**Format:**
```json
[
  {
    "name": "Python",
    "aliases": ["python", "py", "python3"]
  },
  {
    "name": "JavaScript",
    "aliases": ["javascript", "js", "JS", "es6", "ecmascript"]
  }
]
```

**Categories covered:**
- Programming languages: Python, Java, C++, Go, Rust, etc.
- Web frameworks: FastAPI, Django, Flask, React, Angular, etc.
- Databases: PostgreSQL, MySQL, MongoDB, Redis, etc.
- Cloud: AWS, GCP, Azure, Docker, Kubernetes, etc.
- ML/AI: TensorFlow, PyTorch, Scikit-learn, OpenCV, etc.
- Tools: Git, Postman, Jira, etc.
- Concepts: REST API, OOP, DBMS, Data Structures, etc.

---

## tests/

### tests/test_api.py — API Tests

Tests the HTTP endpoint using FastAPI's `TestClient` and `httpx`.

What is tested:
- Uploading a valid PDF → should return 200 with JSON
- Uploading a valid DOCX → should return 200
- Uploading a `.txt` file → should return 400
- Uploading an empty file → should return 400
- Not including a file → should return 422

---

### tests/test_resume_extractor.py — Unit Tests (114 tests)

Tests every extractor function with known input text.

| Test class | What it tests |
|-----------|--------------|
| `TestPDFParsing` | Reading PDF, handling corrupted files |
| `TestDOCXParsing` | Reading DOCX, handling corrupted files |
| `TestFileTypeValidation` | Allowed and rejected file extensions |
| `TestNameExtraction` | 2-word names, 3-word names, skipping emails/URLs |
| `TestEmailExtraction` | Standard emails, Gmail `+` tags, complex domains |
| `TestPhoneExtraction` | Indian (+91), US, and other international formats |
| `TestSkillsExtraction` | Skill detection, normalisation, deduplication |
| `TestLinkedInExtraction` | URLs with and without `https://` |
| `TestGitHubExtraction` | URLs with and without `https://` |
| `TestEducationExtraction` | Basic degree + institution pairs |
| `TestEducationExtractionExtended` | 10th, 12th, Diploma, null rules, compact layouts |
| `TestTotalExperienceYears` | Date parsing, overlap merging, Present keyword |
| `TestExperienceExtraction` | Job title, company, duration detection |
| `TestMissingFields` | Resume with no data — should return nulls |
| `TestTextCleaner` | Whitespace, ligatures, en-dash, blank lines |

---

## Request Flow

Here is what happens from the moment a file is uploaded to when JSON is returned:

```
User uploads file
      |
      v
app/routers/resume.py
  - validates extension
  - reads bytes
  - checks size
      |
      v
app/services/file_parser.py
  - converts bytes to text
  - extracts PDF blocks (if PDF)
  - extracts DOCX tables (if DOCX)
      |
      v
app/services/resume_extractor.py  (_run_pipeline)
  - clean_text()
  - extract_name()
  - extract_email()        → validated by email-validator
  - extract_phone()
  - extract_skills()       → keyword scan against skills.json
  - extract_linkedin()
  - extract_github()
  - extract_education()    → 3-strategy extraction
  - extract_experience()
  - calculate_total_experience()
      |
      v
app/schemas/resume.py
  - ResumeResponse validates and serialises all fields
      |
      v
JSON returned to user
```
