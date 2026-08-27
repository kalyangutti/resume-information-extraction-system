"""
Regex patterns used across the resume extraction pipeline.

All reusable patterns are centralised here to avoid duplication.
"""

import re

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_PATTERN: re.Pattern = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Phone  (supports international formats, Indian numbers, dashes, dots, spaces)
# ---------------------------------------------------------------------------
PHONE_PATTERN: re.Pattern = re.compile(
    r"""
    (?:
        (?:\+?(\d{1,3})[\s\-.]?)?          # optional country code
        (?:\((\d{1,4})\)[\s\-.]?)?          # optional area code in parens
        (\d{3,5})                           # first segment
        [\s\-.]                             # separator
        (\d{3,4})                           # second segment
        (?:[\s\-.](\d{4}))?                 # optional third segment
    )
    """,
    re.VERBOSE,
)

# Simpler fallback phone pattern — matches 10+ digit sequences with separators
PHONE_SIMPLE_PATTERN: re.Pattern = re.compile(
    r"(?:\+?\d[\d\s\-.()/]{7,}\d)",
)

# ---------------------------------------------------------------------------
# LinkedIn
# ---------------------------------------------------------------------------
LINKEDIN_PATTERN: re.Pattern = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_\-%.]+/?",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------
GITHUB_PATTERN: re.Pattern = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_\-%.]+/?",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
URL_PATTERN: re.Pattern = re.compile(
    r"https?://\S+|www\.\S+",
    re.IGNORECASE,
)

# Lines that look like section headings (ALL CAPS or Title Case followed by colon/newline)
SECTION_HEADING_PATTERN: re.Pattern = re.compile(
    r"^[A-Z][A-Za-z\s]{2,40}(?::|$)",
)

# Date/duration patterns for experience extraction
DATE_RANGE_PATTERN: re.Pattern = re.compile(
    r"""
    (?:
        (?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|
           Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)
        [\s,]*\d{4}
    )
    \s*[-–—to]+\s*
    (?:
        (?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|
           Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)
        [\s,]*\d{4}
        |Present|Current|Till\s+Date|Ongoing
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

YEAR_RANGE_PATTERN: re.Pattern = re.compile(
    r"\b(20\d{2}|19\d{2})\s*[-–—to]+\s*(20\d{2}|19\d{2}|Present|Current|Ongoing)\b",
    re.IGNORECASE,
)

# Degree keywords for education extraction
# Covers Indian school (10th/12th/SSC/HSC/Intermediate/Diploma) through postgraduate.
DEGREE_PATTERN: re.Pattern = re.compile(
    r"""
    \b(
        # ── School qualifications ──────────────────────────────
        10th(?:\s+(?:Standard|Grade|Class|Pass))?|
        12th(?:\s+(?:Standard|Grade|Class|Pass))?|
        Class\s+(?:X|XII|10|12)|
        SSC|SSLC|
        HSC|Higher\s+Secondary|
        Intermediate|Inter|
        Secondary(?:\s+School)?(?:\s+Certificate)?|
        Higher\s+Secondary(?:\s+Certificate)?|
        Senior\s+Secondary|
        Matriculation|Matric|

        # ── Diploma ────────────────────────────────────────────
        Diploma(?:\s+in\s+[\w\s]+)?|Polytechnic\s+Diploma|

        # ── Bachelor degrees ───────────────────────────────────
        B\.?Tech(?:\s+in\s+[\w\s&]+)?|
        B\.?E\.?(?:\s+in\s+[\w\s&]+)?|
        B\.?Sc\.?(?:\s+in\s+[\w\s&]+)?|
        BCA|B\.?Com(?:\s+in\s+[\w\s&]+)?|
        BBA(?:\s+in\s+[\w\s&]+)?|BA(?:\s+in\s+[\w\s&]+)?|
        B\.?Arch|B\.?Des|B\.?Ed\.?|B\.?Pharm|
        B\.?Voc|B\.?HM|BHM|
        MBBS|BDS|BAMS|BHMS|B\.?Pharm|
        LLB|LLM|

        # ── Master degrees ─────────────────────────────────────
        M\.?Tech(?:\s+in\s+[\w\s&]+)?|
        M\.?E\.?(?:\s+in\s+[\w\s&]+)?|
        M\.?Sc\.?(?:\s+in\s+[\w\s&]+)?|
        MCA(?:\s+in\s+[\w\s&]+)?|MBA(?:\s+in\s+[\w\s&]+)?|
        M\.?Com(?:\s+in\s+[\w\s&]+)?|MA(?:\s+in\s+[\w\s&]+)?|
        M\.?Arch|M\.?Des|M\.?Ed\.?|
        MD|MS(?:\s+in\s+[\w\s&]+)?|

        # ── Doctorate ──────────────────────────────────────────
        Ph\.?D\.?(?:\s+in\s+[\w\s&]+)?|
        Doctor\s+of\s+Philosophy|
        Doctor\s+of\s+Medicine|

        # ── Generic spelled-out degrees ────────────────────────
        Bachelor(?:s?\s+of\s+[\w\s&]+)?|
        Master(?:s?\s+of\s+[\w\s&]+)?|
        Associate(?:s?\s+of\s+[\w\s&]+)?
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Education section headings
EDUCATION_SECTION_PATTERN: re.Pattern = re.compile(
    r"^(?:Education(?:al)?(?:\s+Background|\s+Details|\s+Qualification)?|"
    r"Academic\s+(?:Background|Qualifications?|Details|Profile)|"
    r"Qualifications?|Academics?|Scholastic\s+(?:Details|Record)|"
    r"Educational\s+Credentials?)\s*:?\s*$",
    re.IGNORECASE,
)

# Experience section headings
EXPERIENCE_SECTION_PATTERN: re.Pattern = re.compile(
    r"^(?:(?:Work\s+)?Experience|Employment(?:\s+History)?|"
    r"Professional\s+Experience|Internship(?:s)?|Work\s+History|Career\s+History|"
    r"Professional\s+Background)\s*:?\s*$",
    re.IGNORECASE,
)
