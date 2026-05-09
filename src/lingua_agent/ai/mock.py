"""Deterministic mock AI provider.

The mock provider is the **default** in MVP. It produces schema-valid Pydantic
output without any network call, so the entire ingest pipeline runs in tests
and on machines with no API keys. The output is templated, not authored —
plug in a real provider for real content.

Determinism is keyed on (prompt + schema name) so repeated calls in tests
return the same bytes.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, TypeVar

from pydantic import BaseModel

from .base import ChatMessage, ChatResponse, GenerationError

T = TypeVar("T", bound=BaseModel)


# Tiny stand-in dictionary for template translations. Real provider replaces all
# of this. Keys are normalized lowercase lemmas.
_FAKE_DICT: dict[str, dict[str, str]] = {
    "coffee": {"it": "caffè", "fa": "قهوه", "ru": "кофе"},
    "water": {"it": "acqua", "fa": "آب", "ru": "вода"},
    "glass": {"it": "bicchiere", "fa": "لیوان", "ru": "стакан"},
    "train": {"it": "treno", "fa": "قطار", "ru": "поезд"},
    "station": {"it": "stazione", "fa": "ایستگاه", "ru": "станция"},
    "friend": {"it": "amico", "fa": "دوست", "ru": "друг"},
    "university": {"it": "università", "fa": "دانشگاه", "ru": "университет"},
    "biology": {"it": "biologia", "fa": "زیست‌شناسی", "ru": "биология"},
    "today": {"it": "oggi", "fa": "امروز", "ru": "сегодня"},
    "yesterday": {"it": "ieri", "fa": "دیروز", "ru": "вчера"},
    "book": {"it": "libro", "fa": "کتاب", "ru": "книга"},
    "letter": {"it": "lettera", "fa": "نامه", "ru": "письмо"},
    "read": {"it": "leggere", "fa": "خواندن", "ru": "читать"},
    "write": {"it": "scrivere", "fa": "نوشتن", "ru": "писать"},
    "the": {"it": "il", "fa": "", "ru": ""},
    "a": {"it": "un", "fa": "یک", "ru": ""},
    "and": {"it": "e", "fa": "و", "ru": "и"},
    "of": {"it": "di", "fa": "از", "ru": ""},
    "is": {"it": "è", "fa": "است", "ru": ""},
    "i": {"it": "io", "fa": "من", "ru": "я"},
    "you": {"it": "tu", "fa": "تو", "ru": "ты"},
    "she": {"it": "lei", "fa": "او", "ru": "она"},
    "he": {"it": "lui", "fa": "او", "ru": "он"},
    "would": {"it": "vorrei", "fa": "می‌خواهم", "ru": "хотел бы"},
    "like": {"it": "vorrei", "fa": "می‌خواهم", "ru": "хотел бы"},
    "where": {"it": "dove", "fa": "کجا", "ru": "где"},
    "study": {"it": "studia", "fa": "می‌خواند", "ru": "изучает"},
    "going": {"it": "va", "fa": "می‌رود", "ru": "идёт"},
}


_TOKEN_RE = re.compile(r"[\w'’]+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text)


def _fake_translate_word(word: str, target_language: str) -> str:
    key = word.lower()
    entry = _FAKE_DICT.get(key)
    if entry and entry.get(target_language):
        return entry[target_language]
    return f"⟨{word}⟩"


def _fake_translate_sentence(sentence: str, target_language: str) -> str:
    parts = []
    for tok in _tokenize(sentence):
        translated = _fake_translate_word(tok, target_language)
        if translated:
            parts.append(translated)
    if not parts:
        return f"⟨{sentence}⟩"
    return " ".join(parts)


def _seed_from(prompt: str, schema_name: str) -> int:
    h = hashlib.sha256(f"{schema_name}::{prompt}".encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big")


def _extract_kv(prompt: str, key: str) -> str | None:
    # Crude parser for our `key: value` lines in prompt templates.
    m = re.search(rf"^{re.escape(key)}:\s*(.+)$", prompt, flags=re.MULTILINE)
    return m.group(1).strip() if m else None


def _extract_text_block(prompt: str) -> str:
    # Look for the `---\n…\n---` block produced by our prompt templates.
    m = re.search(r"---\n(.*?)\n---", prompt, flags=re.DOTALL)
    return m.group(1).strip() if m else ""


class MockProvider:
    name = "mock"

    def generate_structured(self, prompt: str, schema: type[T], *, context: dict[str, Any] | None = None) -> T:
        ctx = context or {}
        target_language = ctx.get("target_language") or _extract_kv(prompt, "target_language") or "it"
        source_language = ctx.get("source_language") or _extract_kv(prompt, "source_language") or "en"
        text = ctx.get("text") or _extract_text_block(prompt)
        schema_name = schema.__name__

        try:
            payload = self._build_payload(schema_name, prompt=prompt, text=text,
                                          source_language=source_language, target_language=target_language,
                                          context=ctx)
            return schema.model_validate(payload)
        except Exception as exc:  # pragma: no cover - defensive
            raise GenerationError(f"mock provider failed for schema {schema_name}: {exc}") from exc

    def chat(self, messages: list[ChatMessage], *, tools: list[dict[str, Any]] | None = None) -> ChatResponse:
        last = messages[-1].content if messages else ""
        return ChatResponse(
            content=f"[mock tutor] I read: {last[:120]!r}. Try `generate_exercise` or `list_due_cards`.",
            tool_calls=[],
        )

    # -- payload builders ---------------------------------------------------

    def _build_payload(self, schema_name: str, *, prompt: str, text: str, source_language: str,
                       target_language: str, context: dict[str, Any]) -> dict[str, Any]:
        if schema_name == "MaterialAnalysis":
            return self._material_analysis(text)
        if schema_name == "VocabularyDraft":
            return self._vocabulary_draft(text, source_language=source_language,
                                           target_language=target_language)
        if schema_name == "GrammarDraft":
            return self._grammar_draft(text, target_language=target_language)
        if schema_name == "LessonDraft":
            return self._lesson_draft(text, source_language=source_language,
                                       target_language=target_language)
        if schema_name == "ExerciseDraft":
            return self._exercise_draft(context, source_language=source_language,
                                         target_language=target_language)
        if schema_name == "GradingResult":
            return self._grading_result(context)
        raise GenerationError(f"mock provider has no template for schema {schema_name!r}")

    def _material_analysis(self, text: str) -> dict[str, Any]:
        words = len(_tokenize(text))
        themes: list[str] = []
        for theme, markers in (("food", {"coffee", "water"}), ("travel", {"train", "station"}),
                                ("study", {"university", "biology", "book"})):
            if any(_tokenize(text.lower()).count(m) for m in markers):
                themes.append(theme)
        return {
            "summary": text[:140].strip() or "(empty)",
            "themes": themes or ["general"],
            "suitable_for_levels": ["A1", "A2"] if words < 40 else ["A2", "B1"],
        }

    def _vocabulary_draft(self, text: str, *, source_language: str, target_language: str) -> dict[str, Any]:
        # Pick distinct content words; cap at 8.
        seen: list[str] = []
        for tok in _tokenize(text):
            t = tok.lower()
            if t in seen:
                continue
            if t in {"the", "a", "and", "of", "to", "is", "in", "i", "you"}:
                continue
            seen.append(t)
        items = []
        for surface in seen[:8]:
            translation = _fake_translate_word(surface, target_language)
            items.append({
                "lemma": surface,
                "surface": surface,
                "translations": {target_language: [translation]},
                "pos": "unknown",
                "example_text": text.split(".")[0].strip() + ".",
                "cefr_level": "A1",
                "confidence": "uncertain",
            })
        return {"items": items}

    def _grammar_draft(self, text: str, *, target_language: str) -> dict[str, Any]:
        evidence = [s.strip() for s in re.split(r"[.?!]", text) if s.strip()][:2]
        if target_language == "it":
            point = {"name": "polite conditional",
                     "summary": "Use 'vorrei' to soften requests.",
                     "evidence": evidence,
                     "confidence": "medium"}
        elif target_language == "fa":
            point = {"name": "ezafe construction",
                     "summary": "Link nouns to modifiers with -e / -ye.",
                     "evidence": evidence,
                     "confidence": "medium"}
        elif target_language == "ru":
            point = {"name": "verbal aspect",
                     "summary": "Pair imperfective and perfective forms when learning a new verb.",
                     "evidence": evidence,
                     "confidence": "medium"}
        else:
            point = {"name": "basic word order",
                     "summary": "Subject-verb-object.",
                     "evidence": evidence,
                     "confidence": "low"}
        return {"points": [point]}

    def _lesson_draft(self, text: str, *, source_language: str, target_language: str) -> dict[str, Any]:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        pairs = [{"source": s, "target": _fake_translate_sentence(s, target_language)} for s in sentences]
        return {
            "summary": (text[:120] + "…") if len(text) > 120 else text,
            "bilingual_reading": pairs,
        }

    def _exercise_draft(self, ctx: dict[str, Any], *, source_language: str, target_language: str) -> dict[str, Any]:
        ex_type = ctx.get("exercise_type", "translate_a_to_b")
        vocab = ctx.get("vocab_items") or ["coffee"]
        word = vocab[0]
        translation = _fake_translate_word(word, target_language)
        if ex_type == "translate_a_to_b":
            return {
                "prompt": f"Translate to {target_language}: {word}",
                "expected_answer": translation,
                "acceptable_answers": [translation],
                "choices": [],
                "hints": [f"It starts with {translation[:1]!r}."] if translation else [],
                "explanation": f"{word!r} maps to {translation!r}.",
            }
        if ex_type == "cloze":
            return {
                "prompt": f"Fill in: ___ {translation}",
                "expected_answer": "un" if target_language == "it" else "a",
                "acceptable_answers": ["un", "uno", "a"],
                "choices": [],
                "hints": [],
                "explanation": "Indefinite article.",
            }
        if ex_type == "multiple_choice":
            choices = [translation, "—", "??"]
            return {
                "prompt": f"Which means {word!r} in {target_language}?",
                "expected_answer": translation,
                "acceptable_answers": [translation],
                "choices": choices,
                "hints": [],
                "explanation": "",
            }
        return {
            "prompt": f"Write a sentence using {translation!r}.",
            "expected_answer": None,
            "acceptable_answers": [],
            "choices": [],
            "hints": [],
            "explanation": "",
        }

    def _grading_result(self, ctx: dict[str, Any]) -> dict[str, Any]:
        answer = (ctx.get("answer") or "").strip().lower()
        expected = (ctx.get("expected") or "").strip().lower()
        correct = bool(expected) and answer == expected
        return {
            "correct": correct,
            "score": 1.0 if correct else 0.0,
            "feedback": "Correct." if correct else f"Expected {expected!r}.",
        }
