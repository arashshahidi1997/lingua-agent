"""Language registry — Language model + the four MVP languages.

Central source of truth for direction, script, and transliteration policy.
External callers should use `get_language(code)`; the registry is read-mostly
but extensible via `register_language`.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Direction(str, Enum):
    LTR = "ltr"
    RTL = "rtl"


class Script(str, Enum):
    LATIN = "latin"
    CYRILLIC = "cyrillic"
    ARABIC = "arabic"
    DEVANAGARI = "devanagari"
    CJK = "cjk"
    OTHER = "other"


class Language(BaseModel):
    code: str = Field(..., description="BCP-47-ish, e.g. 'en', 'fa', 'it', 'ru'")
    name: str
    native_name: str
    script: Script
    direction: Direction
    transliteration_supported: bool = False
    notes: str | None = None


_REGISTRY: dict[str, Language] = {}


def register_language(language: Language) -> Language:
    _REGISTRY[language.code] = language
    return language


def get_language(code: str) -> Language:
    code = code.strip().lower()
    if code not in _REGISTRY:
        raise KeyError(f"unknown language code: {code!r}. Known: {sorted(_REGISTRY)}")
    return _REGISTRY[code]


def list_languages() -> list[Language]:
    return sorted(_REGISTRY.values(), key=lambda lang: lang.code)


def has_language(code: str) -> bool:
    return code.strip().lower() in _REGISTRY


# --- MVP language seed -----------------------------------------------------

register_language(
    Language(
        code="en",
        name="English",
        native_name="English",
        script=Script.LATIN,
        direction=Direction.LTR,
        transliteration_supported=False,
    )
)
register_language(
    Language(
        code="it",
        name="Italian",
        native_name="Italiano",
        script=Script.LATIN,
        direction=Direction.LTR,
        transliteration_supported=False,
        notes="Romance; gendered nouns; rich verb conjugation.",
    )
)
register_language(
    Language(
        code="ru",
        name="Russian",
        native_name="Русский",
        script=Script.CYRILLIC,
        direction=Direction.LTR,
        transliteration_supported=True,
        notes="Six cases; aspect pairs; mobile stress.",
    )
)
register_language(
    Language(
        code="fa",
        name="Persian (Farsi)",
        native_name="فارسی",
        script=Script.ARABIC,
        direction=Direction.RTL,
        transliteration_supported=True,
        notes="Ezafe; light verbs; no grammatical gender; formal vs colloquial register.",
    )
)
register_language(
    Language(
        code="de",
        name="German",
        native_name="Deutsch",
        script=Script.LATIN,
        direction=Direction.LTR,
        transliteration_supported=False,
        notes="Three genders; four cases; V2 word order; separable verbs; capitalised nouns.",
    )
)
register_language(
    Language(
        code="nl",
        name="Dutch",
        native_name="Nederlands",
        script=Script.LATIN,
        direction=Direction.LTR,
        transliteration_supported=False,
        notes="Two genders (de/het); no case marking; V2 word order; separable verbs.",
    )
)


# Convenience type alias for callers that want to constrain at the type level.
LanguageCode = Literal["en", "it", "ru", "fa", "de", "nl"]
