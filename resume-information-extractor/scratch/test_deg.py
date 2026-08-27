import re
from app.utils.regex_patterns import DEGREE_PATTERN

test_cases = [
    "B.Tech in Computer Science & Engineering (2023 – Present)",
    "Intermediate (2021 – 2023)",
    "10th ICSE (2021)",
    "B. Tech",
    "B.Tech",
]

for tc in test_cases:
    m = DEGREE_PATTERN.search(tc)
    print(f"'{tc}' -> Match: {m.group(0) if m else None}")
