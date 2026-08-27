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
    r"Co-Founder|Administrator|Coordinator|Programmer|Technician|Freelancer|"
    r"Data Scientist|ML Engineer|DevOps|SRE|Full[- ]?Stack|Front[- ]?End|"
    r"Back[- ]?End|QA|Tester|Support|Product Manager|Project Manager|"
    r"Business Analyst|Scrum Master)\b",
    re.IGNORECASE,
)

# Known company suffix keywords
_COMPANY_SUFFIXES = re.compile(
    r"\b(?:Inc\.?|LLC|Ltd\.?|Limited|Corp\.?|Corporation|Pvt\.?|Private|"
    r"Technologies|Tech|Solutions|Systems|Services|Labs|Studio|Consulting|"
    r"Software|Digital|Innovations?|Ventures?|Group|Analytics|AI|Agency)\b",
    re.IGNORECASE,
)

# Common action verbs that start bullet description lines (to skip)
_DESCRIPTION_VERB_PATTERN = re.compile(
    r"^(?:Coordinated|Developed|Integrated|Built|Designed|Implemented|Managed|"
    r"Created|Solved|Cleared|Achieved|Led|Organized|Secured|Optimized|Spearheaded|"
    r"Maintained|Automated|Engineered|Formulated|Established|Assisted|Handled|"
    r"Provided|Worked|Utilized|Reduced|Increased|Improved|Delivered|Successfully|"
    r"Programmed|Captured|Captained|Documented|Solved)\b",
    re.IGNORECASE,
)

# Bullet / list prefixes to strip
_BULLET_PREFIX = re.compile(r"^[\s]*[•\*\-–—○◦o►▸▶‣⁃]\s*")

# Bracketed company pattern: [Company Name]
_BRACKETED_COMPANY_PATTERN = re.compile(r"\[([^\]]+)\]")

# Other section headings (signals end of experience section)
_OTHER_SECTION_PATTERN = re.compile(
    r"^(?:Education|Educational Background|Academic|Skills|Certifications?|"
    r"Awards?|Publications?|Projects?|Achievements?|References?|Hobbies?|"
    r"Languages?|Objective|Summary|Profile|Contact|Personal|Extra-Curricular|"
    r"Positions\s+of\s+Responsibility)\s*:?\s*$",
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
    """
    entries: list[dict[str, Optional[str]]] = []
    current_block: list[str] = []

    def flush_block(block: list[str]) -> None:
        entry = _extract_entry_from_block(block)
        if entry["job_title"] or entry["company"] or entry["duration"]:
            entries.append(entry)

    for line in lines:
        raw_stripped = line.strip()
        stripped = _BULLET_PREFIX.sub("", raw_stripped).strip()

        if not stripped:
            if current_block:
                flush_block(current_block)
                current_block = []
            continue

        # Skip description lines starting with a lowercase letter (wrapped sentences)
        if stripped[0].islower():
            continue

        # Skip bullet description lines (action verbs or long sentences)
        if _DESCRIPTION_VERB_PATTERN.match(stripped):
            continue

        words = stripped.split()
        if len(words) > 15 and not _JOB_TITLE_KEYWORDS.search(stripped) and not _extract_duration(stripped):
            continue

        # If new line has a job title or duration and current block already has one, flush
        if current_block:
            block_text = " ".join(current_block)
            has_title = bool(_JOB_TITLE_KEYWORDS.search(stripped))
            has_dur = bool(_extract_duration(stripped))
            block_has_title = bool(_JOB_TITLE_KEYWORDS.search(block_text))
            block_has_dur = bool(_extract_duration(block_text))
            
            # Only split if we see a second title or a second duration
            if (has_title and block_has_title) or (has_dur and block_has_dur):
                flush_block(current_block)
                current_block = []

        current_block.append(stripped)

    if current_block:
        flush_block(current_block)

    return entries


def _extract_entry_from_block(block: list[str]) -> dict[str, Optional[str]]:
    """Extract job_title, company, duration from a block of lines."""
    job_title: Optional[str] = None
    company: Optional[str] = None
    duration: Optional[str] = None

    # 1. Duration extraction
    for line in block:
        if duration is None:
            dur = _extract_duration(line)
            if dur:
                duration = dur

    # 2. Check for bracketed company: [Company Name] in the header line
    first_line = block[0] if block else ""
    bracket_match = _BRACKETED_COMPANY_PATTERN.search(first_line)
    if bracket_match:
        company = bracket_match.group(1).strip()
        # Remove [Company] and duration from first line to get job title
        clean_title = _BRACKETED_COMPANY_PATTERN.sub("", first_line)
        if duration:
            clean_title = clean_title.replace(duration, "")
        clean_title = DATE_RANGE_PATTERN.sub("", clean_title)
        clean_title = YEAR_RANGE_PATTERN.sub("", clean_title)
        clean_title = re.sub(r"[\s\-\|,\u2013\u2014]+", " ", clean_title).strip()
        if clean_title:
            job_title = clean_title

    # 3. Standard line-by-line extraction if title/company not found via brackets
    if job_title is None or company is None:
        for line in block:
            line_clean = DATE_RANGE_PATTERN.sub("", line)
            line_clean = YEAR_RANGE_PATTERN.sub("", line_clean).strip(" -|,–")

            if job_title is None and _JOB_TITLE_KEYWORDS.search(line):
                if line_clean:
                    job_title = line_clean
                    continue

            if company is None and _COMPANY_SUFFIXES.search(line):
                if line_clean and line_clean != job_title:
                    company = line_clean
                    continue

    # Fallback company: second line in block
    if company is None and len(block) >= 2:
        for line in block:
            if _extract_duration(line):
                continue
            if job_title and line in job_title:
                continue
            cleaned = DATE_RANGE_PATTERN.sub("", line)
            cleaned = YEAR_RANGE_PATTERN.sub("", cleaned).strip(" -|,–")
            if cleaned and len(cleaned) > 2:
                company = cleaned
                break

    # Fallback job_title: first line in block
    if job_title is None and block:
        first_line = DATE_RANGE_PATTERN.sub("", block[0])
        first_line = YEAR_RANGE_PATTERN.sub("", first_line).strip(" -|,–")
        if first_line:
            job_title = first_line

    return {"job_title": job_title, "company": company, "duration": duration}


def _extract_duration(line: str) -> Optional[str]:
    """Extract a duration string from a line, if present."""
    match = DATE_RANGE_PATTERN.search(line)
    if match:
        return match.group(0).strip()

    match = YEAR_RANGE_PATTERN.search(line)
    if match:
        return match.group(0).strip()

    return None
