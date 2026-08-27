"""
Work experience extraction service.

Uses rule-based heuristics and regex patterns to detect experience
sections and extract job title, company, and duration.

No LLM or external AI services are used.
"""

from __future__ import annotations

import re
from typing import Optional

from app.utils.regex_patterns import (
    DATE_RANGE_PATTERN,
    EXPERIENCE_SECTION_PATTERN,
    YEAR_RANGE_PATTERN,
)
from app.utils.text_cleaner import get_lines

# ---------------------------------------------------------------------------
# Known job-title keywords
# ---------------------------------------------------------------------------
_JOB_TITLE_KEYWORDS = re.compile(
    r"\b(?:Engineer|Developer|Analyst|Manager|Intern|Internship|Consultant|"
    r"Architect|Designer|Lead|Senior|Junior|Associate|Executive|Officer|"
    r"Specialist|Scientist|Researcher|Director|Head|VP|CTO|CEO|Founder|"
    r"Co-Founder|Administrator|Coordinator|Programmer|Technician|"
    r"Data Scientist|ML Engineer|DevOps|SRE|Full[- ]?Stack|Front[- ]?End|"
    r"Back[- ]?End|QA|Tester|Support|Product Manager|Project Manager|"
    r"Business Analyst|Scrum Master)\b",
    re.IGNORECASE,
)

# Lines that look like company names (heuristic: no common stop-words, moderate length)
_COMPANY_SUFFIXES = re.compile(
    r"\b(?:Inc\.?|LLC|Ltd\.?|Limited|Corp\.?|Corporation|Pvt\.?|Private|"
    r"Technologies|Tech|Solutions|Systems|Services|Labs|Studio|Consulting|"
    r"Software|Digital|Innovations?|Ventures?|Group|Analytics|AI|Agency)\b",
    re.IGNORECASE,
)

# Lines to skip inside experience sections
_SKIP_LINE_PATTERN = re.compile(
    r"^[-•*·▪]\s*",  # bullet-point descriptions
)

# ---------------------------------------------------------------------------
# Other section headings (signals end of experience section)
# ---------------------------------------------------------------------------
_OTHER_SECTION_PATTERN = re.compile(
    r"^(?:Education|Educational Background|Academic|Skills|Certifications?|"
    r"Awards?|Publications?|Projects?|Achievements?|References?|Hobbies?|"
    r"Languages?|Objective|Summary|Profile|Contact|Personal)\s*:?\s*$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_experience(text: str) -> list[dict[str, Optional[str]]]:
    """
    Extract work/internship experience entries from resume text.

    Strategy:
    1. Detect the experience section by heading keywords.
    2. Collect lines within that section.
    3. Group lines into blocks (separated by blank lines or duration markers).
    4. For each block, extract job_title, company, and duration.

    Args:
        text: Cleaned resume text.

    Returns:
        List of dicts with keys 'job_title', 'company', 'duration'.
    """
    lines = get_lines(text)
    section_lines = _extract_experience_section(lines)

    if not section_lines:
        return []

    return _parse_experience_lines(section_lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_experience_section(
    lines: list[str],
    max_lines: int = 50,
) -> list[str]:
    """Find the experience section and return its lines."""
    in_section = False
    collected: list[str] = []

    for line in lines:
        stripped = line.strip()

        if EXPERIENCE_SECTION_PATTERN.match(stripped):
            in_section = True
            continue

        if in_section:
            if _OTHER_SECTION_PATTERN.match(stripped) and collected:
                break
            if len(collected) >= max_lines:
                break
            collected.append(stripped)

    return collected


def _parse_experience_lines(
    lines: list[str],
) -> list[dict[str, Optional[str]]]:
    """
    Group experience lines into blocks and extract structured data.

    A new block starts when a duration / job-title keyword is encountered
    or when a blank line separates entries.
    """
    entries: list[dict[str, Optional[str]]] = []
    current_block: list[str] = []

    def flush_block(block: list[str]) -> None:
        entry = _extract_entry_from_block(block)
        if entry["job_title"] or entry["company"] or entry["duration"]:
            entries.append(entry)

    for line in lines:
        stripped = line.strip()

        # Blank line = block boundary
        if not stripped:
            if current_block:
                flush_block(current_block)
                current_block = []
            continue

        # Skip bullet-point description lines
        if _SKIP_LINE_PATTERN.match(stripped):
            continue

        current_block.append(stripped)

    if current_block:
        flush_block(current_block)

    return entries


def _extract_entry_from_block(block: list[str]) -> dict[str, Optional[str]]:
    """Extract job_title, company, duration from a block of lines."""
    job_title: Optional[str] = None
    company: Optional[str] = None
    duration: Optional[str] = None

    for line in block:
        # Duration: check for date range first
        if duration is None:
            dur = _extract_duration(line)
            if dur:
                duration = dur
                continue

        # Job title: line contains job-title keywords
        if job_title is None and _JOB_TITLE_KEYWORDS.search(line):
            # Strip the duration part if present in the same line
            title_line = DATE_RANGE_PATTERN.sub("", line)
            title_line = YEAR_RANGE_PATTERN.sub("", title_line).strip(" -|,–")
            if title_line:
                job_title = title_line

        # Company: line contains company suffix keywords
        if company is None and _COMPANY_SUFFIXES.search(line):
            comp_line = DATE_RANGE_PATTERN.sub("", line)
            comp_line = YEAR_RANGE_PATTERN.sub("", comp_line).strip(" -|,–")
            if comp_line and comp_line != job_title:
                company = comp_line

    # Fallback: if company not found, use first non-title, non-duration line
    if company is None and len(block) >= 2:
        for line in block:
            dur = _extract_duration(line)
            if dur:
                continue
            if _JOB_TITLE_KEYWORDS.search(line):
                continue
            cleaned = DATE_RANGE_PATTERN.sub("", line)
            cleaned = YEAR_RANGE_PATTERN.sub("", cleaned).strip(" -|,–")
            if cleaned and len(cleaned) > 2:
                company = cleaned
                break

    # Fallback: if job_title not found, use first block line
    if job_title is None and block:
        first_line = DATE_RANGE_PATTERN.sub("", block[0])
        first_line = YEAR_RANGE_PATTERN.sub("", first_line).strip(" -|,–")
        if first_line:
            job_title = first_line

    return {"job_title": job_title, "company": company, "duration": duration}


def _extract_duration(line: str) -> Optional[str]:
    """Extract a duration string from a line, if present."""
    # Try full month-name date range first
    match = DATE_RANGE_PATTERN.search(line)
    if match:
        return match.group(0).strip()

    # Try year-only range
    match = YEAR_RANGE_PATTERN.search(line)
    if match:
        return match.group(0).strip()

    return None
