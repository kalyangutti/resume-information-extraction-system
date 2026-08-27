"""
Text cleaning and normalisation utilities for resume text.

Handles PDF extraction artifacts, excessive whitespace, and common
formatting issues encountered in real-world resumes.
"""

import re
import unicodedata


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """
    Apply full normalisation pipeline to raw extracted resume text.

    Steps:
    1. Unicode normalisation (NFKC)
    2. Replace common PDF ligature / special-character artifacts
    3. Normalise line endings
    4. Remove excessive blank lines (max 2 consecutive)
    5. Strip leading/trailing whitespace per line
    6. Collapse multiple spaces within a line

    Args:
        text: Raw text extracted from a PDF or DOCX file.

    Returns:
        Cleaned, normalised text string.
    """
    if not text:
        return ""

    # 1. Unicode normalisation
    text = unicodedata.normalize("NFKC", text)

    # 2. Replace common PDF artifacts
    text = _replace_pdf_artifacts(text)

    # 3. Normalise line endings to \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 4. Strip each line and collapse internal spaces
    lines = [_collapse_spaces(line.strip()) for line in text.split("\n")]

    # 5. Collapse consecutive blank lines (keep at most 2)
    lines = _collapse_blank_lines(lines)

    return "\n".join(lines).strip()


def get_lines(text: str) -> list[str]:
    """Return non-empty, stripped lines from cleaned text."""
    return [line for line in text.split("\n") if line.strip()]


def get_first_lines(text: str, n: int = 10) -> list[str]:
    """Return first *n* non-empty lines from text."""
    return get_lines(text)[:n]


def normalise_whitespace(text: str) -> str:
    """Collapse all whitespace (including newlines) to single spaces."""
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_PDF_ARTIFACTS: list[tuple[str, str]] = [
    # Ligatures
    ("\ufb01", "fi"),
    ("\ufb02", "fl"),
    ("\ufb00", "ff"),
    ("\ufb03", "ffi"),
    ("\ufb04", "ffl"),
    # Dashes — normalise to ASCII hyphen for simplicity
    ("\u2013", "-"),
    ("\u2014", "-"),
    ("\u2015", "-"),
    # Bullets / list markers
    ("\u2022", "-"),
    ("\u25cf", "-"),
    ("\u2023", "-"),
    ("\u25e6", "-"),
    # Quotes
    ("\u2018", "'"),
    ("\u2019", "'"),
    ("\u201c", '"'),
    ("\u201d", '"'),
    # Non-breaking space
    ("\u00a0", " "),
    # Zero-width characters
    ("\u200b", ""),
    ("\u200c", ""),
    ("\u200d", ""),
    ("\ufeff", ""),
]


def _replace_pdf_artifacts(text: str) -> str:
    for bad, good in _PDF_ARTIFACTS:
        text = text.replace(bad, good)
    return text


def _collapse_spaces(line: str) -> str:
    return re.sub(r" {2,}", " ", line)


def _collapse_blank_lines(lines: list[str]) -> list[str]:
    result: list[str] = []
    blank_count = 0
    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 2:
                result.append(line)
        else:
            blank_count = 0
            result.append(line)
    return result
