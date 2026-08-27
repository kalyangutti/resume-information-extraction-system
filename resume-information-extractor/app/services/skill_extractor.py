"""
Skill extraction service.

Uses a local skills dictionary (app/data/skills.json) for:
- Case-insensitive skill matching
- Skill normalisation (e.g. sklearn → Scikit-learn)
- Duplicate removal
- Multi-word skill phrase matching

No external AI or ML inference is used.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.utils.text_cleaner import normalise_whitespace

# Path to the bundled skills dictionary
_SKILLS_JSON_PATH = Path(__file__).parent.parent / "data" / "skills.json"


# ---------------------------------------------------------------------------
# Skills dictionary loading
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_skills_dict() -> dict[str, str]:
    """
    Load and flatten the skills dictionary from JSON.

    Returns:
        Flat dict mapping lowercase alias → canonical skill name.
    """
    with open(_SKILLS_JSON_PATH, encoding="utf-8") as fh:
        raw: dict[str, dict[str, str]] = json.load(fh)

    flat: dict[str, str] = {}
    for _category, aliases in raw.items():
        for alias, canonical in aliases.items():
            flat[alias.lower().strip()] = canonical
    return flat


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_skills(text: str) -> list[str]:
    """
    Extract and normalise skills from resume text.

    Strategy:
    1. Build the normalised text (lowercase, collapsed whitespace per line).
    2. Sort skill aliases longest-first to prefer multi-word matches.
    3. Scan each line for alias occurrences using whole-word/phrase boundary
       matching to avoid false positives.
    4. Collect canonical names, deduplicate (preserve first-seen order).

    Args:
        text: Cleaned resume text.

    Returns:
        Deduplicated list of canonical skill names in discovery order.
    """
    skills_dict = _load_skills_dict()

    # Sort aliases longest-first so multi-word phrases match before sub-words
    sorted_aliases = sorted(skills_dict.keys(), key=len, reverse=True)

    found: dict[str, str] = {}  # alias → canonical (for dedup by canonical)
    canonical_seen: set[str] = set()

    # Prepare text: work line-by-line to avoid cross-line false positives
    lines = text.split("\n")

    for line in lines:
        normalised_line = normalise_whitespace(line).lower()
        if not normalised_line:
            continue

        for alias in sorted_aliases:
            # Build a regex that matches the alias as a whole word/phrase
            pattern = _build_alias_pattern(alias)
            if pattern is None:
                continue

            if re.search(pattern, normalised_line):
                canonical = skills_dict[alias]
                if canonical not in canonical_seen:
                    canonical_seen.add(canonical)
                    found[alias] = canonical

    return list(found.values())


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

@lru_cache(maxsize=2048)
def _build_alias_pattern(alias: str) -> Optional[re.Pattern]:
    """
    Build a compiled regex pattern for an alias with word boundaries.

    Handles multi-word aliases by using appropriate boundary anchors.
    Returns None if the alias is too short (single char) to avoid noise.
    """
    if len(alias) <= 1:
        return None

    escaped = re.escape(alias)

    # For purely alphabetic single-word aliases: use \b word boundaries
    # For aliases with special chars (C++, C#, .NET): use lookahead/lookbehind
    if re.match(r"^[a-z0-9 ]+$", alias):
        # Simple alphanumeric / space alias — use word boundaries
        # For multi-word: boundary on first and last word
        pattern = rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
    else:
        pattern = rf"(?i){escaped}"

    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error:
        return None
