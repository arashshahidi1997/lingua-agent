"""Lesson markdown export.

The canonical lesson lives at `content/units/<id>.md`. The frontmatter is the
schema; the body is human-readable. RTL target-language sections are wrapped
in `<div dir="rtl">` so they render correctly in any markdown viewer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import frontmatter

from ..languages.registry import get_language, has_language
from ..models import Exercise, Flashcard, GrammarPoint, LessonUnit, VocabularyItem


def _is_rtl(code: str) -> bool:
    return has_language(code) and get_language(code).direction.value == "rtl"


def _wrap_rtl(text: str, code: str) -> str:
    if _is_rtl(code):
        return f'<div dir="rtl">\n\n{text}\n\n</div>'
    return text


def render_unit_markdown(
    unit: LessonUnit,
    *,
    vocabulary: Iterable[VocabularyItem] = (),
    grammar: Iterable[GrammarPoint] = (),
    exercises: Iterable[Exercise] = (),
    flashcards: Iterable[Flashcard] = (),
) -> str:
    target = unit.target_language
    lines: list[str] = [f"# {unit.title}", ""]

    if unit.summary:
        lines += ["## Summary", "", unit.summary, ""]

    if unit.bilingual_reading:
        lines += ["## Bilingual reading", ""]
        # Use a markdown table so both directions are readable inline.
        lines += [f"| {unit.source_language} | {unit.target_language} |",
                  "|---|---|"]
        for pair in unit.bilingual_reading:
            src = pair.source.replace("|", r"\|")
            tgt = pair.target.replace("|", r"\|")
            if _is_rtl(target):
                tgt = f'<span dir="rtl">{tgt}</span>'
            lines.append(f"| {src} | {tgt} |")
        lines.append("")

    vocab_list = list(vocabulary)
    if vocab_list:
        lines += ["## Vocabulary", ""]
        body_lines = []
        for v in vocab_list:
            translation = ", ".join(v.translations.get(target, [])) or "—"
            gender = f" _{v.gender}._ " if v.gender else " "
            body_lines.append(f"- **{v.lemma}**{gender}— {translation}")
        body = "\n".join(body_lines)
        lines += [_wrap_rtl(body, target), ""]

    grammar_list = list(grammar)
    if grammar_list:
        lines += ["## Grammar focus", ""]
        for g in grammar_list:
            lines.append(f"- **{g.name}** — {g.summary}")
            for ev in g.evidence:
                if _is_rtl(target):
                    lines.append(f'    - _evidence:_ <span dir="rtl">{ev}</span>')
                else:
                    lines.append(f"    - _evidence:_ {ev}")
        lines.append("")

    ex_list = list(exercises)
    if ex_list:
        lines += ["## Exercises", ""]
        for i, e in enumerate(ex_list, 1):
            lines.append(f"{i}. **[{e.type.value}]** {e.prompt}")
            if e.expected_answer:
                lines.append(f"    - _expected:_ {e.expected_answer}")
            if e.choices:
                lines.append(f"    - _choices:_ {', '.join(e.choices)}")
        lines.append("")

    cards = list(flashcards)
    if cards:
        lines += ["## Review cards", ""]
        for c in cards:
            front, back = c.front, c.back
            if _is_rtl(target) and c.target_language == target:
                back = f'<span dir="rtl">{back}</span>'
            lines.append(f"- {front} → {back}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_unit(
    unit: LessonUnit,
    *,
    vocabulary: Iterable[VocabularyItem] = (),
    grammar: Iterable[GrammarPoint] = (),
    exercises: Iterable[Exercise] = (),
    flashcards: Iterable[Flashcard] = (),
    content_dir: Path,
) -> Path:
    units_dir = Path(content_dir) / "units"
    units_dir.mkdir(parents=True, exist_ok=True)
    body = render_unit_markdown(unit, vocabulary=vocabulary, grammar=grammar,
                                 exercises=exercises, flashcards=flashcards)
    metadata = {
        "id": unit.id,
        "title": unit.title,
        "source_language": unit.source_language,
        "target_language": unit.target_language,
        "support_language": unit.support_language,
        "cefr_level": unit.cefr_level,
        "source_document_ids": unit.source_document_ids,
        "vocabulary_ids": unit.vocabulary_ids,
        "grammar_ids": unit.grammar_ids,
        "exercise_ids": unit.exercise_ids,
        "flashcard_ids": unit.flashcard_ids,
        "tags": unit.tags,
        "created_at": unit.created_at.isoformat(),
    }
    post = frontmatter.Post(body, **metadata)
    path = units_dir / f"{unit.id}.md"
    path.write_text(frontmatter.dumps(post, sort_keys=False) + "\n", encoding="utf-8")
    return path


def read_unit(path: Path) -> tuple[dict, str]:
    """Return (metadata, body) of a saved unit. Useful for re-loading by hand."""
    post = frontmatter.load(Path(path))
    return dict(post.metadata), post.content
