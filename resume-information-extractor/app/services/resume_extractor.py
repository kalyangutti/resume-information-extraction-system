"""
Main resume extraction pipeline.

Orchestrates all individual extractor functions and combines their
outputs into the validated Pydantic ResumeResponse model.

No LLM or external AI services are used anywhere in this pipeline.
"""

from __future__ import annotations

import re
from typing import Optional

from email_validator import validate_email as validate_email_address, EmailNotValidError

from app.schemas.resume import Education, Experience, ResumeResponse
from app.services.education_extractor import extract_education
from app.services.experience_calculator import calculate_total_experience
from app.services.experience_extractor import extract_experience
from app.services.file_parser import (
    extract_docx_education_tables,
    extract_pdf_education_blocks,
)
from app.services.skill_extractor import extract_skills
from app.utils.regex_patterns import (
    EMAIL_PATTERN,
    GITHUB_PATTERN,
    LINKEDIN_PATTERN,
    PHONE_SIMPLE_PATTERN,
    URL_PATTERN,
    YEAR_RANGE_PATTERN,
)
from app.utils.text_cleaner import clean_text, get_first_lines, get_lines

# ---------------------------------------------------------------------------
# Patterns used for name extraction filtering
# ---------------------------------------------------------------------------
_NAME_EXCLUDE_PATTERN = re.compile(
    r"""
    @|                              # email addresses
    \d{5,}|                         # long digit sequences (phone)
    (?:https?|www)\.|               # URLs
    (?:resume|cv|curriculum\s*vitae| # document headings
       contact|profile|address|
       objective|summary|reference)
    """,
    re.IGNORECASE | re.VERBOSE,
)

_NAME_VALID_PATTERN = re.compile(
    r"^[A-Z][a-zA-Z\-'.]{1,}\s+[A-Z][a-zA-Z\-'.]{1,}(?:\s+[A-Za-z\-'.]+)?$"
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_resume_data(raw_text: str) -> ResumeResponse:
    """
    Run the full resume extraction pipeline from plain text.

    For layout-aware extraction (multi-column PDFs, DOCX tables) prefer
    calling extract_resume_data_from_file() with the raw file bytes.

    Args:
        raw_text: Raw text extracted from the uploaded PDF or DOCX file.

    Returns:
        A validated ResumeResponse Pydantic model.
    """
    return _run_pipeline(raw_text, pdf_blocks=None, docx_tables=None)


def extract_resume_data_from_file(
    file_bytes: bytes,
    filename: str,
    raw_text: str,
) -> ResumeResponse:
    """
    Enhanced extraction pipeline that uses structural layout data.

    Extracts positional blocks (PDF) or table data (DOCX) in addition to
    plain text so that multi-column and table-based education layouts are
    correctly parsed.

    Args:
        file_bytes: Raw file bytes from the upload.
        filename:   Original filename (used to decide PDF vs DOCX path).
        raw_text:   Pre-extracted plain text (avoids re-parsing the file).

    Returns:
        A validated ResumeResponse Pydantic model.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    pdf_blocks = None
    docx_tables = None

    if ext == "pdf":
        try:
            pdf_blocks = extract_pdf_education_blocks(file_bytes)
        except Exception:
            pdf_blocks = None
    elif ext == "docx":
        try:
            docx_tables = extract_docx_education_tables(file_bytes)
        except Exception:
            docx_tables = None

    return _run_pipeline(raw_text, pdf_blocks=pdf_blocks, docx_tables=docx_tables)


def _run_pipeline(
    raw_text: str,
    pdf_blocks,
    docx_tables,
) -> ResumeResponse:
    """Shared extraction pipeline used by both public entry-points."""
    text = clean_text(raw_text)

    name     = extract_name(text)
    email    = extract_email(text)
    phone    = extract_phone(text)
    skills   = extract_skills(text)
    linkedin = extract_linkedin(text)
    github   = extract_github(text)

    raw_education = extract_education(text, pdf_blocks=pdf_blocks, docx_tables=docx_tables)
    education = [Education(**edu) for edu in raw_education]

    raw_experience = extract_experience(text)
    experience = [Experience(**exp) for exp in raw_experience]

    total_experience_years = calculate_total_experience(raw_experience)

    return ResumeResponse(
        name=name,
        email=email,
        phone=phone,
        skills=skills,
        education=education,
        experience=experience,
        linkedin=linkedin,
        github=github,
        total_experience_years=total_experience_years,
    )


# ---------------------------------------------------------------------------
# Individual extraction functions
# (kept here for easy import in tests)
# ---------------------------------------------------------------------------

def extract_name(text: str) -> Optional[str]:
    """
    Extract candidate full name using rule-based heuristics.

    Approach:
    - Inspect the first 10 non-empty lines of the resume.
    - Skip lines that contain email addresses, phone numbers, URLs,
      common section headings, or known non-name patterns.
    - Prefer lines that match the 'Firstname Lastname' pattern.
    - Falls back to the first plausible line if no perfect match found.

    Note: Name extraction may fail on unusual or complex resume layouts.

    Args:
        text: Cleaned resume text.

    Returns:
        Candidate full name string, or None if not found.
    """
    candidates = get_first_lines(text, n=10)

    best_match: Optional[str] = None

    for line in candidates:
        line = line.strip()

        # Skip empty or very long lines (unlikely to be a name)
        if not line or len(line) > 60 or len(line) < 3:
            continue

        # Skip lines with exclusion patterns
        if _NAME_EXCLUDE_PATTERN.search(line):
            continue

        # Skip lines that are likely section headings (ALL CAPS)
        if line.isupper() and len(line) > 20:
            continue

        # Skip lines that look like phone numbers
        if PHONE_SIMPLE_PATTERN.fullmatch(line.strip()):
            continue

        # Highest confidence: matches Firstname Lastname pattern
        if _NAME_VALID_PATTERN.match(line):
            return line.strip()

        # Keep as fallback candidate
        if best_match is None:
            # Must contain at least one space (two words) and look like words
            words = line.split()
            if (
                2 <= len(words) <= 4
                and all(re.match(r"^[A-Za-z\-'.]+$", w) for w in words)
            ):
                best_match = line.strip()

    return best_match


def extract_email(text: str) -> Optional[str]:
    """
    Extract the first valid email address from resume text.

    Uses regex for initial candidate extraction, then validates
    with the email-validator library (not pure regex) to ensure
    RFC 5322 compliance and proper domain format.

    Args:
        text: Cleaned resume text.

    Returns:
        Validated email address string (lowercase), or None.
    """
    match = EMAIL_PATTERN.search(text)
    if not match:
        return None

    candidate = match.group(0).strip().lower()

    # Validate with email-validator library instead of trusting regex alone
    try:
        result = validate_email_address(candidate, check_deliverability=False)
        return result.normalized.lower()
    except EmailNotValidError:
        return None


def extract_phone(text: str) -> Optional[str]:
    """
    Extract the first phone number from resume text.

    Uses a flexible regex that handles international formats,
    Indian mobile numbers, and common separator styles.

    Args:
        text: Cleaned resume text.

    Returns:
        Phone number string, or None.
    """
    # Search line by line to avoid false positives from long number sequences
    for line in get_lines(text):
        # Skip pure URL lines
        if URL_PATTERN.search(line) and not EMAIL_PATTERN.search(line):
            continue

        # Skip lines that are date/year ranges (e.g. "2018 - 2022")
        if YEAR_RANGE_PATTERN.fullmatch(line.strip()):
            continue

        # If the line has an email, strip it out before searching for phone
        # (handles contact lines like "john@email.com | +91 9876543210")
        scan_line = EMAIL_PATTERN.sub("", line)

        match = PHONE_SIMPLE_PATTERN.search(scan_line)
        if match:
            raw = match.group(0).strip()
            # Must have at least 7 digits
            digits_only = re.sub(r"\D", "", raw)
            if 7 <= len(digits_only) <= 15:
                # Reject if it looks like a year range (4-digit-separator-4-digit)
                if re.fullmatch(r"(19|20)\d{2}\s*[-–—to]+\s*(19|20)\d{2}", raw.strip(), re.IGNORECASE):
                    continue
                return raw

    return None


def extract_linkedin(text: str) -> Optional[str]:
    """
    Extract a LinkedIn profile URL from resume text.

    Args:
        text: Cleaned resume text.

    Returns:
        LinkedIn URL string, or None.
    """
    match = LINKEDIN_PATTERN.search(text)
    if not match:
        return None
    url = match.group(0).strip()
    # Ensure it starts with https://
    if not url.startswith("http"):
        url = "https://" + url
    return url.rstrip("/")


def extract_github(text: str) -> Optional[str]:
    """
    Extract a GitHub profile URL from resume text.

    Args:
        text: Cleaned resume text.

    Returns:
        GitHub URL string, or None.
    """
    match = GITHUB_PATTERN.search(text)
    if not match:
        return None
    url = match.group(0).strip()
    if not url.startswith("http"):
        url = "https://" + url
    return url.rstrip("/")
