"""Deterministic, URL-safe ID generation.

Hash-based IDs make the ingest pipeline reproducible: ingesting the same text
twice yields the same Document and LessonUnit IDs, which keeps tests stable
and makes re-ingestion idempotent.
"""

from __future__ import annotations

import hashlib
import re
import secrets

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str, *, max_len: int = 32) -> str:
    text = text.lower()
    text = _SLUG_RE.sub("-", text).strip("-")
    if not text:
        text = "untitled"
    return text[:max_len].rstrip("-") or "untitled"


def short_hash(*parts: str, length: int = 10) -> str:
    h = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return h[:length]


def make_id(prefix: str, *parts: str, slug: str | None = None) -> str:
    """Stable ID derived from `parts` (and optional human-readable `slug`)."""
    digest = short_hash(*parts) if parts else secrets.token_hex(5)
    if slug:
        return f"{prefix}_{slugify(slug, max_len=20)}_{digest}"
    return f"{prefix}_{digest}"
