"""
Experience duration calculator.

Computes total years of work experience from a list of experience entries,
handling overlapping date ranges without double-counting.

Supported duration formats:
  - "Jan 2022 - Present"
  - "January 2022 - May 2023"
  - "2022 - 2024"
  - "2022-2024"
  - "March 2021 - Current"
  - "May 2025 - July 2025"
  - "2019 - Ongoing"

Rules:
  - Present / Current / Ongoing / Till Date → today's date.
  - Year-only start → January 1 of that year.
  - Year-only end   → December 31 of that year.
  - Overlapping jobs are merged before summing (no double-counting).
  - No experience → returns 0.
  - Result is rounded to 1 decimal place.

No LLM or external AI services are used.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MONTH_MAP: dict[str, int] = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_PRESENT_KEYWORDS: frozenset[str] = frozenset({
    "present", "current", "ongoing", "till date", "till now",
    "now", "today", "currently", "date",
})

# Regex to split a duration string into start and end parts.
# Matches separators like " - ", " – ", " — ", " to ".
_SEPARATOR_RE = re.compile(
    r"\s*(?:[-–—]+|(?<!\w)to(?!\w))\s*",
    re.IGNORECASE,
)

# Matches "Month Year" e.g. "Jan 2022", "January 2022"
_MONTH_YEAR_RE = re.compile(
    r"^([A-Za-z]+)\s+(\d{4})$",
)

# Matches bare year e.g. "2022"
_YEAR_ONLY_RE = re.compile(r"^(\d{4})$")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_total_experience(experience_list: list) -> float:
    """
    Compute total years of work experience from a list of experience dicts.

    Overlapping intervals are merged so that concurrent jobs are not
    double-counted. The result is rounded to 1 decimal place.

    Args:
        experience_list: List of dicts (or Pydantic objects) each having
                         an optional ``duration`` field.

    Returns:
        Total years of experience as a float rounded to 1 d.p.,
        or 0.0 if no parseable durations are found.
    """
    if not experience_list:
        return 0.0

    intervals: list[tuple[date, date]] = []

    for exp in experience_list:
        # Support both plain dicts and Pydantic model instances
        if isinstance(exp, dict):
            duration = exp.get("duration")
        else:
            duration = getattr(exp, "duration", None)

        if not duration:
            continue

        interval = _parse_duration(duration)
        if interval is not None:
            intervals.append(interval)

    if not intervals:
        return 0.0

    merged = _merge_intervals(intervals)
    total_days = sum((end - start).days for start, end in merged)
    total_years = total_days / 365.25

    return round(max(0.0, total_years), 1)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_duration(duration: str) -> Optional[tuple[date, date]]:
    """
    Parse a single duration string into a (start_date, end_date) tuple.

    Returns None if the string cannot be reliably parsed.
    """
    duration = duration.strip()

    # Split on separator ( " - ", " – ", " to ", etc.)
    parts = _SEPARATOR_RE.split(duration, maxsplit=1)

    if len(parts) == 2:
        start_str, end_str = parts[0].strip(), parts[1].strip()
        # If start_str is just a month (e.g. "May" in "May-Jul 2022") and end_str has a year, inherit year
        if start_str.lower() in _MONTH_MAP:
            end_match = _MONTH_YEAR_RE.match(end_str)
            if end_match:
                start_str = f"{start_str} {end_match.group(2)}"
    elif len(parts) == 1:
        # Single token — could be just a year; treat as a single-year period
        start_str = parts[0].strip()
        end_str = parts[0].strip()
    else:
        return None

    start = _parse_start_date(start_str)
    end   = _parse_end_date(end_str)

    if start is None or end is None:
        return None

    # Sanity check: start must not be after end
    if start > end:
        return None

    return (start, end)


def _parse_start_date(s: str) -> Optional[date]:
    """
    Parse a start-date token.

    - "Jan 2022" → date(2022, 1, 1)
    - "2022"     → date(2022, 1, 1)   (beginning of year)
    - Present keywords → today
    """
    s = s.strip().lower()

    if s in _PRESENT_KEYWORDS:
        return date.today()

    m = _MONTH_YEAR_RE.match(s)
    if m:
        month = _MONTH_MAP.get(m.group(1).lower())
        year  = int(m.group(2))
        if month and 1900 <= year <= date.today().year + 5:
            return date(year, month, 1)

    m = _YEAR_ONLY_RE.match(s)
    if m:
        year = int(m.group(1))
        if 1900 <= year <= date.today().year + 5:
            return date(year, 1, 1)

    return None


def _parse_end_date(s: str) -> Optional[date]:
    """
    Parse an end-date token.

    - "Jul 2023"  → date(2023, 7, 1)
    - "2024"      → date(2024, 12, 31)  (end of year)
    - Present keywords → today
    """
    s = s.strip().lower()

    if s in _PRESENT_KEYWORDS:
        return date.today()

    m = _MONTH_YEAR_RE.match(s)
    if m:
        month = _MONTH_MAP.get(m.group(1).lower())
        year  = int(m.group(2))
        if month and 1900 <= year <= date.today().year + 5:
            return date(year, month, 1)

    m = _YEAR_ONLY_RE.match(s)
    if m:
        year = int(m.group(1))
        if 1900 <= year <= date.today().year + 5:
            return date(year, 12, 31)  # treat year-end as December 31

    return None


def _merge_intervals(
    intervals: list[tuple[date, date]],
) -> list[tuple[date, date]]:
    """
    Merge overlapping or adjacent date intervals.

    Example:
        [(2020-01-01, 2022-06-01), (2021-01-01, 2023-01-01)]
        → [(2020-01-01, 2023-01-01)]

    Args:
        intervals: List of (start, end) date tuples (non-empty).

    Returns:
        Sorted, non-overlapping list of merged intervals.
    """
    sorted_ivs = sorted(intervals, key=lambda iv: iv[0])
    merged: list[tuple[date, date]] = [sorted_ivs[0]]

    for start, end in sorted_ivs[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:                        # overlapping or adjacent
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))

    return merged
