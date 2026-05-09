"""Script detection for autodetect and rendering decisions.

Codepoint-range based, deliberately simple. Sufficient for the four MVP
languages (Latin / Cyrillic / Arabic) plus a few common extras.
"""

from __future__ import annotations

from collections import Counter

# (script, name, ranges) — ranges as inclusive pairs of unicode codepoints.
_SCRIPT_RANGES: list[tuple[str, list[tuple[int, int]]]] = [
    ("latin", [(0x0041, 0x007A), (0x00C0, 0x024F), (0x1E00, 0x1EFF)]),
    ("cyrillic", [(0x0400, 0x04FF), (0x0500, 0x052F), (0x2DE0, 0x2DFF)]),
    ("arabic", [(0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF)]),
    ("devanagari", [(0x0900, 0x097F)]),
    ("cjk", [(0x4E00, 0x9FFF), (0x3040, 0x30FF), (0xAC00, 0xD7AF)]),
]


def script_of_char(ch: str) -> str | None:
    cp = ord(ch)
    for name, ranges in _SCRIPT_RANGES:
        for lo, hi in ranges:
            if lo <= cp <= hi:
                return name
    return None


def detect_dominant_script(text: str) -> str | None:
    counts: Counter[str] = Counter()
    for ch in text:
        s = script_of_char(ch)
        if s is not None:
            counts[s] += 1
    if not counts:
        return None
    return counts.most_common(1)[0][0]
