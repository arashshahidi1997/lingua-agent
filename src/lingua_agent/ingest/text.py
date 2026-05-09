"""Text normalization and segmentation.

Conservative: never modify the source semantically. Whitespace is collapsed
within paragraphs but paragraph breaks (blank lines) are preserved.
"""

from __future__ import annotations

import re

# Sentence-end punctuation across our four target languages. Persian uses
# U+061F (؟) for question marks, U+06D4 (۔) is rare; Russian/Italian use ASCII.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?؟])\s+", flags=re.UNICODE)
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n+")
_WHITESPACE = re.compile(r"[ \t]+")


def normalize_text(text: str) -> str:
    # Strip BOM and trailing whitespace per line; collapse runs of spaces/tabs.
    text = text.replace("﻿", "")
    lines = [_WHITESPACE.sub(" ", line).rstrip() for line in text.splitlines()]
    text = "\n".join(lines).strip()
    return text


def segment_paragraphs(text: str) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []
    return [p.strip() for p in _PARAGRAPH_SPLIT.split(text) if p.strip()]


def segment_sentences(text: str) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []
    out: list[str] = []
    for paragraph in segment_paragraphs(text):
        parts = _SENTENCE_SPLIT.split(paragraph)
        out.extend(p.strip() for p in parts if p.strip())
    return out
