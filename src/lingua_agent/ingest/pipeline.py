"""Ingest pipeline: text → Document + LessonUnit + vocabulary + grammar + exercises + flashcards.

The pipeline drives the AI provider through a sequence of structured
generations. Schemas live below as `*Draft` Pydantic models; the provider
returns one of them per call. The mock provider produces deterministic,
schema-valid drafts so the whole thing runs end-to-end with no API key.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Literal

from pydantic import BaseModel, Field

from ..ai import AIProvider, MockProvider
from ..ai import prompts as P
from ..config import Settings
from ..ids import make_id
from ..lesson.markdown_export import write_unit
from ..models import (
    CardDirection,
    CardType,
    Document,
    Exercise,
    ExerciseType,
    Flashcard,
    GrammarPoint,
    LessonUnit,
    Provenance,
    ReadingPair,
    VocabularyItem,
)
from ..models.base import utcnow
from ..models.exercises import GeneratedFrom, GradingMode
from ..storage import JsonRepository
from .text import normalize_text, segment_sentences


# --- Provider draft schemas (what the AI returns) -------------------------

class MaterialAnalysis(BaseModel):
    summary: str
    themes: list[str] = Field(default_factory=list)
    suitable_for_levels: list[str] = Field(default_factory=list)


class VocabularyDraftItem(BaseModel):
    lemma: str
    surface: str
    translations: dict[str, list[str]] = Field(default_factory=dict)
    pos: str | None = None
    gender: Literal["m", "f", "n"] | None = None
    transliteration: str | None = None
    example_text: str | None = None
    cefr_level: str | None = None
    confidence: Literal["high", "medium", "low", "uncertain"] | None = "medium"


class VocabularyDraft(BaseModel):
    items: list[VocabularyDraftItem] = Field(default_factory=list)


class GrammarDraftPoint(BaseModel):
    name: str
    summary: str
    evidence: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low", "uncertain"] | None = "medium"


class GrammarDraft(BaseModel):
    points: list[GrammarDraftPoint] = Field(default_factory=list)


class LessonDraft(BaseModel):
    summary: str
    bilingual_reading: list[ReadingPair] = Field(default_factory=list)


class ExerciseDraft(BaseModel):
    prompt: str
    expected_answer: str | None = None
    acceptable_answers: list[str] = Field(default_factory=list)
    choices: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    explanation: str | None = None


# --- Pipeline result -------------------------------------------------------

@dataclass
class IngestResult:
    document: Document
    unit: LessonUnit
    vocabulary: list[VocabularyItem] = field(default_factory=list)
    grammar: list[GrammarPoint] = field(default_factory=list)
    exercises: list[Exercise] = field(default_factory=list)
    flashcards: list[Flashcard] = field(default_factory=list)
    unit_path: str | None = None


# --- Repositories factory --------------------------------------------------

def _repos(settings: Settings) -> dict[str, JsonRepository]:
    settings.ensure_dirs()
    root = settings.data_dir
    return {
        "documents": JsonRepository(root, "documents", Document),
        "lessons": JsonRepository(root, "lessons", LessonUnit),
        "flashcards": JsonRepository(root, "flashcards", Flashcard),
        "exercises": JsonRepository(root, "exercises", Exercise),
    }


# --- Main entrypoint -------------------------------------------------------

def ingest_text(
    *,
    text: str,
    title: str,
    source_language: str,
    target_language: str,
    support_language: str | None = None,
    cefr_level: str | None = None,
    tags: list[str] | None = None,
    provider: AIProvider | None = None,
    settings: Settings | None = None,
    persist: bool = True,
) -> IngestResult:
    """Run the full ingest pipeline and return the produced artifacts."""

    settings = settings or Settings.load()
    provider = provider or MockProvider()
    text = normalize_text(text)
    if not text:
        raise ValueError("ingest_text: empty text")

    repos = _repos(settings) if persist else {}

    # 1. Document
    doc_id = make_id("doc", source_language, text, slug=title)
    document = Document(
        id=doc_id,
        title=title,
        source_language=source_language,
        text=text,
        tags=tags or [],
    )

    # 2. Lesson draft (bilingual reading + summary)
    lesson_prompt = P.lesson_generation_prompt(
        source_language=source_language, target_language=target_language,
        support_language=support_language, level=cefr_level, title=title, text=text,
    )
    lesson_draft = provider.generate_structured(
        lesson_prompt, LessonDraft,
        context={"source_language": source_language, "target_language": target_language, "text": text},
    )

    # 3. Vocabulary
    vocab_prompt = P.vocabulary_extraction_prompt(
        source_language=source_language, target_language=target_language,
        level=cefr_level, text=text,
    )
    vocab_draft = provider.generate_structured(
        vocab_prompt, VocabularyDraft,
        context={"source_language": source_language, "target_language": target_language, "text": text},
    )
    vocab: list[VocabularyItem] = []
    for item in vocab_draft.items:
        vocab.append(VocabularyItem(
            id=make_id("vocab", target_language, item.lemma, slug=item.lemma),
            lemma=item.lemma,
            surface=item.surface,
            target_language=target_language,
            translations=item.translations,
            pos=item.pos,
            gender=item.gender,
            transliteration=item.transliteration,
            example_text=item.example_text,
            cefr_level=item.cefr_level,
            provenance=Provenance.by_model(provider.name, source_doc_id=document.id, confidence=item.confidence or "medium"),
        ))

    # 4. Grammar
    grammar_prompt = P.grammar_extraction_prompt(
        source_language=source_language, target_language=target_language,
        level=cefr_level, text=text,
    )
    grammar_draft = provider.generate_structured(
        grammar_prompt, GrammarDraft,
        context={"source_language": source_language, "target_language": target_language, "text": text},
    )
    grammar: list[GrammarPoint] = []
    for point in grammar_draft.points:
        grammar.append(GrammarPoint(
            id=make_id("grammar", target_language, point.name, slug=point.name),
            target_language=target_language,
            name=point.name,
            summary=point.summary,
            evidence=point.evidence,
            cefr_level=cefr_level,
            support_language=support_language,
            provenance=Provenance.by_model(provider.name, source_doc_id=document.id, confidence=point.confidence or "medium"),
        ))

    # 5. Exercises — one per type, seeded from the first vocab + grammar items.
    exercises: list[Exercise] = []
    seed_vocab = [v.lemma for v in vocab[:3]] or ["coffee"]
    seed_grammar = [g.name for g in grammar[:1]]
    for ex_type in (ExerciseType.TRANSLATE_A_TO_B, ExerciseType.MULTIPLE_CHOICE, ExerciseType.CLOZE):
        prompt = P.exercise_generation_prompt(
            source_language=source_language, target_language=target_language,
            vocab_items=seed_vocab, grammar_points=seed_grammar,
            type=ex_type.value, difficulty=2,
        )
        draft = provider.generate_structured(
            prompt, ExerciseDraft,
            context={"source_language": source_language, "target_language": target_language,
                     "exercise_type": ex_type.value, "vocab_items": seed_vocab,
                     "grammar_points": seed_grammar},
        )
        exercises.append(Exercise(
            id=make_id("ex", target_language, ex_type.value, draft.prompt, slug=ex_type.value),
            type=ex_type,
            source_language=source_language,
            target_language=target_language,
            prompt=draft.prompt,
            expected_answer=draft.expected_answer,
            acceptable_answers=draft.acceptable_answers,
            choices=draft.choices,
            hints=draft.hints,
            explanation=draft.explanation,
            difficulty=2,
            skill_tags=[t for t in (["vocab"] + (["grammar"] if seed_grammar else [])) if t],
            generated_from=GeneratedFrom(
                document_id=document.id,
                vocabulary_ids=[v.id for v in vocab[:3]],
                grammar_ids=[g.id for g in grammar[:1]],
            ),
            grading_mode=GradingMode.HYBRID if ex_type == ExerciseType.TRANSLATE_A_TO_B else GradingMode.DETERMINISTIC,
            provenance=Provenance.by_model(provider.name, source_doc_id=document.id),
        ))

    # 6. Flashcards — one production card per vocab item.
    flashcards: list[Flashcard] = []
    now = utcnow()
    for v in vocab:
        translation = next(iter(v.translations.get(target_language, [])), v.lemma)
        flashcards.append(Flashcard(
            id=make_id("card", target_language, v.id, "production"),
            front=v.lemma,
            back=translation,
            source_language=source_language,
            target_language=target_language,
            direction=CardDirection.PRODUCTION,
            card_type=CardType.VOCAB,
            vocabulary_item_id=v.id,
            examples=[v.example_text] if v.example_text else [],
            tags=[f"unit:{title.lower().replace(' ', '-')}"],
            due_at=now,  # new cards due immediately
            provenance=Provenance.by_model(provider.name, source_doc_id=document.id),
        ))

    # 7. Lesson unit (assemble + write markdown)
    unit_id = make_id("unit", document.id, target_language, slug=title)
    unit = LessonUnit(
        id=unit_id,
        title=title,
        source_language=source_language,
        target_language=target_language,
        support_language=support_language,
        cefr_level=cefr_level,  # type: ignore[arg-type]
        source_document_ids=[document.id],
        vocabulary_ids=[v.id for v in vocab],
        grammar_ids=[g.id for g in grammar],
        exercise_ids=[e.id for e in exercises],
        flashcard_ids=[c.id for c in flashcards],
        bilingual_reading=lesson_draft.bilingual_reading,
        summary=lesson_draft.summary,
        tags=tags or [],
    )

    result = IngestResult(
        document=document, unit=unit, vocabulary=vocab, grammar=grammar,
        exercises=exercises, flashcards=flashcards,
    )

    if persist:
        repos["documents"].save(document)
        repos["lessons"].save(unit)
        for e in exercises:
            repos["exercises"].save(e)
        for c in flashcards:
            repos["flashcards"].save(c)
        result.unit_path = str(write_unit(
            unit, vocabulary=vocab, grammar=grammar, exercises=exercises, flashcards=flashcards,
            content_dir=settings.content_dir,
        ))

    return result
