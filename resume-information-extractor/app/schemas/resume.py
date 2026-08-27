"""
Pydantic / SQLModel schemas for the resume extraction API.

Uses:
  - SQLModel for models (combines Pydantic + SQLAlchemy)
  - EmailStr from email-validator for email validation
  - Field with constraints (min_length, max_length, ge, le, pattern)
  - field_validator for custom validation logic
  - Proper type annotations and descriptions

These are API response models only (table=False) — no database table is created.
If you need to persist resume data later, set table=True and add a primary key.
"""

from __future__ import annotations

from typing import Optional

from pydantic import EmailStr, field_validator, HttpUrl
from sqlmodel import Field, SQLModel


# ---------------------------------------------------------------------------
# Education Model
# ---------------------------------------------------------------------------

class Education(SQLModel):
    """
    A single education record extracted from a resume.

    Strict rules:
      - If degree found    → degree is a non-empty string.
      - If institution found → institution is a non-empty string.
      - Neither found       → this entry is not created at all.
      - Never guess or invent missing data.
    """

    degree: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Academic degree or qualification, e.g. B.Tech, 10th, MBA",
    )
    institution: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=300,
        description="Name of the school, college, or university",
    )

    @field_validator("degree", "institution", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: object) -> object:
        """Convert empty or whitespace-only strings to None, split on newline, and enforce max length."""
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
            if "\n" in v:
                v = v.split("\n")[0].strip()
            return v[:200] if len(v) > 200 else v
        return v


# ---------------------------------------------------------------------------
# Experience Model
# ---------------------------------------------------------------------------

class Experience(SQLModel):
    """
    A single work or internship experience entry.
    """

    job_title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Job title or role, e.g. Software Engineer Intern",
    )
    company: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Employer or company name",
    )
    duration: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Employment period, e.g. 'Jan 2024 - May 2024' or '2022 - Present'",
    )

    @field_validator("job_title", "company", "duration", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: object) -> object:
        """Convert empty or whitespace-only strings to None, split on newline, and enforce max length."""
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
            if "\n" in v:
                v = v.split("\n")[0].strip()
            return v[:200] if len(v) > 200 else v
        return v


# ---------------------------------------------------------------------------
# Resume Response Model
# ---------------------------------------------------------------------------

class ResumeResponse(SQLModel):
    """
    Top-level response model returned by the resume extraction endpoint.

    Uses:
      - EmailStr for validated email (via email-validator, not regex)
      - Field constraints for string lengths and numeric ranges
      - field_validator for custom cleanup logic
    """

    name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Candidate's full name",
    )

    email: Optional[EmailStr] = Field(
        default=None,
        description=(
            "Primary email address — validated using the email-validator library, "
            "not regex. Ensures RFC 5322 compliance and valid domain format."
        ),
    )

    phone: Optional[str] = Field(
        default=None,
        min_length=7,
        max_length=20,
        description="Primary phone number (7-20 characters including country code)",
    )

    skills: list[str] = Field(
        default_factory=list,
        description="List of technical skills detected from the resume",
    )

    education: list[Education] = Field(
        default_factory=list,
        description="Education history — each entry has degree and/or institution",
    )

    experience: list[Experience] = Field(
        default_factory=list,
        description="Work or internship experience entries",
    )

    linkedin: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=200,
        description="LinkedIn profile URL",
    )

    github: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=200,
        description="GitHub profile URL",
    )

    total_experience_years: float = Field(
        default=0.0,
        ge=0.0,
        le=60.0,
        description=(
            "Total years of work experience computed from employment date ranges. "
            "Overlapping jobs are merged (not double-counted). "
            "Present/Current is treated as today. Rounded to 1 decimal place."
        ),
    )

    # ── Custom validators ────────────────────────────────────────────────────

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, v: object) -> object:
        """Strip whitespace; reject empty strings."""
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: object) -> object:
        """Normalise email to lowercase before EmailStr validation."""
        if isinstance(v, str):
            v = v.strip().lower()
            return v if v else None
        return v

    @field_validator("phone", mode="before")
    @classmethod
    def clean_phone(cls, v: object) -> object:
        """Strip whitespace from phone numbers."""
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v

    @field_validator("linkedin", "github", mode="before")
    @classmethod
    def clean_url(cls, v: object) -> object:
        """Strip whitespace and trailing slashes from URLs."""
        if isinstance(v, str):
            v = v.strip().rstrip("/")
            return v if v else None
        return v

    @field_validator("skills", mode="before")
    @classmethod
    def deduplicate_skills(cls, v: object) -> object:
        """Remove duplicate skills while preserving order."""
        if isinstance(v, list):
            seen: set[str] = set()
            result: list[str] = []
            for s in v:
                key = s.lower() if isinstance(s, str) else s
                if key not in seen:
                    seen.add(key)
                    result.append(s)
            return result
        return v

    @field_validator("total_experience_years", mode="before")
    @classmethod
    def round_experience(cls, v: object) -> object:
        """Ensure experience is rounded to 1 decimal place."""
        if isinstance(v, (int, float)):
            return round(float(v), 1)
        return v

    # ── Config ───────────────────────────────────────────────────────────────

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "John Doe",
                "email": "john.doe@email.com",
                "phone": "+91 9876543210",
                "skills": ["Python", "SQL", "Machine Learning"],
                "education": [
                    {"degree": "B.Tech", "institution": "ABC University"}
                ],
                "experience": [
                    {
                        "job_title": "Software Engineer Intern",
                        "company": "XYZ Technologies",
                        "duration": "May 2025 - July 2025",
                    }
                ],
                "linkedin": "https://linkedin.com/in/johndoe",
                "github": "https://github.com/johndoe",
                "total_experience_years": 2.5,
            }
        }
    }
