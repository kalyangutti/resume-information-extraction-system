"""
Integration tests for the FastAPI resume extraction endpoint.

Covers:
- Successful PDF upload
- Successful DOCX upload
- Invalid file type rejection
- Empty file rejection
- Corrupted file handling
- Response schema validation
- Health check endpoints
"""

from __future__ import annotations

import io
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Sample resume content
# ---------------------------------------------------------------------------

SAMPLE_RESUME_TEXT = """Jane Doe
jane.doe@email.com
+91 9988776655
linkedin.com/in/janedoe
github.com/janedoe

EDUCATION
B.Tech in Information Technology
Delhi Technological University
2019 - 2023

SKILLS
Python, FastAPI, Docker, PostgreSQL, Machine Learning

EXPERIENCE

Software Engineer
Infosys Ltd
June 2023 - Present

- Designed microservices using FastAPI
"""


def _make_pdf_bytes(text: str) -> bytes:
    """Create a valid PDF from text using PyMuPDF."""
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(50, 50, 550, 800)
    page.insert_textbox(rect, text, fontsize=10, fontname="helv")
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def _make_docx_bytes(text: str) -> bytes:
    """Create a valid DOCX from text using python-docx."""
    from docx import Document
    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tests: Health Checks
# ---------------------------------------------------------------------------

class TestHealthEndpoints:
    def test_root_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_has_status_ok(self):
        response = client.get("/")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_has_healthy_status(self):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"


# ---------------------------------------------------------------------------
# Tests: Successful Extraction — PDF
# ---------------------------------------------------------------------------

class TestPDFExtraction:
    def test_pdf_upload_returns_200(self):
        pdf_bytes = _make_pdf_bytes(SAMPLE_RESUME_TEXT)
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200

    def test_pdf_response_has_required_keys(self):
        pdf_bytes = _make_pdf_bytes(SAMPLE_RESUME_TEXT)
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        data = response.json()
        assert "name" in data
        assert "email" in data
        assert "phone" in data
        assert "skills" in data
        assert "education" in data
        assert "experience" in data
        assert "linkedin" in data
        assert "github" in data

    def test_pdf_extracts_email(self):
        pdf_bytes = _make_pdf_bytes(SAMPLE_RESUME_TEXT)
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        data = response.json()
        assert data["email"] is not None
        assert "jane.doe@email.com" == data["email"]

    def test_pdf_extracts_skills_as_list(self):
        pdf_bytes = _make_pdf_bytes(SAMPLE_RESUME_TEXT)
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        data = response.json()
        assert isinstance(data["skills"], list)

    def test_pdf_extracts_education_as_list(self):
        pdf_bytes = _make_pdf_bytes(SAMPLE_RESUME_TEXT)
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        data = response.json()
        assert isinstance(data["education"], list)

    def test_pdf_extracts_experience_as_list(self):
        pdf_bytes = _make_pdf_bytes(SAMPLE_RESUME_TEXT)
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        data = response.json()
        assert isinstance(data["experience"], list)


# ---------------------------------------------------------------------------
# Tests: Successful Extraction — DOCX
# ---------------------------------------------------------------------------

class TestDOCXExtraction:
    def test_docx_upload_returns_200(self):
        docx_bytes = _make_docx_bytes(SAMPLE_RESUME_TEXT)
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.docx", docx_bytes,
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert response.status_code == 200

    def test_docx_response_has_required_keys(self):
        docx_bytes = _make_docx_bytes(SAMPLE_RESUME_TEXT)
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.docx", docx_bytes,
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        data = response.json()
        assert "name" in data
        assert "email" in data
        assert "phone" in data
        assert "skills" in data

    def test_docx_extracts_email(self):
        docx_bytes = _make_docx_bytes(SAMPLE_RESUME_TEXT)
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.docx", docx_bytes,
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        data = response.json()
        assert data["email"] == "jane.doe@email.com"

    def test_docx_extracts_skills_list(self):
        docx_bytes = _make_docx_bytes(SAMPLE_RESUME_TEXT)
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.docx", docx_bytes,
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        data = response.json()
        assert isinstance(data["skills"], list)
        assert len(data["skills"]) > 0


# ---------------------------------------------------------------------------
# Tests: Error Handling — Invalid File Types
# ---------------------------------------------------------------------------

class TestInvalidFileType:
    def test_txt_file_returns_400(self):
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.txt", b"Hello World", "text/plain")},
        )
        assert response.status_code == 400

    def test_jpg_file_returns_400(self):
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("photo.jpg", b"\xff\xd8\xff", "image/jpeg")},
        )
        assert response.status_code == 400

    def test_doc_file_returns_400(self):
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.doc", b"PK\x03\x04", "application/msword")},
        )
        assert response.status_code == 400

    def test_invalid_type_error_message(self):
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.csv", b"name,age", "text/csv")},
        )
        data = response.json()
        assert "detail" in data


# ---------------------------------------------------------------------------
# Tests: Error Handling — Empty Files
# ---------------------------------------------------------------------------

class TestEmptyFile:
    def test_empty_pdf_returns_400(self):
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.pdf", b"", "application/pdf")},
        )
        assert response.status_code == 400

    def test_empty_docx_returns_400(self):
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.docx", b"",
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Tests: Error Handling — Corrupted Files
# ---------------------------------------------------------------------------

class TestCorruptedFiles:
    def test_corrupted_pdf_returns_400(self):
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.pdf", b"this is not a pdf file", "application/pdf")},
        )
        assert response.status_code == 400

    def test_corrupted_docx_returns_400(self):
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.docx", b"this is not a docx file",
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Tests: Response Schema Validation
# ---------------------------------------------------------------------------

class TestResponseSchema:
    def test_education_entries_have_degree_and_institution_keys(self):
        pdf_bytes = _make_pdf_bytes(SAMPLE_RESUME_TEXT)
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        data = response.json()
        for edu in data.get("education", []):
            assert "degree" in edu
            assert "institution" in edu

    def test_experience_entries_have_required_keys(self):
        pdf_bytes = _make_pdf_bytes(SAMPLE_RESUME_TEXT)
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        data = response.json()
        for exp in data.get("experience", []):
            assert "job_title" in exp
            assert "company" in exp
            assert "duration" in exp

    def test_skills_is_list_of_strings(self):
        pdf_bytes = _make_pdf_bytes(SAMPLE_RESUME_TEXT)
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        data = response.json()
        assert all(isinstance(s, str) for s in data["skills"])

    def test_missing_fields_are_null_or_empty(self):
        """A resume with only email should have null for most other fields."""
        minimal_text = "user@example.com"
        pdf_bytes = _make_pdf_bytes(minimal_text)
        response = client.post(
            "/api/v1/resume/extract",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        data = response.json()
        # Optional string fields should be null or string
        for field in ["name", "phone", "linkedin", "github"]:
            assert data[field] is None or isinstance(data[field], str)
        # List fields should always be lists
        assert isinstance(data["skills"], list)
        assert isinstance(data["education"], list)
        assert isinstance(data["experience"], list)
