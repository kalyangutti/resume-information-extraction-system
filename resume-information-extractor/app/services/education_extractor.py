"""
Education extraction service — layout-independent, multi-strategy.

Handles the following resume layouts without any LLM:
  1. Standard paragraphs (degree-first or institution-first)
  2. Inline formats: "B.Tech from XYZ", "B.Tech | XYZ", "B.Tech, XYZ School"
  3. Bullet/list lines: "• B.Tech in CSE — ABC Univ"
  4. Lines with CGPA/Percentage suffix: "B.Tech | CGPA: 9.2"
  5. DOCX tables: cells mapped per row
  6. PDF multi-column / table layouts via spatial block grouping
  7. Mixed / unstructured formats with proximity-based pairing

Strict rules (never guess):
  - degree + institution found  -> return both
  - only institution found      -> degree = null
  - only degree found           -> institution = null
  - neither found in entry      -> skip entry
  - duplicates are removed

No LLM or external AI services are used anywhere.
"""

from __future__ import annotations

import re
from typing import Optional

from app.utils.regex_patterns import (
    DEGREE_PATTERN,
    EDUCATION_SECTION_PATTERN,
    YEAR_RANGE_PATTERN,
)
from app.utils.text_cleaner import get_lines

# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------
EduEntry = dict[str, Optional[str]]   # {"degree": ..., "institution": ...}

# ---------------------------------------------------------------------------
# Institution detection — broad keyword set
# ---------------------------------------------------------------------------
_INSTITUTION_KEYWORDS = re.compile(
    r"""
    \b(?:
        University|Univers[iy]ty|Institute(?:s)?|Institution|
        College|Junior\s+College|Jr\.?\s*College|
        School|Academy|Polytechnic|

        # Exam boards
        CBSE|ICSE|ISC|BISE|State\s+Board|Matric\s+Board|
        JNTU|ANNA\s+University|

        # Famous Indian institution abbreviations
        IIT|NIT|BITS|VIT|SRM|MIT|IIIT|IISc|ISB|IIM|XLRI|IISER|

        # International
        Stanford|Harvard|Oxford|Cambridge|

        # Phrase suffixes
        R&D\s+Institute|Science\s+and\s+Technology|
        Engineering\s+College|Medical\s+College|
        Arts\s+(?:and|&)\s+Science
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Lines that are PURELY metadata — only applied to institution detection, never degree
_NOISE_PATTERN = re.compile(
    r"""
    (?:
        ^(?:CGPA|GPA|Percentage|Grade|Score|Marks|Coursework|
            Relevant\s+Courses?|Activities|Clubs|Honors?|Honours?|
            Distinction|Aggregate|Secured|Result|Passed|Appeared|Stream)\s*[:\-]
        |
        ^\d{1,3}(?:\.\d+)?\s*%\s*$
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Lines that are purely year / date ranges
_YEAR_NOISE_RE = re.compile(
    r"""
    ^(?:
        \d{4}\s*[-\u2013\u2014to]+\s*(?:\d{4}|Present|Current|Ongoing)
        |
        (?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|
           Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|
           Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}
    )$
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Other section headings — signals end of education section
_OTHER_SECTION_PATTERN = re.compile(
    r"""
    ^(?:
        (?:Work\s+)?Experience|Employment(?:\s+History)?|
        Professional\s+(?:Experience|Background)|
        Internship(?:s)?|
        (?:Technical\s+)?Skills?|Core\s+Competencies|
        Projects?|Certifications?|Certificates?|
        Awards?|Publications?|Achievements?|
        References?|Hobbies?|Interests?|Languages?|
        Objective|(?:Professional\s+)?Summary|
        Profile|Contact(?:\s+Information)?|
        Personal(?:\s+Details?)?|
        Extracurricular|Workshops?|Trainings?|
        Professional\s+Summary|Career\s+(?:Objective|Summary)
    )\s*:?\s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Bullet / list prefixes to strip
_BULLET_PREFIX = re.compile(r"^[\s]*[•\*\-–—○◦►▸▶‣⁃]\s*")

# Table header keywords to ignore
_TABLE_HEADER_RE = re.compile(
    r"\b(?:Degree|Specialization|Institute|Institution|University|Board|Year|CPI|CGPA|Grade|Marks|Percentage|Passing\s+Year|Year\s+of\s+Passing)\b",
    re.IGNORECASE,
)

def _is_table_header(line: str) -> bool:
    """Return True if line looks like a table header (e.g. 'Degree Specialization Institute Year CPI')."""
    line_clean = re.sub(r"[|,:;\-]", " ", line.strip())
    words = [w.lower() for w in line_clean.split() if w]
    if len(words) <= 6:
        header_words = {
            "degree", "specialization", "institute", "institution", "university",
            "college", "school", "year", "cpi", "cgpa", "grade", "marks",
            "percentage", "board", "passing"
        }
        matches = [w for w in words if w in header_words]
        if len(matches) >= 2:
            return True
        if len(words) <= 3 and any(w in {"degree", "specialization", "institute", "institution"} for w in words):
            return True
    return False

# "Degree from Institution" keyword
_FROM_RE = re.compile(r"\bfrom\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_education(
    text: str,
    pdf_blocks: Optional[list[dict]] = None,
    docx_tables: Optional[list[list[list[str]]]] = None,
) -> list[EduEntry]:
    """
    Extract education entries using multiple complementary strategies.

    Args:
        text:        Cleaned resume text (always provided).
        pdf_blocks:  Positional text blocks from PyMuPDF (optional, PDF only).
        docx_tables: Structured table data from python-docx (optional, DOCX only).

    Returns:
        List of dicts with keys 'degree' and 'institution' (both Optional[str]).
        Entries where neither field is found are excluded.
        Duplicates are removed.
    """
    results: list[EduEntry] = []

    # Strategy A: DOCX tables
    if docx_tables:
        for entry in _extract_from_docx_tables(docx_tables):
            if not _is_duplicate(entry, results):
                results.append(entry)

    # Strategy B: PDF positional blocks
    if pdf_blocks:
        for entry in _extract_from_pdf_blocks(pdf_blocks):
            if not _is_duplicate(entry, results):
                results.append(entry)

    # Strategy C: Section-based text extraction
    for entry in _extract_from_text(text):
        if not _is_duplicate(entry, results):
            results.append(entry)

    return [e for e in results if e["degree"] is not None or e["institution"] is not None]


# ---------------------------------------------------------------------------
# Strategy A — DOCX table extraction
# ---------------------------------------------------------------------------

def _extract_from_docx_tables(
    tables: list[list[list[str]]],
) -> list[EduEntry]:
    """Extract education from DOCX table structures (one entry per row)."""
    entries: list[EduEntry] = []
    for table in tables:
        for row in table:
            cells = [c.strip() for c in row if c.strip()]
            if not cells:
                continue
            degree: Optional[str] = None
            institution: Optional[str] = None
            for cell in cells:
                cell_clean = _strip_year_and_noise(cell)
                if not cell_clean:
                    continue
                if degree is None and DEGREE_PATTERN.search(cell_clean):
                    degree = _clean_degree(cell_clean)
                elif institution is None and (
                    _INSTITUTION_KEYWORDS.search(cell_clean)
                    or _looks_like_institution(cell_clean)
                ):
                    institution = _clean_institution(cell_clean)
            if degree is not None or institution is not None:
                entries.append({"degree": degree, "institution": institution})
    return entries


# ---------------------------------------------------------------------------
# Strategy B — PDF positional block extraction
# ---------------------------------------------------------------------------

def _extract_from_pdf_blocks(blocks: list[dict]) -> list[EduEntry]:
    """
    Extract education using spatial position of PDF text blocks.

    1. Find education section heading block.
    2. Collect blocks within the section boundary.
    3. Group blocks into horizontal rows (same y-band).
    4. Cluster rows into per-entry groups using vertical gap.
    5. Extract one education entry per cluster.
    """
    if not blocks:
        return []

    sorted_blocks = sorted(blocks, key=lambda b: (b.get("page", 0), b.get("y0", 0)))

    edu_start: Optional[int] = None
    edu_end = len(sorted_blocks)

    for i, block in enumerate(sorted_blocks):
        text = block.get("text", "").strip()
        if edu_start is None:
            if EDUCATION_SECTION_PATTERN.match(text):
                edu_start = i + 1
        else:
            if _OTHER_SECTION_PATTERN.match(text) and i > edu_start:
                edu_end = i
                break

    if edu_start is None:
        return []

    edu_blocks = sorted_blocks[edu_start:edu_end]
    if not edu_blocks:
        return []

    ROW_THRESHOLD = 8    # px — blocks within this y-distance are in same row
    ENTRY_GAP = 20       # px — vertical gap signalling a new entry

    # Group blocks into rows
    rows: list[list[dict]] = []
    current_row: list[dict] = []
    prev_y: Optional[float] = None

    for block in edu_blocks:
        y = block.get("y0", 0)
        if prev_y is None or abs(y - prev_y) <= ROW_THRESHOLD:
            current_row.append(block)
        else:
            if current_row:
                rows.append(sorted(current_row, key=lambda b: b.get("x0", 0)))
            current_row = [block]
        prev_y = y
    if current_row:
        rows.append(sorted(current_row, key=lambda b: b.get("x0", 0)))

    # Group rows into per-entry clusters
    clusters: list[list[list[dict]]] = []
    current_cluster: list[list[dict]] = []
    prev_row_y: Optional[float] = None

    for row in rows:
        row_y = row[0].get("y0", 0) if row else 0
        if prev_row_y is None or (row_y - prev_row_y) <= ENTRY_GAP + ROW_THRESHOLD:
            current_cluster.append(row)
        else:
            if current_cluster:
                clusters.append(current_cluster)
            current_cluster = [row]
        prev_row_y = row_y
    if current_cluster:
        clusters.append(current_cluster)

    # Extract education entries per cluster using block parsing
    entries: list[EduEntry] = []
    for cluster in clusters:
        block_texts = [
            block.get("text", "").strip()
            for row in cluster
            for block in row
            if block.get("text", "").strip()
        ]
        cluster_entries = _parse_blocks(block_texts)
        for entry in cluster_entries:
            if entry["degree"] is not None or entry["institution"] is not None:
                entries.append(entry)

    return entries


# ---------------------------------------------------------------------------
# Strategy C — Section-based text extraction
# ---------------------------------------------------------------------------

def _extract_from_text(text: str) -> list[EduEntry]:
    """
    Multi-pass text-based education extractor.
    Pass 1: section detection + block grouping.
    Pass 2: full-document candidate scan (fallback).
    """
    lines = get_lines(text)
    section_lines = _find_section_lines(lines)

    if section_lines:
        return _parse_blocks(section_lines)

    return _candidate_scan(lines)


def _find_section_lines(lines: list[str], max_lines: int = 50) -> list[str]:
    """Return lines belonging to the education section, or [] if not found."""
    in_section = False
    collected: list[str] = []

    for line in lines:
        stripped = line.strip()
        if EDUCATION_SECTION_PATTERN.match(stripped):
            in_section = True
            continue
        if in_section:
            if _OTHER_SECTION_PATTERN.match(stripped) and collected:
                break
            if len(collected) >= max_lines:
                break
            collected.append(stripped)

    return collected


def _parse_blocks(lines: list[str]) -> list[EduEntry]:
    """
    Split section lines into per-entry blocks and extract structured data.

    Block boundaries (any of the following triggers a flush + new block):
      1. Blank line between entries.
      2. A second degree keyword appears when the current block already has one.
      3. A new institution-keyword line appears after the current block already
         has a degree (institution-first layout, no blank line between entries).
      4. A new institution-keyword line appears after the current block already
         has an institution (two consecutive institution-first entries).

    Rule 3 & 4 handle resumes like:
        Vel Tech R&D Institute   2023-Present    <- institution
        B.Tech in CSE | CGPA: 9.2               <- degree  (block 1 done)
        Narayana Junior College  2021-2023       <- NEW institution, no blank!
        Intermediate | Pct: 96%                  <- degree
    """
    entries: list[EduEntry] = []
    current_block: list[str] = []

    def flush(block: list[str]) -> None:
        entry = _extract_entry_from_lines(block)
        if entry["degree"] is not None or entry["institution"] is not None:
            entries.append(entry)

    def block_has_degree() -> bool:
        return any(DEGREE_PATTERN.search(l) for l in current_block)

    def block_has_institution() -> bool:
        return any(_INSTITUTION_KEYWORDS.search(l) for l in current_block)

    def line_is_institution(s: str) -> bool:
        """True when the line carries an institution keyword but no degree."""
        return bool(_INSTITUTION_KEYWORDS.search(s)) and not DEGREE_PATTERN.search(s)

    for line in lines:
        stripped = _strip_bullet(line.strip())

        # Skip blank lines and table header lines
        if not stripped or _is_table_header(stripped):
            if current_block:
                flush(current_block)
                current_block = []
            continue

        # Pure year line -> keep in current block for context only
        if _YEAR_NOISE_RE.match(stripped):
            current_block.append(stripped)
            continue

        if current_block:
            # Boundary trigger 2: second degree in same block
            if DEGREE_PATTERN.search(stripped) and block_has_degree():
                flush(current_block)
                current_block = [stripped]
                continue

            # Boundary trigger 3: new institution appears when block is already
            # complete (has BOTH degree AND institution). This handles layouts
            # where entries share no blank line:
            #   Vel Tech...          <- institution
            #   B.Tech | CGPA: 9.2  <- degree  => block 1 complete
            #   Narayana JC...       <- NEW institution (no blank line!)
            if line_is_institution(stripped) and block_has_degree() and block_has_institution():
                flush(current_block)
                current_block = [stripped]
                continue

            # Boundary trigger 4: second institution when no degree found yet
            # means two institution-only entries back-to-back (rare but valid)
            if line_is_institution(stripped) and block_has_institution() and not block_has_degree():
                flush(current_block)
                current_block = [stripped]
                continue

        current_block.append(stripped)

    if current_block:
        flush(current_block)

    return entries


def _candidate_scan(lines: list[str]) -> list[EduEntry]:
    """
    Full-document fallback: collect all degree + institution candidates
    and pair by proximity (nearest unused institution within 6 lines).
    """
    degree_candidates: list[tuple[int, str]] = []
    institution_candidates: list[tuple[int, str]] = []

    for i, raw_line in enumerate(lines):
        line = _strip_bullet(raw_line.strip())
        if not line or _YEAR_NOISE_RE.match(line):
            continue
        cleaned = _strip_year_and_noise(line)
        if not cleaned:
            continue
        if DEGREE_PATTERN.search(cleaned):
            degree_candidates.append((i, _clean_degree(cleaned)))
        elif _INSTITUTION_KEYWORDS.search(cleaned):
            institution_candidates.append((i, _clean_institution(cleaned)))

    used_institutions: set[int] = set()
    entries: list[EduEntry] = []

    for deg_idx, deg_text in degree_candidates:
        best: Optional[tuple[int, str]] = None
        best_dist = 7

        for inst_idx, inst_text in institution_candidates:
            if inst_idx in used_institutions:
                continue
            dist = abs(deg_idx - inst_idx)
            if dist < best_dist:
                best_dist = dist
                best = (inst_idx, inst_text)

        if best:
            used_institutions.add(best[0])
            entries.append({"degree": deg_text, "institution": best[1]})
        else:
            entries.append({"degree": deg_text, "institution": None})

    for inst_idx, inst_text in institution_candidates:
        if inst_idx not in used_institutions:
            entries.append({"degree": None, "institution": inst_text})

    return entries


# ---------------------------------------------------------------------------
# Per-block entry extraction (shared by all strategies)
# ---------------------------------------------------------------------------

def _extract_entry_from_lines(lines: list[str]) -> EduEntry:
    """
    Extract a single education entry from a list of lines / text fragments.

    Priority order:
      1. "Degree from Institution" pattern
      2. Inline split on pipe (|) or comma (,)
      3. Degree detection — runs BEFORE noise filter so "B.Tech | CGPA: 9.2"
         is not discarded before the degree keyword is matched
      4. Institution detection — WITH noise filter
      5. Fallback: any non-degree, non-year, non-noise proper-noun line
    """
    degree: Optional[str] = None
    institution: Optional[str] = None

    for raw in lines:
        line = _strip_bullet(raw.strip())
        # Collapse multi-space (common in PDF text blocks)
        line = re.sub(r" {2,}", " ", line)
        if not line or _YEAR_NOISE_RE.match(line):
            continue

        # 1. "Degree from Institution"
        if degree is None or institution is None:
            result = _try_from_pattern(line)
            if result:
                d, inst = result
                if degree is None and d:
                    degree = d
                if institution is None and inst:
                    institution = inst
                if degree and institution:
                    break
                continue

        # 2. Inline split on | or ,
        if degree is None or institution is None:
            result = _try_inline_split(line)
            if result:
                d, inst = result
                if degree is None and d:
                    degree = d
                if institution is None and inst:
                    institution = inst
                continue

        # 3. Degree detection (before noise filter)
        if degree is None and DEGREE_PATTERN.search(line):
            degree = _clean_degree(line)
            continue

        # 4. Institution detection (with noise filter)
        if institution is None:
            if _NOISE_PATTERN.search(line):
                continue
            if _INSTITUTION_KEYWORDS.search(line):
                institution = _clean_institution(line)
                continue

    # 5. Fallback institution — any proper-noun line near the degree
    if institution is None and degree is not None:
        for raw in lines:
            line = _strip_bullet(re.sub(r" {2,}", " ", raw.strip()))
            if not line:
                continue
            if DEGREE_PATTERN.search(line):
                continue
            if _YEAR_NOISE_RE.match(line):
                continue
            if _NOISE_PATTERN.search(line):
                continue
            candidate = _clean_institution(line)
            words = candidate.split()
            alpha_ok = (
                sum(1 for w in words if re.match(r"^[A-Za-z&().''\-]+$", w))
                / max(len(words), 1)
            ) >= 0.65
            if len(words) >= 2 and alpha_ok:
                institution = candidate
                break

    return {"degree": degree, "institution": institution}


# ---------------------------------------------------------------------------
# Inline pattern helpers
# ---------------------------------------------------------------------------

def _try_from_pattern(line: str) -> Optional[tuple[str, Optional[str]]]:
    """
    Detect "Degree from Institution" pattern.
    Example: "B.Tech in CSE from ABC University"
    """
    if not _FROM_RE.search(line) or not DEGREE_PATTERN.search(line):
        return None

    parts = _FROM_RE.split(line, maxsplit=1)
    if len(parts) != 2:
        return None

    left, right = parts[0].strip(), parts[1].strip()

    if DEGREE_PATTERN.search(left):
        deg = _clean_degree(left)
        inst = _clean_institution(right) if right else None
        if deg:
            return deg, inst

    return None


def _try_inline_split(line: str) -> Optional[tuple[Optional[str], Optional[str]]]:
    """
    Detect lines where degree and institution are separated by | or ,.

    Examples:
      "B.Tech in CSE | ABC University"        -> ("B.Tech in CSE", "ABC University")
      "B.Tech in CSE | CGPA: 9.2/10"         -> ("B.Tech in CSE", None)
      "Intermediate (Class XII) | Pct: 96%"   -> ("Intermediate (Class XII)", None)
      "10th SSC, St. Ann School"              -> ("10th SSC", "St. Ann School")
    """
    if not DEGREE_PATTERN.search(line):
        return None

    # Try pipe first (higher confidence separator), then comma
    for sep in ("|", ","):
        if sep not in line:
            continue

        parts = line.split(sep, 1)
        left, right = parts[0].strip(), parts[1].strip()

        if not DEGREE_PATTERN.search(left):
            continue

        deg = _clean_degree(left)
        if not deg:
            continue

        # Right side is metadata (CGPA, Percentage…) — not an institution
        if _NOISE_PATTERN.search(right) or re.match(
            r"^(?:CGPA|GPA|Percentage|Score|Marks|Grade)\s*[:\-]",
            right,
            re.IGNORECASE,
        ):
            return deg, None

        if right and (
            _INSTITUTION_KEYWORDS.search(right) or _looks_like_institution(right)
        ):
            return deg, _clean_institution(right)

    return None


# ---------------------------------------------------------------------------
# Text cleaning helpers
# ---------------------------------------------------------------------------

def _strip_bullet(line: str) -> str:
    """Remove leading bullet / list characters."""
    return _BULLET_PREFIX.sub("", line).strip()


def _strip_year_and_noise(line: str) -> str:
    """Remove year ranges and trailing CGPA/Percentage suffixes."""
    cleaned = YEAR_RANGE_PATTERN.sub("", line)
    cleaned = re.sub(
        r"\s*[|,;]?\s*(?:CGPA|GPA|Percentage|Score|Grade|Marks)\s*[:\-]?\s*[\d./%]+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip(" -\u2013\u2014|,")


def _clean_degree(line: str) -> str:
    """
    Extract a clean degree string.
    """
    if "\n" in line:
        line = line.split("\n")[0]
    cleaned = YEAR_RANGE_PATTERN.sub("", line)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\s*\|\s*.*$", "", cleaned)
    cleaned = re.sub(
        r"\s*[,;]?\s*(?:CGPA|GPA|Percentage|Score|Grade|Marks)\s*[:\-]?\s*[\d./%]+\s*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    res = cleaned.strip(" -\u2013\u2014|,")
    return "" if res.lower() in {"degree", "specialization", "qualification"} else res


_SUBJECT_KEYWORDS = re.compile(
    r"\b(?:Physics|Chemistry|Mathematics|Maths|Biology|Science|Arts|Commerce|Humanities|MPC|BiPC|CEC|HEC|PCMB|Computer\s+Science)\b",
    re.IGNORECASE,
)

def _clean_institution(line: str) -> str:
    """Extract a clean institution name — collapse internal spaces, strip noise."""
    if "\n" in line:
        line = line.split("\n")[0]
    cleaned = YEAR_RANGE_PATTERN.sub("", line)
    cleaned = re.sub(r"\s*\|\s*.*$", "", cleaned)
    cleaned = re.sub(r"\s*\b(?:19|20)\d{2}\b\s*$", "", cleaned)
    cleaned = re.sub(
        r"\s*[,;]?\s*(?:CGPA|GPA|Percentage|Score|Grade|Marks)\s*[:\-]?\s*[\d./%]+\s*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r" {2,}", " ", cleaned)
    res = cleaned.strip(" -\u2013\u2014|,")
    if _SUBJECT_KEYWORDS.search(res) and not _INSTITUTION_KEYWORDS.search(res):
        return ""
    return "" if res.lower() in {"institute", "institution", "university", "college", "school"} else res


def _looks_like_institution(text: str) -> bool:
    """Heuristic: does this text look like a proper-noun institution name?"""
    if DEGREE_PATTERN.search(text) or _SUBJECT_KEYWORDS.search(text):
        return False
    words = text.split()
    if len(words) < 2:
        return False
    return any(w and w[0].isupper() for w in words)


# ---------------------------------------------------------------------------
# Deduplication helper
# ---------------------------------------------------------------------------

def _normalise(s: Optional[str]) -> str:
    """Normalise a string for dedup comparison."""
    if s is None:
        return ""
    # Normalise quotes and dashes
    s = s.replace("’", "'").replace("‘", "'").replace("`", "'")
    s = re.sub(r"[–—\-]", "-", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def _is_duplicate(entry: EduEntry, existing: list[EduEntry]) -> bool:
    """
    Return True if entry is already fully represented or redundant in existing.
    Upgrades existing partial entries with degree/institution if the new entry provides them.
    """
    nd = _normalise(entry.get("degree"))
    ni = _normalise(entry.get("institution"))

    for e in existing:
        ed = _normalise(e.get("degree"))
        ei = _normalise(e.get("institution"))

        # Match on institution
        if ni and ei == ni:
            # If the new entry has a degree but the existing one does not, upgrade it
            if nd and not ed:
                e["degree"] = entry["degree"]
                return True
            return True

        # Match on degree
        if nd and ed == nd:
            # If the new entry has an institution but the existing one does not, upgrade it
            if ni and not ei:
                e["institution"] = entry["institution"]
                return True
            return True

    return False
