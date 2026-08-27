"""
Tests for individual resume extraction functions.

Covers:
- PDF parsing
- DOCX parsing
- Name extraction
- Email extraction
- Phone extraction
- Skills extraction
- LinkedIn extraction
- GitHub extraction
- Education extraction
- Experience extraction
- Missing fields
- Invalid file types
- Empty files
- Corrupted files
"""

from __future__ import annotations

import io
import json
import os
import tempfile
from pathlib import Path
from typing import Optional

import pytest

# ---------------------------------------------------------------------------
# Test fixtures and helpers
# ---------------------------------------------------------------------------

SAMPLE_RESUME_TEXT = """John Doe
john.doe@example.com
+91 9876543210
https://linkedin.com/in/johndoe
https://github.com/johndoe

EDUCATION

B.Tech in Computer Science
ABC University
2018 - 2022

SKILLS
Python, FastAPI, Docker, PostgreSQL, Machine Learning, Scikit-learn

EXPERIENCE

Software Engineer
XYZ Technologies
May 2022 - July 2023

- Developed REST APIs using FastAPI
- Deployed services on AWS
"""

MINIMAL_RESUME_TEXT = """
jane.smith@email.com
+91 8888888888
"""


def _make_pdf_bytes(text: str) -> bytes:
    """Create a minimal PDF from text using PyMuPDF."""
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz  # noqa: PLC0415
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(50, 50, 550, 800)
    page.insert_textbox(rect, text, fontsize=10, fontname="helv")
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def _make_docx_bytes(text: str) -> bytes:
    """Create a minimal DOCX from text using python-docx."""
    from docx import Document  # noqa: PLC0415
    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tests: File Parsing — PDF
# ---------------------------------------------------------------------------

class TestPDFParsing:
    def test_extract_text_from_pdf(self):
        from app.services.file_parser import extract_text_from_file
        pdf_bytes = _make_pdf_bytes(SAMPLE_RESUME_TEXT)
        text = extract_text_from_file(pdf_bytes, "resume.pdf")
        assert isinstance(text, str)
        assert len(text.strip()) > 0

    def test_pdf_contains_expected_content(self):
        from app.services.file_parser import extract_text_from_file
        pdf_bytes = _make_pdf_bytes(SAMPLE_RESUME_TEXT)
        text = extract_text_from_file(pdf_bytes, "resume.pdf")
        assert "john" in text.lower() or "doe" in text.lower()

    def test_corrupted_pdf_raises_error(self):
        from app.services.file_parser import CorruptedFileError, extract_text_from_file
        with pytest.raises(CorruptedFileError):
            extract_text_from_file(b"not a real pdf", "resume.pdf")

    def test_empty_pdf_bytes_raises_error(self):
        from app.services.file_parser import EmptyFileError, extract_text_from_file
        with pytest.raises(EmptyFileError):
            extract_text_from_file(b"", "resume.pdf")


# ---------------------------------------------------------------------------
# Tests: File Parsing — DOCX
# ---------------------------------------------------------------------------

class TestDOCXParsing:
    def test_extract_text_from_docx(self):
        from app.services.file_parser import extract_text_from_file
        docx_bytes = _make_docx_bytes(SAMPLE_RESUME_TEXT)
        text = extract_text_from_file(docx_bytes, "resume.docx")
        assert isinstance(text, str)
        assert len(text.strip()) > 0

    def test_docx_contains_expected_content(self):
        from app.services.file_parser import extract_text_from_file
        docx_bytes = _make_docx_bytes(SAMPLE_RESUME_TEXT)
        text = extract_text_from_file(docx_bytes, "resume.docx")
        assert "john" in text.lower() or "doe" in text.lower()

    def test_corrupted_docx_raises_error(self):
        from app.services.file_parser import CorruptedFileError, extract_text_from_file
        with pytest.raises(CorruptedFileError):
            extract_text_from_file(b"not a real docx", "resume.docx")

    def test_empty_docx_bytes_raises_error(self):
        from app.services.file_parser import EmptyFileError, extract_text_from_file
        with pytest.raises(EmptyFileError):
            extract_text_from_file(b"", "resume.docx")


# ---------------------------------------------------------------------------
# Tests: File Type Validation
# ---------------------------------------------------------------------------

class TestFileTypeValidation:
    def test_valid_pdf_extension(self):
        from app.services.file_parser import validate_file_extension
        validate_file_extension("resume.pdf")  # Should not raise

    def test_valid_docx_extension(self):
        from app.services.file_parser import validate_file_extension
        validate_file_extension("resume.docx")  # Should not raise

    def test_invalid_extension_txt(self):
        from app.services.file_parser import UnsupportedFileTypeError, validate_file_extension
        with pytest.raises(UnsupportedFileTypeError):
            validate_file_extension("resume.txt")

    def test_invalid_extension_doc(self):
        from app.services.file_parser import UnsupportedFileTypeError, validate_file_extension
        with pytest.raises(UnsupportedFileTypeError):
            validate_file_extension("resume.doc")

    def test_invalid_extension_png(self):
        from app.services.file_parser import UnsupportedFileTypeError, validate_file_extension
        with pytest.raises(UnsupportedFileTypeError):
            validate_file_extension("photo.png")

    def test_no_extension(self):
        from app.services.file_parser import UnsupportedFileTypeError, validate_file_extension
        with pytest.raises(UnsupportedFileTypeError):
            validate_file_extension("resume")

    def test_case_insensitive_pdf(self):
        from app.services.file_parser import validate_file_extension
        validate_file_extension("RESUME.PDF")  # Should not raise

    def test_case_insensitive_docx(self):
        from app.services.file_parser import validate_file_extension
        validate_file_extension("Resume.DOCX")  # Should not raise


# ---------------------------------------------------------------------------
# Tests: Name Extraction
# ---------------------------------------------------------------------------

class TestNameExtraction:
    def test_extract_name_basic(self):
        from app.services.resume_extractor import extract_name
        from app.utils.text_cleaner import clean_text
        text = clean_text(SAMPLE_RESUME_TEXT)
        name = extract_name(text)
        assert name is not None
        assert "doe" in name.lower() or "john" in name.lower()

    def test_extract_name_returns_string_or_none(self):
        from app.services.resume_extractor import extract_name
        name = extract_name("john.doe@email.com\n+91 9876543210")
        assert name is None or isinstance(name, str)

    def test_extract_name_ignores_email_line(self):
        from app.services.resume_extractor import extract_name
        text = "john.doe@email.com\nJohn Doe\nSoftware Engineer"
        name = extract_name(text)
        # Should return John Doe, not the email
        if name:
            assert "@" not in name

    def test_extract_name_ignores_url(self):
        from app.services.resume_extractor import extract_name
        text = "https://linkedin.com/in/johndoe\nJohn Doe\nEngineer"
        name = extract_name(text)
        if name:
            assert "http" not in name

    def test_extract_name_two_word_name(self):
        from app.services.resume_extractor import extract_name
        text = "Jane Smith\njane@email.com\nDeveloper"
        name = extract_name(text)
        assert name is not None
        assert "Jane" in name or "Smith" in name

    def test_extract_name_single_letter_initials(self):
        from app.services.resume_extractor import extract_name
        text = "G B Harsha Vardhan\nSenior Undergraduate\nIIT Gandhinagar"
        name = extract_name(text)
        assert name == "G B Harsha Vardhan"

    def test_extract_name_ignores_senior_undergraduate(self):
        from app.services.resume_extractor import extract_name
        text = "Senior Undergraduate\nharshagb.itis@gmail.com\nIIT Gandhinagar"
        name = extract_name(text)
        assert name is None or name != "Senior Undergraduate"


# ---------------------------------------------------------------------------
# Tests: Email Extraction
# ---------------------------------------------------------------------------

class TestEmailExtraction:
    def test_extract_email_basic(self):
        from app.services.resume_extractor import extract_email
        email = extract_email(SAMPLE_RESUME_TEXT)
        assert email == "john.doe@example.com"

    def test_extract_email_gmail(self):
        from app.services.resume_extractor import extract_email
        email = extract_email("Name\nuser.name+filter@gmail.com")
        assert email == "user.name+filter@gmail.com"

    def test_extract_email_none_when_missing(self):
        from app.services.resume_extractor import extract_email
        email = extract_email("John Doe\nSoftware Engineer\nPython Developer")
        assert email is None

    def test_extract_email_lowercase(self):
        from app.services.resume_extractor import extract_email
        email = extract_email("JOHN.DOE@COMPANY.COM")
        assert email == "john.doe@company.com"

    def test_extract_email_complex(self):
        from app.services.resume_extractor import extract_email
        email = extract_email("Contact: john_doe-123@sub.domain.co.in")
        assert "john_doe-123@sub.domain.co.in" == email


# ---------------------------------------------------------------------------
# Tests: Phone Extraction
# ---------------------------------------------------------------------------

class TestPhoneExtraction:
    def test_extract_phone_basic(self):
        from app.services.resume_extractor import extract_phone
        phone = extract_phone(SAMPLE_RESUME_TEXT)
        assert phone is not None
        assert "9876543210" in phone.replace(" ", "").replace("-", "")

    def test_extract_phone_with_country_code(self):
        from app.services.resume_extractor import extract_phone
        phone = extract_phone("Phone: +91-9876543210")
        assert phone is not None

    def test_extract_phone_none_when_missing(self):
        from app.services.resume_extractor import extract_phone
        phone = extract_phone("John Doe\njohn@email.com\nSoftware Engineer")
        assert phone is None

    def test_extract_phone_us_format(self):
        from app.services.resume_extractor import extract_phone
        phone = extract_phone("Call me at 555-867-5309")
        assert phone is not None


# ---------------------------------------------------------------------------
# Tests: Skills Extraction
# ---------------------------------------------------------------------------

class TestSkillsExtraction:
    def test_extract_skills_basic(self):
        from app.services.skill_extractor import extract_skills
        skills = extract_skills(SAMPLE_RESUME_TEXT)
        assert isinstance(skills, list)
        assert len(skills) > 0

    def test_extract_skills_python(self):
        from app.services.skill_extractor import extract_skills
        skills = extract_skills("Skills: Python, Java, SQL")
        normalized = [s.lower() for s in skills]
        assert "python" in normalized

    def test_extract_skills_normalisation_sklearn(self):
        from app.services.skill_extractor import extract_skills
        skills = extract_skills("I use sklearn for machine learning.")
        assert "Scikit-learn" in skills

    def test_extract_skills_normalisation_js(self):
        from app.services.skill_extractor import extract_skills
        skills = extract_skills("Frontend: JS, React, TypeScript")
        assert "JavaScript" in skills

    def test_extract_skills_normalisation_postgres(self):
        from app.services.skill_extractor import extract_skills
        skills = extract_skills("Database: postgres, redis")
        assert "PostgreSQL" in skills

    def test_extract_skills_no_duplicates(self):
        from app.services.skill_extractor import extract_skills
        skills = extract_skills("Python python PYTHON")
        python_count = sum(1 for s in skills if s == "Python")
        assert python_count <= 1

    def test_extract_skills_case_insensitive(self):
        from app.services.skill_extractor import extract_skills
        skills = extract_skills("PYTHON, DOCKER, KUBERNETES")
        normalized = [s.lower() for s in skills]
        assert "python" in normalized
        assert "docker" in normalized

    def test_extract_skills_empty_text(self):
        from app.services.skill_extractor import extract_skills
        skills = extract_skills("")
        assert skills == []

    def test_extract_skills_returns_list(self):
        from app.services.skill_extractor import extract_skills
        skills = extract_skills("No skills here.")
        assert isinstance(skills, list)


# ---------------------------------------------------------------------------
# Tests: LinkedIn Extraction
# ---------------------------------------------------------------------------

class TestLinkedInExtraction:
    def test_extract_linkedin_full_url(self):
        from app.services.resume_extractor import extract_linkedin
        linkedin = extract_linkedin("Profile: https://linkedin.com/in/johndoe")
        assert linkedin == "https://linkedin.com/in/johndoe"

    def test_extract_linkedin_without_https(self):
        from app.services.resume_extractor import extract_linkedin
        linkedin = extract_linkedin("linkedin.com/in/janedoe")
        assert linkedin is not None
        assert "linkedin.com/in/janedoe" in linkedin

    def test_extract_linkedin_with_www(self):
        from app.services.resume_extractor import extract_linkedin
        linkedin = extract_linkedin("www.linkedin.com/in/user123")
        assert linkedin is not None

    def test_extract_linkedin_none_when_missing(self):
        from app.services.resume_extractor import extract_linkedin
        linkedin = extract_linkedin("John Doe\njohn@email.com\nSoftware Engineer")
        assert linkedin is None

    def test_extract_linkedin_from_sample(self):
        from app.services.resume_extractor import extract_linkedin
        linkedin = extract_linkedin(SAMPLE_RESUME_TEXT)
        assert linkedin is not None
        assert "linkedin" in linkedin.lower()


# ---------------------------------------------------------------------------
# Tests: GitHub Extraction
# ---------------------------------------------------------------------------

class TestGitHubExtraction:
    def test_extract_github_full_url(self):
        from app.services.resume_extractor import extract_github
        github = extract_github("Code: https://github.com/johndoe")
        assert github == "https://github.com/johndoe"

    def test_extract_github_without_https(self):
        from app.services.resume_extractor import extract_github
        github = extract_github("github.com/janedoe")
        assert github is not None
        assert "github.com/janedoe" in github

    def test_extract_github_none_when_missing(self):
        from app.services.resume_extractor import extract_github
        github = extract_github("John Doe\njohn@email.com\nSoftware Engineer")
        assert github is None

    def test_extract_github_from_sample(self):
        from app.services.resume_extractor import extract_github
        github = extract_github(SAMPLE_RESUME_TEXT)
        assert github is not None
        assert "github" in github.lower()


# ---------------------------------------------------------------------------
# Tests: Education Extraction
# ---------------------------------------------------------------------------

class TestEducationExtraction:
    def test_extract_education_returns_list(self):
        from app.services.education_extractor import extract_education
        result = extract_education(SAMPLE_RESUME_TEXT)
        assert isinstance(result, list)

    def test_extract_education_finds_degree(self):
        from app.services.education_extractor import extract_education
        result = extract_education(SAMPLE_RESUME_TEXT)
        assert len(result) > 0
        degrees = [e.get("degree") for e in result if e.get("degree")]
        assert any("B.Tech" in (d or "") or "btech" in (d or "").lower() for d in degrees)

    def test_extract_education_finds_institution(self):
        from app.services.education_extractor import extract_education
        text = """
Education
B.Tech in Computer Science
ABC University
2018 - 2022
"""
        result = extract_education(text)
        assert len(result) > 0
        institutions = [e.get("institution") for e in result if e.get("institution")]
        assert any("ABC" in (i or "") or "University" in (i or "") for i in institutions)

    def test_extract_education_multiple_entries(self):
        from app.services.education_extractor import extract_education
        text = """
Education

M.Tech in AI
IIT Bombay
2019 - 2021

B.Tech in CS
NIT Trichy
2015 - 2019
"""
        result = extract_education(text)
        assert len(result) >= 1

    def test_extract_education_empty_text(self):
        from app.services.education_extractor import extract_education
        result = extract_education("")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Tests: Education Extraction — Extended (new degree types & strict rules)
# ---------------------------------------------------------------------------

class TestEducationExtractionExtended:
    """Covers 10th/12th/Diploma/SSC/HSC and the strict no-guess rules."""

    def test_extracts_10th_with_school(self):
        from app.services.education_extractor import extract_education
        text = """
Education
10th Standard
Sri Chaitanya School
2013 - 2014
"""
        result = extract_education(text)
        assert len(result) >= 1
        degrees = [e["degree"] for e in result if e["degree"]]
        assert any("10th" in (d or "") for d in degrees)

    def test_extracts_12th_intermediate(self):
        from app.services.education_extractor import extract_education
        text = """
Education
Intermediate (12th)
Narayana Junior College
2015 - 2017
"""
        result = extract_education(text)
        assert len(result) >= 1
        degrees = [e["degree"] for e in result if e["degree"]]
        assert any("Intermediate" in (d or "") or "12th" in (d or "") for d in degrees)

    def test_extracts_b_tech_with_space(self):
        from app.services.education_extractor import extract_education
        text = """
EDUCATION
B. Tech in Computer Science & Engineering (2023 - Present)
Vel Tech Rangarajan Dr. Sagunthala R&D Institute of Science and Technology CGPA: 9.2
"""
        result = extract_education(text)
        assert len(result) >= 1
        degree = result[0]["degree"]
        institution = result[0]["institution"]
        assert degree is not None and "B. Tech" in degree
        assert institution is not None and "Vel Tech" in institution
        assert "CGPA" not in institution

    def test_extracts_diploma(self):
        from app.services.education_extractor import extract_education
        text = """
Education
Diploma in Computer Engineering
XYZ Polytechnic College
2016 - 2019
"""
        result = extract_education(text)
        assert len(result) >= 1
        degrees = [e["degree"] for e in result if e["degree"]]
        assert any("Diploma" in (d or "") for d in degrees)

    def test_extracts_ssc(self):
        from app.services.education_extractor import extract_education
        text = """
Education
SSC
ZP High School
2012 - 2013
"""
        result = extract_education(text)
        assert len(result) >= 1
        degrees = [e["degree"] for e in result if e["degree"]]
        assert any("SSC" in (d or "") for d in degrees)

    def test_institution_only_returns_null_degree(self):
        from app.services.education_extractor import extract_education
        text = """
Education
Narayana Junior College
2014 - 2016
"""
        result = extract_education(text)
        assert len(result) >= 1
        entry = result[0]
        assert entry["institution"] is not None
        assert entry["degree"] is None

    def test_degree_only_returns_null_institution(self):
        from app.services.education_extractor import extract_education
        text = """
Education
MBA
2020 - 2022
"""
        result = extract_education(text)
        assert len(result) >= 1
        entry = result[0]
        assert entry["degree"] is not None
        assert "MBA" in entry["degree"]
        assert entry["institution"] is None

    def test_neither_degree_nor_institution_skipped(self):
        from app.services.education_extractor import extract_education
        text = """
Education
2020 - 2022
CGPA: 8.5
Percentage: 85%
"""
        result = extract_education(text)
        assert result == []

    def test_inline_format_btech_university(self):
        from app.services.education_extractor import extract_education
        text = """
Education
B.Tech | ABC University
"""
        result = extract_education(text)
        assert len(result) >= 1
        assert result[0]["degree"] is not None
        assert result[0]["institution"] is not None

    def test_long_institution_name(self):
        from app.services.education_extractor import extract_education
        text = """
Education
B.Tech in Computer Science
Vel Tech Rangarajan Dr. Sagunthala R&D Institute of Science and Technology
2019 - 2023
"""
        result = extract_education(text)
        assert len(result) >= 1
        institution = result[0]["institution"]
        assert institution is not None
        assert "Vel Tech" in institution or "Institute" in institution

    def test_multiple_levels_10th_12th_btech(self):
        from app.services.education_extractor import extract_education
        text = """
Education
10th Standard
Sri Chaitanya School
2013 - 2014

Intermediate
Narayana Junior College
2014 - 2016

B.Tech in ECE
JNTU Hyderabad
2016 - 2020
"""
        result = extract_education(text)
        assert len(result) >= 3
        degrees = [e["degree"] for e in result if e["degree"]]
        degree_text = " ".join(degrees).lower()
        assert "10th" in degree_text or "standard" in degree_text
        assert "b.tech" in degree_text or "btech" in degree_text

    def test_hsc_sslc_are_detected(self):
        from app.services.education_extractor import extract_education
        text = """
Education
HSC
State Board
2016 - 2017
"""
        result = extract_education(text)
        degrees = [e["degree"] for e in result if e["degree"]]
        assert any("HSC" in (d or "") for d in degrees)

    def test_entry_keys_always_present(self):
        """Every returned entry must have both 'degree' and 'institution' keys."""
        from app.services.education_extractor import extract_education
        result = extract_education(SAMPLE_RESUME_TEXT)
        for entry in result:
            assert "degree" in entry
            assert "institution" in entry


# ---------------------------------------------------------------------------
# Tests: Total Experience Years
# ---------------------------------------------------------------------------

class TestTotalExperienceYears:
    """Tests for the calculate_total_experience() function."""

    def test_no_experience_returns_zero(self):
        from app.services.experience_calculator import calculate_total_experience
        assert calculate_total_experience([]) == 0.0

    def test_empty_duration_returns_zero(self):
        from app.services.experience_calculator import calculate_total_experience
        result = calculate_total_experience([{"job_title": "Dev", "company": "X", "duration": None}])
        assert result == 0.0

    def test_year_only_range(self):
        from app.services.experience_calculator import calculate_total_experience
        result = calculate_total_experience([{"duration": "2022 - 2024"}])
        assert result > 0

    def test_month_year_range(self):
        from app.services.experience_calculator import calculate_total_experience
        result = calculate_total_experience([{"duration": "Jan 2022 - Jan 2023"}])
        assert abs(result - 1.0) < 0.1

    def test_present_keyword(self):
        from app.services.experience_calculator import calculate_total_experience
        from datetime import date
        result = calculate_total_experience([{"duration": "Jan 2023 - Present"}])
        expected_max = (date.today().year - 2023 + 1) + 1.0
        assert 0 < result <= expected_max

    def test_overlapping_jobs_not_double_counted(self):
        from app.services.experience_calculator import calculate_total_experience
        # Two jobs that overlap completely — should count as one period
        result = calculate_total_experience([
            {"duration": "Jan 2022 - Jan 2024"},
            {"duration": "Jun 2022 - Jun 2023"},   # fully inside first
        ])
        # Should be ~2 years, not ~3
        assert result < 2.5

    def test_non_overlapping_jobs_summed(self):
        from app.services.experience_calculator import calculate_total_experience
        result = calculate_total_experience([
            {"duration": "Jan 2020 - Jan 2021"},
            {"duration": "Jan 2022 - Jan 2023"},
        ])
        assert abs(result - 2.0) < 0.2

    def test_result_is_float(self):
        from app.services.experience_calculator import calculate_total_experience
        result = calculate_total_experience([{"duration": "2020 - 2022"}])
        assert isinstance(result, float)

    def test_result_rounded_to_one_decimal(self):
        from app.services.experience_calculator import calculate_total_experience
        result = calculate_total_experience([{"duration": "Jan 2022 - Jul 2022"}])
        assert result == round(result, 1)

    def test_resume_response_has_total_experience_field(self):
        from app.services.resume_extractor import extract_resume_data
        result = extract_resume_data(SAMPLE_RESUME_TEXT)
        assert hasattr(result, "total_experience_years")
        assert isinstance(result.total_experience_years, float)
        assert result.total_experience_years >= 0.0

    def test_no_experience_in_resume_returns_zero(self):
        from app.services.resume_extractor import extract_resume_data
        result = extract_resume_data("Jane Doe\njane@email.com\nSkills: Python")
        assert result.total_experience_years == 0.0



class TestExperienceExtraction:
    def test_extract_experience_returns_list(self):
        from app.services.experience_extractor import extract_experience
        result = extract_experience(SAMPLE_RESUME_TEXT)
        assert isinstance(result, list)

    def test_extract_experience_finds_entry(self):
        from app.services.experience_extractor import extract_experience
        result = extract_experience(SAMPLE_RESUME_TEXT)
        assert len(result) > 0

    def test_extract_experience_has_keys(self):
        from app.services.experience_extractor import extract_experience
        result = extract_experience(SAMPLE_RESUME_TEXT)
        if result:
            entry = result[0]
            assert "job_title" in entry
            assert "company" in entry
            assert "duration" in entry

    def test_extract_experience_duration(self):
        from app.services.experience_extractor import extract_experience
        text = """
Work Experience

Software Engineer
ABC Corp
May 2022 - July 2023

- Developed features
"""
        result = extract_experience(text)
        assert len(result) > 0
        durations = [e.get("duration") for e in result if e.get("duration")]
        assert len(durations) > 0

    def test_extract_experience_empty_text(self):
        from app.services.experience_extractor import extract_experience
        result = extract_experience("")
        assert isinstance(result, list)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Tests: Missing Fields
# ---------------------------------------------------------------------------

class TestMissingFields:
    def test_missing_all_fields(self):
        from app.services.resume_extractor import extract_resume_data
        result = extract_resume_data("This is a text document with no resume info.")
        assert result.name is None
        assert result.email is None
        assert result.phone is None
        assert result.skills == []
        assert result.education == []
        assert result.experience == []
        assert result.linkedin is None
        assert result.github is None

    def test_partial_fields_present(self):
        from app.services.resume_extractor import extract_resume_data
        result = extract_resume_data(MINIMAL_RESUME_TEXT)
        assert result.email is not None
        assert result.phone is not None


# ---------------------------------------------------------------------------
# Tests: Text Cleaner
# ---------------------------------------------------------------------------

class TestTextCleaner:
    def test_clean_text_removes_extra_whitespace(self):
        from app.utils.text_cleaner import clean_text
        result = clean_text("Hello   World")
        assert "  " not in result

    def test_clean_text_handles_pdf_ligatures(self):
        from app.utils.text_cleaner import clean_text
        result = clean_text("pro\ufb01le")  # fi ligature
        assert "fi" in result

    def test_clean_text_normalises_dashes(self):
        from app.utils.text_cleaner import clean_text
        result = clean_text("2022\u20132023")  # en-dash
        assert "2022" in result
        assert "2023" in result

    def test_clean_text_empty_string(self):
        from app.utils.text_cleaner import clean_text
        result = clean_text("")
        assert result == ""

    def test_get_lines_filters_empty(self):
        from app.utils.text_cleaner import get_lines
        lines = get_lines("Hello\n\nWorld\n\n")
        assert "" not in lines
        assert len(lines) == 2
